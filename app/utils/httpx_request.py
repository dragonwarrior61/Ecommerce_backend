import httpx, logging
from fastapi import HTTPException

async def send_post_request(url, headers, error_msg='', data=None, proxies=None, verify=False, params=None, json=None):
    async with httpx.AsyncClient(verify=verify, proxy=proxies) as client:
        try:
            response = await client.post(url, data=data, headers=headers, params=params, json=json)
            return response
        except Exception as e:
            logging.error(f"Failed to {error_msg}: {e}")
            raise HTTPException(status_code=504, detail=f"{e}")

async def send_get_request(url, headers, error_msg='', data=None, proxies=None, verify=False, params=None, json=None):
    async with httpx.AsyncClient(verify=verify, proxy=proxies) as client:
        try:
            response = await client.get(url, headers=headers, params=params)
            return response
        except Exception as e:
            logging.error(f"Failed to {error_msg}: {e}")
            raise HTTPException(status_code=504, detail=f"{e}")

async def send_patch_request(url, headers, error_msg='', data=None, proxies=None, verify=False, params=None, json=None):
    async with httpx.AsyncClient(verify=verify, proxy=proxies) as client:
        try:
            response = await client.patch(url, data=data, headers=headers, params=params, json=json)
            return response
        except Exception as e:
            logging.error(f"Failed to {error_msg}: {e}")
            raise HTTPException(status_code=504, detail=f"{e}")

async def send_put_request(url, headers, error_msg='', data=None, proxies=None, verify=False, params=None, json=None):
    async with httpx.AsyncClient(verify=verify, proxy=proxies) as client:
        try:
            response = await client.put(url, data=data, headers=headers, params=params, json=json)
            return response
        except Exception as e:
            logging.error(f"Failed to {error_msg}: {e}")
            raise HTTPException(status_code=504, detail=f"{e}")