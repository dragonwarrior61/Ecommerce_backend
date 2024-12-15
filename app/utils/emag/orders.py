import datetime
import json
import logging
import psycopg2
from decimal import Decimal
from fastapi import HTTPException
from psycopg2 import sql

from app.config import settings
from app.models import Marketplace
from app.utils.auth_market import get_auth_marketplace
from app.utils.httpx_request import send_post_request, send_get_request

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def count_orders(marketplace: Marketplace, period = 3):
    MARKETPLACE_API_URL = marketplace.baseAPIURL
    ORDERS_ENDPOINT = marketplace.orders_crud["endpoint"]
    COUNT_ENGPOINT = marketplace.orders_crud["count"]

    url = f"{MARKETPLACE_API_URL}/{ORDERS_ENDPOINT}/{COUNT_ENGPOINT}"

    headers = get_auth_marketplace(marketplace)

    modifiedAfter_date = datetime.datetime.today() - datetime.timedelta(days=period)
    modifiedAfter_date = modifiedAfter_date.strftime('%Y-%m-%d')
    data = json.dumps({
        "modifiedAfter": modifiedAfter_date
    })
    response = await send_post_request(url, headers, "count orders", data)
    if response.status_code != 200:
        logging.error(f"Failed to count orders from {MARKETPLACE_API_URL}: {response.text}")
    return response.json()

async def get_orders(marketplace: Marketplace, currentPage, period=3):
    MARKETPLACE_API_URL = marketplace.baseAPIURL
    ORDERS_ENDPOINT = marketplace.orders_crud["endpoint"]
    READ_ENDPOINT = marketplace.orders_crud["read"]
    url = f"{MARKETPLACE_API_URL}{ORDERS_ENDPOINT}/{READ_ENDPOINT}"
    headers = get_auth_marketplace(marketplace)
    modifiedAfter_date = datetime.datetime.today() - datetime.timedelta(days=period)
    modifiedAfter_date = modifiedAfter_date.strftime('%Y-%m-%d')
    data = json.dumps({
        "itemsPerPage": 100,
        "currentPage": currentPage,
        "modifiedAfter": modifiedAfter_date
    })
    response = await send_post_request(url, headers, "get orders", data)
    if response.status_code != 200:
        logging.error(f"Failed to get orders from {MARKETPLACE_API_URL}: {response.text}")
    return response.json()

async def acknowledge(marketplace: Marketplace, order_id):
    MARKETPLACE_API_URL = marketplace.baseAPIURL
    ORDERS_ENDPOINT = marketplace.orders_crud["endpoint"]
    url = f"{MARKETPLACE_API_URL}{ORDERS_ENDPOINT}/acknowledge/{order_id}"
    headers = get_auth_marketplace(marketplace)

    response = await send_get_request(url, headers, f"acknowledge order {order_id}")
    if response.status_code != 200:
        logging.error(f"Failed to acknowledge order {order_id}: {response.text}")
    return response

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
                initial_quantity,
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
                update_time,
                user_id
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            ) ON CONFLICT (id, user_id) DO UPDATE SET
                vendor_name = EXCLUDED.vendor_name,
                type = EXCLUDED.type,
                date = EXCLUDED.date,
                payment_mode = EXCLUDED.payment_mode,
                status = EXCLUDED.status,
                payment_status = EXCLUDED.payment_status,
                product_id = EXCLUDED.product_id,
                quantity = EXCLUDED.quantity,
                initial_quantity = EXCLUDED.initial_quantity,
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
                update_time = EXCLUDED.update_time,
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
                result = await acknowledge(marketplace, id)
                logging.info(result)
            payment_status = order.get('payment_status')
            products_id = [str(product.get('product_id')) for product in order.get('products')]
            quantity = [product.get('quantity') for product in order.get('products')]
            initial_quantity = [product.get('initial_qty') for product in order.get('products')]
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
            update_time = datetime.datetime.now()
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
                initial_quantity,
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
                update_time,
                user_id
            )

            cursor_order.execute(insert_orders_query, values)
            conn.commit()
        cursor_order.close()
        conn.close()
        logging.info("Orders inserted successfully")
    except Exception as e:
        logging.info(f"Failed to insert orders into database: {e}")

async def refresh_emag_orders(marketplace: Marketplace, period=3):
    logging.info(f">>>>>>> Refreshing Marketplace : {marketplace.title} user is {marketplace.user_id} <<<<<<<<")

    result = await count_orders(marketplace)
    if result and result['isError'] == False:
        pages = result['results']['noOfPages']
        items = result['results']['noOfItems']

        logging.info(f"Number of Pages: {pages}")
        logging.info(f"Number of Items: {items}")

        # currentPage = int(pages)
        currentPage = 1
        while currentPage <= int(pages):
            try:
                orders = await get_orders(marketplace, currentPage, period)
                logging.info(f">>>>>>> Current Page : {currentPage} <<<<<<<<")
                if orders and orders['isError'] == False:
                    # await insert_orders_into_db(orders['results'], customer_table, orders_table, marketplace.marketplaceDomain)
                    await insert_orders(orders['results'], marketplace)
                currentPage += 1
            except Exception as e:
                logging.error(f"Error occured while ")

async def change_status(order_id: int, marketplace: Marketplace):
    url = f"{marketplace.baseAPIURL}/order/read"
    headers = get_auth_marketplace(marketplace)
    data = json.dumps({
        "id": order_id
    })
    response = await send_post_request(url=url, data=data, headers=headers, error_msg=f"update order {order_id}")
    if response.status_code != 200:
        logging.error(f"Failed to change status to {marketplace.baseURL}: {response.text}")
        return response.json()
    result = response.json()
    order = result.get('results')[0]
    order['status'] = 5
    order = [order]
    save_url = f"{marketplace.baseAPIURL}/order/save"
    save_data = json.dumps(order)
    response = await send_post_request(url=save_url, data=save_data, headers=headers, error_msg=f"update order {order_id}")
    if response.status_code != 200:
        logging.error(f"Failed to update order from {marketplace.baseURL}: {response.text}")
    return response.json()
