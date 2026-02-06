import argparse

from loguru import logger
from sqlalchemy import create_engine, exc
from sqlalchemy.orm import sessionmaker

from backend.config import pg_settings
from backend.core.models import Base

engine = create_engine(pg_settings.connection_string)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db(drop_all: bool = False):
    try:
        if drop_all:
            logger.warning("Re-initializing database: dropping all tables...")
            Base.metadata.drop_all(engine)
            logger.success("✅ All tables dropped.")

        Base.metadata.create_all(engine)
        logger.success(
            "✅ Database schema initialized for '{}' on {}:{}",
            pg_settings.db,
            pg_settings.host,
            pg_settings.port,
        )
    except exc.SQLAlchemyError as e:
        logger.error("❌ Failed to initialize database: {}", e)
        raise


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Initialize the database.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Drop all tables and re-initialize the database.",
    )
    args = parser.parse_args()

    init_db(drop_all=args.force)
