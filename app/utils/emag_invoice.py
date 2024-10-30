from psycopg2 import sql
from urllib.parse import urlparse
from app.config import settings
from fastapi import Depends
import requests
import psycopg2
import base64
import urllib
import hashlib
import json
import os
import time
import logging
from app.models.marketplace import Marketplace
from sqlalchemy.dialects.postgresql import insert
from app.utils.emag_orders import change_status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from app.database import get_db
from decimal import Decimal

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def post_pdf(order_id: int, name: str, marketplace: Marketplace):
    MARKETPLACE_API_URL = marketplace.baseAPIURL
    url = f"{MARKETPLACE_API_URL}/order/attachments/save"
    USERNAME = marketplace.credentials["firstKey"]
    PASSWORD = marketplace.credentials["secondKey"]
    API_KEY = base64.b64encode(f"{USERNAME}:{PASSWORD}".encode('utf-8'))
    
    api_key = str(API_KEY).replace("b'", '').replace("'", "")
    headers = {
        "Authorization": f"Basic {api_key}",
        "Content-Type": "application/json"
    }

    pdf_url = f"https://seller.upsourcing.net/invoices/{name}"
    
    data = [{
        "order_id": order_id,
        "name": name,
        "url": pdf_url,
        "type": 1,
        "force_download": 1
    }]
    result = change_status(order_id, marketplace)
    response = requests.post(url, data=json.dumps(data), headers=headers)
    return response
    
def post_factura_pdf(order_id: int, name: str, marketplace: Marketplace):
    MARKETPLACE_API_URL = marketplace.baseAPIURL
    url = f"{MARKETPLACE_API_URL}/order/attachments/save"
    USERNAME = marketplace.credentials["firstKey"]
    PASSWORD = marketplace.credentials["secondKey"]
    API_KEY = base64.b64encode(f"{USERNAME}:{PASSWORD}".encode('utf-8'))
    
    api_key = str(API_KEY).replace("b'", '').replace("'", "")
    headers = {
        "Authorization": f"Basic {api_key}",
        "Content-Type": "application/json"
    }

    pdf_url = f"https://seller.upsourcing.net/invoices/{name}"
    
    data = [{
        "order_id": order_id,
        "name": name,
        "url": pdf_url,
        "type": 1,
        "force_download": 1
    }]
    response = requests.post(url, data=json.dumps(data), headers=headers)
    return response
