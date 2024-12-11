import os
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    DB_USERNAME: str = "postgres"
    DB_PASSOWRD: str = "postgres"
    DB_URL: str = "localhost"
    DB_NAME: str = "ecommerce"
    DB_PORT: str = "5432"
    DATABASE_URL: str = f"postgresql+asyncpg://{DB_USERNAME}:{DB_PASSOWRD}@{DB_URL}/{DB_NAME}"
    SECRET_KEY: str = os.urandom(32).hex()
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 1440
    
    update_flag: int = 0
settings = Settings()
