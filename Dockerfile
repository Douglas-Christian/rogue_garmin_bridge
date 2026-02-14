# Multi-stage build for production deployment
# Stage 1: Build dependencies
FROM python:3.12-slim AS builder

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    build-essential \
    libbluetooth-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Stage 2: Production image
FROM python:3.12-slim AS production

# Install runtime system dependencies
RUN apt-get update && apt-get install -y \
    bluetooth \
    bluez \
    libbluetooth3 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser -u 1000 appuser

# Set working directory
WORKDIR /app

# Copy application code
COPY --chown=appuser:appuser . .

# Create necessary directories with proper permissions
RUN mkdir -p /app/data /app/logs /app/fit_files && \
    chown -R appuser:appuser /app/data /app/logs /app/fit_files



# Expose port
EXPOSE 5000

# Copy health check script
COPY scripts/docker-healthcheck.sh /usr/local/bin/healthcheck.sh
RUN chmod +x /usr/local/bin/healthcheck.sh

# Switch to non-root user
USER appuser

# Add health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD /usr/local/bin/healthcheck.sh

# Set environment variables
ENV FLASK_APP=src.web.app \
    FLASK_ENV=production \
    PYTHONPATH=/app \
    PYTHONUNBUFFERED=1

# Run the application
CMD ["python", "src/web/app.py", "--host", "0.0.0.0", "--port", "5000"]
