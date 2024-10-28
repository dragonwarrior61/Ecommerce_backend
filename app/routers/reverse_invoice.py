from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from typing import List
from app.database import get_db
from app.models.reverse_invoice import Reverse_Invoice
from app.models.user import User
from app.models.team_member import Team_member
from app.models.billing_software import Billing_software
from app.utils.smart_api import reverse_invoice_smartbill
from app.routers.auth import get_current_user
from app.schemas.reverse_invoice import Reverse_InvoiceCreate, Reverse_InvoiceRead, Reverse_InvoiceUpdate

router = APIRouter()

@router.post("/")
async def create_reverse_invoice(reverse_invoice: Reverse_InvoiceCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.role == -1:
        raise HTTPException(status_code=401, detail="Authentication error")
    
    if user.role != 4:
        result = await db.execute(select(Team_member).where(Team_member.user == user.id))
        db_team = result.scalars().first()
        user_id = db_team.admin
    else:
        user_id = user.id
        
    db_reverse_invoice = Reverse_Invoice(**reverse_invoice.dict())
    result = await db.execute(select(Reverse_Invoice).where(Reverse_Invoice.order_id == db_reverse_invoice.order_id, Reverse_Invoice.user_id == user_id))
    invoice = result.scalars().first()
    if invoice:
        return invoice
    
    result = await db.execute(select(Billing_software).where(Billing_software.user_id == user_id, Billing_software.site_domain == 'smartbill.ro'))
    smartbill = result.scalars().first()
    
    response = reverse_invoice_smartbill(db_reverse_invoice.companyVatCode, db_reverse_invoice.seriesName, db_reverse_invoice.factura_number, smartbill)
    if response.status_code != 200:
        return response.json()
    
    response = response.json()
    if response.get('error_text') != '':
        return response
    db_reverse_invoice.storno_number = response.get('number')
    db_reverse_invoice.user_id = user_id
    db.add(db_reverse_invoice)
    
    await db.commit()
    await db.refresh(db_reverse_invoice)
    return db_reverse_invoice

@router.get('/count')
async def get_reverse_invoices_count(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.role == -1:
        raise HTTPException(status_code=401, detail="Authentication error")
    
    if user.role != 4:
        result = await db.execute(select(Team_member).where(Team_member.user == user.id))
        db_team = result.scalars().first()
        user_id = db_team.admin
    else:
        user_id = user.id
        
    result = await db.execute(select(Reverse_Invoice).where(Reverse_Invoice.user_id == user_id))
    db_reverse_invoices = result.scalars().all()
    return len(db_reverse_invoices)

@router.get("/", response_model=List[Reverse_InvoiceRead])
async def get_reverse_invoices(
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
        
    result = await db.execute(select(Reverse_Invoice).where(Reverse_Invoice.user_id == user_id))
    db_reverse_invoices = result.scalars().all()
    if db_reverse_invoices is None:
        raise HTTPException(status_code=404, detail="Reverse_Invoice not found")
    return db_reverse_invoices

@router.put("/{reverse_invoice_id}", response_model=Reverse_InvoiceRead)
async def update_reverse_invoice(reverse_invoice_id: int, reverse_invoice: Reverse_InvoiceUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.role == -1:
        raise HTTPException(status_code=401, detail="Authentication error")
    
    if user.role != 4:
        result = await db.execute(select(Team_member).where(Team_member.user == user.id))
        db_team = result.scalars().first()
        user_id = db_team.admin
    else:
        user_id = user.id
        
    result = await db.execute(select(Reverse_Invoice).filter(Reverse_Invoice.id == reverse_invoice_id, Reverse_Invoice.user_id == user_id))
    db_reverse_invoice = result.scalars().first()
    if db_reverse_invoice is None:
        raise HTTPException(status_code=404, detail="Reverse_Invoice not found")
    for var, value in vars(reverse_invoice).items():
        setattr(db_reverse_invoice, var, value) if value is not None else None
    db.add(db_reverse_invoice)
    await db.commit()
    await db.refresh(db_reverse_invoice)
    return db_reverse_invoice

@router.delete("/{reverse_invoice_id}", response_model=Reverse_InvoiceRead)
async def delete_reverse_invoice(reverse_invoice_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.role == -1:
        raise HTTPException(status_code=401, detail="Authentication error")
    
    if user.role != 4:
        result = await db.execute(select(Team_member).where(Team_member.user == user.id))
        db_team = result.scalars().first()
        user_id = db_team.admin
    else:
        user_id = user.id
        
    result = await db.execute(select(Reverse_Invoice).filter(Reverse_Invoice.id == reverse_invoice_id, Reverse_Invoice.user_id == user_id))
    reverse_invoice = result.scalars().first()
    if reverse_invoice is None:
        raise HTTPException(status_code=404, detail="Reverse_Invoice not found")
    await db.delete(reverse_invoice)
    await db.commit()
    return reverse_invoice
