from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import aliased
from sqlalchemy import func, or_, cast, Integer, BigInteger, and_
from typing import List
from app.database import get_db
from app.models.awb import AWB
from app.models.replacement import Replacement
from app.schemas.awb import AWBCreate, AWBRead, AWBUpdate
from app.models.marketplace import Marketplace
from app.models.orders import Order
from app.models.product import Product
from app.models.warehouse import Warehouse
from app.models.internal_product import Internal_Product
from app.models.warehouse import Warehouse
from app.models.user import User
from app.models.team_member import Team_member
from app.routers.auth import get_current_user
from app.backup import export_to_csv
from app.utils.emag_awbs import *
from app.utils.altex_awb import save_altex_awb
from app.utils.sameday import tracking
from sqlalchemy import any_
import datetime
from app.config import settings

router = APIRouter()

@router.post("/manually")
async def create_awb_manually(awb: AWBCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.role == -1:
        raise HTTPException(status_code=401, detail="Authentication error")
    
    if user.role != 4:
        result = await db.execute(select(Team_member).where(Team_member.user == user.id))
        db_team = result.scalars().first()
        user_id = db_team.admin
    else:
        user_id = user.id
        
    db_awb = AWB(**awb.dict())
    
    awb_number = db_awb.awb_number
    number = db_awb.number
    result = await db.execute(select(AWB).where(AWB.awb_number == awb_number, AWB.number == number))
    awb = result.scalars().first()
    
    if awb:
        return awb
    db_awb.user_id = user_id
    
    settings.update_flag = 1
    
    try:
        db.add(db_awb)
        await db.commit()
        await db.refresh(db_awb)
    except Exception as e:
        await db.rollback()
    finally:
        settings.update_flag = 0
    
    return db_awb

@router.post("/")
async def create_awbs(awb: AWBCreate, marketplace: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.role == -1:
        raise HTTPException(status_code=401, detail="Authentication error")
    
    if user.role != 4:
        result = await db.execute(select(Team_member).where(Team_member.user == user.id))
        db_team = result.scalars().first()
        user_id = db_team.admin
    else:
        user_id = user.id
        
    db_awb = AWB(**awb.dict())
    order_id = db_awb.order_id
    number = db_awb.number
    result = await db.execute(select(AWB).where(AWB.order_id == order_id, AWB.number == number, AWB.user_id == user_id))
    awb = result.scalars().first()

    if awb:
        return awb

    db_awb.awb_marketplace = marketplace
    db_awb.user_id = user_id
    
    settings.update_flag = 1
    
    db.add(db_awb)
    
    try:
        await db.commit()
        await db.refresh(db_awb)
    except Exception as ex:
        await db.rollback()
    finally:
        settings.update_flag = 0
    
    result = await db.execute(select(Marketplace).where(Marketplace.marketplaceDomain == marketplace))
    market_place = result.scalars().first()
    
    try:
        if market_place.marketplaceDomain == "altex.ro":
            data = {
                "courier_id": db_awb.courier_account_id,
                "location_id": db_awb.receiver_locality_id,
                "sender_name": db_awb.sender_name,
                "sender_contact_person": None,
                "sender_phone": db_awb.sender_phone1,
                "sender_address": db_awb.sender_street,
                "sender_country": None,
                "sender_city": None,
                "sender_postalcode": db_awb.sender_zipcode,
                "destination_contact_person ": db_awb.receiver_contact,
                "destination_phone": db_awb.receiver_phone1,
                "destination_address": db_awb.receiver_street,
                "destination_county ": None,
                "destination_postalcode ": db_awb.receiver_zipcode,
            }

            result = await save_altex_awb(market_place, data, db_awb.order_id, db)
        else:
            data = {
                "order_id": db_awb.order_id,
                "sender": {
                    "name": db_awb.sender_name,
                    "phone1": db_awb.sender_phone1,
                    "phone2": db_awb.sender_phone2,
                    "locality_id": db_awb.sender_locality_id,
                    "street": db_awb.sender_street,
                    "zipcode": db_awb.sender_zipcode
                },
                "receiver": {
                    "name": db_awb.receiver_name,
                    "contact": db_awb.receiver_contact,
                    "phone1": db_awb.receiver_phone1,
                    "phone2": db_awb.receiver_phone1,
                    "legal_entity": db_awb.receiver_legal_entity,
                    "locality_id": db_awb.receiver_locality_id,
                    "street": db_awb.receiver_street,
                    "zipcode": db_awb.receiver_zipcode
                },
                "locker_id": db_awb.locker_id,
                "is_oversize": db_awb.is_oversize,
                "insured_value": db_awb.insured_value,
                "weight": db_awb.weight,
                "envelope_number": db_awb.envelope_number,
                "parcel_number": db_awb.parcel_number,
                "observation": db_awb.observation,
                "cod": db_awb.cod,
                "courier_account_id": db_awb.courier_account_id,
                "pickup_and_return": db_awb.pickup_and_return,
                "saturday_delivery": db_awb.saturday_delivery,
                "sameday_delivery": db_awb.sameday_delivery,
                "dropoff_locker": db_awb.dropoff_locker
            }

            result = await save_awb(market_place, data, db)
        if result.status_code != 200:
            return result.json()
        result = result.json()
        logging.info(f"AWB generation result is {result}")
        if result['isError'] == True:
            return result
        results = result['results']
        db_awb.reservation_id = results.get('reservation_id') if results.get('reservation_id') else 0
        db_awb.courier_id = results.get('courier_id') if results.get('courier_id') else 0
        db_awb.courier_name = results.get('courier_name') if results.get('courier_name') else ""
       
        if results.get('awb'):
            result_awb = results.get('awb')[0]
            db_awb.awb_number = result_awb.get('awb_number') if result_awb.get('awb_number') else ""
            db_awb.awb_barcode = result_awb.get('awb_barcode') if result_awb.get('awb_barcode') else ""
        
        db_replacement = None

        if db_awb.number < 0:
            result = await db.execute(select(Replacement).where(Replacement.order_id == db_awb.order_id, Replacement.number == -db_awb.number))
            db_replacement = result.scalars().first()
            if db_replacement:
                db_replacement.awb = db_awb.awb_number
        
        await db.commit()
        await db.refresh(db_awb)
        return db_awb
    except Exception as e:  # Roll back any changes made before the error
        logging.info(f"Error processing AWB: {str(e)}")
        
        settings.update_flag = 0
        return {"error": "Failed to process AWB", "message": str(e)}

@router.get("/backup")
async def get_awb_status():
    await export_to_csv()

@router.get("/count")
async def count_awb(
    status_str: str = Query('', description="awb_status"),
    warehouse_id: int = Query(0, description='warehouse_id'),
    flag: bool = Query(False, description="Generated today or not"),
    no_awb_number: bool = Query(False, description="No awb number"),
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
        
    warehouseAlias = aliased(Warehouse)
    query = select(AWB)
    
    if no_awb_number:
        query = query.where(AWB.awb_number.is_(None))
    if status_str:
        status_list = [int(status.strip()) for status in status_str.split(",")]
        query = query.where(AWB.awb_status == any_(status_list))
    query = query.outerjoin(
        warehouseAlias,
        warehouseAlias.street == AWB.sender_street
    )
    if flag == False:
        yesterday = datetime.datetime.today() - datetime.timedelta(days=1)
        query = query.where(AWB.awb_date <= datetime.datetime(yesterday.year, yesterday.month, yesterday.day, 23, 59, 59))
    if warehouse_id:
        query = query.where(warehouseAlias.id == warehouse_id)
    query = query.where(AWB.user_id == user_id)
    result = await db.execute(query)
    db_awb = result.scalars().all()
    return len(db_awb)

@router.get("/count/not_shipped")
async def count_awb_not_shipped(
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
        
    status_list = [1, 18, 23, 73, 74]
    query = select(func.count(AWB.awb_number)).where(AWB.awb_status == any_(status_list))
    yesterday = datetime.datetime.today() - datetime.timedelta(days=1)
    query = query.where(AWB.awb_date <= datetime.datetime(yesterday.year, yesterday.month, yesterday.day, 23, 59, 59))
    query = query.where(AWB.user_id == user_id)
    result = await db.execute(query)
    count = result.scalar()

    return count

@router.get("/order_id")
async def get_awbs_order_id(
    order_id: int,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(AWB).where(AWB.order_id == order_id))
    db_awbs = result.scalars().all()
    return db_awbs

@router.get("/awb_barcode")
async def get_order(
    awb_number: str,
    db: AsyncSession = Depends(get_db)
):

    if awb_number[:2] == "01":
        result = await db.execute(select(AWB).where(or_(AWB.awb_number == awb_number[2:], AWB.awb_number == awb_number[2:-3], AWB.awb_number == awb_number, AWB.awb_number == awb_number[:-3])))
    else:
        result = await db.execute(select(AWB).where(or_(AWB.awb_number == awb_number, AWB.awb_number == awb_number[:-3])))
    db_awb = result.scalars().first()
    if db_awb is None:
        raise HTTPException(status_code=404, detail="awb not found")
    order_id = db_awb.order_id
    result = await db.execute(select(Order).where(Order.id == order_id))
    db_order = result.scalars().first()
    if db_order is None:
        return HTTPException(status_code=404, detail=f"{order_id} not found")
    product_ids = db_order.product_id
    marketplace = db_order.order_market_place
    ean = []
    for product_id in product_ids:
        result = await db.execute(select(Product).where(Product.id == product_id, Product.product_marketplace == marketplace, Product.user_id == db_order.user_id))
        product = result.scalars().first()
        if product is None:
            result = await db.execute(select(Product).where(Product.id == product_id))
            product = result.scalars().first()
        ean.append(product.ean)

    return {
        **{column.name: getattr(db_order, column.name) for column in Order.__table__.columns},
        "ean": ean
    }

@router.get("/")
async def get_awbs(
    page: int = Query(1, ge=1, description="Page number"),
    items_per_page: int = Query(50, ge=1, le=100, description="Number of items per page"),
    status_str: str = Query('', description="awb_status"),
    warehouse_id: int = Query(0, description="warehouse_id"),
    flag: bool = Query(False, description="Generated today or not"),
    no_awb_number: bool = Query(False, description="No AWB number"),
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
        
    warehousealiased = aliased(Warehouse)
    orderaliased = aliased(Order)
    offset = (page - 1) * items_per_page
    query = select(AWB, warehousealiased, orderaliased)
    
    if no_awb_number:
        query = query.where(AWB.awb_number.is_(None))
    if status_str:
        status_list = [int(status.strip()) for status in status_str.split(",")]
        query = query.where(AWB.awb_status == any_(status_list))

    query = query.outerjoin(
        warehousealiased,
        warehousealiased.street == AWB.sender_street
    )

    query = query.outerjoin(
        orderaliased,
        orderaliased.id == cast(AWB.order_id, BigInteger)
    ).order_by(orderaliased.maximum_date_for_shipment.desc())

    if flag == False:
        yesterday = datetime.datetime.today() - datetime.timedelta(days=1)
        query = query.where(AWB.awb_date <= datetime.datetime(yesterday.year, yesterday.month, yesterday.day, 23, 59, 59))
        
    if warehouse_id:
        query = query.where(warehousealiased.id == warehouse_id)
    
    query = query.where(AWB.user_id == user_id)
    query = query.offset(offset).limit(items_per_page)
    result = await db.execute(query)
    db_awbs = result.all()
    if db_awbs is None:
        raise HTTPException(status_code=404, detail="awbs not found")
    
    awb_data = []
    for db_awb, warehouse, order in db_awbs:
        awb_info = {column.name: getattr(db_awb, column.name) for column in AWB.__table__.columns}
        warehouse_info = {column.name: getattr(warehouse, column.name) if warehouse else None for column in Warehouse.__table__.columns}
        
        awb_info.update(warehouse_info)
        awb_info["order"] = order
        if db_awb.number < 0:
            result = await db.execute(select(Replacement).where(Replacement.order_id == db_awb.order_id, Replacement.number == -db_awb.number))
            replacement = result.scalars().first()
            awb_info["replacement"] = replacement
        else:
            awb_info["replacement"] = ""
        awb_data.append(awb_info)
    return awb_data

@router.put("/", response_model=AWBRead)
async def update_awbs(
    order_id: int,
    number: int,
    awb_number: str,
    reservation_id: int,
    courier_id: int,
    courier_name: str,
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
        
    result = await db.execute(select(AWB).filter(AWB.order_id == order_id, AWB.number == number))
    db_awb = result.scalars().first()
    if db_awb is None:
        raise HTTPException(status_code=404, detail="awbs not found")
    if db_awb.user_id != user_id:
        raise HTTPException(status_code=401, detail="Authentication error")
    if db_awb.awb_number:
        raise HTTPException(status_code=429, detail="This awb is created successfully. You can't edit this awb")
    
    db_awb.awb_number = awb_number
    db_awb.awb_barcode = awb_number + '001'
    db_awb.reservation_id = reservation_id
    db_awb.courier_id = courier_id
    db_awb.courier_name = courier_name
    settings.update_flag = 1
    try:
        await db.commit()
        await db.refresh(db_awb)
    except Exception as e:
        await db.rollback()
    finally:
        settings.update_flag = 0
    return db_awb

@router.delete("/", response_model=AWBRead)
async def delete_awbs(order_id: int, number: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.role == -1:
        raise HTTPException(status_code=401, detail="Authentication error")
    
    if user.role != 4:
        result = await db.execute(select(Team_member).where(Team_member.user == user.id))
        db_team = result.scalars().first()
        user_id = db_team.admin
    else:
        user_id = user.id
        
    result = await db.execute(select(AWB).filter(AWB.order_id == order_id, AWB.number == number, AWB.user_id == user_id))
    awb = result.scalars().first()
    if awb is None:
        raise HTTPException(status_code=404, detail="awbs not found")
    
    settings.update_flag = 1
    try:
        await db.delete(awb)
        await db.commit()
    except Exception as e:
        db.rollback()
    finally:
        settings.update_flag = 0
    return awb
