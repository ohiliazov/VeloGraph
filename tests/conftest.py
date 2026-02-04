from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.__main__ import app
from app.core.db import get_db
from app.core.elasticsearch import get_es_client


@pytest.fixture
def mock_db():
    return MagicMock(spec=Session)


@pytest.fixture
def mock_es():
    return AsyncMock()


@pytest.fixture
def client(mock_db, mock_es):
    def override_get_db():
        yield mock_db

    async def override_get_es_client():
        return mock_es

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_es_client] = override_get_es_client

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
