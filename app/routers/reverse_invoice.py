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
from app.utils.smart_api import reverse_invoice_smartbill, download_storno_pdf, download_pdf_server
from app.utils.emag_invoice import post_pdf
from app.routers.auth import get_current_user
from app.schemas.reverse_invoice import Reverse_InvoiceCreate, Reverse_InvoiceRead, Reverse_InvoiceUpdate
import logging
import re
from app.config import settings

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
    logging.info(f"params: {reverse_invoice}")
    result = await db.execute(select(Reverse_Invoice).where(Reverse_Invoice.order_id == db_reverse_invoice.order_id, Reverse_Invoice.user_id == user_id))
    invoice = result.scalars().first()
    if invoice:
        return invoice
    
    result = await db.execute(select(Billing_software).where(Billing_software.user_id == user_id, Billing_software.site_domain == 'smartbill.ro'))
    smartbill = result.scalars().first()
    db_reverse_invoice.companyVatCode = smartbill.registration_number
    response = reverse_invoice_smartbill(db_reverse_invoice.seriesName, db_reverse_invoice.factura_number, smartbill)
    if response.status_code != 200:
        return response.json()
    
    response = response.json()
    if response.get('errorText') != '':
        return response
    db_reverse_invoice.storno_number = response.get('number')
    db_reverse_invoice.post = 0
    db_reverse_invoice.user_id = user_id
    
    settings.update_flag = 1
    try:
        db.add(db_reverse_invoice)
        await db.commit()
        await db.refresh(db_reverse_invoice)
    except Exception as e:
        db.rollback()
    finally:
        settings.update_flag = 0
    
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
    
    result = await db.execute(select(Billing_software).where(Billing_software.user_id == user_id, Billing_software.site_domain == 'smartbill.ro'))
    db_smartbill = result.scalars().first()
    
    result = await db.execute(select(Reverse_Invoice).where(Reverse_Invoice.order_id == order_id, Reverse_Invoice.user_id == user_id))
    db_reverse_invoice = result.scalars().first()
    
    match = re.search(r"_(\D+)(\d+)\.pdf$", name)
    if match:
        seriesname = match.group(1) 
        number = match.group(2)
    else:
        return

    download_pdf_server(seriesname, number, name, db_smartbill)
    response = post_pdf(order_id, name, db_marketplace)
    if response.status_code != 200:
        return response.json()
    
    db_reverse_invoice.post = 1
    
    settings.update_flag = 1
    try:
        await db.commit()
        await db.refresh(db_reverse_invoice)
    except Exception as e:
        db.rollback()
    finally:
        settings.update_flag = 0
    
    return response.json()