from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from typing import List
from app.database import get_db
from app.models.reverse_invoice import Reverse_Invoice
from app.models.user import User
from app.models.marketplace import Marketplace
from app.models.team_member import Team_member
from app.models.billing_software import Billing_software
from app.utils.smart_api import reverse_invoice_smartbill, download_storno_pdf
from app.utils.emag_invoice import post_pdf
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
    db_reverse_invoice.companyVatCode = smartbill.registration_number
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

@router.get('/download_pdf')
async def download_invoice(cif: str, seriesname: str, number: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.role == -1:
        raise HTTPException(status_code=401, detail="Authentication error")
    if user.role != 4:
        result = await db.execute(select(Team_member).where(Team_member.user == user.id))
        db_team = result.scalars().first()
        user_id = db_team.admin
    else:
        user_id = user.id
        
    result = await db.execute(select(Billing_software).where(Billing_software.user_id == user_id, Billing_software.site_domain == "smartbill.ro"))
    db_smartbill = result.scalars().first()
    
    return download_storno_pdf(cif, seriesname, number, db_smartbill)

@router.get('/post_pdf')
async def post_invoice(order_id: int, marketplace: str, name: str, user: User = Depends(get_current_user), db:AsyncSession = Depends(get_db)):
    if user.role == -1:
        raise HTTPException(status_code=401, detail='Authentication error')
    if user.role != 4:
        result = await db.execute(select(Team_member).where(Team_member.user == user.id))
        db_team = result.scalars().first()
        user_id = db_team.admin
    else:
        user_id = user.id
        
    result = await db.execute(select(Marketplace).where(Marketplace.marketplaceDomain == marketplace, Marketplace.user_id == user_id))
    db_marketplace = result.scalars().first()
    return post_pdf(order_id, name, db_marketplace)