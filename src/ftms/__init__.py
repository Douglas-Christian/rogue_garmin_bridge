#!/usr/bin/env python3
"""
FTMS Module Package Initialization

This module provides functionality for connecting to and interacting with
FTMS (Fitness Machine Service) compatible fitness equipment.
"""

from .ftms_connector import FTMSConnector
from .ftms_simulator import FTMSDeviceSimulator
from .ftms_manager import FTMSDeviceManager

__all__ = ['FTMSConnector', 'FTMSDeviceSimulator', 'FTMSDeviceManager']
