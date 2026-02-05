FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . /app/backend/

# Expose port
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "backend.__main__:app", "--host", "0.0.0.0", "--port", "8000"]
