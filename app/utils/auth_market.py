import base64, hashlib
from datetime import datetime, timezone

from app.models import Marketplace

def generate_signature(public_key, private_key, params):
    now = datetime.now(timezone.utc)
    day = now.strftime('%d')
    month = now.strftime('%m')
    timestamp = f"{day}{month}"

    string_to_hash = f"{public_key}||{hashlib.sha512(private_key.encode()).hexdigest()}||{params}||{timestamp}"
    hash_result = hashlib.sha512(string_to_hash.encode()).hexdigest().lower()
    signature = f"{timestamp}{hash_result}"

    return signature

def get_auth_marketplace(marketplace: Marketplace, params=""):
    if marketplace.credentials["type"] == "user_pass":
        USERNAME = marketplace.credentials["firstKey"]
        PASSWORD = marketplace.credentials["secondKey"]
        API_KEY = base64.b64encode(f"{USERNAME}:{PASSWORD}".encode('utf-8'))
        api_key = str(API_KEY).replace("b'", '').replace("'", "")
        headers = {
            "Authorization": f"Basic {api_key}",
            "Content-Type": "application/json"
        }
    else:
        PUBLIC_KEY = marketplace.credentials["firstKey"]
        PRIVATE_KEY = marketplace.credentials["secondKey"]
        signature = generate_signature(PUBLIC_KEY, PRIVATE_KEY, params)
        headers = {
            "X-Request-Public-Key": PUBLIC_KEY,
            "X-Request-Signature": signature
        }
    return headers
