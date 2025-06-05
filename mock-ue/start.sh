#!/bin/bash
# Start script for mock srsRAN UE

echo "Starting mock srsRAN UE..."
echo "================================================"
echo "Configuration:"
echo "  Device Type: UE (User Equipment)"
echo "  Target gNB: ${GNB_ADDRESS:-openran-gnb}"
echo "  Metrics port: ${PROMETHEUS_PORT:-9092}"
echo "================================================"

# Create log directory
mkdir -p /var/log/srsran

# Make sure the Python script is executable
chmod +x /opt/srsran/ue_simulator.py

# Start the UE simulator
exec python3 /opt/srsran/ue_simulator.py
