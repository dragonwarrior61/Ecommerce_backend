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
        db_scan_awb.user_id = user_id
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

@router.get("/improve_user_id")
async def get_improve_user_id(db: AsyncSession = Depends(get_db)):
    awb_number_list = [
        "1ONBLR303921791",
        "1ONBLR306424259",
        "1ONBLR306407720",
        "1ONBRS305730184",
        "1ONBLR306293811",
        "1ONBLR304271632",
        "1ONBLR305599389",
        "1ONBRS306155259",
        "1ONBLR306465500",
        "1ONBLR306399148",
        "1ONBLR306458567",
        "1ONBLR306229597",
        "1ONBLR306467547",
        "1ONBRS306986187",
        "1ONBLR305290867",
        "1ONBLR307333634",
        "1ONBLR307525309",
        "1ONBRS307514446",
        "1ONBLR309567618",
        "011ONBXS307125799",
        "1ONBLR308856033",
        "1ONBLR309608961",
        "1ONBLR309153504",
        "1ONBLR308606248",
        "1ONBLR309153504",
        "1ONBLR310873943",
        "1ONBLR311838169",
        "1ONBLR311803288",
        "1ONBLR311793359",
        "1ONBRS310724181",
        "1ONBLR312454371",
        "1ONBRS311566096",
        "1ONBRS310619305",
        "1ONBLR310867895",
        "1ONBRS312147076",
        "1ONBLR311006402",
        "011ONBXR310423144",
        "1ONBLR310473756",
        "1ONBLR310272353",
        "1ONBRS311285735",
        "1ONBLR312585580",
        "1ONBLR311562585",
        "1ONBLR306311016",
        "1ONBLR305245552",
        "1ONBLR306248325",
        "1ONBRS306155259",
        "1ONBRS307263983",
        "1ONBLR311037913",
        "1ONBLR312110649",
        "1ONBRS311217704",
        "1ONBLR311244046",
        "1ONBLR310966478",
        "1ONBRS311391031",
        "1ONBRS310709044",
        "1ONBLR312688311",
        "1ONBLR312156740",
        "1ONBLR311099496",
        "1ONBRS311581036",
        "1ONBRS310788418",
        "1ONBLR312500042",
        "1ONBRS310994051",
        "1ONBRS311590861",
        "1ONBLR311888462",
        "1ONBRS309622036",
        "1ONBLR310996780",
        "1ONBLR310992108",
        "1ONBRS310350246",
        "1ONBRS311662752",
        "1ONBLR311515657",
        "1ONBLR311514353",
        "1ONBLR311539996",
        "1ONBLR311840597",
        "1ONBRS311391031",
        "1ONBLR310291529",
        "1ONBLR310875929",
        "1ONBLR311517069",
        "1ONBLR310872803",
        "1ONBLR312124440",
        "1ONBLR307915750",
        "1ONBLR310283962",
        "1ONBLR310996780",
        "1ONBLR309640507",
        "1ONBLR310988465",
        "1ONBLR310321259",
        "1ONBLR309533432",
        "1ONBLR310148059",
        "1ONBLR310358666",
        "1ONBLR310982053",
        "1ONBLR309571478",
        "1ONBLR309724691",
        "1ONBLR309031089",
        "1ONBRS310129875",
        "1ONBRS309592358",
        "1ONBLR309626272",
        "1ONBLR311077443",
        "1ONBLR309598996",
        "1ONBLR310182199",
        "1ONBRS310387728",
        "1ONBLR311073054",
        "1ONBRS310396012",
        "1ONBLR310156696",
        "1ONBLR307961080",
        "1ONBLR309732068",
        "1ONBLR309692493",
        "1ONBRS312140819",
        "1ONBLR307891840",
        "1ONBLR310961527",
        "1ONBLR312905429",
        "1ONBLR309808522",
        "1ONBLR312597659",
        "1ONBLR312982791",
        "1ONBLR312817181",
        "1ONBLR312516128",
        "1ONBLR309785694",
        "1ONBLR312551762",
        "1ONBLR312581906",
        "1ONBLR311455074",
        "1ONBLR312832520",
        "1ONBLR312716241",
        "1ONBLR312917140",
        "1ONBLR310908046",
        "1ONBLR312720302",
        "1ONBLR310867044",
        "1ONBLR312490422",
        "011ONBXS311567977",
        "1ONBLR313198578",
        "1ONBLR313019214",
        "1ONBLR312888071",
        "1ONBLR310156696",
        "1ONBLR310961527",
        "1ONBLR310961527",
        "1ONBLR310156696",
        "1ONBLR310961527",
        "1ONBRS311656546",
        "1ONBLR311516303",
        "1ONBRS310999578",
        "1ONBRS311490648",
        "1ONBRS311425835",
        "1ONBLR309271250",
        "1ONBLR311532140",
        "1ONBLR309328639",
        "1ONBLR310278364",
        "1ONBLR311538861",
        "1ONBRS311044134",
        "1ONBLR310961527",
        "1ONBRS310988242",
        "1ONBLR306293811",
        "011ONBXS308171635",
        "1ONBLR308871922",
        "1ONBLR310865620",
        "1ONBLR309682898",
        "1ONBLR309657294",
        "1ONBLR309769498",
        "1ONBLR309591740",
        "1ONBRS309572291",
        "1ONBLR308377314",
        "1ONBLR310871806",
        "1ONBLR309596686",
        "1ONBLR311777418",
        "1ONBRS312140819",
        "1ONBLR312903596",
        "1ONBLR312723660",
        "1ONBLR311645741",
        "1ONBLR311169685",
        "1ONBLR309617386",
        "1ONBLR309319039",
        "1ONBRS306986187",
        "1ONBLR313965190",
    ]
    for awb_number in awb_number_list:
        result = await db.execute(select(Scan_awb).where(Scan_awb.awb_number == awb_number))
        db_scan_awb = result.scalars().first()
        result = await db.execute(select(Returns).where(or_(Returns.awb == awb_number, Returns.awb == awb_numer[:-3])))
        db_return = result.scalars().first()
        if db_return:
            user_id = db_return.user_id
            db_scan_awb.user_id = user_id
    await db.commit()
            
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
