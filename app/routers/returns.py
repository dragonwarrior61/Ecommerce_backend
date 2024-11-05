from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, any_, or_, cast, Integer
from typing import List
from app.database import get_db
from app.models.product import Product
from app.models.user import User
from app.routers.auth import get_current_user
from app.models.returns import Returns
from app.models.team_member import Team_member
from app.schemas.returns import ReturnsCreate, ReturnsRead, ReturnsUpdate
from app.config import settings

router = APIRouter()

@router.post("/", response_model=ReturnsRead)
async def create_return(returns: ReturnsCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.role == -1:
        raise HTTPException(status_code=401, detail="Authentication error")
    
    if user.role != 4:
        result = await db.execute(select(Team_member).where(Team_member.user == user.id))
        db_team = result.scalars().first()
        user_id = db_team.admin
    else:
        user_id = user.id
    db_return = Returns(**returns.dict())
    db_return.user_id = user_id
    
    settings.update_flag = 1
    db.add(db_return)
    await db.commit()
    await db.refresh(db_return)
    settings.update_flag = 0
    
    return db_return

@router.get('/count')
async def get_return_count(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.role == -1:
        raise HTTPException(status_code=401, detail="Authentication error")
    
    if user.role != 4:
        result = await db.execute(select(Team_member).where(Team_member.user == user.id))
        db_team = result.scalars().first()
        user_id = db_team.admin
    else:
        user_id = user.id
        
    result = await db.execute(select(Returns).where(Returns.user_id == user_id))
    db_returns = result.scalars().all()
    return len(db_returns)

@router.get("/")
async def get_returns(
    page: int = Query(1, ge=1, description="page number"),
    items_per_page: int = Query(50, ge=1, le=100, description="Number of items per page"),
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
    result = await db.execute(select(Returns).where(Returns.user_id == user_id).offset(offset).limit(items_per_page))
    db_returns = result.scalars().all()
    if db_returns is None:
        raise HTTPException(status_code=404, detail="return not found")
    
    return_data = []
    for db_return in db_returns:
        product_ids = db_return.products
        marketplace = db_return.return_market_place
        ean = []

        for product_id in product_ids:
            result = await db.execute(select(Product).where(Product.id == product_id, Product.product_marketplace == marketplace, Product.user_id == db_return.user_id))
            product = result.scalars().first()
            if product is None:
                result = await db.execute(select(Product).where(Product.id == product_id))
                product = result.scalars().first()
            else:
                continue
            ean.append(product.ean) 
        
        return_data.append({
            **{column.name: getattr(db_return, column.name) for column in Returns.__table__.columns},
            "ean": ean
        })
    return return_data

@router.get("/return_id")
async def get_return_info(return_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.role == -1:
        raise HTTPException(status_code=401, detail="Authentication error")
    
    if user.role != 4:
        result = await db.execute(select(Team_member).where(Team_member.user == user.id))
        db_team = result.scalars().first()
        user_id = db_team.admin
    else:
        user_id = user.id
        
    result = await db.execute(select(Returns).where(cast(Returns.emag_id, Integer) == return_id, Returns.user_id == user_id))
    db_return = result.scalars().first()
    if db_return is None:
        raise HTTPException(status_code=404, detail="awb not found")
    return db_return

@router.get("/awb")
async def get_return_awb(awb: str, db: AsyncSession = Depends(get_db)):
    if awb[:2] == "01":
        result = await db.execute(select(Returns).where(or_(Returns.awb == awb[2:], Returns.awb == awb[2:-3], Returns.awb == awb, Returns.awb == awb[:-3])))
    else:
        result = await db.execute(select(Returns).where(or_(Returns.awb == awb, Returns.awb == awb[:-3])))
    db_return = result.scalars().first()
    if db_return is None:
        raise HTTPException(status_code=404, detail="awb not found")
    
    product_ids = db_return.products
    marketplace = db_return.return_market_place
    user_id = db_return.user_id
    ean = []

    for product_id in product_ids:
        result = await db.execute(select(Product).where(Product.id == product_id, Product.product_marketplace == marketplace, Product.user_id == user_id))
        product = result.scalars().first()
        # if product is None:
        #     result = await db.execute(select(Product).where(Product.id == product_id, Product.user_id == db_return.user_id))
        #     product = result.scalars().first()
        ean.append(product.ean)

    return {
        **{column.name: getattr(db_return, column.name) for column in Returns.__table__.columns},
        "ean": ean
    }

@router.put("/{return_id}", response_model=ReturnsRead)
async def update_return(return_id: int, returns: ReturnsUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.role == -1:
        raise HTTPException(status_code=401, detail="Authentication error")
    
    if user.role != 4:
        result = await db.execute(select(Team_member).where(Team_member.user == user.id))
        db_team = result.scalars().first()
        user_id = db_team.admin
    else:
        user_id = user.id
        
    result = await db.execute(select(Returns).filter(Returns.order_id == return_id, Returns.user_id == user_id))
    db_return = result.scalars().first()
    if db_return is None:
        raise HTTPException(status_code=404, detail="return not found")
    for var, value in vars(returns).items():
        setattr(db_return, var, value) if value is not None else None
    
    settings.update_flag = 1
    await db.commit()
    await db.refresh(db_return)
    settings.update_flag = 0
    
    return db_return

@router.delete("/{return_id}", response_model=ReturnsRead)
async def delete_return(return_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.role == -1:
        raise HTTPException(status_code=401, detail="Authentication error")
    
    if user.role != 4:
        result = await db.execute(select(Team_member).where(Team_member.user == user.id))
        db_team = result.scalars().first()
        user_id = db_team.admin
    else:
        user_id = user.id
        
    result = await db.execute(select(Returns).filter(Returns.order_id == return_id, Returns.user_id == user_id))
    returns = result.scalars().first()
    if ReturnsCreate is None:
        raise HTTPException(status_code=404, detail="return not found")
    
    settings.update_flag = 1
    await db.delete(returns)
    await db.commit()
    settings.update_flag = 0
    
    return Returns
