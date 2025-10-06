FROM python:3.13-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Create non-root user
RUN groupadd -r chef && useradd -r -g chef chef

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --no-cache-dir poetry

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Configure Poetry and install dependencies
RUN poetry config virtualenvs.create false && \
    poetry install --only=main

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/data /app/migrations /app/locales && \
    chown -R chef:chef /app

# Switch to non-root user
USER chef

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run migrations and start application
CMD ["sh", "-c", "poetry run python -m scripts.migrate && poetry run uvicorn main:app --host 0.0.0.0 --port 8000"]
