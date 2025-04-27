"""
FTMS Device Simulator for Rogue to Garmin Bridge

This module provides a simulator for FTMS devices to facilitate testing
without requiring physical Rogue Echo Bike and Rower equipment.
"""

import asyncio
import random
import time
from typing import Dict, List, Any, Optional, Callable
from bleak.backends.device import BLEDevice
from src.utils.logging_config import get_component_logger

# Get logger from centralized logging system
logger = get_component_logger('ftms')

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
        
        # Force DEBUG level for simulator
        logger.setLevel("DEBUG")
        
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
    
    def discover_devices(self):
        """
        Discover simulated FTMS devices.
        
        Returns:
            Dictionary with the simulated device(s)
        """
        logger.info("Discovering simulated FTMS devices")
        
        # Return a JSON-serializable dictionary representation of the device
        devices = {
            self.device.address: {
                "address": self.device.address,
                "name": self.device.name,
                "rssi": self.device.rssi,
                "metadata": self.device.metadata
            }
        }
        
        return devices
    
    def discover_devices_sync(self):
        """
        Synchronous version of discover_devices for better compatibility.
        
        Returns:
            Dictionary with the simulated device(s)
        """
        return self.discover_devices()
        
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
        logger.info("Starting simulation task for generating workout data")
        try:
            # Try to get the current event loop
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                # No event loop found in this thread, create a new one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                logger.info("Created new event loop for simulation")
            
            # If the loop is closed, create a new one
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                logger.info("Created new event loop (previous was closed)")
            
            # Clear any existing task to prevent resource leaks
            if hasattr(self, '_simulation_task') and self._simulation_task is not None:
                if not self._simulation_task.done() and not self._simulation_task.cancelled():
                    self._simulation_task.cancel()
                    logger.info("Cancelled existing simulation task")
            
            # Create a dedicated thread for the simulation if we're not in an event loop
            # This is a more robust approach for non-async environments
            def run_event_loop():
                logger.info("Starting dedicated simulation thread")
                # Set the event loop for this thread
                asyncio.set_event_loop(loop)
                # Run the loop
                loop.run_forever()
                
            # Create and start the thread
            import threading
            self._loop_thread = threading.Thread(target=run_event_loop, daemon=True)
            self._loop_thread.start()
            logger.info("Started simulation thread")
            
            # Create and store a reference to the task
            self._simulation_task = asyncio.run_coroutine_threadsafe(self._simulation_loop(), loop)
            logger.info("Created simulation task in separate thread")
            
            # Add a callback to handle task completion
            self._simulation_task.add_done_callback(self._on_simulation_task_done)
            
        except Exception as e:
            logger.error(f"Error starting simulation task: {str(e)}", exc_info=True)
            import traceback
            traceback.print_exc()
    
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
    
    def start_workout(self) -> None:
        """
        Start a workout session in the simulator.
        
        This method activates the workout data generation in the simulator by:
        1. Setting the workout_active flag to True
        2. Resetting the workout start time and duration
        3. Resetting all accumulated metrics (distance, calories, etc.)
        4. Generating and sending an initial data point immediately
        5. Notifying status callbacks of workout start
        
        After this method is called, the simulator will begin generating workout
        data points at regular intervals (typically every second) until end_workout()
        is called or the simulation is stopped.
        
        Returns:
            None
        """
        logger.info(f"Starting workout in {self.device_type} simulator")
        
        # Reset workout state
        self.workout_active = True
        self.start_time = time.time()
        self.workout_duration = 0
        
        # Reset accumulated metrics
        self.total_distance = 0.0
        self.total_calories = 0
        
        # Generate and send an initial data point immediately
        # This ensures data flow starts right away without waiting for the simulation loop
        if self.device_type == "bike":
            initial_data = self._generate_bike_data()
        else:  # rower
            initial_data = self._generate_rower_data()
        
        # Log and send the initial data point
        logger.info(f"Sending initial {self.device_type} data: power={initial_data.get('instantaneous_power')}, " +
                   f"distance={initial_data.get('total_distance'):.2f}m")
        self._notify_data(initial_data)
        
        # Notify status
        self._notify_status("workout_started", {
            "device": self.device,
            "workout_active": True
        })
    
    def end_workout(self) -> None:
        """
        End a workout session in the simulator.
        
        This method stops the workout data generation in the simulator by:
        1. Setting the workout_active flag to False to stop the generation loop
        2. Logging the current state for debugging purposes
        3. Notifying status callbacks of workout end
        4. Generating and sending a final data point to ensure the workout data is complete
        
        After this method is called, the simulator will stop generating workout data
        until start_workout() is called again. The simulation loop continues running,
        but checks the workout_active flag to determine whether to generate data.
        
        Returns:
            None
        """
        logger.info(f"Ending workout in {self.device_type} simulator")
        
        # Set flag to stop data generation
        self.workout_active = False
        
        # Log the current state to help debug
        logger.info(f"[STATE] Simulator workout ended: running={self.running}, workout_active={self.workout_active}")
        
        # Notify status
        self._notify_status("workout_ended", {
            "device": self.device,
            "workout_active": False,
            "duration": int(time.time() - self.start_time)
        })
        
        # Send a final data point to ensure we have a complete workout
        try:
            if self.device_type == "bike":
                final_data = self._generate_bike_data()
            else:  # rower
                final_data = self._generate_rower_data()
                
            # Mark this as the final data point
            final_data['is_final_point'] = True
            
            # Add a distinct data_id for the final point
            final_data['data_id'] = f"final_{int(time.time())}"
            
            logger.info(f"Sending final data point for {self.device_type} workout")
            self._notify_data(final_data)
        except Exception as e:
            logger.error(f"Error sending final data point: {str(e)}")
            import traceback
            traceback.print_exc()
    
    async def _simulation_loop(self) -> None:
        """Main simulation loop that generates data."""
        try:
            # Set a flag to track successful data sending
            data_generation_count = 0
            last_successful_send_time = time.time()
            
            logger.info("Simulation loop STARTED - will generate data when workout is active")
            
            while self.running:
                try:
                    # Update workout duration
                    current_time = time.time()
                    
                    if self.workout_active:
                        self.workout_duration = int(current_time - self.start_time)
                        
                        # Only generate and send data if a workout is active
                        if self.device_type == "bike":
                            data = self._generate_bike_data()
                            data_generation_count += 1
                            logger.info(f"[{data_generation_count}] Generated bike data: power={data.get('instantaneous_power')}, "
                                       f"cadence={data.get('instantaneous_cadence')}, "
                                       f"distance={data.get('total_distance'):.2f}m, "
                                       f"calories={data.get('total_calories')}")
                            
                            # Try to send the data, and track success/failure
                            sent_successfully = self._notify_data(data)
                            if sent_successfully:
                                last_successful_send_time = current_time
                                logger.info(f"Successfully sent data point #{data_generation_count}")
                            else:
                                time_since_last_success = current_time - last_successful_send_time
                                logger.error(f"Failed to send data point #{data_generation_count} - {time_since_last_success:.1f}s since last success")
                        else:  # rower
                            data = self._generate_rower_data()
                            data_generation_count += 1
                            logger.info(f"[{data_generation_count}] Generated rower data: power={data.get('instantaneous_power')}, "
                                       f"stroke_rate={data.get('stroke_rate')}, "
                                       f"distance={data.get('total_distance'):.2f}m, "
                                       f"calories={data.get('total_calories')}")
                            
                            # Try to send the data, and track success/failure
                            sent_successfully = self._notify_data(data)
                            if sent_successfully:
                                last_successful_send_time = current_time
                                logger.info(f"Successfully sent data point #{data_generation_count}")
                            else:
                                time_since_last_success = current_time - last_successful_send_time
                                logger.error(f"Failed to send data point #{data_generation_count} - {time_since_last_success:.1f}s since last success")
                    else:
                        logger.debug(f"Workout not active, not generating data (running={self.running}, workout_active={self.workout_active})")
                    
                    # Wait before next iteration - use a very short interval to ensure we're generating data
                    await asyncio.sleep(1.0)  # Generate data every 1.0 second
                except asyncio.CancelledError:
                    logger.info("Simulation loop cancelled")
                    break
                except Exception as e:
                    logger.error(f"Error in simulation iteration: {str(e)}", exc_info=True)
                    # Print full traceback
                    import traceback
                    traceback.print_exc()
                    # Continue the loop if there's an error in a single iteration
                    await asyncio.sleep(1)
        except asyncio.CancelledError:
            logger.info("Simulation loop cancelled")
        except Exception as e:
            logger.error(f"Fatal error in simulation loop: {str(e)}", exc_info=True)
            import traceback
            traceback.print_exc()
        finally:
            # Ensure we mark as not running if we exit for any reason
            self.running = False
            logger.info(f"Simulation loop ended after generating {data_generation_count} data points")
    
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
    
    def _notify_data(self, data: Dict[str, Any]) -> bool:
        """
        Notify all registered data callbacks with new data.
        
        Args:
            data: Dictionary of FTMS data
            
        Returns:
            True if data was successfully sent to at least one callback, False otherwise
        """
        try:
            # Force dump the first few and last few data items to debug data flow
            data_keys = list(data.keys())
            first_few = {k: data[k] for k in data_keys[:3] if k in data}
            last_few = {k: data[k] for k in data_keys[-3:] if k in data}
            logger.debug(f"Simulator generating data - first few keys: {first_few}, last few keys: {last_few}")
            
            if len(self.data_callbacks) == 0:
                logger.warning("No data callbacks registered with simulator!")
                return False
                
            success_count = 0
            error_count = 0
            
            for callback in self.data_callbacks:
                try:
                    callback_name = callback.__name__ if hasattr(callback, '__name__') else 'anonymous'
                    logger.debug(f"Calling data callback: {callback_name}")
                    
                    # Include a unique ID for each data point to make sure it's different
                    data = data.copy()  # Make a copy to avoid modifying the original
                    data['data_id'] = f"{self.workout_duration}_{int(time.time() * 1000) % 1000}"
                    
                    callback(data)
                    success_count += 1
                except Exception as e:
                    error_count += 1
                    logger.error(f"Error in data callback: {str(e)}", exc_info=True)
                    # Print the traceback for better debugging
                    import traceback
                    traceback.print_exc()
            
            # Return True if at least one callback succeeded
            return success_count > 0
        except Exception as e:
            logger.error(f"Error in _notify_data: {str(e)}", exc_info=True)
            import traceback
            traceback.print_exc()
            return False
    
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