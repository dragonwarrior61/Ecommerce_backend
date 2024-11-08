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

def change_string(ean_str):
    if len(ean_str) == 12:
        return '0' + ean_str
    else:
        return ean_str

async def insert_products(products, offers, mp_name, user_id):
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
                user_id
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            ) ON CONFLICT (ean) DO UPDATE SET
                buy_button_rank = EXCLUDED.buy_button_rank,
                market_place = array(SELECT DISTINCT unnest(array_cat(EXCLUDED.market_place, internal_products.market_place))),
                user_id = EXCLUDED.user_id
        """).format(sql.Identifier("internal_products"))

        for i in range(len(products)):
            product = products[i]
            offer = offers[i]
            id = 0
            part_number_key = ""
            product_code = ""
            product_name = product.get('name')
            model_name = product.get('brand')
            buy_button_rank = 1
            price = 0
            sale_price = offer.get('price')
            ean = str(product.get('ean')[0]) if product.get('ean') else None
            ean = change_string(ean)
            image_link = ""
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
            stock = offer.get('stock')[0].get('quantity') if offer.get('stock') else None
            smartbill_stock = 0
            orders_stock = 0
            damaged_goods = 0
            warehouse_id = 0
            internal_shipping_price = Decimal('0')
            market_place = [mp_name]  # Ensure this is an array to use array_cat
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
                user_id
            )
            
            cursor.execute(insert_query, values)
            
        conn.commit()
        cursor.close()
        conn.close()
        logging.info("Internal_Products inserted into table successfully")
    except Exception as e:
        logging.info(f"Failed to insert Internal_Products into database: {e}")

async def insert_products_into_db(products, offers, place, user_id):
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
                sale_price = EXCLUDED.sale_price,
                barcode_title = EXCLUDED.barcode_title,
                stock = EXCLUDED.stock
        """).format(sql.Identifier("products"))

        for i in range(len(products)):
            product = products[i]
            offer = offers[i]
            if product.get('id') != offer.get('product_id'):
                continue
            id = str(product.get('id'))
            part_number_key = ""
            product_name = product.get('name')
            model_name = product.get('brand')
            buy_button_rank = 1
            price = 0
            sale_price = offer.get('price')
            sku = product.get('sku')
            ean = str(product.get('ean')[0]) if product.get('ean') else None
            ean = change_string(ean)
            image_link = product.get('images')[0]['url'] if product.get('images') else None
            barcode_title =  str(offer.get('id'))
            masterbox_title = ""
            link_address_1688 = ""
            price_1688 = Decimal('0')
            variation_name_1688 = ""
            pcs_ctn = ""
            weight = 0
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
            stock = offer.get('stock')[0].get('quantity') if offer.get('stock') else None
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
        
        while settings.update_flag == 1:
            continue
        conn.commit()
        
        cursor.close()
        conn.close()
        logging.info("Products inserted successfully")
    except Exception as e:
        logging.info(f"Failed to insert products into database: {e}")

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

def get_products(url, public_key, private_key, page_nr):

    params = f"page_nr={page_nr}"
    url = f"{url}catalog/product/?{params}"
    signature = generate_signature(public_key, private_key, params)
    headers = {
        'X-Request-Public-Key': public_key,
        'X-Request-Signature': signature
    }
    response = requests.get(url, headers=headers, verify=False, proxies=PROXIES)
    return response.json()

def get_offers(url, public_key, private_key, page_nr):

    params = f"page_nr={page_nr}"
    url = f"{url}catalog/offer/?{params}"
    signature = generate_signature(public_key, private_key, params)
    headers = {
        'X-Request-Public-Key': public_key,
        'X-Request-Signature': signature
    }
    response = requests.get(url, headers=headers, verify=False, proxies=PROXIES)
    return response.json()

async def refresh_altex_products(marketplace: Marketplace):
    # create_database()
    logging.info(f">>>>>>> Refreshing Marketplace : {marketplace.title} user is {marketplace.user_id} <<<<<<<<")
    user_id = marketplace.user_id
    PUBLIC_KEY = marketplace.credentials["firstKey"]
    PRIVATE_KEY = marketplace.credentials["secondKey"]

    page_nr = 1
    while True:
        try:
            result = get_products(marketplace.baseAPIURL, PUBLIC_KEY, PRIVATE_KEY, page_nr)
            if result['status'] == 'error':
                break
            data = result['data']
            products = data.get("items")

            result = get_offers(marketplace.baseAPIURL, PUBLIC_KEY, PRIVATE_KEY, page_nr)
            data = result['data']
            offers = data.get("items")

            await insert_products(products, offers, marketplace.marketplaceDomain, user_id)
            await insert_products_into_db(products, offers, marketplace.marketplaceDomain, user_id)
            page_nr += 1
        except Exception as e:
            logging.error(f"Exception occurred: {e}")
            break

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

    response = requests.post(url, data=json.dumps(data), headers=headers, proxies=PROXIES)
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

def post_stock_altex(marketplace:Marketplace, offer_id, stock):
    PUBLIC_KEY = marketplace.credentials["firstKey"]
    PRIVATE_KEY = marketplace.credentials["secondKey"]
    url = marketplace.baseAPIURL
    params  = ""
    url = f"{url}catalog/stock/"
    signature = generate_signature(PUBLIC_KEY, PRIVATE_KEY, params)
    headers = {
        'X-Request-Public-Key': PUBLIC_KEY,
        'X-Request-Signature': signature
    }

    data = {
        "0": {
            "stock": stock,
            "offer_id": offer_id
        }
    }
    response = requests.post(url, headers=headers, data = json.dumps(data), verify=False, proxies=PROXIES)
    return response.json()