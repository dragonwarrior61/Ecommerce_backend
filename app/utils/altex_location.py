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

async def insert_locations(locations, place, user_id):
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
                id,
                name,
                name_latin,
                region1,
                region2,
                region3,
                region1_latin,
                region2_latin,
                region3_latin,
                geoid,
                modified,
                zipcode,
                country_code,
                localtity_marketplace,
                user_id
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            ) ON CONFLICT (id, localtity_marketplace) DO UPDATE SET
                name = EXCLUDED.name,
                name_latin = EXCLUDED.name_latin               
        """).format(sql.Identifier("localities"))

        for locality in locations:
            id = locality.get('courier_location_id')
            name = locality.get('courier')
            name_latin = ""
            region1 = locality.get('address')
            region2 = ""
            region3 = ""
            region1_latin = ""
            region2_latin = ""
            region3_latin = ""
            geoid = locality.get('courier_id')
            modified = None
            zipcode = ""
            country_code = ""
            localtity_marketplace = place
            user_id = user_id

            value = (
                id,
                name,
                name_latin,
                region1,
                region2,
                region3,
                region1_latin,
                region2_latin,
                region3_latin,
                geoid,
                modified,
                zipcode,
                country_code,
                localtity_marketplace,
                user_id
            )

            cursor.execute(insert_query, value)
        while settings.update_flag == 1:
            continue
        conn.commit()
        cursor.close()
        conn.close()
        print("Localities inserted successfully")
    except Exception as e:
        print(f"Failed to insert localities into database: {e}")

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

def get_locations(url, public_key, private_key, page_nr):

    params = f"page_nr={page_nr}"
    url = f"{url}sales/location/?{params}"
    signature = generate_signature(public_key, private_key, params)
    headers = {
        'X-Request-Public-Key': public_key,
        'X-Request-Signature': signature
    }
    response = requests.get(url, headers=headers, verify=False, proxies=PROXIES)
    return response.json()

async def refresh_altex_locations(marketplace: Marketplace):
    # create_database()
    logging.info(f">>>>>>> Refreshing Marketplace : {marketplace.title} user is {marketplace.user_id} <<<<<<<<")

    user_id = marketplace.user_id
    PUBLIC_KEY = marketplace.credentials["firstKey"]
    PRIVATE_KEY = marketplace.credentials["secondKey"]

    page_nr = 1
    while True:
        try:
            result = get_locations(marketplace.baseAPIURL, PUBLIC_KEY, PRIVATE_KEY, page_nr)
            if result['status'] == 'error':
                break
            data = result['data']
            locations = data.get("items")

            await insert_locations(locations, marketplace.marketplaceDomain, user_id)
            page_nr += 1
        except Exception as e:
            logging.error(f"Exception occurred: {e}")
            break