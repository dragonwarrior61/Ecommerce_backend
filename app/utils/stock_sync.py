import logging
import requests
import base64
from app.models.product import Product
from app.models.internal_product import Internal_Product
from app.models.orders import Order
from app.models.marketplace import Marketplace
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import any_
import psycopg2
from app.config import settings
from psycopg2 import sql

async def calc_order_stock(db: AsyncSession):
    result = await db.execute(select(Order).where(Order.status == any_([1,2,3])))
    db_new_orders = result.scalars().all()
    if db_new_orders is None:
        logging.info("Can't find new orders")
        return
    else:
        logging.info(f"Find {len(db_new_orders)} new orders")
    try:
        for db_new_order in db_new_orders:
            product_id_list = db_new_order.product_id
            quantity_list = db_new_order.quantity
            marketplace = db_new_order.order_market_place
            logging.info(f"@#@#!#@#@##!@#@#@ order_id is {db_new_order.id}")
            for i in range(len(product_id_list)):
                product_id = product_id_list[i]
                quantity = quantity_list[i]
            
                result = await db.execute(select(Product).where(Product.id == product_id, Product.product_marketplace == marketplace, Product.user_id == db_new_order.user_id))
                db_product = result.scalars().first()
                if db_product is None:
                    logging.info(f"Can't find {product_id} in {marketplace}")
                    continue
                ean = db_product.ean
                logging.info(f"&*&*&*&&*&*&**&ean number is {ean}")

                result = await db.execute(select(Internal_Product).where(Internal_Product.ean == ean))
                db_internal_product = result.scalars().first()
                if db_internal_product is None:
                    logging.info(f"Can't find {ean}")
                db_internal_product.orders_stock = db_internal_product.orders_stock + quantity
                # logging.info(f"#$$$#$#$#$#$ Orders_stock is {db_internal_product.orders_stock}")
        await db.commit()
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        await db.rollback()