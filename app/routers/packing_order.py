import base64, logging, os
from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import aliased
from sqlalchemy import and_, any_, BigInteger, cast
from typing import List

from app.config import settings
from app.database import get_db
from app.models import (
    AWB,
    Internal_Product,
    Order,
    Packing_order,
    Product,
    User
)
from app.routers.auth import get_team_admin_user, get_current_user
from app.schemas.packing_order import Packing_orderCreate, Packing_orderRead

router = APIRouter()

class PictureData(BaseModel):
    data_url: str
    name: str

class EANPictureData(BaseModel):
    data_url: str
    name: str
    order_id: int

@router.post("/save_picture")
async def save_picture(payload: PictureData, user_id: int = Depends(get_team_admin_user)):
    try:
        if not payload.data_url.startswith("data:image/"):
            raise HTTPException(status_code=400, detail="Invalid data URL format")

        header, base64_data = payload.data_url.split(",", 1)
        image_data = base64.b64decode(base64_data)
        image_type = header.split(";")[0].split("/")[1]
        file_name = f"/var/www/html/pack_pictures/{payload.name}.{image_type}"

        with open(file_name, "wb") as f:
            f.write(image_data)

        return JSONResponse(content={"message": f"Image uploaded successfully as {file_name}"})

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error: {str(e)}")

@router.post("/save_ean_picture")
async def save_ean_picture(payload: EANPictureData, user_id: int = Depends(get_team_admin_user), db: AsyncSession = Depends(get_db)):
    try:
        if not payload.data_url.startswith("data:image/"):
            raise HTTPException(status_code=400, detail="Invalid data URL format")

        os.makedirs(f"/var/www/html/ean_pictures/{payload.order_id}", exist_ok=True)
        header, base64_data = payload.data_url.split(",", 1)
        image_data = base64.b64decode(base64_data)
        image_type = header.split(";")[0].split("/")[1]
        file_name = f"/var/www/html/ean_pictures/{payload.order_id}/{payload.name}.{image_type}"

        with open(file_name, "wb") as f:
            f.write(image_data)

        return JSONResponse(content={"message": f"Image uploaded successfully as {file_name}"})

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error: {str(e)}")

@router.post("/", response_model=Packing_orderRead)
async def create_packing_order(
    packing_order: Packing_orderCreate,
    user: User = Depends(get_current_user),
    user_id: int = Depends(get_team_admin_user),
    db: AsyncSession = Depends(get_db)
):
    order_id = packing_order.order_id

    result = await db.execute(select(Order).where(Order.id == order_id, Order.user_id == user_id))
    order = result.scalars().first()
    if order is None:
        raise HTTPException(401, f"Not found order{order_id}")

    result = await db.execute(select(Packing_order).where(Packing_order.order_id == order_id, Packing_order.user_id == user_id))
    db_packing_order = result.scalars().first()
    if db_packing_order is None:
        new_packing_order = Packing_order(**packing_order.model_dump())
        new_packing_order.staff_id = user.id
        new_packing_order.user_id = user_id
        new_packing_order.pack_status = 1
        order.packing_status = 1
        flag = 1
        product_ean = new_packing_order.product_ean
        quantity = new_packing_order.quantity
        order_quantity = new_packing_order.order_quantity
        for i in range(len(product_ean)):
            if quantity[i] != order_quantity[i]:
                flag = 0
                break
        if flag:
            new_packing_order.pack_status = 2
            order.packing_status = 2
        settings.update_flag = 1
        try:
            db.add(new_packing_order)
            await db.commit()
            await db.refresh(new_packing_order)
            await db.refresh(order)
        except Exception as e:
            db.rollback()
        finally:
            settings.update_flag = 0

        return new_packing_order

    for var, value in vars(packing_order).items():
        setattr(db_packing_order, var, value) if value is not None else None

    flag = 1
    product_ean = db_packing_order.product_ean
    quantity = db_packing_order.quantity
    order_quantity = db_packing_order.order_quantity
    for i in range(len(product_ean)):
        if quantity[i] != order_quantity[i]:
            flag = 0
            break
    if flag:
        db_packing_order.pack_status = 2
        order.packing_status = 2
    else:
        db_packing_order.pack_status = 1
        order.packing_status = 1

    settings.update_flag = 1
    try:
        await db.commit()
        await db.refresh(db_packing_order)
        await db.refresh(order)
    except Exception as e:
        db.rollback()
    finally:
        settings.update_flag = 0
    return db_packing_order

@router.get('/count')
async def get_packing_orders_count(user_id: int = Depends(get_team_admin_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Packing_order).where(Packing_order.user_id == user_id))
    db_packing_orders = result.scalars().all()
    return len(db_packing_orders)

@router.get("/", response_model=List[Packing_orderRead])
async def get_packing_orders(
    user_id: int = Depends(get_team_admin_user), 
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Packing_order).where(Packing_order.user_id == user_id))
    db_packing_orders = result.scalars().all()
    if db_packing_orders is None:
        raise HTTPException(status_code=404, detail="Packing_order not found")
    return db_packing_orders

@router.get("/not_packed")
async def get_not_packed_orders(
    items_per_page: int = Query(50, ge=1, le=100, description="Number of items per page"),
    page: int = Query(1, ge=1, description="page_number"),
    warehouse_id: int = Query(0, description="Warehouse ID"),
    user_id: int = Depends(get_team_admin_user),
    db: AsyncSession = Depends(get_db)
):
    Internal_productAlias = aliased(Internal_Product)
    ProductAlias = aliased(Product)
    AWBAlias = aliased(AWB)
    offset = (page - 1) * items_per_page
    query = select(Order).where(Order.packing_status != 2, Order.user_id == user_id)
    query = query.outerjoin(AWBAlias, and_(AWBAlias.order_id == Order.id, AWBAlias.number > 0, AWBAlias.user_id == Order.user_id))
    query = query.where(AWBAlias.awb_status == any_([1, 18, 23, 73, 74]))

    if warehouse_id > 0:
        query = query.outerjoin(
            ProductAlias,
            and_(
                ProductAlias.id == any_(Order.product_id),
                ProductAlias.product_marketplace == Order.order_market_place,
                ProductAlias.user_id == Order.user_id
            )
        )
        query = query.outerjoin(Internal_productAlias, Internal_productAlias.ean == ProductAlias.ean)
        query = query.where(Internal_productAlias.warehouse_id == warehouse_id)
        query = query.group_by(Order.id, Order.user_id)

    query = query.offset(offset).limit(items_per_page)
    result = await db.execute(query)
    db_orders = result.scalars().all()

    if db_orders is None:
        raise HTTPException(status_code=404, detail="There are not packed orders")

    order_ids = [order.id for order in db_orders]
    awb_query = select(AWB).where(cast(AWB.order_id, BigInteger) == any_(order_ids), AWB.number > 0, AWB.user_id == user_id)
    awb_result = await db.execute(awb_query)
    awbs = awb_result.scalars().all()
    awb_dict = defaultdict(list)

    for awb in awbs:
        awb_dict[awb.order_id].append(awb)

    orders_data = []

    for db_order in db_orders:
        ean = []
        marketplace = db_order.order_market_place
        product_list = db_order.product_id
        for product_id in product_list:
            result = await db.execute(select(Product).where(Product.id == product_id, Product.product_marketplace == marketplace, Product.user_id == user_id))
            db_product = result.scalars().first()
            if db_product is None:
                result = await db.execute(select(Product).where(Product.id == product_id, Product.user_id == user_id))
                db_product = result.scalars().first()
                if db_product is None:
                    logging.error(f"Failed to get product {product_id} of order {db_order.id}")
                    continue
            ean.append(db_product.ean)

        if awb_dict[db_order.id]:
            awb = awb_dict[db_order.id]
        else:
            awb = []
        orders_data.append({
            **{column.name: getattr(db_order, column.name) for column in Order.__table__.columns},
            "ean": ean,
            "awb": awb
        })

    return orders_data

@router.get("/count_not_packing")
async def count_not_packing(
    warehouse_id: int = Query(0, description="Warehouse ID"), 
    user_id: int = Depends(get_team_admin_user), 
    db: AsyncSession = Depends(get_db)
):
    Internal_productAlias = aliased(Internal_Product)
    ProductAlias = aliased(Product)
    AWBAlias = aliased(AWB)
    query = select(Order).where(Order.packing_status != 2, Order.user_id == user_id)
    query = query.outerjoin(AWBAlias, and_(AWBAlias.order_id == Order.id, AWBAlias.number > 0, AWBAlias.user_id == Order.user_id))
    query = query.where(AWBAlias.awb_status == any_([1, 18, 23, 73, 74]))

    if warehouse_id > 0:
        query = query.outerjoin(ProductAlias, and_(ProductAlias.id == any_(Order.product_id), ProductAlias.product_marketplace == Order.order_market_place, ProductAlias.user_id == Order.user_id))
        query = query.outerjoin(Internal_productAlias, Internal_productAlias.ean == ProductAlias.ean)
        query = query.where(Internal_productAlias.warehouse_id == warehouse_id)
        query = query.group_by(Order.id, Order.user_id)

    result = await db.execute(query)
    db_orders = result.scalars().all()

    return len(db_orders)

@router.delete("/{packing_order_id}", response_model=Packing_orderRead)
async def delete_packing_order(
    packing_order_id: int,
    user_id: int = Depends(get_team_admin_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Packing_order).filter(Packing_order.id == packing_order_id, Packing_order.user_id == user_id))
    packing_order = result.scalars().first()
    if packing_order is None:
        raise HTTPException(status_code=404, detail="Packing_order not found")

    settings.update_flag = 1
    try:
        await db.delete(packing_order)
        await db.commit()
    except Exception as e:
        logging.error(f"An error occured: {e}")
        db.rollback()
    finally:
        settings.update_flag = 0

    return packing_order
