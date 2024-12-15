import psycopg2
import json
import logging
from fastapi import HTTPException
from psycopg2 import sql

from app.config import settings
from app.models import Marketplace
from app.utils.auth_market import get_auth_marketplace
from app.utils.httpx_request import send_post_request

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def get_all_couriers(marketplace: Marketplace):
    url = f"{marketplace.baseAPIURL}/courier_accounts/read"
    headers = get_auth_marketplace(marketplace)

    response = await send_post_request(url, headers=headers, error_msg='retrieve refunds')
    if response.status_code != 200:
        logging.error(f"Failed to get couriers: {response.text}")
    localities = response.json()
    return localities

async def insert_couriers_into_db(couriers, place:str, user_id: int):
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
            account_id = courier.get('account_id')
            account_display_name = courier.get('account_display_name')
            courier_account_type = courier.get('courier_account_type')
            courier_name = courier.get('courier_name')
            courier_account_properties = json.dumps(courier.get('courier_account_properties'))
            created = courier.get('created')
            status = courier.get('status')
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

async def refresh_emag_couriers(marketplace: Marketplace):
    # create_database()
    logging.info(f">>>>>>> Refreshing Marketplace : {marketplace.title} user is {marketplace.user_id} <<<<<<<<")
    result = await get_all_couriers(marketplace)
    print(result)
    user_id = marketplace.user_id
    await insert_couriers_into_db(result['results'], marketplace.marketplaceDomain, user_id)
