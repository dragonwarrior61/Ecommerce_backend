import requests
import psycopg2
import base64
import json
import os
from app.config import settings
from psycopg2 import sql
from urllib.parse import urlparse
from app.models.marketplace import Marketplace
from app.models.orders import Order
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any
import time
from sqlalchemy.exc import IntegrityError
import logging
from sqlalchemy import insert
from sqlalchemy.dialects.postgresql import insert as pg_insert
import datetime
from decimal import Decimal
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


MARKETPLACE_URL = 'https://marketplace.emag.ro/'
MARKETPLACE_API_URL = 'https://marketplace-api.emag.ro/api-3'
ORDERS_ENDPOINT = "/order"

def count_orders(MARKETPLACE_API_URL, ORDERS_ENDPOINT, COUNT_ENGPOINT, API_KEY, PUBLIC_KEY=None, usePublicKey=False):
    url = f"{MARKETPLACE_API_URL}{ORDERS_ENDPOINT}/{COUNT_ENGPOINT}"
    if usePublicKey is False:
        api_key = str(API_KEY).replace("b'", '').replace("'", "")
        headers = {
            "Authorization": f"Basic {api_key}",
            "Content-Type": "application/json"
        }
    else:
        headers = {
            "X-Request-Public-Key": f"{PUBLIC_KEY}",
            "X-Request-Signature": f"{API_KEY}"
        }

    modifiedAfter_date = datetime.datetime.today() - datetime.timedelta(days=3)
    modifiedAfter_date = modifiedAfter_date.strftime('%Y-%m-%d')
    data = json.dumps({
        "modifiedAfter": modifiedAfter_date
    })
    response = requests.post(url, data=data, headers=headers)
    if response.status_code == 200:
        logging.info("success to count orders")
        return response.json()
    else:
        logging.info(f"Failed to retrieve orders: {response.status_code}")
        return None
    
def count_months_orders(MARKETPLACE_API_URL, ORDERS_ENDPOINT, COUNT_ENGPOINT, API_KEY, PUBLIC_KEY=None, usePublicKey=False):
    url = f"{MARKETPLACE_API_URL}{ORDERS_ENDPOINT}/{COUNT_ENGPOINT}"
    if usePublicKey is False:
        api_key = str(API_KEY).replace("b'", '').replace("'", "")
        headers = {
            "Authorization": f"Basic {api_key}",
            "Content-Type": "application/json"
        }
    else:
        headers = {
            "X-Request-Public-Key": f"{PUBLIC_KEY}",
            "X-Request-Signature": f"{API_KEY}"
        }

    modifiedAfter_date = datetime.datetime.today() - datetime.timedelta(days=180)
    modifiedAfter_date = modifiedAfter_date.strftime('%Y-%m-%d')
    data = json.dumps({
        "modifiedAfter": modifiedAfter_date
    })
    response = requests.post(url, data=data, headers=headers)
    if response.status_code == 200:
        logging.info("success to count orders")
        return response.json()
    else:
        logging.info(f"Failed to retrieve orders: {response.status_code}")
        return None
    
def count_all_orders(MARKETPLACE_API_URL, ORDERS_ENDPOINT, COUNT_ENGPOINT, API_KEY, PUBLIC_KEY=None, usePublicKey=False):
    url = f"{MARKETPLACE_API_URL}{ORDERS_ENDPOINT}/{COUNT_ENGPOINT}"
    if usePublicKey is False:
        api_key = str(API_KEY).replace("b'", '').replace("'", "")
        headers = {
            "Authorization": f"Basic {api_key}",
            "Content-Type": "application/json"
        }
    else:
        headers = {
            "X-Request-Public-Key": f"{PUBLIC_KEY}",
            "X-Request-Signature": f"{API_KEY}"
        }

    modifiedAfter_date = datetime.datetime.today() - datetime.timedelta(days=3)
    modifiedAfter_date = modifiedAfter_date.strftime('%Y-%m-%d')

    MAX_RETRIES = 5
    retry_delay = 5  # seconds

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, headers=headers, timeout=20)
            if response.status_code == 200:
                return response.json()
            else:
                logging.info(f"Failed to retrieve orders: {response.status_code}")
                return None
        except requests.Timeout:
            logging.warning(f"Request timed out. Attempt {attempt + 1} of {MAX_RETRIES}. Retrying...")
            time.sleep(retry_delay)
    logging.error("All attempts failed. Could not retrieve orders.")
    return None
    
def get_orders(MARKETPLACE_API_URL, ORDERS_ENDPOINT, READ_ENDPOINT,  API_KEY, currentPage, PUBLIC_KEY=None, usePublicKey=False):
    url = f"{MARKETPLACE_API_URL}{ORDERS_ENDPOINT}/{READ_ENDPOINT}"
    if usePublicKey is True:
        headers = {
            "X-Request-Public-Key": f"{PUBLIC_KEY}",
            "X-Request-Signature": f"{API_KEY}"
        }
    elif usePublicKey is False:
        api_key = str(API_KEY).replace("b'", '').replace("'", "")
        headers = {
            "Authorization": f"Basic {api_key}",
            "Content-Type": "application/json"
        }

    modifiedAfter_date = datetime.datetime.today() - datetime.timedelta(days=3)
    modifiedAfter_date = modifiedAfter_date.strftime('%Y-%m-%d')
    
    data = json.dumps({
        "itemsPerPage": 100,
        "currentPage": currentPage,
        "modifiedAfter": modifiedAfter_date
    })
    MAX_RETRIES = 5
    retry_delay = 5  # seconds

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(url, data=data, headers=headers, timeout=20)
            if response.status_code == 200:
                return response.json()
            else:
                logging.info(f"Failed to retrieve orders: {response.status_code}")
                return None
        except requests.Timeout:
            logging.warning(f"Request timed out. Attempt {attempt + 1} of {MAX_RETRIES}. Retrying...")
            time.sleep(retry_delay)
    logging.error("All attempts failed. Could not retrieve orders.")
    return None

def get_months_orders(MARKETPLACE_API_URL, ORDERS_ENDPOINT, READ_ENDPOINT,  API_KEY, currentPage, PUBLIC_KEY=None, usePublicKey=False):
    url = f"{MARKETPLACE_API_URL}{ORDERS_ENDPOINT}/{READ_ENDPOINT}"
    if usePublicKey is True:
        headers = {
            "X-Request-Public-Key": f"{PUBLIC_KEY}",
            "X-Request-Signature": f"{API_KEY}"
        }
    elif usePublicKey is False:
        api_key = str(API_KEY).replace("b'", '').replace("'", "")
        headers = {
            "Authorization": f"Basic {api_key}",
            "Content-Type": "application/json"
        }

    modifiedAfter_date = datetime.datetime.today() - datetime.timedelta(days=180)
    modifiedAfter_date = modifiedAfter_date.strftime('%Y-%m-%d')
    
    data = json.dumps({
        "itemsPerPage": 100,
        "currentPage": currentPage,
        "modifiedAfter": modifiedAfter_date
    })
    MAX_RETRIES = 5
    retry_delay = 5  # seconds

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(url, data=data, headers=headers, timeout=20)
            if response.status_code == 200:
                return response.json()
            else:
                logging.info(f"Failed to retrieve orders: {response.status_code}")
                return None
        except requests.Timeout:
            logging.warning(f"Request timed out. Attempt {attempt + 1} of {MAX_RETRIES}. Retrying...")
            time.sleep(retry_delay)
    logging.error("All attempts failed. Could not retrieve orders.")
    return None

def get_all_orders(MARKETPLACE_API_URL, ORDERS_ENDPOINT, READ_ENDPOINT,  API_KEY, currentPage, PUBLIC_KEY=None, usePublicKey=False):
    url = f"{MARKETPLACE_API_URL}{ORDERS_ENDPOINT}/{READ_ENDPOINT}"
    if usePublicKey is True:
        headers = {
            "X-Request-Public-Key": f"{PUBLIC_KEY}",
            "X-Request-Signature": f"{API_KEY}"
        }
    elif usePublicKey is False:
        api_key = str(API_KEY).replace("b'", '').replace("'", "")
        headers = {
            "Authorization": f"Basic {api_key}",
            "Content-Type": "application/json"
        }

    modifiedAfter_date = datetime.datetime.today() - datetime.timedelta(days=3)
    modifiedAfter_date = modifiedAfter_date.strftime('%Y-%m-%d')
    
    data = json.dumps({
        "itemsPerPage": 100,
        "currentPage": currentPage
    })
    response = requests.post(url, data=data, headers=headers)
    if response.status_code == 200:
        orders = response.json()
        return orders
    else:
        print(f"Failed to retrieve orders: {response.status_code}")
        return None

def acknowledge(MARKETPLACE_API_URL, ORDERS_ENDPOINT, API_KEY, order_id):
    url = f"{MARKETPLACE_API_URL}{ORDERS_ENDPOINT}/acknowledge/{order_id}"
    api_key = str(API_KEY).replace("b'", '').replace("'", "")
    headers = {
        "Authorization": f"Basic {api_key}",
        "Content-Type": "application/json"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to retrieve orders: {response.status_code}")
        return None
    
async def insert_orders(orders, marketplace: Marketplace):
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
            ) ON CONFLICT (id, user_id) DO UPDATE SET
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
                attachments = EXCLUDED.attachments,
                emag_club = EXCLUDED.emag_club,
                finalization_date = EXCLUDED.finalization_date,
                details = EXCLUDED.details,
                payment_mode_id = EXCLUDED.payment_mode_id,
                product_voucher_split = EXCLUDED.product_voucher_split
        """).format(sql.Identifier("orders"))
        
        for order in orders:
            customer = order.get('customer', {})
            customer_id = customer.get('id')
            customer_mkt_id = customer.get('mkt_id')
            customer_name = customer.get('name')
            customer_company = customer.get('company')
            customer_gender = customer.get('gender')
            customer_phone_1 = customer.get('phone_1')
            customer_billing_name = customer.get('billing_name')
            customer_billing_phone = customer.get('billing_phone')
            customer_billing_country = customer.get('billing_country')
            customer_billing_suburb = customer.get('billing_suburb')
            customer_billing_city = customer.get('billing_city')
            customer_billing_locality_id = customer.get('billing_locality_id')
            customer_billing_street = customer.get('billing_street')
            customer_shipping_country = customer.get('shipping_country')
            customer_shipping_suburb = customer.get('shipping_suburb')
            customer_shipping_city = customer.get('shipping_city')
            customer_shipping_locality_id = customer.get('shipping_locality_id')
            customer_shipping_street = customer.get('shipping_street')
            customer_shipping_contact = customer.get('shipping_contact')
            customer_shipping_phone = customer.get('shipping_phone')
            customer_created = customer.get('created')
            customer_modified = customer.get('modified')
            customer_legal_entity = customer.get('legal_entity')
            customer_is_vat_payer = customer.get('is_vat_payer')
            code = customer.get('code')
            bank = customer.get('bank')
            iban = customer.get('iban')
            email = customer.get('email')
            registration_number = customer.get('registration_number')

            id = order.get('id')
            vendor_name = order.get('vendor_name')
            type = order.get('type')
            date = order.get('date')
            payment_mode = order.get('payment_mode')
            detailed_payment_method = order.get('detailed_payment_method')
            delivery_mode = order.get('delivery_mode')
            status = order.get('status')
            if status == 1:
                logging.info(f"order_{id} is new order")
                USERNAME = marketplace.credentials["firstKey"]
                PASSWORD = marketplace.credentials["secondKey"]
                API_KEY = base64.b64encode(f"{USERNAME}:{PASSWORD}".encode('utf-8'))
                result = acknowledge(marketplace.baseAPIURL, marketplace.orders_crud["endpoint"], API_KEY, id)
                logging.info(result)
            payment_status = order.get('payment_status')
            products_id = [str(product.get('product_id')) for product in order.get('products')]
            quantity = [product.get('quantity') for product in order.get('products')]
            sale_price = [Decimal(product.get('sale_price', '0')) for product in order.get('products')]
            shipping_tax = Decimal(order.get('shipping_tax'))
            shipping_tax_voucher_split = json.dumps(order.get('shipping_tax_voucher_split', []))
            vouchers = json.dumps(order.get('vouchers'))
            proforms = json.dumps(order.get('proforms'))
            attachments = json.dumps(order.get('attachments'))
            shipping_address = customer_shipping_street
            if order.get('cashed_co'):
                cashed_co = Decimal(order.get('cashed_co'))
            else:
                cashed_co = Decimal('0')
            cashed_cod = Decimal(order.get('cashed_cod'))
            refunded_amount = order.get('refunded_amount')
            is_complete = order.get('is_complete')
            cancellation_request = order.get('cancellation_request') if order.get('cancellation_request') else ''
            cancellation_reason = str(order.get('reason_cancellation'))
            refund_status = order.get('refund_status')
            maximum_date_for_shipment = order.get('maximum_date_for_shipment')
            late_shipment = order.get('late_shipment')
            flags = json.dumps(order.get('flags'))
            emag_club = order.get('emag_club')
            finalization_date = order.get('finalization_date')
            details = json.dumps(order.get('details'))
            payment_mode_id = order.get('payment_mode_id')
            product_voucher_split = [str(product.get('product_voucher_split')) for product in order.get('products')]
            order_martet_place = marketplace.marketplaceDomain
            user_id = marketplace.user_id
            
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

async def refresh_emag_orders(marketplace: Marketplace):
    # create_database()

    logging.info(f">>>>>>> Refreshing Marketplace : {marketplace.title} user is {marketplace.user_id} <<<<<<<<")
    orders_table = f"{marketplace.marketplaceDomain.replace('.', '_')}_orders".lower()
    
    settings.orders_table_name.append(orders_table)

    if marketplace.credentials["type"] == "user_pass":
        USERNAME = marketplace.credentials["firstKey"]
        PASSWORD = marketplace.credentials["secondKey"]
        API_KEY = base64.b64encode(f"{USERNAME}:{PASSWORD}".encode('utf-8'))
        result = count_orders(marketplace.baseAPIURL, marketplace.orders_crud["endpoint"], marketplace.orders_crud["count"], API_KEY)
        if result:
            pages = result['results']['noOfPages']
            items = result['results']['noOfItems']

            logging.info(f"Number of Pages: {pages}")
            logging.info(f"Number of Items: {items}")

            # currentPage = int(pages)
            currentPage = 1
            baseAPIURL = marketplace.baseAPIURL
            endpoint = marketplace.orders_crud['endpoint']
            read_endpoint = marketplace.orders_crud['read']
            try:
                while currentPage <= int(pages):
                    orders = get_orders(baseAPIURL, endpoint, read_endpoint, API_KEY, currentPage)
                    print(f">>>>>>> Current Page : {currentPage} <<<<<<<<")
                    if orders and orders['isError'] == False:
                        # await insert_orders_into_db(orders['results'], customer_table, orders_table, marketplace.marketplaceDomain)
                        await insert_orders(orders['results'], marketplace)
                    currentPage += 1
            except Exception as e:
                print('++++++++++++++++++++++++++++++++++++++++++')
                print(e)

async def refresh_months_emag_orders(marketplace: Marketplace):
    # create_database()

    logging.info(f">>>>>>> Refreshing Marketplace : {marketplace.title} user is {marketplace.user_id} <<<<<<<<")
    orders_table = f"{marketplace.marketplaceDomain.replace('.', '_')}_orders".lower()
    
    settings.orders_table_name.append(orders_table)

    if marketplace.credentials["type"] == "user_pass":
        USERNAME = marketplace.credentials["firstKey"]
        PASSWORD = marketplace.credentials["secondKey"]
        API_KEY = base64.b64encode(f"{USERNAME}:{PASSWORD}".encode('utf-8'))
        result = count_months_orders(marketplace.baseAPIURL, marketplace.orders_crud["endpoint"], marketplace.orders_crud["count"], API_KEY)
        if result:
            pages = result['results']['noOfPages']
            items = result['results']['noOfItems']

            logging.info(f"Number of Pages: {pages}")
            logging.info(f"Number of Items: {items}")

            # currentPage = int(pages)
            currentPage = 1
            baseAPIURL = marketplace.baseAPIURL
            endpoint = marketplace.orders_crud['endpoint']
            read_endpoint = marketplace.orders_crud['read']
            try:
                while currentPage <= int(pages):
                    orders = get_months_orders(baseAPIURL, endpoint, read_endpoint, API_KEY, currentPage)
                    print(f">>>>>>> Current Page : {currentPage} <<<<<<<<")
                    if orders and orders['isError'] == False:
                        # await insert_orders_into_db(orders['results'], customer_table, orders_table, marketplace.marketplaceDomain)
                        await insert_orders(orders['results'], marketplace)
                    currentPage += 1
            except Exception as e:
                print('++++++++++++++++++++++++++++++++++++++++++')
                print(e)

async def refresh_emag_all_orders(marketplace: Marketplace, db:AsyncSession):
    # create_database()

    logging.info(f">>>>>>> Refreshing Marketplace : {marketplace.title} user is {marketplace.user_id} <<<<<<<<")
    orders_table = f"{marketplace.marketplaceDomain.replace('.', '_')}_orders".lower()
    
    settings.orders_table_name.append(orders_table)

    endpoint = "/order"
    read_endpoint = "/read"
    count_endpoint = "/count"
    
    USERNAME = marketplace.credentials["firstKey"]
    PASSWORD = marketplace.credentials["secondKey"]
    API_KEY = base64.b64encode(f"{USERNAME}:{PASSWORD}".encode('utf-8'))
    result = count_all_orders(marketplace.baseAPIURL, endpoint, count_endpoint, API_KEY)
    if result:
        pages = result['results']['noOfPages']
        items = result['results']['noOfItems']

        logging.info(f"Number of Pages: {pages}")
        logging.info(f"Number of Items: {items}")

        # currentPage = int(pages)
        currentPage = 1
        baseAPIURL = marketplace.baseAPIURL
        try:
            while currentPage <= int(pages):
                orders = get_all_orders(baseAPIURL, endpoint, read_endpoint, API_KEY, currentPage)
                print(f">>>>>>> Current Page : {currentPage} <<<<<<<<")
                if orders and orders['isError'] == False:
                    # await insert_orders_into_db(orders['results'], customer_table, orders_table, marketplace.marketplaceDomain)
                    await insert_orders(orders['results'], marketplace)
                currentPage += 1
        except Exception as e:
            print('++++++++++++++++++++++++++++++++++++++++++')
            print(e)
            
def change_status(order_id: int, marketplace: Marketplace):
    USERNAME = marketplace.credentials["firstKey"]
    PASSWORD = marketplace.credentials["secondKey"]
    API_KEY = base64.b64encode(f"{USERNAME}:{PASSWORD}".encode('utf-8'))
    url = f"{marketplace.baseAPIURL}/order/read"
    
    api_key = str(API_KEY).replace("b'", '').replace("'", "")
    headers = {
        "Authorization": f"Basic {api_key}",
        "Content-Type": "application/json"
    }
    
    data = json.dumps({
        "id": order_id
    })
    response = requests.post(url, data=data, headers=headers)
    if response.status_code != 200:
        return response.json()
    result = response.json()
    order = result.get('results')[0]
    order['status'] = 5
    order = [order]
    
    save_url = f"{marketplace.baseAPIURL}/order/save"
    save_data = json.dumps(order)
    
    save_response = requests.post(save_url, data=save_data, headers=headers)
    return save_response.json()
        