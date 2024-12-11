from fastapi import APIRouter
import requests
from fastapi.responses import StreamingResponse
from io import BytesIO
router = APIRouter()

@router.get("/")
async def proxy(url: str):
    # Make the external request using the URL
    try:
        response = requests.get(url, stream=True)
        # Pass the response back as a StreamingResponse
        return StreamingResponse(BytesIO(response.content), media_type=response.headers['Content-Type'])
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}