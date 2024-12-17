import asyncio
import json
import logging
import psycopg2
import threading
from decimal import Decimal
from fastapi import HTTPException
from psycopg2 import sql
from sqlalchemy import any_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.config import settings
from app.database import get_db
from app.models import Marketplace, Product, Internal_Product
from app.utils.auth_market import get_auth_marketplace
from app.utils.httpx_request import send_post_request, send_get_request, send_patch_request
from app.logfiles import log_refresh_orders

lock = threading.Lock()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def change_string(ean_str):
    if ean_str and len(ean_str) == 12:
        return '0' + ean_str
    else:
        return ean_str

async def count_all_products(marketplace: Marketplace):
    logging.info("counting start")
    url = f"{marketplace.baseAPIURL}/product_offer/count"
    headers = get_auth_marketplace(marketplace)
    response = await send_get_request(url, headers=headers, error_msg='retrieve products')
    if response.status_code != 200:
        logging.error(f"Failed to get couriers from altex: {response.text}")
        return None
    return response.json()

async def get_all_products(marketplace: Marketplace, currentPage):
    url = f"{marketplace.baseAPIURL}/product_offer/read"
    headers = get_auth_marketplace(marketplace)
    data = json.dumps({
        "itemsPerPage": 100,
        "currentPage": currentPage,
    })
    response = await send_post_request(url, data=data, headers=headers)
    return response

async def insert_products(products, mp_name: str, user_id):
    async for db in get_db():
        async with db as session:
            for product in products:
                try:
                    ean = str(product.get('ean')[0]) if product.get('ean') else ''
                    ean = change_string(ean)
                    weight_value = product.get('weight')
                    if isinstance(weight_value, str):
                        weight_value = weight_value.replace(',', '.')
                    product_id = product.get('id')
                    product_processed = Internal_Product(
                        id = product_id,
                        part_number_key = product.get('part_number_key'),
                        product_code = '',
                        product_name = product.get('name'),
                        model_name = product.get('brand'),
                        buy_button_rank = product.get('buy_button_rank'),
                        ean = ean,
                        price = 0,
                        sale_price = Decimal(product.get('sale_price', '0.0')),
                        image_link = product.get('images')[0]['url'] if product.get('images') else '',
                        barcode_title = '',
                        masterbox_title = '',
                        link_address_1688 = '',
                        price_1688 = Decimal('0'),
                        variation_name_1688 = '',
                        pcs_ctn = '',
                        weight = Decimal(weight_value) if weight_value else Decimal('0'),
                        volumetric_weight = 0,
                        dimensions = '',
                        supplier_id = 0,
                        english_name = '',
                        romanian_name = '',
                        material_name_en = '',
                        material_name_ro = '',
                        hs_code = '',
                        battery = False,
                        default_usage = '',
                        production_time = Decimal('0'),
                        discontinued = False,
                        stock = int(product.get('stock')[0].get('value') if product.get('stock') else 0),
                        smartbill_stock = 0,
                        orders_stock = 0,
                        damaged_goods = 0,
                        warehouse_id = 0,
                        internal_shipping_price = Decimal('0'),
                        observation = '',
                        short_product_name = '',
                        market_place = [mp_name],
                        sync_stock_time = None,
                        smartbill_stock_time = None,
                        user_id = user_id
                    )
                    try:
                        result = await session.execute(
                            select(Internal_Product).where(
                                Internal_Product.ean == ean,
                                Internal_Product.user_id == user_id
                            )
                        )
                        product_db = result.scalars().first()
                    except Exception as e:
                        logging.error(f"Failed to get product {product_id} from database: {e}")
                        log_refresh_orders(f"Failed to get product {product_id} from database: {e}")
                        await session.rollback()
                    try:
                        if product_db:
                            origin_mkp = product_db.market_place or []
                            product_db.market_place = list(set(origin_mkp + [mp_name]))
                            product_db.buy_button_rank = product_processed.buy_button_rank
                            product_db.stock = product_processed.stock
                        else:
                            session.add(product_processed)
                        await session.commit()
                    except Exception as e:
                        logging.error(f"Failed to insert or update product {product_id}: {e}")
                        log_refresh_orders(f"Failed to insert or update product {product_id}: {e}")
                        await session.rollback()
                except Exception as e:
                    logging.error(f"Failed to insert or update product {product_id}: {e}")
                    log_refresh_orders(f"Failed to insert or update product {product_id}: {e}")
            log_refresh_orders("Internal_Products inserted into Products successfully")
            logging.info("Internal_Products inserted into Products successfully")

async def insert_products_into_db(products, place, user_id):
    async for db in get_db():
        async with db as session:
            for product in products:
                try:
                    product_id = str(product.get('id'))
                    ean = str(product.get('ean')[0]) if product.get('ean') else None
                    weight_value = product.get('weight')
                    if isinstance(weight_value, str):
                        weight_value = weight_value.replace(',', '.')  # Handle any comma as decimal separator
                    product_processed = Product(
                        id = product_id,
                        part_number_key = product.get('part_number_key'),
                        product_name = product.get('name'),
                        model_name = product.get('brand'),
                        buy_button_rank = product.get('buy_button_rank'),
                        sku = "",
                        ean = change_string(ean),
                        price = 0,
                        sale_price = Decimal(product.get('sale_price', '0.0')),
                        image_link = product.get('images')[0]['url'] if product.get('images') else '',
                        barcode_title = '',
                        masterbox_title = '',
                        link_address_1688 = '',
                        price_1688 = Decimal('0'),
                        variation_name_1688 = '',
                        pcs_ctn = '',
                        weight = Decimal(weight_value) if weight_value else Decimal('0'),
                        volumetric_weight = 0,
                        dimensions = '',
                        supplier_id = 0,
                        english_name = '',
                        romanian_name = '',
                        material_name_en = '',
                        material_name_ro = '',
                        hs_code = '',
                        battery = False,
                        default_usage = '',
                        production_time = Decimal('0'),
                        discontinued = False,
                        stock = int(product.get('stock')[0].get('value') if product.get('stock') else 0),
                        warehouse_id = 0,
                        internal_shipping_price = Decimal('0'),
                        observation = '',
                        product_marketplace = place,
                        user_id = user_id
                    )
                    try:
                        result = await session.execute(select(Product).where(Product.id == product_id, Product.product_marketplace == place))
                        product_db = result.scalars().first()
                    except Exception as e:
                        logging.error(f"Failed to get product {product_id} from database: {e}")
                        log_refresh_orders(f"Failed to get product {product_id} from database: {e}")
                        await session.rollback()
                    try:
                        if product_db:
                            product_db.product_name = product_processed.product_name
                            product_db.sale_price = product_processed.sale_price
                            product_db.stock = product_processed.stock
                        else:
                            session.add(product_processed)
                        await session.commit()
                    except Exception as e:
                        logging.error(f"Failed to insert or update product {product_id}: {e}")
                        log_refresh_orders(f"Failed to insert or update product {product_id}: {e}")
                        await session.rollback()
                except Exception as e:
                    logging.error(f"Failed to insert or update product {product_id}: {e}")
                    log_refresh_orders(f"Failed to insert or update product {product_id}: {e}")
            log_refresh_orders("Products inserted into Products successfully")

async def refresh_emag_products(marketplace: Marketplace):
    # create_database()
    logging.info(f">>>>>>> Refreshing Marketplace : {marketplace.title} user is {marketplace.user_id} <<<<<<<<")

    user_id = marketplace.user_id
    result = await count_all_products(marketplace)
    logging.info(f"count result is {result}")
    log_refresh_orders(f"count result is {result}")
    if result and result['isError'] == False:
        pages = result['results']['noOfPages']
        items = result['results']['noOfItems']

        logging.info(f"------------pages--------------{pages}")
        logging.info(f"------------items--------------{items}")
        currentPage = 1
        while currentPage <= int(pages):
            try:
                log_refresh_orders(f"Started fetching products from emag: page {currentPage}")
                response = await get_all_products(marketplace, currentPage)
                if response.status_code != 200:
                    logging.error(f"Failed to get products: {response.text}")
                    log_refresh_orders(f"Failed to get products: {response.text}")
                    currentPage += 1
                    continue

                logging.info(f">>>>>>> Current Page : {currentPage} <<<<<<<<")
                products = response.json()
                if products.get('isError') == False:
                    for _ in range(3):
                        try:
                            await insert_products_into_db(products['results'], marketplace.marketplaceDomain, user_id)
                            await asyncio.sleep(2)
                            await insert_products(products['results'], marketplace.marketplaceDomain, user_id)
                            break
                        except Exception as e:
                            log_refresh_orders(f"Failed to insert products: {e}")
                            continue
            except Exception as e:
                logging.error(f"An error occured to get products from page {currentPage}: {e}")
                log_refresh_orders(f"An error occured to get products from page {currentPage}: {e}")
            currentPage += 1

async def save(marketplace: Marketplace, data):
    ENDPOINT = marketplace.products_crud['endpoint']
    save_ENDPOINT = marketplace.products_crud['savepoint']
    url = f"{marketplace.baseAPIURL}{ENDPOINT}/{save_ENDPOINT}"
    headers = get_auth_marketplace(marketplace)
    response = await send_post_request(url, data=json.dumps(data), headers=headers, error_msg='save products')
    return response

async def save_product(data, marketplace:Marketplace, db: AsyncSession):
    result = await save(marketplace, data)
    return result

async def post_stock_emag(marketplace: Marketplace, product_id: int, stock: int):
    url = f"{marketplace.baseAPIURL}/offer_stock"
    headers = get_auth_marketplace(marketplace)
    data = {
        "stock": stock
    }
    response = await send_patch_request(f"{url}/{product_id}", json=data, headers=headers, error_msg="update stock")
    if response.status_code != 200:
        logging.error(f"Failed to post stock to {marketplace.baseURL}: {response.text}")
    return response
