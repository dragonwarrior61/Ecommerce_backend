from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

DATABASE_URL = settings.DATABASE_URL

engine = create_async_engine(
    DATABASE_URL,
    echo=True,
    future=True,  # Ensure using the latest async features
    pool_size=10,  # Increase the pool size to 10 (default is 5)
    max_overflow=20,  # Allow more overflow connections
    pool_timeout=30,  # Timeout in seconds before giving up on acquiring a connection
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=AsyncSession)
Base = declarative_base()

async def get_db():
    async with SessionLocal() as session:
        yield session
