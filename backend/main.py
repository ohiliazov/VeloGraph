import logging
import sys
import time
from typing import Annotated

from elasticsearch import AsyncElasticsearch
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.routes import bikes
from core.db import get_async_db
from core.elasticsearch import get_es_client
from utils.logging import InterceptHandler


def setup_logging():
    # 1. Clear default handlers and set Loguru format
    logger.remove()

    def filter_health_checks(record):
        return "/health" not in record["message"]

    logger.add(
        sys.stdout,
        enqueue=True,
        backtrace=True,
        level="INFO",
        filter=filter_health_checks,
    )

    # 2. Prepare the list of loggers to intercept
    # We include 'uvicorn' specifically because it might not be in loggerDict yet
    loggers = [name for name in logging.root.manager.loggerDict if name.startswith(("uvicorn", "fastapi"))] + [
        "uvicorn",
        "uvicorn.access",
        "uvicorn.error",
    ]

    for name in loggers:
        logging_logger = logging.getLogger(name)
        logging_logger.handlers = [InterceptHandler()]
        logging_logger.propagate = False

    # 3. Handle the root logger
    logging.getLogger().handlers = [InterceptHandler()]


def create_app() -> FastAPI:
    setup_logging()

    _app = FastAPI(title="VeloGraph API")

    _app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    _app.include_router(bikes.router, prefix="/api/bikes", tags=["bikes"])

    logger.info("VeloGraph API setup complete.")
    return _app


app = create_app()


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time

    logger.info(f"{request.method} {request.url.path} Status: {response.status_code} Duration: {duration:.2f}s")
    return response


@app.get("/")
async def root():
    return {"message": "VeloGraph API", "version": "0.1.0"}


@app.get("/health", tags=["health"])
async def health_check(
    db: Annotated[AsyncSession, Depends(get_async_db)], es: Annotated[AsyncElasticsearch, Depends(get_es_client)]
):
    """
    Check if the API, Database, and Elasticsearch are responsive.
    """
    health_status = {"status": "healthy", "timestamp": time.time(), "services": {}}
    errors = []

    try:
        await db.execute(text("SELECT 1"))
        health_status["services"]["database"] = "reachable"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        health_status["services"]["database"] = "unreachable"
        errors.append("database")

    try:
        if await es.ping():
            health_status["services"]["elasticsearch"] = "reachable"
        else:
            raise ValueError("Elasticsearch ping returned False")
    except Exception as e:
        logger.error(f"Elasticsearch health check failed: {e}")
        health_status["services"]["elasticsearch"] = "unreachable"
        errors.append("elasticsearch")

    if errors:
        health_status["status"] = "unhealthy"
        raise HTTPException(status_code=503, detail=health_status)

    logger.info("Health check complete: {}", health_status)

    return health_status
