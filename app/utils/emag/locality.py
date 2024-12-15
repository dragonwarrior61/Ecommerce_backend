import psycopg2
import json
import logging
from fastapi import HTTPException
from psycopg2 import sql

from app.config import settings
from app.models import Marketplace
from app.utils.auth_market import get_auth_marketplace
from app.utils.httpx_request import send_post_request, send_get_request

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def get_all_localities(marketplace: Marketplace, currentPage):
    url = f"{marketplace.baseAPIURL}/locality/read"
    headers = get_auth_marketplace(marketplace)
    data = json.dumps({
        "itmesPerPage": 100,
        "currentPage": currentPage
    })
    response = await send_post_request(url, data=data, headers=headers, error_msg='retrieve localities')
    if response.status_code != 200:
        logging.error(f"Failed to get localities: {response.text}")
    localities = response.json()
    return localities

async def count_all_localities(marketplace: Marketplace):
    url = f"{marketplace.baseAPIURL}/locality/count"

    headers = get_auth_marketplace(marketplace)

    response = await send_get_request(url, headers=headers, error_msg='count localities')
    if response.status_code != 200:
        logging.error(f"Failed to count localities: {response.text}")
    return response.json()

async def insert_localities_into_db(localities, place:str, user_id):
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

        for locality in localities:
            id = locality.get('emag_id')
            name = locality.get('name')
            name_latin = locality.get('name_latin')
            region1 = locality.get('region1')
            region2 = locality.get('region2')
            region3 = locality.get('region3')
            region1_latin = locality.get('region1_latin')
            region2_latin = locality.get('region2_latin')
            region3_latin = locality.get('region3_latin')
            geoid = locality.get('geoid')
            modified = locality.get('modified')
            zipcode = locality.get('zipcode')
            country_code = locality.get('country_code')
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

async def refresh_emag_localities(marketplace: Marketplace):
    # create_database()
    logging.info(f">>>>>>> Refreshing Marketplace : {marketplace.title} user is {marketplace.user_id} <<<<<<<<")
    user_id = marketplace.user_id
    result = await count_all_localities(marketplace)
    print(result)
    if result and result['isError'] == False:
        pages = result['results']['noOfPages']
        items = result['results']['noOfItems']
        logging.info(f"------------pages--------------{pages}")
        logging.info(f"------------items--------------{items}")
    while current_page <= int(pages):
        current_page  = 1
        try:
            localities = await get_all_localities(marketplace, current_page)
            logging.info(f">>>>>>> Current Page : {current_page} <<<<<<<<")
            if len(localities['results'] ) == 0:
                print("empty locality")
                break
            await insert_localities_into_db(localities['results'], marketplace.marketplaceDomain, user_id)
            current_page += 1
        except Exception as e:
            logging.error(f"An error ocurred in page {current_page}: {e}")
