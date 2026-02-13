import argparse
from collections.abc import AsyncGenerator

from loguru import logger
from sqlalchemy import create_engine, exc
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker

from config import pg_settings
from core.models import Base

engine = create_engine(pg_settings.connection_string)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

async_engine = create_async_engine(pg_settings.async_connection_string, echo=False, future=True)
AsyncSessionLocal = async_sessionmaker(bind=async_engine, class_=AsyncSession, expire_on_commit=False, autoflush=False)


def init_db(drop_all: bool = False):
    try:
        if drop_all:
            logger.warning("Re-initializing database: dropping all tables...")
            Base.metadata.drop_all(engine)
            logger.success("✅ All tables dropped.")

        Base.metadata.create_all(engine)
        logger.success("✅ Database schema initialized.")
    except exc.SQLAlchemyError as e:
        logger.error("❌ Failed to initialize database: {}", e)
        raise


async def get_async_db() -> AsyncGenerator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Initialize the database.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Drop all tables and re-initialize the database.",
    )
    args = parser.parse_args()

    init_db(drop_all=args.force)
