import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database import get_db  # Assuming get_db is an async generator that provides a Session object
from app.models.awb import AWB
import pandas as pd
import numpy as np
from fastapi import Depends

# Assuming the excel file path is correct


# Use an async function to handle the database interaction
async def update_awbs(db: AsyncSession = Depends(get_db)):
    async for db in get_db():
        async with db as session:
            exceal_file = "app/routers/awb.xlsx"

            df = pd.read_excel(exceal_file)

            awb_order = df[['AWB', 'ORDERID', 'WarehouseID', 'Data creare AWB']]
            awb_order_list = awb_order.values.tolist()
            
            order_id_count = {}
            for awb in awb_order_list:
                order_id = awb[1]
                if pd.isna(order_id):
                    continue  # Skip if order_id is NaN
                order_id = int(order_id)
                if order_id in order_id_count:
                    order_id_count[order_id] += 1
                else:
                    order_id_count[order_id] = 1
            
            duplicate_order = []
            for awb in awb_order_list:
                order_id = awb[1]
                if pd.isna(order_id):
                    continue  # Skip if order_id is NaN
                order_id = int(order_id)
                if order_id_count[order_id] > 1:
                    duplicate_order.append(order_id)
            
            
            print(duplicate_order)
            # for awb in awb_order_list:
            #     awb_number = awb[0]
            #     if awb_number is None:
            #         continue
                
            #     # Check for NaN values and convert to integer only if valid
            #     order_id = awb[1]
            #     if pd.isna(order_id):
            #         continue  # Skip if order_id is NaN
            #     order_id = int(order_id)
                
            #     warehouse_id = awb[2]
            #     if pd.isna(warehouse_id):
            #         continue  # Skip if warehouse_id is NaN
            #     warehouse_id = int(warehouse_id)
                
            #     awb_date = awb[3]
            #     if pd.isna(awb_date):
            #         continue
            #     awb_date = str(awb_date)
                
            #     # Query the AWB record in the database
            #     result = await session.execute(select(AWB).where(AWB.order_id == order_id, AWB.number == warehouse_id))
            #     db_awb = result.scalars().first()
                
            #     new_awb = []
            #     if db_awb is None:
            #         new_awb.append(
            #             {
            #                 'orderId': order_id,
            #                 'date': awb_date,
            #                 'awb': awb_number
            #             }
            #         )
            #         continue
                
                # Update the AWB record with the new number and barcode
                

# Running the async function in an event loop
if __name__ == "__main__":
    asyncio.run(update_awbs())
