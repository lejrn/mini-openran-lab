#!/usr/bin/env python3
"""
Mock srsRAN UE Simulator
Simulates a 5G User Equipment with connection lifecycle
"""

import time
import random
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [UE] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

# Global state
connected = False
start_time = time.time()

class MetricsHandler(BaseHTTPRequestHandler):
    """Simple HTTP handler for Prometheus-style metrics"""
    
    def do_GET(self):
        if self.path == '/metrics':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            
            # Mock Prometheus metrics
            metrics = f"""# UE Metrics
ue_connection_state {1 if connected else 0}
ue_signal_strength_dbm {random.randint(-80, -60)}
ue_uptime_seconds {int(time.time() - start_time)}
ue_data_throughput_mbps {random.uniform(5, 25):.2f}
ue_battery_level_percent {random.uniform(20, 100):.1f}
"""
            self.wfile.write(metrics.encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        # Suppress default HTTP server logs
        pass

def start_metrics_server():
    """Start the metrics HTTP server"""
    port = int(os.environ.get('PROMETHEUS_PORT', 9092))
    server = HTTPServer(('0.0.0.0', port), MetricsHandler)
    logger.info(f"Starting metrics server on port {port}")
    server.serve_forever()

def simulate_ue_operations():
    """Simulate UE operations with realistic connection lifecycle"""
    global connected
    
    connected = False
    
    logger.info("Initializing srsRAN UE...")
    time.sleep(2)
    
    # Wait for gNB to be ready (simulate init container behavior)  
    gnb_address = os.environ.get('GNB_ADDRESS', 'openran-gnb')
    logger.info(f"Waiting for gNB at {gnb_address}...")
    
    # Simulate cell search process
    logger.info("Starting cell search...")
    for i in range(3):
        logger.info(f"Cell search attempt {i+1}/3...")
        time.sleep(random.uniform(2, 5))
    
    logger.info("Cell found! PLMN: 001-01, Cell ID: 1")
    logger.info("Signal strength: -65 dBm")
    
    time.sleep(1)
    logger.info("Attempting RRC Connection...")
    time.sleep(random.uniform(1, 3))
    
    logger.info("RRC Connection Request sent")
    time.sleep(1)
    
    logger.info("RRC CONNECTED")
    logger.info("Successfully connected to gNB")
    connected = True
    
    # Simulate authentication and setup
    time.sleep(1)
    logger.info("Authentication procedure completed")
    logger.info("Security mode setup completed")
    logger.info("Initial context setup completed")
    
    # Simulate periodic UE operations
    while True:
        if connected:
            # Periodic status updates
            if random.random() < 0.3:
                signal_strength = random.randint(-80, -60)
                throughput = random.uniform(5, 25)
                logger.info(f"Status: Signal={signal_strength}dBm, Throughput={throughput:.1f}Mbps")
            
            # Simulate occasional data transmission
            if random.random() < 0.2:
                data_size = random.randint(100, 1000)
                logger.info(f"Data transmission: {data_size} KB uplink")
            
            # Very small chance of disconnection
            if random.random() < 0.05:
                logger.info("Connection lost - attempting reconnection...")
                connected = False
                time.sleep(5)
                logger.info("RRC CONNECTED")
                connected = True
        
        time.sleep(random.uniform(10, 20))

def main():
    """Main function to start both metrics server and UE simulation"""
    
    # Start metrics server in background thread
    metrics_thread = threading.Thread(target=start_metrics_server, daemon=True)
    metrics_thread.start()
    
    # Start UE simulation
    try:
        simulate_ue_operations()
    except KeyboardInterrupt:
        logger.info("Shutting down UE...")

if __name__ == "__main__":
    main()
