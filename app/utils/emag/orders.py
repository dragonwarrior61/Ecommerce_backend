import asyncio, json, logging
from decimal import Decimal
from sqlalchemy.future import select
from datetime import datetime, timezone, timedelta

from app.database import get_db
from app.models import AWB, Marketplace, Order
from app.utils.auth_market import get_auth_marketplace
from app.utils.httpx_request import send_post_request, send_get_request
from app.logfiles import log_refresh_orders, log_refresh_month_order

# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.getLogger("sqlalchemy").setLevel(logging.ERROR)

def log_message(message: str, period = 3):
    if period == 3:
        log_refresh_orders(message)
    else:
        log_refresh_month_order(message)

async def count_orders(marketplace: Marketplace, period = 3):
    MARKETPLACE_API_URL = marketplace.baseAPIURL
    ORDERS_ENDPOINT = marketplace.orders_crud["endpoint"]
    COUNT_ENGPOINT = marketplace.orders_crud["count"]

    url = f"{MARKETPLACE_API_URL}/{ORDERS_ENDPOINT}/{COUNT_ENGPOINT}"

    headers = get_auth_marketplace(marketplace)

    modifiedAfter_date = datetime.today() - timedelta(days=period)
    modifiedAfter_date = modifiedAfter_date.strftime('%Y-%m-%d')
    data = json.dumps({
        "modifiedAfter": modifiedAfter_date
    })
    response = await send_post_request(url, headers, "count orders", data)
    if response.status_code != 200:
        logging.error(f"Failed to count orders from {MARKETPLACE_API_URL}: {response.text}")
    return response.json()

async def get_orders(marketplace: Marketplace, currentPage, period=3):
    try:
        MARKETPLACE_API_URL = marketplace.baseAPIURL
        ORDERS_ENDPOINT = marketplace.orders_crud["endpoint"]
        READ_ENDPOINT = marketplace.orders_crud["read"]
        url = f"{MARKETPLACE_API_URL}{ORDERS_ENDPOINT}/{READ_ENDPOINT}"
        headers = get_auth_marketplace(marketplace)
        modifiedAfter_date = datetime.today() - timedelta(days=period)
        modifiedAfter_date = modifiedAfter_date.strftime('%Y-%m-%d')
        data = json.dumps({
            "itemsPerPage": 100,
            "currentPage": currentPage,
            "modifiedAfter": modifiedAfter_date
        })
    except Exception as e:
        log_message(f"Failed to authenticate marketplace: {e}", period)
    response = await send_post_request(url, headers=headers, data=data)
    return response

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
    async for db in get_db():
        async with db as session:
            date_2_hours_ago = datetime.now(timezone.utc) - timedelta(hours=2)
            date_1_hours_ago = datetime.now(timezone.utc) - timedelta(hours=1)
            for order in orders:
                try:
                    order_id = order.get('id')
                    new_status = order.get('status')
                    customer = order.get('customer', {})
                    products = order.get('products', [])
                    order_processed = Order(
                        id = order_id,
                        vendor_name = order.get('vendor_name'),
                        type = order.get('type'),
                        date = datetime.strptime(order.get('date'), '%Y-%m-%d %H:%M:%S'),
                        payment_mode = order.get('payment_mode'),
                        detailed_payment_method = order.get('detailed_payment_method'),
                        delivery_mode = order.get('delivery_mode'),
                        status = new_status,
                        payment_status = order.get('payment_status'),
                        product_id = [str(product.get('product_id')) for product in products],
                        quantity = [product.get('quantity') for product in products],
                        initial_quantity = [product.get('initial_qty') for product in products],
                        sale_price = [Decimal(product.get('sale_price', '0')) for product in products],
                        shipping_tax = Decimal(order.get('shipping_tax')),
                        shipping_tax_voucher_split = json.dumps(order.get('shipping_tax_voucher_split', [])),
                        vouchers = json.dumps(order.get('vouchers')),
                        proforms = json.dumps(order.get('proforms')),
                        attachments = json.dumps(order.get('attachments')),
                        shipping_address = customer.get('shipping_street'),
                        cashed_cod = Decimal(order.get('cashed_cod')),
                        refunded_amount = Decimal(order.get('refunded_amount')),
                        is_complete = order.get('is_complete'),
                        cancellation_request = order.get('cancellation_request'),
                        cancellation_reason = str(order.get('reason_cancellation')),
                        refund_status = order.get('refund_status'),
                        maximum_date_for_shipment = datetime.strptime(order.get('maximum_date_for_shipment'), '%Y-%m-%d %H:%M:%S'),
                        late_shipment = order.get('late_shipment'),
                        flags = json.dumps(order.get('flags')),
                        emag_club = order.get('emag_club'),
                        finalization_date = datetime.strptime(order.get('finalization_date'), '%Y-%m-%d %H:%M:%S') if order.get('finalization_date') else None,
                        details = json.dumps(order.get('details')),
                        payment_mode_id = order.get('payment_mode_id'),
                        product_voucher_split = [str(product.get('product_voucher_split')) for product in order.get('products')],
                        order_market_place = marketplace.marketplaceDomain,
                        update_time = datetime.now(),
                        user_id = marketplace.user_id,
                        customer_id = customer.get('id'),
                        mkt_id = customer.get('mkt_id'),
                        name = customer.get('name'),
                        company = customer.get('company'),
                        gender = customer.get('gender'),
                        phone_1 = customer.get('phone_1'),
                        billing_name = customer.get('billing_name'),
                        billing_phone = customer.get('billing_phone'),
                        billing_country = customer.get('billing_country'),
                        billing_suburb = customer.get('billing_suburb'),
                        billing_city = customer.get('billing_city'),
                        billing_locality_id = customer.get('billing_locality_id'),
                        billing_street = customer.get('billing_street'),
                        shipping_country = customer.get('shipping_country'),
                        shipping_suburb = customer.get('shipping_suburb'),
                        shipping_city = customer.get('shipping_city'),
                        shipping_locality_id = customer.get('shipping_locality_id'),
                        shipping_street = customer.get('shipping_street'),
                        shipping_contact = customer.get('shipping_contact'),
                        shipping_phone = customer.get('shipping_phone'),
                        created = datetime.strptime(customer.get('created'), '%Y-%m-%d %H:%M:%S'),
                        modified = datetime.strptime(customer.get('modified'), '%Y-%m-%d %H:%M:%S'),
                        legal_entity = customer.get('legal_entity'),
                        is_vat_payer = customer.get('is_vat_payer'),
                        code = customer.get('code'),
                        bank = customer.get('bank'),
                        iban = customer.get('iban'),
                        email = customer.get('email'),
                        registration_number = customer.get('registration_number'),
                        cashed_co = Decimal(order.get('cashed_co')) if order.get('cashed_co') else Decimal('0')
                    )
                    try:
                        result = await session.execute(select(Order).where(Order.id == order_id))
                        order_db = result.scalars().first()
                    except Exception as e:
                        logging.error(f"Failed to get order {order_id} from database: {e}")
                        log_refresh_orders(f"Failed to get order {order_id} from database: {e}")
                        await session.rollback()
                    try:
                        if order_db:
                            fetched_time = order_db.update_time
                            if fetched_time:
                                fetched_time = fetched_time.replace(tzinfo=timezone.utc)
                            await session.merge(order_processed)
                            order_db.vendor_name = order_processed.vendor_name
                            order_db.type = order_processed.type
                            order_db.date = order_processed.date
                            order_db.payment_mode = order_processed.payment_mode
                            order_db.status = order_processed.status
                            order_db.payment_status = order_processed.payment_status
                            order_db.product_id = order_processed.product_id
                            order_db.quantity = order_processed.quantity
                            order_db.initial_quantity = order_processed.initial_quantity
                            order_db.sale_price = order_processed.sale_price
                            order_db.shipping_tax = order_processed.shipping_tax
                            order_db.shipping_tax_voucher_split = order_processed.shipping_tax_voucher_split
                            order_db.refunded_amount = order_processed.refunded_amount
                            order_db.cancellation_request = order_processed.cancellation_request
                            order_db.cancellation_reason = order_processed.cancellation_reason
                            order_db.is_complete = order_processed.is_complete
                            order_db.refund_status = order_processed.refund_status
                            order_db.attachments = order_processed.attachments
                            order_db.emag_club = order_processed.emag_club
                            order_db.finalization_date = order_processed.finalization_date
                            order_db.details = order_processed.details
                            order_db.payment_mode_id = order_processed.payment_mode_id
                            order_db.update_time = order_processed.update_time
                            order_db.product_voucher_split = order_processed.product_voucher_split
                            try:
                                result = await session.execute(select(AWB).where(AWB.order_id == order_id))
                                awbs = result.scalars().all()
                            except Exception as e:
                                logging.error(f"Failed to get awb of order {order_id} from database: {e}")
                                log_refresh_orders(f"Failed to get awb of order {order_id} from database: {e}")
                                await session.rollback()
                            for awb in awbs:
                                if awb and not awb.awb_barcode:
                                    awb_date = awb.awb_date
                                    if awb_date:
                                        awb_date = awb_date.replace(tzinfo=timezone.utc)
                                    print(f"Order {order_id} has awb, but not have awb_barcode ({awb_date}).")
                                    if awb_date < date_2_hours_ago and fetched_time < date_1_hours_ago and new_status in [1, 2, 3]:
                                        try:
                                            await session.delete(awb)
                                            logging.warning(f"The empty AWB of order {order_id} was deleted.")
                                            log_refresh_orders(f"The empty AWB of order {order_id} was deleted.")
                                        except Exception as e:
                                            logging.error(f"Failed to delete awb of order {order_id}: {e}")
                                            log_refresh_orders(f"Failed to delete awb of order {order_id}: {e}")
                                            await session.rollback()
                        else:
                            session.add(order_processed)
                        await session.commit()
                    except Exception as e:
                        logging.error(f"Failed to insert or update order {order_id}: {e}")
                        log_refresh_orders(f"Failed to insert or update order {order_id}: {e}")
                        await session.rollback()
                except Exception as e:
                    logging.error(f"Failed to insert or update order {order_id}: {e}")
                    log_refresh_orders(f"Failed to insert or update order {order_id}: {e}")

async def refresh_emag_orders(marketplace: Marketplace, period=3):
    logging.info(f">>>>>>> Refreshing Marketplace : {marketplace.title} user is {marketplace.user_id} <<<<<<<<")

    result = await count_orders(marketplace)
    log_message(f"count result is: {result}", period)
    if result and result.get('isError', True) == False:
        pages = result['results']['noOfPages']
        items = result['results']['noOfItems']

        logging.info(f"Number of Pages: {pages}")
        logging.info(f"Number of Items: {items}")

        # currentPage = int(pages)
        currentPage = 1
        while currentPage <= int(pages):
            try:
                log_message(f"Started fetching orders from emag: page {currentPage}", period)
                for i in range(3):
                    try:
                        response = await get_orders(marketplace, currentPage, period)
                    except Exception as e:
                        log_message(f"Failed to get orders (attempt {i + 1} of 3): {e}", period)
                        logging.error(f"Failed to get orders (attempt {i + 1} of 3): {e}")
                        await asyncio.sleep(1)
                if not response or response.status_code != 200:
                    log_message(f"Failed to get orders: {response.text}", period)
                    logging.error(f"Failed to get orders: {response.text}")
                    currentPage += 1
                    continue
                logging.info(f">>>>>>> Current Page : {currentPage} <<<<<<<<")
                order_response = response.json()
                if order_response.get('isError', True) == False:
                    for i in range(3):
                        try:
                            await insert_orders(order_response['results'], marketplace)
                            break
                        except Exception as e:
                            log_message(f"Failed to insert orders (attempt {i + 1} of 3): {e}", period)

            except Exception as e:
                logging.error(f"Error occured while refreshing emag orders: {e}")
                log_message(f"Error occured while refreshing emag orders: {e}", period)
            currentPage += 1

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
