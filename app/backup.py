import pandas as pd
from sqlalchemy import create_engine, inspect
from app.config import settings
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
import io
import datetime
import logging

async def export_to_csv():
    engine = create_async_engine(settings.DATABASE_URL, future=True, echo=True)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    
    async with async_session() as session:
        async with session.begin():  # Ensure session is active
            conn = await session.connection()  # Get a connection
            inspector = inspect(conn)  # Inspect the connection
            
            table_names = inspector.get_table_names()
            for table in table_names:
                backup_date = datetime.datetime.now().strftime("%Y%m%d")
                file_name = f"{table}_{backup_date}.csv"
                query = f'SELECT * FROM {table}'
                df = pd.read_sql(query, con=conn)

                # Use StringIO to create an in-memory CSV
                csv_buffer = io.StringIO()
                df.to_csv(csv_buffer, index=False)
                csv_buffer.seek(0)  # Move to the start of the StringIO buffer
                logging.info(f"Success {table} backup")
                await upload_to_google_sheets(csv_buffer, file_name)
            
async def upload_to_google_sheets(csv_buffer, file_name):
    SCOPES = ['https://www.googleapis.com/auth/drive.file']
    SERVICE_ACCOUNT_FILE = 'google.json'

    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    
    logging.info(f"Create credentials {credentials}")
    drive_service = build('drive', 'v3', credentials=credentials)

    file_metadata = {
        'name': file_name,
        'mimeType': 'text/csv'
    }

    media = MediaFileUpload(csv_buffer, mimetype='text/csv')  # Use the buffer directly
    file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    print(f'File ID: {file.get("id")}')
