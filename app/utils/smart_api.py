from psycopg2 import sql
from urllib.parse import urlparse
from app.config import settings
from fastapi import Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.internal_product import Internal_Product
from app.models.billing_software import Billing_software
from app.models.marketplace import Marketplace
from sqlalchemy import select
import requests
from io import BytesIO
from requests.auth import HTTPBasicAuth
import base64
import json
import logging
from datetime import datetime

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
    logging.info(data)
    response = requests.post(url, headers=headers, data=data)
    logging.info(response.json())
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
    
    output_filename = f"/var/www/html/factura_{seriesname}{number}.pdf"
    if response.status_code == 200:
        content = BytesIO(response.content)
        
        with open(output_filename, 'wb') as pdf_file:
            pdf_file.write(content.getvalue())
            
        logging.info(f"PDF saved as {output_filename}")
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
    
    output_filename = f"/var/www/html/storno_{seriesname}{number}.pdf"
    if response.status_code == 200:
        # content = BytesIO(response.content)
        
        with open(output_filename, 'wb') as pdf_file:
            pdf_file.write(response.content)
            
        logging.info(f"PDF saved as {output_filename}")
        return StreamingResponse(BytesIO(response.content), media_type=response.headers['Content-Type']) 
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