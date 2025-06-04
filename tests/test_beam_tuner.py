"""
Unit tests for Beam Tuner xApp

Tests the core logic without requiring actual RAN components.
Uses mocking for external dependencies like E2 client and metrics collection.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'xapps', 'beam_tuner'))

from logic import BeamTunerLogic
from e2_client import E2Client
from metrics import MetricsCollector


class TestBeamTunerLogic:
    """Test suite for BeamTunerLogic class."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.config = {
            'cqi_threshold': 7.0,
            'adjustment_interval': 30,
            'ric_host': 'localhost',
            'ric_port': 36421
        }
        self.logic = BeamTunerLogic(self.config)
    
    def test_initialization(self):
        """Test proper initialization of BeamTunerLogic."""
        assert self.logic.config == self.config
        assert self.logic.cqi_threshold_low == 7.0
        assert self.logic.cqi_threshold_high == 10.0
        assert len(self.logic.cqi_history) == 0
        assert self.logic.current_mcs == 16
    
    def test_process_metrics_insufficient_history(self):
        """Test that no action is taken with insufficient metric history."""
        metrics = {'cqi': 8.0, 'mcs': 16}
        
        # First call - insufficient history
        action = self.logic.process_metrics(metrics)
        assert action is None
        
        # Second call - still insufficient  
        action = self.logic.process_metrics(metrics)
        assert action is None
    
    def test_process_metrics_low_cqi_triggers_mcs_reduction(self):
        """Test that consistently low CQI triggers MCS reduction."""
        # Build up history with low CQI values
        low_cqi_metrics = [
            {'cqi': 5.0, 'mcs': 16},
            {'cqi': 4.5, 'mcs': 16}, 
            {'cqi': 5.5, 'mcs': 16}
        ]
        
        # Process metrics to build history
        for metrics in low_cqi_metrics:
            self.logic.process_metrics(metrics)
        
        # Trigger decision with time adjustment
        self.logic.last_adjustment_time = 0  # Force time condition
        action = self.logic.process_metrics({'cqi': 5.0, 'mcs': 16})
        
        assert action is not None
        assert action['type'] == 'mcs_adjustment'
        assert action['direction'] == 'down'
        assert action['target_mcs'] < 16
    
    def test_process_metrics_high_cqi_triggers_mcs_increase(self):
        """Test that high CQI triggers MCS increase."""
        # Build up history with high CQI values
        high_cqi_metrics = [
            {'cqi': 12.0, 'mcs': 16},
            {'cqi': 11.5, 'mcs': 16},
            {'cqi': 12.5, 'mcs': 16}
        ]
        
        for metrics in high_cqi_metrics:
            self.logic.process_metrics(metrics)
        
        # Trigger decision
        self.logic.last_adjustment_time = 0
        action = self.logic.process_metrics({'cqi': 12.0, 'mcs': 16})
        
        assert action is not None
        assert action['type'] == 'mcs_adjustment'
        assert action['direction'] == 'up'
        assert action['target_mcs'] > 16
    
    def test_calculate_trend_positive(self):
        """Test trend calculation for increasing values."""
        values = [5.0, 6.0, 7.0, 8.0]
        trend = self.logic._calculate_trend(values)
        assert trend > 0  # Should be positive for increasing trend
    
    def test_calculate_trend_negative(self):
        """Test trend calculation for decreasing values."""
        values = [10.0, 8.0, 6.0, 4.0]
        trend = self.logic._calculate_trend(values)
        assert trend < 0  # Should be negative for decreasing trend
    
    def test_mcs_boundaries(self):
        """Test that MCS adjustments respect min/max boundaries."""
        # Test minimum boundary
        self.logic.current_mcs = 1
        action = self.logic._make_decision(5.0, -1.0, 1)  # Low CQI, should want to decrease
        # Should not decrease further when already at minimum
        if action:
            assert action['target_mcs'] >= self.logic.mcs_min
        
        # Test maximum boundary  
        self.logic.current_mcs = 28
        action = self.logic._make_decision(12.0, 1.0, 28)  # High CQI, should want to increase
        # Should not increase further when already at maximum
        if action:
            assert action['target_mcs'] <= self.logic.mcs_max
    
    @pytest.mark.asyncio
    async def test_adjust_mcs_success(self):
        """Test successful MCS adjustment."""
        # Mock E2 client
        e2_client = AsyncMock()
        e2_client.send_mcs_adjustment.return_value = True
        
        # Test upward adjustment
        self.logic.current_mcs = 16
        result = await self.logic.adjust_mcs('up', e2_client)
        
        assert result is True
        assert self.logic.current_mcs == 17
        e2_client.send_mcs_adjustment.assert_called_once_with(17)
    
    @pytest.mark.asyncio
    async def test_adjust_mcs_failure(self):
        """Test MCS adjustment failure handling."""
        # Mock E2 client to fail
        e2_client = AsyncMock()
        e2_client.send_mcs_adjustment.return_value = False
        
        original_mcs = self.logic.current_mcs
        result = await self.logic.adjust_mcs('up', e2_client)
        
        assert result is False
        assert self.logic.current_mcs == original_mcs  # Should not change on failure
    
    def test_get_status(self):
        """Test status reporting functionality."""
        # Add some test data
        test_metrics = [
            {'cqi': 8.0, 'mcs': 16},
            {'cqi': 7.5, 'mcs': 16},
            {'cqi': 8.5, 'mcs': 16}
        ]
        
        for metrics in test_metrics:
            self.logic.process_metrics(metrics)
        
        status = self.logic.get_status()
        
        assert 'current_mcs' in status
        assert 'cqi_history' in status
        assert 'median_cqi' in status
        assert 'thresholds' in status
        assert status['current_mcs'] == 16
        assert len(status['cqi_history']) == 3


class TestE2Client:
    """Test suite for E2Client class."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.client = E2Client('localhost', 36421)
    
    def test_initialization(self):
        """Test E2Client initialization."""
        assert self.client.ric_host == 'localhost'
        assert self.client.ric_port == 36421
        assert self.client.base_url == 'http://localhost:36421'
        assert self.client.connected is False
    
    @pytest.mark.asyncio
    async def test_connection_success(self):
        """Test successful E2 connection."""
        with patch('aiohttp.ClientSession.get') as mock_get:
            # Mock successful health check
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_get.return_value.__aenter__.return_value = mock_response
            
            # Mock xApp registration
            with patch.object(self.client, '_register_xapp', new_callable=AsyncMock):
                result = await self.client.connect()
                
                assert result is True
                assert self.client.connected is True
    
    @pytest.mark.asyncio
    async def test_connection_failure(self):
        """Test E2 connection failure handling."""
        with patch('aiohttp.ClientSession.get') as mock_get:
            # Mock failed health check
            mock_response = AsyncMock()
            mock_response.status = 500
            mock_get.return_value.__aenter__.return_value = mock_response
            
            result = await self.client.connect()
            
            assert result is False
            assert self.client.connected is False
    
    @pytest.mark.asyncio
    async def test_send_mcs_adjustment(self):
        """Test sending MCS adjustment command."""
        self.client.connected = True
        self.client.session = AsyncMock()
        
        # Mock successful HTTP response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {'status': 'success'}
        self.client.session.post.return_value.__aenter__.return_value = mock_response
        
        # Mock is_connected check
        with patch.object(self.client, 'is_connected', return_value=True):
            result = await self.client.send_mcs_adjustment(20)
            
            assert result is True
            self.client.session.post.assert_called_once()


class TestMetricsCollector:
    """Test suite for MetricsCollector class."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.collector = MetricsCollector('localhost', 9091)
    
    def test_initialization(self):
        """Test MetricsCollector initialization."""
        assert self.collector.gnb_host == 'localhost'
        assert self.collector.gnb_port == 9091
        assert 'localhost:9091' in self.collector.gnb_metrics_url
    
    def test_parse_prometheus_metrics(self):
        """Test parsing of Prometheus metrics format."""
        metrics_text = """
# HELP cqi_value Current Channel Quality Indicator
# TYPE cqi_value gauge
cqi_value 8.5

# HELP mcs_setting Current Modulation and Coding Scheme  
# TYPE mcs_setting gauge
mcs_setting 16

# HELP throughput_bps Current throughput
# TYPE throughput_bps gauge
throughput_bps 50000000
"""
        
        parsed = self.collector._parse_prometheus_metrics(metrics_text)
        
        assert parsed['cqi'] == 8.5
        assert parsed['mcs'] == 16
        assert parsed['throughput_mbps'] == 50.0  # Converted from bps
        assert 'timestamp' in parsed
        assert parsed['source'] == 'gnb'
    
    def test_merge_metrics(self):
        """Test merging metrics from multiple sources."""
        gnb_metrics = {
            'cqi': 8.0,
            'mcs': 16,
            'source': 'gnb'
        }
        
        prometheus_metrics = {
            'throughput_mbps': 75.0,
            'bler': 0.01,
            'source': 'prometheus'
        }
        
        merged = self.collector._merge_metrics(gnb_metrics, prometheus_metrics)
        
        assert merged['cqi'] == 8.0  # From gNB (priority)
        assert merged['throughput_mbps'] == 75.0  # From Prometheus
        assert merged['source'] == 'gnb'  # gNB has priority
    
    @pytest.mark.asyncio
    async def test_get_latest_metrics_success(self):
        """Test successful metrics collection."""
        self.collector.session = AsyncMock()
        
        # Mock HTTP response with metrics
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text.return_value = "cqi_value 9.0\nmcs_setting 18\n"
        self.collector.session.get.return_value.__aenter__.return_value = mock_response
        
        metrics = await self.collector.get_latest_metrics()
        
        assert metrics is not None
        assert metrics['cqi'] == 9.0
        assert metrics['mcs'] == 18
    
    def test_get_metrics_summary(self):
        """Test metrics summary functionality."""
        summary = self.collector.get_metrics_summary()
        
        assert 'collector_status' in summary
        assert 'gnb_endpoint' in summary
        assert 'cached_metrics_available' in summary


if __name__ == '__main__':
    # Run tests with pytest
    pytest.main([__file__, '-v'])
