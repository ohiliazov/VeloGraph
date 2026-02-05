# VeloGraph Database Migrations

This directory contains Alembic migration scripts for the VeloGraph PostgreSQL database.

## Usage

Migrations should be run from the `backend` directory. Ensure your `PYTHONPATH` includes the current directory.

### Applying Migrations

To upgrade the database to the latest version:
```bash
export PYTHONPATH=$PYTHONPATH:.
alembic upgrade head
```

### Creating a New Migration

After modifying models in `backend/core/models.py`, generate a new migration script:
```bash
export PYTHONPATH=$PYTHONPATH:.
alembic revision --autogenerate -m "description of changes"
```

### Reverting Migrations

To downgrade the database by one version:
```bash
export PYTHONPATH=$PYTHONPATH:.
alembic downgrade -1
```

## Structure

- `versions/`: Directory containing individual migration scripts.
- `env.py`: Configuration script for the Alembic migration environment.
- `script.py.mako`: Template for generating new migration scripts.
