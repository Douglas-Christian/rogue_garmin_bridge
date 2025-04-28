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
FTMS_INDOOR_BIKE_DATA_UUID = "00002ad2-0000-1000-8000-00805f9b34fb" # Added Indoor Bike Data UUID
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
                    
                    # --- Add Logging ---
                    logger.info("Setting FTMS data handlers...")
                    # --- End Add Logging ---

                    # --- Add Notification Enabling for Bike and Status ---
                    try:
                        logger.info("Attempting to enable FTMS notifications...")
                        # Enable notifications for indoor bike data
                        await self.ftms.enable_indoor_bike_data_notify()
                        # Enable fitness machine status notifications
                        await self.ftms.enable_fitness_machine_status_notify()
                        logger.info("FTMS notifications enabled successfully.")
                    except AttributeError as ae:
                        logger.warning(f"AttributeError enabling notifications: {ae}. Trying generic approach (might fail).")
                        try:
                            # Fallback specifically for indoor bike data
                            await self.client.start_notify(FTMS_INDOOR_BIKE_DATA_UUID, self._handle_raw_notification)
                            logger.info("Fallback notification attempt initiated for Indoor Bike Data.")
                        except Exception as fallback_exc:
                            logger.error(f"Fallback notification attempt failed: {fallback_exc}")
                    except Exception as notify_exc:
                        logger.warning(f"Could not explicitly enable FTMS notifications: {notify_exc}. Data might still be received.")
                    # --- End Notification Enabling ---

                    # Set up data handlers for bike and status
                    self.ftms.set_indoor_bike_data_handler(self._handle_indoor_bike_data)
                    self.ftms.set_fitness_machine_status_handler(self._handle_fitness_machine_status)
                    
                    # --- Add Logging ---
                    logger.info("FTMS data handlers set.")
                    # --- End Add Logging ---

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
                
            logger.debug(f"Received fitness machine status: {data}")
            self._notify_status("machine_status", data)
            
        except Exception as e:
            logger.error(f"Error processing fitness machine status: {str(e)}")
    
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

    def _handle_raw_notification(self, sender, data):
        """Placeholder handler for raw notifications (used in fallback)."""
        logger.warning(f"Received raw notification from {sender}: {data.hex()}")
        # Basic parsing attempt or logging needed here if fallback is used
        pass
        
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
