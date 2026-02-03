from loguru import logger
from sqlalchemy import create_engine

from app.config import pg_settings
from app.core.models import Base

if __name__ == "__main__":
    engine = create_engine(pg_settings.connection_string)
    Base.metadata.create_all(engine)
    logger.success(
        "✅ Database schema created for '{}' on {}:{}",
        pg_settings.db,
        pg_settings.host,
        pg_settings.port,
    )
