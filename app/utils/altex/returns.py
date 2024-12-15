import psycopg2
import logging
from fastapi import HTTPException
from psycopg2 import sql

from app.config import settings, PROXIES
from app.models import Marketplace
from app.utils.auth_market import get_auth_marketplace
from app.utils.httpx_request import send_get_request

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def get_rmas(marketplace: Marketplace, page_nr):
    params = f"page_nr={page_nr}"
    url = f"{marketplace.baseAPIURL}sales/rma/?{params}"
    headers = get_auth_marketplace(marketplace, params=params)
    response = await send_get_request(url, headers=headers, proxies=PROXIES)
    if response.status_code != 200:
        logging.error(f"Failed to get rmas from altex: {response.text}")
    return response.json()

async def get_detail_rma(marketplace: Marketplace, order_id):
    params = ""
    url = f"{marketplace.baseAPIURL}sales/rms/{order_id}/"
    headers = get_auth_marketplace(marketplace, params=params)
    response = await send_get_request(url, headers=headers, proxies=PROXIES)
    if response.status_code != 200:
        logging.error(f"Failed to get detailed RMA: {response.text}")
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
    logging.info(f">>>>>>> Refreshing Marketplace : {marketplace.title} user is {marketplace.user_id} <<<<<<<<")

    user_id = marketplace.user_id

    page_nr = 1
    while True:
        try:
            result = await get_rmas(marketplace, page_nr)
            if result['status'] == 'error':
                break
            data = result['data']
            rmas = data.get('items')
            if ((not rmas) or len(rmas) == 0):
                break
            detail_rmas = []
            for rma in rmas:
                if rma.get('rma_id') is not None:
                    rma_id = rma.get('rma_id')
                    detail_rma_result = await get_detail_rma(marketplace, rma_id)
                    if detail_rma_result.get('status') == 'success':
                        detail_rmas.append(detail_rma_result.get('data'))

            await insert_rmas(detail_rmas, marketplace.marketplaceDomain, user_id)
            page_nr += 1
        except Exception as e:
            logging.error(f"Exception occurred: {e}")
            break
