#!/usr/bin/env bash

alembic -c alembic.ini upgrade head

exec "$@"
