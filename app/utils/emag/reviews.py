import logging
import psycopg2
from psycopg2 import sql
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.config import settings, PROXIES
from app.models import Marketplace, Product
from app.utils.httpx_request import send_get_request

async def get_review_by_product(product_id, product_part_number_key, marketplace: Marketplace):
    url = f'{marketplace.baseURL.replace("marketplace", "www")}/product-feedback/{product_id}/pd/{product_part_number_key}/reviews/list'
    print('------------------', url)

    response = await send_get_request(url, proxies=PROXIES, error_msg=f"retrieve reviews from product '{product_part_number_key}'")
    if response.status_code != 200:
        logging.error(f"Failed to get review of product {product_id}: {response.text}")
        return []
    result = response.json()
    return result

async def get_all_reviews(product_id_list, product_part_number_key_list, marketplace: Marketplace):
    result = []
    for i in range(len(product_id_list)):
        try:
            result.append({
                "product_id": product_id_list[i],
                "reviews": await get_review_by_product(product_id_list[i], product_part_number_key_list[i], marketplace)
            })
        except Exception as e:
            logging.error('Failed to retrieve reviews')
            result.append({
                "product_id": product_id_list[i],
                "reviews": []
            })
    return await get_review_by_product(product_id_list[i], product_part_number_key_list[i], marketplace)

async def insert_review_into_db(review, place, ean):
    try:
        conn = psycopg2.connect(
            dbname=settings.DB_NAME,
            user=settings.DB_USERNAME,
            password=settings.DB_PASSOWRD,  # Corrected spelling from DB_PASSOWRD to DB_PASSWORD
            host=settings.DB_URL,
            port=settings.DB_PORT
        )
        conn.set_client_encoding('UTF8')
        cursor = conn.cursor()

        insert_query = sql.SQL("""
            INSERT INTO {} (
                product_id,
                ean,
                review_id,
                user_id,
                user_name,
                content,
                moderated_by,
                rating,
                brand_id,
                review_marketplace
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            ) ON CONFLICT (id, review_id, review_marketplace) DO UPDATE SET
                user_id = EXCLUDED.user_id,
                user_name = EXCLUDED.user_name,
                content = EXCLUDED.content,
                moderated_by = EXCLUDED.moderated_by,
                rating = EXCLUDED.rating,
                brand_id = EXCLUDED.brand_id
        """).format(sql.Identifier("reviews"))

        product_id = review.get("product", {}).get("id")
        review_id = review.get("id")
        user_id = review.get("user", {}).get("id")
        user_name = review.get("user", {}).get("name")
        content = review.get("content")
        moderated_by = review.get("moderated_by")
        rating = review.get("rating")
        brand_id = review.get("brand_id")
        review_marketplace = place

        values = (
            product_id,
            ean,
            review_id,
            user_id,
            user_name,
            content,
            moderated_by,
            rating,
            brand_id,
            review_marketplace
        )

        cursor.execute(insert_query, values)
        conn.commit()
        print(f"Successfully inserted review")

        cursor.close()
        conn.close()
    except Exception as inner_e:
        print(f"Error inserting review {review_id}: {inner_e}")

async def insert_reviews_into_db(reviews, place, ean):
    for review in reviews:
        await insert_review_into_db(review, place, ean)

async def refresh_emag_reviews(marketplace: Marketplace, db: AsyncSession):
    user_id = marketplace.user_id
    result = await db.execute(select(Product).where(Product.user_id == user_id))
    products = result.scalars().all()

    logging.info(f"Number of products: {len(products)}")

    cnt = 0
    for product in products:
        marketplacedomain = product.product_marketplace
        if marketplacedomain.lower()[:4] != "emag":
            continue
        cnt += 1

        try:
            logging.info(f"Processing product {cnt}/{len(products)}: {product.id}")

            result = await get_review_by_product(product.id, product.part_number_key, marketplace)

        except Exception as e:
            logging.error(f"Error processing reviews: {e}")

        if result == "nothing" or result.get("reviews").get("count") == 0:
            logging.info(f"No reviews for product {product.id}")
            continue

        reviews = result.get("reviews").get("items")

        await insert_reviews_into_db(reviews, marketplace.marketplaceDomain, product.ean)

    logging.info(f"Processed {cnt} products")
