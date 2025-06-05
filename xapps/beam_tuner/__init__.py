"""
Beam Tuner xApp Package

This package implements a Near-RT RIC xApp for real-time optimization
of radio access network parameters, specifically focusing on:

- Channel Quality Indicator (CQI) monitoring
- Modulation and Coding Scheme (MCS) optimization
- Future: Beamforming weight adjustment

The xApp demonstrates the integration of telecom domain knowledge
with modern cloud-native DevOps practices.
"""

__version__ = "1.0.0"
__author__ = "Mini-OpenRAN Lab Team"
__license__ = "Apache 2.0"

# Make key classes easily importable
from .app import app
from .logic import BeamTunerLogic
from .e2_client import E2Client
from .metrics import MetricsCollector

__all__ = [
    "app",
    "BeamTunerLogic", 
    "E2Client",
    "MetricsCollector"
]
