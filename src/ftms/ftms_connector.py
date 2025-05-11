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
import binascii
import threading

import bleak
from bleak import BleakScanner, BleakClient
from bleak.backends.device import BLEDevice

import pyftms
from pyftms import FitnessMachine, MachineType

# Define our own data classes for compatibility until we figure out the correct imports
class RowerData:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

class IndoorBikeData:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

class FitnessMachineStatus:
    def __init__(self, status_code=None):
        self.status_code = status_code

class StatusCode:
    def __init__(self, value, name):
        self.value = value
        self.name = name

# Define FitnessMachineFeatures class as it's not available in pyftms
class FitnessMachineFeatures:
    def __init__(self):
        self.rower_data_supported = False
        self.indoor_bike_data_supported = False

# Add the project root to the path so we can use absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from src.utils.logging_config import get_component_logger

# Get component logger
logger = get_component_logger("ftms_connector")

# FTMS UUIDs (still useful for discovery and reference)
FTMS_SERVICE_UUID = "00001826-0000-1000-8000-00805f9b34fb"
ROGUE_MANUFACTURER_NAME = "Rogue"  # Adjust if needed based on actual device advertising

class FTMSConnector:
    """
    Class for handling connections to FTMS-compatible fitness equipment using pyftms.
    """
    
    def __init__(self, device_type="auto"):
        """
        Initialize the FTMS connector.
        
        Args:
            device_type: Type of device to connect to ("auto", "indoor_bike", "rower", "cross_trainer")
        """
        self.devices: Dict[str, BLEDevice] = {}
        self.ble_client: Optional[BleakClient] = None
        self.ftms_client: Optional[FitnessMachine] = None 
        self.connected_device_ble: Optional[BLEDevice] = None
        self.data_callbacks: List[Callable[[Dict[str, Any]], None]] = []
        self.status_callbacks: List[Callable[[str, Any], None]] = []
        self.connection_errors = []
        self.last_error_time = None
        self.consecutive_errors = 0
        self.max_consecutive_errors = 5
        self.device_type: Optional[MachineType] = None
        
        # Variables for distance smoothing
        self.last_distance = 0
        self.last_timestamp = None
        self.last_speed = 0
        
        # Save the requested device type
        self.requested_device_type = device_type
        logger.info(f"FTMS Connector initialized with device type: {device_type}")
        
        # Map the string device type to MachineType enum
        if device_type == "indoor_bike":
            self.requested_machine_type = MachineType.INDOOR_BIKE
        elif device_type == "rower":
            self.requested_machine_type = MachineType.ROWER
        elif device_type == "cross_trainer":
            self.requested_machine_type = MachineType.CROSS_TRAINER
        else:
            # For "auto" or any other value, we'll determine the type during connection
            self.requested_machine_type = None

    def register_data_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """
        Register a callback function to be called when data is received from the device.
        
        Args:
            callback: A function that takes a dictionary of data as an argument
        """
        if callback not in self.data_callbacks:
            self.data_callbacks.append(callback)
            logger.info(f"Data callback {callback.__name__ if hasattr(callback, '__name__') else str(callback)} registered.")
        else:
            logger.debug(f"Data callback {callback.__name__ if hasattr(callback, '__name__') else str(callback)} already registered.")

    def unregister_data_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """
        Unregister a previously registered data callback function.
        
        Args:
            callback: The callback function to unregister
        """
        if callback in self.data_callbacks:
            self.data_callbacks.remove(callback)
            logger.info(f"Data callback {callback.__name__ if hasattr(callback, '__name__') else str(callback)} unregistered.")
        else:
            logger.debug(f"Data callback {callback.__name__ if hasattr(callback, '__name__') else str(callback)} not found in registered callbacks.")
            
    def register_status_callback(self, callback: Callable[[str, Any], None]):
        """
        Register a callback function to be called when device status changes.
        
        Args:
            callback: A function that takes a status string and data as arguments
        """
        if callback not in self.status_callbacks:
            self.status_callbacks.append(callback)
            logger.info(f"Status callback {callback.__name__ if hasattr(callback, '__name__') else str(callback)} registered.")
        else:
            logger.debug(f"Status callback {callback.__name__ if hasattr(callback, '__name__') else str(callback)} already registered.")

    def unregister_status_callback(self, callback: Callable[[str, Any], None]):
        """
        Unregister a previously registered status callback function.
        
        Args:
            callback: The callback function to unregister
        """
        if callback in self.status_callbacks:
            self.status_callbacks.remove(callback)
            logger.info(f"Status callback {callback.__name__ if hasattr(callback, '__name__') else str(callback)} unregistered.")
        else:
            logger.debug(f"Status callback {callback.__name__ if hasattr(callback, '__name__') else str(callback)} not found in registered callbacks.")

    def _notify_data(self, data: Dict[str, Any]):
        """Notify all registered data callbacks with new FTMS data."""
        logger.debug(f"Notifying {len(self.data_callbacks)} data callbacks")
        for callback in self.data_callbacks:
            try:
                callback(data)
            except Exception as e:
                logger.error(f"Error in data callback {callback.__name__ if hasattr(callback, '__name__') else str(callback)}: {e}")
                
    def _notify_status(self, status_type: str, data: Any):
        """Notify all registered status callbacks with status updates."""
        logger.debug(f"Notifying {len(self.status_callbacks)} status callbacks: {status_type}")
        for callback in self.status_callbacks:
            try:
                callback(status_type, data)
            except Exception as e:
                logger.error(f"Error in status callback {callback.__name__ if hasattr(callback, '__name__') else str(callback)}: {e}")

    def _handle_pyftms_callback(self, event_type, data):
        """
        Handle callbacks from the pyftms client with new callback architecture.
        
        Args:
            event_type: Type of event (data, status, etc.)
            data: The data associated with the event
        """
        logger.debug(f"pyftms callback: {event_type} - {data}")
        logger.info(f"BLUETOOTH DATA RECEIVED: Event type: {event_type}")
        
        try:
            # Handle different event types
            if event_type == "indoor_bike_data" or event_type == "bike_data":
                # Process indoor bike data
                processed_data = {
                    "device_type": "bike",
                    "timestamp": datetime.datetime.now().isoformat(),
                }
                
                # Add all data fields from the callback data
                if hasattr(data, "__dict__"):
                    processed_data.update({k: v for k, v in data.__dict__.items() if not k.startswith("_")})
                    logger.info(f"BIKE DATA: Speed: {getattr(data, 'instantaneous_speed', 'N/A')}, " +
                               f"Cadence: {getattr(data, 'instantaneous_cadence', 'N/A')}, " +
                               f"Power: {getattr(data, 'instantaneous_power', 'N/A')}")
                elif isinstance(data, dict):
                    processed_data.update(data)
                    logger.info(f"BIKE DATA: {data}")
                else:
                    # Try to extract common attributes
                    for attr in ["instantaneous_speed", "instantaneous_cadence", "instantaneous_power", 
                                "total_distance", "heart_rate", "resistance_level"]:
                        if hasattr(data, attr):
                            processed_data[attr.replace("instantaneous_", "")] = getattr(data, attr)
                    
                    logger.info(f"BIKE DATA: Speed: {getattr(data, 'instantaneous_speed', 'N/A')}, " +
                               f"Cadence: {getattr(data, 'instantaneous_cadence', 'N/A')}, " +
                               f"Power: {getattr(data, 'instantaneous_power', 'N/A')}")
                
                # Standardize field names and ensure values are not None
                if "instantaneous_speed" in processed_data:
                    processed_data["speed"] = processed_data.pop("instantaneous_speed")
                if "instantaneous_cadence" in processed_data:
                    processed_data["cadence"] = processed_data.pop("instantaneous_cadence")
                if "instantaneous_power" in processed_data:
                    processed_data["power"] = processed_data.pop("instantaneous_power")
                
                # Ensure critical values are present and not None
                processed_data["speed"] = processed_data.get("speed", 0) or 0
                processed_data["cadence"] = processed_data.get("cadence", 0) or 0
                processed_data["power"] = processed_data.get("power", 0) or 0
                
                logger.info(f"Forwarding processed bike data to _notify_data")
                self._notify_data(processed_data)
                
            elif event_type == "rower_data":
                # Process rower data
                processed_data = {
                    "device_type": "rower",
                    "timestamp": datetime.datetime.now().isoformat(),
                }
                
                # Add all data fields from the callback data
                if hasattr(data, "__dict__"):
                    processed_data.update({k: v for k, v in data.__dict__.items() if not k.startswith("_")})
                    logger.info(f"ROWER DATA: Stroke Rate: {getattr(data, 'stroke_rate', 'N/A')}, " +
                               f"Power: {getattr(data, 'instantaneous_power', 'N/A')}, " +
                               f"Pace: {getattr(data, 'instantaneous_pace', 'N/A')}")
                elif isinstance(data, dict):
                    processed_data.update(data)
                    logger.info(f"ROWER DATA: {data}")
                else:
                    # Try to extract common attributes
                    for attr in ["stroke_rate", "stroke_count", "total_distance", "instantaneous_pace", 
                                "instantaneous_power", "heart_rate", "resistance_level"]:
                        if hasattr(data, attr):
                            processed_data[attr.replace("instantaneous_", "")] = getattr(data, attr)
                    
                    logger.info(f"ROWER DATA: Stroke Rate: {getattr(data, 'stroke_rate', 'N/A')}, " +
                               f"Power: {getattr(data, 'instantaneous_power', 'N/A')}, " +
                               f"Pace: {getattr(data, 'instantaneous_pace', 'N/A')}")
                
                # Calculate speed from pace if available
                if "instantaneous_pace" in processed_data and processed_data["instantaneous_pace"] > 0:
                    processed_data["speed"] = 500.0 / processed_data["instantaneous_pace"]
                elif "pace" in processed_data and processed_data["pace"] > 0:
                    processed_data["speed"] = 500.0 / processed_data["pace"]
                else:
                    processed_data["speed"] = None
                
                # Standardize field names
                if "instantaneous_pace" in processed_data:
                    processed_data["pace"] = processed_data.pop("instantaneous_pace")
                if "instantaneous_power" in processed_data:
                    processed_data["power"] = processed_data.pop("instantaneous_power")
                
                logger.info(f"Forwarding processed rower data to _notify_data")
                self._notify_data(processed_data)
                
            elif event_type == "status" or event_type == "machine_status":
                # Process status updates
                status_code = None
                status_meaning = "Unknown"
                
                if hasattr(data, "status_code"):
                    status_code = data.status_code
                    # Try to get the name or value from the status code
                    if hasattr(status_code, "name"):
                        status_meaning = status_code.name.replace("_", " ").capitalize()
                    elif hasattr(status_code, "value"):
                        status_meaning = f"Status code {status_code.value}"
                    
                logger.info(f"Machine Status: {status_meaning}")
                self._notify_status("machine_status", {"code": getattr(status_code, "value", 0), 
                                                     "meaning": status_meaning, 
                                                     "raw_enum": status_code})
                
            elif event_type == "control_point_result":
                # Process control point results
                logger.info(f"Control Point Result: {data}")
                self._notify_status("control_result", data)
                
            else:
                # Handle any other event types
                logger.info(f"Unhandled event type: {event_type} - {data}")
                self._notify_status(event_type, data)
                
        except Exception as e:
            logger.error(f"Error in pyftms callback handler: {e}")
            import traceback
            logger.error(traceback.format_exc())

    async def discover_devices(self, timeout: int = 5) -> Dict[str, BLEDevice]:
        """
        Discover FTMS-compatible devices.
        
        Args:
            timeout: Number of seconds to scan for devices
            
        Returns:
            Dictionary of discovered devices, with addresses as keys
        """
        logger.info(f"Scanning for FTMS devices for {timeout} seconds...")
        self.devices = {}
        try:
            def detection_callback(device: BLEDevice, advertisement_data):
                try:
                    if not device or not hasattr(device, "address"):
                        logger.warning("Received invalid device in detection callback")
                        return
                    service_uuids = advertisement_data.service_uuids if hasattr(advertisement_data, "service_uuids") else []
                    device_name = device.name if device.name else "Unknown"
                    
                    if FTMS_SERVICE_UUID.lower() in [str(uuid).lower() for uuid in service_uuids]:
                        logger.info(f"Found FTMS device: {device_name} ({device.address})")
                        self.devices[device.address] = device
                        self._notify_status("device_found", device)
                    elif device_name and ROGUE_MANUFACTURER_NAME.lower() in device_name.lower():
                        logger.info(f"Found potential Rogue device: {device_name} ({device.address})")
                        self.devices[device.address] = device
                        self._notify_status("device_found", device)
                except Exception as e:
                    logger.error(f"Error in detection callback: {str(e)}")
                    
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
            self._notify_status("discovery_error", str(e))
            return {}

    async def connect(self, device_address: str, max_retries: int = 3) -> bool:
        """
        Connect to a specific FTMS device and set up pyftms client.
        
        Args:
            device_address: BLE address of the device to connect to
            max_retries: Number of connection attempts to make before giving up
            
        Returns:
            True if connection successful, False otherwise
        """
        if not device_address:
            logger.error("No device address provided")
            self._notify_status("connection_error", "No device address provided")
            return False
            
        if device_address not in self.devices:
            logger.warning(f"Device {device_address} not found, attempting rediscovery")
            await self.discover_devices(timeout=3)
            if device_address not in self.devices:
                logger.error(f"Device {device_address} not found after rediscovery")
                self._notify_status("connection_error", "Device not found")
                return False
        
        device = self.devices[device_address]
        logger.info(f"Connecting to {device.name} ({device.address})...")
        self._notify_status("connecting", device)
        
        retry_count = 0
        while retry_count < max_retries:
            try:
                if self.ble_client and self.ble_client.is_connected:
                    await self.disconnect()
                
                self.ble_client = BleakClient(device.address)
                connect_timeout = 15  
                try:
                    await asyncio.wait_for(self.ble_client.connect(), timeout=connect_timeout)
                except asyncio.TimeoutError:
                    retry_count += 1
                    logger.warning(f"Connection timed out (Attempt {retry_count}/{max_retries})")
                    if retry_count >= max_retries:
                        self._notify_status("connection_error", "Connection timed out")
                        return False
                    await asyncio.sleep(2)
                    continue
                
                if not self.ble_client.is_connected:
                    raise bleak.exc.BleakError("Failed to connect after connect() call.")

                logger.info(f"Successfully connected to BLE device: {device.name}")
                # Determine which machine type to use with the pyftms client
                machine_type = None
                
                # Use explicitly requested machine type if set
                if self.requested_device_type:
                    machine_type = self.requested_device_type
                    self.device_type = self.requested_device_type
                    logger.info(f"Using explicitly requested device type: {machine_type}")
                # Otherwise try to determine machine type from device name
                elif device.name and "bike" in device.name.lower():
                    machine_type = MachineType.INDOOR_BIKE
                    self.device_type = MachineType.INDOOR_BIKE
                    logger.info("Inferred device type from name: Indoor Bike")
                elif device.name and "rower" in device.name.lower():
                    machine_type = MachineType.ROWER
                    self.device_type = MachineType.ROWER
                    logger.info("Inferred device type from name: Rower")
                elif device.name and "echo" in device.name.lower():
                    # Rogue Echo Bike is likely an indoor bike
                    machine_type = MachineType.INDOOR_BIKE
                    self.device_type = MachineType.INDOOR_BIKE
                    logger.info("Inferred device type from name (Echo): Indoor Bike")
                else:
                    # Default to indoor bike if we can't determine
                    machine_type = MachineType.INDOOR_BIKE
                    self.device_type = MachineType.INDOOR_BIKE
                    logger.info("Using default device type: Indoor Bike")

                # Check the current pyftms version we're working with
                try:
                    # First, try to create the client with the appropriate machine type
                    if hasattr(pyftms, 'get_client'):
                        # For newer pyftms versions
                        logger.info("Using pyftms.get_client() method")
                        
                        # Make sure we have the BleakDevice object
                        ble_device = None
                        if isinstance(device, bleak.backends.device.BLEDevice):
                            ble_device = device
                        else:
                            logger.error(f"Device is not a BleakDevice instance: {type(device)}")
                            raise ValueError("Expected a BleakDevice instance")
                            
                        # Import the machine type enum from pyftms
                        try:
                            # Try to import the machine type from the new location
                            from pyftms.client.properties import MachineType as PyftmsMachineType
                            logger.info("Using MachineType from pyftms.client.properties")
                        except ImportError:
                            try:
                                # Fall back to the old location
                                from pyftms.properties import MachineType as PyftmsMachineType
                                logger.info("Using MachineType from pyftms.properties")
                            except ImportError:
                                logger.error("Could not import MachineType from pyftms")
                                raise RuntimeError("Could not import MachineType from pyftms")
                        
                        # Convert our machine type to the pyftms machine type
                        pyftms_machine_type = None
                        if machine_type == MachineType.INDOOR_BIKE:
                            pyftms_machine_type = PyftmsMachineType.INDOOR_BIKE
                        elif machine_type == MachineType.ROWER:
                            pyftms_machine_type = PyftmsMachineType.ROWER
                        elif machine_type == MachineType.CROSS_TRAINER:
                            pyftms_machine_type = PyftmsMachineType.CROSS_TRAINER
                        else:
                            pyftms_machine_type = PyftmsMachineType.INDOOR_BIKE  # Default
                            
                        logger.info(f"Using pyftms machine type: {pyftms_machine_type}")
                        
                        # Create a callback function that will call our handler
                        def on_ftms_event(event_type, data):
                            self._handle_pyftms_callback(event_type, data)
                            
                        # Now we can create the client correctly
                        try:
                            logger.info(f"Creating FTMS client with proper parameters")
                            self.ftms_client = pyftms.get_client(
                                ble_device=ble_device,
                                adv_or_type=pyftms_machine_type,
                                timeout=10.0,
                                on_ftms_event=on_ftms_event
                            )
                        except Exception as e_client:
                            logger.error(f"Failed to create client with proper parameters: {e_client}")
                            
                            # Try another approach - use get_client_from_address
                            try:
                                logger.info(f"Attempting to create client with get_client_from_address")
                                # This is an async function, so we need to run it in the event loop
                                self.ftms_client = asyncio.get_event_loop().run_until_complete(
                                    pyftms.get_client_from_address(
                                        address=device.address,
                                        timeout=10.0,
                                        on_ftms_event=on_ftms_event
                                    )
                                )
                            except Exception as e_address:
                                logger.error(f"Failed to create client with get_client_from_address: {e_address}")
                                raise RuntimeError(f"All attempts to create FTMS client failed")
                    else:
                        # For older pyftms versions, try to directly instantiate the classes
                        logger.info("Attempting to directly create FTMS client instance")
                        if machine_type == MachineType.INDOOR_BIKE:
                            self.ftms_client = pyftms.IndoorBike(self.ble_client)
                        elif machine_type == MachineType.ROWER:
                            self.ftms_client = pyftms.Rower(self.ble_client)
                        else:
                            # Fall back to generic handler
                            self.ftms_client = pyftms.FitnessMachine(self.ble_client)
                except Exception as e:
                    logger.error(f"Failed to create FTMS client: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                    raise RuntimeError(f"Failed to initialize FTMS client: {e}")
                
                if not self.ftms_client:
                    raise RuntimeError("Failed to create FTMS client object")
                    
                logger.info(f"Successfully created FTMS client: {type(self.ftms_client).__name__}")
                self.connected_device_ble = device

                try:
                    features_data: Optional[FitnessMachineFeatures] = await self.ftms_client.get_fitness_machine_feature()
                    if features_data:
                        logger.info(f"FTMS Features: {features_data}")
                        if features_data.rower_data_supported:
                            self.device_type = MachineType.ROWER
                            logger.info("Inferred device type: Rower")
                        elif features_data.indoor_bike_data_supported:
                            self.device_type = MachineType.INDOOR_BIKE
                            logger.info("Inferred device type: Indoor Bike")
                except Exception as e_feat:
                    logger.warning(f"Could not read FTMS features: {e_feat}. Proceeding with generic setup.")

                logger.info("Setting pyftms data handlers...")
                # Set up the right handlers based on the machine type
                try:
                    # Check the direct class types instead of module paths
                    if isinstance(self.ftms_client, pyftms.IndoorBike):
                        logger.info("Setting up handlers for IndoorBike client...")
                        # IndoorBike has its own callback system
                        self.ftms_client.set_callback(self._handle_pyftms_callback)
                    elif isinstance(self.ftms_client, pyftms.Rower):
                        logger.info("Setting up handlers for Rower client...")
                        # Rower has its own callback system
                        self.ftms_client.set_callback(self._handle_pyftms_callback)
                    else:
                        logger.warning(f"Unknown client type: {type(self.ftms_client)}, using generic approach...")
                        # Try to set up a generic callback
                        if hasattr(self.ftms_client, 'set_callback'):
                            self.ftms_client.set_callback(self._handle_pyftms_callback)
                        else:
                            logger.error("Cannot set up any handlers for this client type!")
                except Exception as e:
                    logger.error(f"Error setting up data handlers: {e}")
                    # Don't fail the connection due to handler setup issues
                    # We'll try to proceed anyway
                
                logger.info("FTMS client initialized and handlers set.")
                
                # Special handling for Echo Bike - set up notifications right away
                if self.connected_device_ble and self.connected_device_ble.name and 'echo' in self.connected_device_ble.name.lower():
                    logger.info("Echo Bike detected, setting up notifications immediately...")
                    # Set a flag to avoid duplicate notification setup
                    self._notifications_set_up = False
                    # Set up notifications in a background task to avoid blocking the connection
                    asyncio.create_task(self._setup_echo_bike_notifications())
                
                # Start data polling thread for reliable data collection
                self._start_data_polling()
                
                self._notify_status("connected", device)
                self.consecutive_errors = 0
                return True
            
            except (bleak.exc.BleakDeviceNotFoundError, bleak.exc.BleakError) as e_bleak:
                retry_count += 1
                logger.error(f"BLEAK Error during connection (Attempt {retry_count}/{max_retries}): {e_bleak}")
                self._track_connection_error("connection_bleak", str(e_bleak))
                if self.ble_client and self.ble_client.is_connected:
                    await self.ble_client.disconnect() 
                self.ble_client = None
                self.ftms_client = None
                if retry_count >= max_retries:
                    self._notify_status("connection_error", f"BleakError: {e_bleak}")
                    return False
                await asyncio.sleep(2)
            except Exception as e_connect:
                retry_count += 1
                logger.error(f"Unexpected error during connection (Attempt {retry_count}/{max_retries}): {e_connect}")
                self._track_connection_error("connection_unexpected", str(e_connect))
                if self.ble_client and self.ble_client.is_connected:
                    await self.ble_client.disconnect()
                self.ble_client = None
                self.ftms_client = None
                if retry_count >= max_retries:
                    self._notify_status("connection_error", f"Unexpected error: {e_connect}")
                    return False
                await asyncio.sleep(2)
        
        logger.error("Failed to connect after multiple retries.")
        self._notify_status("connection_error", "Failed after multiple retries")
        return False

    async def disconnect(self):
        """Disconnect from the currently connected device."""
        if self.ble_client and self.ble_client.is_connected:
            logger.info(f"Disconnecting from {self.connected_device_ble.name if self.connected_device_ble else 'Unknown device'}...")
            try:
                if self.ftms_client:
                    # Clean up any FTMS client resources if needed
                    pass
                await self.ble_client.disconnect()
                self._notify_status("disconnected", self.connected_device_ble)
                return True
            except Exception as e:
                logger.error(f"Error during disconnection: {e}")
                return False
            finally:
                self._stop_data_polling()
                self.ble_client = None
                self.ftms_client = None
                self.connected_device_ble = None
                self.device_type = None
                logger.info("Disconnected.")
        else:
            logger.info("No device connected or already disconnected.")
            return True

    def is_connected(self) -> bool:
        """Check if currently connected to a device."""
        return self.ble_client is not None and self.ble_client.is_connected and self.ftms_client is not None

    def _track_connection_error(self, error_type: str, error_message: str):
        """Track connection errors to detect repeated failures."""
        now = time.time()
        self.connection_errors.append((now, error_type, error_message))
        
        # Limit the number of stored errors to avoid memory issues
        if len(self.connection_errors) > 100:
            self.connection_errors = self.connection_errors[-100:]
        
        # Check if this is a consecutive error within a short time period
        if self.last_error_time and (now - self.last_error_time) < 10:  # 10 seconds
            self.consecutive_errors += 1
            logger.warning(f"Consecutive connection error #{self.consecutive_errors}")
            
            # If too many consecutive errors, suggest restart
            if self.consecutive_errors >= self.max_consecutive_errors:
                logger.error(f"Detected {self.consecutive_errors} consecutive connection errors. " +
                           "Bluetooth stack may need to be restarted.")
                self._notify_status("connection_error", "Multiple consecutive errors - Bluetooth stack may need to be restarted")
        else:
            self.consecutive_errors = 1
        
        self.last_error_time = now

    def _start_data_polling(self):
        """Start a background thread to poll for data periodically."""
        # Implementation will depend on what needs to be polled
        logger.info("Data polling started...")
        # This would typically create a thread or task to periodically check for data

    def _stop_data_polling(self):
        """Stop the background data polling thread."""
        logger.info("Data polling stopped.")
        # This would typically signal a thread or task to stop polling

    async def _setup_echo_bike_notifications(self):
        """Set up notification handlers specifically for the Echo Bike."""
        if not self.is_connected() or not self.ftms_client:
            logger.error("Cannot set up Echo Bike notifications - not connected")
            return
        
        try:
            logger.info("Setting up Echo Bike notification handlers...")
            
            # Indoor Bike Data characteristic UUID (standard FTMS UUID)
            indoor_bike_data_uuid = "00002AD2-0000-1000-8000-00805f9b34fb"
            
            # Define the notification callback
            def bike_data_notification_handler(sender, data):
                try:
                    # Log the raw data
                    logger.info(f"Received bike data notification: {data.hex()}")
                    
                    # Parse the data according to FTMS specification
                    if len(data) >= 2:  # Need at least 2 bytes for flags
                        # First 2 bytes are flags indicating which fields are present
                        flags_low = data[0]
                        flags_high = data[1]
                        flags = (flags_high << 8) | flags_low
                        logger.info(f"Flags: {flags:016b} (binary), 0x{flags:04x} (hex)")
                        
                        # Create a dictionary to store parsed values
                        parsed_data = {
                            "device_type": "bike",
                            "timestamp": datetime.datetime.now().isoformat()
                        }
                        
                        # Field presence flags (based on FTMS spec)
                        flag_more_data = bool(flags_low & 0x01)
                        flag_average_speed = bool(flags_low & 0x02)
                        flag_instantaneous_cadence = bool(flags_low & 0x04)
                        flag_average_cadence = bool(flags_low & 0x08)
                        flag_total_distance = bool(flags_low & 0x10)
                        flag_resistance_level = bool(flags_low & 0x20)
                        flag_instantaneous_power = bool(flags_low & 0x40)
                        flag_average_power = bool(flags_low & 0x80)
                        flag_expended_energy = bool(flags_high & 0x01)
                        flag_heart_rate = bool(flags_high & 0x02)
                        flag_metabolic_equivalent = bool(flags_high & 0x04)
                        flag_elapsed_time = bool(flags_high & 0x08)
                        flag_remaining_time = bool(flags_high & 0x10)
                        
                        logger.info(f"Field flags: speed={not flag_more_data}, avg_speed={flag_average_speed}, " +
                                   f"cadence={flag_instantaneous_cadence}, avg_cadence={flag_average_cadence}, " +
                                   f"distance={flag_total_distance}, resistance={flag_resistance_level}, " +
                                   f"power={flag_instantaneous_power}, avg_power={flag_average_power}, " +
                                   f"energy={flag_expended_energy}, heart_rate={flag_heart_rate}")
                        
                        # Parse data based on flags - follow the FTMS spec field ordering
                        offset = 2  # Start after the 2 bytes of flags
                        
                        # Instantaneous Speed (present if bit 0 is CLEAR per FTMS spec)
                        if not flag_more_data:
                            if offset + 2 <= len(data):
                                # Speed is in units of 0.01 km/h
                                inst_speed = int.from_bytes(data[offset:offset+2], byteorder='little') / 100.0
                                parsed_data["speed"] = inst_speed
                                logger.info(f"Speed: {inst_speed} km/h, bytes: {data[offset:offset+2].hex()}")
                                offset += 2
                        
                        # Average Speed (present if bit 1 is set)
                        if flag_average_speed:
                            if offset + 2 <= len(data):
                                # Speed is in units of 0.01 km/h
                                avg_speed = int.from_bytes(data[offset:offset+2], byteorder='little') / 100.0
                                parsed_data["average_speed"] = avg_speed
                                logger.info(f"Avg Speed: {avg_speed} km/h, bytes: {data[offset:offset+2].hex()}")
                                offset += 2
                        
                        # Instantaneous Cadence (present if bit 2 is set)
                        if flag_instantaneous_cadence:
                            if offset + 2 <= len(data):
                                # Cadence is in units of 0.5 rpm
                                inst_cadence = int.from_bytes(data[offset:offset+2], byteorder='little') / 2.0
                                parsed_data["cadence"] = inst_cadence
                                logger.info(f"Cadence: {inst_cadence} rpm, bytes: {data[offset:offset+2].hex()}")
                                offset += 2
                        
                        # Average Cadence (present if bit 3 is set)
                        if flag_average_cadence:
                            if offset + 2 <= len(data):
                                # Cadence is in units of 0.5 rpm
                                avg_cadence = int.from_bytes(data[offset:offset+2], byteorder='little') / 2.0
                                parsed_data["average_cadence"] = avg_cadence
                                logger.info(f"Avg Cadence: {avg_cadence} rpm, bytes: {data[offset:offset+2].hex()}")
                                offset += 2
                        
                        # Total Distance (present if bit 4 is set)
                        if flag_total_distance:
                            if offset + 3 <= len(data):
                                # Distance is in units of meters - UINT24 (3 bytes)
                                distance_bytes = data[offset:offset+3]
                                distance = int.from_bytes(distance_bytes, byteorder='little')
                                parsed_data["distance"] = distance
                                logger.info(f"Distance: {distance} meters, bytes: {distance_bytes.hex()}")
                                offset += 3
                        else:
                            logger.info("Distance flag not set in data packet")
                        
                        # Resistance Level (present if bit 5 is set)
                        if flag_resistance_level:
                            if offset + 2 <= len(data):
                                # Resistance level (implementation-specific units)
                                resistance = int.from_bytes(data[offset:offset+2], byteorder='little', signed=True)
                                parsed_data["resistance_level"] = resistance
                                logger.info(f"Resistance: {resistance}, bytes: {data[offset:offset+2].hex()}")
                                offset += 2
                        
                        # Instantaneous Power (present if bit 6 is set)
                        if flag_instantaneous_power:
                            if offset + 2 <= len(data):
                                # Power is in units of watts
                                inst_power = int.from_bytes(data[offset:offset+2], byteorder='little', signed=True)
                                parsed_data["power"] = inst_power
                                logger.info(f"Power: {inst_power} watts, bytes: {data[offset:offset+2].hex()}")
                                offset += 2
                        
                        # Average Power (present if bit 7 is set)
                        if flag_average_power:
                            if offset + 2 <= len(data):
                                # Power is in units of watts
                                avg_power = int.from_bytes(data[offset:offset+2], byteorder='little', signed=True)
                                parsed_data["average_power"] = avg_power
                                logger.info(f"Avg Power: {avg_power} watts, bytes: {data[offset:offset+2].hex()}")
                                offset += 2
                        
                        # Expended Energy (present if bit 8 is set)
                        if flag_expended_energy:
                            if offset + 5 <= len(data):
                                # Energy fields are 2+2+1 bytes
                                total_energy = int.from_bytes(data[offset:offset+2], byteorder='little')
                                energy_per_hour = int.from_bytes(data[offset+2:offset+4], byteorder='little')
                                energy_per_minute = data[offset+4]
                                
                                parsed_data["total_energy"] = total_energy
                                parsed_data["energy_per_hour"] = energy_per_hour
                                parsed_data["energy_per_minute"] = energy_per_minute
                                
                                logger.info(f"Energy: {total_energy} kcal, {energy_per_hour} kcal/h, {energy_per_minute} kcal/min")
                                offset += 5
                        
                        # Heart Rate (present if bit 9 is set)
                        if flag_heart_rate:
                            if offset + 1 <= len(data):
                                # Heart rate in BPM
                                heart_rate = data[offset]
                                parsed_data["heart_rate"] = heart_rate
                                logger.info(f"Heart Rate: {heart_rate} BPM, byte: {data[offset:offset+1].hex()}")
                                offset += 1
                        
                        # Metabolic Equivalent (present if bit 10 is set)
                        if flag_metabolic_equivalent:
                            if offset + 1 <= len(data):
                                # Metabolic equivalent
                                metabolic = data[offset] / 10.0
                                parsed_data["metabolic_equivalent"] = metabolic
                                logger.info(f"Metabolic Equivalent: {metabolic}, byte: {data[offset:offset+1].hex()}")
                                offset += 1
                        
                        # Elapsed Time (present if bit 11 is set)
                        if offset + 2 <= len(data):
                            # Elapsed time in seconds
                            elapsed = int.from_bytes(data[offset:offset+2], byteorder='little')
                            parsed_data["elapsed_time"] = elapsed
                            logger.info(f"Elapsed Time: {elapsed} seconds, bytes: {data[offset:offset+2].hex()}")
                            offset += 2
                        
                        # Remaining Time (present if bit 12 is set)
                        if flag_remaining_time:
                            if offset + 2 <= len(data):
                                # Remaining time in seconds
                                remaining = int.from_bytes(data[offset:offset+2], byteorder='little')
                                parsed_data["remaining_time"] = remaining
                                logger.info(f"Remaining Time: {remaining} seconds, bytes: {data[offset:offset+2].hex()}")
                                offset += 2
                        
                        # Log the final parsed data
                        logger.info(f"Parsed bike data: {parsed_data}")
                        
                        # Only notify if we have actual data (at least one value is non-None)
                        has_real_data = any(v is not None and v != 0 for k, v in parsed_data.items() 
                                          if k not in ["device_type", "timestamp"])
                        
                        if has_real_data:
                            # Notify data subscribers
                            self._notify_data(parsed_data)
                        else:
                            logger.debug(f"All data values are None or 0, skipping notification")
                    else:
                        logger.warning(f"Received data packet too small (need at least 2 bytes): {len(data)} bytes")
                except Exception as e:
                    logger.error(f"Error parsing bike data notification: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
            
            # Get the BLE client from the FTMS client
            ble_client = None
            if hasattr(self.ftms_client, 'client'):
                ble_client = self.ftms_client.client
            else:
                ble_client = self.ble_client
            
            # Set up notifications for Indoor Bike Data characteristic
            if ble_client:
                # Start notifications on the Indoor Bike Data characteristic
                try:
                    await ble_client.start_notify(indoor_bike_data_uuid, bike_data_notification_handler)
                    logger.info("Successfully started notifications for Indoor Bike Data")
                    self._notifications_set_up = True
                except Exception as e_notify:
                    logger.error(f"Error starting notifications: {e_notify}")
                    import traceback
                    logger.error(traceback.format_exc())
            else:
                logger.error("Cannot access BLE client for setting up notifications")
                
        except Exception as e:
            logger.error(f"Error setting up Echo Bike notifications: {e}")
            import traceback
            logger.error(traceback.format_exc())

async def main():
    connector = FTMSConnector()
    def my_data_callback(data):
        print(f"Received data: {datetime.datetime.now()} - {data}")
    def my_status_callback(status_type, data):
        print(f"Status update: {datetime.datetime.now()} - {status_type} - {data}")
        
    connector.register_data_callback(my_data_callback)
    connector.register_status_callback(my_status_callback)
    
    try:
        devices = await connector.discover_devices()
        if not devices:
            print("No FTMS devices found.")
            return
        
        print("Discovered devices:")
        device_list = list(devices.values())
        for i, dev_obj in enumerate(device_list):
            print(f"{i+1}. {dev_obj.name} ({dev_obj.address})")
        
        try:
            selection = input("Select device to connect (number): ")
            selected_index = int(selection) - 1
            if 0 <= selected_index < len(device_list):
                selected_address = device_list[selected_index].address
            else:
                print("Invalid selection."); return
        except ValueError:
            print("Invalid input."); return

        if await connector.connect(selected_address):
            print(f"Connected to {connector.connected_device_ble.name if connector.connected_device_ble else 'Unknown'}") # Corrected invalid character
            await asyncio.sleep(2) 
            print("Listening for data for 60 seconds... Press Ctrl+C to stop.")
            await asyncio.sleep(60)
        else:
            print("Failed to connect.")
            
    except asyncio.CancelledError:
        print("Main task cancelled.")
    except KeyboardInterrupt:
        print("Program terminated by user during main test.")
    except Exception as e:
        print(f"An error occurred in main: {e}")
    finally:
        pass

