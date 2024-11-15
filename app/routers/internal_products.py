from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, literal, any_, and_
from typing import List
from sqlalchemy.orm import aliased
from app.database import get_db
from app.routers.auth import get_current_user
from app.models.orders import Order
from app.models.user import User
from app.routers.auth import get_current_user
from app.models.product import Product
from app.models.damaged_good import Damaged_good
from app.models.returns import Returns
from app.models.awb import AWB
from app.models.shipment import Shipment
from app.models.internal_product import Internal_Product
from app.schemas.internal_product import Internal_ProductCreate, Internal_ProductRead, Internal_ProductUpdate
from app.models.shipment import Shipment
from app.models.team_member import Team_member
from sqlalchemy import cast, String
from app.models.marketplace import Marketplace
import json
from app.config import settings

import datetime
from datetime import timedelta

import base64
import calendar

def get_valid_date(year, month, day):
    # Find the last day of the month
    last_day_of_month = calendar.monthrange(year, month)[1]
    # Set the day to the last day of the month if necessary
    day = min(day, last_day_of_month)
    return datetime.date(year, month, day)

async def get_orders_info(ean: str, db: AsyncSession):
    query = select(Product).where(Product.ean == ean)
    result = await db.execute(query)
    products = result.scalars().all()
    product_id_list = []
    for product in products:
        product_id_list.append(product.id)
        
    product_id_list = list(set(product_id_list))
    
    result = await db.execute(select(Internal_Product).where(Internal_Product.ean == ean))
    internal_product = result.scalars().first()
    warehouse_id = internal_product.warehouse_id
    user_id = internal_product.user_id
    
    order_data = []

    for product_id in product_id_list:
        AWBAlias = aliased(AWB)
        query = select(Order, AWBAlias).where(product_id == any_(Order.product_id, Order.user_id == user_id))
        query = query.outerjoin(AWBAlias, and_(AWBAlias.order_id == Order.id, AWBAlias.number == warehouse_id, AWBAlias.user_id == user_id))
        
        order_awb = result.fetchall()

        for order, awb in order_awb:
            order_data.append({
                "order": order,
                "awb": awb
            })
    return order_data
    
async def get_refunded_info(ean: str, db: AsyncSession):
    query = select(Product).where(Product.ean == ean)
    result = await db.execute(query)
    products = result.scalars().all()

    total = 0
    num1 = 0
    num2 = 0
    num3 = 0
    num4 = 0
    num5 = 0

    for product in products:
        product_id = product.id

        query_total = select(Returns).where(product_id == any_(Returns.products))
        result_total = await db.execute(query_total)
        total += len(result_total.scalars().all())
        query1 = query_total.where(Returns.return_type == 1)
        result_1 = await db.execute(query1)
        num1 += len(result_1.scalars().all())
        query2 = query_total.where(Returns.return_type == 2)
        result_2 = await db.execute(query2)
        num2 += len(result_2.scalars().all())
        query3 = query_total.where(Returns.return_type == 3)
        result_3 = await db.execute(query3)
        num3 += len(result_3.scalars().all())
        query4 = query_total.where(Returns.return_type == 4)
        result_4 = await db.execute(query4)
        num4 += len(result_4.scalars().all())
        query5 = query_total.where(Returns.return_type == 5)
        resutl_5 = await db.execute(query5)
        num5 += len(resutl_5.scalars().all())

    return {
        "total": total,
        "type_1": num1,
        "type_2": num2,
        "type_3": num3,
        "type_4": num4,
        "type_5": num5
    }

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

router = APIRouter()

@router.post("/", response_model=Internal_ProductRead)
async def create_product(product: Internal_ProductCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.role == -1:
        raise HTTPException(status_code=401, detail="Authentication error")
    
    if user.role != 4:
        result = await db.execute(select(Team_member).where(Team_member.user == user.id))
        db_team = result.scalars().first()
        user_id = db_team.admin
    else:
        user_id = user.id
        
    db_product = Internal_Product(**product.dict())
    db_product.user_id = user_id
    
    settings.update_flag = 1
    try:
        db.add(db_product)
        await db.commit()
        await db.refresh(db_product)
    except Exception as e:
        db.rollback()
    finally:
        settings.update_flag = 0
    
    return db_product

@router.get('/count')
async def get_products_count(
    supplier_ids: str = Query(None),
    search_text: str = Query('', description="Text for searching"),
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
        
    query = select(Internal_Product)
    if supplier_ids:
        supplier_id_list = [int(id.strip()) for id in supplier_ids.split(",")]
        query = query.filter(Internal_Product.supplier_id == any_(supplier_id_list))
    
    query = query.filter(
        (cast(Internal_Product.id, String).ilike(f"%{search_text}%")) |
        (Internal_Product.product_name.ilike(f"%{search_text}%")) |
        (Internal_Product.model_name.ilike(f"%{search_text}%")) |
        (Internal_Product.ean.ilike(f"%{search_text}%"))).order_by(Internal_Product.id)
    query = query.where(Internal_Product.user_id == user_id)
    
    result = await db.execute(query)
    db_products = result.scalars().all()
    return len(db_products)

@router.get("/all_products")
async def get_all_products(
    db: AsyncSession = Depends(get_db)
):
    query = select(Internal_Product)
    result = await db.execute(query)
    db_products = result.scalars().all()

    if db_products is None:
        raise HTTPException(status_code=404, detail="Internal_Product not found")
    return db_products

@router.get("/{ean}", response_model=Internal_ProductRead)
async def read_product(ean: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.role == -1:
        raise HTTPException(status_code=401, detail="Authentication error")
    
    if user.role != 4:
        result = await db.execute(select(Team_member).where(Team_member.user == user.id))
        db_team = result.scalars().first()
        user_id = db_team.admin
    else:
        user_id = user.id
        
    result = await db.execute(select(Internal_Product).where(Internal_Product.ean == ean))
    product = result.scalars().first()
    if product is None:
        raise HTTPException(status_code=404, detail="Internal_Product not found")
    if product.user_id != user_id:
        raise HTTPException(status_code=404, detail="You can't see this product")
    return product

@router.get("/info/{ean}")
async def get_info(
    ean: str,
    type: int,
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
        
    result = await db.execute(select(Internal_Product).where(Internal_Product.ean == ean, Internal_Product.user_id == user_id))
    db_product = result.scalars().first()
    if db_product is None:
        raise HTTPException(status_code=404, detail="You can't see this product")
    sales_info = await get_sales_info(ean, type, db)
    orders_info = await get_orders_info(ean, db)
    returns_info = await get_refunded_info(ean, db)
    shipments_info = await get_shipment_info(ean, db)
    return {
        "sales_info": sales_info,
        "orders_info": orders_info,
        "returns_info": returns_info,
        "shipments_info": shipments_info
    }
    # orders_info = await get_orders_info(product_id, db)

async def get_sales_info(ean, type, db: AsyncSession):
    today = datetime.date.today()
    sales_info = []

    if type == 1:
        for i in range(13):
            month = today.month + i
            year = today.year - 1 if month <= 12 else today.year
            month = month if month <= 12 else month - 12
            date = get_valid_date(year, month, today.day)
            
            date_string = f"{date.strftime('%b')} {date.year}"
            st_date = datetime.date(date.year, date.month, 1)
            if date.month == 12:
                en_date = datetime.date(date.year, 12, 31)
            else:
                en_date = datetime.date(date.year, date.month + 1, 1) - datetime.timedelta(days = 1)

            st_datetime = datetime.datetime.combine(st_date, datetime.time.min)
            en_datetime = datetime.datetime.combine(en_date, datetime.time.max)
            
            sales_month_data = await get_date_info(ean, st_datetime, en_datetime, db)
            sales_info.append({"date_string": date_string, "sales": sales_month_data["sales"]})

    elif type == 2:
        week_num_en = today.isocalendar()[1]
        en_date = today
        st_date = today - datetime.timedelta(today.weekday())
        for i in range(14):
            if week_num_en - i > 0:
                week_string = f"week {week_num_en - i}"
            else:
                week_string = f"week {week_num_en + 52 - i}"
            st_datetime = datetime.datetime.combine(st_date, datetime.time.min)
            en_datetime = datetime.datetime.combine(en_date, datetime.time.max)

            sales_week_data = await get_date_info(ean, st_datetime, en_datetime, db)
            sales_info.append({"date_string": week_string, "sales": sales_week_data["sales"]})
            en_date = st_date - datetime.timedelta(days=1)
            st_date = st_date - datetime.timedelta(days=7)
    else:
        for i in range(30):
            date = today - datetime.timedelta(days=i)
            st_datetime = datetime.datetime.combine(date, datetime.time.min)
            en_datetime = datetime.datetime.combine(date, datetime.time.max)

            day_string = f"{date.day} {date.strftime('%b')} {date.year}"
            sales_day_info = await get_date_info(ean, st_datetime, en_datetime, db)
            sales_info.append({"date_string": day_string, "sales": sales_day_info["sales"]})

    return sales_info

async def get_date_info(ean: str, st_datetime, en_datetime, db: AsyncSession):

    query = select(Product).where(Product.ean == ean)
    result = await db.execute(query)
    products = result.scalars().all()
    units = 0

    for product in products:
        product_id = product.id
        marketplace = product.product_marketplace

        query = select(Order).where(Order.date >= st_datetime, Order.date <= en_datetime, Order.order_market_place == marketplace, Order.user_id == product.user_id)
        query = query.where(product_id == any_(Order.product_id))
        result = await db.execute(query)
        orders = result.scalars().all()
        for order in orders:
            product_list = order.product_id
            index = product_list.index(product_id)
            units += order.quantity[index]

    return {
        "sales": units
    }

async def get_shipment_info(ean: str, db: AsyncSession):
    result = await db.execute(select(Shipment).where(ean == any_(Shipment.ean)))
    shipments = result.scalars().all()

    shipment_data = []
    for shipment in shipments:
        index = shipment.ean.index(ean)
        total_quantity = sum(shipment.quantity)
        quantity = shipment.quantity[index]
        shipment_data.append({
            "shipment_id": shipment.id,
            "shipment_title": shipment.title,
            "shipment_date": shipment.create_date,
            "shipment_quantity": total_quantity,
            "supplier_name": shipment.wechat_group[index],
            "shipment_status": shipment.status,
            "shipment_product_quantity": quantity
        })

    return shipment_data

@router.get("/")
async def get_products(
    supplier_ids: str = Query(None),
    page: int = Query(1, ge=1, description="Page number"),
    items_per_page: int = Query(50, ge=1, le=1000, description="Number of items per page"),
    search_text: str = Query('', description="Text for searching"),
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
    
    # result = await db.execute(select(Internal_Product).where(Internal_Product.user_id == user_id))
    # db_internal_products = result.scalars().all()
    # for internal_product in db_internal_products:
    #     internal_product.orders_stock = 0
    
    # result = await db.execute(select(Order).where(Order.status == any_([1,2,3]), Order.user_id == user_id))
    # db_new_orders = result.scalars().all()
    
    # for order in db_new_orders:
    #     product_id_list = order.product_id
    #     quantity_list = order.quantity
    #     for i in range(len(product_id_list)):
    #         product_id = product_id_list[i]
    #         quantity = quantity_list[i]
    #         result = await db.execute(select(Product).where(Product.id == product_id, Product.user_id == user_id, Product.product_marketplace == order.order_market_place))
    #         db_product = result.scalars().first()
    #         if db_product is None:
    #             result = await db.execute(select(Product).where(Product.id == product_id, Product.user_id == user_id))
    #             db_product = result.scalars().first()
    #         ean = db_product.ean

    #         result = await db.execute(select(Internal_Product).where(Internal_Product.ean == ean))
    #         db_internal_product = result.scalars().first()
    #         db_internal_product.orders_stock = db_internal_product.orders_stock + quantity
    
    # await db.commit() 
    
    cnt = {}
    
    ProductAlias = aliased(Product)
    query = select(Order, ProductAlias).outerjoin(
        ProductAlias,
        and_(
            ProductAlias.id == any_(Order.product_id),
            ProductAlias.product_marketplace == Order.order_market_place,
            ProductAlias.user_id == Order.user_id
        )
    )
    query = query.where(Order.user_id == user_id)
    time = datetime.datetime.now()
    thirty_days_ago = time - timedelta(days=30)
    query1 = query.where(Order.date > thirty_days_ago)
    result = await db.execute(query1)
    orders_with_products = result.all()

    for order, product in orders_with_products:
        if product is None:
            continue
        product_ids = order.product_id
        quantities = order.quantity
        for i in range(len(product_ids)):
            if product.id == product_ids[i]:
                if product.ean not in cnt:
                    cnt[product.ean] = quantities[i]
                else:
                    cnt[product.ean] += quantities[i]
                    
    returns_cnt = {}
    ProductAlias = aliased(Product)
    query = select(Returns, ProductAlias).outerjoin(
        ProductAlias,
        and_(
            ProductAlias.id == any_(Returns.products),
            ProductAlias.product_marketplace == Returns.return_market_place,
            ProductAlias.user_id == Returns.user_id
        )
    )
    query = query.where(Returns.user_id == user_id)
    time = datetime.datetime.now()
    thirty_days_ago = time - timedelta(days=30)
    query1 = query.where(Returns.date > thirty_days_ago)
    result = await db.execute(query1)
    returns_with_products = result.all()

    for returns, product in returns_with_products:
        if product is None:
            continue
        product_ids = returns.products
        quantities = returns.quantity
        for i in range(len(product_ids)):
            if product.id == product_ids[i]:
                if product.ean not in returns_cnt:
                    returns_cnt[product.ean] = quantities[i]
                else:
                    returns_cnt[product.ean] += quantities[i]
    
    offset = (page - 1) * items_per_page
    query = select(Internal_Product)
    if supplier_ids:
        supplier_id_list = [int(id.strip()) for id  in supplier_ids.split(",")]
        query = query.filter(Internal_Product.supplier_id == any_(supplier_id_list))
    
    query = query.filter(
        (cast(Internal_Product.id, String).ilike(f"%{search_text}")) |
        (Internal_Product.product_name.ilike(f"%{search_text}%")) |
        (Internal_Product.model_name.ilike(f"%{search_text}%")) |
        (Internal_Product.ean.ilike(f"%{search_text}%"))).order_by(Internal_Product.id)
    query = query.where(Internal_Product.user_id == user_id, Internal_Product.ean != '').offset(offset).limit(items_per_page)
    result = await db.execute(query)
    db_products = result.scalars().all()

    if db_products is None:
        raise HTTPException(status_code=404, detail="Internal_Product not found")
    
    product_data = []
    for db_product in db_products:
        if db_product.ean is None:
            continue
        ean = db_product.ean
        if ean not in cnt:
            sales = 0
        else:
            sales = cnt[ean]
        if ean not in returns_cnt:
            refunds = 0
        else:
            refunds = returns_cnt[ean]
            
        imports_data = await get_imports(ean, db)
        damaged_good = await get_damaged(ean, db)
        product_data.append({
            **{column.name: getattr(db_product, column.name) for column in Internal_Product.__table__.columns},
            "sales": sales,
            "refunds": refunds,
            "imports_data": imports_data,
            "damaged_good": damaged_good
        })
    return product_data

async def get_damaged(ean: str, db: AsyncSession):
    query = select(Damaged_good).where(ean == any_(Damaged_good.product_ean))
    result = await db.execute(query)
    db_damageds = result.scalars().all()
    if db_damageds is None:
        return 0
    total = 0
    for db_damaged in db_damageds:
        for i in range(len(db_damaged.product_ean)):
            if db_damaged.product_ean[i] == ean:
                total += db_damaged.quantity[i]
                
    return total

@router.put("/{ean}", response_model=Internal_ProductRead)
async def update_product(ean: str, product: Internal_ProductUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.role == -1:
        raise HTTPException(status_code=401, detail="Authentication error")
    
    if user.role != 4:
        result = await db.execute(select(Team_member).where(Team_member.user == user.id))
        db_team = result.scalars().first()
        user_id = db_team.admin
    else:
        user_id = user.id
        
    result = await db.execute(select(Internal_Product).filter(Internal_Product.ean == ean, Internal_Product.user_id == user_id).with_for_update())
    db_product = result.scalars().first()

    if db_product is None:
        raise HTTPException(status_code=404, detail="Internal_Product not found")
    
    for var, value in vars(product).items():
        setattr(db_product, var, value) if value is not None else None

    settings.update_flag = 1
    try:
        await db.commit()
        await db.refresh(db_product)
    except Exception as e:
        db.rollback()
    finally:
        settings.update_flag = 0
    
    return db_product

@router.delete("/{ean}", response_model=Internal_ProductRead)
async def delete_product(ean: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.role == -1:
        raise HTTPException(status_code=401, detail="Authentication error")
    
    if user.role != 4:
        result = await db.execute(select(Team_member).where(Team_member.user == user.id))
        db_team = result.scalars().first()
        user_id = db_team.admin
    else:
        user_id = user.id
        
    result = await db.execute(select(Internal_Product).filter(Internal_Product.ean == ean, Internal_Product.user_id == user_id))
    product = result.scalars().first()
    if product is None:
        raise HTTPException(status_code=404, detail="Internal_Product not found")
    if product.market_place:
        raise HTTPException(status_code=500, detail="This product is in marketplaces")
    
    query = select(Shipment).where(ean == any_(Shipment.ean))
    result = await db.execute(query)
    shipment = result.scalars().all()
    if shipment:
        raise HTTPException(status_code=500, detail="This product is in shipment")
    
    settings.update_flag = 1
    try:
        await db.delete(product)
        await db.commit()
    except Exception as e:
        db.rollback()
    finally:
        settings.update_flag = 0
    return product
