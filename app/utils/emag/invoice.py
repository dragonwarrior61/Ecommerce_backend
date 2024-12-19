import json
import logging
from fastapi import HTTPException
import requests
from app.models import Marketplace
from app.utils.emag.orders import change_status
from app.utils.auth_market import get_auth_marketplace
from app.utils.httpx_request import send_post_request

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def post_pdf(order_id: int, name: str, marketplace: Marketplace):
    MARKETPLACE_API_URL = marketplace.baseAPIURL
    url = f"{MARKETPLACE_API_URL}/order/attachments/save"
    headers = get_auth_marketplace(marketplace)
    pdf_url = f"https://seller.upsourcing.net/invoices/{name}"
    data = [{
        "order_id": order_id,
        "name": name,
        "url": pdf_url,
        "type": 1,
        "force_download": 1
    }]
    await change_status(order_id, marketplace)
    response = await send_post_request(url=url, data=json.dumps(data), headers=headers, error_msg="post pdf")
    if response.status_code != 200:
        logging.error(f"Failed to post pdf to {MARKETPLACE_API_URL}: {response.text}")
    result = response.json()
    return result

def post_factura_pdf(order_id: int, name: str, marketplace: Marketplace):
    MARKETPLACE_API_URL = marketplace.baseAPIURL
    url = f"{MARKETPLACE_API_URL}/order/attachments/save"
    headers = get_auth_marketplace(marketplace)
    pdf_url = f"https://seller.upsourcing.net/invoices/{name}"
    data = [{
        "order_id": order_id,
        "name": name,
        "url": pdf_url,
        "type": 1,
        "force_download": 1
    }]
    response = requests.post(url, data=json.dumps(data), headers=headers)
    return response
