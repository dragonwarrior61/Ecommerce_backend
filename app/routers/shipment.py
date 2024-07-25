from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from sqlalchemy import any_
from typing import List
from app.database import get_db
from app.models.shipment import Shipment
from app.schemas.shipment import ShipmentCreate, ShipmentRead, ShipmentUpdate

router = APIRouter()

@router.post("/", response_model=ShipmentRead)
async def create_shipment(shipment: ShipmentCreate, db: AsyncSession = Depends(get_db)):
    db_shipment = Shipment(**shipment.dict())
    db.add(db_shipment)
    await db.commit()
    await db.refresh(db_shipment)
    return db_shipment

@router.get('/count')
async def get_shipments_count(db: AsyncSession = Depends(get_db)):
    result = await db.execute(func.count(Shipment.id))
    count = result.scalar()
    return count

@router.get("/", response_model=List[ShipmentRead])
async def get_shipments(
    page: int = Query(1, ge=1, description="Page number"),
    items_per_page: int = Query(50, ge=1, le=100, description="Number of items per page"),
    db: AsyncSession = Depends(get_db)
):
    
    offset = (page - 1) * items_per_page
    result = await db.execute(select(Shipment).offset(offset).limit(items_per_page))
    db_shipments = result.scalars().all()
    if db_shipments is None:
        raise HTTPException(status_code=404, detail="shipment not found")
    return db_shipments

@router.get("/imports")
async def get_imports(ean: str, db:AsyncSession = Depends(get_db)):
    query = select(Shipment).where(ean == any_(Shipment.ean))
    result = await db.execute(query)

    shipments = result.scalars().all()

    imports_data = []

    for shipment in shipments:
        ean_list = shipment.ean
        quantity_list = shipment.quantity
        title = shipment.title
        index = ean_list.index(ean)
        quantity = quantity_list[index]

        imports_data.append({
            "title": title,
            "quantity": quantity
        })

    return imports_data

@router.put("/{shipment_id}", response_model=ShipmentRead)
async def update_shipment(shipment_id: int, shipment: ShipmentUpdate, db: AsyncSession = Depends(get_db)):
    db_shipment = await db.execute(select(Shipment).filter(Shipment.id == shipment_id)).scalars().first()
    if db_shipment is None:
        raise HTTPException(status_code=404, detail="shipment not found")
    update_data = shipment.dict(exclude_unset=True)  # Only update fields that are set
    for key, value in update_data.items():
        setattr(shipment, key, value)
    await db.commit()
    await db.refresh(db_shipment)
    return db_shipment

@router.delete("/{shipment_id}", response_model=ShipmentRead)
async def delete_shipment(shipment_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Shipment).filter(Shipment.id == shipment_id))
    shipment = result.scalars().first()
    if shipment is None:
        raise HTTPException(status_code=404, detail="shipment not found")
    await db.delete(shipment)
    await db.commit()
    return shipment