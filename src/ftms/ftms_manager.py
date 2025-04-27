#!/usr/bin/env python3
"""
FTMS Device Manager for Rogue to Garmin Bridge

This module provides a high-level interface for managing FTMS devices,
handling both real devices and simulated devices with a consistent API.
"""

import asyncio
import logging
import time
import random
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
        logger.info(f"Connecting to device: {device_address}")
        
        # Simple connection logic that works the same for both simulators and real devices
        if self.use_simulator:
            if device_address not in self.simulators:
                logger.error(f"Simulated device {device_address} not found")
                return False
            
            simulator = self.simulators[device_address]
            simulator.start_simulation()
            self.active_device = simulator
            logger.info(f"Connected to simulator: {device_address}")
            return True
        else:
            success = await self.connector.connect(device_address)
            if success:
                self.active_device = self.connector.connected_device
                logger.info(f"Connected to device: {device_address}")
            else:
                logger.error(f"Failed to connect to device: {device_address}")
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
            # Simple simulator disconnection
            for simulator in self.simulators.values():
                if hasattr(self.active_device, 'device') and hasattr(simulator.device, 'address'):
                    if simulator.device.address == self.active_device.device.address:
                        simulator.stop_simulation()
                        self.active_device = None
                        return True
            logger.error("Could not find matching simulator to disconnect")
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
        try:
            # Add a unique identifier for this data point if one doesn't exist
            if 'data_id' not in data:
                data['data_id'] = f"data_{time.time()}_{random.randint(1000, 9999)}"
                
            # Debug logging for data flow tracking
            logger.info(f"FTMS Manager received data: type={data.get('type', 'unknown')}, " +
                       f"timestamp={data.get('timestamp', 'N/A')}, " +
                       f"data_id={data.get('data_id', 'N/A')}")
                   
            # Ensure we have callbacks to forward to
            if not self.data_callbacks:
                logger.warning("No data callbacks registered with FTMS Manager!")
                return
            
            # Forward data to all registered callbacks
            success_count = 0
            for callback in self.data_callbacks:
                try:
                    callback_name = callback.__name__ if hasattr(callback, '__name__') else 'anonymous'
                    logger.debug(f"Forwarding data to callback: {callback_name}")
                    
                    # Create a copy of the data to avoid modifications affecting other callbacks
                    callback_data = data.copy()
                    callback(callback_data)
                    success_count += 1
                except Exception as e:
                    logger.error(f"Error in FTMS Manager data callback: {str(e)}", exc_info=True)
                    # Log full traceback for better debugging
                    import traceback
                    traceback.print_exc()
                    
            if success_count == 0:
                logger.error("No callbacks successfully processed the data!")
                
        except Exception as e:
            logger.error(f"Error in FTMS Manager _handle_data: {str(e)}", exc_info=True)
            import traceback
            traceback.print_exc()
    
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
    
    def notify_workout_start(self, workout_id: int, device_id: Optional[int] = None) -> None:
        """
        Notify the FTMS Manager that a workout has started.
        This will begin workout data generation in simulators or trigger appropriate commands on real devices.
        
        The workout_id is used to associate generated data with a specific workout in the database.
        For simulators, this activates the data generation loop. For real devices, this may involve
        sending commands to prepare the device for workout data collection.
        
        Args:
            workout_id: ID of the new workout to associate with generated data
            device_id: Optional ID of the device in the database (not used for simulation)
        
        Returns:
            None
        
        Raises:
            No exceptions are raised, but warnings are logged if no device is connected
        """
        if not self.active_device:
            logger.warning("Cannot start workout data - no device connected")
            return
            
        if self.use_simulator:
            logger.info(f"Starting workout {workout_id} on simulator")
            
            # Find the active simulator
            active_simulator = None
            
            # First check if active_device is directly a simulator
            if isinstance(self.active_device, FTMSDeviceSimulator):
                active_simulator = self.active_device
            else:
                # Look for a matching simulator by address
                for addr, simulator in self.simulators.items():
                    # Check different ways the address might be accessible
                    if hasattr(self.active_device, 'address') and simulator.device.address == self.active_device.address:
                        active_simulator = simulator
                        break
                    elif hasattr(self.active_device, 'device') and simulator.device.address == self.active_device.device.address:
                        active_simulator = simulator
                        break
            
            if active_simulator:
                # Set the active device to be the simulator directly for better reference
                self.active_device = active_simulator
                active_simulator.start_workout()
                logger.info(f"Started workout data generation for simulator: {active_simulator.device.name}")
            else:
                # If we get here, no matching simulator was found
                logger.error(f"Could not find matching simulator to start workout data generation")
        else:
            # For real devices, we'd send any necessary commands here
            logger.info(f"Workout {workout_id} started - continuing real device data stream")
    
    def notify_workout_end(self, workout_id: int) -> None:
        """
        Notify the FTMS Manager that a workout has ended.
        This will stop workout data generation in simulators or trigger appropriate commands on real devices.
        
        For simulators, this stops the data generation for the current workout by setting the workout_active
        flag to False. For real devices, this would send commands to stop data collection if necessary.
        
        This method is critical for proper cleanup and state management when workouts end.
        
        Args:
            workout_id: ID of the ended workout
        
        Returns:
            None
        
        Raises:
            No exceptions are raised, but warnings are logged if no device is connected
        """
        if not self.active_device:
            logger.warning("Cannot end workout data - no device connected")
            return
            
        if self.use_simulator:
            logger.info(f"Ending workout {workout_id} on simulator")
            
            # Find the active simulator
            active_simulator = None
            
            # Check if active_device is directly a simulator
            if isinstance(self.active_device, FTMSDeviceSimulator):
                active_simulator = self.active_device
            else:
                # Look for a matching simulator by address
                for addr, simulator in self.simulators.items():
                    # Check different ways the address might be accessible
                    if hasattr(self.active_device, 'address') and simulator.device.address == self.active_device.address:
                        active_simulator = simulator
                        break
                    elif hasattr(self.active_device, 'device') and simulator.device.address == self.active_device.device.address:
                        active_simulator = simulator
                        break
            
            if active_simulator:
                active_simulator.end_workout()
                logger.info(f"Ended workout data generation for simulator: {active_simulator.device.name}")
            else:
                # If we get here, no matching simulator was found
                logger.error(f"Could not find matching simulator to end workout data generation")
        else:
            # For real devices, we'd send any necessary commands here
            logger.info(f"Workout {workout_id} ended - continuing real device data stream")


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
