import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database import get_db  # Assuming get_db is an async generator that provides a Session object
from app.models.awb import AWB
import pandas as pd
import numpy as np
from fastapi import Depends

# Assuming the excel file path is correct
exceal_file = "app/routers/awb.xlsx"

df = pd.read_excel(exceal_file)

awb_order = df[['AWB', 'ORDERID', 'WarehouseID']]
awb_order_list = awb_order.values.tolist()

# Use an async function to handle the database interaction
async def update_awbs(db: AsyncSession = Depends(get_db)):
    for awb in awb_order_list:
        awb_number = awb[0]
        if awb_number is None:
            continue
        
        # Check for NaN values and convert to integer only if valid
        order_id = awb[1]
        if pd.isna(order_id):
            continue  # Skip if order_id is NaN
        order_id = int(order_id)
        
        warehouse_id = awb[2]
        if pd.isna(warehouse_id):
            continue  # Skip if warehouse_id is NaN
        warehouse_id = int(warehouse_id)
        
        print(f"order_id: {order_id}, awb_number: {awb_number}, warehouse_id: {warehouse_id}")
        
        # Query the AWB record in the database
        result = await db.execute(select(AWB).where(AWB.order_id == order_id, AWB.number == warehouse_id))
        db_awb = result.scalars().first()
        
        if db_awb is None:
            continue
        
        # Update the AWB record with the new number and barcode
        db_awb.awb_number = awb_number
        db_awb.awb_barcode = awb_number + '001'

    # Commit the changes to the database after processing all rows
    await db.commit()

# Running the async function in an event loop
if __name__ == "__main__":
    asyncio.run(update_awbs())
