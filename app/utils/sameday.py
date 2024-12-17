import logging

from app.models import Billing_software
from app.utils.httpx_request import send_post_request, send_get_request

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def auth_sameday(sameday: Billing_software):
    USERNAME = sameday.username
    PASSWORD = sameday.password
    auth_url = "https://api.sameday.ro/api/authenticate"
    headers = {
        "X-Auth-Username": f"{USERNAME}",
        "X-Auth-Password": f"{PASSWORD}",
    }

    response = await send_post_request(auth_url, headers=headers, error_msg="auth sameday")
    if response.status_code != 200:
        logging.error(f"Failed to auhenticate: {response.text}")
        return response.json()
    result = response.json()
    return result.get('token')

async def tracking(sameday: Billing_software, awb_barcode):
    url = "https://api.sameday.ro/api/client/parcel"
    api_key = sameday.registration_number

    headers = {
        "X-Auth-TOKEN": api_key,
    }
    response = await send_get_request(f"{url}/{awb_barcode}/status-history", headers=headers, error_msg="get history", verify=False)
    if response.status_code != 200:
        logging.error(f"Failed to track awb {awb_barcode}: {response.text}")
    return response
