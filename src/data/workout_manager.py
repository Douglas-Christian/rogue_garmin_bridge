#!/usr/bin/env python3
"""
Workout Manager Module for Rogue to Garmin Bridge

This module handles workout data collection, processing, and management.
It serves as an intermediary between the FTMS module and the database.
"""

import logging
import time
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime

# Fix the import to be relative to the project structure
import sys
import os
# Add the project root to the path so we can use absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.ftms.ftms_manager import FTMSDeviceManager
from .database import Database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('workout_manager')

class WorkoutManager:
    """
    Class for managing workout sessions, collecting and processing data.
    """
    
    def __init__(self, db_path: str, ftms_manager: FTMSDeviceManager = None):
        """
        Initialize the workout manager.
        
        Args:
            db_path: Path to the SQLite database file
            ftms_manager: FTMS device manager instance (optional)
        """
        self.database = Database(db_path)
        self.ftms_manager = ftms_manager
        
        # Current workout state
        self.active_workout_id = None
        self.active_device_id = None
        self.workout_start_time = None
        self.workout_type = None
        self.data_points = []
        self.summary_metrics = {}
        
        # Callbacks
        self.data_callbacks = []
        self.status_callbacks = []
        
        # Register with FTMS manager if provided
        if self.ftms_manager:
            self.ftms_manager.register_data_callback(self._handle_ftms_data)
            self.ftms_manager.register_status_callback(self._handle_ftms_status)
    
    def register_data_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        Register a callback function to receive processed workout data.
        
        Args:
            callback: Function that will be called with workout data
        """
        self.data_callbacks.append(callback)
    
    def register_status_callback(self, callback: Callable[[str, Any], None]) -> None:
        """
        Register a callback function to receive workout status updates.
        
        Args:
            callback: Function that will be called with status updates
        """
        self.status_callbacks.append(callback)
    
    def start_workout(self, device_id: int, workout_type: str) -> int:
        """
        Start a new workout session.
        
        Args:
            device_id: Device ID
            workout_type: Type of workout (bike, rower, etc.)
            
        Returns:
            Workout ID
        """
        if self.active_workout_id:
            logger.warning("Workout already in progress, ending current workout")
            self.end_workout()
        
        # Start new workout in database
        workout_id = self.database.start_workout(device_id, workout_type)
        
        # Set current workout state
        self.active_workout_id = workout_id
        self.active_device_id = device_id
        self.workout_start_time = time.time()
        self.workout_type = workout_type
        self.data_points = []
        self.summary_metrics = {
            'total_distance': 0,
            'total_calories': 0,
            'avg_power': 0,
            'max_power': 0,
            'avg_heart_rate': 0,
            'max_heart_rate': 0,
            'avg_cadence': 0,
            'max_cadence': 0,
            'avg_speed': 0,
            'max_speed': 0,
            'total_strokes': 0,  # For rower
            'avg_stroke_rate': 0,  # For rower
            'max_stroke_rate': 0,  # For rower
        }
        
        # Notify FTMS manager to start workout data generation if using simulator
        if self.ftms_manager:
            self.ftms_manager.notify_workout_start(workout_id, workout_type)
        
        # Notify status
        self._notify_status('workout_started', {
            'workout_id': workout_id,
            'device_id': device_id,
            'workout_type': workout_type,
            'start_time': datetime.now().isoformat()
        })
        
        logger.info(f"Started workout {workout_id} with device {device_id}")
        return workout_id
    
    def end_workout(self, workout_id=None) -> bool:
        """
        End the current workout session.
        
        Args:
            workout_id: Optional specific workout ID to end.
                        If not provided, ends the currently active workout.
        
        Returns:
            True if successful, False otherwise
        """
        # If workout_id is provided but doesn't match active workout, log warning
        if workout_id is not None and self.active_workout_id != workout_id:
            logger.warning(f"Requested to end workout {workout_id} but active workout is {self.active_workout_id}")
            # Continue anyway with the active workout
        
        if not self.active_workout_id:
            logger.warning("No active workout to end")
            return False
        
        # For debugging - log the call to end_workout
        logger.info(f"[DATA_FLOW] Ending workout {self.active_workout_id}")
        
        # Store the workout ID before clearing state for later use
        workout_id = self.active_workout_id
        
        # Notify FTMS manager to stop workout data generation BEFORE ending the workout in the database
        # This ensures the simulator stops generating data before we complete the workout
        if self.ftms_manager:
            logger.info(f"[DATA_FLOW] Notifying FTMS manager to end workout {workout_id}")
            self.ftms_manager.notify_workout_end(workout_id)
        
        # Calculate final summary metrics
        self._calculate_summary_metrics()
        
        # End workout in database
        logger.info(f"[DATA_FLOW] Ending workout {workout_id} in database with {len(self.data_points)} data points")
        success = self.database.end_workout(
            workout_id,
            summary=self.summary_metrics
        )
        
        if success:
            # Notify status callbacks
            self._notify_status('workout_ended', {
                'workout_id': workout_id,
                'device_id': self.active_device_id,
                'workout_type': self.workout_type,
                'duration': int(time.time() - self.workout_start_time),
                'summary': self.summary_metrics,
                'total_data_points': len(self.data_points)
            })
            
            logger.info(f"Ended workout {workout_id}")
            
            # Clear current workout state
            self.active_workout_id = None
            self.active_device_id = None
            self.workout_start_time = None
            self.workout_type = None
            self.data_points = []
            self.summary_metrics = {}
            
            return True
        else:
            logger.error(f"Failed to end workout {workout_id}")
            return False
    
    def add_data_point(self, data: Dict[str, Any]) -> bool:
        """
        Add a data point to the current workout.
        
        Args:
            data: Workout data point
            
        Returns:
            True if successful, False otherwise
        """
        if not self.active_workout_id:
            logger.warning("No active workout to add data to")
            return False
        
        # Calculate timestamp relative to workout start
        timestamp = int(time.time() - self.workout_start_time)
        
        # Add timestamp to data
        data['timestamp'] = timestamp
        
        # Store data point
        self.data_points.append(data)
        
        # Update summary metrics
        self._update_summary_metrics(data)
        
        # Store in database
        success = self.database.add_workout_data(
            self.active_workout_id,
            timestamp,
            data
        )
        
        if success:
            logger.info(f"Added data point to workout {self.active_workout_id}: time={timestamp}s, " + 
                       f"power={data.get('instantaneous_power', 'N/A')}, " +
                       f"distance={data.get('total_distance', 'N/A'):.2f}m, " +
                       f"calories={data.get('total_calories', 'N/A')}")
            # Notify data callbacks
            self._notify_data(data)
            return True
        else:
            logger.error(f"Failed to add data point to workout {self.active_workout_id}")
            return False
    
    def get_workout(self, workout_id: int) -> Optional[Dict[str, Any]]:
        """
        Get workout information.
        
        Args:
            workout_id: Workout ID
            
        Returns:
            Workout dictionary or None if not found
        """
        return self.database.get_workout(workout_id)
    
    def get_workout_data(self, workout_id: int) -> List[Dict[str, Any]]:
        """
        Get all data points for a workout.
        
        Args:
            workout_id: Workout ID
            
        Returns:
            List of workout data dictionaries
        """
        return self.database.get_workout_data(workout_id)
    
    def get_workouts(self, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get recent workouts.
        
        Args:
            limit: Maximum number of workouts to return
            offset: Offset for pagination
            
        Returns:
            List of workout dictionaries
        """
        return self.database.get_workouts(limit, offset)
    
    def get_devices(self) -> List[Dict[str, Any]]:
        """
        Get all devices from the database.
        
        Returns:
            List of device dictionaries
        """
        return self.database.get_devices()
    
    def get_user_profile(self) -> Optional[Dict[str, Any]]:
        """
        Get user profile information.
        
        Returns:
            User profile dictionary or None if not found
        """
        return self.database.get_user_profile()
    
    def set_user_profile(self, profile: Dict[str, Any]) -> bool:
        """
        Set user profile information.
        
        Args:
            profile: User profile dictionary
            
        Returns:
            True if successful, False otherwise
        """
        return self.database.set_user_profile(profile)
    
    def _handle_ftms_data(self, data: Dict[str, Any]) -> bool:
        """
        Handle data received from FTMS devices and integrate it into the active workout.
        
        This method serves as the critical bridge between raw data from devices (real or simulated)
        and the workout database. It performs the following key operations:
        
        1. Receives raw FTMS data points from connected devices/simulators 
        2. Validates, enriches, and normalizes the data (adding timestamps, IDs, etc.)
        3. Stores the data in the database under the active workout
        4. Updates local metrics tracking (including summary statistics)
        5. Notifies registered callbacks of new data for UI updates
        
        The method incorporates timestamp collision prevention by adding microsecond precision
        to timestamps, ensuring each data point has a unique identifier in the database.
        
        Args:
            data: Dictionary containing raw FTMS data from a device or simulator
                  Expected keys vary by device type but typically include:
                  - power measurements
                  - cadence/stroke rate
                  - distance
                  - calories
                  - heart rate (if available)
                  - timestamp or elapsed_time
        
        Returns:
            bool: True if data was successfully processed and stored, False otherwise
        
        Raises:
            No exceptions are raised directly. Exceptions are caught, logged, and False is returned.
        """
        try:
            # Log more information about the incoming data point to track data flow
            data_id = data.get('data_id', 'unknown')
            timestamp = data.get('timestamp', 'unknown')
            
            logger.info(f"[DATA_FLOW] Workout manager received FTMS data point ID={data_id}, timestamp={timestamp}, " +
                      f"type={data.get('type', 'unknown')}, power={data.get('instantaneous_power', 'N/A')}")
            
            if self.active_workout_id:
                # Make sure total_calories is present since some metrics depend on it
                if 'total_calories' not in data and 'calories' in data:
                    data['total_calories'] = data['calories']
                    
                # Make sure there's a timestamp
                if 'timestamp' not in data:
                    if 'elapsed_time' in data:
                        data['timestamp'] = data['elapsed_time']
                    else:
                        data['timestamp'] = int(time.time() - self.workout_start_time)
                
                # CRITICAL FIX: Ensure every timestamp is unique by adding a fractional part
                # This is the most reliable way to ensure unique timestamps
                if isinstance(data['timestamp'], int):
                    # Convert integer timestamp to float with microsecond precision
                    microsecond_part = datetime.now().microsecond / 1000000
                    data['timestamp'] = float(data['timestamp']) + microsecond_part
                
                # Debug the exact data being saved
                logger.info(f"[DATA_FLOW] Adding data point to workout {self.active_workout_id}: " +
                           f"time={data['timestamp']:.6f}s, data_id={data_id}")
                
                # Store in database - CRITICAL: Use a copy of the data to avoid modification issues
                data_copy = data.copy()
                success = self.database.add_workout_data(self.active_workout_id, data_copy['timestamp'], data_copy)
                
                if success:
                    # Store data point locally
                    self.data_points.append(data_copy)
                    
                    # Update summary metrics
                    self._update_summary_metrics(data_copy)
                    
                    # Notify data callbacks
                    self._notify_data(data_copy)
                    
                    logger.info(f"[DATA_FLOW] Successfully stored data point ID={data_id}")
                    return True
                else:
                    logger.error(f"[DATA_FLOW] Failed to add data point ID={data_id} to workout {self.active_workout_id}")
                    return False
            else:
                logger.info(f"[DATA_FLOW] Received FTMS data but no active workout - ID={data_id}")
                # Still update latest data even if no workout is active
                self._notify_data(data)
                return False
        except Exception as e:
            logger.error(f"Error handling FTMS data: {str(e)}", exc_info=True)
            import traceback
            traceback.print_exc()
            return False
    
    def _handle_ftms_status(self, status: str, data: Any) -> None:
        """
        Handle status updates from FTMS devices.
        
        Args:
            status: Status type
            data: Status data
        """
        if status == 'device_found':
            # Add device to database
            device = data
            self.database.add_device(
                address=device.address,
                name=device.name,
                device_type='unknown',  # Will be updated when connected
                metadata={'rssi': getattr(device, 'rssi', 0)}
            )
        
        elif status == 'connected':
            # Update device in database
            device = data
            device_type = 'bike' if getattr(device, 'name', '').lower().find('bike') >= 0 else 'rower'
            device_id = self.database.add_device(
                address=device.address,
                name=device.name,
                device_type=device_type,
                metadata={'rssi': getattr(device, 'rssi', 0)}
            )
            
            # Don't automatically start a workout when device connects
            # Let the user manually start workouts from the UI
            logger.info(f"Device connected: {device.name} ({device.address}). Workout can be started manually.")
            
            # Notify status for connected device
            self._notify_status('device_connected', {
                'device_id': device_id,
                'device_address': device.address,
                'device_name': device.name,
                'device_type': device_type
            })
        
        elif status == 'disconnected':
            # End workout if in progress
            if self.active_workout_id:
                self.end_workout()
    
    def _update_summary_metrics(self, data: Dict[str, Any]) -> None:
        """
        Update summary metrics with new data point.
        
        Args:
            data: New data point
        """
        # Extract metrics based on workout type
        if self.workout_type == 'bike':
            self._update_bike_metrics(data)
        elif self.workout_type == 'rower':
            self._update_rower_metrics(data)
    
    def _update_bike_metrics(self, data: Dict[str, Any]) -> None:
        """
        Update bike-specific metrics.
        
        Args:
            data: New data point
        """
        # Update distance
        if 'total_distance' in data:
            self.summary_metrics['total_distance'] = data['total_distance']
        
        # Update calories
        if 'total_energy' in data:
            self.summary_metrics['total_calories'] = data['total_energy']
        
        # Update power metrics
        if 'instantaneous_power' in data:
            power = data['instantaneous_power']
            
            # Update max power
            if power > self.summary_metrics.get('max_power', 0):
                self.summary_metrics['max_power'] = power
            
            # Update average power
            power_values = [d.get('instantaneous_power', 0) for d in self.data_points if 'instantaneous_power' in d]
            if power_values:
                self.summary_metrics['avg_power'] = sum(power_values) / len(power_values)
        
        # Update heart rate metrics
        if 'heart_rate' in data:
            hr = data['heart_rate']
            
            # Update max heart rate
            if hr > self.summary_metrics.get('max_heart_rate', 0):
                self.summary_metrics['max_heart_rate'] = hr
            
            # Update average heart rate
            hr_values = [d.get('heart_rate', 0) for d in self.data_points if 'heart_rate' in d]
            if hr_values:
                self.summary_metrics['avg_heart_rate'] = sum(hr_values) / len(hr_values)
        
        # Update cadence metrics
        if 'instantaneous_cadence' in data:
            cadence = data['instantaneous_cadence']
            
            # Update max cadence
            if cadence > self.summary_metrics.get('max_cadence', 0):
                self.summary_metrics['max_cadence'] = cadence
            
            # Update average cadence
            cadence_values = [d.get('instantaneous_cadence', 0) for d in self.data_points if 'instantaneous_cadence' in d]
            if cadence_values:
                self.summary_metrics['avg_cadence'] = sum(cadence_values) / len(cadence_values)
        
        # Update speed metrics
        if 'instantaneous_speed' in data:
            speed = data['instantaneous_speed']
            
            # Update max speed
            if speed > self.summary_metrics.get('max_speed', 0):
                self.summary_metrics['max_speed'] = speed
            
            # Update average speed
            speed_values = [d.get('instantaneous_speed', 0) for d in self.data_points if 'instantaneous_speed' in d]
            if speed_values:
                self.summary_metrics['avg_speed'] = sum(speed_values) / len(speed_values)
    
    def _update_rower_metrics(self, data: Dict[str, Any]) -> None:
        """
        Update rower-specific metrics.
        
        Args:
            data: New data point
        """
        # Update distance
        if 'total_distance' in data:
            self.summary_metrics['total_distance'] = data['total_distance']
        
        # Update calories
        if 'total_energy' in data:
            self.summary_metrics['total_calories'] = data['total_energy']
        
        # Update power metrics
        if 'instantaneous_power' in data:
            power = data['instantaneous_power']
            
            # Update max power
            if power > self.summary_metrics.get('max_power', 0):
                self.summary_metrics['max_power'] = power
            
            # Update average power
            power_values = [d.get('instantaneous_power', 0) for d in self.data_points if 'instantaneous_power' in d]
            if power_values:
                self.summary_metrics['avg_power'] = sum(power_values) / len(power_values)
        
        # Update heart rate metrics
        if 'heart_rate' in data:
            hr = data['heart_rate']
            
            # Update max heart rate
            if hr > self.summary_metrics.get('max_heart_rate', 0):
                self.summary_metrics['max_heart_rate'] = hr
            
            # Update average heart rate
            hr_values = [d.get('heart_rate', 0) for d in self.data_points if 'heart_rate' in d]
            if hr_values:
                self.summary_metrics['avg_heart_rate'] = sum(hr_values) / len(hr_values)
        
        # Update stroke metrics
        if 'stroke_count' in data:
            self.summary_metrics['total_strokes'] = data['stroke_count']
        
        if 'stroke_rate' in data:
            stroke_rate = data['stroke_rate']
            
            # Update max stroke rate
            if stroke_rate > self.summary_metrics.get('max_stroke_rate', 0):
                self.summary_metrics['max_stroke_rate'] = stroke_rate
            
            # Update average stroke rate
            stroke_rate_values = [d.get('stroke_rate', 0) for d in self.data_points if 'stroke_rate' in d]
            if stroke_rate_values:
                self.summary_metrics['avg_stroke_rate'] = sum(stroke_rate_values) / len(stroke_rate_values)
    
    def _calculate_summary_metrics(self) -> None:
        """Calculate final summary metrics for the workout."""
        # Most metrics are already calculated incrementally
        
        # Round average values
        for key in self.summary_metrics:
            if key.startswith('avg_'):
                self.summary_metrics[key] = round(self.summary_metrics[key], 2)
        
        # Calculate estimated VO2max (if applicable)
        # Only do this for workouts with heart rate data and power data
        if (self.summary_metrics.get('avg_heart_rate', 0) > 0 and 
            self.summary_metrics.get('avg_power', 0) > 0):
            
            # Get user profile for weight and other parameters
            user_profile = self.get_user_profile()
            
            if user_profile and 'weight_kg' in user_profile:
                weight_kg = user_profile.get('weight_kg', 70)  # Default to 70kg if not available
                max_hr = self.summary_metrics.get('max_heart_rate', 0)
                avg_hr = self.summary_metrics.get('avg_heart_rate', 0)
                avg_power = self.summary_metrics.get('avg_power', 0)
                
                # Only estimate if we have a significant heart rate
                if avg_hr > 120 and max_hr > 130:
                    # Simplified VO2max estimation based on power output and heart rate
                    # This is a basic formula and could be improved with more advanced models
                    power_per_kg = avg_power / weight_kg
                    hr_ratio = avg_hr / max_hr
                    
                    # Basic VO2max estimation formula
                    # Adapted from standard exercise physiology formulas
                    estimated_vo2max = power_per_kg * 10.8 * (1 + (1 - hr_ratio))
                    
                    # Ensure reasonable bounds
                    estimated_vo2max = max(min(estimated_vo2max, 90), 20)
                    
                    # Add to summary metrics
                    self.summary_metrics['estimated_vo2max'] = round(estimated_vo2max, 1)
                    logger.info(f"Estimated VO2max: {estimated_vo2max:.1f} ml/kg/min")
                else:
                    logger.info("Heart rate too low for reliable VO2max estimation")
            else:
                logger.info("User weight not available for VO2max calculation")
    
    def _notify_data(self, data: Dict[str, Any]) -> None:
        """
        Notify all registered data callbacks with new data.
        
        Args:
            data: Dictionary of workout data
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


# Example usage
if __name__ == "__main__":
    import asyncio
    from src.ftms.ftms_manager import FTMSDeviceManager
    
    async def main():
        # Create FTMS manager with simulator
        ftms_manager = FTMSDeviceManager(use_simulator=True)
        
        # Create workout manager
        workout_manager = WorkoutManager("test.db", ftms_manager)
        
        # Define callbacks
        def data_callback(data):
            print(f"Processed data: {data}")
        
        def status_callback(status, data):
            print(f"Workout status: {status} - {data}")
        
        # Register callbacks
        workout_manager.register_data_callback(data_callback)
        workout_manager.register_status_callback(status_callback)
        
        # Discover devices
        devices = await ftms_manager.discover_devices()
        
        if devices:
            # Connect to the first device found
            device_address = list(devices.keys())[0]
            await ftms_manager.connect(device_address)
            
            # Workout will be started automatically by the workout manager
            # when the device connects
            
            # Keep the connection open for 30 seconds
            await asyncio.sleep(30)
            
            # Disconnect (will end the workout)
            await ftms_manager.disconnect()
            
            # Get workout history
            workouts = workout_manager.get_workouts()
            print(f"Workout history: {workouts}")
        else:
            print("No FTMS devices found")
    
    asyncio.run(main())