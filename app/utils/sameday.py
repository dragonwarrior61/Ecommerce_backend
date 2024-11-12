from psycopg2 import sql
from urllib.parse import urlparse
from app.config import settings
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.internal_product import Internal_Product
from app.models.billing_software import Billing_software
from sqlalchemy import select
import requests
from requests.auth import HTTPBasicAuth
import base64
import json
import logging
from datetime import datetime
import httpx

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# PROXIES = {
#     'http://': 'http://14a20bb3efda4:d69e723f2d@168.158.127.74:12323',
#     'https://': 'http://14a20bb3efda4:d69e723f2d@168.158.127.74:12323',
# }

async def auth_sameday(sameday: Billing_software):
    USERNAME = sameday.username
    PASSWORD = sameday.password
    auth_url = "https://api.sameday.ro/api/authenticate"
    headers = {
        "X-Auth-Username": f"{USERNAME}",
        "X-Auth-Password": f"{PASSWORD}",
    }
    
    async with httpx.AsyncClient(timeout=20) as client:
        auth_response = await client.post(auth_url, headers=headers)
        result = auth_response.json()
        return result.get('token')

async def tracking(sameday: Billing_software, awb_barcode):
    url = "https://api.sameday.ro/api/client/parcel"
    api_key = sameday.registration_number
    
    async with httpx.AsyncClient(timeout=20) as client:
        tracking_headers = {
            "X-Auth-TOKEN": api_key,
        }
        response = await client.get(f"{url}/{awb_barcode}/status-history", headers=tracking_headers)
        
        if response.status_code == 200:
            result = response.json()
            return result
        else:
            print("Status Code:", response.status_code)
            print("Error:", response.json())