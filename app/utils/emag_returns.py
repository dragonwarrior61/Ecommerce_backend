from psycopg2 import sql
from app.config import settings
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
from app.database import get_db
from decimal import Decimal

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# PROXIES = {
#     'http': 'http://p2p_user:jDkAx4EkAyKw@65.109.7.74:54021',
#     'https': 'http://p2p_user:jDkAx4EkAyKw@65.109.7.74:54021',
# }

def get_attachments(API_KEY):
    url = 'https://marketplace-api.emag.ro/api-3/product_offer/save'
    api_key = str(API_KEY).replace("b'", '').replace("'", "")
    headers = {
        "Authorization": f"Basic {api_key}",
        "Content-Type": "application/json"
    }
    
    data = json.dumps({
        "itmesPerPage": 100,
        "currentPage": 1
    })

    # response = requests.post(url, data=data, headers=headers, proxies=PROXIES)
    response = requests.post(url, data=data, headers=headers)
    if response.status_code == 200:
        get_attachments = response.json()
        return get_attachments
    else:
        logging.info(f"Failed to retrieve refunds: {response.status_code}")
        return None

def get_all_rmas(MARKETPLACE_API_URL, RMAS_ENDPOINT, READ_ENDPOINT,  API_KEY, currentPage, PUBLIC_KEY=None, usePublicKey=False):
    url = f"{MARKETPLACE_API_URL}{RMAS_ENDPOINT}{READ_ENDPOINT}"
    
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

    data = json.dumps({
        "itmesPerPage": 100,
        "currentPage": currentPage
    })
    # response = requests.post(url, data=data, headers=headers, proxies=PROXIES)
    MAX_RETRIES = 5
    retry_delay = 5  # seconds

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(url, data=data, headers=headers, timeout=20)
            if response.status_code == 200:
                return response.json()
            else:
                logging.info(f"Failed to retrieve refunds: {response.status_code}")
                return None
        except requests.Timeout:
            logging.warning(f"Request timed out. Attempt {attempt + 1} of {MAX_RETRIES}. Retrying...")
            time.sleep(retry_delay)
    logging.error("All attempts failed. Could not retrieve refunds.")
    return None

def get_awb(reservation_id, marketplace: Marketplace):
    baseurl = marketplace.baseAPIURL
    url = f'{baseurl}/awb/read'
    USERNAME = marketplace.credentials["firstKey"]
    PASSWORD = marketplace.credentials["secondKey"]
    API_KEY = base64.b64encode(f"{USERNAME}:{PASSWORD}".encode('utf-8'))
    
    api_key = str(API_KEY).replace("b'", '').replace("'", "")
    headers = {
        "Authorization": f"Basic {api_key}",
        "Content-Type": "application/json"
    }
    
    data = json.dumps({
        "reservation_id": reservation_id
    })
    response = requests.post(url, data=data, headers=headers)
    if response.status_code == 200:
        awb = response.json()
        return awb
    elif response.status_code == 429:
        retry_after = int(response.headers.get("Retry-After", 60))  # Default to 60 seconds if not provided
        logging.info(f"Rate limit exceeded. Retrying after {retry_after} seconds.")
        time.sleep(retry_after)
        return get_awb(reservation_id, marketplace)  # Retry the request
    else:
        logging.info(f"Failed to retrieve refunds: {response.status_code} {reservation_id}")
        return None

def count_all_rmas(MARKETPLACE_API_URL, RMAS_ENDPOINT, COUNT_ENGPOINT, API_KEY):
    logging.info("counting start")
    url = f"{MARKETPLACE_API_URL}{RMAS_ENDPOINT}{COUNT_ENGPOINT}"

    api_key = str(API_KEY).replace("b'", '').replace("'", "")
    headers = {
        "Authorization": f"Basic {api_key}",
        "Content-Type": "application/json"
    }

    # response = requests.post(url, headers=headers, proxies=PROXIES)
    MAX_RETRIES = 5
    retry_delay = 5  # seconds

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, headers=headers, timeout=20)
            if response.status_code == 200:
                return response.json()
            else:
                logging.info(f"Failed to retrieve refunds: {response.status_code}")
                return None
        except requests.Timeout:
            logging.warning(f"Request timed out. Attempt {attempt + 1} of {MAX_RETRIES}. Retrying...")
            time.sleep(retry_delay)
    logging.error("All attempts failed. Could not retrieve refunds.")

async def insert_rmas_into_db(rmas, marketplace: Marketplace):
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
                observations,
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
                awb,
                awb_status,
                user_id
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            ) ON CONFLICT (emag_id, return_market_place) DO UPDATE SET
                return_reason = EXCLUDED.return_reason,
                request_status = EXCLUDED.request_status,
                awb = EXCLUDED.awb,
                products = EXCLUDED.products,
                quantity = EXCLUDED.quantity,
                observations = EXCLUDED.observations,
                awb_status = EXCLUDED.awb_status,
                user_id = EXCLUDED.user_id         
        """).format(sql.Identifier("returns"))

        for rma in rmas:
            try:
                emag_id = rma.get('emag_id') if rma.get('emag_id') else 0
                order_id = rma.get('order_id') if rma.get('order_id') else 0
                type = rma.get('type') if rma.get('type') else 0
                customer_name = rma.get('customer_name') if rma.get('customer_name') else ""
                customer_company = rma.get('customer_company') if rma.get('customer_company') else ""
                customer_phone = rma.get('customer_phone') if rma.get('customer_phone') else ""
                products = [str(product.get('product_id')) if product.get('product_id') else 0 for product in rma.get('products')]
                quantity = [int(product.get('quantity')) if product.get('quantity') else 0 for product in rma.get('products')]
                observations = [str(product.get('observations')) if product.get('observations') else "" for product in rma.get('products')]
                pickup_address = rma.get('pickup_address') if rma.get('pickup_address') else ""
                return_reason = str(rma.get('return_reason')) if rma.get('return_reason') else ""
                return_type = rma.get('return_type') if rma.get('return_type') else 0
                replacement_product_emag_id = rma.get('replacement_product_emag_id') if rma.get('replacement_product_emag_id') else 0
                replacement_product_id = rma.get('replacement_product_id') if rma.get('replacement_product_id') else 0
                replacement_product_name = rma.get('replacement_product_name') if rma.get('replacement_product_name') else ""
                replacement_product_quantity = rma.get('replacement_product_quantity') if rma.get('replacement_product_quantity') else 0
                date = rma.get('date') if rma.get('date') else ""
                request_status = rma.get('request_status') if rma.get('request_status') else 0
                return_market_place = marketplace.marketplaceDomain
                awbs = rma.get('awbs')
                if awbs and len(awbs) > 0:
                    reservation_id = awbs[0].get('reservation_id') if awbs[0] else ''
                    if reservation_id:
                        response = get_awb(reservation_id, marketplace)
                        if response is None:
                            awb = ""
                        else:
                            awb = response.get('results').get('awb')[0].get('awb_number') if response.get('results').get('awb') and len(response.get('results').get('awb')) > 0 else ""
                            awb_status = str(response.get('results').get('status')) if response.get('results').get('status') else ""
                    else:
                        awb = ""
                else:
                    awb = ""
                user_id = marketplace.user_id

                value = (
                    emag_id,
                    order_id,
                    type,
                    customer_name,
                    customer_company,
                    customer_phone,
                    products,
                    quantity,
                    observations,
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
                    awb,
                    awb_status,
                    user_id
                )
                cursor.execute(insert_query, value)
            except Exception as inner_error:
                logging.error(f"Failed to insert RMA with emag_id {rma}: {inner_error}")
                continue
        conn.commit()
        cursor.close()
        conn.close()
        logging.info("Refunds inserted successfully")
    except Exception as e:
        logging.info(f"Failed to insert refunds into database: {e}")

async def refresh_emag_returns(marketplace: Marketplace):
    # create_database()
    logging.info(f">>>>>>> Refreshing Marketplace : {marketplace.title} user is {marketplace.user_id} <<<<<<<<")

    user_id = marketplace.user_id
    USERNAME = marketplace.credentials["firstKey"]
    PASSWORD = marketplace.credentials["secondKey"]
    API_KEY = base64.b64encode(f"{USERNAME}:{PASSWORD}".encode('utf-8'))
    
    baseAPIURL = marketplace.baseAPIURL
    endpoint = "/rma"
    read_endpoint = "/read"
    count_endpoint = "/count"

    result = count_all_rmas(baseAPIURL, endpoint, count_endpoint, API_KEY)
    if result:
        pages = result['results']['noOfPages']
        items = result['results']['noOfItems']
        logging.info(f"------------pages--------------{pages}")
        logging.info(f"------------items--------------{items}")
    try:
        current_page  = 1
        while current_page <= int(pages):
            rmas = get_all_rmas(baseAPIURL, endpoint, read_endpoint, API_KEY, current_page)
            logging.info(f">>>>>>> Current Page : {current_page} <<<<<<<<")
            await insert_rmas_into_db(rmas['results'], marketplace)
            current_page += 1
    except Exception as e:
        print('++++++++++++++++++++++++++++++++++++++++++')
        print(e)