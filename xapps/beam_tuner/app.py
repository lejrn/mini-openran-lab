"""
Beam Tuner xApp for Mini-OpenRAN Lab

This xApp demonstrates real-time optimization of radio parameters
by monitoring CQI (Channel Quality Indicator) and adjusting MCS
(Modulation and Coding Scheme) through the E2 interface.

Author: Mini-OpenRAN Lab Team
License: Apache 2.0
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from prometheus_client import CONTENT_TYPE_LATEST
import asyncio
import logging
import os
from datetime import datetime
from typing import Dict, Any

from .logic import BeamTunerLogic
from .e2_client import E2Client
from .metrics import MetricsCollector

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Prometheus metrics
cqi_observations = Histogram(
    'cqi_observations_seconds',
    'CQI observation processing time',
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
)

adjustment_counter = Counter(
    'mcs_adjustments_total',
    'Total number of MCS adjustments made',
    ['direction']  # 'up' or 'down'
)

current_cqi = Gauge(
    'current_cqi_value',
    'Current median CQI value'
)

current_mcs = Gauge(
    'current_mcs_value', 
    'Current MCS (Modulation and Coding Scheme) setting'
)

# FastAPI app
app = FastAPI(
    title="Beam Tuner xApp",
    description="Near-RT RIC xApp for real-time radio optimization",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Global components
beam_tuner: BeamTunerLogic = None
e2_client: E2Client = None
metrics_collector: MetricsCollector = None

@app.on_event("startup")
async def startup_event():
    """Initialize xApp components on startup."""
    global beam_tuner, e2_client, metrics_collector
    
    logger.info("🚀 Starting Beam Tuner xApp...")
    
    # Initialize components
    config = {
        'cqi_threshold': float(os.getenv('CQI_THRESHOLD', '7.0')),
        'adjustment_interval': int(os.getenv('ADJUSTMENT_INTERVAL', '30')),
        'ric_host': os.getenv('RIC_HOST', 'ric-platform'),
        'ric_port': int(os.getenv('RIC_PORT', '36421')),
        'gnb_host': os.getenv('GNB_HOST', 'srsran-gnb'),
        'gnb_port': int(os.getenv('GNB_PORT', '9091'))
    }
    
    try:
        beam_tuner = BeamTunerLogic(config)
        e2_client = E2Client(config['ric_host'], config['ric_port'])
        metrics_collector = MetricsCollector(config['gnb_host'], config['gnb_port'])
        
        # Start background monitoring task
        asyncio.create_task(monitoring_loop())
        
        logger.info("✅ Beam Tuner xApp started successfully")
        
    except Exception as e:
        logger.error(f"❌ Failed to start xApp: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("🛑 Shutting down Beam Tuner xApp...")
    
    if e2_client:
        await e2_client.disconnect()
    
    logger.info("✅ Shutdown complete")

@app.get("/healthz")
async def health_check():
    """Health check endpoint for Kubernetes."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.get("/readiness")
async def readiness_check():
    """Readiness check - verifies E2 connection."""
    if e2_client and await e2_client.is_connected():
        return {"status": "ready", "e2_connected": True}
    else:
        raise HTTPException(status_code=503, detail="E2 client not ready")

@app.get("/metrics")
async def get_metrics():
    """Prometheus metrics endpoint."""
    return generate_latest()

@app.get("/status")
async def get_status():
    """Get current xApp status and metrics."""
    if not beam_tuner:
        raise HTTPException(status_code=503, detail="xApp not initialized")
    
    status = beam_tuner.get_status()
    return JSONResponse(content=status)

@app.post("/adjust")
async def manual_adjustment(direction: str):
    """Manual MCS adjustment endpoint for testing."""
    if direction not in ['up', 'down']:
        raise HTTPException(status_code=400, detail="Direction must be 'up' or 'down'")
    
    if not beam_tuner or not e2_client:
        raise HTTPException(status_code=503, detail="xApp not ready")
    
    try:
        success = await beam_tuner.adjust_mcs(direction, e2_client)
        if success:
            adjustment_counter.labels(direction=direction).inc()
            return {"status": "success", "direction": direction}
        else:
            raise HTTPException(status_code=500, detail="Adjustment failed")
    except Exception as e:
        logger.error(f"Manual adjustment failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def monitoring_loop():
    """Main monitoring loop - runs continuously."""
    logger.info("📡 Starting monitoring loop...")
    
    while True:
        try:
            with cqi_observations.time():
                # Collect current metrics from gNB
                metrics = await metrics_collector.get_latest_metrics()
                
                if metrics:
                    cqi_value = metrics.get('cqi', 0)
                    current_cqi.set(cqi_value)
                    
                    mcs_value = metrics.get('mcs', 0)
                    current_mcs.set(mcs_value)
                    
                    # Process with beam tuner logic
                    action = beam_tuner.process_metrics(metrics)
                    
                    if action:
                        logger.info(f"🎯 Taking action: {action}")
                        success = await beam_tuner.execute_action(action, e2_client)
                        
                        if success:
                            adjustment_counter.labels(direction=action['direction']).inc()
                        else:
                            logger.warning(f"⚠️ Action execution failed: {action}")
                
                # Wait for next iteration
                await asyncio.sleep(beam_tuner.config['adjustment_interval'])
                
        except Exception as e:
            logger.error(f"❌ Error in monitoring loop: {e}")
            await asyncio.sleep(5)  # Short sleep on error

if __name__ == "__main__":
    import uvicorn
    
    # For development
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8080,
        log_level="info",
        reload=True
    )
