FROM alpine:3.19

# Install basic tools for networking and HTTP server  
RUN apk add --no-cache curl netcat-openbsd python3 py3-pip

# Create a simple Python HTTP server for metrics
RUN mkdir -p /opt/srsran
WORKDIR /opt/srsran

# Copy Python scripts
COPY ue_simulator.py start.sh ./
RUN chmod +x start.sh ue_simulator.py

# Debug - list files and permissions
RUN ls -la /opt/srsran/

# Expose metrics port
EXPOSE 9092

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:9092/metrics || exit 1

CMD ["/bin/sh", "/opt/srsran/start.sh"]
