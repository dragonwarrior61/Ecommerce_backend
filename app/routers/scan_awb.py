from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, any_, or_, and_
from sqlalchemy.orm import aliased
from typing import List
from app.database import get_db
from app.models.user import User
from app.models.orders import Order
from app.routers.auth import get_current_user
from app.models.internal_product import Internal_Product
from app.models.product import Product
from app.models.returns import Returns
from app.models.invoice import Invoice
from app.models.reverse_invoice import Reverse_Invoice
from app.models.returns import Returns
from app.models.scan_awb import Scan_awb
from app.models.replacement import Replacement
from app.models.team_member import Team_member
from app.models.awb import AWB
from app.schemas.scan_awb import Scan_awbCreate, Scan_awbRead, Scan_awbUpdate
from app.config import settings
from collections import defaultdict
from fastapi.encoders import jsonable_encoder

router = APIRouter()

@router.post("/")
async def create_scan_awb(scan_awb: Scan_awbCreate, db: AsyncSession = Depends(get_db)):
    db_scan_awb = Scan_awb(**scan_awb.dict())
    result = await db.execute(select(Scan_awb).where(Scan_awb.awb_number == db_scan_awb.awb_number))
    scan_awb = result.scalars().first()
    if scan_awb:
        return scan_awb
    awb_numer = db_scan_awb.awb_number
    
    result = await db.execute(select(Returns).where(or_(Returns.awb == awb_numer, Returns.awb == awb_numer[:-3])))
    db_return = result.scalars().first()
    if db_return:
        db_scan_awb.awb_type = "Return"
        user_id = db_return.user_id
        db_scan_awb.user_id == user_id
        if db_scan_awb.awb_number[-3:] == '001':
            db_scan_awb.awb_number = db_scan_awb.awb_number[:-3]
        settings.update_flag = 1
        try:
            db.add(db_scan_awb)
            await db.commit()
            await db.refresh(db_scan_awb)
        except Exception as e:
            db.rollback()
        finally:
            settings.update_flag = 0
        
        return db_scan_awb
    
    result = await db.execute(select(AWB).where(or_(AWB.awb_number == awb_numer, AWB.awb_number == awb_numer[:-3])))
    db_awb = result.scalars().first()
    if db_awb is None:
        raise HTTPException(status_code=404, detail="This awb_nubmer is not in our database")
    
    if db_awb.awb_status in ([16, 35, 93]):
        db_scan_awb.awb_type = "Refusal of Delivery"
        user_id = db_awb.user_id
        db_scan_awb.user_id = user_id
    else:
        return
    if db_scan_awb.awb_number[-3:] == '001':
        db_scan_awb.awb_number = db_scan_awb.awb_number[:-3]
    
    settings.update_flag = 1
    try:
        db.add(db_scan_awb)
        await db.commit()
        await db.refresh(db_scan_awb)
    except Exception as e:
        db.rollback()
    finally:
        settings.update_flag = 0
    
    return db_scan_awb

@router.get('/count')
async def get_scan_awb_count(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.role == -1:
        raise HTTPException(status_code=401, detail="Authentication error")
    
    if user.role != 4:
        result = await db.execute(select(Team_member).where(Team_member.user == user.id))
        db_team = result.scalars().first()
        user_id = db_team.admin
    else:
        user_id = user.id
        
    result = await db.execute(select(Scan_awb).where(Scan_awb.user_id == user_id))
    scan_awbs = result.scalars().all()
    return len(scan_awbs)

@router.get("/")
async def get_scan_awbs(
    page: int = Query(1, ge=1, description="Page number"),
    itmes_per_page: int = Query(50, ge=1, le=100, description="Number of items per page"),
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
        
    offset = (page - 1) * itmes_per_page
    
    AWBAlias = aliased(AWB)
    InvoiceAlias = aliased(Invoice)
    OrderAlias = aliased(Order)
    Reverse_InvoiceAlias = aliased(Reverse_Invoice)
    ReturnsAlias = aliased(Returns)
    ReplacementAlias = aliased(Replacement)
    
    query = select(Scan_awb, ReturnsAlias, AWBAlias, OrderAlias, ReplacementAlias, InvoiceAlias, Reverse_InvoiceAlias).where(Scan_awb.user_id == user_id)
    query = query.outerjoin(ReturnsAlias, and_(Scan_awb.awb_number == ReturnsAlias.awb))
    query = query.outerjoin(AWBAlias, AWBAlias.awb_number == Scan_awb.awb_number)
    query = query.outerjoin(OrderAlias, and_(OrderAlias.id == AWBAlias.order_id, OrderAlias.user_id == AWBAlias.user_id, AWBAlias.number > 0))
    query = query.outerjoin(ReplacementAlias, and_(ReplacementAlias.order_id == AWBAlias.order_id, ReplacementAlias.user_id == AWBAlias.user_id, AWBAlias.number < 0))
    query = query.outerjoin(InvoiceAlias, and_(InvoiceAlias.order_id == OrderAlias.id, InvoiceAlias.user_id == OrderAlias.user_id))
    query = query.outerjoin(Reverse_InvoiceAlias, and_(Reverse_InvoiceAlias.order_id == OrderAlias.id, Reverse_InvoiceAlias.user_id == OrderAlias.user_id))
    query = query.order_by(Scan_awb.scan_date.desc())
    query = query.offset(offset).limit(itmes_per_page)
    result = await db.execute(query)
    db_scan_awbs = result.fetchall()
    
    if db_scan_awbs is None:
        raise HTTPException(status_code=404, detail="scan_awb not found")
    
    scan_awb_data = []
    for db_scan_awb, return_info, awb, order, replacement, invoice, reverse_invoice in db_scan_awbs:
        if return_info:
            ean = []
            product_id_list = return_info.products
            for product_id in product_id_list:
                result = await db.execute(select(Product).where(Product.id == product_id, Product.product_marketplace == return_info.return_market_place, Product.user_id == return_info.user_id))
                db_product = result.scalars().first()
                if db_product is None:
                    result = await db.execute(select(Product).where(Product.id == product_id, Product.user_id == return_info.user_id))
                    db_product = result.scalars().first()
                ean.append(db_product.ean)
        elif order:
            ean = []
            product_id_list = order.product_id
            for product_id in product_id_list:
                result = await db.execute(select(Product).where(Product.id == product_id, Product.product_marketplace == order.order_market_place, Product.user_id == order.user_id))
                db_product = result.scalars().first()
                if db_product is None:
                    result = await db.execute(select(Product).where(Product.id == product_id, Product.user_id == order.user_id))
                    db_product = result.scalars().first()
                ean.append(db_product.ean)
        else:
            ean = []
            
        scan_awb_data.append({
            "scan_awb": db_scan_awb,
            "awb": awb,
            "order": order,
            "replacement": replacement,
            "invoice": invoice,
            "reverse_invoice": reverse_invoice,
            "return": return_info,
            "ean": ean
        })
    return scan_awb_data

@router.get("/awb_number")
async def get_scan_awb_number(awb_number: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Scan_awb).where(Scan_awb.awb_number == awb_number))
    db_scan_awb = result.scalars().first()
    return db_scan_awb

@router.get("/{scan_awb_id}", response_model=Scan_awbRead)
async def get_scan_awb(scan_awb_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.role == -1:
        raise HTTPException(status_code=401, detail="Authentication error")
    
    if user.role != 4:
        result = await db.execute(select(Team_member).where(Team_member.user == user.id))
        db_team = result.scalars().first()
        user_id = db_team.admin
    else:
        user_id = user.id
        
    result = await db.execute(select(Scan_awb).where(Scan_awb.id == scan_awb_id, Scan_awb.user_id == user_id))
    db_scan_awb = result.scalars().first()
    return db_scan_awb

@router.put("/{scan_awb_id}", response_model=Scan_awbRead)
async def update_scan_awb(scan_awb_id: int, scan_awb: Scan_awbUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.role == -1:
        raise HTTPException(status_code=401, detail="Authentication error")
    
    if user.role != 4:
        result = await db.execute(select(Team_member).where(Team_member.user == user.id))
        db_team = result.scalars().first()
        user_id = db_team.admin
    else:
        user_id = user.id
        
    result = await db.execute(select(Scan_awb).where(Scan_awb.id == scan_awb_id, Scan_awb.user_id == user_id))
    db_scan_awb = result.scalars().first()
    if db_scan_awb is None:
        raise HTTPException(status_code=404, detail="scan_awb not found")
    for var, value in vars(scan_awb).items():
        setattr(db_scan_awb, var, value) if value is not None else None
        
    settings.update_flag = 1
    try:
        await db.commit()
        await db.refresh(db_scan_awb)
    except Exception as e:
        db.rollback()
    finally:
        settings.update_flag = 0
    
    return db_scan_awb

@router.delete("/{scan_awb_id}", response_model=Scan_awbRead)
async def delete_scan_awb(scan_awb_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.role == -1:
        raise HTTPException(status_code=401, detail="Authentication error")
    
    if user.role != 4:
        result = await db.execute(select(Team_member).where(Team_member.user == user.id))
        db_team = result.scalars().first()
        user_id = db_team.admin
    else:
        user_id = user.id
        
    result = await db.execute(select(Scan_awb).where(Scan_awb.id == scan_awb_id, Scan_awb.user_id == user_id))
    scan_awb = result.scalars().first()
    if scan_awb is None:
        raise HTTPException(status_code=404, detail="scan_awb not found")
    
    settings.update_flag = 1
    try:
        await db.delete(scan_awb)
        await db.commit()
    except Exception as e:
        db.rollback()
    finally:
        settings.update_flag = 0
    
    return scan_awb
