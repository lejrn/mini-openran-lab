"""
Beam Tuner Logic Module

Implements the core decision-making logic for the xApp.
Currently uses rule-based approach, designed to be extended with ML.

Key concepts:
- CQI (Channel Quality Indicator): 0-15 scale, higher is better
- MCS (Modulation and Coding Scheme): 0-28, affects data rate vs robustness
- Beamforming: Antenna pattern optimization (future enhancement)
"""

import logging
import time
from collections import deque
from typing import Dict, Any, Optional, List
import statistics

logger = logging.getLogger(__name__)

class BeamTunerLogic:
    """
    Core logic for beam tuning and MCS optimization.
    
    This class implements the intelligence of the xApp, making decisions
    based on observed radio conditions and sending optimization commands
    through the E2 interface.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.cqi_history = deque(maxlen=10)  # Last 10 CQI observations
        self.mcs_history = deque(maxlen=10)  # Last 10 MCS values
        self.last_adjustment_time = 0
        self.current_mcs = 16  # Start with moderate MCS
        
        # Thresholds for decision making
        self.cqi_threshold_low = config.get('cqi_threshold', 7.0)
        self.cqi_threshold_high = config.get('cqi_threshold', 7.0) + 3.0
        self.mcs_min = 1
        self.mcs_max = 28
        
        logger.info(f"🧠 Beam Tuner Logic initialized with CQI thresholds: {self.cqi_threshold_low}-{self.cqi_threshold_high}")
    
    def process_metrics(self, metrics: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process incoming metrics and decide if action is needed.
        
        Args:
            metrics: Dictionary containing CQI, MCS, and other radio metrics
            
        Returns:
            Action dictionary if adjustment needed, None otherwise
        """
        cqi = metrics.get('cqi', 0)
        current_mcs = metrics.get('mcs', self.current_mcs)
        
        # Update history
        self.cqi_history.append(cqi)
        self.mcs_history.append(current_mcs)
        self.current_mcs = current_mcs
        
        # Need minimum history to make decisions
        if len(self.cqi_history) < 3:
            logger.debug(f"📊 Collecting metrics... CQI history: {len(self.cqi_history)}/3")
            return None
        
        # Check if enough time has passed since last adjustment
        current_time = time.time()
        if current_time - self.last_adjustment_time < self.config['adjustment_interval']:
            return None
        
        # Calculate statistics
        median_cqi = statistics.median(self.cqi_history)
        cqi_trend = self._calculate_trend(list(self.cqi_history))
        
        logger.debug(f"📈 CQI stats - Current: {cqi}, Median: {median_cqi:.1f}, Trend: {cqi_trend:.2f}")
        
        # Decision logic
        action = self._make_decision(median_cqi, cqi_trend, current_mcs)
        
        if action:
            self.last_adjustment_time = current_time
            logger.info(f"🎯 Decision: {action}")
        
        return action
    
    def _make_decision(self, median_cqi: float, cqi_trend: float, current_mcs: int) -> Optional[Dict[str, Any]]:
        """
        Core decision-making logic.
        
        Decision rules:
        1. If CQI is consistently low and trending down: reduce MCS (more robust)
        2. If CQI is high and stable: increase MCS (higher throughput)
        3. If CQI is unstable: adjust conservatively
        """
        
        # Rule 1: Poor signal quality - prioritize reliability
        if median_cqi < self.cqi_threshold_low:
            if current_mcs > self.mcs_min + 2:
                return {
                    'type': 'mcs_adjustment',
                    'direction': 'down',
                    'current_mcs': current_mcs,
                    'target_mcs': max(current_mcs - 2, self.mcs_min),
                    'reason': f'Low CQI ({median_cqi:.1f}) - reducing MCS for reliability'
                }
        
        # Rule 2: Good signal quality - optimize for throughput
        elif median_cqi > self.cqi_threshold_high and cqi_trend >= 0:
            if current_mcs < self.mcs_max - 2:
                return {
                    'type': 'mcs_adjustment',
                    'direction': 'up',
                    'current_mcs': current_mcs,
                    'target_mcs': min(current_mcs + 2, self.mcs_max),
                    'reason': f'High CQI ({median_cqi:.1f}) - increasing MCS for throughput'
                }
        
        # Rule 3: Declining signal - preemptive adjustment
        elif cqi_trend < -0.5 and median_cqi < self.cqi_threshold_high:
            if current_mcs > self.mcs_min + 1:
                return {
                    'type': 'mcs_adjustment',
                    'direction': 'down',
                    'current_mcs': current_mcs,
                    'target_mcs': max(current_mcs - 1, self.mcs_min),
                    'reason': f'Declining CQI trend ({cqi_trend:.2f}) - preemptive MCS reduction'
                }
        
        return None
    
    def _calculate_trend(self, values: List[float]) -> float:
        """
        Calculate the trend (slope) of recent values.
        
        Returns:
            Positive value indicates increasing trend, negative indicates decreasing
        """
        if len(values) < 2:
            return 0.0
        
        # Simple linear regression slope
        n = len(values)
        x_mean = (n - 1) / 2  # Mean of indices 0, 1, 2, ..., n-1
        y_mean = sum(values) / n
        
        numerator = sum((i - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return 0.0
        
        return numerator / denominator
    
    async def adjust_mcs(self, direction: str, e2_client) -> bool:
        """
        Execute MCS adjustment.
        
        Args:
            direction: 'up' or 'down'
            e2_client: E2 client for sending commands
            
        Returns:
            True if adjustment was successful
        """
        if direction == 'up':
            new_mcs = min(self.current_mcs + 1, self.mcs_max)
        else:
            new_mcs = max(self.current_mcs - 1, self.mcs_min)
        
        if new_mcs == self.current_mcs:
            logger.warning(f"⚠️ MCS already at limit: {self.current_mcs}")
            return False
        
        try:
            success = await e2_client.send_mcs_adjustment(new_mcs)
            if success:
                logger.info(f"✅ MCS adjusted: {self.current_mcs} → {new_mcs}")
                self.current_mcs = new_mcs
                return True
            else:
                logger.error(f"❌ Failed to adjust MCS to {new_mcs}")
                return False
        except Exception as e:
            logger.error(f"❌ Exception during MCS adjustment: {e}")
            return False
    
    async def execute_action(self, action: Dict[str, Any], e2_client) -> bool:
        """
        Execute a decision action.
        
        Args:
            action: Action dictionary from process_metrics()
            e2_client: E2 client for sending commands
            
        Returns:
            True if action was executed successfully
        """
        if action['type'] == 'mcs_adjustment':
            return await self.adjust_mcs(action['direction'], e2_client)
        else:
            logger.warning(f"⚠️ Unknown action type: {action['type']}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current status and statistics.
        
        Returns:
            Status dictionary with current state and metrics
        """
        return {
            'current_mcs': self.current_mcs,
            'cqi_history': list(self.cqi_history),
            'mcs_history': list(self.mcs_history),
            'median_cqi': statistics.median(self.cqi_history) if self.cqi_history else 0,
            'cqi_trend': self._calculate_trend(list(self.cqi_history)) if len(self.cqi_history) > 1 else 0,
            'thresholds': {
                'cqi_low': self.cqi_threshold_low,
                'cqi_high': self.cqi_threshold_high
            },
            'last_adjustment': self.last_adjustment_time,
            'config': self.config
        }
