# Multi-stage build for minimal production image
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim

# Create non-root user for security
RUN groupadd --gid 1000 xapp && \
    useradd --uid 1000 --gid xapp --shell /bin/bash --create-home xapp

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy application code
COPY . .

# Change ownership to xapp user
RUN chown -R xapp:xapp /app

# Switch to non-root user
USER xapp

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/healthz')" || exit 1

# Expose port
EXPOSE 8080

# Set environment variables
ENV PYTHONPATH=/app
ENV LOG_LEVEL=INFO
ENV CQI_THRESHOLD=7.0
ENV ADJUSTMENT_INTERVAL=30

# Labels for better container management
LABEL org.opencontainers.image.title="Beam Tuner xApp"
LABEL org.opencontainers.image.description="Near-RT RIC xApp for beam tuning and MCS optimization"
LABEL org.opencontainers.image.vendor="Mini-OpenRAN Lab"
LABEL org.opencontainers.image.version="1.0.0"
LABEL org.opencontainers.image.source="https://github.com/mini-openran-lab/mini-openran-lab"

# Run the application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080", "--log-level", "info"]
