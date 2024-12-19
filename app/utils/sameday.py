import logging
import httpx
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
    return response

async def tracking(sameday: Billing_software, awb_barcode):
    url = "https://api.sameday.ro/api/client/parcel"
    api_key = sameday.registration_number

    async with httpx.AsyncClient(timeout=20) as client:
        tracking_headers = {
            "X-Auth-TOKEN": api_key,
        }
        response = await client.get(f"{url}/{awb_barcode}/status-history", headers=tracking_headers)
        
        if response.status_code == 200:
            result = response.json()
            return result
        else:
            print("Status Code:", response.status_code)
            print("Error:", response.json())
