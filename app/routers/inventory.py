from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import any_
from app.models.product import Product
from app.models.orders import Order
from app.models.shipment import Shipment 
from app.schemas.shipment import ShipmentCreate, ShipmentRead, ShipmentUpdate
from app.database import get_db
from app.utils.emag_products import *
from sqlalchemy import func, and_, text
import datetime
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
        ean_list = shipment.ean
        quantity_list = shipment.quantity
        status_list = shipment.each_status
        title = shipment.title
        index = ean_list.index(ean)
        quantity = quantity_list[index]
        if status_list[index] == "arrived":
            continue
        imports_data.append({
            "title": title,
            "quantity": quantity
        })

    return imports_data


@router.get('shipment/product')
async def get_product_info(
    query_stock_days: int = Query(None),
    ean: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    query = await db.execute(select(Product).where(Product.ean == ean))
    product = query.scalars().first()
    product_id = product.id

    if product.weight < 350 and product.volumetric_weight < 350:
        type = 1
    elif product.battery:
        type = 2
    else:
        type = 3

    query = await db.execute(select(Order).where(product_id == any_(Order.product_id)))
    orders = query.scalars().all()
    
    cnt = 0
    min_time = datetime.datetime.today()
    max_time = datetime.datetime(0, 0, 0, 0, 0, 0)
    for order in orders:
        product_ids = order.product_id
        quantities = order.quantity

        index = product_ids.index(product_id)
        cnt += quantities[index]
        min_time = min(min_time, order.date)
        max_time = max(max_time, order.date)

    stock = product.stock
    import_datas = await get_imports(ean, db)
    imports = sum(import_data.get("quantity") for import_data in import_datas)
    days = (max_time - min_time).days + 1
    ave_sale = cnt / days
    stock_days = int(stock / ave_sale) if ave_sale > 0 else -1
    stock_imports_days = int((stock + imports) / ave_sale)

    if query_stock_days and stock_imports_days < query_stock_days:
        quantity = int(query_stock_days * ave_sale) - stock - imports
    else:
        quantity = ""

    return {
        "type": type,
        "quantity": quantity,
        "image_link": product.image_link,
        "wechat": product.supplier_id,
        "stock_imports": [product.stock, ave_sale, imports],
        "day_stock": [stock_days, stock_imports_days],
        "imports_data": import_datas
    }

@router.get('/product')
async def get_product_info(
    shipment_type: int = Query(0),
    query_stock_days: int = Query(0),
    query_imports_stocks: int = Query(0),
    db: AsyncSession = Depends(get_db)
):
    
    order_result = await db.execute(select(Order))
    orders = order_result.scalars().all()

    cnt = {}
    min_time = {}
    max_time = {}

    for order in orders:
        product_ids = order.product_id
        quantities = order.quantity
        for i in range(len(product_ids)):
            if product_ids[i] not in cnt:
                cnt[product_ids[i]] = 0
                min_time[product_ids[i]] = order.date
                max_time[product_ids[i]] = order.date
            
            cnt[product_ids[i]] += quantities[i]
            min_time[product_ids[i]] = min(min_time[product_ids[i]], order.date)
            max_time[product_ids[i]] = max(max_time[product_ids[i]], order.date)

    product_result = await db.execute(select(Product))
    products = product_result.scalars().all()

    product_data = []
    for product in products:
        if product.weight < 250 and product.volumetric_weight < 250:
            type = 1
        elif product.battery:
            type = 2
        else:
            type = 3
        
        if type != shipment_type and shipment_type != 0:
            continue
        stock = product.stock
        product_id = product.id
        ean = product.ean

        imports_datas = await get_imports(ean, db)
        imports = sum(imports_data.get("quantity") for imports_data in imports_datas)

        if product_id not in cnt:
            stock_days = -1
        else:
            days = (max_time[product_id] - min_time[product_id]).days + 1
            ave_sales = cnt[product_id] / days
            stock_days = int(stock / ave_sales) if ave_sales > 0 else -1
            stock_imports_days = int(((stock + imports) / ave_sales))

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
                "wechat": product.supplier_id,
                "stock_imports": [product.stock, ave_sales, imports],
                "day_stock": [stock_days, stock_imports_days],
                "imports_data": imports_datas
            })
    return product_data

@router.get('/product/advance')
async def get_product_advanced_info(
    db: AsyncSession = Depends(get_db),
    shipment_type: int = Query(None),
    weight_min: Decimal = Query(None),
    weight_max: Decimal = Query(None),
    volumetric_weight_min: Decimal = Query(None),
    volumetric_weight_max: Decimal = Query(None)
):
    query_ship = select(Shipment)

    if shipment_type is not None:
        query_ship = query_ship.where(Shipment.type == shipment_type)
    
    shipments_result = await db.execute(query_ship)
    shipments = shipments_result.scalars().all()

    product_type_list = []
    unique_names = set()

    for shipment in shipments:
        name_list = shipment.name
        for name in name_list:
            if name not in unique_names:
                product_type_list.append(name)
                unique_names.add(name)

    query = select(Product)
    if weight_min is not None:
        query = query.where(Product.weight >= weight_min)
    
    if weight_max is not None:
        query = query.where(Product.weight <= weight_max)
    
    if volumetric_weight_min is not None:
        query = query.where(Product.volumetric_weight >= volumetric_weight_min)
    
    if volumetric_weight_max is not None:
        query = query.where(Product.volumetric_weight <= volumetric_weight_max)
    
    if shipment_type is not None:
        query = query.where(Product.product_name in product_type_list)

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

# @router.get('/count')
# async def get_count():
#     count = count_all_products(MARKETPLACE_API_URL, PRODUCTS_ENDPOINT, COUNT_ENGPOINT, API_KEY, PUBLIC_KEY=None, usePublicKey=False, PROXIES=None)
#     return

@router.get('/shipment')
async def  get_shipment_info(
    db: AsyncSession = Depends(get_db),
    type_str: str = Query(None),
    status_str: str = Query(None)
):
    if type_str:
        type = [str(id.strip()) for id in type_str.split(",")]
    else:
        type = []

    if status_str:
        status = [str(id.strip()) for id in status_str.split(",")]
    else:
        status = []

    query = select(Shipment).where(Shipment.type.in_(type))
    query = query.where(status == any_(Shipment.status))

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

@router.post('/shipment')
async def create_shipment(shipment: ShipmentCreate, db: AsyncSession = Depends(get_db)):
    db_shipment = Shipment(**shipment.dict())
    db.add(db_shipment)
    await db.commit()
    await db.refresh(db_shipment)
    return db_shipment

@router.put("/shipment", response_model=ShipmentRead)
async def update_shipment(shipment_id: int, shipment: ShipmentUpdate, db: AsyncSession = Depends(get_db)):
    db_shipment = await db.execute(select(Shipment).filter(Shipment.id == shipment_id)).scalars().first()
    if db_shipment is None:
        raise HTTPException(status_code=404, detail="shipment not found")
    for var, value in vars(shipment).items():
        setattr(db_shipment, var, value) if value else None
    await db.commit()
    await db.refresh(db_shipment)
    return db_shipment
