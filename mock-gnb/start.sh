#!/bin/bash
# Start script for mock srsRAN gNB

echo "Starting mock srsRAN gNB..."
echo "================================================"
echo "Configuration:"
echo "  Cell ID: 1"
echo "  PLMN: 001-01"
echo "  Frequency: 3500 MHz (Band n78)"
echo "  Bandwidth: 20 MHz"
echo "  Metrics port: 9091"
echo "================================================"

# Make sure the Python script is executable
chmod +x /opt/srsran/gnb_simulator.py

# Start the gNB simulator
exec python3 /opt/srsran/gnb_simulator.py
