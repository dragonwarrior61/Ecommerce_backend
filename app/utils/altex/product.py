import psycopg2
import json
import logging
from fastapi import HTTPException
from psycopg2 import sql
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal

from app.config import settings, PROXIES
from app.models import Marketplace
from app.utils.auth_market import get_auth_marketplace
from app.utils.httpx_request import send_get_request, send_post_request
from app.logfiles import log_refresh_orders

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

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

async def get_products(marketplace: Marketplace, page_nr):
    params = f"page_nr={page_nr}"
    url = f"{marketplace.baseAPIURL}catalog/product/?{params}"
    headers = get_auth_marketplace(marketplace)
    response = await send_get_request(url, headers=headers, proxies=PROXIES)
    if response.status_code != 200:
        logging.error(f"Failed to get products from altex: {response.text}")
    return response.json()

async def get_offers(marketplace: Marketplace, page_nr):
    params = f"page_nr={page_nr}"
    url = f"{marketplace.baseAPIURL}catalog/offer/?{params}"
    headers = get_auth_marketplace(marketplace, params=params)
    print(headers)
    response = await send_get_request(url, headers=headers, proxies=PROXIES)
    if response.status_code != 200:
        logging.error(f"Failed to get offers from altex: {response.text}")
    return response.json()

async def refresh_altex_products(marketplace: Marketplace):
    logging.info(f">>>>>>> Refreshing Marketplace : {marketplace.title} user is {marketplace.user_id} <<<<<<<<")
    user_id = marketplace.user_id
    page_nr = 1
    while True:
        try:
            log_refresh_orders(f"Started fetching products from altex: page {page_nr}")
            result = await get_products(marketplace, page_nr)
            if result['status'] == 'error':
                break
            data = result['data']
            products = data.get("items")
            if ((not products) or len(products) == 0):
                break

            result = await get_offers(marketplace, page_nr)
            data = result['data']
            offers = data.get("items")

            await insert_products(products, offers, marketplace.marketplaceDomain, user_id)
            await insert_products_into_db(products, offers, marketplace.marketplaceDomain, user_id)
            page_nr += 1
        except Exception as e:
            logging.error(f"Exception occurred: {e}")
            log_refresh_orders(f"Exception occurred: {e}")
            break

async def save(marketplace: Marketplace, data):
    MARKETPLACE_API_URL = marketplace.baseAPIURL
    ENDPOINT = marketplace.products_crud['endpoint']
    save_ENDPOINT = marketplace.products_crud['savepoint']
    url = f"{MARKETPLACE_API_URL}/{ENDPOINT}/{save_ENDPOINT}"
    headers = get_auth_marketplace(marketplace)

    response = await send_post_request(url, data=json.dumps(data), headers=headers, proxies=PROXIES, error_msg="retrieve products")
    if response.status_code != 200:
        logging.error(f"Failed to save data: {response.text}")
    products = response.json()
    return products

async def save_product(data, marketplace:Marketplace, db: AsyncSession):
    result = await save(marketplace, data)
    return result

async def post_stock_altex(marketplace: Marketplace, offer_id, stock):
    params  = ""
    url = f"{marketplace.baseAPIURL}catalog/stock/"
    headers = get_auth_marketplace(marketplace, params=params)

    data = {
        "0": {
            "stock": stock,
            "offer_id": offer_id
        }
    }
    response = await send_post_request(url, headers=headers, data=json.dumps(data), proxies=PROXIES)
    if response.status_code != 200:
        logging.error(f"Failed to post stock to altex: {response.text}")
    return response.json()
