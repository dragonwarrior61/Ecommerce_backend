from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, literal, any_, and_
from typing import List
from sqlalchemy.orm import aliased
from app.database import get_db
from app.models.user import User
from app.routers.auth import get_current_user
from app.models.orders import Order
from app.models.returns import Returns
from app.models.product import Product
from app.schemas.product import ProductCreate, ProductRead, ProductUpdate
from app.models.shipment import Shipment
import json

import datetime
import base64
import calendar
from app.config import settings


def get_valid_date(year, month, day):
    # Find the last day of the month
    last_day_of_month = calendar.monthrange(year, month)[1]
    # Set the day to the last day of the month if necessary
    day = min(day, last_day_of_month)
    return datetime.date(year, month, day)

router = APIRouter()

@router.post("/", response_model=ProductRead)
async def create_product(product: ProductCreate, db: AsyncSession = Depends(get_db)):
    db_product = Product(**product.dict())
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
async def get_products_count(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Product))
    count = result.scalars().all()
    return len(count)

@router.get("/products", response_model=List[ProductRead])
async def read_products(db:AsyncSession = Depends(get_db)):
    result = await db.execute(select(Product))
    db_products = result.scalars().all()
    return db_products

@router.get("/{product_id}")
async def read_product(product_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Product).filter(Product.id == product_id))
    product = result.scalars().all()
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
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
    product = result.scalars().first()
    product_id = product.id

    query = select(Order).where(Order.date >= st_datetime, Order.date <= en_datetime)
    query = query.where(product_id == any_(Order.product_id))
    result = await db.execute(query)
    orders = result.scalars().all()
    units = 0
    for order in orders:
        products = order.product_id
        index = products.index(product_id)
        units += order.quantity[index]
    return {
        "sales": units
    }

async def get_orders_info(ean: str, db: AsyncSession):
    query = select(Product).where(Product.ean == ean)
    result = await db.execute(query)
    product = result.scalars().first()
    product_id = product.id

    result = await db.execute(select(Order).where(product_id == any_(Order.product_id)))
    orders = result.scalars().all()

    order_data = []

    for order in orders:
        order_id = order.id
        order_date = order.date
        unit = sum(order.quantity)
        order_data.append(
            {
                "order_id": order_id,
                "order_date": order_date,
                "quantity_orders": unit,
                "order_status": order.status
            }
        )
    return order_data
    
async def get_refunded_info(ean: str, db: AsyncSession):
    query = select(Product).where(Product.ean == ean)
    result = await db.execute(query)
    product = result.scalars().first()
    product_id = product.id

    query_total = select(Returns).where(product_id == any_(Returns.products))
    result_total = await db.execute(query_total)
    total = len(result_total.scalars().all())
    query1 = query_total.where(Returns.return_type == 1)
    result_1 = await db.execute(query1)
    num1 = len(result_1.scalars().all())
    query2 = query_total.where(Returns.return_type == 2)
    result_2 = await db.execute(query2)
    num2 = len(result_2.scalars().all())
    query3 = query_total.where(Returns.return_type == 3)
    result_3 = await db.execute(query3)
    num3 = len(result_3.scalars().all())
    query4 = query_total.where(Returns.return_type == 4)
    result_4 = await db.execute(query4)
    num4 = len(result_4.scalars().all())
    query5 = query_total.where(Returns.return_type == 5)
    resutl_5 = await db.execute(query5)
    num5 = len(resutl_5.scalars().all())

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
            "shipment_date": shipment.create_date,
            "shipment_quantity": total_quantity,
            "supplier_name": shipment.supplier_name[index],
            "shipment_status": shipment.status,
            "shipment_product_quantity": quantity
        })

    return shipment_data

@router.get("/", response_model=List[ProductRead])
async def get_products(
    supplier_ids: str = Query(None),
    page: int = Query(1, ge=1, description="Page number"),
    items_per_page: int = Query(50, ge=1, le=1000, description="Number of items per page"),
    search_text: str = Query('', description="Text for searching"),
    db: AsyncSession = Depends(get_db)
):
    
    offset = (page - 1) * items_per_page
    if supplier_ids:
        supplier_id_list = [int(id.strip()) for id  in supplier_ids.split(",")]
        result = await db.execute(select(Product).filter(
            (Product.supplier_id == any_(supplier_id_list)) | 
            (Product.product_name.ilike(f"%{search_text}%")) |
            (Product.model_name.ilike(f"%{search_text}%")) |
            (Product.ean.ilike(f"%{search_text}%"))
        ).order_by(Product.id).offset(offset).limit(items_per_page))
    else:
        result = await db.execute(select(Product).filter(
            (Product.product_name.ilike(f"%{search_text}%")) |
            (Product.model_name.ilike(f"%{search_text}%")) |
            (Product.ean.ilike(f"%{search_text}%"))).order_by(Product.id).offset(offset).limit(items_per_page))
    db_products = result.scalars().all()
    if db_products is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return db_products

@router.put("/{product_id}", response_model=ProductRead)
async def update_product(product_id: int, product: ProductUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Product).filter(Product.id == product_id))
    db_product = result.scalars().first()

    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    
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

@router.delete("/{product_id}", response_model=ProductRead)
async def delete_product(product_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Product).filter(Product.id == product_id))
    product = result.scalars().first()
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    
    settings.update_flag = 1
    try:
        await db.delete(product)
        await db.commit()
    except Exception as e:
        db.rollback()
    finally:
        settings.update_flag = 0
    
    return product
