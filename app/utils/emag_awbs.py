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
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from app.database import get_db
from decimal import Decimal

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def convert_decimal_to_float(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

def save(MARKETPLACE_API_URL, awb_ENDPOINT, save_ENDPOINT,  API_KEY, data, PUBLIC_KEY=None, usePublicKey=False):
    url = f"{MARKETPLACE_API_URL}{awb_ENDPOINT}/{save_ENDPOINT}"
    if usePublicKey is True:
        headers = {
            "X-Request-Public-Key": f"{PUBLIC_KEY}",
            "X-Request-Signature": f"{API_KEY}"
        }
    elif usePublicKey is False:
        api_key = str(API_KEY).replace("b'", '').replace("'", "")
        headers = {
            "Authorization": f"Basic {api_key}",
            "Content-Type": "application/json"
        }
    MAX_RETRIES = 5
    retry_delay = 5
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(url, data=json.dumps(data, default=convert_decimal_to_float), headers=headers, timeout=20)
            if response.status_code == 200:
                return response
            else:
                logging.info(f"Failed to awb generate: {response.status_code}")
                return response
        except requests.Timeout:
            logging.warning(f"Request timed out. Attempt {attempt + 1} of {MAX_RETRIES}. Retrying...")
            time.sleep(retry_delay)
    logging.error("All attempts failed. Could not generate this awb.")
    return None

async def save_awb(marketplace: Marketplace, data, db: AsyncSession):
    if marketplace.credentials["type"] == "user_pass":
        
        USERNAME = marketplace.credentials["firstKey"]
        PASSWORD = marketplace.credentials["secondKey"]
        API_KEY = base64.b64encode(f"{USERNAME}:{PASSWORD}".encode('utf-8'))
        result = save(marketplace.baseAPIURL, "/awb", "/save", API_KEY, data)
        print(result)
        return result
