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
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

PROXIES = {
    'http': 'http://p2p_user:jDkAx4EkAyKw@65.109.7.74:54021',
    'https': 'http://p2p_user:jDkAx4EkAyKw@65.109.7.74:54021',
}

def generate_signature(public_key, private_key, params):

    now = datetime.utcnow()
    day = now.strftime('%d')
    month = now.strftime('%m')
    timestamp = f"{day}{month}"

    string_to_hash = f"{public_key}||{hashlib.sha512(private_key.encode()).hexdigest()}||{params}||{timestamp}"
    hash_result = hashlib.sha512(string_to_hash.encode()).hexdigest().lower()
    signature = f"{timestamp}{hash_result}"
    # signature = timestamp + hash_result
    return signature

def save(MARKETPLACE_API_URL, public_key, private_key, data, order_id):
    params = ""
    url = f"{MARKETPLACE_API_URL}sales/order/{order_id}/awb/generate/"
    signature = generate_signature(public_key, private_key, params)
    headers = {
        'X-Request-Public-Key': public_key,
        'X-Request-Signature': signature
    }

    response = requests.post(url, data=json.dumps(data), headers=headers, verify=False, proxies=PROXIES)
    if response.status_code == 200:
        awb = response.json()
        return awb
    else:
        logging.info(f"Failed to retrieve awbs: {response.status_code}")
        return None

async def save_altex_awb(marketplace: Marketplace, data, order_id, db: AsyncSession):
    PUBLIC_KEY = marketplace.credentials["firstKey"]
    PRIVATE_KEY = marketplace.credentials["secondKey"]

    save(marketplace.baseAPIURL, PUBLIC_KEY, PRIVATE_KEY, data, order_id)
