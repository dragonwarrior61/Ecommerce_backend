import requests
import psycopg2
import base64
import hashlib
import json
import os
from app.config import settings
from psycopg2 import sql
from urllib.parse import urlparse
from app.models.marketplace import Marketplace
from app.models.orders import Order
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any

from sqlalchemy.exc import IntegrityError
import logging
from sqlalchemy import insert
from sqlalchemy.dialects.postgresql import insert as pg_insert
from datetime import datetime
from decimal import Decimal
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


MARKETPLACE_URL = 'https://marketplace.emag.ro/'
MARKETPLACE_API_URL = 'https://marketplace-api.emag.ro/api-3'
ORDERS_ENDPOINT = "/order"

PROXIES = {
    'http': 'http://p2p_user:jDkAx4EkAyKw@65.109.7.74:54021',
    'https': 'http://p2p_user:jDkAx4EkAyKw@65.109.7.74:54021',
}
    
def generate_signature(public_key, private_key, params):

    now = datetime.utcnow()
    day = now.strftime('%d')
    month = now.strftime('%m')
    timestamp = f"{day}{month}"

    string_to_hash = f"{public_key}||{hashlib.sha512(private_key.encode()).hexdigest()}||{params}||{timestamp}"
    hash_result = hashlib.sha512(string_to_hash.encode()).hexdigest().lower()
    signature = f"{timestamp}{hash_result}"
    # signature = timestamp + hash_result
    return signature

def get_orders(url, public_key, private_key, page_nr):

    params = f"page_nr={page_nr}"
    url = f"{url}sales/order/?{params}"
    signature = generate_signature(public_key, private_key, params)
    headers = {
        'X-Request-Public-Key': public_key,
        'X-Request-Signature': signature
    }
    response = requests.get(url, headers=headers, verify=False, proxies=PROXIES)
    if response.status_code == 200:
        logging.info("Get orders in Altex Successed!")
    else:
        logging.info(response.json())
    return response.json()

def get_detail_order(url, public_key, private_key, order_id):
    params = ""
    url = f"{url}sales/order/{order_id}/"
    signature = generate_signature(public_key, private_key, params)
    headers = {
        'X-Request-Public-Key': public_key,
        'X-Request-Signature': signature
    }
    response = requests.get(url, headers=headers, verify=False, proxies=PROXIES)
    return response.json()

async def insert_orders(orders, mp_name:str, user_id):
    try:
        conn = psycopg2.connect(
            dbname=settings.DB_NAME,
            user=settings.DB_USERNAME,
            password=settings.DB_PASSOWRD,
            host=settings.DB_URL,
            port=settings.DB_PORT
        )
        conn.set_client_encoding('UTF8')
        cursor_order = conn.cursor()

        insert_orders_query = sql.SQL("""
            INSERT INTO {} (
                id,
                vendor_name,
                type,
                date,
                payment_mode,
                detailed_payment_method,
                delivery_mode,
                status,
                payment_status,
                customer_id,
                product_id,
                quantity,
                sale_price,
                shipping_tax,
                shipping_tax_voucher_split,
                vouchers,
                proforms,
                attachments,
                shipping_address,
                cashed_co,
                cashed_cod,
                refunded_amount,
                is_complete,
                cancellation_request,
                cancellation_reason,
                refund_status,
                maximum_date_for_shipment,
                late_shipment,
                flags,
                emag_club,
                finalization_date,
                details,
                payment_mode_id,
                order_market_place,
                mkt_id,
                name,
                company,
                gender,
                phone_1,
                billing_name,
                billing_phone,
                billing_country,
                billing_suburb,
                billing_city,
                billing_locality_id,
                billing_street,
                shipping_country,
                shipping_suburb,
                shipping_city,
                shipping_locality_id,
                shipping_contact,
                shipping_phone,
                shipping_street,
                created,
                modified,
                legal_entity,
                is_vat_payer,
                code,
                bank,
                iban,
                email,
                product_voucher_split,
                registration_number,
                user_id
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            ) ON CONFLICT (id) DO UPDATE SET
                vendor_name = EXCLUDED.vendor_name,
                type = EXCLUDED.type,
                date = EXCLUDED.date,
                payment_mode = EXCLUDED.payment_mode,                      
                status = EXCLUDED.status,
                payment_status = EXCLUDED.payment_status,
                product_id = EXCLUDED.product_id,
                quantity = EXCLUDED.quantity,
                sale_price = EXCLUDED.sale_price,
                shipping_tax = EXCLUDED.shipping_tax,
                shipping_tax_voucher_split = EXCLUDED.shipping_tax_voucher_split,
                refunded_amount = EXCLUDED.refunded_amount,
                cancellation_request = EXCLUDED.cancellation_request,
                cancellation_reason = EXCLUDED.cancellation_reason,
                is_complete = EXCLUDED.is_complete,
                refund_status = EXCLUDED.refund_status,
                emag_club = EXCLUDED.emag_club,
                finalization_date = EXCLUDED.finalization_date,
                details = EXCLUDED.details,
                payment_mode_id = EXCLUDED.payment_mode_id
        """).format(sql.Identifier("orders"))
        
        for order in orders:
            customer_id = order.get('order_id')
            customer_mkt_id = 0
            customer_name = order.get('billing_customer_name')
            customer_company = order.get('billing_company_name')
            customer_gender = ""
            customer_phone_1 = order.get('billing_phone_number')
            customer_billing_name = order.get('billing_customer_name')
            customer_billing_phone = order.get('billing_phone_number')
            customer_billing_country = order.get('billing_country')
            customer_billing_suburb = ""
            customer_billing_city = order.get('billing_city')
            customer_billing_locality_id = ""
            customer_billing_street = order.get('billing_address')
            customer_shipping_country = order.get('shipping_country')
            customer_shipping_suburb = ""
            customer_shipping_city = order.get('shipping_city')
            customer_shipping_locality_id = ""
            customer_shipping_street = order.get('shipping_address')
            customer_shipping_contact = ""
            customer_shipping_phone = order.get('shipping_phone_number')
            customer_created = None
            customer_modified = None
            customer_legal_entity = 0
            customer_is_vat_payer = 0
            code = order.get('billing_company_code')
            bank = order.get('billing_company_bank')
            iban = order.get('billing_company_iban')
            email = ""
            registration_number = order.get('billing_company_registration_number')

            id = order.get('order_id')
            vendor_name = ""
            type = 0
            date = order.get('order_date')
            payment_mode = order.get('payment_mode')
            detailed_payment_method = ""
            delivery_mode = order.get('delivery_mode')
            status = order.get('status')
            payment_status = 0
            products_id = [str(product.get('product_id')) for product in order.get('products')]
            quantity = [product.get('quantity') for product in order.get('products')]
            product_voucher_split = ["" for product in order.get('products')]
            sale_price = [product.get('selling_price') for product in order.get('products')]
            shipping_tax = Decimal(order.get('shipping_tax'))
            shipping_tax_voucher_split = ""
            vouchers = ""
            proforms = ""
            attachments = ''
            shipping_address = customer_shipping_street
            cashed_co = Decimal('0')
            cashed_cod = 0
            refunded_amount = 0
            is_complete = 0
            cancellation_request = ""
            cancellation_reason = ""
            refund_status = ""
            maximum_date_for_shipment = None
            late_shipment = 0
            flags = ""
            emag_club = 0
            finalization_date = None
            details = ""
            payment_mode_id = 0
            order_martet_place = mp_name
            user_id = user_id
            
            values = (
                id,
                vendor_name,
                type,
                date,
                payment_mode,
                detailed_payment_method,
                delivery_mode,
                status,
                payment_status,
                customer_id,
                products_id,
                quantity,
                sale_price,
                shipping_tax,
                shipping_tax_voucher_split,
                vouchers,
                proforms,
                attachments,
                shipping_address,
                cashed_co,
                cashed_cod,
                refunded_amount,
                is_complete,
                cancellation_request,
                cancellation_reason,
                refund_status,
                maximum_date_for_shipment,
                late_shipment,
                flags,
                emag_club,
                finalization_date,
                details,
                payment_mode_id,
                order_martet_place,
                customer_mkt_id,
                customer_name,
                customer_company,
                customer_gender,
                customer_phone_1,
                customer_billing_name,
                customer_billing_phone,
                customer_billing_country,
                customer_billing_suburb,
                customer_billing_city,
                customer_billing_locality_id,
                customer_billing_street,
                customer_shipping_country,
                customer_shipping_suburb,
                customer_shipping_city,
                customer_shipping_locality_id,
                customer_shipping_contact,
                customer_shipping_phone,
                customer_shipping_street,
                customer_created,
                customer_modified,
                customer_legal_entity,
                customer_is_vat_payer,
                code,
                bank,
                iban,
                email,
                product_voucher_split,
                registration_number,
                user_id
            )

            cursor_order.execute(insert_orders_query, values)

            conn.commit()
        cursor_order.close()
        conn.close()
        logging.info("Orders inserted successfully")
    except Exception as e:
        logging.info(f"Failed to insert orders into database: {e}")

async def refresh_altex_orders(marketplace: Marketplace):
    # create_database()
    logging.info(f">>>>>>> Refreshing Marketplace : {marketplace.title} user is {marketplace.user_id} <<<<<<<<")

    user_id = marketplace.user_id
    PUBLIC_KEY = marketplace.credentials["firstKey"]
    PRIVATE_KEY = marketplace.credentials["secondKey"]

    page_nr = 1
    while True:
        try:
            result = get_orders(marketplace.baseAPIURL, PUBLIC_KEY, PRIVATE_KEY, page_nr)
            if result['status'] == 'error':
                break
            data = result['data']
            orders = data.get('items')
            logging.info(f"Get {len(orders)}")
            detail_orders = []
            for order in orders:
                if order.get('order_id') is not None:
                    order_id = order.get('order_id')
                    logging.info(f"Get order id is {order_id}")
                    detail_order_result = get_detail_order(marketplace.baseAPIURL, PUBLIC_KEY, PRIVATE_KEY, order_id)
                    if detail_order_result.get('status') == 'success':
                        detail_orders.append(detail_order_result.get('data'))

            await insert_orders(detail_orders, marketplace.marketplaceDomain, user_id)
            logging.info(f"Fishish fetching orders in {page_nr} pages!")
            page_nr += 1
        except Exception as e:
            logging.error(f"Exception occurred: {e}")
            