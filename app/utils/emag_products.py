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
import asyncio
import os
import time
import logging
from app.models.marketplace import Marketplace
from app.models.user import User
from app.models.internal_product import Internal_Product
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from app.database import get_db
from app.routers.auth import get_current_user
from decimal import Decimal
import httpx
import time
import threading

lock = threading.Lock()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def change_string(ean_str):
    if len(ean_str) == 12:
        return '0' + ean_str
    else:
        return ean_str

def count_all_products(MARKETPLACE_API_URL, PRODUCTS_ENDPOINT, COUNT_ENGPOINT, API_KEY, PUBLIC_KEY=None, usePublicKey=False):
    logging.info("counting start")
    url = f"{MARKETPLACE_API_URL}{PRODUCTS_ENDPOINT}/{COUNT_ENGPOINT}"
    if usePublicKey is False:
        api_key = str(API_KEY).replace("b'", '').replace("'", "")
        headers = {
            "Authorization": f"Basic {api_key}",
            "Content-Type": "application/json"
        }
    else:
        headers = {
            "X-Request-Public-Key": f"{PUBLIC_KEY}",
            "X-Request-Signature": f"{API_KEY}"
        }

    MAX_RETRIES = 5
    retry_delay = 5  # seconds

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, headers=headers, timeout=20)
            if response.status_code == 200:
                return response.json()
            else:
                logging.info(f"Failed to retrieve products: {response.status_code}")
                return None
        except requests.Timeout:
            logging.warning(f"Request timed out. Attempt {attempt + 1} of {MAX_RETRIES}. Retrying...")
            time.sleep(retry_delay)
    logging.error("All attempts failed. Could not retrieve products.")
    return None
    
def get_all_products(MARKETPLACE_API_URL, PRODUCTS_ENDPOINT, READ_ENDPOINT,  API_KEY, currentPage, PUBLIC_KEY=None, usePublicKey=False):
    url = f"{MARKETPLACE_API_URL}{PRODUCTS_ENDPOINT}/{READ_ENDPOINT}"
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
        "itemsPerPage": 100,
        "currentPage": currentPage,
    })
    MAX_RETRIES = 5
    retry_delay = 5  # seconds

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(url, data=data, headers=headers, timeout=20)
            if response.status_code == 200:
                return response.json()
            else:
                logging.info(f"Failed to retrieve products: {response.status_code}")
                return None
        except requests.Timeout:
            logging.warning(f"Request timed out. Attempt {attempt + 1} of {MAX_RETRIES}. Retrying...")
            time.sleep(retry_delay)
    logging.error("All attempts failed. Could not retrieve products.")
    return None

async def insert_products(products, mp_name: str, user_id):
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
                part_number_key,
                product_code,
                product_name,
                model_name,
                buy_button_rank,
                price,
                sale_price,
                ean,
                image_link,
                barcode_title,
                masterbox_title,
                link_address_1688,
                price_1688,
                variation_name_1688,
                pcs_ctn,
                weight,
                volumetric_weight,
                dimensions,
                supplier_id,
                english_name,
                romanian_name,
                material_name_en,
                material_name_ro,
                hs_code,
                battery,
                default_usage,
                production_time,
                discontinued,
                stock,
                smartbill_stock,
                orders_stock,
                damaged_goods, 
                warehouse_id,
                internal_shipping_price,
                market_place,
                sync_stock_time,
                user_id
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            ) ON CONFLICT (ean) DO UPDATE SET
                id = EXCLUDED.id,
                buy_button_rank = EXCLUDED.buy_button_rank,
                stock = EXCLUDED.stock,
                market_place = array(SELECT DISTINCT unnest(array_cat(EXCLUDED.market_place, internal_products.market_place))),
                user_id = EXCLUDED.user_id
        """).format(sql.Identifier("internal_products"))

        for product in products:
            id = product.get('id')
            part_number_key = product.get('part_number_key')
            product_code = ""
            product_name = product.get('name')
            model_name = product.get('brand')
            buy_button_rank = product.get('buy_button_rank')
            price = 0
            sale_price = Decimal(product.get('sale_price', '0.0'))
            ean = str(product.get('ean')[0]) if product.get('ean') else None
            ean = change_string(ean)
            image_link = product.get('images')[0]['url'] if product.get('images') else None
            barcode_title = ""
            masterbox_title = ""
            link_address_1688 = ""
            price_1688 = Decimal('0')
            variation_name_1688 = ""
            pcs_ctn = ""
            weight_value = product.get('weight')
            if isinstance(weight_value, str):
                weight_value = weight_value.replace(',', '.')  # Handle any comma as decimal separator
            weight = Decimal(weight_value) if weight_value else Decimal('0')
            volumetric_weight = 0
            dimensions = ""
            supplier_id = 0
            english_name = ""
            romanian_name = ""
            material_name_en = ""
            material_name_ro = ""
            hs_code = ""
            battery = False
            default_usage = ""
            production_time = Decimal('0')
            discontinued = False
            stock = int(product.get('stock')[0].get('value') if product.get('stock') else 0)
            smartbill_stock = 0
            orders_stock = 0
            damaged_goods = 0
            warehouse_id = 0
            internal_shipping_price = Decimal('0')
            market_place = [mp_name]  # Ensure this is an array to use array_cat
            sync_stock_time = None
            user_id = user_id

            values = (
                id,
                part_number_key,
                product_code,
                product_name,
                model_name,
                buy_button_rank,
                price,
                sale_price,
                ean,
                image_link,
                barcode_title,
                masterbox_title,
                link_address_1688,
                price_1688,
                variation_name_1688,
                pcs_ctn,
                weight,
                volumetric_weight,
                dimensions,
                supplier_id,
                english_name,
                romanian_name,
                material_name_en,
                material_name_ro,
                hs_code,
                battery,
                default_usage,
                production_time,
                discontinued,
                stock,
                smartbill_stock,
                orders_stock,
                damaged_goods,
                warehouse_id,
                internal_shipping_price,
                market_place,
                sync_stock_time,
                user_id
            )
            cursor.execute(insert_query, values)
            conn.commit()
        
        cursor.close()
        conn.close()
        logging.info("Internal_Products inserted into Products successfully")
    except Exception as e:
        logging.info(f"Failed to insert Internal_Products into database: {e}")

async def insert_products_into_db(products, place, user_id):
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
                part_number_key,
                product_name,
                model_name,
                buy_button_rank,
                price,
                sale_price,
                sku,
                ean,
                image_link,
                barcode_title,
                masterbox_title,
                link_address_1688,
                price_1688,
                variation_name_1688,
                pcs_ctn,
                weight,
                volumetric_weight,
                dimensions,
                supplier_id,
                english_name,
                romanian_name,
                material_name_en,
                material_name_ro,
                hs_code,
                battery,
                default_usage,
                production_time,
                discontinued,
                stock,
                warehouse_id,
                internal_shipping_price,
                product_marketplace,
                user_id
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            ) ON CONFLICT (ean, product_marketplace) DO UPDATE SET
                id = EXCLUDED.id,
                sale_price = EXCLUDED.sale_price,
                stock = EXCLUDED.stock,
                user_id = EXCLUDED.user_id
        """).format(sql.Identifier("products"))

        for product in products:
            id = str(product.get('id'))
            part_number_key = product.get('part_number_key')
            product_name = product.get('name')
            model_name = product.get('brand')
            buy_button_rank = product.get('buy_button_rank')
            price = 0
            sale_price = Decimal(product.get('sale_price', '0.0'))
            sku = ""
            ean = str(product.get('ean')[0]) if product.get('ean') else None
            ean = change_string(ean)
            image_link = product.get('images')[0]['url'] if product.get('images') else None
            barcode_title = ""
            masterbox_title = ""
            link_address_1688 = ""
            price_1688 = Decimal('0')
            variation_name_1688 = ""
            pcs_ctn = ""
            weight_value = product.get('weight')
            if isinstance(weight_value, str):
                weight_value = weight_value.replace(',', '.')  # Handle any comma as decimal separator
            weight = Decimal(weight_value) if weight_value else Decimal('0')
            volumetric_weight = 0
            dimensions = ""
            supplier_id = 0
            english_name = ""
            romanian_name = ""
            material_name_en = ""
            material_name_ro = ""
            hs_code = ""
            battery = False
            default_usage = ""
            production_time = Decimal('0')
            discontinued = False
            stock = int(product.get('stock')[0].get('value') if product.get('stock') else 0)
            warehouse_id = 0
            internal_shipping_price = Decimal('0')
            product_marketplace = place  # Ensure this is an array to use array_cat
            user_id = user_id

            values = (
                id,
                part_number_key,
                product_name,
                model_name,
                buy_button_rank,
                price,
                sale_price,
                sku,
                ean,
                image_link,
                barcode_title,
                masterbox_title,
                link_address_1688,
                price_1688,
                variation_name_1688,
                pcs_ctn,
                weight,
                volumetric_weight,
                dimensions,
                supplier_id,
                english_name,
                romanian_name,
                material_name_en,
                material_name_ro,
                hs_code,
                battery,
                default_usage,
                production_time,
                discontinued,
                stock,
                warehouse_id,
                internal_shipping_price,
                product_marketplace,
                user_id
            )
            cursor.execute(insert_query, values)
            conn.commit()
        cursor.close()
        conn.close()
        logging.info("Products inserted successfully")
    except Exception as e:
        logging.info(f"Failed to insert products into database: {e}")

async def refresh_emag_products(marketplace: Marketplace):
    # create_database()
    logging.info(f">>>>>>> Refreshing Marketplace : {marketplace.title} user is {marketplace.user_id} <<<<<<<<")

    endpoint = "/product_offer"
    count_point = "/count"
    read_endpoint = "/read"
    user_id = marketplace.user_id
    USERNAME = marketplace.credentials["firstKey"]
    PASSWORD = marketplace.credentials["secondKey"]
    API_KEY = base64.b64encode(f"{USERNAME}:{PASSWORD}".encode('utf-8'))
    result = count_all_products(marketplace.baseAPIURL, endpoint, count_point, API_KEY)
    logging.info(f"count result is {result}")
    if result:
        pages = result['results']['noOfPages']
        items = result['results']['noOfItems']

        logging.info(f"------------pages--------------{pages}")
        logging.info(f"------------items--------------{items}")
        currentPage = 1
        baseAPIURL = marketplace.baseAPIURL
        try:
            while currentPage <= int(pages):
                products = get_all_products(baseAPIURL, endpoint, read_endpoint, API_KEY, currentPage)

                logging.info(f">>>>>>> Current Page : {currentPage} <<<<<<<<")
                if products and not products.get('isError'):
                    await insert_products_into_db(products['results'], marketplace.marketplaceDomain, user_id)
                    await asyncio.sleep(2)
                    await insert_products(products['results'], marketplace.marketplaceDomain, user_id)
                currentPage += 1
        except Exception as e:
            print('++++++++++++++++++++++++++++++++++++++++++')
            print(e)

def save(MARKETPLACE_API_URL, ENDPOINT, save_ENDPOINT,  API_KEY, data, PUBLIC_KEY=None, usePublicKey=False):
    url = f"{MARKETPLACE_API_URL}{ENDPOINT}/{save_ENDPOINT}"
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

    response = requests.post(url, data=json.dumps(data), headers=headers)
    if response.status_code == 200:
        products = response.json()
        return products
    else:
        logging.info(f"Failed to retrieve products: {response.status_code}")
        return None

async def save_product(data, marketplace:Marketplace, db: AsyncSession):
    if marketplace.credentials["type"] == "user_pass":
        USERNAME = marketplace.credentials["firstKey"]
        PASSWORD = marketplace.credentials["secondKey"]
        API_KEY = base64.b64encode(f"{USERNAME}:{PASSWORD}".encode('utf-8'))
        endpoint = marketplace.products_crud['endpoint']
        savepoint = marketplace.products_crud['savepoint']
        result = save(marketplace.baseAPIURL, endpoint, savepoint, API_KEY, data)

    return result

async def post_stock_emag(marketplace: Marketplace, product_id: int, stock: int):
    USERNAME = marketplace.credentials["firstKey"]
    PASSWORD = marketplace.credentials["secondKey"]
    API_KEY = base64.b64encode(f"{USERNAME}:{PASSWORD}".encode('utf-8'))
    url = f"{marketplace.baseAPIURL}/offer_stock"
    api_key = str(API_KEY).replace("b'", '').replace("'", "")
    headers = {
        "Authorization": f"Basic {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "stock": stock
    }
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.patch(f"{url}/{product_id}", json=data, headers=headers)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 204:
            return "Stock updated successfully, no content returned."
        elif response.status_code == 404:
            return f"Product not found: {response.status_code} {response.text}"
        else:
            try:
                return f"Failed to update stock: {response.status_code} {response.json()}"
            except Exception:
                return f"Failed to update stock: {response.status_code} {response.text}"