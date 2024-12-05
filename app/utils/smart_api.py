from psycopg2 import sql
from urllib.parse import urlparse
from app.config import settings
from fastapi import Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.internal_product import Internal_Product
from app.models.product import Product
from app.models.orders import Order
from app.models.invoice import Invoice
from app.models.reverse_invoice import Reverse_Invoice
from app.models.awb import AWB
from app.schemas.invoice import InvoicesCreate
from app.utils.emag_invoice import post_pdf, post_factura_pdf
from app.models.billing_software import Billing_software
from app.models.marketplace import Marketplace
from sqlalchemy import select, any_, and_, or_, not_
from sqlalchemy.orm import aliased
import requests
from io import BytesIO
from requests.auth import HTTPBasicAuth
import base64
import json
import logging
from datetime import datetime, timedelta
import re
import math


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_stock(smartbill: Billing_software):
    today = datetime.today()
    today = today.strftime("%Y-%m-%d")

    USERNAME = smartbill.username
    PASSWORD = smartbill.password
    url = "https://ws.smartbill.ro/SBORO/api/stocks"
    params = {
        "cif": smartbill.registration_number,
        "date": today,
        "warehouseName": smartbill.warehouse_name
    }
    credentials = base64.b64encode(f"{USERNAME}:{PASSWORD}".encode()).decode()
    headers = {
        "Authorization": f"Basic {credentials}",
        "accept": "application/json",
    }

    # Replace 'username' and 'password' with the actual credentials
    response = requests.get(url, headers=headers, params=params)
    # Replace 'username' and 'password' with the actual credentials
    if response.status_code == 200:
        result = response.json()
        products = result.get('list')
        return products
    else:
        return response.json().get('errorText')

async def update_stock(db: AsyncSession):
    results = get_stock()
    for product_list in results:
        products = product_list.get('products')
        for product in products:
            product_code = product.get('productCode')
            result = await db.execute(select(Internal_Product).where(Internal_Product.product_code == product_code))
            db_product = result.scalars.first()
            db_product.stock = product.get('quantity')

async def refresh_invoice(db: AsyncSession):
    result = await db.execute(select(Order).where(Order.status == any_([1, 2, 3]), Order.user_id == 1))
    new_orders = result.scalars().all()
    
    order_id_list = []
    starting_time = datetime.now()
    
    for order in new_orders:
        try:
            order_id = order.id
            user_id = order.user_id
            marketplace = order.order_market_place
            
            result = await db.execute(select(Billing_software).where(Billing_software.user_id == user_id, Billing_software.site_domain == "smartbill.ro"))
            smartbill = result.scalars().first()
            
            if smartbill is None:
                continue
            
            result = await db.execute(select(Marketplace).where(Marketplace.marketplaceDomain == marketplace, Marketplace.user_id == user_id))
            marketplace = result.scalars().first()
            if marketplace.marketplaceDomain == "altex.ro":
                continue
            if marketplace.country == "hu":
                currency = "HUF"
            elif marketplace.country == "bg":
                currency = "BGN"
            else:
                currency = "RON"
            vat = marketplace.vat / 100 + 1
            
            result = await db.execute(select(Invoice).where(Invoice.user_id == user_id, Invoice.order_id == order_id))
            db_invoice = result.scalars().first()
            if db_invoice is not None:
                continue
            
            attachments = json.loads(order.attachments)
            if "factura" in str(attachments).lower():
                continue
            issueDate = datetime.now()
            products = []
            
            product_list = order.product_id
            quantity = order.quantity
            sale_price = order.sale_price
            
            for i in range(len(product_list)):
                product_id = product_list[i]
                result = await db.execute(select(Product).where(Product.id == product_id, Product.user_id == user_id, Product.product_marketplace == marketplace.marketplaceDomain))
                db_product = result.scalars().first()
                
                if db_product is None:
                    result = await db.execute(select(Product).where(Product.id == product_id, Product.user_id == user_id))
                    db_product = result.scalars().first()

                name = db_product.product_name
                ean = db_product.ean
                
                result = await db.execute(select(Internal_Product).where(Internal_Product.ean == ean))
                db_internal_product = result.scalars().first()
                product_code = db_internal_product.product_code
                
                products.append({
                    "code": product_code,
                    "name": name,
                    "measuringUnitName": "buc",
                    "currency": currency,
                    "quantity": quantity[i],
                    "price": sale_price[i],
                    "isTaxIncluded": False,
                    "taxPercentage": marketplace.vat,
                    "saveToDb": False,
                    "isDiscount": False,
                    "isService": False,
                    "warehouseName": "Produse Emag"
                })
            
            for product in products:
                if currency == "HUF":
                    product['price'] = round(float(product['price']), 2)
                    product['price'] *= vat
                    product['isTaxIncluded'] = True
                    product['price'] = round(math.ceil(product['price'] * 2) / 2, 2)
                else:
                    product['price'] *= vat
                    product['isTaxIncluded'] = True
                    
            shipping_tax_voucher = json.loads(order.shipping_tax_voucher_split)
            vouchers = json.loads(order.vouchers)
            
            is_shipping_tax = True
            details = json.loads(order.details)
            
            if order.delivery_mode == 'pickup' and details.get('locker_id') not in [None, '']:
                is_shipping_tax = False
            
            isEMGINvoice = False
            
            for attachment in attachments:
                if attachment.get('type') == 13:
                    isEMGINvoice = True
                    break
            
            for index, voucher in enumerate(vouchers):
                deduct_value = 0
                if shipping_tax_voucher and index < len(shipping_tax_voucher):
                    deduct_value = float(shipping_tax_voucher[index]['value'])
                
                discount_value = float(voucher['sale_price']) if is_shipping_tax else float(voucher['sale_price']) - deduct_value
                discount_value = round(discount_value, 2)
                discount_value *= vat
                if currency == "HUF":
                    discount_value = round(math.ceil(discount_value * 2) / 2, 2)
                else:
                    discount_value = round(discount_value, 2)
                    
                products.append({
                    'name': voucher['voucher_name'],
                    'code': str(voucher['voucher_id']),
                    'measuringUnitName': 'buc',
                    'currency': currency,
                    'isTaxIncluded': is_shipping_tax,
                    'isDiscount': True,
                    'taxPercentage': float(voucher['vat']) * 100,
                    'taxName': "" if float(voucher['vat']) else "SDD",
                    'discountType': 1,
                    'discountValue': discount_value,
                })
                
            if isEMGINvoice == False and is_shipping_tax:
                products.append({
                    'name': 'Taxe de livrare',
                    'code': 'shipping_tax',
                    'isDiscount': False,
                    'measuringUnitName': 'buc',
                    'currency': currency,
                    'isTaxIncluded': True,
                    'taxPercentage': round((vat - 1) * 100, 0),
                    'quantity': 1,
                    'saveToDb': False,
                    'price': order.shipping_tax,
                    'isService': True,
                })
            client = {
                "name": order.company if order.company else order.name,
                "vatCode": order.code if order.is_vat_payer else '',
                "isTaxPayer": order.is_vat_payer == 1,
                "address": order.billing_street,
                "city": order.billing_city,
                "country": order.billing_country,
                "county": order.billing_suburb,
                "bank": order.bank,
                "iban": order.iban,
                "saveToDb": True,
                "regCom": order.registration_number
            }
            data = {
                "companyVatCode": smartbill.registration_number,
                "seriesName": "EMG" + marketplace.country.upper(),
                # "seriesName": "EMGINL",
                "client": client,
                "useStock": True,
                "isDraft": False,
                "mentions": f"Comanda Emag nr. {order.id}",
                "observations": f"{order.id}_{order.order_market_place.split('.')[1].upper()}",
                "language": order.billing_country,
                "precision": 2,
                "useEstimateDetails": False,
                "estimate": {
                    "seriesName": "",
                    "number": ""
                },
                "currency": currency,
                "issueDate": issueDate.strftime('%Y-%m-%d'),
                "products": products
            }
            
            while starting_time + timedelta(seconds=3) > datetime.now():
                continue
            starting_time = datetime.now()
            
            result = generate_invoice(data, smartbill)
            if result.get('errorText') != '':
                logging.info(f"generate invoice result is {result}")
            
            invoice = Invoice()
            invoice.replacement_id = 0
            invoice.order_id = order.id
            invoice.companyVatCode = smartbill.registration_number
            invoice.seriesName = "EMG" + marketplace.country.upper()
            # invoice.seriesName = "EMGINL"
            invoice.client = str(client)
            invoice.usestock = True
            invoice.isdraft = False
            invoice.issueDate = issueDate
            invoice.mentions = f"Comanda Emag nr. {order.id}"
            invoice.observations = f"{order.id}_{order.order_market_place.split('.')[1].upper()}"
            invoice.language = order.billing_country
            invoice.precision = 2
            invoice.useEstimateDetails = False
            invoice.estimate = str({
                "seriesName": "",
                "number": ""
            })
            invoice.currency = currency
            invoice.products = str(products)
            number = result.get('number') if result.get('number') else ''
            series = result.get('series') if result.get('series') else ''
            invoice.number = number
            invoice.series = series
            invoice.url = result.get('url') if result.get('url') else ''
            invoice.post = 0
            invoice.user_id = user_id
            
            logging.info(f"Invoice data being saved: {invoice.__dict__}")
            # try:
            #     db.add(invoice)
            #     # await db.commit()
            # except Exception as e:
            #     await db.rollback()
            #     logging.error(f"Error saving invoice: {e}")
            db.add(invoice)
            # logging.info(f"order_id_list is {order_id_list}")
            # logging.info(f"successfully generate invoice of {len(order_id_list)}")
            name = f"factura_{series}{number}.pdf"
            download_result = download_pdf_server(series, number, name, smartbill)
            logging.info(f"download pdf result is {download_result}")
            order_id_list.append(order.id)
            post_factura_pdf(order.id, name, marketplace)
    
        except Exception as e:
            logging.error(f"Error in generating invoice: {e}")

    try:
        logging.info("start commit")
        await db.commit()    
        logging.info(f"order_id_list is {order_id_list}")
        logging.info(f"successfully generate invoice of {len(order_id_list)}")
    except Exception as e:
        await db.rollback()
        logging.error(f"Error saving invoice: {e}")
    
async def refresh_storno_invoice(marketplace: Marketplace, db: AsyncSession):
    user_id = marketplace.user_id
    
    result = await db.execute(select(Billing_software).where(Billing_software.user_id == user_id, Billing_software.site_domain == "smartbill.ro"))
    smartbill = result.scalars().first()
    if smartbill is None:
        return
    
    AWBAlias = aliased(AWB)
    Reverse_InvoiceAlias = aliased(Reverse_Invoice)
    
    query = select(Order).outerjoin(
        AWBAlias,
        and_(AWBAlias.order_id == Order.id, AWBAlias.number > 0, AWBAlias.user_id == Order.user_id)
    )
    query.where(or_(Order.status == 5, AWBAlias.awb_status == any_([16, 35, 93])))
    query = query.outerjoin(
        Reverse_InvoiceAlias,
        and_(Reverse_InvoiceAlias.order_id == Order.id, Reverse_InvoiceAlias.user_id == Order.user_id)
    )
    query = query.where(
        not_(
            or_(
                Order.attachments.ilike("%storno%"),
                Reverse_InvoiceAlias.id != None
            )
        )
    )
    result = await db.execute(query)
    orders = result.scalars().all()
    
    starting_time = datetime.now()
    
    order_id_list = []
    for order in orders:
        try:
            attachments = json.loads(order.attachments)
            name = ''
            for attachment in attachments:
                if "factura" in str(attachment).lower():
                    name = attachment.get("name")
                    break
            match = re.search(r"_(\D+)(\d+)\.pdf$", name)
            if match:
                seriesname = match.group(1)
                number = match.group(2)
            else:
                continue
            
            while starting_time + timedelta(seconds=3) > datetime.now():
                continue
            starting_time = datetime.now()
            result = reverse_invoice_smartbill(seriesname, number, smartbill)
            if result.status_code != 200:
                logging.info(f"Failed generating storno invoice of {name}")
            result = result.json()
            if result.get('errorText') != '':
                logging.info(f"Error text of generaing storno inovice of {name} is {result.get('errorText')}")
            
            reverse_invoice = Reverse_Invoice()
            reverse_invoice.replacement_id = 0
            reverse_invoice.order_id = order.id
            reverse_invoice.companyVatCode = smartbill.registration_number
            reverse_invoice.seriesName = seriesname
            reverse_invoice.factura_number = number
            storno_number = result.get('number') if result.get('number') else ''
            reverse_invoice.storno_number = storno_number
            reverse_invoice.post = 0
            reverse_invoice.user_id = order.user_id
            
            logging.info(f"Storno Invoice data being saved: {reverse_invoice.__dict__}")
            db.add(reverse_invoice)
            pdf_name = f"storno_{seriesname}{storno_number}.pdf"
            download_result = download_pdf_server(seriesname, storno_number, pdf_name, smartbill)
            logging.info(f"download pdf result is {download_result}")
            order_id_list.append(order.id)
        except Exception as e:
            logging.error(f"Error in generating reverse invoice of {order.id}: {e}")
    try:
        logging.info("start commit storno invoice")
        await db.commit()
        logging.info(f"order_id_list of storno invoice is {order_id_list}")
        logging.info(f"successfully generate storno invoice of {len(order_id_list)}")
    except Exception as e:
        await db.rollback()
        logging.error(f"Error saving storno invoice: {e}")

def generate_invoice(data, smartbill: Billing_software):
    USERNAME = smartbill.username
    PASSWORD = smartbill.password
    url = "https://ws.smartbill.ro/SBORO/api/invoice"
    credentials = base64.b64encode(f"{USERNAME}:{PASSWORD}".encode()).decode()
    headers = {
        "accept": "application/json",
        "authorization": f"Basic {credentials}",
        "content-type": "application/json"
    }
    data = json.dumps(data)
    response = requests.post(url, headers=headers, data=data)
    return response.json()

def download_pdf(cif: str, seriesname: str, number: str, smartbill: Billing_software):
    USERNAME = smartbill.username
    PASSWORD = smartbill.password
    credentials = base64.b64encode(f"{USERNAME}:{PASSWORD}".encode()).decode()
    url = "https://ws.smartbill.ro/SBORO/api/invoice/pdf"
    headers = {
        "Authorization": f"Basic {credentials}",
        "accept": "application/json",
    }
    
    params = {
        "cif": cif,
        "seriesname": seriesname,
        "number": number
    }
    
    response = requests.get(url, headers=headers, params=params, stream=True)
    
    if response.status_code == 200:
        content = BytesIO(response.content)
        return StreamingResponse(content, media_type=response.headers['Content-Type']) 
    else:
        return response

def download_storno_pdf(cif: str, seriesname: str, number: str, smartbill: Billing_software):
    USERNAME = smartbill.username
    PASSWORD = smartbill.password
    credentials = base64.b64encode(f"{USERNAME}:{PASSWORD}".encode()).decode()
    url = "https://ws.smartbill.ro/SBORO/api/invoice/pdf"
    headers = {
        "Authorization": f"Basic {credentials}",
        "accept": "application/json",
    }
    
    params = {
        "cif": cif,
        "seriesname": seriesname,
        "number": number
    }
    
    response = requests.get(url, headers=headers, params=params, stream=True)
    
    if response.status_code == 200:
        content = BytesIO(response.content)
        return StreamingResponse(content, media_type=response.headers['Content-Type']) 
    else:
        return response

def download_pdf_server(seriesname: str, number: str, name: str, smartbill: Billing_software):
    USERNAME = smartbill.username
    PASSWORD = smartbill.password
    credentials = base64.b64encode(f"{USERNAME}:{PASSWORD}".encode()).decode()
    url = "https://ws.smartbill.ro/SBORO/api/invoice/pdf"
    headers = {
        "Authorization": f"Basic {credentials}",
        "accept": "application/json",
    }
    
    cif = smartbill.registration_number
    
    params = {
        "cif": cif,
        "seriesname": seriesname,
        "number": number
    }
    
    response = requests.get(url, headers=headers, params=params, stream=True)
    
    output_filename = f"/var/www/html/invoices/{name}"
    if response.status_code == 200:
        content = BytesIO(response.content)
        
        with open(output_filename, 'wb') as pdf_file:
            pdf_file.write(content.getvalue())
        return
    else:
        return response

def cancel_invoice_smartbill(cif: str, seriesname: str, number: str, smartbill: Billing_software):
    USERNAME = smartbill.username
    PASSWORD = smartbill.password
    credentials = base64.b64encode(f"{USERNAME}:{PASSWORD}".encode()).decode()
    url = "https://ws.smartbill.ro/SBORO/api/invoice/cancel"
    headers = {
        "Authorization": f"Basic {credentials}",
        "accept": "application/json",
    }
    
    params = {
        "cif": cif,
        "seriesname": seriesname,
        "number": number
    }
    
    response = requests.put(url, headers=headers, params=params)
    
    return response

def reverse_invoice_smartbill(seriesname: str, factura_number: str, smartbill: Billing_software):
    USERNAME = smartbill.username
    PASSWORD = smartbill.password
    credentials = base64.b64encode(f"{USERNAME}:{PASSWORD}".encode()).decode()
    
    today = datetime.today()
    today = today.strftime("%Y-%m-%d")
    
    url = "https://ws.smartbill.ro/SBORO/api/invoice/reverse"
    
    headers = {
        "accept": "application/json",
        "authorization": f"Basic {credentials}",
        "content-type": "application/json"
    }
    
    cif = smartbill.registration_number
    
    data = ({
        "companyVatCode": cif,
        "seriesName": seriesname,
        "number": factura_number,
        "issueDate": today
    })
    logging.info(data)
    response = requests.post(url, headers=headers, json=data)
    
    return response