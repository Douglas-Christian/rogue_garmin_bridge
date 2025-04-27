"""
FTMS Device Simulator for Rogue to Garmin Bridge

This module provides a simulator for FTMS devices to facilitate testing
without requiring physical Rogue Echo Bike and Rower equipment.
"""

import asyncio
import logging
import random
import time
from typing import Dict, List, Any, Optional, Callable
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
        
        # Accumulated metrics
        self.total_distance = 0.0
        self.total_calories = 0
        
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
        
        # Reset accumulated metrics
        self.total_distance = 0.0
        self.total_calories = 0
        
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
    
    def _on_simulation_task_done(self, task):
        """Handle simulation task completion."""
        try:
            # Get the result to propagate any exceptions
            task.result()
        except asyncio.CancelledError:
            logger.info("Simulation task was cancelled")
        except Exception as e:
            logger.error(f"Simulation task failed with error: {str(e)}")
    
    def stop_simulation(self) -> None:
        """Stop the simulation."""
        if not self.running:
            logger.warning("Simulation not running")
            return
        
        self.running = False
        self.workout_active = False  # Ensure workout is marked as inactive
        
        # Notify status
        self._notify_status("disconnected", self.device)
        
        logger.info("Stopped simulation")
    
    # Add this method to handle workout start
    def start_workout(self) -> None:
        """Start a workout session in the simulator."""
        logger.info(f"Starting workout in {self.device_type} simulator")
        self.workout_active = True
        self.start_time = time.time()
        self.workout_duration = 0
        
        # Reset accumulated metrics
        self.total_distance = 0.0
        self.total_calories = 0
        
        # Notify status
        self._notify_status("workout_started", {
            "device": self.device,
            "workout_active": True
        })
    
    # Add this method to handle workout end
    def end_workout(self) -> None:
        """End a workout session in the simulator."""
        logger.info(f"Ending workout in {self.device_type} simulator")
        self.workout_active = False
        
        # Notify status
        self._notify_status("workout_ended", {
            "device": self.device,
            "workout_active": False,
            "duration": int(time.time() - self.start_time)
        })
    
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
                            logger.info(f"Generated bike data: power={data.get('instantaneous_power')}, "
                                       f"cadence={data.get('instantaneous_cadence')}, "
                                       f"distance={data.get('total_distance'):.2f}m, "
                                       f"calories={data.get('total_calories')}")
                            self._notify_data(data)
                        else:  # rower
                            data = self._generate_rower_data()
                            logger.info(f"Generated rower data: power={data.get('instantaneous_power')}, "
                                       f"stroke_rate={data.get('stroke_rate')}, "
                                       f"distance={data.get('total_distance'):.2f}m, "
                                       f"calories={data.get('total_calories')}")
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
            power_base = 80 + int(70 * phase_progress)  # 80-150 watts
            speed_base = 15 + int(10 * phase_progress)  # 15-25 km/h
        elif current_phase == 1:  # Increasing intensity
            cadence_base = 80 + int(10 * phase_progress)  # 80-90 rpm
            power_base = 150 + int(50 * phase_progress)  # 150-200 watts
            speed_base = 25 + int(5 * phase_progress)  # 25-30 km/h
        elif current_phase == 2:  # Steady state
            cadence_base = 90  # 90 rpm
            power_base = 200  # 200 watts
            speed_base = 30  # 30 km/h
        elif current_phase == 3:  # Intervals
            # Create interval pattern (high intensity/recovery)
            interval_period = 10  # seconds
            is_high_intensity = (phase_time % (interval_period * 2)) < interval_period
            
            if is_high_intensity:
                cadence_base = 100  # 100 rpm
                power_base = 250  # 250 watts
                speed_base = 35  # 35 km/h
            else:
                cadence_base = 70  # 70 rpm
                power_base = 120  # 120 watts
                speed_base = 20  # 20 km/h
        else:  # Cooldown
            cadence_base = 80 - int(20 * phase_progress)  # 80-60 rpm
            power_base = 150 - int(70 * phase_progress)  # 150-80 watts
            speed_base = 25 - int(10 * phase_progress)  # 25-15 km/h
        
        # Add some random variation
        cadence = max(0, cadence_base + random.randint(-5, 5))
        power = max(0, power_base + random.randint(-10, 10))
        speed = max(0, speed_base + random.uniform(-1.0, 1.0))
        
        # Calculate distance increment (speed in km/h → m/s → m)
        # 1 km/h = 0.277778 m/s
        speed_ms = speed * 0.277778
        distance_increment = speed_ms * 1.0  # 1 second since last update
        
        # Update total distance
        self.total_distance += distance_increment
        
        # Calculate calories increment (very simplified)
        # Assuming ~4 calories per minute per 100 watts
        calories_per_hour = power * 0.04 * 60
        calories_per_second = calories_per_hour / 3600  # per second
        
        # Accumulate calories (non-decreasing)
        # Store as a running total and ensure it only increases
        calories_accumulated = self.workout_duration * calories_per_second
        self.total_calories = max(self.total_calories, int(calories_accumulated))
        
        # Calculate heart rate (simplified model)
        # Assume heart rate correlates with power
        heart_rate_base = 60 + (power / 3)
        heart_rate = min(220, int(heart_rate_base + random.randint(-5, 5)))
        
        # Create data packet
        data = {
            "type": "bike",  # Add workout type to the data
            "instantaneous_power": power,
            "instantaneous_cadence": cadence,
            "instantaneous_speed": speed,
            "heart_rate": heart_rate,
            "total_distance": self.total_distance,  # Use accumulated value
            "total_calories": self.total_calories,  # Use accumulated value
            "timestamp": self.workout_duration,
            "elapsed_time": self.workout_duration  # Add elapsed time for UI
        }
        
        return data
    
    def _generate_rower_data(self) -> Dict[str, Any]:
        """
        Generate simulated rower data with realistic variations over time.
        
        Returns:
            Dictionary of simulated rower data
        """
        # Define workout phases similar to bike
        workout_phase_duration = 60  # seconds per phase
        total_phases = 5
        
        # Determine current phase based on workout duration
        current_phase = min(int(self.workout_duration / workout_phase_duration), total_phases - 1)
        phase_time = self.workout_duration % workout_phase_duration
        phase_progress = phase_time / workout_phase_duration  # 0.0 to 1.0
        
        # Base values by phase
        if current_phase == 0:  # Warmup
            stroke_rate_base = 18 + int(6 * phase_progress)  # 18-24 spm
            power_base = 100 + int(50 * phase_progress)  # 100-150 watts
            speed_base = 2.0 + 0.5 * phase_progress  # 2.0-2.5 m/s
        elif current_phase == 1:  # Increasing intensity
            stroke_rate_base = 24 + int(4 * phase_progress)  # 24-28 spm
            power_base = 150 + int(50 * phase_progress)  # 150-200 watts
            speed_base = 2.5 + 0.3 * phase_progress  # 2.5-2.8 m/s
        elif current_phase == 2:  # Steady state
            stroke_rate_base = 28  # 28 spm
            power_base = 200  # 200 watts
            speed_base = 2.8  # 2.8 m/s
        elif current_phase == 3:  # Intervals
            # Create interval pattern (high intensity/recovery)
            interval_period = 10  # seconds
            is_high_intensity = (phase_time % (interval_period * 2)) < interval_period
            
            if is_high_intensity:
                stroke_rate_base = 32  # 32 spm
                power_base = 250  # 250 watts
                speed_base = 3.2  # 3.2 m/s
            else:
                stroke_rate_base = 20  # 20 spm
                power_base = 120  # 120 watts
                speed_base = 2.2  # 2.2 m/s
        else:  # Cooldown
            stroke_rate_base = 24 - int(6 * phase_progress)  # 24-18 spm
            power_base = 150 - int(50 * phase_progress)  # 150-100 watts
            speed_base = 2.5 - 0.5 * phase_progress  # 2.5-2.0 m/s
        
        # Add some random variation
        stroke_rate = max(0, stroke_rate_base + random.randint(-2, 2))
        power = max(0, power_base + random.randint(-10, 10))
        speed = max(0, speed_base + random.uniform(-0.1, 0.1))
        
        # Calculate distance increment (m/s → m)
        distance_increment = speed * 1.0  # 1 second since last update
        
        # Update total distance
        self.total_distance += distance_increment
        
        # Calculate calories increment (very simplified)
        # Assuming ~5 calories per minute per 100 watts for rowing
        calories_per_hour = power * 0.05 * 60
        calories_per_second = calories_per_hour / 3600  # per second
        
        # Accumulate calories (non-decreasing)
        # Store as a running total and ensure it only increases
        calories_accumulated = self.workout_duration * calories_per_second
        self.total_calories = max(self.total_calories, int(calories_accumulated))
        
        # Calculate heart rate (simplified model)
        # Assume heart rate correlates with power
        heart_rate_base = 60 + (power / 2.5)
        heart_rate = min(220, int(heart_rate_base + random.randint(-5, 5)))
        
        # Calculate total strokes
        strokes = int(self.workout_duration * stroke_rate / 60)
        
        # Create data packet
        data = {
            "type": "rower",  # Add workout type to the data
            "instantaneous_power": power,
            "stroke_rate": stroke_rate,
            "heart_rate": heart_rate,
            "total_distance": self.total_distance,  # Use accumulated value
            "total_calories": self.total_calories,  # Use accumulated value
            "total_strokes": strokes,
            "timestamp": self.workout_duration,
            "elapsed_time": self.workout_duration  # Add elapsed time for UI
        }
        
        return data
    
    def _notify_data(self, data: Dict[str, Any]) -> None:
        """
        Notify all registered data callbacks with new data.
        
        Args:
            data: Dictionary of FTMS data
        """
        logger.debug(f"Simulator generating data: {data}")
        if len(self.data_callbacks) == 0:
            logger.warning("No data callbacks registered with simulator!")
            
        for callback in self.data_callbacks:
            try:
                logger.debug(f"Calling data callback: {callback.__name__ if hasattr(callback, '__name__') else 'anonymous'}")
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
        if len(self.status_callbacks) == 0:
            logger.warning("No status callbacks registered with simulator!")
            
        for callback in self.status_callbacks:
            try:
                logger.debug(f"Calling status callback: {callback.__name__ if hasattr(callback, '__name__') else 'anonymous'}")
                callback(status, data)
            except Exception as e:
                logger.error(f"Error in status callback: {str(e)}")


# Example usage
if __name__ == "__main__":
    # Create a bike simulator
    bike_simulator = FTMSDeviceSimulator(device_type="bike")
    
    # Define a callback function
    def data_callback(data):
        print(f"Received data: {data}")
    
    def status_callback(status, data):
        print(f"Status update: {status}")
    
    # Register callbacks
    bike_simulator.register_data_callback(data_callback)
    bike_simulator.register_status_callback(status_callback)
    
    # Start the simulation
    bike_simulator.start_simulation()
    
    # Start a workout
    bike_simulator.start_workout()
    
    # Run for a while
    try:
        import time
        time.sleep(10)
    finally:
        # End the workout
        bike_simulator.end_workout()
        
        # Stop the simulation
        bike_simulator.stop_simulation()