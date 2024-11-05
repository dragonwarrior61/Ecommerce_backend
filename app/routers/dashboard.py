from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import text, and_, func, literal_column, cast, ARRAY, Integer, BigInteger, String
from sqlalchemy.orm import aliased
from sqlalchemy.orm import joinedload
from app.models.product import Product
from app.models.marketplace import Marketplace
from app.models.orders import Order
from app.models.user import User
from app.models.team_member import Team_member
from app.routers.auth import get_current_user
from app.models.returns import Returns
from typing import List, Optional
from app.database import get_db
import datetime
import asyncpg
from app.config import settings
from psycopg2.extras import RealDictCursor
from decimal import Decimal
from sqlalchemy import any_
import calendar

router = APIRouter()

def get_valid_date(year, month, day):
    # Find the last day of the month
    last_day_of_month = calendar.monthrange(year, month)[1]
    # Set the day to the last day of the month if necessary
    day = min(day, last_day_of_month)
    return datetime.date(year, month, day)

async def get_vat_dict(db: AsyncSession):
    query = select(Marketplace.marketplaceDomain, Marketplace.vat)
    result = await db.execute(query)
    records = result.all()
    
    return {record.marketplaceDomain: record.vat for record in records}

async def get_db_connection():
    return await asyncpg.connect(
        database=settings.DB_NAME,
        user=settings.DB_USERNAME,
        password=settings.DB_PASSOWRD,
        host=settings.DB_URL,
        port=settings.DB_PORT,
    )

async def get_return(st_datetime, en_datetime, user: User, db:AsyncSession):
    if user.role == -1:
        raise HTTPException(status_code=401, detail="Authentication error")
    
    if user.role != 4:
        result = await db.execute(select(Team_member).where(Team_member.user == user.id))
        db_team = result.scalars().first()
        user_id = db_team.admin
    else:
        user_id = user.id
        
    query = select(Returns).where(Returns.date <= en_datetime, Returns.date >= st_datetime, Returns.user_id == user_id)
    query = query.where(Returns.type == 3)
    result = await db.execute(query)
    refunds = result.scalars().all()
    count = len(refunds)

    return count

async def get_orders(date_string, product_ids_list, st_datetime, en_datetime, user: User, db:AsyncSession):
    if user.role == -1:
        raise HTTPException(status_code=401, detail="Authentication error")
    
    if user.role != 4:
        result = await db.execute(select(Team_member).where(Team_member.user == user.id))
        db_team = result.scalars().first()
        user_id = db_team.admin
    else:
        user_id = user.id
        
    vat_dict = await get_vat_dict(db)
    total_units = 0
    total_refund = 0
    total_net_profit = 0
    total_refund = await get_return(st_datetime, en_datetime, user, db)

    orders_with_products = []

    ProductAlias = aliased(Product)
    query = select(Order, ProductAlias).where(
        and_(
            Order.date >= st_datetime,
            Order.date <= en_datetime
        )
    ).join(
        ProductAlias,
        ProductAlias.id == any_(Order.product_id)
    ).where(Order.user_id == user_id)

    if product_ids_list:
        query = query.where(
            Order.product_id.op('&&')(cast(product_ids_list, ARRAY(String)))
        )
    result = await db.execute(query)
    orders_with_products = result.all()

    orders = []

    for order, product in orders_with_products:
        orders.append(order)
        total_units += sum(order.quantity)
        product_ids = order.product_id
        quantities = order.quantity

        marketplace_domain = order.order_market_place
        vat = vat_dict[marketplace_domain]

        for i in range(len(product_ids)):
            if product.id == product_ids[i]:
                total_net_profit += (product.sale_price * 100 / Decimal(100.0 + vat) - product.price) * quantities[i]
        
    return {
        "date_string": date_string,
        "total_units": total_units,
        "total_refund": total_refund,
        "total_net_profit": total_net_profit,
        # "orders": orders
    }

async def get_PL(date_string, product_ids_list, st_datetime, en_datetime, user: User, db:AsyncSession):
    if user.role == -1:
        raise HTTPException(status_code=401, detail="Authentication error")
    
    if user.role != 4:
        result = await db.execute(select(Team_member).where(Team_member.user == user.id))
        db_team = result.scalars().first()
        user_id = db_team.admin
    else:
        user_id = user.id
        
    vat_dict = await get_vat_dict(db)
    
    total_units = 0
    total_refund = 0
    total_net_profit = 0
    total_sales = 0
    total_gross_profit = 0
    total_refund = await get_return(st_datetime, en_datetime, user, db)

    ProductAlias = aliased(Product)
    query = select(Order, ProductAlias).where(
        and_(
            Order.date >= st_datetime,
            Order.date <= en_datetime
        )
    ).join(
        ProductAlias,
        ProductAlias.id == any_(Order.product_id)
    ).where(Order.user_id == user_id)

    if product_ids_list:
        query = query.where(
            Order.product_id.op('&&')(cast(product_ids_list, ARRAY(String)))
        )
    result = await db.execute(query)
    orders_with_products = result.all()

    orders = []

    for order, product in orders_with_products:
        orders.append(order)
        total_units += sum(order.quantity)
        product_ids = order.product_id
        quantity = order.quantity

        marketplace_domain = order.order_market_place
        vat = vat_dict[marketplace_domain]

        for i in range(len(product_ids)):
            if product.id == product_ids[i]:
                total_sales += product.sale_price * quantity[i]
                total_net_profit += (product.sale_price * 100 / Decimal(100.0 + vat) - product.price) * quantity[i]
                total_gross_profit += (product.sale_price - product.price) * quantity[i]

    return {
        "date_string": date_string,
        "total_sales": total_sales,
        "total_units": total_units,
        "total_refund": total_refund,
        "total_gross_profit": total_gross_profit,
        "total_net_profit": total_net_profit,
        # "orders": orders
    }   
    
async def get_trend(date_string, product_id, st_datetime, en_datetime, user: User, db:AsyncSession):
    if user.role == -1:
        raise HTTPException(status_code=401, detail="Authentication error")
    
    if user.role != 4:
        result = await db.execute(select(Team_member).where(Team_member.user == user.id))
        db_team = result.scalars().first()
        user_id = db_team.admin
    else:
        user_id = user.id
        
    vat_dict = await get_vat_dict(db)
    
    total_units = 0
    total_refund = 0
    total_net_profit = 0
    total_sales = 0
    total_gross_profit = 0
    total_refund = await get_return(st_datetime, en_datetime, user, db)

    query = select(Product).where(Product.id == product_id, Product.user_id == user_id)
    result = await db.execute(query)
    product = result.scalars().first()

    query = select(Order).where(product_id == any_(Order.product_id))
    query = query.where(Order.date > st_datetime, Order.date < en_datetime)
    result = await db.execute(query)
    orders = result.scalars().all()

    for order in orders:
        total_units += sum(order.quantity)
        product_ids = order.product_id
        quantity = order.quantity

        marketplace_domain = order.order_market_place
        vat = vat_dict[marketplace_domain]

        for i in range(len(product_ids)):
            if product_id == product_ids[i]:
                total_sales += product.sale_price * quantity[i]
                total_net_profit += (product.sale_price * 100 / Decimal(100.0 + vat) - product.price) * quantity[i]
                total_gross_profit += (product.sale_price - product.price) * quantity[i]

    return {
        "date_string": date_string,
        "total_sales": total_sales,
        "total_units": total_units,
        "total_refund": total_refund,
        "total_gross_profit": total_gross_profit,
        "total_net_profit": total_net_profit,
        # "orders": orders
    }   

@router.get('/tiles')
async def get_dashboard_info(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
        
    today = datetime.date.today()
    orders_today_data = await get_value(today, today, user, db)

    yesterday = datetime.date.today() - datetime.timedelta(days = 1)
    orders_yesterday_data = await get_value(yesterday, yesterday, user, db)
    
    first_day_of_month = datetime.date(today.year, today.month, 1)
    orders_month_data = await get_value(first_day_of_month, today, user, db)

    orders_forecast_data = await forecast(first_day_of_month, today, user, db)

    if today.month > 1:
        last_month_st = datetime.date(today.year, today.month - 1, 1)
        last_month_en = first_day_of_month - datetime.timedelta(days = 1)
    else:
        last_month_st = datetime.date(today.year - 1, 12, 1)
        last_month_en = datetime.date(today.year - 1, 12, 31)
    orders_last_month_data = await get_value(last_month_st, last_month_en, user, db)

    return {
        "orders_today_data": { "title": "Today", **orders_today_data },
        "orders_yesterday_data": { "title": "Yesterday", **orders_yesterday_data },
        "orders_month_data": { "title": "This month", **orders_month_data },
        "orders_forecast_data": {"title": "Forecast", **orders_forecast_data},
        "orders_last_month_data": { "title": "Last month", **orders_last_month_data },
    }

async def get_value(st_date, en_date, user: User, db:AsyncSession):
    if user.role == -1:
        raise HTTPException(status_code=401, detail="Authentication error")
    
    if user.role != 4:
        result = await db.execute(select(Team_member).where(Team_member.user == user.id))
        db_team = result.scalars().first()
        user_id = db_team.admin
    else:
        user_id = user.id
        
    vat_dict = await get_vat_dict(db)

    st_datetime = datetime.datetime.combine(st_date, datetime.time.min)
    en_datetime = datetime.datetime.combine(en_date, datetime.time.max)

    orders_with_products = []

    query = text(f"""
        SELECT orders.*, products.*
        FROM orders AS orders
        JOIN products AS products ON products.id = ANY(orders.product_id)
        WHERE orders.date >= :st_datetime AND orders.date <= :en_datetime AND orders.user_id = :user_id
    """)

    result = await db.execute(query, {'st_datetime': st_datetime, 'en_datetime': en_datetime, 'user_id': user_id})
    records = result.fetchall()

    for record in records:
        record_dict = {key: value for key, value in zip(result.keys(), record)}
        orders_with_products.append(record_dict)

    date_string = ""
    if st_date == en_date:
        date_string = f"{st_date.day} {st_date.strftime('%B')} {st_date.year}"
    else:
        date_string = f"{st_date.day}-{en_date.day} {st_date.strftime('%B')} {st_date.year}"

    total_sales = 0
    total_orders = len(orders_with_products)
    total_units = 0
    total_refund = await get_return(st_datetime, en_datetime, user, db)
    total_gross_profit = 0
    total_net_profit = 0
    orders = []
    for order in orders_with_products:
        orders.append(order)
        product_ids = order.get("product_id")
        quantities = order.get("quantity")
        total_units += sum(quantity for quantity in quantities)

        marketplace_domain = order.get("order_market_place")
        vat = vat_dict[marketplace_domain]
        # print(marketplace_domain)
        # query = select(Marketplace).where(marketplace_domain == Marketplace.marketplaceDomain)
        # marketplace_result = await db.execute(query)
        # marketplace = marketplace_result.scalars().first()
        # vat = marketplace.vat

        for i in range(len(product_ids)): 
            product = next((p for p in orders_with_products if p['id'] == product_ids[i]), None)
            if product:
                sale_price = product.get("sale_price", Decimal(0))
                price = product.get("price", Decimal(0))
                quantity = quantities[i]
                total_sales += sale_price * quantity
                total_gross_profit += (sale_price - price) * quantity
                total_net_profit += (sale_price * 100 / Decimal(100.0 + vat) - price) * quantity

    return {
        "date_range": date_string,
        "total_sales": total_sales,
        "total_orders": total_orders,
        "total_units": total_units,
        "total_refund": total_refund,
        "total_gross_profit": total_gross_profit,
        "total_net_profit": total_net_profit,
        # "orders": orders
    }
    
async def forecast(st_date, en_date, user: User, db: AsyncSession):
    if user.role == -1:
        raise HTTPException(status_code=401, detail="Authentication error")
    
    if user.role != 4:
        result = await db.execute(select(Team_member).where(Team_member.user == user.id))
        db_team = result.scalars().first()
        user_id = db_team.admin
    else:
        user_id = user.id
        
    st_datetime = datetime.datetime.combine(st_date, datetime.time.min)
    en_datetime = datetime.datetime.combine(en_date, datetime.time.max)

    result = await db.execute(select(Order).where(Order.date >= st_datetime, Order.date <= en_datetime, Order.user_id == user_id))
    orders = result.scalars().all()
    if not orders:
        return {
            "date_range": f"Forecast for {st_date.strftime('%B')} {st_date.year}",
            "total_sales": 0.0,
            "total_orders": 0,
            "total_units": 0,
            "total_refund": 0,
            "total_gross_profit": 0,
            "total_net_profit": 0,
        }
    
    present_data = await get_value(st_datetime, en_datetime, user, db)

    total_sales = present_data.get("total_sales")
    total_orders = present_data.get("total_orders")
    total_units = present_data.get("total_units")
    total_refund = present_data.get("total_refund")
    total_gross_profit = present_data.get("total_gross_profit")
    total_net_profit = present_data.get("total_net_profit")

    days_passed = (en_date - st_date).days + 1
    total_days_in_month = (datetime.date(st_date.year, st_date.month + 1, 1) - st_date).days if st_date.month < 12 else 31
    days_remaining = total_days_in_month - days_passed

    avg_daily_sales = total_sales / days_passed
    avg_daily_orders = total_orders / days_passed
    avg_daily_units = total_units / days_passed
    avg_daily_refund = total_refund / days_passed
    avg_daily_gross_profit = total_gross_profit / days_passed
    avg_daily_net_profit = total_net_profit / days_passed

    forecasted_sales = total_sales + (avg_daily_sales * days_remaining)
    forecasted_orders = int(total_orders + (avg_daily_orders * days_remaining))
    forecasted_units = int(total_units + (avg_daily_units * days_remaining))
    forecasted_refund = int(total_refund + (avg_daily_refund * days_remaining))
    forecasted_gross_profit = total_gross_profit + (avg_daily_gross_profit * days_remaining)
    forecasted_net_profit = total_net_profit + (avg_daily_net_profit * days_remaining)

    return {
        "date_range": f"Forecast for {st_date.strftime('%B')} {st_date.year}",
        "total_sales": forecasted_sales,
        "total_orders": forecasted_orders,
        "total_units": forecasted_units,
        "total_refund": forecasted_refund,
        "total_gross_profit": forecasted_gross_profit,
        "total_net_profit": forecasted_net_profit,
    }

@router.get('/chart')
async def get_chart_data(
    product_ids: str = Query(None),  # Make product_ids required
    type: int = Query(...),  # Make type required
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    
    today = datetime.date.today()
    chart_data = []

    if product_ids:
        product_ids_list = [str(id.strip()) for id in product_ids.split(",")]
    else:
        product_ids_list = []

    if type == 1:
        for i in range(13):
            month = today.month + i
            year = today.year - 1 if month <= 12 else today.year
            month = month if month <= 12 else month - 12
            date = get_valid_date(year, month, today.day)

            chart_data.append(await get_month_data(product_ids_list, date, user, db))
    elif type == 2:
        week_num_en = today.isocalendar()[1]
        en_date = today
        st_date = today - datetime.timedelta(today.weekday())
        for i in range(14):
            if week_num_en - i > 0:
                week_string = f"week {week_num_en - i}"
            else:
                week_string = f"week {week_num_en + 52 - i}"

            chart_data.insert(0, await get_week_data(week_string, product_ids_list, st_date, en_date, user, db))
            en_date = st_date - datetime.timedelta(days=1)
            st_date = st_date - datetime.timedelta(days=7)
    else:
        for i in range(30):
            date = today - datetime.timedelta(days=i)
            chart_data.insert(0, await get_day_data(date, product_ids_list, user, db))
    return {
        "chart_data": chart_data
    }

async def get_month_data(product_ids_list, date, user: User, db: AsyncSession):
    date_string = f"{date.strftime('%b')} {date.year}"
    st_date = datetime.date(date.year, date.month, 1)
    if date.month == 12:
        en_date = datetime.date(date.year, 12, 31)
    else:
        en_date = datetime.date(date.year, date.month + 1, 1) - datetime.timedelta(days = 1)

    st_datetime = datetime.datetime.combine(st_date, datetime.time.min)
    en_datetime = datetime.datetime.combine(en_date, datetime.time.max)

    return await get_orders(date_string, product_ids_list, st_datetime, en_datetime, user, db)

async def get_week_data(week_string, product_ids_list, st_date, en_date, user: User, db: AsyncSession):
    st_datetime = datetime.datetime.combine(st_date, datetime.time.min)
    en_datetime = datetime.datetime.combine(en_date, datetime.time.max)

    return await get_orders(week_string, product_ids_list, st_datetime, en_datetime, user, db)

async def get_day_data(date, product_ids_list, user: User, db: AsyncSession):
    st_datetime = datetime.datetime.combine(date, datetime.time.min)
    en_datetime = datetime.datetime.combine(date, datetime.time.max)
    date_string = f"{date.day} {date.strftime('%b')} {date.year}"

    return await get_orders(date_string, product_ids_list, st_datetime, en_datetime, user, db)

@router.get('/P_L')
async def get_PL_data(
    product_ids: str = Query(None),  # Make product_ids required
    type: int = Query(...),  # Make type required
    user: User = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)
):
    today = datetime.date.today()
    PL_data = []

    if product_ids:
        product_ids_list = [str(id.strip()) for id in product_ids.split(",")]
    else:
        product_ids_list = []

    if type == 1:
        for i in range(13):
            month = today.month + i
            year = today.year - 1 if month <= 12 else today.year
            month = month if month <= 12 else month - 12
            date = get_valid_date(year, month, today.day)

            PL_data.insert(0, await PL_month_data(product_ids_list, date, user, db))
    elif type == 2:
        week_num_en = today.isocalendar()[1]
        en_date = today
        st_date = today - datetime.timedelta(today.weekday())
        for i in range(14):
            if week_num_en - i > 0:
                week_string = f"week {week_num_en - i}"
            else:
                week_string = f"week {week_num_en + 52 - i}"

            PL_data.append(await PL_week_data(week_string, product_ids_list, st_date, en_date, user, db))
            en_date = st_date - datetime.timedelta(days=1)
            st_date = st_date - datetime.timedelta(days=7)
    else:
        for i in range(30):
            date = today - datetime.timedelta(days=i)
            PL_data.append(await PL_day_data(date, product_ids_list, user, db))
    return {
        "PL_data": PL_data
    }

async def PL_month_data(product_ids_list, date, user: User, db: AsyncSession):
    date_string = f"{date.strftime('%b')} {date.year}"
    st_date = datetime.date(date.year, date.month, 1)
    if date.month == 12:
        en_date = datetime.date(date.year, 12, 31)
    else:
        en_date = datetime.date(date.year, date.month + 1, 1) - datetime.timedelta(days = 1)

    st_datetime = datetime.datetime.combine(st_date, datetime.time.min)
    en_datetime = datetime.datetime.combine(en_date, datetime.time.max)

    return await get_PL(date_string, product_ids_list, st_datetime, en_datetime, user, db)

async def PL_week_data(week_string, product_ids_list, st_date, en_date, user: User, db: AsyncSession):
    st_datetime = datetime.datetime.combine(st_date, datetime.time.min)
    en_datetime = datetime.datetime.combine(en_date, datetime.time.max)

    return await get_PL(week_string, product_ids_list, st_datetime, en_datetime, user, db)

async def PL_day_data(date, product_ids_list, user: User, db: AsyncSession):
    day_string = f"{date.day} {date.strftime('%b')} {date.year}"
    st_datetime = datetime.datetime.combine(date, datetime.time.min)
    en_datetime = datetime.datetime.combine(date, datetime.time.max)

    return await get_PL(day_string, product_ids_list, st_datetime, en_datetime, user, db)

@router.get('/trends')

async def get_trends_info(
    product_ids: str = Query(None),
    type: int = Query(...),
    field: str = Query(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    today = datetime.date.today()
    trends_data = []

    if product_ids:
        product_ids_list = [str(id.strip()) for id in product_ids.split(",")]
    else:
        product_ids_list = []

    def get_valid_date(year, month, day):
        # Find the last day of the month
        last_day_of_month = calendar.monthrange(year, month)[1]
        # Set the day to the last day of the month if necessary
        day = min(day, last_day_of_month)
        return datetime.date(year, month, day)

    if type == 1:
        for i in range(13):
            month = today.month + i
            year = today.year - 1 if month <= 12 else today.year
            month = month if month <= 12 else month - 12
            date = get_valid_date(year, month, today.day)

            trends_data.insert(0, await treand_month_data(product_ids_list, date, field, user, db))
    elif type == 2:
        week_num_en = today.isocalendar()[1]
        en_date = today
        st_date = today - datetime.timedelta(today.weekday())
        for i in range(14):
            if week_num_en - i > 0:
                week_string = f"week {week_num_en - i}"
            else:
                week_string = f"week {week_num_en + 52 - i}"

            trends_data.append(await trend_week_data(week_string, product_ids_list, st_date, en_date, field, user, db))
            en_date = st_date - datetime.timedelta(days=1)
            st_date = st_date - datetime.timedelta(days=7)
    else:
        for i in range(30):
            date = today - datetime.timedelta(days=i)
            trends_data.append(await trend_day_data(date, product_ids_list, field, user, db))
    return {
        "trends_data": trends_data
    }

async def treand_month_data(product_ids_list, date, field, user: User, db: AsyncSession):
    date_string = f"{date.strftime('%b')} {date.year}"
    st_date = datetime.date(date.year, date.month, 1)
    if date.month == 12:
        en_date = datetime.date(date.year, 12, 31)
    else:
        en_date = datetime.date(date.year, date.month + 1, 1) - datetime.timedelta(days = 1)

    st_datetime = datetime.datetime.combine(st_date, datetime.time.min)
    en_datetime = datetime.datetime.combine(en_date, datetime.time.max)

    rlt = []
    field = "total_" + field

    for product_id in product_ids_list:
        result = await get_trend(date_string, product_id, st_datetime, en_datetime, user, db)
        rlt.append(result.get(f"{field}"))
    return rlt

async def trend_week_data(week_string, product_ids_list, st_date, en_date, field, user: User, db: AsyncSession):
    st_datetime = datetime.datetime.combine(st_date, datetime.time.min)
    en_datetime = datetime.datetime.combine(en_date, datetime.time.max)

    rlt = []
    for product_id in product_ids_list:
        result = await get_trend(week_string, product_id, st_datetime, en_datetime, user, db)
        field = "total_" + field
        rlt.append(result.get(f"{field}"))
    return rlt

async def trend_day_data(date, product_ids_list, field, user: User, db: AsyncSession):
    day_string = f"{date.day} {date.strftime('%b')} {date.year}"
    st_datetime = datetime.datetime.combine(date, datetime.time.min)
    en_datetime = datetime.datetime.combine(date, datetime.time.max)

    rlt = []
    for product_id in product_ids_list:
        result = await get_trend(day_string, product_id, st_datetime, en_datetime, user, db)
        field = "total_" + field
        rlt.append(result.get(f"{field}"))
    return rlt