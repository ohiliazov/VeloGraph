# -------- Builder stage: build deps into a venv --------
FROM python:3.12-slim AS builder

ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# System build deps for compiling wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy only dependency manifests first to leverage Docker layer caching
COPY requirements.txt ./

# Create venv and install deps
RUN python -m venv "$VIRTUAL_ENV" \
 && pip install --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# -------- Development stage --------
FROM python:3.14-slim AS dev

ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Include headers for possible native builds in dev
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install python deps in a venv (editable dev experience via bind-mount)
COPY requirements.txt /tmp/requirements.txt
RUN python -m venv "$VIRTUAL_ENV" \
 && pip install --upgrade pip \
 && pip install --no-cache-dir -r /tmp/requirements.txt

# Copy source (can be overridden by volume in docker-compose for live reload)
COPY . /app/backend/

EXPOSE 8000

# Dev server with reload
CMD ["uvicorn", "backend.__main__:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# -------- Production runtime stage: slim image with runtime libs only --------
FROM python:3.14-slim AS prod

# Install only runtime libraries (no compilers)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

WORKDIR /app

# Bring in the prebuilt virtualenv from builder
COPY --from=builder /opt/venv /opt/venv

# Copy application code (keep module path as in original image)
COPY . /app/backend/

# Expose port
EXPOSE 8000

# Default command (no reload)
CMD ["uvicorn", "backend.__main__:app", "--host", "0.0.0.0", "--port", "8000"]
