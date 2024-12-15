import json
import logging
from fastapi import HTTPException

from app.config import PROXIES
from app.models import Marketplace
from app.utils.httpx_request import send_post_request
from app.utils.auth_market import get_auth_marketplace

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def save(marketplace: Marketplace, data, order_id):
    params = ""
    url = f"{marketplace.baseAPIURL}sales/order/{order_id}/awb/generate/"
    headers = get_auth_marketplace(marketplace, params=params)

    response = await send_post_request(url=url, data=json.dumps(data), headers=headers, proxies=PROXIES, error_msg="retrieve awbs")
    if response.status_code != 200:
        logging.error(f"Failed to save alext awb: {response.text}")
        return response.json()
    awb = response.json()
    return awb

async def save_altex_awb(marketplace: Marketplace, data, order_id):
    return await save(marketplace, data, order_id)
