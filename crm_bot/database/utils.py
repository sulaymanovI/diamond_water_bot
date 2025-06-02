from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from config import Config
import asyncio

async def create_db_engine():
    try:
        engine = create_async_engine(
            Config.DATABASE_URL,
            echo=True,
            pool_pre_ping=True,  # Проверяет соединения перед использованием
            pool_recycle=3600     # Пересоздает соединения каждый час
        )
        return engine
    except SQLAlchemyError as e:
        raise

engine = asyncio.run(create_db_engine())
async_session = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)