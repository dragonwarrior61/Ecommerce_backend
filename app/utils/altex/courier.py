import psycopg2
import logging
from fastapi import HTTPException
from psycopg2 import sql

from app.config import settings, PROXIES
from app.models import Marketplace
from app.utils.auth_market import get_auth_marketplace
from app.utils.httpx_request import send_get_request

# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

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

async def get_couriers(marketplace: Marketplace, page_nr):

    params = f"page_nr={page_nr}"
    url = f"{marketplace.baseAPIURL}sales/courier/?{params}"
    headers = get_auth_marketplace(marketplace, params=params)
    response = await send_get_request(url=url, headers=headers, proxies=PROXIES)
    if response.status_code != 200:
        logging.error(f"Failed to get couriers from altex: {response.text}")
    return response.json()

async def refresh_altex_couriers(marketplace: Marketplace):
    logging.info(f">>>>>>> Refreshing Marketplace : {marketplace.title} user is {marketplace.user_id} <<<<<<<<")
    user_id = marketplace.user_id

    page_nr = 1
    while True:
        try:
            result = await get_couriers(marketplace, page_nr)
            if result['status'] == 'error':
                break
            data = result['data']
            couriers = data.get("items")
            if ((not couriers) or len(couriers) == 0):
                break

            await insert_couriers(couriers, marketplace.marketplaceDomain, user_id)
            page_nr += 1
        except Exception as e:
            logging.error(f"Exception occurred: {e}")
            break