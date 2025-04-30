#!/usr/bin/env python3
"""
Workout Manager Module for Rogue to Garmin Bridge

This module handles workout data management, storage, and retrieval.
"""

import os
import sys
import json
import time
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime

# Add the project root to the path so we can use absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.data.database import Database
from src.data.data_processor import DataProcessor
from src.utils.logging_config import get_component_logger
from src.ftms.ftms_manager import FTMSDeviceManager

# Get component logger
logger = get_component_logger('workout_manager')

class WorkoutManager:
    """
    Manages workout data, including data collection, processing, storage, and retrieval.
    Interfaces between FTMS devices, the database, and FIT file generation.
    """
    
    def __init__(self, db_path_or_instance, ftms_manager: FTMSDeviceManager = None):
        """
        Initialize the workout manager.
        
        Args:
            db_path_or_instance: Path to the SQLite database file or a Database instance
            ftms_manager: FTMS device manager instance (optional)
        """
        # Check if db_path_or_instance is already a Database instance
        if isinstance(db_path_or_instance, Database):
            self.database = db_path_or_instance
        else:
            # Otherwise assume it's a path string
            self.database = Database(db_path_or_instance)
            
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
    
    def start_workout(self, device_id: str, workout_type: str) -> int:
        """
        Start a new workout session.
        
        Args:
            device_id: ID of the connected device
            workout_type: Type of workout (e.g., 'bike', 'rower')
            
        Returns:
            Workout ID if successful, -1 if failed
        """
        try:
            # Validate parameters
            if not device_id:
                logger.error("Cannot start workout: No device ID provided")
                return -1
                
            if not workout_type:
                logger.error("Cannot start workout: No workout type provided")
                return -1
                
            # Check if already in a workout
            if self.active_workout_id is not None:
                logger.warning(f"Workout already in progress (ID: {self.active_workout_id}). Ending previous workout.")
                self.end_workout()
            
            logger.info(f"Starting new {workout_type} workout on device {device_id}")
            
            # Create a new workout record - Remove start_time parameter to match database API
            workout_id = self.database.start_workout(
                device_id=device_id,
                workout_type=workout_type
            )
            
            if workout_id == -1:
                logger.error("Failed to create workout in database")
                return -1
                
            self.active_workout_id = workout_id
            self.active_device_id = device_id
            self.workout_start_time = datetime.now()
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
        
        except Exception as e:
            logger.error(f"Error starting workout: {str(e)}")
            return -1
    
    def end_workout(self, workout_id=None) -> bool:
        """
        End the current workout session.
        
        Args:
            workout_id: Optional workout ID to end. If None, ends the active workout.
            
        Returns:
            True if successful, False if failed
        """
        try:
            # If no workout_id is provided, use the active workout
            if workout_id is None:
                workout_id = self.active_workout_id
                
            if workout_id is None:
                logger.warning("No workout in progress to end")
                return False
                
            logger.info(f"Ending workout (ID: {workout_id})")
            
            # Calculate workout duration
            end_time = datetime.now()
            duration = (end_time - self.workout_start_time).total_seconds()
            
            # Process workout data for summary metrics
            summary = self._calculate_summary_metrics()
            
            # Update the workout record
            success = self.database.end_workout(
                workout_id=workout_id,
                summary=summary
            )
            
            if not success:
                logger.error(f"Failed to update workout {workout_id} in database")
                
            # Notify any connected device managers
            if self.ftms_manager:
                self.ftms_manager.notify_workout_end(workout_id)
                
            # Generate FIT file (Commented out for now to avoid fit_converter error)
            # if self.fit_converter and len(self.data_points) > 0:
            #     try:
            #         fit_file = self.fit_converter.convert_workout_to_fit(
            #             workout_id=workout_id,
            #             workout_type=self.workout_type,
            #             data=self.data_points,
            #             summary=summary
            #         )
            #         
            #         # If Garmin uploader is available, upload the file
            #         if self.garmin_uploader and fit_file:
            #             self.garmin_uploader.upload_workout(fit_file)
            #     except Exception as e:
            #         logger.error(f"Error generating or uploading FIT file: {str(e)}")
            
            # Clear current workout state
            self.active_workout_id = None
            self.active_device_id = None
            self.workout_start_time = None
            self.workout_type = None
            self.data_points = []
            self.summary_metrics = {}
            
            return success
            
        except Exception as e:
            logger.error(f"Error ending workout: {str(e)}")
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
        
        # Calculate timestamp relative to workout start as a float
        # Use datetime objects for accurate difference calculation
        if not self.workout_start_time:
             logger.error("Workout start time not set, cannot calculate relative timestamp")
             return False
             
        current_time = datetime.now()
        timestamp = (current_time - self.workout_start_time).total_seconds()
        
        # Add timestamp to data
        data['timestamp'] = timestamp
        
        # Store data point locally (for summary calculation)
        self.data_points.append(data)
        
        # Update summary metrics
        self._update_summary_metrics(data)
        
        # Store in database
        success = self.database.add_workout_data(
            self.active_workout_id,
            timestamp, # Pass the float timestamp
            data
        )
        
        if success:
            logger.info(f"Added data point to workout {self.active_workout_id}: time={timestamp:.3f}s, " + 
                       f"power={data.get('instant_power', 'N/A')}, " + # Corrected key
                       f"distance={data.get('total_distance', 'N/A'):.2f}m, " +
                       f"calories={data.get('total_energy', 'N/A')}") # Corrected key for calories
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
    
    def _handle_ftms_data(self, data: Dict[str, Any]):
        """Handle incoming FTMS data points."""
        logger.debug(f"Workout manager received FTMS data point: {data}") # Log data reception
        if self.active_workout_id is not None and self.workout_start_time is not None:
            # Calculate timestamp relative to workout start
            # Ensure high precision timestamp
            now = datetime.now()
            timestamp = (now - self.workout_start_time).total_seconds()
            # Add microseconds for higher precision, avoiding potential collisions
            timestamp += now.microsecond / 1000000.0 
            
            logger.info(f"Processing data point for workout {self.active_workout_id} at relative timestamp {timestamp:.6f}") # Log processing attempt
            
            # Add timestamp to data for local tracking
            data_with_timestamp = data.copy()
            data_with_timestamp['timestamp'] = timestamp
            
            # Add data point to local memory (for summary calculation)
            self.data_points.append(data_with_timestamp)
            
            # Update summary metrics
            self._update_summary_metrics(data_with_timestamp)
            
            # Add data point to the database
            success = self.database.add_workout_data(self.active_workout_id, timestamp, data)
            
            if success:
                logger.info(f"Successfully requested database add for workout {self.active_workout_id}, timestamp {timestamp:.6f}") # Log success call
                # Notify data callbacks about the new data
                self._notify_data(data_with_timestamp)
            else:
                logger.error(f"Failed to request database add for workout {self.active_workout_id}, timestamp {timestamp:.6f}") # Log failed call
                
            # Update live data
            self.live_workout_data = data_with_timestamp
        else:
            logger.warning("Received FTMS data but no active workout. Ignoring.") # Log ignored data
    
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
        if 'total_distance' in data and data['total_distance'] is not None:
            self.summary_metrics['total_distance'] = data['total_distance']
        
        # Update calories
        if 'total_energy' in data and data['total_energy'] is not None:
            self.summary_metrics['total_calories'] = data['total_energy']
        
        # Update power metrics
        if 'instant_power' in data and data['instant_power'] is not None: # Corrected key
            power = data['instant_power']
            
            # Update max power
            if power > self.summary_metrics.get('max_power', 0):
                self.summary_metrics['max_power'] = power
            
            # Update average power
            power_values = [d.get('instant_power', 0) for d in self.data_points if d.get('instant_power') is not None] # Corrected key
            if power_values:
                self.summary_metrics['avg_power'] = sum(power_values) / len(power_values)
        
        # Update heart rate metrics
        if 'heart_rate' in data and data['heart_rate'] is not None:
            hr = data['heart_rate']
            
            # Update max heart rate
            if hr > self.summary_metrics.get('max_heart_rate', 0):
                self.summary_metrics['max_heart_rate'] = hr
            
            # Update average heart rate
            hr_values = [d.get('heart_rate', 0) for d in self.data_points if d.get('heart_rate') is not None]
            if hr_values:
                self.summary_metrics['avg_heart_rate'] = sum(hr_values) / len(hr_values)
        
        # Update cadence metrics
        if 'instant_cadence' in data and data['instant_cadence'] is not None: # Corrected key
            cadence = data['instant_cadence']
            
            # Update max cadence
            if cadence > self.summary_metrics.get('max_cadence', 0):
                self.summary_metrics['max_cadence'] = cadence
            
            # Update average cadence
            cadence_values = [d.get('instant_cadence', 0) for d in self.data_points if d.get('instant_cadence') is not None] # Corrected key
            if cadence_values:
                self.summary_metrics['avg_cadence'] = sum(cadence_values) / len(cadence_values)
        
        # Update speed metrics
        if 'instant_speed' in data and data['instant_speed'] is not None: # Corrected key
            speed = data['instant_speed']
            
            # Update max speed
            if speed > self.summary_metrics.get('max_speed', 0):
                self.summary_metrics['max_speed'] = speed
            
            # Update average speed
            speed_values = [d.get('instant_speed', 0) for d in self.data_points if d.get('instant_speed') is not None] # Corrected key
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
    
    def get_workout_summary_metrics(self) -> Dict[str, Any]:
        """
        Get the current summary metrics for the active workout.
        Used to provide live summary data to the frontend.
        
        Returns:
            Dictionary of summary metrics
        """
        # If no active workout, return empty dict
        if not self.active_workout_id:
            return {}
            
        # Create a copy of the summary metrics to avoid reference issues
        summary = self.summary_metrics.copy()
        
        # Handle any potential NaN values and convert them to proper formats
        for key, value in summary.items():
            # Check if value is NaN or None
            if value is None or (isinstance(value, float) and (value != value)):  # NaN check
                summary[key] = 0
                
        # Only add estimated VO2max if we have enough data
        if (summary.get('avg_heart_rate', 0) > 0 and 
            summary.get('avg_power', 0) > 0):
            
            # Get user profile for weight
            user_profile = self.get_user_profile()
            
            if user_profile and 'weight_kg' in user_profile:
                weight_kg = user_profile.get('weight_kg', 70)  # Default to 70kg if not available
                max_hr = summary.get('max_heart_rate', 0)
                avg_hr = summary.get('avg_heart_rate', 0)
                avg_power = summary.get('avg_power', 0)
                
                # Only estimate if we have a significant heart rate
                if avg_hr > 120 and max_hr > 130:
                    # Simplified VO2max estimation
                    power_per_kg = avg_power / weight_kg
                    hr_ratio = avg_hr / max_hr
                    
                    estimated_vo2max = power_per_kg * 10.8 * (1 + (1 - hr_ratio))
                    estimated_vo2max = max(min(estimated_vo2max, 90), 20)
                    
                    summary['estimated_vo2max'] = round(estimated_vo2max, 1)
                else:
                    # Add a placeholder value that's not null
                    summary['estimated_vo2max'] = 0
            else:
                # Set a default value when user weight isn't available
                summary['estimated_vo2max'] = 0
                
        return summary
    
    def delete_workout(self, workout_id: int) -> bool:
        """
        Delete a workout and all its associated data from the database.
        
        Args:
            workout_id: ID of the workout to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Deleting workout {workout_id}")
            
            # First check if the workout exists
            workout = self.get_workout(workout_id)
            if not workout:
                logger.warning(f"Workout {workout_id} not found, cannot delete")
                return False
                
            # Since there's no direct delete method in the Database class,
            # we'll establish a connection and execute SQL directly
            self.database._connect()
            
            # Delete workout data points first
            self.database.cursor.execute(
                "DELETE FROM workout_data WHERE workout_id = ?", 
                (workout_id,)
            )
            
            # Then delete the workout itself
            self.database.cursor.execute(
                "DELETE FROM workouts WHERE id = ?", 
                (workout_id,)
            )
            
            # Commit the changes
            self.database.conn.commit()
            
            # Disconnect from the database
            self.database._disconnect()
            
            logger.info(f"Deleted workout {workout_id} and its data points")
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting workout: {str(e)}", exc_info=True)
            
            # Make sure to rollback and close the connection on error
            if hasattr(self.database, 'conn') and self.database.conn:
                try:
                    self.database.conn.rollback()
                except:
                    pass
                finally:
                    self.database._disconnect()
                    
            return False


# Example usage
if __name__ == "__main__":
    import asyncio
    
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