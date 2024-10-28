from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, any_
from typing import List
from app.models.user import User
from app.routers.auth import get_current_user
from app.database import get_db
from app.models.invoice import Invoice
from app.models.marketplace import Marketplace
from app.models.team_member import Team_member
from app.utils.emag_invoice import post_pdf
from app.models.billing_software import Billing_software
from app.schemas.invoice import InvoicesCreate, InvoicesRead, InvoicesUpdate
from app.utils.smart_api import generate_invoice, download_pdf, cancel_invoice_smartbill
import json
import logging

router = APIRouter()

@router.post("/")
async def create_invoice(invoice: InvoicesCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.role == -1:
        raise HTTPException(status_code=401, detail="Authentication error")
    
    if user.role != 4:
        result = await db.execute(select(Team_member).where(Team_member.user == user.id))
        db_team = result.scalars().first()
        user_id = db_team.admin
    else:
        user_id = user.id
        
    db_invoice = Invoice(**invoice.dict())
    order_id = db_invoice.order_id

    result = await db.execute(select(Invoice).where(Invoice.order_id == order_id))
    invoice = result.scalars().first()

    if invoice:
        return invoice
    
    result = await db.execute(select(Invoice).where(db_invoice.replacement_id != 0, Invoice.replacement_id == db_invoice.replacement_id))
    invoice = result.scalars().first()
    if invoice:
        return invoice
    
    result = await db.execute(select(Billing_software).where(Billing_software.user_id == user_id, Billing_software.site_domain == "smartbill.ro"))
    smartbill = result.scalars().first()
    if smartbill is None:
        raise HTTPException(status_code=404, detail="You have to add Smartbill account")
    
    data = {
        "companyVatCode": db_invoice.companyVatCode,
        "seriesName": db_invoice.seriesName,
        "client": json.loads(db_invoice.client),
        "useStock": db_invoice.usestock,
        "isDraft": db_invoice.isdraft,
        "mentions": db_invoice.mentions,
        "observations": db_invoice.observations,
        "language": db_invoice.language,
        "precision": db_invoice.precision,
        "useEstimateDetails": db_invoice.useEstimateDetails,
        "estimate": json.loads(db_invoice.estimate),
        "currency": db_invoice.currency,
        "issueDate": db_invoice.issueDate.strftime('%Y-%m-%d'),
        "products": json.loads(db_invoice.products)
    }
    result = generate_invoice(data, smartbill)
    if result.get('errorText') != '':
        return result
    
    db_invoice.number = result.get('number') if result.get('number') else ''
    db_invoice.series = result.get('series') if result.get('series') else ''
    db_invoice.url = result.get('url') if result.get('url') else ''
    db_invoice.user_id = user_id
    
    db.add(db_invoice)
    await db.commit()
    await db.refresh(db_invoice)
    return db_invoice

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
    
    return download_pdf(cif, seriesname, number, db_smartbill)

@router.get("/cancel_invoice")
async def cancel_invoice(cif: str, seriesname: str, number: str, user: User = Depends(get_current_user), db:AsyncSession = Depends(get_db)):
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
    
    resopnse = cancel_invoice_smartbill(cif, seriesname, number, db_smartbill)
    if resopnse.status_code == 200:
        result = await db.execute(select(Invoice).where(Invoice.number == number))
        db_invoice = result.scalars().first()
        db_invoice.type = 'Cancel'
        await db.commit()
        cancel_response = resopnse.json()
        return cancel_response.get("message")
    else:
        return resopnse

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

@router.get('/count')
async def get_invoice_count(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.role == -1:
        raise HTTPException(status_code=401, detail="Authentication error")
    
    if user.role != 4:
        result = await db.execute(select(Team_member).where(Team_member.user == user.id))
        db_team = result.scalars().first()
        user_id = db_team.admin
    else:
        user_id = user.id
        
    result = await db.execute(select(Invoice).where(Invoice.user_id == user_id))
    db_invoices = result.scalars().all()
    return len(db_invoices)

@router.get("/", response_model=List[InvoicesRead])
async def get_invoices(
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
        
    result = await db.execute(select(Invoice).where(Invoice.user_id == user_id))
    db_invoices = result.scalars().all()
    if db_invoices is None:
        raise HTTPException(status_code=404, detail="invoice not found")
    return db_invoices

@router.get("/{invoice_id}", response_model=InvoicesRead)
async def get_invoice(invoice_id: int, user:User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.role == -1:
        raise HTTPException(status_code=401, detail="Authentication error")
    
    if user.role != 4:
        result = await db.execute(select(Team_member).where(Team_member.user == user.id))
        db_team = result.scalars().first()
        user_id = db_team.admin
    else:
        user_id = user.id
        
    result = await db.execute(select(Invoice).filter(Invoice.id == invoice_id, Invoice.user_id == user_id))
    db_invoice = result.scalars().first()
    return db_invoice

@router.put("/{invoice_id}", response_model=InvoicesRead)
async def update_invoice(invoice_id: int, invoice: InvoicesUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.role == -1:
        raise HTTPException(status_code=401, detail="Authentication error")
    
    if user.role != 4:
        result = await db.execute(select(Team_member).where(Team_member.user == user.id))
        db_team = result.scalars().first()
        user_id = db_team.admin
    else:
        user_id = user.id
        
    result = await db.execute(select(Invoice).filter(Invoice.id == invoice_id, Invoice.user_id == user_id))
    db_invoice = result.scalars().first()
    if db_invoice is None:
        raise HTTPException(status_code=404, detail="invoice not found")
    for var, value in vars(invoice).items():
        setattr(db_invoice, var, value) if value is not None else None
    await db.commit()
    await db.refresh(db_invoice)
    return db_invoice

@router.delete("/{invoice_id}", response_model=InvoicesRead)
async def delete_invoice(invoice_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.role == -1:
        raise HTTPException(status_code=401, detail="Authentication error")
    
    if user.role != 4:
        result = await db.execute(select(Team_member).where(Team_member.user == user.id))
        db_team = result.scalars().first()
        user_id = db_team.admin
    else:
        user_id = user.id
        
    result = await db.execute(select(Invoice).filter(Invoice.id == invoice_id, Invoice.user_id == user_id))
    invoice = result.scalars().first()
    if invoice is None:
        raise HTTPException(status_code=404, detail="invoice not found")
    await db.delete(invoice)
    await db.commit()
    return invoice
