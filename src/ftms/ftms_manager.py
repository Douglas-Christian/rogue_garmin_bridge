#!/usr/bin/env python3
"""
FTMS Device Manager for Rogue to Garmin Bridge

This module provides a high-level interface for managing FTMS devices,
handling both real devices and simulated devices with a consistent API.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Callable, Any, Union

from bleak.backends.device import BLEDevice

from .ftms_connector import FTMSConnector
from .ftms_simulator import FTMSDeviceSimulator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('ftms_manager')

class FTMSDeviceManager:
    """
    Manager class for FTMS devices, providing a unified interface for
    both real and simulated devices.
    """
    
    def __init__(self, use_simulator: bool = False):
        """
        Initialize the FTMS device manager.
        
        Args:
            use_simulator: Whether to use simulated devices instead of real ones
        """
        self.use_simulator = use_simulator
        self.connector = FTMSConnector() if not use_simulator else None
        self.simulators: Dict[str, FTMSDeviceSimulator] = {}
        self.active_device: Optional[Union[BLEDevice, FTMSDeviceSimulator]] = None
        self.data_callbacks: List[Callable[[Dict[str, Any]], None]] = []
        self.status_callbacks: List[Callable[[str, Any], None]] = []
        
        # Register callbacks if using real connector
        if self.connector:
            self.connector.register_data_callback(self._handle_data)
            self.connector.register_status_callback(self._handle_status)
    
    async def discover_devices(self, timeout: int = 5) -> Dict[str, Any]:
        """
        Discover FTMS devices.
        
        Args:
            timeout: Scan timeout in seconds (only used for real devices)
            
        Returns:
            Dictionary of discovered devices
        """
        if self.use_simulator:
            # Create simulated devices
            bike_simulator = FTMSDeviceSimulator(device_type="bike")
            rower_simulator = FTMSDeviceSimulator(device_type="rower")
            
            # Register callbacks
            bike_simulator.register_data_callback(self._handle_data)
            bike_simulator.register_status_callback(self._handle_status)
            rower_simulator.register_data_callback(self._handle_data)
            rower_simulator.register_status_callback(self._handle_status)
            
            # Store simulators
            self.simulators = {
                bike_simulator.device.address: bike_simulator,
                rower_simulator.device.address: rower_simulator
            }
            
            # Return simulated devices
            return {
                bike_simulator.device.address: bike_simulator.device,
                rower_simulator.device.address: rower_simulator.device
            }
        else:
            # Discover real devices
            return await self.connector.discover_devices(timeout)
    
    async def connect(self, device_address: str) -> bool:
        """
        Connect to a specific FTMS device.
        
        Args:
            device_address: BLE address of the device to connect to
            
        Returns:
            True if connection successful, False otherwise
        """
        if self.use_simulator:
            if device_address not in self.simulators:
                logger.error(f"Simulated device {device_address} not found")
                return False
            
            simulator = self.simulators[device_address]
            simulator.start_simulation()
            self.active_device = simulator
            return True
        else:
            success = await self.connector.connect(device_address)
            if success:
                self.active_device = self.connector.connected_device
            return success
    
    async def disconnect(self) -> bool:
        """
        Disconnect from the current FTMS device.
        
        Returns:
            True if disconnection successful, False otherwise
        """
        if not self.active_device:
            logger.warning("No device connected")
            return False
        
        if self.use_simulator:
            for simulator in self.simulators.values():
                if simulator.device.address == self.active_device.address:
                    simulator.stop_simulation()
                    self.active_device = None
                    return True
            return False
        else:
            success = await self.connector.disconnect()
            if success:
                self.active_device = None
            return success
    
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
    
    def _handle_data(self, data: Dict[str, Any]) -> None:
        """
        Handle data from FTMS devices and forward to registered callbacks.
        
        Args:
            data: Dictionary of FTMS data
        """
        for callback in self.data_callbacks:
            try:
                callback(data)
            except Exception as e:
                logger.error(f"Error in data callback: {str(e)}")
    
    def _handle_status(self, status: str, data: Any) -> None:
        """
        Handle status updates from FTMS devices and forward to registered callbacks.
        
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
    """Example usage of the FTMSDeviceManager class."""
    # Create a device manager with simulator
    manager = FTMSDeviceManager(use_simulator=True)
    
    # Define callbacks
    def data_callback(data):
        print(f"Received data: {data}")
    
    def status_callback(status, data):
        print(f"Status update: {status} - {data}")
    
    # Register callbacks
    manager.register_data_callback(data_callback)
    manager.register_status_callback(status_callback)
    
    # Discover devices
    devices = await manager.discover_devices()
    
    if devices:
        # Connect to the first device found
        device_address = list(devices.keys())[0]
        await manager.connect(device_address)
        
        # Keep the connection open for 30 seconds
        await asyncio.sleep(30)
        
        # Disconnect
        await manager.disconnect()
    else:
        print("No FTMS devices found")


if __name__ == "__main__":
    asyncio.run(main())
