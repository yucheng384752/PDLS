"""Database configuration and connection management for PDLS"""

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from contextlib import asynccontextmanager
from typing import AsyncGenerator
import logging

from .config import settings

logger = logging.getLogger(__name__)

# Create async engine for the database
async_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=300,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Async context manager for database sessions.
    
    Usage:
        async with get_async_session() as session:
            # Use session here
            result = await session.execute(...)
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency function for FastAPI to get database session.
    
    Usage:
        @router.get("/")
        async def get_items(db: AsyncSession = Depends(get_db_session)):
            result = await db.execute(...)
    """
    async with get_async_session() as session:
        yield session


async def init_database():
    """Initialize database connection and verify connectivity"""
    try:
        async with async_engine.begin() as conn:
            # Test connection
            await conn.execute(text("SELECT 1"))
            logger.info("Database connection established successfully")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise


async def close_database():
    """Close database connections"""
    await async_engine.dispose()
    logger.info("Database connections closed")


# For synchronous operations (like Alembic migrations)
sync_engine = create_engine(
    settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://"),
    echo=settings.DEBUG,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)

SyncSessionLocal = sessionmaker(bind=sync_engine)


def get_sync_session():
    """Get synchronous database session for migrations and admin tasks"""
    db = SyncSessionLocal()
    try:
        yield db
    finally:
        db.close()