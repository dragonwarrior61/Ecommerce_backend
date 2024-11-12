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

            awb_order = df[['AWB', 'order_id', 'warehouse_id', 'Data creare AWB']]
            awb_order_list = awb_order.values.tolist()
            
            # Step 1: Track order_ids and associated warehouse_ids
            # order_warehouse_map = {}
            # for awb in awb_order_list:
            #     order_id = awb[1]
            #     warehouse_id = awb[2]
            #     if pd.isna(order_id) or pd.isna(warehouse_id):
            #         continue  # Skip if order_id or warehouse_id is NaN
                
            #     order_id = int(order_id)
            #     warehouse_id = int(warehouse_id)
                
            #     if order_id not in order_warehouse_map:
            #         order_warehouse_map[order_id] = set()
                
            #     # Add the warehouse_id to the set for this order_id
            #     order_warehouse_map[order_id].add(warehouse_id)
            
            # # Step 2: Find order_ids with multiple distinct warehouse_ids
            # order_ids_with_multiple_warehouses = []
            # for order_id, warehouses in order_warehouse_map.items():
            #     if len(warehouses) > 1:  # More than 1 distinct warehouse_id
            #         order_ids_with_multiple_warehouses.append(order_id)
            
            # print(order_ids_with_multiple_warehouses)
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
                
                awb_date = awb[3]
                if pd.isna(awb_date):
                    continue
                awb_date = str(awb_date)
                
                # Query the AWB record in the database
                result = await session.execute(select(AWB).where(AWB.order_id == order_id, AWB.number == warehouse_id))
                db_awb = result.scalars().first()
                
                db_awb.awb_number = awb_number
                db_awb.awb_barcode = awb_number + '001'
                
                
                # new_awb = []
                # if db_awb is None:
                #     new_awb.append(
                #         {
                #             'orderId': order_id,
                #             'date': awb_date,
                #             'awb': awb_number
                #         }
                #     )
                #     continue
                
                # Update the AWB record with the new number and barcode
                

# Running the async function in an event loop
if __name__ == "__main__":
    asyncio.run(update_awbs())
