# Use Python 3.12 as base image
FROM python:3.12-slim as builder

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential

# Install uv
RUN pip install --no-cache-dir uv

# Set working directory
WORKDIR /app

# Copy all files
COPY . .

# Install dependencies and package using uv
RUN uv sync --frozen --no-dev

# Runtime stage
FROM python:3.12-slim

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app && \
    chown -R appuser:appuser /app

# Set working directory
WORKDIR /app

# Copy application files and virtual environment from builder
COPY --from=builder --chown=appuser:appuser /app/ /app/

# Switch to non-root user
USER appuser

# Add virtual environment to PATH
ENV PATH="/app/.venv/bin:$PATH"

# Expose default HTTP port
EXPOSE 8000

# Set default command to serve HTTP server
CMD ["otar-mcp", "serve-http", "--host", "0.0.0.0", "--port", "8000"]

