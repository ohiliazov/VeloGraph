from elasticsearch import AsyncElasticsearch

from app.config import es_settings

es_client = AsyncElasticsearch(
    hosts=[es_settings.url],
)


async def get_es_client() -> AsyncElasticsearch:
    return es_client
