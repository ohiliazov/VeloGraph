from loguru import logger
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.config import pg_settings
from backend.core.models import Base

engine = create_engine(pg_settings.connection_string)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    Base.metadata.create_all(engine)
    logger.success(
        "✅ Database schema created for '{}' on {}:{}",
        pg_settings.db,
        pg_settings.host,
        pg_settings.port,
    )


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
