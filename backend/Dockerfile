# -------- Base stage: Shared settings --------
FROM python:3.14-slim AS base

ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# -------- Builder stage: Compile dependencies --------
FROM base AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN python -m venv "$VIRTUAL_ENV" \
    && pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# -------- Development stage --------
FROM base AS dev

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder "$VIRTUAL_ENV" "$VIRTUAL_ENV"

COPY . .
RUN chmod +x docker_entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["./docker_entrypoint.sh"]
CMD ["uvicorn", "backend.__main__:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# -------- Production stage --------
FROM base AS prod

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder "$VIRTUAL_ENV" "$VIRTUAL_ENV"

COPY . .
RUN chmod +x docker_entrypoint.sh

# Security: Run as non-root user (Standard Production Practice)
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
ENTRYPOINT ["./docker_entrypoint.sh"]
CMD ["uvicorn", "backend.__main__:app", "--host", "0.0.0.0", "--port", "8000"]
