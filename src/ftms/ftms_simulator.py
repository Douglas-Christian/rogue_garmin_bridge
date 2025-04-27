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
    
    This class is designed to be independent of the main application
    and only responsible for generating simulated device info and data.
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
        self.workout_active = False  # Track if a workout is active
        
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
            # Always notify status regardless
            self._notify_status("connected", self.device)
            return
        
        self.running = True
        self.start_time = time.time()
        self.workout_duration = 0
        
        # Notify status
        self._notify_status("connected", self.device)
        
        # Start the simulation task within a running event loop
        self._start_simulation_task()
        logger.info(f"Started {self.device_type} simulation")
    
    def _start_simulation_task(self) -> None:
        """
        Start the simulation task in a proper asyncio context.
        This handles task creation in a more robust way.
        """
        try:
            # Try to get the current event loop
            loop = asyncio.get_event_loop()
            
            # If the loop is closed or we're not in an event loop context,
            # create a new loop
            if loop.is_closed():
                asyncio.set_event_loop(asyncio.new_event_loop())
                loop = asyncio.get_event_loop()
        except RuntimeError:
            # Not in an event loop context, create a new one
            asyncio.set_event_loop(asyncio.new_event_loop())
            loop = asyncio.get_event_loop()
        
        # Clear any existing task to prevent resource leaks
        if hasattr(self, '_simulation_task') and self._simulation_task is not None:
            if not self._simulation_task.done() and not self._simulation_task.cancelled():
                self._simulation_task.cancel()
        
        # Create and store a reference to the task
        self._simulation_task = loop.create_task(self._simulation_loop())
        
        # Add a callback to handle task completion
        self._simulation_task.add_done_callback(self._on_simulation_task_done)
    
    def stop_simulation(self) -> None:
        """Stop the simulation."""
        if not self.running:
            logger.warning("Simulation not running")
            return
        
        self.running = False
        
        # Notify status
        self._notify_status("disconnected", self.device)
        logger.info("Stopped simulation")
    
    async def _simulation_loop(self) -> None:
        """Main simulation loop that generates data."""
        try:
            while self.running:
                try:
                    # Update workout duration
                    current_time = time.time()
                    if self.workout_active:
                        self.workout_duration = int(current_time - self.start_time)
                    
                    # Only generate and send data if a workout is active
                    if self.workout_active:
                        # Generate and send data
                        if self.device_type == "bike":
                            data = self._generate_bike_data()
                            logger.info(f"Generated bike data: power={data.get('instantaneous_power')}, cadence={data.get('instantaneous_cadence')}, distance={data.get('total_distance'):.2f}m, calories={data.get('total_calories')}")
                            self._notify_data(data)
                        else:  # rower
                            data = self._generate_rower_data()
                            logger.info(f"Generated rower data: power={data.get('instantaneous_power')}, stroke_rate={data.get('stroke_rate')}, distance={data.get('total_distance'):.2f}m, calories={data.get('total_calories')}")
                            self._notify_data(data)
                    else:
                        logger.debug(f"Workout not active, not generating data (running={self.running})")
                    
                    # Wait before next iteration
                    await asyncio.sleep(1)
                except asyncio.CancelledError:
                    logger.info("Simulation loop cancelled")
                    break
                except Exception as e:
                    logger.error(f"Error in simulation iteration: {str(e)}")
                    # Continue the loop if there's an error in a single iteration
                    await asyncio.sleep(1)
        except asyncio.CancelledError:
            logger.info("Simulation loop cancelled")
        except Exception as e:
            logger.error(f"Fatal error in simulation loop: {str(e)}")
        finally:
            # Ensure we mark as not running if we exit for any reason
            self.running = False
    
    def _generate_bike_data(self) -> Dict[str, Any]:
        """
        Generate simulated bike data with realistic variations over time.
        
        Returns:
            Dictionary of simulated bike data
        """
        # Define workout phases to create a more interesting pattern
        # Warmup → increasing intensity → steady state → intervals → cooldown
        workout_phase_duration = 60  # seconds per phase
        total_phases = 5
        
        # Determine current phase based on workout duration
        current_phase = min(int(self.workout_duration / workout_phase_duration), total_phases - 1)
        phase_time = self.workout_duration % workout_phase_duration
        phase_progress = phase_time / workout_phase_duration  # 0.0 to 1.0
        
        # Base values by phase
        if current_phase == 0:  # Warmup
            cadence_base = 60 + int(20 * phase_progress)  # 60-80 rpm
            power_base = 80 + int(70 * phase_progress)    # 80-150 watts
            speed_base = 15 + int(10 * phase_progress)    # 15-25 km/h
        elif current_phase == 1:  # Increasing intensity
            cadence_base = 80 + int(10 * phase_progress)  # 80-90 rpm
            power_base = 150 + int(50 * phase_progress)   # 150-200 watts
            speed_base = 25 + int(5 * phase_progress)     # 25-30 km/h
        elif current_phase == 2:  # Steady state
            cadence_base = 90                            # 90 rpm
            power_base = 200                             # 200 watts
            speed_base = 30                              # 30 km/h
        elif current_phase == 3:  # Intervals
            # Create interval pattern (high intensity/recovery)
            interval_period = 10  # seconds
            is_high_intensity = (phase_time % (interval_period * 2)) < interval_period
            
            if is_high_intensity:
                cadence_base = 100                       # 100 rpm
                power_base = 250                         # 250 watts
                speed_base = 35                          # 35 km/h
            else:
                cadence_base = 70                        # 70 rpm
                power_base = 120                         # 120 watts
                speed_base = 20                          # 20 km/h
        else:  # Cooldown
            cadence_base = 80 - int(30 * phase_progress)  # 80-50 rpm
            power_base = 150 - int(70 * phase_progress)   # 150-80 watts
            speed_base = 25 - int(10 * phase_progress)    # 25-15 km/h
            
        # Add random variations to make it feel natural
        cadence = max(0, cadence_base + random.randint(-5, 5))
        power = max(0, power_base + random.randint(-20, 20))
        speed = max(0, speed_base + random.randint(-3, 3))
        
        # Calculate cumulative distance (speed in km/h converted to m/s)
        speed_ms = speed / 3.6
        
        # We need to calculate just the distance for this second, not the cumulative distance
        # This is important for accurate accumulation over time
        distance_this_second = speed_ms  # meters covered in this second
        
        # Calculate calories (simplified)
        calories_this_second = power / 60  # rough estimate for 1 second
        
        # Heart rate simulation (with some lag behind power changes)
        target_hr = 60 + int(power * 0.6)  # Base HR calculation
        
        # Gradually approach target heart rate (simulating cardiovascular lag)
        prev_hr = getattr(self, '_prev_heart_rate', 100)  # Default to 100 if not set
        heart_rate = prev_hr + int((target_hr - prev_hr) * 0.1)  # 10% adjustment toward target
        heart_rate = min(max(heart_rate, 60), 200)  # Keep within reasonable bounds
        self._prev_heart_rate = heart_rate  # Store for next time
        
        # Store the incremental values for this second to report back
        self._last_distance = getattr(self, '_last_distance', 0) + distance_this_second
        self._last_calories = getattr(self, '_last_calories', 0) + calories_this_second
        
        return {
            'type': 'bike',
            'device_name': self.device.name,
            'device_address': self.device.address,
            'timestamp': self.workout_duration,
            'instantaneous_speed': speed_ms,  # in m/s
            'instantaneous_cadence': cadence,
            'instantaneous_power': power,
            'heart_rate': heart_rate,
            'elapsed_time': self.workout_duration,
            'total_distance': self._last_distance,
            'resistance_level': 8,
            'total_calories': int(self._last_calories),
            'workout_type': 'bike'
        }
    
    def _generate_rower_data(self) -> Dict[str, Any]:
        """
        Generate simulated rower data with realistic variations over time.
        
        Returns:
            Dictionary of simulated rower data
        """
        # Define workout phases to create a more interesting pattern
        # Warmup → steady state → intervals → steady state → cooldown
        workout_phase_duration = 60  # seconds per phase
        total_phases = 5
        
        # Determine current phase based on workout duration
        current_phase = min(int(self.workout_duration / workout_phase_duration), total_phases - 1)
        phase_time = self.workout_duration % workout_phase_duration
        phase_progress = phase_time / workout_phase_duration  # 0.0 to 1.0
        
        # Base values by phase
        if current_phase == 0:  # Warmup
            stroke_rate_base = 18 + int(7 * phase_progress)  # 18-25 spm
            power_base = 100 + int(80 * phase_progress)      # 100-180 watts
        elif current_phase == 1:  # Steady state
            stroke_rate_base = 25                            # 25 spm
            power_base = 180                                 # 180 watts
        elif current_phase == 2:  # Intervals
            # Create interval pattern (high intensity/recovery)
            interval_period = 10  # seconds
            is_high_intensity = (phase_time % (interval_period * 2)) < interval_period
            
            if is_high_intensity:
                stroke_rate_base = 30                        # 30 spm
                power_base = 250                             # 250 watts
            else:
                stroke_rate_base = 20                        # 20 spm
                power_base = 120                             # 120 watts
        elif current_phase == 3:  # Second steady state
            stroke_rate_base = 26                            # 26 spm
            power_base = 190                                 # 190 watts
        else:  # Cooldown
            stroke_rate_base = 25 - int(10 * phase_progress)  # 25-15 spm
            power_base = 180 - int(100 * phase_progress)      # 180-80 watts
            
        # Add random variations to make it feel natural
        stroke_rate = max(0, stroke_rate_base + random.randint(-2, 2))
        power = max(0, power_base + random.randint(-15, 15))
        
        # Calculate stroke count based on stroke rate and time
        stroke_count = int((stroke_rate / 60) * self.workout_duration)
        
        # Calculate speed (simplified)
        speed = 2.5 + (power / 200)  # rough estimate in m/s
        
        # We need to calculate just the distance for this second, not the cumulative distance
        # This is important for accurate accumulation over time
        distance_this_second = speed  # meters covered in this second
        
        # Calculate calories (simplified)
        calories_this_second = power / 60  # rough estimate for 1 second
        
        # Heart rate simulation (with some lag behind power changes)
        target_hr = 60 + int(power * 0.65)  # Base HR calculation (rowers tend to have higher HR than cycling)
        
        # Gradually approach target heart rate (simulating cardiovascular lag)
        prev_hr = getattr(self, '_prev_heart_rate_rower', 110)  # Default to 110 if not set
        heart_rate = prev_hr + int((target_hr - prev_hr) * 0.1)  # 10% adjustment toward target
        heart_rate = min(max(heart_rate, 60), 200)  # Keep within reasonable bounds
        self._prev_heart_rate_rower = heart_rate  # Store for next time
        
        # Store the incremental values for this second to report back
        self._last_distance_rower = getattr(self, '_last_distance_rower', 0) + distance_this_second
        self._last_calories_rower = getattr(self, '_last_calories_rower', 0) + calories_this_second
        
        return {
            'type': 'rower',
            'device_name': self.device.name,
            'device_address': self.device.address,
            'timestamp': self.workout_duration,
            'stroke_rate': stroke_rate,
            'stroke_count': stroke_count,
            'instantaneous_power': power,
            'instantaneous_speed': speed,
            'heart_rate': heart_rate,
            'elapsed_time': self.workout_duration,
            'total_distance': self._last_distance_rower,
            'total_calories': int(self._last_calories_rower),
            'workout_type': 'rower'
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
    
    def start_workout(self) -> None:
        """Start a workout on the simulated device."""
        if not self.running:
            logger.warning("Cannot start workout - simulator is not running")
            return
            
        logger.info(f"Starting workout on simulated {self.device_type}")
        self.workout_active = True
        self.start_time = time.time()  # Reset start time when workout begins
        self.workout_duration = 0
        
        # Reset accumulated metrics
        self._last_distance = 0
        self._last_calories = 0
        self._last_distance_rower = 0
        self._last_calories_rower = 0
        self._prev_heart_rate = 100
        self._prev_heart_rate_rower = 110
        
        # Generate initial data point immediately without waiting for loop
        if self.device_type == "bike":
            initial_data = self._generate_bike_data()
        else:
            initial_data = self._generate_rower_data()
            
        logger.info(f"Generated initial workout data point: {initial_data.get('type')}")
        self._notify_data(initial_data)
        
        # Notify that workout has started
        self._notify_status("workout_started", {
            "device": self.device,
            "workout_type": self.device_type
        })
    
    def end_workout(self) -> None:
        """End the current workout on the simulated device."""
        if not self.workout_active:
            logger.warning("No active workout to end")
            return
            
        logger.info(f"Ending workout on simulated {self.device_type}")
        self.workout_active = False
        
        # Notify that workout has ended
        self._notify_status("workout_ended", {
            "device": self.device,
            "workout_type": self.device_type,
            "duration": self.workout_duration
        })
    
    def _on_simulation_task_done(self, task: asyncio.Task) -> None:
        """
        Handle the completion of the simulation task.
        
        Args:
            task: The completed asyncio task
        """
        try:
            # Check if there's an exception
            if not task.cancelled() and task.exception():
                logger.error(f"Simulation task failed with exception: {task.exception()}")
                
                # Restart the simulation if it failed but should be running
                if self.running:
                    logger.info("Restarting simulation after error...")
                    self._start_simulation_task()
        except asyncio.CancelledError:
            logger.info("Simulation task was cancelled")
        except Exception as e:
            logger.error(f"Error handling simulation task completion: {str(e)}")
            
        # Ensure running flag is properly set if the task ended unexpectedly
        if self.running and not hasattr(self, '_simulation_task'):
            logger.warning("Simulation task ended unexpectedly, stopping simulation")
            self.running = False


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
