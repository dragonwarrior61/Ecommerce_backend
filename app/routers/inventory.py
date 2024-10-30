from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import any_
from sqlalchemy.orm import aliased
from app.models.product import Product
from app.models.user import User
from app.routers.auth import get_current_user
from app.models.internal_product import Internal_Product
from app.models.orders import Order
from app.models.shipment import Shipment 
from app.models.team_member import Team_member
from app.schemas.shipment import ShipmentCreate, ShipmentRead, ShipmentUpdate
from app.database import get_db
from app.utils.emag_products import *
from sqlalchemy import func, and_, text
from datetime import datetime, timedelta
from decimal import Decimal
import barcode
from barcode.writer import ImageWriter

router = APIRouter()

async def get_imports(ean: str, db:AsyncSession):
    query = select(Shipment).where(ean == any_(Shipment.ean))
    result = await db.execute(query)

    shipments = result.scalars().all()

    imports_data = []

    for shipment in shipments:
        quantity = 0
        if shipment.status == "Arrived":
            continue
        ean_list = shipment.ean
        quantity_list = shipment.quantity
        title = shipment.title
        for i in range(len(ean_list)):
            if ean_list[i] != ean:
                continue
            quantity += quantity_list[i]
        imports_data.append({
            "id": shipment.id,
            "title": title,
            "quantity": quantity
        })

    return imports_data

@router.get('/product')
async def get_product_info(
    shipment_type: int = Query(0),
    query_stock_days: int = Query(0),
    query_imports_stocks: int = Query(0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if user.role == -1:
        raise HTTPException(status_code=401, detail="Authentication error")
    
    if user.role != 4:
        result = await db.execute(select(Team_member).where(Team_member.user == user.id))
        db_team = result.scalars().first()
        user_id = db_team.admin
    else:
        user_id = user.id
        
    cnt = {}

    ProductAlias = aliased(Product)
    query = select(Order, ProductAlias).join(
        ProductAlias,
        and_(
            ProductAlias.id == any_(Order.product_id),
            ProductAlias.product_marketplace == Order.order_market_place,
            ProductAlias.user_id == Order.user_id
        )
    )
    query = query.where(Order.user_id == user_id)
    time = datetime.now()
    thirty_days_ago = time - timedelta(days=30)
    query1 = query.where(Order.date > thirty_days_ago)
    result = await db.execute(query1)
    orders_with_products = result.all()

    for order, product in orders_with_products:
        product_ids = order.product_id
        quantities = order.quantity
        for i in range(len(product_ids)):
            if product.id == product_ids[i]:
                if product.ean not in cnt:
                    cnt[product.ean] = quantities[i]
                else:
                    cnt[product.ean] += quantities[i]

    ninety_days_ago = time - timedelta(days=90)
    query2 = query.where(Order.date > ninety_days_ago)

    result = await db.execute(query2)

    orders_with_products_ninety = result.all()
    cnt90 = {}
    for order, product in orders_with_products_ninety:
        product_ids = order.product_id
        quantities = order.quantity
        for i in range(len(product_ids)):
            if product.id == product_ids[i]:
                if product.ean not in cnt90:
                    cnt90[product.ean] = quantities[i]
                else:
                    cnt90[product.ean] += quantities[i]

    product_result = await db.execute(select(Internal_Product).where(Internal_Product.user_id == user_id))
    products = product_result.scalars().all()

    product_data = []
    for product in products:
        dimension = product.dimensions
        if dimension:
            numbers = dimension.split('*')
            if len(numbers) == 3 and all(num.strip() for num in numbers):
                w, h, d = map(lambda x: float(x.replace(',', '.')), numbers)
            else:
                w, h, d = (0.0, 0.0, 0.0)
        else:
            w, h, d = (0.0, 0.0, 0.0)
        if product.pcs_ctn:
            volumetric_weight = w * h * d / 5000 / int(product.pcs_ctn)
        else:
            volumetric_weight = 0
        
        if w == 0.0 or h == 0.0 or d == 0.0:
            type = -1
        elif product.weight < 0.35 and volumetric_weight < 0.35:
            type = 1
        elif product.battery:
            type = 2
        else:
            type = 3
        
        if type != shipment_type and shipment_type != 0:
            continue

        if type == 2:
            volumetric_weight = w * h * d / 6000 / int(product.pcs_ctn)
        stock = product.stock
        product_id = product.id
        ean = product.ean

        imports_datas = await get_imports(ean, db)
        imports = sum(imports_data.get("quantity") for imports_data in imports_datas)

        if ean not in cnt:
            continue
        else:
            days = 30
            ave_sales = cnt[ean] / days
            logging.info(f" sales per day is {ave_sales}")
            stock_days = int(stock / ave_sales) if ave_sales > 0 else -1
            stock_imports_days = int(((stock + imports) / ave_sales)) if ave_sales > 0 else -1

            if  stock_imports_days < query_stock_days:
                quantity = int(query_stock_days * ave_sales) - stock - imports
            else:
                quantity = ""
        
            if (query_imports_stocks == 0 or imports < query_imports_stocks) or (query_stock_days == 0 or stock_imports_days < query_stock_days):
                product_data.append({
                    "id": product.id,
                    "type": type,
                    "product_name": product.product_name,
                    "ean": product.ean,
                    "sales_per_day": ave_sales,
                    "quantity": quantity,
                    "image_link": product.image_link,
                    "link_address_1688": product.link_address_1688,
                    "sale_price": product.price,
                    "wechat": product.supplier_id,
                    "stock_imports": [product.stock, ave_sales, imports],
                    "day_stock": [stock_days, stock_imports_days],
                    "imports_data": imports_datas,
                    "pcs_ctn": product.pcs_ctn,
                    "masterbox_title": product.masterbox_title,
                    "barcode_title": product.barcode_title, 
                    "price_1688": product.price_1688,
                    "link_address_1688": product.link_address_1688,
                    "variation_name_1688": product.variation_name_1688,
                    "dimensions": product.dimensions,
                    "weight": product.weight,
                    "volumetric_weight": volumetric_weight,
                    "model_name": product.model_name,
                    "short_product_name": product.short_product_name,
                    "observation": product.observation,
                    "discontinued": product.discontinued,
                    "battery": product.battery,
                    "sales": cnt[ean],
                    "sales90": cnt90[ean],
                    "product_code": product.product_code
                })
    return product_data

@router.get('/shipment_product')
async def get_product_info(
    shipment_type: int = Query(0),
    query_stock_days: int = Query(0),
    query_imports_stocks: int = Query(0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if user.role == -1:
        raise HTTPException(status_code=401, detail="Authentication error")
    
    if user.role != 4:
        result = await db.execute(select(Team_member).where(Team_member.user == user.id))
        db_team = result.scalars().first()
        user_id = db_team.admin
    else:
        user_id = user.id

    cnt = {}

    ProductAlias = aliased(Product)
    query = select(Order, ProductAlias).join(
        ProductAlias,
        and_(
            ProductAlias.id == any_(Order.product_id),
            ProductAlias.product_marketplace == Order.order_market_place,
            ProductAlias.user_id == Order.user_id
        )
    )
    
    query = query.where(Order.user_id == user_id)

    time = datetime.now()
    thirty_days_ago = time - timedelta(days=30)
    query1 = query.where(Order.date > thirty_days_ago)

    result = await db.execute(query1)
    orders_with_products = result.all()

    for order, product in orders_with_products:
        product_ids = order.product_id
        quantities = order.quantity
        for i in range(len(product_ids)):
            if product.id == product_ids[i]:
                if product.ean not in cnt:
                    cnt[product.ean] = quantities[i]
                else:
                    cnt[product.ean] += quantities[i]

    product_result = await db.execute(select(Internal_Product).where(Internal_Product.user_id == user_id))
    products = product_result.scalars().all()

    product_data = []
    for product in products:
        dimension = product.dimensions
        if dimension:
            numbers = dimension.split('*')
            # Ensure all parts are valid before conversion
            if len(numbers) == 3 and all(num.strip() for num in numbers):
                # Replace commas with dots to handle different decimal notations
                w, h, d = map(lambda x: float(x.replace(',', '.')), numbers)
            else:
                w, h, d = (0.0, 0.0, 0.0)
        else:
            w, h, d = (0.0, 0.0, 0.0)
        if product.pcs_ctn:
            volumetric_weight = w * h * d / 5000 / int(product.pcs_ctn)
        else:
            volumetric_weight = 0
        
        if w == 0.0 or h == 0.0 or d == 0.0:
            type = -1
        else:
            if product.weight < 0.35 and volumetric_weight < 0.35:
                type = 1
            else:
                volumetric_weight = w * h * d / 6000 / int(product.pcs_ctn)
                if product.battery:
                    type = 2
                else:
                    type = 3
        
        if type != shipment_type and shipment_type != 0:
            continue

        if type == 2:
            volumetric_weight = w * h * d / 6000 / int(product.pcs_ctn)
        stock = product.stock
        product_id = product.id
        ean = product.ean

        imports_datas = await get_imports(ean, db)
        imports = sum(imports_data.get("quantity") for imports_data in imports_datas)

        if ean not in cnt:
            product_data.append({
                "id": product.id,
                "type": type,
                "product_name": product.product_name,
                "ean": product.ean,
                "quantity": query_imports_stocks,
                "image_link":product.image_link,
                "link_address_1688": product.link_address_1688,
                "sale_price": product.price,
                "wechat": product.supplier_id,
                "stock_imports": [product.stock, 0, imports],
                "day_stock": [0, 0],
                "imports_data": imports_datas,
                "pcs_ctn": product.pcs_ctn,
                "masterbox_title": product.masterbox_title,
                "barcode_title": product.barcode_title,
                "price_1688": product.price_1688,
                "link_address_1688": product.link_address_1688,
                "variation_name_1688": product.variation_name_1688,
                "dimensions": product.dimensions,
                "weight": product.weight,
                "volumetric_weight": volumetric_weight,
                "model_name": product.model_name,
                "short_product_name": product.short_product_name,
                "battery": product.battery
            })
        else:
            days = 30
            ave_sales = cnt[ean] / days
            logging.info(f" sales per day is {ave_sales}")
            stock_days = int(stock / ave_sales) if ave_sales > 0 else -1
            stock_imports_days = int(((stock + imports) / ave_sales)) if ave_sales > 0 else -1

            if  stock_imports_days < query_stock_days:
                quantity = int(query_stock_days * ave_sales) - stock - imports
            else:
                quantity = ""
        
            if (query_imports_stocks == 0 or imports < query_imports_stocks) and (query_stock_days == 0 or stock_imports_days < query_stock_days):
                product_data.append({
                    "id": product.id,
                    "type": type,
                    "product_name": product.product_name,
                    "ean": product.ean,
                    "quantity": quantity,
                    "image_link": product.image_link,
                    "link_address_1688": product.link_address_1688,
                    "sale_price": product.price,
                    "wechat": product.supplier_id,
                    "stock_imports": [product.stock, ave_sales, imports],
                    "day_stock": [stock_days, stock_imports_days],
                    "imports_data": imports_datas,
                    "pcs_ctn": product.pcs_ctn,
                    "masterbox_title": product.masterbox_title,
                    "barcode_title": product.barcode_title, 
                    "price_1688": product.price_1688,
                    "link_address_1688": product.link_address_1688,
                    "variation_name_1688": product.variation_name_1688,
                    "dimensions": product.dimensions,
                    "weight": product.weight,
                    "volumetric_weight": volumetric_weight,
                    "model_name": product.model_name,
                    "short_product_name": product.short_product_name
                })
    return product_data

@router.get('/product/advance')
async def get_product_advanced_info(
    db: AsyncSession = Depends(get_db),
    shipment_type: int = Query(None),
    weight_min: Decimal = Query(None),
    weight_max: Decimal = Query(None),
    volumetric_weight_min: Decimal = Query(None),
    volumetric_weight_max: Decimal = Query(None),
    user: User = Depends(get_current_user)
):
    if user.role == -1:
        raise HTTPException(status_code=401, detail="Authentication error")
    
    if user.role != 4:
        result = await db.execute(select(Team_member).where(Team_member.user == user.id))
        db_team = result.scalars().first()
        user_id = db_team.admin
    else:
        user_id = user.id
        
    query_ship = select(Shipment)

    if shipment_type is not None:
        query_ship = query_ship.where(Shipment.type == shipment_type)
    
    query_ship = query_ship.where(Shipment.user_id == user_id)
    shipments_result = await db.execute(query_ship)
    shipments = shipments_result.scalars().all()

    product_type_list = []
    unique_names = set()

    for shipment in shipments:
        name_list = shipment.title
        for name in name_list:
            if name not in unique_names:
                product_type_list.append(name)
                unique_names.add(name)

    query = select(Internal_Product)
    if weight_min is not None:
        query = query.where(Internal_Product.weight >= weight_min)
    
    if weight_max is not None:
        query = query.where(Internal_Product.weight <= weight_max)
    
    if volumetric_weight_min is not None:
        query = query.where(Internal_Product.volumetric_weight >= volumetric_weight_min)
    
    if volumetric_weight_max is not None:
        query = query.where(Internal_Product.volumetric_weight <= volumetric_weight_max)
    
    if shipment_type is not None:
        query = query.where(Internal_Product.product_name in product_type_list)
    query = query.where(Internal_Product.user_id == user_id)
    result = await db.execute(query)
    products = result.scalars().all()
    product_data = []

    for product in products:
        product_data.append({
            "id": product.id,
            "product_name" : product.product_name,
            "price": product.price,
            "sale_price": product.sale_price,
            "image_link": product.image_link,
            "weight": product.weight,
            "volumetric_weight": product.volumetric_weight,
            "stock": product.stock,
            "shipment_type": shipment_type
        })

    return product_data

@router.get('/shipment')
async def  get_shipment_info(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    type_str: str = Query(None),
    status_str: str = Query(None)
):
    if user.role == -1:
        raise HTTPException(status_code=401, detail="Authentication error")
    
    if user.role != 4:
        result = await db.execute(select(Team_member).where(Team_member.user == user.id))
        db_team = result.scalars().first()
        user_id = db_team.admin
    else:
        user_id = user.id
        
    if type_str:
        type = [str(id.strip()) for id in type_str.split(",")]
    else:
        type = []

    if status_str:
        status = [str(id.strip()) for id in status_str.split(",")]
    else:
        status = []

    query = select(Shipment).where(Shipment.type.in_(type))
    query = query.where(Shipment.status == any_(status))
    query = query.where(Shipment.user_id == user_id)
    result = await db.execute(query)
    shipments = result.scalars().all()

    shipment_data = []
    for shipment in shipments:
        shipment_data.append({
            "id": shipment.id,
            "date": shipment.date,
            "type": shipment.type,
            "satus": shipment.status,
            "product_list": shipment.product_name_list
        })

    return shipment_data
