import httpx, logging
from fastapi import HTTPException
from app.logfiles import log_refresh_orders

async def send_post_request(url, headers, error_msg='', data=None, proxies=None, verify=False, params=None, json=None):
    async with httpx.AsyncClient(verify=verify, proxy=proxies) as client:
        response = await client.post(url, data=data, headers=headers, params=params, json=json)
        log_refresh_orders(response.json())
        return response

async def send_get_request(url, headers, error_msg='', data=None, proxies=None, verify=False, params=None, json=None):
    async with httpx.AsyncClient(verify=verify, proxy=proxies) as client:
        response = await client.get(url, headers=headers, params=params)
        return response

async def send_patch_request(url, headers, error_msg='', data=None, proxies=None, verify=False, params=None, json=None):
    async with httpx.AsyncClient(verify=verify, proxy=proxies) as client:
        response = await client.patch(url, data=data, headers=headers, params=params, json=json)
        return response

async def send_put_request(url, headers, error_msg='', data=None, proxies=None, verify=False, params=None, json=None):
    async with httpx.AsyncClient(verify=verify, proxy=proxies) as client:
        response = await client.put(url, data=data, headers=headers, params=params, json=json)
        return response
