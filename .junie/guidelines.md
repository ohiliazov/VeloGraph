# VeloGraph Project Guidelines

You are an expert in Python, FastAPI, SQLAlchemy, and scalable web application development.
You write secure, maintainable, and performant code following modern Python and FastAPI best practices.

## Python Best Practices
- Follow PEP 8 with a 120-character line limit (as configured in `ruff.toml`).
- Use `ruff` for linting and formatting; it handles both `flake8` and `isort` rules.
- Prefer double quotes for strings and docstrings.
- Use f-strings for string formatting.
- Always use type hints for function signatures and variable declarations (Python 3.14+).
- **Target Version**: Python 3.13+ (Use 3.14 features only if explicitly requested).
- **Docstrings**: Use Google-style docstrings for non-trivial functions.

## FastAPI Best Practices
- Use `Annotated` for dependency injection (e.g., `db: Annotated[AsyncSession, Depends(get_async_db)]`).
- Always define `response_model` in route decorators to ensure data validation and documentation.
- Use `async def` for route handlers to leverage asynchronous I/O.
- Handle exceptions gracefully with `HTTPException` or custom exception handlers.
- Use `APIRouter` to modularize API routes into logical groups.

## Models (SQLAlchemy)
- Use modern SQLAlchemy 2.0 style with `Mapped` and `mapped_column`.
- Define `__tablename__` for all ORM models.
- Use `relationship` with `back_populates` for bidirectional relationships.
- Use `UniqueConstraint` for composite unique keys when needed.
- Prefer `selectinload` for prefetching collections and `joinedload` for many-to-one relationships to avoid N+1 queries.
- Use `AsyncSession` for all database interactions.

## Schemas (Pydantic)
- Use Pydantic v2 features and syntax (`model_validator`, `computed_field`, etc.).
- Use `ConfigDict(from_attributes=True)` to allow Pydantic models to work with ORM objects.
- Use `Field(default_factory=list)` for list fields to avoid issues with mutable default arguments.
- Use `model_validator(mode="after")` for complex field derivations or cross-field validation.
- Keep schemas in `api/schemas.py` and reuse them across routes and scripts.

## Database & Migrations
- Use Alembic for all database schema changes.
- Never modify the database schema manually; always generate a new migration.
- Add indexes to frequently queried columns (e.g., `brand_name`, `stack_mm`) in the model definition.
- Optimize database queries by selecting only required fields when possible.

## Search (Elasticsearch)
- Use the asynchronous Elasticsearch client (`AsyncElasticsearch`).
- Keep Elasticsearch indices in sync with the database; implement sync logic in route handlers or background tasks.
- Use Painless scripts for complex search scoring or distance calculations.
- Always handle potential Elasticsearch connection issues or errors gracefully.

## Settings
- Use `pydantic-settings` to manage configuration via environment variables.
- Group related settings into a single `config.py` file or similar.
- Never commit secrets to version control; use `.env` files for local development.

## Scripts & Crawling
- Use `playwright` for dynamic content and `selectolax` for fast HTML parsing.
- Modularize scripts into `crawlers` (fetching data) and `extractors` (parsing data).
- Use `loguru` for logging in scripts to provide better visibility during long-running tasks.
- Implement proper error handling and retries (e.g., using `tenacity`) for external requests.

## Testing
- Use `pytest` for all tests.
- Write asynchronous tests using `pytest-asyncio` and `httpx.AsyncClient`.
- Ensure new features have both unit tests for core logic and integration tests for API endpoints.
- Test both positive and negative scenarios (e.g., 404 responses, invalid input).
- **Data Generation**: Use `polyfactory` to generate test data models; avoid manual dictionary creation for complex Pydantic models.
- **Isolation**: Ensure `conftest.py` handles the async loop scope correctly (`scope="session"` vs `scope="function"`).
