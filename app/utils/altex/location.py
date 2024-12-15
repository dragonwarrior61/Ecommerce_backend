import psycopg2
import logging
from fastapi import HTTPException
from psycopg2 import sql

from app.config import settings, PROXIES
from app.models import Marketplace
from app.utils.auth_market import get_auth_marketplace
from app.utils.httpx_request import send_get_request

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

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
            conn.commit()
        cursor.close()
        conn.close()
        print("Localities inserted successfully")
    except Exception as e:
        print(f"Failed to insert localities into database: {e}")

async def get_locations(marketplace: Marketplace, page_nr):
    params = f"page_nr={page_nr}"
    url = f"{marketplace.baseAPIURL}sales/location/?{params}"
    headers = get_auth_marketplace(marketplace, params=params)
    response = await send_get_request(url, headers=headers, proxies=PROXIES)
    if response.status_code != 200:
        logging.error(f"Failed to get locations from altex: {response.text}")
    return response.json()

async def refresh_altex_locations(marketplace: Marketplace):
    # create_database()
    logging.info(f">>>>>>> Refreshing Marketplace : {marketplace.title} user is {marketplace.user_id} <<<<<<<<")

    user_id = marketplace.user_id

    page_nr = 1
    while True:
        try:
            result = await get_locations(marketplace, page_nr)
            if result['status'] == 'error':
                break
            data = result['data']
            locations = data.get("items")
            if ((not locations) or len(locations) == 0):
                break

            await insert_locations(locations, marketplace.marketplaceDomain, user_id)
            page_nr += 1
        except Exception as e:
            logging.error(f"Exception occurred: {e}")
            break
