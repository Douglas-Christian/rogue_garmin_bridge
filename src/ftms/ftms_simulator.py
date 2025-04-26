#!/usr/bin/env python3
"""
FTMS Device Simulator for Rogue to Garmin Bridge

This module provides a simulator for FTMS devices to facilitate testing
without requiring physical Rogue Echo Bike and Rower equipment.
"""

import asyncio
import logging
import random
import time
from typing import Dict, Any, Optional, List, Callable

from bleak.backends.device import BLEDevice

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('ftms_simulator')

class FTMSDeviceSimulator:
    """
    Simulator for FTMS-compatible fitness equipment.
    Can simulate both Rogue Echo Bike and Rower.
    """
    
    def __init__(self, device_type: str = "bike"):
        """
        Initialize the FTMS device simulator.
        
        Args:
            device_type: Type of device to simulate ("bike" or "rower")
        """
        if device_type not in ["bike", "rower"]:
            raise ValueError("Device type must be 'bike' or 'rower'")
        
        self.device_type = device_type
        self.running = False
        self.data_callbacks: List[Callable[[Dict[str, Any]], None]] = []
        self.status_callbacks: List[Callable[[str, Any], None]] = []
        self.workout_duration = 0
        self.start_time = 0
        
        # Create a simulated BLE device
        self.device = self._create_simulated_device()
        
    def _create_simulated_device(self) -> BLEDevice:
        """
        Create a simulated BLE device object.
        
        Returns:
            Simulated BLE device
        """
        # This is a simplified representation - in a real environment,
        # we would need to mock the BLEDevice class more completely
        device_name = f"Rogue Echo {'Bike' if self.device_type == 'bike' else 'Rower'} (Simulated)"
        device_address = f"00:11:22:33:44:{random.randint(10, 99)}"
        
        # Create a dictionary with the necessary attributes
        device_dict = {
            "address": device_address,
            "name": device_name,
            "rssi": -60,
            "metadata": {"uuids": ["00001826-0000-1000-8000-00805f9b34fb"]}
        }
        
        # Create a BLEDevice-like object
        class SimulatedBLEDevice:
            def __init__(self, data):
                self.address = data["address"]
                self.name = data["name"]
                self.rssi = data["rssi"]
                self.metadata = data["metadata"]
                
            def __str__(self):
                return f"{self.name} ({self.address})"
        
        return SimulatedBLEDevice(device_dict)
    
    def register_data_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        Register a callback function to receive simulated FTMS data.
        
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
    
    def start_simulation(self) -> None:
        """Start the simulation."""
        if self.running:
            logger.warning("Simulation already running")
            return
        
        self.running = True
        self.start_time = time.time()
        self.workout_duration = 0
        
        # Notify status
        self._notify_status("connected", self.device)
        self._notify_status("machine_status", {"status": "ready"})
        
        # Start the simulation task
        asyncio.create_task(self._simulation_loop())
        logger.info(f"Started {self.device_type} simulation")
    
    def stop_simulation(self) -> None:
        """Stop the simulation."""
        if not self.running:
            logger.warning("Simulation not running")
            return
        
        self.running = False
        self._notify_status("disconnected", self.device)
        logger.info("Stopped simulation")
    
    async def _simulation_loop(self) -> None:
        """Main simulation loop that generates data."""
        try:
            while self.running:
                # Update workout duration
                self.workout_duration = int(time.time() - self.start_time)
                
                # Generate and send data
                if self.device_type == "bike":
                    data = self._generate_bike_data()
                    self._notify_data(data)
                else:  # rower
                    data = self._generate_rower_data()
                    self._notify_data(data)
                
                # Wait before sending next data point
                await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"Error in simulation loop: {str(e)}")
            self.running = False
    
    def _generate_bike_data(self) -> Dict[str, Any]:
        """
        Generate simulated bike data.
        
        Returns:
            Dictionary of simulated bike data
        """
        # Base values
        cadence_base = 80
        power_base = 150
        speed_base = 25
        
        # Add some variation
        cadence = max(0, cadence_base + random.randint(-5, 5))
        power = max(0, power_base + random.randint(-20, 20))
        speed = max(0, speed_base + random.randint(-3, 3))
        
        # Calculate distance based on speed and time
        distance = (speed / 3.6) * self.workout_duration  # speed in km/h, distance in meters
        
        # Calculate calories (simplified)
        calories = int(power * self.workout_duration / 60)  # rough estimate
        
        # Heart rate simulation
        heart_rate = 110 + int(power / 10) + random.randint(-5, 5)
        heart_rate = min(max(heart_rate, 60), 200)  # Keep within reasonable bounds
        
        return {
            'type': 'bike',
            'timestamp': self.workout_duration,
            'instantaneous_speed': speed,
            'instantaneous_cadence': cadence,
            'instantaneous_power': power,
            'heart_rate': heart_rate,
            'elapsed_time': self.workout_duration,
            'total_distance': distance,
            'resistance_level': 8,
            'total_energy': calories
        }
    
    def _generate_rower_data(self) -> Dict[str, Any]:
        """
        Generate simulated rower data.
        
        Returns:
            Dictionary of simulated rower data
        """
        # Base values
        stroke_rate_base = 25
        power_base = 180
        
        # Add some variation
        stroke_rate = max(0, stroke_rate_base + random.randint(-3, 3))
        power = max(0, power_base + random.randint(-20, 20))
        
        # Calculate stroke count based on stroke rate and time
        stroke_count = int((stroke_rate / 60) * self.workout_duration)
        
        # Calculate distance (simplified)
        distance = 5 * self.workout_duration  # rough estimate, 5 meters per second
        
        # Calculate calories (simplified)
        calories = int(power * self.workout_duration / 60)  # rough estimate
        
        # Heart rate simulation
        heart_rate = 120 + int(power / 10) + random.randint(-5, 5)
        heart_rate = min(max(heart_rate, 60), 200)  # Keep within reasonable bounds
        
        return {
            'type': 'rower',
            'timestamp': self.workout_duration,
            'stroke_rate': stroke_rate,
            'stroke_count': stroke_count,
            'instantaneous_power': power,
            'heart_rate': heart_rate,
            'elapsed_time': self.workout_duration,
            'total_distance': distance,
            'total_energy': calories
        }
    
    def _notify_data(self, data: Dict[str, Any]) -> None:
        """
        Notify all registered data callbacks with new data.
        
        Args:
            data: Dictionary of simulated FTMS data
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
    """Example usage of the FTMSDeviceSimulator class."""
    # Create a bike simulator
    bike_simulator = FTMSDeviceSimulator(device_type="bike")
    
    # Define callbacks
    def data_callback(data):
        print(f"Received data: {data}")
    
    def status_callback(status, data):
        print(f"Status update: {status} - {data}")
    
    # Register callbacks
    bike_simulator.register_data_callback(data_callback)
    bike_simulator.register_status_callback(status_callback)
    
    # Start simulation
    bike_simulator.start_simulation()
    
    # Run for 30 seconds
    await asyncio.sleep(30)
    
    # Stop simulation
    bike_simulator.stop_simulation()


if __name__ == "__main__":
    asyncio.run(main())
