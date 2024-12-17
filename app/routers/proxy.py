import httpx
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from io import BytesIO

router = APIRouter()

@router.get("/")
async def proxy(url: str):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            return StreamingResponse(BytesIO(response.content), media_type=response.headers['Content-Type'])
    except httpx.RequestError as e:
        return {"error": str(e)}
