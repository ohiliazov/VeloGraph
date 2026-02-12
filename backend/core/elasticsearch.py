from elasticsearch import AsyncElasticsearch

from config import es_settings

BIKE_INDEX_NAME = "bikes"
GEOMETRY_INDEX_NAME = "geometries"

BIKE_INDEX_MAPPING = {
    "mappings": {
        "properties": {
            "id": {"type": "integer"},
            "definition": {
                "properties": {
                    "brand_name": {"type": "keyword"},
                    "model_name": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword"}},
                    },
                    "category": {"type": "keyword"},
                    "material": {"type": "keyword"},
                    "material_group": {"type": "keyword"},
                }
            },
            "sizes": {"type": "keyword"},
        }
    }
}

GEOMETRY_INDEX_SETTINGS = {
    "analysis": {
        "analyzer": {
            "bike_name_analyzer": {
                "type": "custom",
                "tokenizer": "standard",
                "filter": ["lowercase", "asciifolding"],
            }
        }
    }
}

GEOMETRY_INDEX_MAPPING = {
    "mappings": {
        "properties": {
            "id": {"type": "integer"},
            "geometry_spec": {
                "properties": {
                    "size_label": {"type": "keyword"},
                    "stack_mm": {"type": "integer"},
                    "reach_mm": {"type": "integer"},
                }
            },
            "definition": {
                "properties": {
                    "brand_name": {"type": "keyword"},
                    "model_name": {
                        "type": "text",
                        "analyzer": "bike_name_analyzer",
                        "fields": {"keyword": {"type": "keyword"}},
                    },
                    "category": {"type": "keyword"},
                    "material": {"type": "keyword"},
                    "material_group": {"type": "keyword"},
                }
            },
        }
    }
}


es_client = AsyncElasticsearch(
    hosts=[es_settings.url],
)


async def get_es_client() -> AsyncElasticsearch:
    return es_client
