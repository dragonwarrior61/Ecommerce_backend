from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, literal, any_, and_
from typing import List
from sqlalchemy.orm import aliased
from app.database import get_db
from app.models.orders import Order
from app.models.product import Product
from app.models.returns import Returns
from app.models.customer import Customers
from app.models.internal_product import Internal_Product
from app.schemas.internal_product import Internal_ProductCreate, Internal_ProductRead, Internal_ProductUpdate
from app.models.shipment import Shipment
from sqlalchemy import cast, String
from app.models.marketplace import Marketplace
import json

import datetime
import base64
import calendar

def get_valid_date(year, month, day):
    # Find the last day of the month
    last_day_of_month = calendar.monthrange(year, month)[1]
    # Set the day to the last day of the month if necessary
    day = min(day, last_day_of_month)
    return datetime.date(year, month, day)

router = APIRouter()

@router.post("/", response_model=Internal_ProductRead)
async def create_product(product: Internal_ProductCreate, db: AsyncSession = Depends(get_db)):
    db_product = Internal_Product(**product.dict())
    db.add(db_product)
    await db.commit()
    await db.refresh(db_product)
    return db_product

@router.get('/count')
async def get_products_count(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Internal_Product))
    count = result.scalars().all()
    return len(count)

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

@router.get("/{product_id}", response_model=Internal_ProductRead)
async def read_product(product_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Internal_Product).filter(Internal_Product.id == product_id))
    product = result.scalars().first()
    if product is None:
        raise HTTPException(status_code=404, detail="Internal_Product not found")
    return product

@router.get("/info/{ean}")
async def get_info(
    ean: str,
    type: int,
    db: AsyncSession = Depends(get_db)
):
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

        query = select(Order).where(Order.date >= st_datetime, Order.date <= en_datetime, Order.order_market_place == marketplace)
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

async def get_orders_info(ean: str, db: AsyncSession):
    query = select(Product).where(Product.ean == ean)
    result = await db.execute(query)
    products = result.scalars().all()
    order_data = []

    for product in products:
        product_id = product.id

        result = await db.execute(select(Order).where(product_id == any_(Order.product_id)))
        orders = result.scalars().all()

        for order in orders:
            order_id = order.id
            product_list = order.product_id
            index = product_list.index(product_id)
            unit = order.quantity[index]
            order_date = order.date
            marketplace = order.order_market_place
            customer_id = order.customer_id
            customer_result = await db.execute(select(Customers).where(Customers.id == customer_id))
            customer = customer_result.scalars().first()
            customer_name = customer.name
            order_data.append(
                {
                    "order_id": order_id,
                    "order_date": order_date,
                    "customer_name": customer_name,
                    "quantity_orders": unit,
                    "order_status": order.status,
                    "marketplace": marketplace
                }
            )
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
            "shipment_date": shipment.date,
            "shipment_quantity": total_quantity,
            "supplier_name": shipment.supplier_name[index],
            "shipment_status": shipment.status,
            "shipment_product_quantity": quantity
        })

    return shipment_data

@router.get("/", response_model=List[Internal_ProductRead])
async def get_products(
    supplier_ids: str = Query(None),
    page: int = Query(1, ge=1, description="Page number"),
    items_per_page: int = Query(50, ge=1, le=1000, description="Number of items per page"),
    search_text: str = Query('', description="Text for searching"),
    db: AsyncSession = Depends(get_db)
):
    
    offset = (page - 1) * items_per_page
    query = select(Internal_Product)
    if supplier_ids:
        supplier_id_list = [int(id.strip()) for id  in supplier_ids.split(",")]
        query = query.filter(Internal_Product.supplier_id == any_(supplier_id_list))
        
    query = query.filter(
        (cast(Internal_Product.id, String).ilike(f"%{search_text}")) |
        (Internal_Product.product_name.ilike(f"%{search_text}%")) |
        (Internal_Product.model_name.ilike(f"%{search_text}%")) |
        (Internal_Product.ean.ilike(f"%{search_text}%"))).order_by(Internal_Product.id).offset(offset).limit(items_per_page)

    result = await db.execute(query)
    db_products = result.scalars().all()

    if db_products is None:
        raise HTTPException(status_code=404, detail="Internal_Product not found")
    return db_products

@router.put("/{product_id}", response_model=Internal_ProductRead)
async def update_product(product_id: int, product: Internal_ProductUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Internal_Product).filter(Internal_Product.id == product_id))
    db_product = result.scalars().first()

    if db_product is None:
        raise HTTPException(status_code=404, detail="Internal_Product not found")
    
    for var, value in vars(product).items():
        setattr(db_product, var, value) if value else None

    await db.commit()
    await db.refresh(db_product)
    return db_product

@router.delete("/{product_id}", response_model=Internal_ProductRead)
async def delete_product(product_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Internal_Product).filter(Internal_Product.id == product_id))
    product = result.scalars().first()
    if product is None:
        raise HTTPException(status_code=404, detail="Internal_Product not found")
    await db.delete(product)
    await db.commit()
    return product
