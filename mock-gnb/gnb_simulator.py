#!/usr/bin/env python3
"""
Mock srsRAN gNB Simulator
Simulates a 5G gNodeB with basic logging and metrics
"""

import time
import random
import threading
import socket
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import logging
import os
import re
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [gNB] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

def parse_device_args():
    """Parse ZMQ device arguments from environment variables"""
    device_args = os.getenv('DEVICE_ARGS', '')
    logger.info(f"Parsing device args: {device_args}")
    
    # Default values
    tx_port = ('127.0.0.1', 2000)
    rx_port = ('127.0.0.1', 2001)
    
    if device_args:
        # Parse tx_port=tcp://127.0.0.1:2000,rx_port=tcp://127.0.0.1:2001,base_srate=23.04e6
        parts = device_args.split(',')
        for part in parts:
            if 'tx_port=' in part:
                url = part.split('tx_port=')[1]
                parsed = urlparse(url)
                tx_port = (parsed.hostname or '127.0.0.1', parsed.port or 2000)
                logger.info(f"Parsed TX port: {tx_port}")
            elif 'rx_port=' in part:
                url = part.split('rx_port=')[1]
                parsed = urlparse(url)
                rx_port = (parsed.hostname or '127.0.0.1', parsed.port or 2001)
                logger.info(f"Parsed RX port: {rx_port}")
    
    return tx_port, rx_port

class MetricsHandler(BaseHTTPRequestHandler):
    """Simple HTTP handler for Prometheus-style metrics"""
    
    def do_GET(self):
        if self.path == '/metrics':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            
            # Mock Prometheus metrics
            metrics = f"""# gNB Metrics
gnb_connected_ues_total {random.randint(1, 5)}
gnb_active_bearers_total {random.randint(1, 10)}
gnb_ul_throughput_mbps {random.uniform(10, 100):.2f}
gnb_dl_throughput_mbps {random.uniform(20, 150):.2f}
gnb_cpu_usage_percent {random.uniform(20, 80):.1f}
gnb_memory_usage_percent {random.uniform(30, 70):.1f}
"""
            self.wfile.write(metrics.encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        # Suppress default HTTP server logs
        pass

def start_zmq_ports():
    """Start TCP servers on ZMQ ports to simulate RF connectivity"""
    # Parse the device arguments to get correct IPs and ports
    tx_port, rx_port = parse_device_args()
    
    def start_port_listener(host, port, port_name):
        try:
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind((host, port))
            server_socket.listen(5)
            logger.info(f"ZMQ {port_name} port {host}:{port} listener started")
            
            while True:
                try:
                    client_socket, addr = server_socket.accept()
                    logger.info(f"ZMQ connection from {addr} on {port_name} port {host}:{port}")
                    # Keep connection alive to simulate ZMQ
                    client_socket.recv(1024)  # Consume any data
                    client_socket.close()
                except Exception as e:
                    logger.debug(f"ZMQ {port_name} port {host}:{port} error: {e}")
                    time.sleep(1)
        except Exception as e:
            logger.error(f"Failed to start ZMQ {port_name} port {host}:{port}: {e}")
    
    # Start port listeners in background threads using parsed configuration
    threading.Thread(target=start_port_listener, args=(tx_port[0], tx_port[1], "TX"), daemon=True).start()
    threading.Thread(target=start_port_listener, args=(rx_port[0], rx_port[1], "RX"), daemon=True).start()

def start_metrics_server():
    """Start the metrics HTTP server"""
    server = HTTPServer(('0.0.0.0', 9091), MetricsHandler)
    logger.info("Starting metrics server on port 9091")
    server.serve_forever()

def simulate_gnb_operations():
    """Simulate gNB operations with realistic logging"""
    
    logger.info("Initializing srsRAN gNB...")
    time.sleep(2)
    
    logger.info("Loading RF configuration...")
    time.sleep(1)
    
    logger.info("Starting gNB with cell ID: 1")
    logger.info("PLMN: 001-01")
    logger.info("Frequency: 3500 MHz (Band n78)")
    logger.info("Bandwidth: 20 MHz")
    
    time.sleep(2)
    logger.info("gNB is now operational and ready for UE connections")
    
    # Simulate periodic operations
    ue_connections = []
    
    while True:
        # Simulate random UE connections/disconnections
        if random.random() < 0.3 and len(ue_connections) < 5:
            ue_id = f"ue_{random.randint(1000, 9999)}"
            ue_connections.append(ue_id)
            logger.info(f"UE {ue_id} attempting RRC connection")
            time.sleep(1)
            logger.info(f"UE {ue_id} RRC CONNECTED")
            logger.info(f"UE {ue_id} completed authentication and security setup")
            
        if random.random() < 0.1 and ue_connections:
            ue_id = random.choice(ue_connections)
            ue_connections.remove(ue_id)
            logger.info(f"UE {ue_id} disconnected")
        
        # Simulate periodic status updates
        if random.random() < 0.2:
            logger.info(f"Active UEs: {len(ue_connections)}")
            if ue_connections:
                logger.info(f"Total throughput: UL={random.uniform(10, 50):.1f} Mbps, DL={random.uniform(20, 100):.1f} Mbps")
        
        time.sleep(random.uniform(5, 15))

def main():
    """Main function to start both metrics server and gNB simulation"""
    
    # Start ZMQ ports simulation
    start_zmq_ports()
    
    # Start metrics server in background thread
    metrics_thread = threading.Thread(target=start_metrics_server, daemon=True)
    metrics_thread.start()
    
    # Start gNB simulation
    try:
        simulate_gnb_operations()
    except KeyboardInterrupt:
        logger.info("Shutting down gNB...")

if __name__ == "__main__":
    main()
