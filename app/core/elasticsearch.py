from elasticsearch import AsyncElasticsearch
from pydantic_settings import BaseSettings


class ElasticsearchSettings(BaseSettings):
    model_config = {"env_prefix": "ES_"}

    url: str = "http://elasticsearch:9200"

    def __repr__(self):
        return f"ElasticsearchSettings(url='{self.url}')"


es_settings = ElasticsearchSettings()

es_client = AsyncElasticsearch(
    hosts=[es_settings.url],
    # not needed
    # verify_certs=False,
    # basic_auth=("elastic", "password")
)


async def get_es_client() -> AsyncElasticsearch:
    return es_client
