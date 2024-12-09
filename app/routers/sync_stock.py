from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, any_
from typing import List
from app.database import get_db
from app.models.internal_product import Internal_Product
from app.models.orders import Order
from app.models.user import User
from app.routers.auth import get_current_user
from app.models.product import Product
from app.models.marketplace import Marketplace
from app.utils.altex_product import post_stock_altex
from app.utils.emag_products import post_stock_emag
from sqlalchemy import update
import logging
from app.config import settings

router = APIRouter()

@router.get("/")
async def send_stock(
    db: AsyncSession = Depends(get_db)
):
    logging.info("Init orders_stock")
    settings.update_flag = 1
    try:
        await db.execute(update(Internal_Product).values(orders_stock=0))
        await db.commit()
    except Exception as e:
        db.rollback()
    finally:
        settings.update_flag = 0
    logging.info("Calculate orders_stock")
    result = await db.execute(select(Order).where(Order.status == any_([1,2,3])))
    new_orders = result.scalars().all()
    if new_orders is None:
        logging.info("Can't find new orders")
        return
    logging.info(f"Find {len(new_orders)} new orders")

    try:
        for new_order in new_orders:
            product_id_list = new_order.product_id
            quantity_list = new_order.quantity
            marketplace = new_order.order_market_place
            logging.info(f"@#@#!#@#@##!@#@#@ order_id is {new_order.id}")
            for i in range(len(product_id_list)):
                product_id = product_id_list[i]
                quantity = quantity_list[i]
            
                result = await db.execute(select(Product).where(Product.id == product_id, Product.product_marketplace == marketplace, Product.user_id == new_order.user_id))
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
                    continue
                db_internal_product.orders_stock = db_internal_product.orders_stock + quantity
                # logging.info(f"#$$$#$#$#$#$ Orders_stock is {db_internal_product.orders_stock}")
        
        settings.update_flag = 1
        try:
            await db.commit()
        except Exception as e:
            db.rollback()
        finally:
            settings.update_flag = 0
        
        logging.info(f"#$$$#$#$#$#$ Orders_stock is {db_internal_product.orders_stock}")
        logging.info("Sync stock")
        result = await db.execute(select(Internal_Product))
        products = result.scalars().all()
        for product in products:
            if product.smartbill_stock is None:
                continue
            ean = product.ean
            marketplaces = product.market_place
            for domain in marketplaces:
                result = await db.execute(select(Marketplace).where(Marketplace.marketplaceDomain == domain))
                marketplace = result.scalars().first()
                
                result = await db.execute(select(Product).where(Product.ean == ean, Product.product_marketplace == domain))
                db_product = result.scalars().first()
                product_id = db_product.id
                stock = product.smartbill_stock - product.orders_stock - product.damaged_goods

                if marketplace.marketplaceDomain == "altex.ro":
                    continue
                    # if db_product.barcode_title == "":
                    #     continue
                    # post_stock_altex(marketplace, db_product.barcode_title, stock)
                    # logging.info("post stock success in altex")
                else:
                    await post_stock_emag(marketplace, product_id, stock)
                    logging.info("post stock success in emag")

    except Exception as e:
        logging.error(f"An error occurred: {e}")
        # await db.rollback() 


