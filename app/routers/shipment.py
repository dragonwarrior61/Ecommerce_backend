from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import aliased
from sqlalchemy import func
from sqlalchemy import any_, text
from typing import List
from app.models.user import User
from app.routers.auth import get_current_user
from app.database import get_db
from app.models.shipment import Shipment
from app.models.supplier import Supplier
from app.models.internal_product import Internal_Product
from app.models.team_member import Team_member
from app.schemas.shipment import ShipmentCreate, ShipmentRead, ShipmentUpdate
import logging
import json
from datetime import datetime
import time
import math
from app.config import settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

router = APIRouter()

@router.post("/", response_model=ShipmentRead)
async def create_shipment(shipment: ShipmentCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.role == -1:
        raise HTTPException(status_code=401, detail="Authentication error")
    
    if user.role != 4:
        result = await db.execute(select(Team_member).where(Team_member.user == user.id))
        db_team = result.scalars().first()
        user_id = db_team.admin
    else:
        user_id = user.id
    db_shipment = Shipment(**shipment.dict())
    db_shipment.user_id = user_id
    
    settings.update_flag = 1
    try:
        db.add(db_shipment)
        await db.commit()
        await db.refresh(db_shipment)
    except Exception as e:
        db.rollback()
    finally:
        settings.update_flag = 0
    
    return db_shipment

@router.get('/count')
async def get_shipments_count(
    type: str = Query('', description="Shipping type"),
    status: str = Query('', description="Shipping status"),
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
    
    query = select(Shipment).where(Shipment.user_id == user_id)
    if type:
        query = query.where(Shipment.type == type)
    if status:
        query = query.where(Shipment.status == status)
    result = await db.execute(query)
    db_shipments = result.scalars().all()
    return len(db_shipments)

@router.get("/new_count")
async def get_new_shipments(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.role == -1:
        raise HTTPException(status_code=401, detail="Authentication error")
    
    if user.role != 4:
        result = await db.execute(select(Team_member).where(Team_member.user == user.id))
        db_team = result.scalars().first()
        user_id = db_team.admin
    else:
        user_id = user.id
    result = await db.execute(select(Shipment).where(Shipment.status == "New", Shipment.user_id == user_id))
    db_new_shipments = result.scalars().all()
    return len(db_new_shipments)

@router.get("/agent")
async def get_shipments_agent(
    agent: str,
    db:AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Shipment).where(Shipment.agent == agent))
    db_shipments = result.scalars().all()
    if db_shipments is None:
        raise HTTPException(status_code=404, detail="shipment not found")
    return db_shipments

@router.get("/admin_supplier")
async def get_admin_supplier(
    supplier_id: int,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Supplier).where(Supplier.id == supplier_id))
    db_supplier = result.scalars().first()
    if db_supplier is None:
        raise HTTPException(status_code=404, detail="Supplier not found")
    user_id = db_supplier.user_id
    
    result = await db.execute(select(Supplier).where(Supplier.user_id == user_id))
    db_suppliers = result.scalars().all()
    if db_suppliers is None:
        raise HTTPException(status_code=404, detail="Suppliers not found")
    return db_suppliers

@router.get("/supplier")
async def get_shipments_supplier(
    supplier_id: int,
    db: AsyncSession = Depends(get_db)
):
    internal_productaliased = aliased(Internal_Product)
    query = select(Shipment).where(Shipment.status == any_(["New", "Pending"]))
    query = query.outerjoin(
        internal_productaliased,
        internal_productaliased.ean == any_(Shipment.ean)
    ).where(internal_productaliased.supplier_id == supplier_id).group_by(Shipment.id)
    result = await db.execute(query)
    db_shipments = result.scalars().all()
    if db_shipments is None:
        raise HTTPException(status_code=404, detail="shipment not found")
    return db_shipments

@router.get("/", response_model=List[ShipmentRead])
async def get_shipments(
    page: int = Query(1, ge=1, description="Page number"),
    items_per_page: int = Query(50, ge=1, le=100, description="Number of items per page"),
    type: str = Query('', description="Shipping type"),
    status: str = Query('', description="Shipping status"),
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
    offset = (page - 1) * items_per_page
    query = select(Shipment).where(Shipment.user_id == user_id)
    if type:
        query = query.where(Shipment.type == type)
    if status:
        query = query.where(Shipment.status == status)
    result = await db.execute(query.offset(offset).limit(items_per_page))
    db_shipments = result.scalars().all()
    if db_shipments is None:
        raise HTTPException(status_code=404, detail="shipment not found")
    return db_shipments

@router.get("/new", response_model=List[ShipmentRead])
async def get_new_shipments(
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
    result = await db.execute(select(Shipment).where(Shipment.status == any_(["New", "Pending"]), Shipment.user_id == user_id))
    db_new_shipments = result.scalars().all()
    if db_new_shipments is None:
        raise HTTPException(status_code=400, detail="New shipment not found")
    return db_new_shipments

@router.get("/extra") 
async def get_extra_info(
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
    query = text("""
        SELECT id, title 
        FROM shipments
        WHERE status = 'New' and user_id = :user_id
    """)
    
    result = await db.execute(query, {"user_id": user_id})
    extra_info = result.fetchall()
    
    extra_info_list = [{"id": row[0], "title": row[1]} for row in extra_info]
    return extra_info_list

@router.get("/move", response_model=ShipmentRead)
async def move_products(shipment_id1: int, shipment_id2: int, ean: str, ship_id: str, user: User = Depends(get_current_user), db:AsyncSession = Depends(get_db)):
    if user.role == -1:
        raise HTTPException(status_code=401, detail="Authentication error")
    
    if user.role != 4:
        result = await db.execute(select(Team_member).where(Team_member.user == user.id))
        db_team = result.scalars().first()
        user_id = db_team.admin
    else:
        user_id = user.id
        
    result = await db.execute(select(Shipment).where(Shipment.id == shipment_id1))
    shipment_1 = result.scalars().first()

    result = await db.execute(select(Shipment).where(Shipment.id == shipment_id2))
    shipment_2 = result.scalars().first()
    
    if shipment_1.user_id != user_id or shipment_2.user_id != user_id:
        raise HTTPException(status_code=401, detail="Authentication error")
    ean_list = shipment_1.ean

    for i in range(len(ean_list)):
        if ean_list[i] == ean and shipment_1.ship_id[i] == ship_id:
            index = i
            break
    quantity = shipment_1.quantity[index]
    item_per_box = shipment_1.item_per_box[index]
    pdf_sent = shipment_1.pdf_sent[index]
    pay_url = shipment_1.pay_url[index]
    tracking = shipment_1.tracking[index]
    inland_cost = shipment_1.inland_cost[index]
    arrive_agent = shipment_1.arrive_agent[index]
    wechat_group = shipment_1.wechat_group[index]
    pp = shipment_1.pp[index]
    each_status = shipment_1.each_status[index]
    box_number = shipment_1.box_number[index]
    document = shipment_1.document[index]
    date_added = shipment_1.date_added[index]
    date_agent = shipment_1.date_agent[index]
    ship_id = shipment_1.ship_id[index]
    before = shipment_1.before[index]
    if before:
        before = before.replace("'", '"')
        before = json.loads(before)
        before = before + [f"{ship_id}_{shipment_1.title}"]
        before = str(before)
    else:
        before = str([f"{ship_id}_{shipment_1.title}"])
    user = shipment_1.user[index]
    other_cost = shipment_1.other_cost[index]
    received = shipment_1.received[index]
    price = shipment_1.price[index]
    each_note = shipment_1.each_note[index]
    
    shipment_1.ean = shipment_1.ean[:index] + shipment_1.ean[index+1:]
    shipment_1.quantity = shipment_1.quantity[:index] + shipment_1.quantity[index+1:]
    shipment_1.item_per_box = shipment_1.item_per_box[:index] + shipment_1.item_per_box[index+1:]
    shipment_1.pdf_sent = shipment_1.pdf_sent[:index] + shipment_1.pdf_sent[index+1:]
    shipment_1.pay_url = shipment_1.pay_url[:index] + shipment_1.pay_url[index+1:]
    shipment_1.tracking = shipment_1.tracking[:index] + shipment_1.tracking[index+1:]
    shipment_1.inland_cost = shipment_1.inland_cost[:index] + shipment_1.inland_cost[index+1:]
    shipment_1.arrive_agent = shipment_1.arrive_agent[:index] + shipment_1.arrive_agent[index+1:]
    shipment_1.wechat_group = shipment_1.wechat_group[:index] + shipment_1.wechat_group[index+1:]
    shipment_1.pp = shipment_1.pp[:index] + shipment_1.pp[index+1:]
    shipment_1.each_status = shipment_1.each_status[:index] + shipment_1.each_status[index+1:]
    shipment_1.box_number = shipment_1.box_number[:index] + shipment_1.box_number[index+1:]
    shipment_1.document = shipment_1.document[:index] + shipment_1.document[index+1:]
    shipment_1.date_added = shipment_1.date_added[:index] + shipment_1.date_added[index+1:]
    shipment_1.date_agent = shipment_1.date_agent[:index] + shipment_1.date_agent[index+1:]
    shipment_1.ship_id = shipment_1.ship_id[:index] + shipment_1.ship_id[index+1:]
    shipment_1.before = shipment_1.before[:index] + shipment_1.before[index+1:]
    shipment_1.user = shipment_1.user[:index] + shipment_1.user[index+1:]
    shipment_1.other_cost = shipment_1.other_cost[:index] + shipment_1.other_cost[index+1:]
    shipment_1.received = shipment_1.received[:index] + shipment_1.received[index+1:]
    shipment_1.price = shipment_1.price[:index] + shipment_1.price[index+1:]
    shipment_1.each_note = shipment_1.each_note[:index] + shipment_1.each_note[index+1:]
    
    # await db.refresh(shipment_1)

    shipment_2.ean = shipment_2.ean + [ean]
    shipment_2.quantity = shipment_2.quantity + [quantity]
    shipment_2.item_per_box = shipment_2.item_per_box + [item_per_box]
    shipment_2.pdf_sent = shipment_2.pdf_sent + [pdf_sent]
    shipment_2.pay_url = shipment_2.pay_url + [pay_url]
    shipment_2.tracking = shipment_2.tracking + [tracking]
    shipment_2.inland_cost = shipment_2.inland_cost + [inland_cost]
    shipment_2.arrive_agent = shipment_2.arrive_agent + [arrive_agent]
    shipment_2.wechat_group = shipment_2.wechat_group + [wechat_group]
    shipment_2.pp = shipment_2.pp + [pp]
    shipment_2.each_status = shipment_2.each_status + [each_status]
    shipment_2.box_number = shipment_2.box_number + [box_number]
    shipment_2.document = shipment_2.document + [document]
    shipment_2.date_added = shipment_2.date_added + [date_added]
    shipment_2.date_agent = shipment_2.date_agent + [date_agent]
    shipment_2.ship_id = shipment_2.ship_id + [ship_id]
    shipment_2.before = shipment_2.before + [before]
    shipment_2.user = shipment_2.user + [user]
    shipment_2.other_cost = shipment_2.other_cost + [other_cost]
    shipment_2.received = shipment_2.received + [received]
    shipment_2.price = shipment_2.price + [price]
    shipment_2.each_note = shipment_2.each_note + [each_note]

    settings.update_flag = 1
    try:
        await db.commit()
        await db.refresh(shipment_1)
    except Exception as e:
        db.rollback()
    finally:
        settings.update_flag = 0
    logging.info(f"@@@@@After update: {shipment_1}")
    settings.update_flag = 0
    
    return shipment_1

@router.get("/product_info")
async def get_info(ean: str, item_per_box: int, user: User = Depends(get_current_user), db:AsyncSession = Depends(get_db)):
    if user.role == -1:
        raise HTTPException(status_code=401, detail="Authentication error")
    
    if user.role != 4:
        result = await db.execute(select(Team_member).where(Team_member.user == user.id))
        db_team = result.scalars().first()
        user_id = db_team.admin
    else:
        user_id = user.id
    query = select(Shipment).where(ean == any_(Shipment.ean), Shipment.user_id == user_id)
    result = await db.execute(query)

    shipments = result.scalars().all()

    imports_data = []

    for shipment in shipments:
        if shipment.status == "arrived":
            continue
        ean_list = shipment.ean
        quantity_list = shipment.quantity
        title = shipment.title
        index = ean_list.index(ean)
        quantity = quantity_list[index]

        imports_data.append({
            "title": title,
            "quantity": quantity
        })

    result = await db.execute(select(Internal_Product).where(Internal_Product.ean == ean))
    product = result.scalars().first()
 
    dimension = product.dimensions
    if dimension:
        numbers = dimension.split('*')
        # Ensure all parts are valid before conversion
        if len(numbers) == 3 and all(num.strip() for num in numbers):
            w, h, d = map(float, numbers)
        else:
            w, h, d = (0.0, 0.0, 0.0)
    else:
        w, h, d = (0.0, 0.0, 0.0)
    if item_per_box:
        volumetric_weight = w * h * d / 5000 / item_per_box
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

        return {
            "type": type,
            "imports_data": imports_data
        }
    else:
        return {
            "type": 1,
            "imports_data": imports_data
        }
        
@router.get("/add product")
async def add_product_in_shipment(ean: str, qty: int, ship_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.role == -1:
        raise HTTPException(status_code=401, detail="Authentication error")
    
    if user.role != 4:
        result = await db.execute(select(Team_member).where(Team_member.user == user.id))
        db_team = result.scalars().first()
        user_id = db_team.admin
    else:
        user_id = user.id
        
    result = await db.execute(select(Shipment).where(Shipment.id == ship_id, Shipment.user_id == user_id))
    db_shipment = result.scalars().first()
    
    result = await db.execute(select(Internal_Product).where(Internal_Product.ean == ean, Internal_Product.user_id == user_id))
    db_product = result.scalars().first()
    pcs_ctn = db_product.pcs_ctn
    supplier = db_product.supplier_id
    price = db_product.price
    
    if db_product.link_address_1688:
        pp = "agent"
    else:
        pp = ""
    if db_shipment is None:
        raise HTTPException(status_code=404, detail="Shipment not found")
    
    cnt = db_shipment.cnt + 1
    db_shipment.ean = db_shipment.ean + [ean]
    db_shipment.quantity = db_shipment.quantity + [qty]
    db_shipment.item_per_box = db_shipment.item_per_box + [int(pcs_ctn)]
    db_shipment.pdf_sent = db_shipment.pdf_sent + [False]
    db_shipment.pay_url = db_shipment.pay_url + [""]
    db_shipment.tracking = db_shipment.tracking + [""]
    db_shipment.inland_cost = db_shipment.inland_cost + [0.0]
    db_shipment.arrive_agent = db_shipment.arrive_agent + [False]
    db_shipment.wechat_group = db_shipment.wechat_group + [str(supplier)]
    db_shipment.pp = db_shipment.pp + [pp]
    db_shipment.each_status = db_shipment.each_status + [""]
    db_shipment.box_number = db_shipment.box_number + [math.ceil(qty / int(pcs_ctn))]
    db_shipment.document = db_shipment.document + [""]
    db_shipment.date_added = db_shipment.date_added + [datetime.now()]
    db_shipment.date_agent = db_shipment.date_agent + [datetime.now()]
    db_shipment.ship_id = db_shipment.ship_id + [f"{user.id}-{int(time.time() * 1000)}-{cnt}"]
    db_shipment.before = db_shipment.before + [""]
    db_shipment.user = db_shipment.user + [user.id]
    db_shipment.cnt = cnt
    db_shipment.other_cost = db_shipment.other_cost + [0.0]
    db_shipment.received = db_shipment.received + [0]
    db_shipment.price = db_shipment.price + [price]
    db_shipment.each_note = db_shipment.each_note + [""]
    db_shipment.updated_at = datetime.now()

    settings.update_flag = 1
    try:
        await db.commit()
        await db.refresh(db_shipment)
    except Exception as e:
        db.rollback()
    finally:
        settings.update_flag = 0
    
    return db_shipment

@router.get("/{shipment_id}")
async def get_shipment(shipment_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.role == -1:
        raise HTTPException(status_code=401, detail="Authentication error")
    
    if user.role != 4:
        result = await db.execute(select(Team_member).where(Team_member.user == user.id))
        db_team = result.scalars().first()
        user_id = db_team.admin
    else:
        user_id = user.id
    result = await db.execute(select(Shipment).where(Shipment.id == shipment_id, Shipment.user_id == user_id))
    db_shipment = result.scalars().first()
    if db_shipment is None:
        raise HTTPException(status_code=404, detail="shipment not found")
    return db_shipment

@router.put("/{shipment_id}", response_model=ShipmentRead)
async def update_shipment(shipment_id: int, shipment: ShipmentUpdate, db: AsyncSession = Depends(get_db)):
    # if user.role == -1:
    #     raise HTTPException(status_code=401, detail="Authentication error")
    
    # if user.role != 4:
    #     result = await db.execute(select(Team_member).where(Team_member.user == user.id))
    #     db_team = result.scalars().first()
    #     user_id = db_team.admin
    # else:
    #     user_id = user.id
    result = await db.execute(select(Shipment).where(Shipment.id == shipment_id))
    db_shipment = result.scalars().first()
    if db_shipment is None:
        raise HTTPException(status_code=404, detail="shipment not found")
    update_data = shipment.dict(exclude_unset=True)  # Only update fields that are set
    for key, value in update_data.items():
        setattr(db_shipment, key, value) if value is not None else None
        
    settings.update_flag = 1
    try:
        await db.commit()
        await db.refresh(db_shipment)
    except Exception as e:
        db.rollback()
    finally:
        settings.update_flag = 0
    
    return db_shipment

@router.delete("/{shipment_id}", response_model=ShipmentRead)
async def delete_shipment(shipment_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.role == -1:
        raise HTTPException(status_code=401, detail="Authentication error")
    
    if user.role != 4:
        result = await db.execute(select(Team_member).where(Team_member.user == user.id))
        db_team = result.scalars().first()
        user_id = db_team.admin
    else:
        user_id = user.id
    result = await db.execute(select(Shipment).filter(Shipment.id == shipment_id, Shipment.user_id == user_id))
    shipment = result.scalars().first()
    if shipment is None:
        raise HTTPException(status_code=404, detail="shipment not found")
    
    settings.update_flag = 1
    try:
        await db.delete(shipment)
        await db.commit()
    except Exception as e:
        db.rollback()
    finally:
        settings.update_flag = 0
    
    return shipment
