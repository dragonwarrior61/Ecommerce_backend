from apscheduler.schedulers.asyncio import AsyncIOScheduler
# from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from fastapi import Depends
from openpyxl import Workbook
from sqlalchemy import select, any_, cast, BigInteger
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio
import logging
# import ssl

from app.database import get_db
from app.models import (
    AWB,
    Billing_software,
    Damaged_good,
    Internal_Product,
    Invoice,
    Marketplace,
    Order,
    Product
)
from app.utils.emag.products import refresh_emag_products, post_stock_emag
from app.utils.emag.orders import refresh_emag_orders
from app.utils.emag.returns import refresh_emag_returns
from app.utils.emag.courier import refresh_emag_couriers
from app.utils.emag.invoice import post_factura_pdf
from app.utils.altex.product import refresh_altex_products
from app.utils.altex.orders import refresh_altex_orders
from app.utils.altex.returns import refresh_altex_rmas
from app.utils.smart_api import get_stock, refresh_invoice
from app.utils.sameday import tracking, auth_sameday
from app.logfiles import (
    log_generate_invoice,
    log_msg_file,
    log_refresh_month_order,
    log_refresh_orders,
    log_refresh_returns,
    log_refresh_stock,
    log_send_stock,
    log_update_awb
)

logging.getLogger("sqlalchemy").setLevel(logging.CRITICAL)

# app = FastAPI()

# ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
# ssl_context.load_cert_chain('ssl/cert.pem', keyfile='ssl/key.pem')

# async def on_startup(db: AsyncSession = Depends(get_db)):
#     async for db in get_db():
#         async with db as session:
#             print("Starting localities refresh")
#             result = await session.execute(select(Marketplace).order_by(Marketplace.id.asc()))
#             marketplaces = result.scalars().all()
#             print(f"Success getting {len(marketplaces)} marketplaces")
#             for marketplace in marketplaces:
#                 if marketplace.marketplaceDomain == "altex.ro":
#                     # print("Refresh locations from altex")
#                     # await refresh_altex_locations(marketplace)
#                     # print("Refresh couriers from altex")
#                     # await refresh_altex_couriers(marketplace)
#                     continue
#                 else:
#                     # print("Refresh localities from marketplace")
#                     # await refresh_emag_localities(marketplace)
#                     print("Refresh couriers refresh")
#                     await refresh_emag_couriers(marketplace)
#                     # print("Refresh orders form marketplace")
#                     # await refresh_emag_all_orders(marketplace, session)
#                     continue

# async def update_invoice_post(db: AsyncSession = Depends(get_db)):
#     async for db in get_db():
#         async with db as session:
#             try:
#                 print("Starting post invoices")
#                 result = await session.execute(select(Invoice).where(Invoice.user_id == 1, Invoice.seriesName != 'EMGINL'))
#                 invoices = result.scalars().all()

#                 for invoice in invoices:
#                     order_id = invoice.order_id
#                     series = invoice.seriesName
#                     number = invoice.number
#                     name = f"factura_{series}{number}.pdf"
#                     country = series[-2:]
#                     result = await session.execute(select(Marketplace).where(Marketplace.country.upper() == country, Marketplace.user_id == 1))
#                     marketplace = result.scalars().first()
#                     result = await post_factura_pdf(order_id, name, marketplace)
#                     if result is None:
#                         continue
#                     invoice.post = 1
#                 await session.commit()
#             except Exception as e:
#                 print(f"Error in post invoice: {e}")

# async def update_damaged_goods(db: AsyncSession = Depends(get_db)):
#     async for db in get_db():
#         async with db as session:
#             try:
#                 print("Starting update damaged_goods")
#                 result = await session.execute(select(Damaged_good).where(Damaged_good.user_id == 1))
#                 damaged_goods = result.scalars().all()
#                 if damaged_goods is None:
#                     print(f"Can not find dmaged goods")
#                 for damaged_good in damaged_goods:
#                     product_code_list = damaged_good.product_code
#                     quantity_list = damaged_good.quantity
#                     ean_list = damaged_good.product_ean
#                     for i in range(len(product_code_list)):
#                         quantity = quantity_list[i]
#                         product_code = product_code_list[i]
#                         ean = ean_list[i]
#                         if product_code == "":
#                             result = await session.execute(select(Internal_Product).where(Internal_Product.ean == ean))
#                             product = result.scalars().first()
#                             if product is None:
#                                 print(f"Can not find product that have {ean}")
#                                 continue
#                             product_code = product.product_code
#                         result = await session.execute(select(Internal_Product).where(Internal_Product.product_code == product_code, Internal_Product.user_id == 1))
#                         products = result.scalars().all()
#                         for product in products:
#                             product.damaged_goods = product.damaged_goods + quantity
#                 await session.commit()
#             except Exception as e:
#                 print(f"Unexpected error: {e}")

async def update_awb(db: AsyncSession = Depends(get_db)):
    async for db in get_db():
        async with db as session:
            log_update_awb(f"Started on {datetime.now(timezone.utc)}")
            print("Starting update api_key in sameday")
            result = await session.execute(select(Billing_software).where(Billing_software.site_domain == "sameday.ro"))
            sameday = result.scalars().first()
            if not sameday:
                log_update_awb("Not found sameday in database.")
                logging.warning("Not found sameday in database.")
                return
            response = await auth_sameday(sameday)
            if response.status_code != 200:
                log_update_awb(f"Failed to authenticate sameday: {response.text}")
                logging.error(f"Failed to authenticate sameday: {response.text}")
                return
            result = response.json()
            api_key = result.get('token')
            sameday.registration_number = api_key
            try:
                await session.commit()
            except Exception as e:
                logging.error(f"Failed to commit database: {e}")
                log_update_awb(f"Failed to commit database: {e}")

            awb_status_list = [56, 85, 84, 37, 63, 1, 2, 25, 33, 7, 78, 6, 26, 14, 23, 35, 79, 112, 81, 10, 113, 27,
                               87, 4, 99, 74, 116, 18, 61, 111, 57, 137, 82, 3, 11, 28, 127, 17, 68,
                               101, 147, 73, 126, 47, 145, 128, 19, 0, 5, 22, 62, 65, 140, 149, 153]
            # awb_status_list = [93, 16, 15, 9]
            print("Start updating AWB status")

            error_barcode = []

            try:
                result = await session.execute(
                    select(AWB)
                    .where(AWB.awb_status == any_(awb_status_list))
                )
                db_awbs = result.scalars().all()

                if not db_awbs:
                    return
                
                log_update_awb(f"Found {len(db_awbs)} awbs.")

                for awb in db_awbs:
                    awb_barcode = awb.awb_barcode
                    if not awb_barcode:
                        logging.warning("AWB number is empty.")
                    awb_user_id = awb.user_id
                    result = await session.execute(select(Billing_software).where(Billing_software.user_id == awb_user_id, Billing_software.site_domain == "sameday.ro"))
                    sameday = result.scalars().first()
                    try:
                        # Track and update awb status
                        awb_status_response = await tracking(sameday, awb_barcode)
                        if (awb_status_response.status_code != 200):
                            raise Exception(awb_status_response.text)
                        awb_status_result = awb_status_response.json()
                        pickedup = awb_status_result.get('parcelSummary').get('isPickedUp')
                        weight = awb_status_result.get('parcelSummary').get('parcelWeight')
                        length = awb_status_result.get('parcelSummary').get('parcelLength')
                        width = awb_status_result.get('parcelSummary').get('parcelWidth')
                        height = awb_status_result.get('parcelSummary').get('parcelHeight')
                        history_list = awb_status_result.get('parcelHistory')
                        statusID = []
                        statusDate = []
                        for history in history_list:
                            statusID.append(history.get('statusId'))
                            statusDate.append(history.get('statusDate'))
                        parsed_dates = [datetime.fromisoformat(date) for date in statusDate]
                        latest_index = parsed_dates.index(max(parsed_dates))
                        first_index = parsed_dates.index(min(parsed_dates))
                        awb_status = statusID[latest_index]
                        awb.awb_creation_date = statusDate[first_index]
                        awb.awb_status = awb_status
                        awb.pickedup = pickedup
                        awb.weight = weight
                        awb.height = height
                        awb.width = width
                        awb.length = length
                        awb.awb_status_update_time = datetime.now()
                        await asyncio.sleep(20)
                    except Exception as track_ex:
                        error_barcode.append(awb_barcode)
                        print(f"Tracking API error for AWB {awb_barcode}: {str(track_ex)}")
                        log_update_awb(f"Tracking API error for AWB {awb_barcode}: {str(track_ex)}")
                        continue  # Continue to next AWB if tracking fails
                #     count += 1
                MAX_RETRIES = 5
                retries = 0

                while retries < MAX_RETRIES:
                    try:
                        await session.commit()
                        print(f"Successfully committed AWBs so far")
                        break  # Break out of the retry loop if commit succeeds
                    except Exception as e:
                        await session.rollback()
                        retries += 1
                        print(f"Failed to commit batch, attempt {retries}/{MAX_RETRIES}: {str(e)}")
                        if retries == MAX_RETRIES:
                            print(f"Max retries reached. Aborting commit.")
                            break
                        else:
                            print(f"Retrying commit...")
                            await asyncio.sleep(2)
            except Exception as db_ex:
                print(f"Database query failed: {str(db_ex)}")
                log_update_awb(f"Database query failed: {str(db_ex)}")
                await session.rollback()

            print(f"Getting awb status error barcodes {error_barcode}")
            log_update_awb(f"Getting awb status error barcodes {error_barcode}")
            print("AWB status update completed")
            log_update_awb(f"Finished on {datetime.now(timezone.utc)}\n")

# def backup_db():
#     export_to_csv()

async def refresh_orders_data(db:AsyncSession = Depends(get_db)):
    async for db in get_db():
        async with db as session:
            log_refresh_orders(f"Started on {datetime.now(timezone.utc)}")
            # print("Starting orders refresh")
            result = await session.execute(select(Marketplace).order_by(Marketplace.id.asc()))
            marketplaces = result.scalars().all()
            # await session.commit()
            # print(f"Success getting {len(marketplaces)} marketplaces")
            for marketplace in marketplaces:
                if marketplace.marketplaceDomain == "altex.ro":
                    print("Refresh products from altex")
                    log_refresh_orders("Refresh products from altex")
                    try:
                        await refresh_altex_products(marketplace)
                    except Exception as e:
                        log_refresh_orders(f"An error occurred: {e}")
                    print("Refresh orders from altex")
                    log_refresh_orders("Refresh orders from altex")
                    try:
                        await refresh_altex_orders(marketplace)
                    except Exception as e:
                        log_refresh_orders(f"An error occurred: {e}")
                else:
                    print("Refresh products from emag")
                    log_refresh_orders("Refresh products from emag")
                    try:
                        await refresh_emag_products(marketplace)
                    except Exception as e:
                        log_refresh_orders(f"An error occurred: {e}")
                    print("Refresh orders from emag")
                    log_refresh_orders("Refresh orders from emag")
                    try:
                        await refresh_emag_orders(marketplace)
                    except Exception as e:
                        log_refresh_orders(f"An error occurred: {e}")
            log_refresh_orders(f"Finished on {datetime.now(timezone.utc)}")

async def generate_invoice(db:AsyncSession = Depends(get_db)):
    async for db in get_db():
        async with db as session:
            log_generate_invoice(f"Started on {datetime.now(timezone.utc)}")
            print("Create Invoice and Reverse Invoice")
            try:
                await refresh_invoice(session)
            except Exception as e:
                log_generate_invoice(f"An error occured: {e}")
            log_generate_invoice(f"Finished on {datetime.now(timezone.utc)}\n")

async def refresh_months_order(db:AsyncSession = Depends(get_db)):
    async for db in get_db():
        async with db as session:
            log_refresh_month_order(f"Started on {datetime.now(timezone.utc)}")
            print("Starting orders refresh")
            result = await session.execute(select(Marketplace).order_by(Marketplace.id.asc()))
            marketplaces = result.scalars().all()
            print(f"Success getting {len(marketplaces)} marketplaces")
            for marketplace in marketplaces:
                try:
                    if marketplace.marketplaceDomain == "altex.ro":
                        print("Refresh orders from marketplace")
                        await refresh_altex_orders(marketplace)
                    else:
                        print("Refresh orders from marketplace")
                        await refresh_emag_orders(marketplace, period=180)
                except Exception as e:
                    log_refresh_month_order(f"An error occured: {e}")
            log_refresh_month_order(f"Finished on {datetime.now(timezone.utc)}\n")

async def send_stock(db:AsyncSession = Depends(get_db)):
    async for db in get_db():
        log_send_stock(f"Stock sending started on f{datetime.now(timezone.utc)}")
        try:
            async with db as session:
                print("Calculate orders_stock")
                result = await session.execute(select(Order).where(Order.status == any_([1,2,3])))
                db_new_orders = result.scalars().all()
                if db_new_orders is None:
                    print("Can't find new orders")
                    log_send_stock("Can't find new orders")
                    return
                else:
                    print(f"Find {len(db_new_orders)} new orders")
                    log_send_stock(f"Find {len(db_new_orders)} new orders")
                # try:
                #     for db_new_order in db_new_orders:
                #         product_id_list = db_new_order.product_id
                #         quantity_list = db_new_order.quantity
                #         marketplace = db_new_order.order_market_place
                #         # print(f"@#@#!#@#@##!@#@#@ order_id is {db_new_order.id}")
                #         for i in range(len(product_id_list)):
                #             product_id = product_id_list[i]
                #             quantity = quantity_list[i]

                #             result = await db.execute(select(Product).where(Product.id == product_id, Product.product_marketplace == marketplace, Product.user_id == db_new_order.user_id))
                #             db_product = result.scalars().first()
                #             if db_product is None:
                #                 print(f"Can't find {product_id} in {marketplace}")
                #                 continue
                #             ean = db_product.ean
                #             # print(f"&*&*&*&&*&*&**&ean number is {ean}")

                #             result = await db.execute(select(Internal_Product).where(Internal_Product.ean == ean))
                #             db_internal_product = result.scalars().first()
                #             if db_internal_product is None:
                #                 print(f"Can't find {ean}")
                #             db_internal_product.orders_stock = db_internal_product.orders_stock + quantity
                #             # print(f"#$$$#$#$#$#$ Orders_stock is {db_internal_product.orders_stock}")
                #     await db.commit()
                # except Exception as e:
                #     print(f"An error occurred: {e}")
                #     await db.rollback() 

                workbook = Workbook()
                worksheet = workbook.active
                worksheet.title = "Product Stocks"
                worksheet.append(["EAN", "Product_code", "User_id", "Smartbill", "Damaged", "EMAG_Stock", "Stock", "Post"])

                print("Sync stock")
                result = await session.execute(select(Internal_Product).where(Internal_Product.user_id == 1))
                db_products = result.scalars().all()
                for product in db_products:
                    current_time = datetime.now()
                    if product.smartbill_stock_time is None:
                        worksheet.append([product.ean, product.product_code, product.user_id, 0, 0, 0, 0, "Smartbill stock time is none"])
                        continue
                    if product.smartbill_stock_time < current_time - timedelta(days = 1):
                        worksheet.append([product.ean, product.product_code, product.user_id, 0, 0, 0, 0, "Smartbill stock time is old"])
                        continue
                    if product.smartbill_stock is None:
                        worksheet.append([product.ean, product.product_code, product.user_id, 0, 0, 0, 0, "Smartbill stock is None"])
                        continue
                    stock = product.smartbill_stock
                    smartbill_stock = stock
                    damaged = 0
                    if product.damaged_goods:
                        stock = stock - product.damaged_goods
                        damaged = product.damaged_goods
                    ean = product.ean
                    user_id = product.user_id
                    product_code = product.product_code

                    worksheet.append([ean, product_code, user_id, smartbill_stock, damaged, product.stock, stock, "Successfully get stock", current_time.isoformat()])

                    marketplaces = product.market_place
                    for domain in marketplaces:
                        try:
                            if domain == "altex.ro":
                                continue
                                # if db_product.barcode_title == "":
                                    #     continue
                                    # post_stock_altex(marketplace, db_product.barcode_title, stock)
                                    # print("post stock success in altex")
                            result = await session.execute(select(Marketplace).where(Marketplace.marketplaceDomain == domain, Marketplace.user_id == product.user_id))
                            marketplace = result.scalars().first()

                            if marketplace is None:
                                continue

                            result = await session.execute(select(Product).where(Product.ean == ean, Product.product_marketplace == domain))
                            db_product = result.scalars().first()

                            if db_product is None:
                                log_send_stock(f"Product not found: EAN {ean}")
                                continue
                            if db_product.stock == stock:
                                continue
                            product_id = db_product.id

                            # if marketplace.marketplaceDomain == "altex.ro":
                            #     continue
                            #     # if db_product.barcode_title == "":
                            #     #     continue
                            #     # post_stock_altex(marketplace, db_product.barcode_title, stock)
                            #     # print("post stock success in altex")
                        except Exception as e:
                            log_send_stock(f"Failed to send stock to {domain}: {e}")
                            logging.error(f"Failed to send stock to {domain}: {e}")

                        product_id = int(product_id)
                        response = await post_stock_emag(marketplace, product_id, stock)
                        print(f"{response}") 
                        if response.status_code == 200:
                            product.sync_stock_time = datetime.now(timezone.utc)
                        else:
                            log_send_stock(f"An error occured: {response.text}")
                            continue
                await session.commit() 
                workbook.save("/var/www/html/invoices/stock_sync.xlsx")
                print("successfully saved stock data")
                log_send_stock(f"successfully saved stock data on {datetime.now(timezone.utc)}")
        except Exception as e:
            print(f"An error occurred: {e}")
            log_send_stock(f"An error occurred: {e}")
            await session.rollback()
        log_send_stock(f"Finished on {datetime.now(timezone.utc)}\n")

async def refresh_stock(db: AsyncSession = Depends(get_db)):
    async for db in get_db():
        async with db as session:
            log_refresh_stock(f"Stock refresh started on f{datetime.now(timezone.utc)}")
            print("Starting stock refresh")
            result = await session.execute(select(Billing_software).where(Billing_software.site_domain == "smartbill.ro"))
            db_smarts = result.scalars().all()
            if db_smarts is None:
                print("Can't find billing software")
                log_refresh_stock("Can't find billing software")
                return

            print("Fetch stock via smarbill api")
            product_code_list = []
            products = []
            try:
                for db_smart in db_smarts:
                    products_list = await get_stock(db_smart)
                    for smart_products in products_list:
                        if smart_products.get('products'):
                            products = products + smart_products.get('products')
                        else:
                            continue
            except Exception as e:
                logging.error(f"getting stock data error: {e}")
                log_refresh_stock(f"getting stock data error: {e}")
            for product in products:
                print(product)
                product_code = product.get('productCode')
                if product_code is None:
                    continue
                print(f"Update stock {product_code}")
                product_code_list.append({
                    "product_code": product_code,
                    "quantity": int(product.get('quantity'))
                })
                result = await session.execute(select(Internal_Product).where(Internal_Product.product_code == product_code))
                db_products = result.scalars().all()
                if db_products is None:
                    continue
                for db_product in db_products:
                    db_product.smartbill_stock = int(product.get('quantity'))
                    db_product.smartbill_stock_time = datetime.now()
            try:
                await session.commit()
                print(f"product_code_list: {product_code_list}")
                print("Finish sync stock")
            except Exception as e:
                logging.error(f"sync stock error {e}")
                log_refresh_stock(f"sync stock error {e}")
            log_refresh_stock(f"Finish sync stock on {datetime.now(timezone.utc)}\n")

# Run daily for deleting video last 30 days
async def refresh_return(db: AsyncSession = Depends(get_db)): 
    async for db in get_db():
        async with db as session:
            log_refresh_returns(f"Refresh return (returns) started on f{datetime.now(timezone.utc)}")
            print("Starting product refresh")
            result = await session.execute(select(Marketplace).order_by(Marketplace.id.asc()))
            marketplaces = result.scalars().all()
            print(f"Success getting {len(marketplaces)} marketplaces")
            for marketplace in marketplaces:
                if marketplace.marketplaceDomain == "altex.ro":
                    try:
                        print("Refresh rmas from altex")
                        log_refresh_returns("Refresh rmas from altex")
                        await refresh_altex_rmas(marketplace)
                    except Exception as e:
                        log_refresh_returns(f"An error occured: {e}")
                else:
                    try:
                        print(f"Refresh refunds from marketplace: {marketplace.marketplaceDomain}")
                        log_refresh_returns(f"Refresh refunds from marketplace: {marketplace.marketplaceDomain}")
                        await refresh_emag_returns(marketplace)
                    except Exception as e:
                        log_refresh_returns(f"An error occured: {e}")

                    # print("Refresh reviews from emag")
                    # await refresh_emag_reviews(marketplace, session)
                    # print("Check hijacker and review")
                    # await check_hijacker_and_bad_reviews(marketplace, session)
            log_refresh_returns(f"Finished on {datetime.now(timezone.utc)}\n")

# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     print("App started")
#     scheduler = AsyncIOScheduler()
#     scheduler.add_job(update_awb, trigger='interval', seconds=14400)
#     scheduler.add_job(refresh_orders_data, trigger='interval', seconds=900)
#     scheduler.add_job(generate_invoice, trigger='interval', seconds=900)
#     scheduler.add_job(refresh_months_order, trigger='interval', seconds=28800)
#     scheduler.add_job(send_stock, trigger='interval', seconds=7200)
#     scheduler.add_job(refresh_stock, trigger='interval', seconds=7200)
#     scheduler.add_job(refresh_data, trigger='interval', seconds=86400)
#     # scheduler.add_job(backup_db, trigger='interval', seconds=86400)
#     scheduler.start()
#     # asyncio.create_task(on_startup())
#     # asyncio.create_task(update_damaged_goods())
#     # asyncio.create_task(update_invoice_post())
#     asyncio.create_task(update_awb())
#     asyncio.create_task(refresh_orders_data())
#     asyncio.create_task(generate_invoice())
#     asyncio.create_task(refresh_months_order())
#     asyncio.create_task(send_stock())
#     asyncio.create_task(refresh_stock())
#     asyncio.create_task(refresh_data())
#     # asyncio.create_task(backup_db())
#     yield
#     print("App stopped")

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run("refresh_data:app", host="0.0.0.0", port=3000, reload=False)
