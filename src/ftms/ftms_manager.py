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
        if self.use_simulator:
            logger.info(f"Using FTMS device simulator for {device_type}")
            self.connector = FTMSDeviceSimulator(device_type=device_type)
        else:
            logger.info("Using real FTMS devices")
            self.connector = FTMSConnector()
            
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
                else:
                    # For a standard BLEDevice, create a dictionary with the required fields
                    self.connected_device = {
                        "address": device.address,
                        "name": device.name,
                        "rssi": getattr(device, 'rssi', None),
                        "metadata": getattr(device, 'metadata', {})
                    }
                
                self.device_status = "connected"
                logger.info(f"Connected to device: {self.connected_device.get('name', 'Unknown')}")
            
            # For 'disconnected' status
            elif status == "disconnected":
                self.device_status = "disconnected"
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
    
    def start_scanning(self):
        """Start scanning for devices in a loop."""
        while True:
            try:
                # Use asyncio.run to handle the async discover_devices method
                self.discover_devices()
                time.sleep(5)  # Wait 5 seconds between scans
            except Exception as e:
                logger.error(f"Error in scanning loop: {str(e)}")
                time.sleep(10)  # Wait a bit longer after an error
    
    def discover_devices(self):
        """Discover FTMS devices."""
        try:
            logger.debug(f"Attempting to discover devices, connector type: {type(self.connector).__name__}")
            
            # Safely check if connector exists
            if not hasattr(self, 'connector') or self.connector is None:
                logger.error("No connector available for device discovery")
                return {}
                
            # Check explicitly for FTMSDeviceSimulator and handle differently
            if isinstance(self.connector, FTMSDeviceSimulator):
                try:
                    logger.debug("Using simulator's discover_devices method")
                    devices = self.connector.discover_devices()
                    return devices
                except Exception as e:
                    logger.error(f"Error calling simulator's discover_devices: {str(e)}", exc_info=True)
                    return {}
            # Standard approach for other connectors
            elif hasattr(self.connector, 'discover_devices_sync'):
                logger.debug("Using synchronous discover_devices_sync method")
                try:
                    devices = self.connector.discover_devices_sync()
                except AttributeError as e:
                    logger.error(f"AttributeError calling discover_devices_sync: {str(e)}")
                    return {}
                except Exception as e:
                    logger.error(f"Error in discover_devices_sync: {str(e)}", exc_info=True)
                    return {}
            elif hasattr(self.connector, 'discover_devices'):
                logger.debug("Using discover_devices method")
                try:
                    # Check if it's already a synchronous method
                    import inspect
                    if not inspect.iscoroutinefunction(self.connector.discover_devices):
                        logger.debug("discover_devices is synchronous, calling directly")
                        devices = self.connector.discover_devices()
                    else:
                        logger.debug("discover_devices is asynchronous, using event loop")
                        # Use asyncio.run for the async method
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        devices = loop.run_until_complete(self.connector.discover_devices())
                        loop.close()
                except AttributeError as e:
                    logger.error(f"AttributeError calling discover_devices: {str(e)}")
                    return {}
                except Exception as e:
                    logger.error(f"Error in discover_devices: {str(e)}", exc_info=True)
                    return {}
            else:
                available_methods = [method for method in dir(self.connector) if not method.startswith('_')]
                logger.error(f"No discover_devices method found on connector of type {type(self.connector).__name__}. Available methods: {available_methods}")
                return {}
                
            return devices
        except Exception as e:
            logger.error(f"Critical error discovering devices: {str(e)}", exc_info=True)
            import traceback
            traceback.print_exc()
            return {}
    
    async def connect_to_device(self, device_address: str) -> bool:
        """
        Connect to a specific FTMS device.
        
        Args:
            device_address: BLE address of the device to connect to
            
        Returns:
            True if connection successful, False otherwise
        """
        try:
            if self._workout_in_progress:
                logger.warning("Cannot connect to a device while a workout is in progress")
                return False
                
            # Attempt connection with timeout
            connect_timeout = 15  # seconds
            try:
                connection_task = self.connector.connect(device_address)
                result = await asyncio.wait_for(connection_task, timeout=connect_timeout)
                if not result:
                    logger.error(f"Failed to connect to device {device_address}")
                    return False
            except asyncio.TimeoutError:
                logger.error(f"Connection attempt timed out after {connect_timeout} seconds")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Error connecting to device: {str(e)}")
            return False
    
    def disconnect(self):
        """Disconnect from the current device."""
        try:
            logger.debug("Attempting to disconnect from device")
            
            # Safely check if connector exists
            if not hasattr(self, 'connector') or self.connector is None:
                logger.error("No connector available for device disconnection")
                return False
                
            # Explicitly check if the sync or async version exists
            if hasattr(self.connector, 'disconnect_sync'):
                logger.debug("Using synchronous disconnect_sync method")
                try:
                    return self.connector.disconnect_sync()
                except AttributeError as e:
                    logger.error(f"AttributeError calling disconnect_sync: {str(e)}")
                    return False
                except Exception as e:
                    logger.error(f"Error in disconnect_sync: {str(e)}", exc_info=True)
                    return False
            elif hasattr(self.connector, 'disconnect'):
                logger.debug("Using disconnect method")
                try:
                    # Check if it's already a synchronous method
                    import inspect
                    if not inspect.iscoroutinefunction(self.connector.disconnect):
                        logger.debug("disconnect is synchronous, calling directly")
                        return self.connector.disconnect()
                    else:
                        logger.debug("disconnect is asynchronous, using event loop")
                        # Use asyncio.run for the async method
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        result = loop.run_until_complete(self.connector.disconnect())
                        loop.close()
                        return result
                except AttributeError as e:
                    logger.error(f"AttributeError calling disconnect: {str(e)}")
                    return False
                except Exception as e:
                    logger.error(f"Error in disconnect: {str(e)}", exc_info=True)
                    return False
            else:
                available_methods = [method for method in dir(self.connector) if not method.startswith('_')]
                logger.error(f"No disconnect method found on connector of type {type(self.connector).__name__}. Available methods: {available_methods}")
                return False
        except Exception as e:
            logger.error(f"Critical error disconnecting from device: {str(e)}", exc_info=True)
            import traceback
            traceback.print_exc()
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
