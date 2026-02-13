from pathlib import Path

from loguru import logger
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class PostgresSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="POSTGRES_",
        env_file=Path(__file__).parent.parent / ".env",
        extra="ignore",
    )

    user: str
    password: SecretStr
    db: str
    host: str = "postgres"
    port: int = 5432

    def __repr__(self):
        return f"PostgresSettings({self})"

    @property
    def connection_string(self):
        return f"postgresql+asyncpg://{self.user}:{self.password.get_secret_value()}@{self.host}:{self.port}/{self.db}"


class ElasticsearchSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ELASTICSEARCH_",
        env_file=Path(__file__).parent.parent / ".env",
        extra="ignore",
    )

    host: str = "elasticsearch"
    port: int = 9200

    def __repr__(self):
        return f"ElasticsearchSettings({self})"

    @property
    def url(self):
        return f"http://{self.host}:{self.port}"


pg_settings = PostgresSettings()
es_settings = ElasticsearchSettings()


if __name__ == "__main__":
    logger.info("🐘 Postgres settings loaded: {}", repr(pg_settings))
    logger.info("🔍 Elasticsearch settings loaded: {}", repr(es_settings))
