import asyncio
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi_utils.tasks import repeat_every
from sqlalchemy import select
from app.routers import auth, billing_software, internal_products, returns, users, shipment, profile, marketplace, utils, orders, dashboard, supplier, inventory, AWB_generation, notifications, warehouse, team_member, locality, courier, review, product, replacement, invoice, damaged_good, sync_stock, temp_product, proxy, scan_awb, reverse_invoice
from app.database import Base, engine
from app.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.marketplace import Marketplace
from app.models.locality import Locality
from sqlalchemy.orm import Session
import ssl
import logging

logging.getLogger("sqlalchmy").setLevel(logging.CRITICAL)

# member
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
# from module import Member, get_member, check_access

app = FastAPI()

class MemberResponse(BaseModel):
    username: str
    role_name: str
    access_level: str


app = FastAPI()

ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ssl_context.load_cert_chain('ssl/cert.pem', keyfile='ssl/key.pem')

origins = [
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
async def init_models():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.on_event("startup")
async def on_startup():
    await init_models()

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(internal_products.router, prefix="/api/internal_products", tags=["internal_products"])
app.include_router(profile.router, prefix="/profile", tags=["profile"])
app.include_router(marketplace.router, prefix="/api/marketplace", tags=["marketplace"])
app.include_router(utils.router, prefix="/api/utils", tags=["utils"])
app.include_router(orders.router, prefix="/api/orders", tags=["orders"])
app.include_router(supplier.router, prefix="/api/suppliers", tags=["supppliers"])
app.include_router(shipment.router, prefix="/api/shipment", tags=["shipment"])
app.include_router(returns.router, prefix="/api/returns", tags=["returns"])
app.include_router(inventory.router, prefix="/api/inventory", tags=["inventory"])
app.include_router(AWB_generation.router, prefix="/awb", tags=["awb"])
app.include_router(notifications.router, prefix='/api/notifications', tags=["notifications"])
app.include_router(warehouse.router, prefix="/api/warehouse", tags=["warehouses"])
app.include_router(team_member.router, prefix="/api/team_member", tags=["team_member"])
app.include_router(locality.router, prefix="/api/locality", tags=['locality'])
app.include_router(courier.router, prefix="/api/courier", tags=['courier'])
app.include_router(review.router, prefix="/api/reiew", tags=["review"])
app.include_router(product.router, prefix="/api/product", tags=["product"])
app.include_router(replacement.router, prefix="/api/replacement", tags=["replacement"])
app.include_router(invoice.router, prefix="/api/invoice", tags=["invoice"])
app.include_router(billing_software.router, prefix="/api/smartbill_account", tags=["smartbill_account"])
app.include_router(damaged_good.router, prefix="/api/damaged_good", tags=["damaged_good"])
app.include_router(sync_stock.router, prefix="/api/sync_stock", tags=["sync_stock"])
app.include_router(temp_product.router, prefix="/api/temp_product", tags=["temp_product"])
app.include_router(proxy.router, prefix="/api/proxy", tags=["proxy"])
app.include_router(scan_awb.router, prefix="/api/Scan_awb", tags=["Scan_awb"])
app.include_router(reverse_invoice.router, prefix="/api/reverse_invoice", tags=["Reverse_Invoice"])

if __name__ == "__main__":
    import uvicorn
    ssl_keyfile = "ssl/key.pem"
    ssl_certfile = "ssl/cert.pem"
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        ssl_keyfile=ssl_keyfile,
        ssl_certfile=ssl_certfile,
    )
