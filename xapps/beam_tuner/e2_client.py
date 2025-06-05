"""
E2 Interface Client

Handles communication with the O-RAN RIC through the E2 interface.
This is a simplified implementation for the lab environment.

In a real deployment, this would use the full E2AP protocol stack,
but for our demo we'll use a simplified HTTP/gRPC approach.
"""

import asyncio
import logging
import aiohttp
import json
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class E2Client:
    """
    Client for E2 interface communication with RIC platform.
    
    The E2 interface is the standardized interface between the RAN 
    and the Near-RT RIC in O-RAN architecture.
    """
    
    def __init__(self, ric_host: str, ric_port: int):
        self.ric_host = ric_host
        self.ric_port = ric_port
        self.base_url = f"http://{ric_host}:{ric_port}"
        self.session: Optional[aiohttp.ClientSession] = None
        self.connected = False
        
        logger.info(f"🔗 E2 Client initialized for RIC at {self.base_url}")
    
    async def connect(self) -> bool:
        """
        Establish connection to RIC platform.
        
        Returns:
            True if connection successful
        """
        try:
            if not self.session:
                self.session = aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=10)
                )
            
            # Test connection with health check
            async with self.session.get(f"{self.base_url}/health") as response:
                if response.status == 200:
                    self.connected = True
                    logger.info("✅ E2 connection established")
                    
                    # Register xApp with RIC
                    await self._register_xapp()
                    return True
                else:
                    logger.error(f"❌ RIC health check failed: {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Failed to connect to RIC: {e}")
            self.connected = False
            return False
    
    async def disconnect(self):
        """Close E2 connection."""
        if self.session:
            await self._unregister_xapp()
            await self.session.close()
            self.session = None
        
        self.connected = False
        logger.info("🔌 E2 connection closed")
    
    async def is_connected(self) -> bool:
        """Check if E2 connection is active."""
        if not self.connected or not self.session:
            return False
        
        try:
            async with self.session.get(f"{self.base_url}/health") as response:
                return response.status == 200
        except:
            self.connected = False
            return False
    
    async def send_mcs_adjustment(self, new_mcs: int) -> bool:
        """
        Send MCS adjustment command through E2 interface.
        
        Args:
            new_mcs: New MCS value to set (0-28)
            
        Returns:
            True if command was sent successfully
        """
        if not await self.is_connected():
            logger.error("❌ E2 client not connected")
            return False
        
        # E2 message structure for MCS adjustment
        e2_message = {
            "messageType": "RIC_CONTROL_REQUEST",
            "ranFunctionId": 1,  # Standard ID for radio resource management
            "ricRequestId": {
                "ricRequestorId": 1001,  # xApp identifier
                "ricInstanceId": 0
            },
            "ricControlHeader": {
                "controlType": "MCS_ADJUSTMENT",
                "targetNodeId": "gnb-001"  # Our gNB identifier
            },
            "ricControlMessage": {
                "parameters": {
                    "mcs": new_mcs,
                    "timestamp": asyncio.get_event_loop().time()
                }
            }
        }
        
        try:
            async with self.session.post(
                f"{self.base_url}/v1/controls",
                json=e2_message,
                headers={"Content-Type": "application/json"}
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"✅ E2 MCS adjustment sent: MCS={new_mcs}")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"❌ E2 command failed: {response.status} - {error_text}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Exception sending E2 command: {e}")
            return False
    
    async def send_beamforming_adjustment(self, beam_weights: Dict[str, float]) -> bool:
        """
        Send beamforming adjustment (future enhancement).
        
        Args:
            beam_weights: Antenna weight coefficients
            
        Returns:
            True if command was sent successfully
        """
        # Placeholder for future beamforming implementation
        logger.info(f"🔮 Beamforming adjustment (placeholder): {beam_weights}")
        return True
    
    async def subscribe_to_metrics(self, callback) -> bool:
        """
        Subscribe to real-time metrics from RAN nodes.
        
        Args:
            callback: Function to call when metrics are received
            
        Returns:
            True if subscription successful
        """
        if not await self.is_connected():
            logger.error("❌ E2 client not connected for subscription")
            return False
        
        subscription_message = {
            "messageType": "RIC_SUBSCRIPTION_REQUEST",
            "ranFunctionId": 2,  # Metrics reporting function
            "ricRequestId": {
                "ricRequestorId": 1001,
                "ricInstanceId": 1
            },
            "ricSubscriptionDetails": {
                "ricEventTriggerDefinition": {
                    "triggerType": "PERIODIC",
                    "intervalMs": 1000  # 1 second intervals
                },
                "ricActionDefinitions": [
                    {
                        "ricActionId": 1,
                        "ricActionType": "REPORT",
                        "ricActionDefinition": {
                            "parameters": ["CQI", "MCS", "THROUGHPUT", "BLER"]
                        }
                    }
                ]
            }
        }
        
        try:
            async with self.session.post(
                f"{self.base_url}/v1/subscriptions",
                json=subscription_message
            ) as response:
                
                if response.status == 201:
                    logger.info("✅ E2 metrics subscription active")
                    return True
                else:
                    logger.error(f"❌ E2 subscription failed: {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Exception creating E2 subscription: {e}")
            return False
    
    async def _register_xapp(self):
        """Register this xApp with the RIC platform."""
        registration = {
            "xappName": "beam-tuner",
            "xappVersion": "1.0.0",
            "xappDescription": "Beam tuning and MCS optimization xApp",
            "configMetadata": {
                "cqiThreshold": {"type": "float", "default": 7.0},
                "adjustmentInterval": {"type": "int", "default": 30}
            },
            "supportedRanFunctions": [1, 2],  # Control and reporting
            "endpoints": {
                "healthCheck": "/healthz",
                "metrics": "/metrics",
                "config": "/config"
            }
        }
        
        try:
            async with self.session.post(
                f"{self.base_url}/v1/xapps",
                json=registration
            ) as response:
                if response.status in [200, 201]:
                    logger.info("✅ xApp registered with RIC")
                else:
                    logger.warning(f"⚠️ xApp registration returned: {response.status}")
        except Exception as e:
            logger.warning(f"⚠️ xApp registration failed: {e}")
    
    async def _unregister_xapp(self):
        """Unregister this xApp from the RIC platform."""
        try:
            async with self.session.delete(
                f"{self.base_url}/v1/xapps/beam-tuner"
            ) as response:
                if response.status == 200:
                    logger.info("✅ xApp unregistered from RIC")
        except Exception as e:
            logger.warning(f"⚠️ xApp unregistration failed: {e}")
