#!/usr/bin/env python3
"""
FTMS Connector Module for Rogue to Garmin Bridge

This module handles Bluetooth Low Energy (BLE) connections to Rogue Echo Bike and Rower
equipment using the FTMS (Fitness Machine Service) standard.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Callable, Any

import bleak
from bleak import BleakScanner, BleakClient
from bleak.backends.device import BLEDevice
from pycycling.fitness_machine_service import FitnessMachineService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('ftms_connector')

# FTMS UUIDs
FTMS_SERVICE_UUID = "00001826-0000-1000-8000-00805f9b34fb"
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
        
        # Define a detection callback that filters for FTMS devices
        def detection_callback(device: BLEDevice, advertisement_data):
            if FTMS_SERVICE_UUID.lower() in [str(uuid).lower() for uuid in advertisement_data.service_uuids]:
                logger.info(f"Found FTMS device: {device.name} ({device.address})")
                self.devices[device.address] = device
                self._notify_status("device_found", device)
            elif device.name and ROGUE_MANUFACTURER_NAME.lower() in device.name.lower():
                # Also include devices with Rogue in the name even if they don't advertise FTMS
                logger.info(f"Found potential Rogue device: {device.name} ({device.address})")
                self.devices[device.address] = device
                self._notify_status("device_found", device)
        
        # Start scanning with the callback
        scanner = BleakScanner(detection_callback=detection_callback)
        await scanner.start()
        await asyncio.sleep(timeout)
        await scanner.stop()
        
        logger.info(f"Discovered {len(self.devices)} FTMS devices")
        return self.devices
    
    async def connect(self, device_address: str) -> bool:
        """
        Connect to a specific FTMS device.
        
        Args:
            device_address: BLE address of the device to connect to
            
        Returns:
            True if connection successful, False otherwise
        """
        if device_address not in self.devices:
            logger.error(f"Device {device_address} not found in discovered devices")
            self._notify_status("connection_error", "Device not found")
            return False
        
        device = self.devices[device_address]
        logger.info(f"Connecting to {device.name} ({device.address})...")
        self._notify_status("connecting", device)
        
        try:
            # Disconnect if already connected
            if self.client and self.client.is_connected:
                await self.disconnect()
            
            # Connect to the device
            self.client = BleakClient(device)
            await self.client.connect()
            
            # Initialize FTMS service
            self.ftms = FitnessMachineService(self.client)
            await self.ftms.enable_notifications()
            
            # Set up callbacks for FTMS data
            self.ftms.set_indoor_bike_data_handler(self._handle_indoor_bike_data)
            self.ftms.set_rower_data_handler(self._handle_rower_data)
            self.ftms.set_fitness_machine_status_handler(self._handle_fitness_machine_status)
            
            self.connected_device = device
            logger.info(f"Connected to {device.name} ({device.address})")
            self._notify_status("connected", device)
            return True
            
        except Exception as e:
            logger.error(f"Error connecting to device: {str(e)}")
            self._notify_status("connection_error", str(e))
            return False
    
    async def disconnect(self) -> bool:
        """
        Disconnect from the current FTMS device.
        
        Returns:
            True if disconnection successful, False otherwise
        """
        if not self.client:
            logger.warning("No device connected")
            return False
        
        try:
            await self.client.disconnect()
            logger.info(f"Disconnected from {self.connected_device.name if self.connected_device else 'device'}")
            self._notify_status("disconnected", self.connected_device)
            self.client = None
            self.ftms = None
            self.connected_device = None
            return True
            
        except Exception as e:
            logger.error(f"Error disconnecting: {str(e)}")
            self._notify_status("disconnection_error", str(e))
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
    
    def _handle_indoor_bike_data(self, data: Dict[str, Any]) -> None:
        """
        Handle indoor bike data from FTMS.
        
        Args:
            data: Dictionary of bike data
        """
        logger.debug(f"Received indoor bike data: {data}")
        self._notify_data({
            'type': 'bike',
            'timestamp': data.get('instantaneous_speed_present', 0),
            'speed': data.get('instantaneous_speed', 0),
            'cadence': data.get('instantaneous_cadence', 0),
            'power': data.get('instantaneous_power', 0),
            'heart_rate': data.get('heart_rate', 0),
            'elapsed_time': data.get('elapsed_time', 0),
            'distance': data.get('total_distance', 0),
            'resistance_level': data.get('resistance_level', 0),
            'calories': data.get('total_energy', 0),
            **data  # Include all original data
        })
    
    def _handle_rower_data(self, data: Dict[str, Any]) -> None:
        """
        Handle rower data from FTMS.
        
        Args:
            data: Dictionary of rower data
        """
        logger.debug(f"Received rower data: {data}")
        self._notify_data({
            'type': 'rower',
            'timestamp': data.get('elapsed_time', 0),
            'stroke_rate': data.get('stroke_rate', 0),
            'stroke_count': data.get('stroke_count', 0),
            'power': data.get('instantaneous_power', 0),
            'heart_rate': data.get('heart_rate', 0),
            'elapsed_time': data.get('elapsed_time', 0),
            'distance': data.get('total_distance', 0),
            'calories': data.get('total_energy', 0),
            **data  # Include all original data
        })
    
    def _handle_fitness_machine_status(self, data: Dict[str, Any]) -> None:
        """
        Handle fitness machine status updates.
        
        Args:
            data: Dictionary of status data
        """
        logger.debug(f"Received fitness machine status: {data}")
        self._notify_status("machine_status", data)
    
    def _notify_data(self, data: Dict[str, Any]) -> None:
        """
        Notify all registered data callbacks with new data.
        
        Args:
            data: Dictionary of FTMS data
        """
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
        for callback in self.status_callbacks:
            try:
                callback(status, data)
            except Exception as e:
                logger.error(f"Error in status callback: {str(e)}")


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
