import requests
import psycopg2
import base64
import hashlib
import json
import os
from app.config import settings
from psycopg2 import sql
from urllib.parse import urlparse
from app.models.marketplace import Marketplace
from app.models.orders import Order
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any

from sqlalchemy.exc import IntegrityError
import logging
from sqlalchemy import insert
from sqlalchemy.dialects.postgresql import insert as pg_insert
from datetime import datetime
from decimal import Decimal
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


MARKETPLACE_URL = 'https://marketplace.emag.ro/'
MARKETPLACE_API_URL = 'https://marketplace-api.emag.ro/api-3'
ORDERS_ENDPOINT = "/order"

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

def get_rmas(url, public_key, private_key, page_nr):

    params = f"page_nr={page_nr}"
    url = f"{url}sales/rma/?{params}"
    signature = generate_signature(public_key, private_key, params)
    headers = {
        'X-Request-Public-Key': public_key,
        'X-Request-Signature': signature
    }
    response = requests.get(url, headers=headers, verify=False, proxies=PROXIES)
    return response.json()

def get_detail_rma(url, public_key, private_key, order_id):
    params = ""
    url = f"{url}sales/rms/{order_id}/"
    signature = generate_signature(public_key, private_key, params)
    headers = {
        'X-Request-Public-Key': public_key,
        'X-Request-Signature': signature
    }
    response = requests.get(url, headers=headers, verify=False, proxies=PROXIES)
    return response.json()

async def insert_rmas(rmas, place:str, user_id):
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
                emag_id,
                order_id,
                type,
                customer_name,
                customer_company,
                customer_phone,
                products,
                quantity,
                pickup_address,
                return_reason,
                return_type,
                replacement_product_emag_id,
                replacement_product_id,
                replacement_product_name,
                replacement_product_quantity,
                date,
                request_status,
                return_market_place,
                user_id
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            ) ON CONFLICT (eamg_id, return_market_place) DO UPDATE SET
                return_reason = EXCLUDED.return_reason,
                request_status = EXCLUDED.request_status               
        """).format(sql.Identifier("returns"))

        for rma in rmas:
            emag_id = ""
            order_id = rma.get('order_id')
            type = ""
            customer_name = rma.get('customer_name')
            customer_company = ""
            customer_phone = rma.get('customer_phone_number')
            products = [str(product.get('product_id')) for product in rma.get('products')]
            quantity = [1 for product in rma.get('products')]
            pickup_address = ""
            return_reason = ""
            return_type = ""
            replacement_product_emag_id = ""
            replacement_product_id = ""
            replacement_product_name = ""
            replacement_product_quantity = ""
            date = rma.get('created_date')
            request_status = ""
            return_market_place = place
            user_id = user_id

            value = (
                emag_id,
                order_id,
                type,
                customer_name,
                customer_company,
                customer_phone,
                products,
                quantity,
                pickup_address,
                return_reason,
                return_type,
                replacement_product_emag_id,
                replacement_product_id,
                replacement_product_name,
                replacement_product_quantity,
                date,
                request_status,
                return_market_place,
                user_id
            )
            cursor.execute(insert_query, value)
            conn.commit()
        cursor.close()
        conn.close()
        logging.info("Refunds inserted successfully")
    except Exception as e:
        logging.info(f"Failed to insert refunds into database: {e}")

async def refresh_altex_rmas(marketplace: Marketplace):
    # create_database()
    logging.info(f">>>>>>> Refreshing Marketplace : {marketplace.title} user is {marketplace.user_id} <<<<<<<<")

    user_id = marketplace.user_id
    PUBLIC_KEY = marketplace.credentials["firstKey"]
    PRIVATE_KEY = marketplace.credentials["secondKey"]

    page_nr = 1
    while True:
        try:
            result = get_rmas(marketplace.baseAPIURL, PUBLIC_KEY, PRIVATE_KEY, page_nr)
            if result['status'] == 'error':
                break
            data = result['data']
            rmas = data.get('items')
            detail_rmas = []
            for rma in rmas:
                if rma.get('rma_id') is not None:
                    rma_id = rma.get('rma_id')
                    detail_rma_result = get_detail_rma(marketplace.baseAPIURL, PUBLIC_KEY, PRIVATE_KEY, rma_id)
                    if detail_rma_result.get('status') == 'success':
                        detail_rmas.append(detail_rma_result.get('data'))

            await insert_rmas(detail_rmas, marketplace.marketplaceDomain, user_id)
            page_nr += 1
        except Exception as e:
            logging.error(f"Exception occurred: {e}")
            break