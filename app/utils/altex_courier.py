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

# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
PROXIES = {
    'http': 'http://p2p_user:jDkAx4EkAyKw@65.109.7.74:54021',
    'https': 'http://p2p_user:jDkAx4EkAyKw@65.109.7.74:54021',
}

async def insert_couriers(couriers, place, user_id):
    try:
        conn = psycopg2.connect(
            dbname=settings.DB_NAME,
            user=settings.DB_USERNAME,
            password=settings.DB_PASSOWRD,
            host=settings.DB_URL,
            port=settings.DB_PORT
        )
        cursor = conn.cursor()
        insert_query = sql.SQL("""
            INSERT INTO {} (
                account_id,
                account_display_name,
                courier_account_type,
                courier_name,
                courier_account_properties,
                created,
                status,
                market_place,
                user_id
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s
            ) ON CONFLICT (account_id, market_place) DO UPDATE SET
                account_display_name = EXCLUDED.account_display_name,
                courier_account_type = EXCLUDED.courier_account_type
        """).format(sql.Identifier("couriers"))

        for courier in couriers:
            account_id = courier.get('id')
            account_display_name = courier.get('name')
            courier_account_type = 0
            courier_name = ""
            courier_account_properties = ""
            created = None
            status = 0
            market_place = place
            user_id = user_id

            value = (
                account_id,
                account_display_name,
                courier_account_type,
                courier_name,
                courier_account_properties,
                created,
                status,
                market_place,
                user_id
            )

            print(value)
            cursor.execute(insert_query, value)
        
        conn.commit()
        cursor.close()
        conn.close()
        print("Couriers inserted successfully")
    except Exception as e:
        print(f"Failed to insert couriers into database: {e}")

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

def get_couriers(url, public_key, private_key, page_nr):

    params = f"page_nr={page_nr}"
    url = f"{url}sales/courier/?{params}"
    signature = generate_signature(public_key, private_key, params)
    headers = {
        'X-Request-Public-Key': public_key,
        'X-Request-Signature': signature
    }
    response = requests.get(url, headers=headers, verify=False, proxies=PROXIES)
    return response.json()

async def refresh_altex_couriers(marketplace: Marketplace):
    # create_database()
    logging.info(f">>>>>>> Refreshing Marketplace : {marketplace.title} user is {marketplace.user_id} <<<<<<<<")
    user_id = marketplace.user_id
    PUBLIC_KEY = marketplace.credentials["firstKey"]
    PRIVATE_KEY = marketplace.credentials["secondKey"]

    page_nr = 1
    while True:
        try:
            result = get_couriers(marketplace.baseAPIURL, PUBLIC_KEY, PRIVATE_KEY, page_nr)
            if result['status'] == 'error':
                break
            data = result['data']
            couriers = data.get("items")

            await insert_couriers(couriers, marketplace.marketplaceDomain, user_id)
            page_nr += 1
        except Exception as e:
            logging.error(f"Exception occurred: {e}")
            break