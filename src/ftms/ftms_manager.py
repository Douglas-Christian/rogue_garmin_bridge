#!/usr/bin/env python3
"""
FTMS Manager Module for Rogue to Garmin Bridge

This module handles the connection and data flow with FTMS-capable fitness equipment.
"""

import time
import asyncio
from bleak import BleakScanner, BleakClient
from bleak.exc import BleakError
import threading
import os
import sys
from typing import Dict, Any

# Add the project root to the path so we can use absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.utils.logging_config import get_component_logger
from src.ftms.ftms_connector import FTMSConnector
from src.ftms.ftms_simulator import FTMSDeviceSimulator

# Get component logger
logger = get_component_logger('ftms')

# FTMS Service UUID
FTMS_SERVICE_UUID = "00001826-0000-1000-8000-00805f9b34fb"

class FTMSDeviceManager:
    """
    Manager for FTMS devices (Fitness Machine Service) that handles:
    - Discovering FTMS-capable devices
    - Connecting to devices
    - Reading and writing characteristics
    - Processing incoming data
    """
    
    def __init__(self, workout_manager=None, use_simulator=False, device_type="bike"):
        """
        Initialize the FTMS device manager.
        
        Args:
            workout_manager: The workout manager instance
            use_simulator: Whether to use the simulator instead of real devices
            device_type: Type of device to simulate ("bike" or "rower"), only used with simulator
        """
        self.workout_manager = workout_manager
        self.use_simulator = use_simulator
        self.device_status = "disconnected"
        self.connected_device = None
        self.data_callbacks = []
        self.status_callbacks = []
        
        # Initialize the connector or simulator
        if use_simulator:
            self.connector = FTMSDeviceSimulator(device_type=device_type)
            logger.info("Using FTMSDeviceSimulator for testing.")
        else:
            self.connector = FTMSConnector()
            logger.info("Using FTMSConnector for real device.")
            
        # Register callbacks
        self.connector.register_data_callback(self._handle_data)
        self.connector.register_status_callback(self._handle_status)
    
    def register_data_callback(self, callback):
        """Register a callback for data events."""
        self.data_callbacks.append(callback)
        
    def register_status_callback(self, callback):
        """Register a callback for status events."""
        self.status_callbacks.append(callback)
    
    def _handle_data(self, data):
        """Handle data from the device and forward to callbacks."""
        # Store the latest data for status queries
        self.latest_data = data.copy() if data else None
        
        # Log the received data for debugging
        logger.debug(f"Received data from device: {data}")
        
        # Forward data to all registered callbacks
        for callback in self.data_callbacks:
            try:
                callback(data)
            except Exception as e:
                logger.error(f"Error in data callback: {str(e)}")
    
    def _handle_status(self, status, data):
        """Handle status updates from the device and forward to callbacks."""
        logger.debug(f"Handling status update: {status}")
        
        try:
            # For 'connected' status, extract the device information
            if status == "connected":
                # Extract the device object, which could be a SimulatedBLEDevice or a standard BLEDevice
                device = data
                
                # Check if it's a SimulatedBLEDevice (which has a to_dict method)
                if hasattr(device, 'to_dict') and callable(getattr(device, 'to_dict')):
                    self.connected_device = device.to_dict()
                    # Store the address separately for easier access
                    self.connected_device_address = self.connected_device.get("address")
                else:
                    # For a standard BLEDevice, create a dictionary with the required fields
                    self.connected_device = {
                        "address": device.address,
                        "name": device.name,
                        "rssi": getattr(device, 'rssi', None),
                        "metadata": getattr(device, 'metadata', {})
                    }
                    # Store the address separately for easier access
                    self.connected_device_address = device.address
                
                # Store the latest received data for use in status API
                self.latest_data = None
                
                self.device_status = "connected"
                logger.info(f"Connected to device: {self.connected_device.get('name', 'Unknown')}")
            
            # For 'disconnected' status
            elif status == "disconnected":
                self.device_status = "disconnected"
                self.connected_device = None
                self.connected_device_address = None
                self.latest_data = None
                logger.info("Disconnected from device")
            
            # For workout-related status updates
            elif status in ["workout_started", "workout_ended", "workout_paused", "workout_resumed"]:
                logger.info(f"Workout status: {status}")
                # Pass the status update to callbacks
            
            # Pass the status update to all registered callbacks
            for callback in self.status_callbacks:
                try:
                    callback(status, data)
                except Exception as e:
                    logger.error(f"Error in status callback: {str(e)}")
        except Exception as e:
            logger.error(f"Error handling status update: {str(e)}", exc_info=True)
    
    async def discover_devices(self):
        """Discover FTMS devices (asynchronous)."""
        try:
            logger.debug(f"Attempting to discover devices using connector: {type(self.connector).__name__}")
            if not hasattr(self.connector, 'discover_devices') or not asyncio.iscoroutinefunction(self.connector.discover_devices):
                logger.error(f"Connector {type(self.connector).__name__} does not have an async discover_devices method.")
                return {}

            # Directly await the connector's async method
            devices = await self.connector.discover_devices()
            return devices
        except Exception as e:
            logger.error(f"Error discovering devices: {str(e)}", exc_info=True)
            return {}
    
    async def connect(self, device_address: str) -> bool:
        """
        Connect to a specific FTMS device (asynchronous).
        
        Args:
            device_address: BLE address of the device to connect to
            
        Returns:
            True if connection successful, False otherwise
        """
        try:
            logger.debug(f"Attempting to connect to {device_address} using connector: {type(self.connector).__name__}")
            if not hasattr(self.connector, 'connect') or not asyncio.iscoroutinefunction(self.connector.connect):
                 logger.error(f"Connector {type(self.connector).__name__} does not have an async connect method.")
                 return False

            # Attempt connection with timeout
            connect_timeout = 30  # seconds
            try:
                # Directly await the connector's async method
                result = await asyncio.wait_for(self.connector.connect(device_address), timeout=connect_timeout)
                if not result:
                    logger.error(f"Connector failed to connect to device {device_address}")
                    return False
                return True # Connection successful
            except asyncio.TimeoutError:
                logger.error(f"Connection attempt to {device_address} timed out after {connect_timeout} seconds")
                return False
            except Exception as connect_exc:
                 logger.error(f"Error during connector.connect: {connect_exc}", exc_info=True)
                 return False
            
        except Exception as e:
            logger.error(f"Error in FTMSDeviceManager.connect: {str(e)}", exc_info=True)
            return False
    
    async def disconnect(self):
        """Disconnect from the current device (asynchronous)."""
        try:
            logger.debug(f"Attempting to disconnect using connector: {type(self.connector).__name__}")
            if not hasattr(self.connector, 'disconnect') or not asyncio.iscoroutinefunction(self.connector.disconnect):
                 logger.error(f"Connector {type(self.connector).__name__} does not have an async disconnect method.")
                 return False

            # Directly await the connector's async method
            result = await self.connector.disconnect()
            return result
        except Exception as e:
            logger.error(f"Error disconnecting from device: {str(e)}", exc_info=True)
            return False
    
    def notify_workout_start(self, workout_id, workout_type):
        """Notify the device that a workout has started."""
        try:
            logger.debug(f"Notifying workout start: id={workout_id}, type={workout_type}")
            
            # Safely check if connector exists
            if not hasattr(self, 'connector') or self.connector is None:
                logger.error("No connector available for workout start notification")
                return False
                
            if hasattr(self.connector, 'start_workout'):
                try:
                    self.connector.start_workout()
                    logger.info(f"Workout started: id={workout_id}, type={workout_type}")
                    return True
                except AttributeError as e:
                    logger.error(f"AttributeError calling start_workout: {str(e)}")
                    return False
                except Exception as e:
                    logger.error(f"Error in start_workout: {str(e)}", exc_info=True)
                    return False
            else:
                available_methods = [method for method in dir(self.connector) if not method.startswith('_')]
                logger.warning(f"No start_workout method found on connector of type {type(self.connector).__name__}. Available methods: {available_methods}")
                return False
        except Exception as e:
            logger.error(f"Critical error notifying workout start: {str(e)}", exc_info=True)
            return False
    
    def notify_workout_end(self, workout_id):
        """Notify the device that a workout has ended."""
        try:
            logger.debug(f"Notifying workout end: id={workout_id}")
            
            # Safely check if connector exists
            if not hasattr(self, 'connector') or self.connector is None:
                logger.error("No connector available for workout end notification")
                return False
                
            if hasattr(self.connector, 'end_workout'):
                try:
                    self.connector.end_workout()
                    logger.info(f"Workout ended: id={workout_id}")
                    return True
                except AttributeError as e:
                    logger.error(f"AttributeError calling end_workout: {str(e)}")
                    return False
                except Exception as e:
                    logger.error(f"Error in end_workout: {str(e)}", exc_info=True)
                    return False
            else:
                available_methods = [method for method in dir(self.connector) if not method.startswith('_')]
                logger.warning(f"No end_workout method found on connector of type {type(self.connector).__name__}. Available methods: {available_methods}")
                return False
        except Exception as e:
            logger.error(f"Critical error notifying workout end: {str(e)}", exc_info=True)
            return False
    
    def _handle_ftms_data(self, data: Dict[str, Any]) -> None:
        """
        Handle data received from the FTMS connector.
        Passes data to the workout manager if a workout is active.
        Also updates latest_data for status endpoint.
        
        Args:
            data: Dictionary of FTMS data
        """
        # --- Added Logging ---
        logger.info(f"[FTMSManager] Received data from connector: {data}")
        # --- End Added Logging ---
        
        # Update latest data regardless of workout state
        self.latest_data = data
        
        # Pass data to workout manager if a workout is active
        if self.workout_manager and self.workout_manager.active_workout_id:
            # --- Added Logging ---
            logger.info(f"[FTMSManager] Passing data to WorkoutManager (Active Workout ID: {self.workout_manager.active_workout_id})")
            # --- End Added Logging ---
            self.workout_manager.add_data_point(data)
        else:
            # --- Added Logging ---
            logger.info("[FTMSManager] No active workout, not passing data to WorkoutManager.")
            # --- End Added Logging ---
            pass # No active workout, just update latest_data
