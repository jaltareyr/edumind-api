# Simple Dockerfile for FastAPI LightRAG application
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY lightrag/ ./lightrag/
COPY pyproject.toml .
COPY setup.py .

# Install the application
RUN pip install --no-cache-dir ".[api]"

# Create data directories
RUN mkdir -p /app/data/rag_storage /app/data/inputs /app/data/tiktoken

# Set environment variables
ENV WORKING_DIR=/app/data/rag_storage
ENV INPUT_DIR=/app/data/inputs
ENV TIKTOKEN_CACHE_DIR=/app/data/tiktoken

# Expose port
EXPOSE 9621

# Run the FastAPI server
CMD ["python", "-m", "lightrag.api.lightrag_server"]
