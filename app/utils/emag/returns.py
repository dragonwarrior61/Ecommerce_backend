import asyncio
import json
import logging
import psycopg2
from fastapi import HTTPException
from psycopg2 import sql

from app.config import settings
from app.models import Marketplace
from app.utils.auth_market import get_auth_marketplace
from app.utils.httpx_request import send_post_request, send_get_request

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def get_attachments(marketplace: Marketplace):
    url = 'https://marketplace-api.emag.ro/api-3/product_offer/save'
    headers = get_auth_marketplace(marketplace)
    data = json.dumps({
        "itmesPerPage": 100,
        "currentPage": 1
    })

    response = await send_post_request(url, data=data, headers=headers, error_msg='get attachements')
    if response.status_code != 200:
        logging.error(f"Failed to get attachments: {response.text}")
    attachments = response.json()
    return attachments

async def get_all_rmas(marketplace: Marketplace, currentPage):
    url = f"{marketplace.baseAPIURL}/rma/read"
    headers = get_auth_marketplace(marketplace)
    data = json.dumps({
        "itmesPerPage": 100,
        "currentPage": currentPage
    })
    response = await send_post_request(url, data=data, headers=headers, error_msg='retrieve refunds')
    if response.status_code != 200:
        logging.error(f"Failed to get rmas: {response.text}")
    return response.json()

async def get_awb(reservation_id, marketplace: Marketplace):
    baseurl = marketplace.baseAPIURL
    headers = get_auth_marketplace(marketplace)
    url = f'{baseurl}/awb/read'
    data = json.dumps({
        "reservation_id": reservation_id
    })
    response = await send_post_request(url, data=data, headers=headers, error_msg="get awb")
    if response.status_code != 200:
        logging.error(f"Failed to get awb: {response.text}")
    awb = response.json()
    return awb

async def count_all_rmas(marketplace: Marketplace):
    logging.info("counting start")
    url = f"{marketplace.baseAPIURL}/rma/count"

    headers = get_auth_marketplace(marketplace)

    # response = requests.post(url, headers=headers, proxies=PROXIES)
    MAX_RETRIES = 5
    retry_delay = 5  # seconds
    async def retry(attempt: int):
        logging.warning(f"Request timed out. Attempt {attempt + 1} of {MAX_RETRIES}. Retrying...")
        await asyncio.sleep(retry_delay)

    for attempt in range(MAX_RETRIES):
        try:
            response = await send_get_request(url, headers=headers, error_msg='cound refunds')
            if response.status_code == 200:
                return response.json()
            else:
                logging.error(f"Failed to cound rmas from {marketplace.baseURL}: {response.text}")
                await retry(attempt)
        except Exception as e:
            logging.error(f"An error occured: {e}")
            await retry(attempt)
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

    result = await count_all_rmas(marketplace)
    if result and result['isError'] == False:
        pages = result['results']['noOfPages']
        items = result['results']['noOfItems']
        logging.info(f"------------pages--------------{pages}")
        logging.info(f"------------items--------------{items}")
    current_page  = 1
    while current_page <= int(pages):
        try:
            rmas = await get_all_rmas(marketplace, current_page)
            logging.info(f">>>>>>> Current Page : {current_page} <<<<<<<<")
            await insert_rmas_into_db(rmas['results'], marketplace)
            current_page += 1
        except Exception as e:
            logging.error(f"An error occured: {e}")
