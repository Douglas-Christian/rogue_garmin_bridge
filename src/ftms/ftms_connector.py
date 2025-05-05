#!/usr/bin/env python3
"""
FTMS Connector Module for Rogue to Garmin Bridge

This module handles Bluetooth Low Energy (BLE) connections to Rogue Echo Bike and Rower
equipment using the FTMS (Fitness Machine Service) standard.
"""

import asyncio
import sys
import os
from typing import Dict, List, Optional, Callable, Any
import datetime
import time
import struct
import binascii

import bleak
from bleak import BleakScanner, BleakClient
from bleak.backends.device import BLEDevice
from pycycling.fitness_machine_service import FitnessMachineService

# Add the project root to the path so we can use absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.utils.logging_config import get_component_logger

# Get component logger
logger = get_component_logger('ftms_connector')

# FTMS UUIDs
FTMS_SERVICE_UUID = "00001826-0000-1000-8000-00805f9b34fb"
FTMS_INDOOR_BIKE_DATA_UUID = "00002ad2-0000-1000-8000-00805f9b34fb" # Indoor Bike Data UUID
FTMS_ROWER_DATA_UUID = "00002ad1-0000-1000-8000-00805f9b34fb" # Rower Data UUID
FTMS_FITNESS_MACHINE_STATUS_UUID = "00002ada-0000-1000-8000-00805f9b34fb" # Machine Status UUID
FTMS_CONTROL_POINT_UUID = "00002ad9-0000-1000-8000-00805f9b34fb" # Control Point UUID
ROGUE_MANUFACTURER_NAME = "Rogue"  # Adjust if needed based on actual device advertising

class FTMSConnector:
    """
    Class for handling connections to FTMS-compatible fitness equipment.
    """
    
    def __init__(self):
        """Initialize the FTMS connector."""
        self.devices: Dict[str, BLEDevice] = {}
        self.client: Optional[BleakClient] = None
        self.ftms: Optional[FitnessMachineService] = None
        self.connected_device: Optional[BLEDevice] = None
        self.data_callbacks: List[Callable[[Dict[str, Any]], None]] = []
        self.status_callbacks: List[Callable[[str, Any], None]] = []
        # Error tracking
        self.connection_errors = []
        self.last_error_time = None
        self.consecutive_errors = 0
        self.max_consecutive_errors = 5
        
    async def discover_devices(self, timeout: int = 5) -> Dict[str, BLEDevice]:
        """
        Discover FTMS-compatible devices.
        
        Args:
            timeout: Scan timeout in seconds
            
        Returns:
            Dictionary of discovered devices with address as key
        """
        logger.info(f"Scanning for FTMS devices for {timeout} seconds...")
        
        # Clear previous devices
        self.devices = {}
        
        try:
            # Define a detection callback that filters for FTMS devices
            def detection_callback(device: BLEDevice, advertisement_data):
                try:
                    if not device or not hasattr(device, 'address'):
                        logger.warning("Received invalid device in detection callback")
                        return
                        
                    service_uuids = advertisement_data.service_uuids if hasattr(advertisement_data, 'service_uuids') else []
                    
                    # Check if device name is available
                    device_name = device.name if device.name else "Unknown"
                    
                    if FTMS_SERVICE_UUID.lower() in [str(uuid).lower() for uuid in service_uuids]:
                        logger.info(f"Found FTMS device: {device_name} ({device.address})")
                        self.devices[device.address] = device
                        self._notify_status("device_found", device)
                    elif device_name and ROGUE_MANUFACTURER_NAME.lower() in device_name.lower():
                        # Also include devices with Rogue in the name even if they don't advertise FTMS
                        logger.info(f"Found potential Rogue device: {device_name} ({device.address})")
                        self.devices[device.address] = device
                        self._notify_status("device_found", device)
                except Exception as e:
                    logger.error(f"Error in detection callback: {str(e)}")
                    self._track_connection_error("discovery_callback", str(e))
            
            # Start scanning with the callback
            scanner = BleakScanner(detection_callback=detection_callback)
            await scanner.start()
            await asyncio.sleep(timeout)
            await scanner.stop()
            
            logger.info(f"Discovered {len(self.devices)} FTMS devices")
            return self.devices
            
        except asyncio.CancelledError:
            logger.warning("Device discovery cancelled")
            raise
        except Exception as e:
            logger.error(f"Error during device discovery: {str(e)}")
            self._track_connection_error("discovery", str(e))
            self._notify_status("discovery_error", str(e))
            # Return empty dict on failure
            return {}
    
    async def connect(self, device_address: str, max_retries: int = 3) -> bool:
        """
        Connect to a specific FTMS device.
        
        Args:
            device_address: BLE address of the device to connect to
            max_retries: Maximum number of connection attempts
            
        Returns:
            True if connection successful, False otherwise
        """
        if not device_address:
            logger.error("No device address provided")
            self._notify_status("connection_error", "No device address provided")
            return False
            
        # If device not in discovered list, try to rediscover it
        if device_address not in self.devices:
            logger.warning(f"Device {device_address} not found in discovered devices, attempting rediscovery")
            try:
                await self.discover_devices(timeout=3)
                if device_address not in self.devices:
                    logger.error(f"Device {device_address} not found after rediscovery attempt")
                    self._notify_status("connection_error", "Device not found")
                    return False
            except Exception as e:
                logger.error(f"Error during device rediscovery: {str(e)}")
                self._notify_status("connection_error", "Device not found and rediscovery failed")
                return False
        
        device = self.devices[device_address]
        logger.info(f"Connecting to {device.name} ({device.address})...")
        self._notify_status("connecting", device)
        
        retry_count = 0
        while retry_count < max_retries:
            try:
                # Disconnect if already connected
                if self.client and self.client.is_connected:
                    await self.disconnect()
                
                # Connect to the device using its address string
                self.client = BleakClient(device.address)
                
                # Set a connection timeout
                connect_timeout = 10  # seconds
                try:
                    await asyncio.wait_for(self.client.connect(), timeout=connect_timeout)
                except asyncio.TimeoutError:
                    retry_count += 1
                    logger.warning(f"Connection timed out after {connect_timeout} seconds (Attempt {retry_count}/{max_retries})")
                    
                    if retry_count < max_retries:
                        # Wait before retrying
                        await asyncio.sleep(2)
                        continue
                    else:
                        logger.error("Connection timed out after maximum retries")
                        self._notify_status("connection_error", "Connection timed out")
                        self.client = None
                        return False
                
                if not self.client.is_connected:
                    retry_count += 1
                    logger.warning(f"Connection failed (Attempt {retry_count}/{max_retries})")
                    
                    if retry_count < max_retries:
                        # Wait before retrying
                        await asyncio.sleep(2)
                        continue
                    else:
                        logger.error("Connection failed after maximum retries")
                        self._notify_status("connection_error", "Connection failed")
                        self.client = None
                        return False
                
                # Initialize FTMS service
                try:
                    self.ftms = FitnessMachineService(self.client)
                    
                    logger.info("Setting FTMS data handlers...")
                    
                    # First discover services to identify device type
                    device_info = await self.discover_services()
                    
                    # Try to determine if this is a rower based on available characteristics
                    is_rower = False
                    if device_info:
                        # Look for the FTMS service
                        ftms_service = next((s for s in device_info["services"] 
                                            if s["uuid"].lower() == FTMS_SERVICE_UUID.lower()), None)
                        if ftms_service:
                            # Check if it has the rower characteristic
                            rower_char = next((c for c in ftms_service["characteristics"]
                                            if c["uuid"].lower() == FTMS_ROWER_DATA_UUID.lower()), None)
                            bike_char = next((c for c in ftms_service["characteristics"]
                                            if c["uuid"].lower() == FTMS_INDOOR_BIKE_DATA_UUID.lower()), None)
                            
                            if rower_char:
                                logger.info("Device identified as a rower based on available characteristics")
                                is_rower = True
                            elif bike_char:
                                logger.info("Device identified as a bike based on available characteristics")
                                is_rower = False
                            else:
                                # Fallback to name-based detection if no specific characteristic is found
                                device_name = self.connected_device.name.lower() if self.connected_device and self.connected_device.name else ""
                                is_rower = "rower" in device_name
                    
                    # Set the connected device so it's available for notification enabling
                    self.connected_device = device
                    
                    # Enable appropriate notifications based on device type
                    try:
                        logger.info("Attempting to enable FTMS notifications...")
                        
                        if is_rower:
                            logger.info("Setting up as a rowing machine...")
                            # Try to enable rower data notifications first
                            try:
                                await self.ftms.enable_rower_data_notify()
                                logger.info("Rower data notifications enabled.")
                            except AttributeError:
                                logger.warning("AttributeError enabling rower notifications. Trying generic approach.")
                                try:
                                    # Fallback for rower data using direct BLE notifications
                                    if device_info:
                                        # Find the FTMS service and rower characteristic in our discovered services
                                        ftms_service = next((s for s in device_info["services"] 
                                                            if s["uuid"].lower() == FTMS_SERVICE_UUID.lower()), None)
                                        if ftms_service:
                                            rower_char = next((c for c in ftms_service["characteristics"]
                                                            if c["uuid"].lower() == FTMS_ROWER_DATA_UUID.lower()), None)
                                            if rower_char and "notify" in rower_char["properties"]:
                                                await self.client.start_notify(rower_char["uuid"], self._handle_raw_notification)
                                                logger.info(f"Started notifications for rower data: {rower_char['uuid']}")
                                            else:
                                                logger.warning("Rower data characteristic not found or doesn't support notifications")
                                    else:
                                        # Try the standard UUID if we don't have discovery info
                                        await self.client.start_notify(FTMS_ROWER_DATA_UUID, self._handle_raw_notification)
                                        logger.info("Fallback notification attempt initiated for Rower Data.")
                                except Exception as fallback_exc:
                                    logger.error(f"Fallback rower notification attempt failed: {fallback_exc}")
                        else:
                            logger.info("Setting up as a cycling machine...")
                            # Enable notifications for indoor bike data
                            try:
                                await self.ftms.enable_indoor_bike_data_notify()
                                logger.info("Indoor bike data notifications enabled.")
                            except AttributeError:
                                logger.warning("AttributeError enabling bike notifications. Trying generic approach.")
                                try:
                                    # Fallback for indoor bike data using direct BLE notifications
                                    if device_info:
                                        # Find the FTMS service and bike characteristic in our discovered services
                                        ftms_service = next((s for s in device_info["services"] 
                                                        if s["uuid"].lower() == FTMS_SERVICE_UUID.lower()), None)
                                        if ftms_service:
                                            bike_char = next((c for c in ftms_service["characteristics"]
                                                            if c["uuid"].lower() == FTMS_INDOOR_BIKE_DATA_UUID.lower()), None)
                                            if bike_char and "notify" in bike_char["properties"]:
                                                await self.client.start_notify(bike_char["uuid"], self._handle_raw_notification)
                                                logger.info(f"Started notifications for bike data: {bike_char['uuid']}")
                                            else:
                                                logger.warning("Bike data characteristic not found or doesn't support notifications")
                                    else:
                                        # Try the standard UUID if we don't have discovery info
                                        await self.client.start_notify(FTMS_INDOOR_BIKE_DATA_UUID, self._handle_raw_notification)
                                        logger.info("Fallback notification attempt initiated for Indoor Bike Data.")
                                except Exception as fallback_exc:
                                    logger.error(f"Fallback bike notification attempt failed: {fallback_exc}")
                        
                        # Try to find and enable the status characteristic
                        try:
                            # First try using the pycycling library
                            await self.ftms.enable_fitness_machine_status_notify()
                            logger.info("Fitness machine status notifications enabled through pycycling.")
                        except AttributeError:
                            logger.warning("AttributeError enabling status notifications. Trying generic approach.")
                            try:
                                # Check if we have discovered the status characteristic
                                if device_info:
                                    ftms_service = next((s for s in device_info["services"] 
                                                        if s["uuid"].lower() == FTMS_SERVICE_UUID.lower()), None)
                                    if ftms_service:
                                        status_char = next((c for c in ftms_service["characteristics"]
                                                        if c["uuid"].lower() == FTMS_FITNESS_MACHINE_STATUS_UUID.lower()), None)
                                        if status_char and "notify" in status_char["properties"]:
                                            await self.client.start_notify(status_char["uuid"], self._handle_raw_notification)
                                            logger.info(f"Started notifications for machine status: {status_char['uuid']}")
                                        else:
                                            logger.warning("Machine status characteristic not found or doesn't support notifications")
                                else:
                                    # Try the standard UUID if we don't have discovery info
                                    await self.client.start_notify(FTMS_FITNESS_MACHINE_STATUS_UUID, self._handle_raw_notification)
                                    logger.info("Fallback notification attempt initiated for Machine Status.")
                            except Exception as status_exc:
                                logger.warning(f"Could not enable machine status notifications: {status_exc}")
                        
                        logger.info("FTMS notifications setup completed.")
                    except Exception as notify_exc:
                        logger.warning(f"Could not explicitly enable FTMS notifications: {notify_exc}. Data might still be received.")

                    # Set up data handlers for bike, rower, and status
                    self.ftms.set_indoor_bike_data_handler(self._handle_indoor_bike_data)
                    
                    # Set up rower data handler if available
                    try:
                        self.ftms.set_rower_data_handler(self._handle_rower_data)
                        logger.info("Rower data handler set successfully.")
                    except AttributeError:
                        logger.warning("Could not set rower data handler - may not be supported by pycycling library.")
                    
                    self.ftms.set_fitness_machine_status_handler(self._handle_fitness_machine_status)
                    
                    logger.info("FTMS data handlers set.")

                    # Add disconnect handler to detect unexpected disconnections
                    self.client.set_disconnected_callback(self._handle_disconnection)
                except Exception as e:
                    logger.error(f"Error initializing FTMS service or enabling notifications: {str(e)}")
                    self._notify_status("connection_error", f"FTMS service initialization/notification failed: {str(e)}")
                    await self.client.disconnect()
                    self.client = None
                    return False
                
                self.connected_device = device
                logger.info(f"Connected to {device.name} ({device.address})")
                self._notify_status("connected", device)
                return True
                
            except asyncio.CancelledError:
                logger.warning("Connection cancelled")
                self._notify_status("connection_error", "Connection cancelled")
                if self.client:
                    try:
                        await self.client.disconnect()
                    except:
                        pass
                    self.client = None
                raise
            except bleak.exc.BleakError as e:
                retry_count += 1
                logger.warning(f"BLE error connecting to device: {str(e)} (Attempt {retry_count}/{max_retries})")
                
                if retry_count < max_retries:
                    logger.info(f"Retrying connection in 2 seconds...")
                    await asyncio.sleep(2)
                    continue
                else:
                    logger.error(f"BLE error connecting to device after maximum retries: {str(e)}")
                    self._notify_status("connection_error", f"BLE error: {str(e)}")
                    self.client = None
                    return False
            except Exception as e:
                retry_count += 1
                logger.warning(f"Error connecting to device: {str(e)} (Attempt {retry_count}/{max_retries})")
                
                if retry_count < max_retries:
                    logger.info(f"Retrying connection in 2 seconds...")
                    await asyncio.sleep(2)
                    continue
                else:
                    logger.error(f"Error connecting to device after maximum retries: {str(e)}")
                    self._notify_status("connection_error", str(e))
                    self.client = None
                    return False
    
    async def disconnect(self) -> bool:
        """
        Disconnect from the currently connected FTMS device.
        
        Returns:
            True if disconnect successful or already disconnected, False if disconnect failed
        """
        if not self.client:
            logger.info("No active connection to disconnect")
            return True
            
        try:
            if self.client.is_connected:
                logger.info(f"Disconnecting from {self.connected_device.name if self.connected_device else 'device'}...")
                self._notify_status("disconnecting", self.connected_device)
                
                # Clean up the notifications
                if self.ftms:
                    try:
                        await self.ftms.disable_notifications()
                    except Exception as e:
                        logger.warning(f"Error disabling notifications: {str(e)}")
                        # Continue with disconnect even if this fails
                
                # Attempt to disconnect
                try:
                    await asyncio.wait_for(self.client.disconnect(), timeout=5.0)
                except asyncio.TimeoutError:
                    logger.warning("Disconnect timed out after 5 seconds, forcing cleanup")
                    # Force cleanup even if timeout occurs
                
                logger.info("Disconnected from device")
            else:
                logger.info("Client already disconnected")
        except bleak.exc.BleakError as e:
            logger.error(f"BLE error during disconnect: {str(e)}")
            # Continue with cleanup despite error
        except Exception as e:
            logger.error(f"Error during disconnect: {str(e)}")
            # Continue with cleanup despite error
        finally:
            # Always clean up resources
            self.client = None
            self.ftms = None
            if self.connected_device:
                self._notify_status("disconnected", self.connected_device)
                self.connected_device = None
        
        return True
    
    async def reset_connection(self) -> bool:
        """
        Reset the current connection and attempt to reconnect to the same device.
        
        This method is useful when the connection is in a bad state and needs to be
        completely reset and reestablished.
        
        Returns:
            True if reset and reconnection successful, False otherwise
        """
        if not self.connected_device:
            logger.warning("No device currently connected to reset")
            return False
            
        device_address = self.connected_device.address
        device_name = self.connected_device.name
        
        logger.info(f"Resetting connection to {device_name} ({device_address})")
        self._notify_status("resetting_connection", self.connected_device)
        
        # Force disconnect
        await self.disconnect()
        
        # Wait a moment before reconnecting
        await asyncio.sleep(2)
        
        # Attempt to reconnect
        try:
            connected = await self.connect(device_address)
            if connected:
                logger.info(f"Successfully reset connection to {device_name}")
                self._notify_status("connection_reset", self.connected_device)
                return True
            else:
                logger.error(f"Failed to reconnect after reset to {device_name}")
                self._notify_status("reset_failed", {"address": device_address, "name": device_name})
                return False
        except Exception as e:
            logger.error(f"Error during connection reset: {str(e)}")
            self._notify_status("reset_failed", {"address": device_address, "name": device_name, "error": str(e)})
            return False
    
    async def discover_services(self):
        """
        Discover all GATT services and characteristics available on the connected device.
        This is an exploratory function to help identify what features the device actually supports.
        
        Returns:
            A dictionary of services and characteristics
        """
        if not self.client or not self.client.is_connected:
            logger.error("Cannot discover services: No active connection")
            return None
            
        try:
            logger.info(f"Discovering services for {self.connected_device.name if self.connected_device else 'device'}...")
            services = await self.client.get_services()
            
            # Build a report of all services and characteristics
            device_info = {
                "device_name": self.connected_device.name if self.connected_device else "Unknown",
                "device_address": self.connected_device.address if self.connected_device else "Unknown",
                "services": []
            }
            
            for service in services:
                service_info = {
                    "uuid": str(service.uuid),
                    "description": "",
                    "characteristics": []
                }
                
                # Add a description for known services
                if str(service.uuid).lower() == FTMS_SERVICE_UUID.lower():
                    service_info["description"] = "Fitness Machine Service (FTMS)"
                
                # Gather characteristic information
                for char in service.characteristics:
                    char_info = {
                        "uuid": str(char.uuid),
                        "description": "",
                        "properties": []
                    }
                    
                    # Populate properties
                    if char.properties:
                        for prop_name, prop_value in char.properties.items():
                            if prop_value:
                                char_info["properties"].append(prop_name)
                    
                    # Add descriptions for known characteristics
                    if str(char.uuid).lower() == FTMS_INDOOR_BIKE_DATA_UUID.lower():
                        char_info["description"] = "Indoor Bike Data"
                    elif str(char.uuid).lower() == FTMS_ROWER_DATA_UUID.lower():
                        char_info["description"] = "Rower Data"
                    elif str(char.uuid).lower() == FTMS_FITNESS_MACHINE_STATUS_UUID.lower():
                        char_info["description"] = "Fitness Machine Status"
                    elif str(char.uuid).lower() == FTMS_CONTROL_POINT_UUID.lower():
                        char_info["description"] = "Fitness Machine Control Point"
                    
                    service_info["characteristics"].append(char_info)
                
                device_info["services"].append(service_info)
            
            # Log and return the discovered information
            logger.info(f"Discovered {len(device_info['services'])} services with "
                       f"{sum(len(s['characteristics']) for s in device_info['services'])} characteristics")
            
            # Specific check for FTMS service
            ftms_service = next((s for s in device_info["services"] 
                                 if s["uuid"].lower() == FTMS_SERVICE_UUID.lower()), None)
            if ftms_service:
                logger.info(f"Found FTMS service with {len(ftms_service['characteristics'])} characteristics")
                for char in ftms_service["characteristics"]:
                    logger.info(f"FTMS characteristic: {char['uuid']} - {char['description']} - {', '.join(char['properties'])}")
            else:
                logger.warning("FTMS service not found!")
            
            return device_info
            
        except Exception as e:
            logger.error(f"Error discovering services: {str(e)}")
            return None
    
    def register_data_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        Register a callback function to receive FTMS data.
        
        Args:
            callback: Function that will be called with FTMS data
        """
        self.data_callbacks.append(callback)
    
    def register_status_callback(self, callback: Callable[[str, Any], None]) -> None:
        """
        Register a callback function to receive status updates.
        
        Args:
            callback: Function that will be called with status updates
        """
        self.status_callbacks.append(callback)
    
    def _handle_indoor_bike_data(self, data):
        """Handle indoor bike data notifications."""
        try:
            # Log the raw data object for inspection
            logger.info(f"[FTMSConnector] Received raw indoor bike data: {data}")

            # Check if data is None or not the expected type (optional but good practice)
            if data is None:
                logger.warning("Received None for indoor bike data.")
                return

            # Access data using attributes, provide defaults for optional fields
            processed_data = {
                'type': 'bike',
                'instant_speed': getattr(data, 'instant_speed', None),
                'average_speed': getattr(data, 'average_speed', None),
                'instant_cadence': getattr(data, 'instant_cadence', None),
                'average_cadence': getattr(data, 'average_cadence', None),
                'total_distance': getattr(data, 'total_distance', None),
                'resistance_level': getattr(data, 'resistance_level', None),
                'instant_power': getattr(data, 'instant_power', None),
                'average_power': getattr(data, 'average_power', None),
                'total_energy': getattr(data, 'total_energy', None),
                'energy_per_hour': getattr(data, 'energy_per_hour', None),
                'energy_per_minute': getattr(data, 'energy_per_minute', None),
                'heart_rate': getattr(data, 'heart_rate', None),
                'metabolic_equivalent': getattr(data, 'metabolic_equivalent', None),
                'elapsed_time': getattr(data, 'elapsed_time', None),
                'remaining_time': getattr(data, 'remaining_time', None),
                # Add a timestamp using the current time
                'timestamp': time.time() # Use current time as fallback/primary timestamp
            }

            # Log the processed data
            logger.debug(f"Processed indoor bike data: {processed_data}")

            # Pass data to registered callbacks
            for callback in self.data_callbacks:
                callback(processed_data)

        except AttributeError as ae:
            logger.error(f"AttributeError processing indoor bike data: {ae}. Data object: {data}", exc_info=True)
        except Exception as e:
            logger.error(f"Error processing indoor bike data: {e}. Data object: {data}", exc_info=True)
    
    def _handle_rower_data(self, data):
        """Handle rower data notifications."""
        try:
            # Log the raw data object for inspection
            logger.info(f"[FTMSConnector] Received raw rower data: {data}")

            # Check if data is None
            if data is None:
                logger.warning("Received None for rower data.")
                return

            # Access data using attributes, provide defaults for optional fields
            processed_data = {
                'type': 'rower',
                'instant_stroke_rate': getattr(data, 'stroke_rate', None),
                'average_stroke_rate': getattr(data, 'average_stroke_rate', None),
                'total_distance': getattr(data, 'total_distance', None),
                'instant_pace': getattr(data, 'instantaneous_pace', None),
                'average_pace': getattr(data, 'average_pace', None),
                'instant_power': getattr(data, 'instantaneous_power', None),
                'average_power': getattr(data, 'average_power', None),
                'resistance_level': getattr(data, 'resistance_level', None),
                'total_energy': getattr(data, 'total_energy', None),
                'energy_per_hour': getattr(data, 'energy_per_hour', None),
                'energy_per_minute': getattr(data, 'energy_per_minute', None),
                'heart_rate': getattr(data, 'heart_rate', None),
                'metabolic_equivalent': getattr(data, 'metabolic_equivalent', None),
                'elapsed_time': getattr(data, 'elapsed_time', None),
                'remaining_time': getattr(data, 'remaining_time', None),
                'total_strokes': getattr(data, 'stroke_count', None),
                # Add a timestamp using the current time
                'timestamp': time.time()
            }

            # Log the processed data
            logger.debug(f"Processed rower data: {processed_data}")

            # Pass data to registered callbacks
            for callback in self.data_callbacks:
                callback(processed_data)

        except AttributeError as ae:
            logger.error(f"AttributeError processing rower data: {ae}. Data object: {data}", exc_info=True)
        except Exception as e:
            logger.error(f"Error processing rower data: {e}. Data object: {data}", exc_info=True)
    
    def _handle_fitness_machine_status(self, data: Dict[str, Any]) -> None:
        """
        Handle fitness machine status updates.
        
        Args:
            data: Dictionary of status data
        """
        try:
            if not data:
                logger.warning("Received empty fitness machine status")
                return
                
            logger.info(f"Received fitness machine status: {data}")
            
            # Map FTMS status codes to appropriate workout events
            # Reference FTMS specification: https://www.bluetooth.com/specifications/specs/fitness-machine-service-1-0/
            if 'op_code' in data:
                op_code = data['op_code']
                
                # Map relevant FTMS status codes to workout events
                status_mapping = {
                    # Common codes
                    1: "reset",              # Reset
                    2: "workout_stopped",    # Stopped by User
                    3: "workout_paused",     # Paused by User
                    4: "workout_stopped",    # Stopped by Safety Key
                    5: "workout_started",    # Started/Resumed by User
                    
                    # These are additional status codes that might be relevant
                    15: "workout_update",    # New Training Time
                    19: "workout_update",    # New Parameters
                }
                
                if op_code in status_mapping:
                    status_event = status_mapping[op_code]
                    logger.info(f"Mapping FTMS status {op_code} to event: {status_event}")
                    
                    # Notify the status callback with the mapped event
                    self._notify_status(status_event, data)
                else:
                    # For other status codes, just pass through
                    self._notify_status("machine_status", data)
            else:
                self._notify_status("machine_status", data)
            
        except Exception as e:
            logger.error(f"Error processing fitness machine status: {str(e)}")
            logger.exception(e)
    
    def _notify_data(self, data: Dict[str, Any]) -> None:
        """
        Notify all registered data callbacks with new data.
        
        Args:
            data: Dictionary of FTMS data
        """
        if not data:
            logger.warning("Received empty data in _notify_data")
            return
            
        for callback in self.data_callbacks:
            try:
                callback(data)
            except Exception as e:
                logger.error(f"Error in data callback: {str(e)}")
    
    def _notify_status(self, status: str, data: Any) -> None:
        """
        Notify all registered status callbacks with new status.
        
        Args:
            status: Status type
            data: Status data
        """
        if not status:
            logger.warning("Received empty status in _notify_status")
            return
            
        for callback in self.status_callbacks:
            try:
                callback(status, data)
            except Exception as e:
                logger.error(f"Error in status callback: {str(e)}")
    
    def _handle_disconnection(self, client: BleakClient) -> None:
        """
        Handle unexpected disconnections from the device.
        
        Args:
            client: The BleakClient that was disconnected
        """
        logger.warning(f"Unexpected disconnection from {self.connected_device.name if self.connected_device else 'device'}")
        self._notify_status("unexpected_disconnect", self.connected_device)
        
        # Clean up resources
        self.client = None
        self.ftms = None
        device = self.connected_device
        self.connected_device = None
        
        # Schedule reconnection attempt if we have the device info
        if device:
            logger.info(f"Scheduling reconnection attempt to {device.name} ({device.address})")
            asyncio.create_task(self._attempt_reconnection(device.address))
    
    async def _attempt_reconnection(self, address: str, max_attempts: int = 10) -> bool:
        """
        Attempt to reconnect to a device with exponential backoff for more robust recovery.
        
        Args:
            address: The address of the device to reconnect to
            max_attempts: Maximum number of reconnection attempts
            
        Returns:
            True if reconnection was successful, False otherwise
        """
        base_delay = 2  # Start with 2 seconds
        max_delay = 60  # Cap at 60 seconds
        
        logger.info(f"Starting reconnection with exponential backoff to {address}")
        self._notify_status("reconnecting_backoff", {"address": address, "max_attempts": max_attempts})
        
        for attempt in range(1, max_attempts + 1):
            # Calculate exponential backoff delay with jitter
            delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
            # Add a small random jitter (±20%) to prevent thundering herd problem
            jitter = delay * 0.2 * (2 * (0.5 - asyncio.get_event_loop().time() % 1))
            actual_delay = delay + jitter
            
            logger.info(f"Reconnection attempt {attempt}/{max_attempts} after {actual_delay:.2f}s delay")
            
            # Wait before attempting reconnection
            await asyncio.sleep(actual_delay)
            
            try:
                connected = await self.connect(address, max_retries=1)  # Single retry per attempt
                if connected and self.connected_device:
                    logger.info(f"Successfully reconnected to {self.connected_device.name} after {attempt} attempts")
                    self._notify_status("reconnected", {
                        "device": self.connected_device,
                        "attempts": attempt,
                        "total_time": sum([base_delay * (2 ** (i - 1)) for i in range(1, attempt + 1)])
                    })
                    return True
            except Exception as e:
                logger.error(f"Backoff reconnection attempt {attempt} failed: {str(e)}")
        
        logger.error(f"Failed to reconnect to device {address} after {max_attempts} backoff attempts")
        self._notify_status("reconnect_failed", {"address": address, "attempts": max_attempts})
        return False
        
    def clear_error_history(self, time_window: Optional[int] = None) -> None:
        """
        Clear the error history, optionally only clearing errors older than a specified time window.
        
        Args:
            time_window: Optional time window in seconds. If provided, only errors older than 
                         this many seconds will be cleared. If None, all errors are cleared.
        """
        if time_window is None:
            # Clear all errors
            self.connection_errors = []
            self.consecutive_errors = 0
            self.last_error_time = None
            logger.info("Cleared all connection error history")
        else:
            # Clear only errors older than the time window
            cutoff_time = datetime.datetime.now() - datetime.timedelta(seconds=time_window)
            old_count = len(self.connection_errors)
            self.connection_errors = [e for e in self.connection_errors if e['time'] > cutoff_time]
            removed_count = old_count - len(self.connection_errors)
            logger.info(f"Cleared {removed_count} connection errors older than {time_window} seconds")
            
            # Also reset consecutive errors if the last error is now gone
            if self.last_error_time and self.last_error_time < cutoff_time:
                self.consecutive_errors = 0
                self.last_error_time = None
                
        self._notify_status("error_history_cleared", {"time_window": time_window})
    
    async def check_connection_health(self) -> Dict[str, Any]:
        """
        Check the health of the current connection and return diagnostics.
        
        This method performs various checks to assess the stability and health
        of the current connection, and can be used for proactive monitoring.
        
        Returns:
            Dictionary with connection health information
        """
        health_info = {
            'is_connected': False,
            'device_name': None,
            'device_address': None,
            'connection_duration': None,
            'error_count': len(self.connection_errors),
            'consecutive_errors': self.consecutive_errors,
            'last_error_time': self.last_error_time,
            'status': 'unknown'
        }
        
        # Check if we have an active connection
        if not self.client or not self.connected_device:
            health_info['status'] = 'disconnected'
            return health_info
            
        try:
            # Basic connection check
            is_connected = self.client.is_connected
            health_info['is_connected'] = is_connected
            health_info['device_name'] = self.connected_device.name
            health_info['device_address'] = self.connected_device.address
            
            # More detailed checks if connected
            if is_connected:
                # Get connection duration if we have a connected device
                if hasattr(self.client, 'connect_time'):
                    connect_time = getattr(self.client, 'connect_time', None)
                    if connect_time:
                        health_info['connection_duration'] = (datetime.datetime.now() - connect_time).total_seconds()
                
                # Test FTMS service if available
                if self.ftms:
                    # Check if we can access FTMS services
                    health_info['ftms_available'] = True
                    # Attempt to read a characteristic to verify connection is working
                    try:
                        # Try to read a basic characteristic
                        await self.client.get_services()
                        health_info['status'] = 'healthy'
                    except Exception as e:
                        health_info['status'] = 'unstable'
                        health_info['error'] = str(e)
                        logger.warning(f"Connection health check failed: {str(e)}")
                else:
                    health_info['ftms_available'] = False
                    health_info['status'] = 'connected_no_ftms'
            else:
                health_info['status'] = 'disconnected'
                
            # Calculate error rate
            if self.connection_errors:
                # Calculate errors in the last hour
                one_hour_ago = datetime.datetime.now() - datetime.timedelta(hours=1)
                recent_errors = [e for e in self.connection_errors 
                                if e['time'] > one_hour_ago]
                health_info['recent_error_count'] = len(recent_errors)
                
                # Assess connection quality based on recent errors
                if len(recent_errors) > 10:
                    health_info['connection_quality'] = 'poor'
                elif len(recent_errors) > 5:
                    health_info['connection_quality'] = 'fair'
                else:
                    health_info['connection_quality'] = 'good'
            else:
                health_info['connection_quality'] = 'excellent'
                
            return health_info
            
        except Exception as e:
            logger.error(f"Error checking connection health: {str(e)}")
            health_info['status'] = 'error'
            health_info['error'] = str(e)
            return health_info

    def _track_connection_error(self, context: str, error_msg: str) -> None:
        """
        Track connection errors to help identify recurring issues.
        
        Args:
            context: The context in which the error occurred
            error_msg: The error message
        """
        now = datetime.datetime.now()
        self.connection_errors.append({
            'time': now,
            'context': context,
            'error': error_msg
        })
        self.last_error_time = now
        self.consecutive_errors += 1
        
        # Log when we hit consecutive error thresholds
        if self.consecutive_errors == self.max_consecutive_errors:
            logger.error(f"Hit {self.consecutive_errors} consecutive connection errors - connection may be unstable")
            self._notify_status("connection_unstable", {
                "consecutive_errors": self.consecutive_errors,
                "last_error": error_msg
            })

    def _handle_raw_notification(self, sender, data):
        """Handle raw notifications from FTMS characteristics."""
        try:
            logger.info(f"Received raw notification from {sender}: {data.hex()}")
            
            # Identify which characteristic sent this data
            if FTMS_ROWER_DATA_UUID.lower() == sender.lower():
                # This is rower data - parse according to FTMS specification
                self._parse_rower_data(data)
            elif FTMS_INDOOR_BIKE_DATA_UUID.lower() == sender.lower():
                # This is bike data - parse according to FTMS specification
                self._parse_bike_data(data)
            elif FTMS_FITNESS_MACHINE_STATUS_UUID.lower() == sender.lower():
                # This is machine status data - parse according to FTMS specification
                self._parse_status_data(data)
            else:
                logger.warning(f"Received notification from unknown characteristic: {sender}")
        except Exception as e:
            logger.error(f"Error processing raw notification: {e}", exc_info=True)
    
    def _parse_rower_data(self, data_bytes):
        """
        Parse raw rower data according to FTMS specification.
        
        The FTMS Rower Data characteristic is defined in the Bluetooth FTMS specification.
        This method parses the binary data sent by the rower.
        """
        try:
            logger.info(f"Parsing raw rower data: {data_bytes.hex()}")
            
            if len(data_bytes) < 2:
                logger.warning(f"Rower data too short: {len(data_bytes)} bytes")
                return
            
            # First 2 bytes are flags indicating which fields are present
            flags = int.from_bytes(data_bytes[0:2], byteorder='little')
            
            # Initialize data dictionary with default values
            rower_data = {
                'type': 'rower',
                'timestamp': time.time()
            }
            
            # Parse data fields based on flags
            index = 2  # Start after flags
            
            # Check if stroke rate is present (bit 0)
            if flags & 0x01:
                if index + 1 <= len(data_bytes):
                    # Stroke rate is uint8 in 0.5 strokes/minute
                    stroke_rate = data_bytes[index] * 0.5
                    rower_data['instant_stroke_rate'] = stroke_rate
                    index += 1
            
            # Check if stroke count is present (bit 1)
            if flags & 0x02:
                if index + 2 <= len(data_bytes):
                    # Stroke count is uint16
                    stroke_count = int.from_bytes(data_bytes[index:index+2], byteorder='little')
                    rower_data['total_strokes'] = stroke_count
                    index += 2
            
            # Check if average stroke rate is present (bit 2)
            if flags & 0x04:
                if index + 1 <= len(data_bytes):
                    # Average stroke rate is uint8 in 0.5 strokes/minute
                    avg_stroke_rate = data_bytes[index] * 0.5
                    rower_data['average_stroke_rate'] = avg_stroke_rate
                    index += 1
            
            # Check if total distance is present (bit 3)
            if flags & 0x08:
                if index + 3 <= len(data_bytes):
                    # Total distance is uint24 in meters
                    total_distance = int.from_bytes(data_bytes[index:index+3], byteorder='little')
                    rower_data['total_distance'] = total_distance
                    index += 3
            
            # Check if instantaneous pace is present (bit 4)
            if flags & 0x10:
                if index + 2 <= len(data_bytes):
                    # Instantaneous pace is uint16 in seconds per 500m
                    instant_pace = int.from_bytes(data_bytes[index:index+2], byteorder='little')
                    rower_data['instant_pace'] = instant_pace
                    index += 2
            
            # Check if average pace is present (bit 5)
            if flags & 0x20:
                if index + 2 <= len(data_bytes):
                    # Average pace is uint16 in seconds per 500m
                    avg_pace = int.from_bytes(data_bytes[index:index+2], byteorder='little')
                    rower_data['average_pace'] = avg_pace
                    index += 2
            
            # Check if instantaneous power is present (bit 6)
            if flags & 0x40:
                if index + 2 <= len(data_bytes):
                    # Instantaneous power is int16 in watts
                    instant_power = int.from_bytes(data_bytes[index:index+2], byteorder='little')
                    rower_data['instant_power'] = instant_power
                    index += 2
            
            # Check if average power is present (bit 7)
            if flags & 0x80:
                if index + 2 <= len(data_bytes):
                    # Average power is uint16 in watts
                    avg_power = int.from_bytes(data_bytes[index:index+2], byteorder='little')
                    rower_data['average_power'] = avg_power
                    index += 2
            
            # Check if resistance level is present (bit 8)
            if flags & 0x100:
                if index + 1 <= len(data_bytes):
                    # Resistance level is int8
                    resistance = int.from_bytes(data_bytes[index:index+1], byteorder='little', signed=True)
                    rower_data['resistance_level'] = resistance
                    index += 1
            
            # Check if energy/calories is present (bit 9)
            if flags & 0x200:
                if index + 2 <= len(data_bytes):
                    # Energy is uint16 in calories
                    energy = int.from_bytes(data_bytes[index:index+2], byteorder='little')
                    rower_data['total_energy'] = energy
                    index += 2
            
            # Check if heart rate is present (bit 10)
            if flags & 0x400:
                if index + 1 <= len(data_bytes):
                    # Heart rate is uint8 in BPM
                    heart_rate = data_bytes[index]
                    rower_data['heart_rate'] = heart_rate
                    index += 1
            
            # Check if elapsed time is present (bit 11)
            if flags & 0x800:
                if index + 2 <= len(data_bytes):
                    # Elapsed time is uint16 in seconds
                    elapsed_time = int.from_bytes(data_bytes[index:index+2], byteorder='little')
                    rower_data['elapsed_time'] = elapsed_time
                    index += 2
            
            # Check if remaining time is present (bit 12)
            if flags & 0x1000:
                if index + 2 <= len(data_bytes):
                    # Remaining time is uint16 in seconds
                    remaining_time = int.from_bytes(data_bytes[index:index+2], byteorder='little')
                    rower_data['remaining_time'] = remaining_time
                    index += 2
            
            logger.info(f"Parsed rower data: {rower_data}")
            
            # Pass the parsed data to registered callbacks
            for callback in self.data_callbacks:
                callback(rower_data)
                
        except Exception as e:
            logger.error(f"Error parsing rower data: {e}", exc_info=True)
    
    def _parse_bike_data(self, data_bytes):
        """
        Parse raw bike data according to FTMS specification.
        
        The FTMS Indoor Bike Data characteristic is defined in the Bluetooth FTMS specification.
        This method parses the binary data sent by the bike.
        """
        try:
            logger.info(f"Parsing raw bike data: {data_bytes.hex()}")
            
            if len(data_bytes) < 2:
                logger.warning(f"Bike data too short: {len(data_bytes)} bytes")
                return
            
            # First 2 bytes are flags indicating which fields are present
            flags = int.from_bytes(data_bytes[0:2], byteorder='little')
            
            # Initialize data dictionary with default values
            bike_data = {
                'type': 'bike',
                'timestamp': time.time()
            }
            
            # Parse data fields based on flags
            index = 2  # Start after flags
            
            # Check if instantaneous speed is present (bit 0)
            if flags & 0x01:
                if index + 2 <= len(data_bytes):
                    # Speed is uint16 in units of 0.01 km/h
                    speed = int.from_bytes(data_bytes[index:index+2], byteorder='little') * 0.01
                    bike_data['instant_speed'] = speed
                    index += 2
            
            # Check if average speed is present (bit 1)
            if flags & 0x02:
                if index + 2 <= len(data_bytes):
                    # Avg speed is uint16 in units of 0.01 km/h
                    avg_speed = int.from_bytes(data_bytes[index:index+2], byteorder='little') * 0.01
                    bike_data['average_speed'] = avg_speed
                    index += 2
            
            # Check if instantaneous cadence is present (bit 2)
            if flags & 0x04:
                if index + 2 <= len(data_bytes):
                    # Cadence is uint16 in units of 0.5 RPM
                    cadence = int.from_bytes(data_bytes[index:index+2], byteorder='little') * 0.5
                    bike_data['instant_cadence'] = cadence
                    index += 2
            
            # Check if average cadence is present (bit 3)
            if flags & 0x08:
                if index + 2 <= len(data_bytes):
                    # Avg cadence is uint16 in units of 0.5 RPM
                    avg_cadence = int.from_bytes(data_bytes[index:index+2], byteorder='little') * 0.5
                    bike_data['average_cadence'] = avg_cadence
                    index += 2
            
            # Check if total distance is present (bit 4)
            if flags & 0x10:
                if index + 3 <= len(data_bytes):
                    # Total distance is uint24 in meters
                    total_distance = int.from_bytes(data_bytes[index:index+3], byteorder='little')
                    bike_data['total_distance'] = total_distance
                    index += 3
            
            # Check if resistance level is present (bit 5)
            if flags & 0x20:
                if index + 1 <= len(data_bytes):
                    # Resistance level is int8
                    resistance = int.from_bytes(data_bytes[index:index+1], byteorder='little', signed=True)
                    bike_data['resistance_level'] = resistance
                    index += 1
            
            # Check if instantaneous power is present (bit 6)
            if flags & 0x40:
                if index + 2 <= len(data_bytes):
                    # Instantaneous power is int16 in watts
                    power = int.from_bytes(data_bytes[index:index+2], byteorder='little', signed=True)
                    bike_data['instant_power'] = power
                    index += 2
            
            # Check if average power is present (bit 7)
            if flags & 0x80:
                if index + 2 <= len(data_bytes):
                    # Average power is int16 in watts
                    avg_power = int.from_bytes(data_bytes[index:index+2], byteorder='little', signed=True)
                    bike_data['average_power'] = avg_power
                    index += 2
            
            # Check if energy expenditure is present (bit 8)
            if flags & 0x100:
                if index + 2 <= len(data_bytes):
                    # Total energy is uint16 in calories
                    energy = int.from_bytes(data_bytes[index:index+2], byteorder='little')
                    bike_data['total_energy'] = energy
                    index += 2
                    
                # Check if energy per hour is present (included with total energy)
                if index + 2 <= len(data_bytes):
                    # Energy per hour is uint16 in calories per hour
                    energy_per_hour = int.from_bytes(data_bytes[index:index+2], byteorder='little')
                    bike_data['energy_per_hour'] = energy_per_hour
                    index += 2
                    
                # Check if energy per minute is present (included with total energy)
                if index + 1 <= len(data_bytes):
                    # Energy per minute is uint8 in calories per minute
                    energy_per_minute = data_bytes[index]
                    bike_data['energy_per_minute'] = energy_per_minute
                    index += 1
            
            # Check if heart rate is present (bit 9)
            if flags & 0x200:
                if index + 1 <= len(data_bytes):
                    # Heart rate is uint8 in BPM
                    heart_rate = data_bytes[index]
                    bike_data['heart_rate'] = heart_rate
                    index += 1
            
            # Check if metabolic equivalent is present (bit 10)
            if flags & 0x400:
                if index + 1 <= len(data_bytes):
                    # Metabolic equivalent is uint8 in 0.1 MET units
                    met = data_bytes[index] * 0.1
                    bike_data['metabolic_equivalent'] = met
                    index += 1
            
            # Check if elapsed time is present (bit 11)
            if flags & 0x800:
                if index + 2 <= len(data_bytes):
                    # Elapsed time is uint16 in seconds
                    elapsed_time = int.from_bytes(data_bytes[index:index+2], byteorder='little')
                    bike_data['elapsed_time'] = elapsed_time
                    index += 2
            
            # Check if remaining time is present (bit 12)
            if flags & 0x1000:
                if index + 2 <= len(data_bytes):
                    # Remaining time is uint16 in seconds
                    remaining_time = int.from_bytes(data_bytes[index:index+2], byteorder='little')
                    bike_data['remaining_time'] = remaining_time
                    index += 2
            
            logger.info(f"Parsed bike data: {bike_data}")
            
            # Pass the parsed data to registered callbacks
            for callback in self.data_callbacks:
                callback(bike_data)
                
        except Exception as e:
            logger.error(f"Error parsing bike data: {e}", exc_info=True)
    
    def _parse_status_data(self, data_bytes):
        """
        Parse raw fitness machine status data according to FTMS specification.
        """
        try:
            logger.info(f"Parsing raw status data: {data_bytes.hex()}")
            
            if len(data_bytes) < 1:
                logger.warning(f"Status data too short: {len(data_bytes)} bytes")
                return
            
            # First byte is the op code
            op_code = data_bytes[0]
            
            # Create status data dictionary
            status_data = {
                'op_code': op_code,
                'parameters': data_bytes[1:].hex() if len(data_bytes) > 1 else None
            }
            
            # Map op code to status name for readability
            op_code_map = {
                1: "Reset",
                2: "Stopped by User",
                3: "Stopped by Safety Key",
                4: "Started/Resumed by User",
                5: "Target Speed Changed",
                6: "Target Incline Changed",
                7: "Target Resistance Level Changed",
                8: "Target Power Changed",
                9: "Target Heart Rate Changed",
                10: "Targeted Expended Energy Changed",
                11: "Targeted Number of Steps Changed",
                12: "Targeted Number of Strides Changed",
                13: "Targeted Distance Changed",
                14: "Targeted Training Time Changed",
                15: "Targeted Time in Two Heart Rate Zones Changed",
                16: "Targeted Time in Three Heart Rate Zones Changed",
                17: "Targeted Time in Five Heart Rate Zones Changed",
                18: "Indoor Bike Simulation Parameters Changed",
                19: "Wheel Circumference Changed"
            }
            
            if op_code in op_code_map:
                status_data['name'] = op_code_map[op_code]
            else:
                status_data['name'] = f"Unknown ({op_code})"
            
            logger.info(f"Parsed status data: {status_data}")
            
            # Pass to the fitness machine status handler
            self._handle_fitness_machine_status(status_data)
            
        except Exception as e:
            logger.error(f"Error parsing status data: {e}", exc_info=True)
        
async def main():
    """Example usage of the FTMSConnector class."""
    connector = FTMSConnector()
    
    # Define callbacks
    def data_callback(data):
        print(f"Received data: {data}")
    
    def status_callback(status, data):
        print(f"Status update: {status} - {data}")
    
    # Register callbacks
    connector.register_data_callback(data_callback)
    connector.register_status_callback(status_callback)
    
    # Discover devices
    devices = await connector.discover_devices()
    
    if devices:
        # Connect to the first device found
        device_address = list(devices.keys())[0]
        await connector.connect(device_address)
        
        # Keep the connection open for 60 seconds
        await asyncio.sleep(60)
        
        # Disconnect
        await connector.disconnect()
    else:
        print("No FTMS devices found")


if __name__ == "__main__":
    asyncio.run(main())
