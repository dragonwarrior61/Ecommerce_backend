from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_, cast, Integer

from app.config import settings
from app.database import get_db
from app.models import Product, Returns
from app.routers.auth import get_team_admin_user
from app.schemas.returns import ReturnsCreate, ReturnsRead, ReturnsUpdate

router = APIRouter()

@router.post("/", response_model=ReturnsRead)
async def create_return(returns: ReturnsCreate, user_id: int = Depends(get_team_admin_user), db: AsyncSession = Depends(get_db)):
    db_return = Returns(**returns.model_dump())
    db_return.user_id = user_id
    settings.update_flag = 1
    try:
        db.add(db_return)
        await db.commit()
        await db.refresh(db_return)
    except Exception as e:
        db.rollback()
    finally:
        settings.update_flag = 0

    return db_return

@router.get('/count')
async def get_return_count(user_id: int = Depends(get_team_admin_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Returns).where(Returns.user_id == user_id))
    db_returns = result.scalars().all()
    return len(db_returns)

@router.get("/")
async def get_returns(
    page: int = Query(1, ge=1, description="page number"),
    items_per_page: int = Query(50, ge=1, le=100, description="Number of items per page"),
    user_id: int = Depends(get_team_admin_user), 
    db: AsyncSession = Depends(get_db)
):
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
            result = await db.execute(
                select(Product).where(
                    Product.id == product_id,
                    Product.product_marketplace == marketplace,
                    Product.user_id == db_return.user_id
                )
            )
            product = result.scalars().first()
            if product is None:
                result = await db.execute(select(Product).where(Product.id == product_id))
                product = result.scalars().first()
            ean.append(product.ean) 

        return_data.append({
            **{column.name: getattr(db_return, column.name) for column in Returns.__table__.columns},
            "ean": ean
        })
    return return_data

@router.get("/return_id")
async def get_return_info(return_id: int, user_id: int = Depends(get_team_admin_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Returns).where(cast(Returns.emag_id, Integer) == return_id, Returns.user_id == user_id))
    db_return = result.scalars().first()
    if db_return is None:
        raise HTTPException(status_code=404, detail="awb not found")
    return db_return

@router.get("/awb")
async def get_return_awb(awb: str, db: AsyncSession = Depends(get_db)):
    if awb[:2] == "01":
        result = await db.execute(
            select(Returns).where(
                or_(
                    Returns.awb == awb[2:],
                    Returns.awb == awb[2:-3],
                    Returns.awb == awb,
                    Returns.awb == awb[:-3]
                )
            )
        )
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
        result = await db.execute(
            select(Product).where(
                Product.id == product_id,
                Product.product_marketplace == marketplace,
                Product.user_id == user_id
            )
        )
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
async def update_return(return_id: int, returns: ReturnsUpdate, user_id: int = Depends(get_team_admin_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Returns).filter(Returns.order_id == return_id, Returns.user_id == user_id))
    db_return = result.scalars().first()
    if db_return is None:
        raise HTTPException(status_code=404, detail="return not found")
    for var, value in vars(returns).items():
        setattr(db_return, var, value) if value is not None else None

    settings.update_flag = 1
    try:
        await db.commit()
        await db.refresh(db_return)
    except Exception as e:
        db.rollback()
    finally:
        settings.update_flag = 0

    return db_return

@router.delete("/{return_id}", response_model=ReturnsRead)
async def delete_return(return_id: int, user_id: int = Depends(get_team_admin_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Returns).filter(Returns.order_id == return_id, Returns.user_id == user_id))
    returns = result.scalars().first()
    if ReturnsCreate is None:
        raise HTTPException(status_code=404, detail="return not found")

    settings.update_flag = 1
    try:
        await db.delete(returns)
        await db.commit()
    except Exception as e:
        db.rollback()
    finally:
        settings.update_flag = 0

    return Returns
