from fastapi import FastAPI, HTTPException # type: ignore
from pydantic import BaseModel # type: ignore
from typing import List, Dict
import psycopg2
from psycopg2 import sql
from app.models.internal_product import Internal_Product
from app.models.notifications import Notification
from app.models.review import Review
from app.models.user import User
from app.routers.auth import get_current_user
from app.routers.notifications import create_new_notification
from app.utils.emag_reviews import *
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.config import settings
from sqlalchemy import text
from datetime import datetime
from app.config import settings

app = FastAPI()

# def create_notifications_table(notifications_table):
#     conn = psycopg2.connect(
#         dbname=settings.DB_NAME,
#         user=settings.DB_USERNAME,
#         password=settings.DB_PASSOWRD,
#         host=settings.DB_URL,
#         port=settings.DB_PORT
#     )
#     cursor = conn.cursor()
#     create_table_query = sql.SQL("""
#         CREATE TABLE IF NOT EXISTS {} (
#             id SERIAL PRIMARY KEY,
#             title TEXT,
#             description TEXT,
#             time TIMESTAMP,
#             ean TEXT UNIQUE,
#             state TEXT,
#             read BOOLEAN,
#             user_id INTEGER,
#             market_place TEXT                    
#         )"""
#     ).format(sql.Identifier(notifications_table))
#     cursor.execute(create_table_query)
#     conn.commit()
#     cursor.close()
#     conn.close()

def check_hijacker(product_list):
    hijackers = []
    try:
        for product in product_list:
            product_id = product.get("id")

            buy_button_rank = product.get("buy_button_rank")
            # for i in range(len(buy_button_ranks)):
            if buy_button_rank == None:
                continue
            if buy_button_rank > 1:
                hijackers.append({
                        "product_id": product_id,
                        "name": product.get("product_name"),
                        "ean": product.get("ean")
                    })
        
        logging.info("############Success to read hijackers")
        return hijackers
    except Exception as e:
        logging.info("Can't Read hijackers", e)

def check_bad_reviews(review_list: List[Review]):
    bad_reviews = []

    for review in review_list:
        if review.rating <= 3:
            bad_reviews.append(review)

    return bad_reviews

async def check_hijacker_and_bad_reviews(marketplace: Marketplace, db: AsyncSession):
    conn = psycopg2.connect(
        dbname=settings.DB_NAME,
        user=settings.DB_USERNAME,
        password=settings.DB_PASSOWRD,
        host=settings.DB_URL,
        port=settings.DB_PORT
    )
    conn.set_client_encoding('UTF8')
    
    result = await db.execute(text(f"SELECT * FROM products"))
    products = result.fetchall()

    product_dicts = []
    for product in products:
        product_dict = {key: value for key, value in zip(result.keys(), product)}
        product_dicts.append(product_dict)

    logging.info("Start checking hijacker")

    hijackers = check_hijacker(product_dicts)

    # await refresh_emag_reviews(marketplace, db)
    marketplacename = marketplace.marketplaceDomain
    logging.info(marketplacename)
    result = await db.execute(select(Review).where(Review.review_marketplace == marketplacename))
    reviews = result.scalars().all()

    bad_reviews = check_bad_reviews(reviews)

    admin_id = 1

    result = await db.execute(select(Notification))
    notifications = result.scalars().all()
    id = max(notification.id for notification in notifications) + 1

    cursor = conn.cursor()

    # delete_notifications_query = sql.SQL("DELETE FROM {}").format(sql.Identifier("notifications"))
    # cursor.execute(delete_notifications_query)

    insert_notification_query = sql.SQL("""
        INSERT INTO {} (
            id,
            title,
            description,
            time,
            ean,
            state,
            read,
            user_id,
            market_place
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s                     
        ) ON CONFLICT (title, ean, market_place) DO UPDATE SET
            time = EXCLUDED.time,
            user_id = EXCLUDED.user_id       
    """).format(sql.Identifier("notifications"))

    for bad_review in bad_reviews:
        date_str = datetime.now()
        title = "Bad Review"
        
        description = bad_review.content
        time = date_str.strftime('%Y-%m-%dT%H:%M:%S')
        ean = bad_review.ean
        state = bad_review.user_name
        read = False
        user_id = admin_id
        market_place = marketplace.marketplaceDomain.lower()


        values = (
            id,
            title,
            description,
            time,
            ean,
            state,
            read,
            user_id,
            market_place,
        )

        try:
            cursor.execute(insert_notification_query, values)
            id += 1
            logging.info("Success to insert review into notification")
        except Exception as e:
            logging.info(f"Failed to insert review into notification: {e}")
            await db.rollback()
            
    for hijacker in hijackers:
        date_str = datetime.now()            
        title = "Detected Hijacker"
        description = hijacker["name"]
        time = date_str.strftime('%Y-%m-%dT%H:%M:%S')
        ean = hijacker["ean"]
        state = "error"
        read = False
        user_id = admin_id
        market_place = marketplace.marketplaceDomain.lower()

        values = (
            id,
            title,
            description,
            time,
            ean,
            state,
            read,
            user_id,
            market_place
        )
        try:
            cursor.execute(insert_notification_query, values)
            id += 1
        except Exception as e:
            logging.info(f"Failed to insert hijacker into notification: {e}")
            await db.rollback()
            
    settings.update_flag = 1
    try:
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        conn.rollback()
    finally:
        settings.update_flag = 0