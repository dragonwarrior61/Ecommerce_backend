import json
import logging
from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Marketplace
from app.utils.auth_market import get_auth_marketplace
from app.utils.httpx_request import send_post_request

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def convert_decimal_to_float(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

async def save(marketplace: Marketplace, data):
    url = f"{marketplace.baseAPIURL}/awb/save"
    headers = get_auth_marketplace()
    response = await send_post_request(url, data=json.dumps(data, default=convert_decimal_to_float), headers=headers, error_msg='generate awb')
    if response.status_code != 200:
        logging.error(f"Failed to save data: {response.text}")
    return response

async def save_awb(marketplace: Marketplace, data, db: AsyncSession):
    result = await save(marketplace, data)
    return result
