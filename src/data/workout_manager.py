#!/usr/bin/env python3
"""
Workout Manager Module for Rogue to Garmin Bridge

This module handles workout data collection, processing, and management.
It serves as an intermediary between the FTMS module and the database.
"""

import logging
import time
import os  # Added for path joining
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime

from ..ftms.ftms_manager import FTMSDeviceManager
from .database import Database
from .data_processor import DataProcessor  # Added import
from ..fit.fit_converter import FITConverter  # Added import

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime:s) - %(name)s - %(levelname)s - %(message)s'
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
        self.data_processor = DataProcessor() # Initialize DataProcessor
        # Define the output directory for FIT files relative to the project root
        fit_output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "fit_files"))
        self.fit_converter = FITConverter(output_dir=fit_output_dir) # Initialize FITConverter
        
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
        
        # Notify status
        self._notify_status('workout_started', {
            'workout_id': workout_id,
            'device_id': device_id,
            'workout_type': workout_type,
            'start_time': datetime.now().isoformat()
        })
        
        logger.info(f"Started workout {workout_id} with device {device_id}")
        return workout_id
    
    def end_workout(self) -> bool:
        """
        End the current workout session.
        
        Returns:
            True if successful, False otherwise
        """
        if not self.active_workout_id:
            logger.warning("No active workout to end")
            return False
        
        # Store workout ID and type before clearing state
        workout_id_to_end = self.active_workout_id
        workout_type_to_end = self.workout_type
        start_time_to_end = self.workout_start_time
        
        # Calculate final summary metrics
        self._calculate_summary_metrics()
        
        # End workout in database with summary metrics (but no FIT file path yet)
        success = self.database.end_workout(
            workout_id_to_end,
            summary=self.summary_metrics
        )
        
        if not success:
            logger.error(f"Failed to end workout {workout_id_to_end}")
            return False
        
        # Use the optimized FIT processor to generate the FIT file
        try:
            # Import FITProcessor here to avoid circular imports
            from ..fit.fit_processor import FITProcessor
            
            # Define the output directory for FIT files
            fit_output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "fit_files"))
            
            # Create FIT processor
            fit_processor = FITProcessor(self.database.db_path, fit_output_dir)
            
            # Process workout and generate FIT file
            fit_file_path = fit_processor.process_workout(
                workout_id_to_end, 
                user_profile=self.get_user_profile()
            )
            
            # Update the workout record with the FIT file path
            if fit_file_path:
                logger.info(f"Successfully created FIT file for workout {workout_id_to_end}: {fit_file_path}")
            else:
                logger.warning(f"Failed to create FIT file for workout {workout_id_to_end}")
        
            # Notify status
            duration = (datetime.now() - start_time_to_end).total_seconds()
            self._notify_status("workout_ended", {
                "workout_id": workout_id_to_end,
                "device_id": self.active_device_id,
                "workout_type": workout_type_to_end,
                "duration": int(duration),
                "summary": self.summary_metrics,
                "fit_file_path": fit_file_path
            })
            
            # Clear current workout state
            self.active_workout_id = None
            self.active_device_id = None
            self.workout_start_time = None
            self.workout_type = None
            self.data_points = []
            self.summary_metrics = {}
            
            return True
        except Exception as e:
            logger.error(f"Error processing workout for FIT file: {str(e)}")
            
            # Clear current workout state            self.active_workout_id = None
            self.active_device_id = None
            self.workout_start_time = None
            self.workout_type = None
            self.data_points = []
            self.summary_metrics = {}
            
            return True  # Still return True since the workout was ended in database
    
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
            return False        # Get absolute timestamp for data point
        absolute_timestamp = datetime.now()
        
        # Log the incoming data with timestamp for diagnostics
        logger.info(f"ADDING DATA POINT at {absolute_timestamp.isoformat()}")
        logger.info(f"Data: {data}")
        
        # Store data point locally (optional, consider if needed for summary)
        # Add absolute timestamp to local data point if keeping it
        data_with_ts = data.copy()
        data_with_ts["timestamp"] = absolute_timestamp 
        self.data_points.append(data_with_ts)
          # Update summary metrics
        self._update_summary_metrics(data)
        
        # Store in database using absolute timestamp
        try:
            success = self.database.add_workout_data(
                self.active_workout_id,
                absolute_timestamp, # Pass the datetime object
                data # Pass the original data without the timestamp field
            )
            
            if success:
                # Log successful data point storage
                logger.info(f"Successfully saved data point to workout {self.active_workout_id}")
                
                # Notify data callbacks
                self._notify_data(data)
                return True
            else:
                logger.error(f"Failed to add data point to workout {self.active_workout_id}")
                return False
        except Exception as e:
            logger.error(f"Exception adding data point to workout {self.active_workout_id}: {str(e)}")
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
    
    def _handle_ftms_data(self, data: Dict[str, Any]) -> None:
        """
        Handle data from FTMS devices.
        
        Args:
            data: Dictionary of FTMS data
        """
        if self.active_workout_id:
            self.add_data_point(data)
    
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
            
            # Start workout if not already started
            if not self.active_workout_id:
                self.start_workout(device_id, device_type)
        
        elif status == 'disconnected':
            # End workout if in progress
            if self.active_workout_id:
                self.end_workout()
    
    def _update_summary_metrics(self, data: Dict[str, Any]) -> None:
        """
        Update summary metrics with new data point.
        
        Args:
            data: New data point
        """        # Extract metrics based on workout type
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
        # Update distance - check for different possible field names
        if 'total_distance' in data:
            self.summary_metrics['total_distance'] = data['total_distance']
        elif 'distance' in data:
            self.summary_metrics['total_distance'] = data['distance']
        # If still no distance but we have speed, try to estimate distance from speed and time
        elif any(key in data for key in ['instantaneous_speed', 'speed', 'instant_speed']):
            # Get speed in km/h
            for speed_key in ['instantaneous_speed', 'speed', 'instant_speed']:
                if speed_key in data:
                    speed_kmh = data[speed_key]
                    break
            else:
                speed_kmh = 0
                
            # Convert to meters per second and calculate distance increment
            if speed_kmh > 0 and 'timestamp' in data:
                # If we have previous timestamp, calculate time delta
                if hasattr(self, '_last_timestamp'):
                    try:
                        current_ts = datetime.fromisoformat(data['timestamp'])
                        time_delta_sec = (current_ts - self._last_timestamp).total_seconds()
                        
                        # Speed is km/h, convert to m/s and calculate distance increment
                        speed_mps = speed_kmh / 3.6  # Convert km/h to m/s
                        distance_increment = speed_mps * time_delta_sec
                        
                        # Update the total distance
                        self.summary_metrics['total_distance'] = self.summary_metrics.get('total_distance', 0) + distance_increment
                    except (ValueError, TypeError):
                        pass  # Skip if timestamp parsing fails
                        
                # Update timestamp for next calculation
                try:
                    self._last_timestamp = datetime.fromisoformat(data['timestamp'])
                except (ValueError, TypeError):
                    pass  # Skip if timestamp parsing fails
        
        # Update calories
        if 'total_energy' in data:
            self.summary_metrics['total_calories'] = data['total_energy']
        
        # Update power metrics - check both instant and average values
        if 'instant_power' in data or 'instantaneous_power' in data or 'power' in data:
            # Get the instantaneous power value from various possible keys
            power = data.get('instant_power', data.get('instantaneous_power', data.get('power', 0)))
            
            # Update max power if higher
            if power > self.summary_metrics.get('max_power', 0):
                self.summary_metrics['max_power'] = power
        
        # Use average power directly from device if available
        if 'average_power' in data and data['average_power'] is not None:
            self.summary_metrics['avg_power'] = data['average_power']
        # Otherwise calculate from instantaneous values
        elif any(key in data for key in ['instant_power', 'instantaneous_power', 'power']):
            power_values = []
            for d in self.data_points:
                for key in ['instant_power', 'instantaneous_power', 'power']:
                    if key in d and d[key] is not None:
                        power_values.append(d[key])
                        break
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
          # Update cadence metrics - check for multiple possible field names
        cadence_keys = ['instant_cadence', 'instantaneous_cadence', 'cadence']
        cadence_value = None
        
        # Try to get the cadence value from the data
        for key in cadence_keys:
            if key in data and data[key] is not None and data[key] > 0:
                cadence_value = data[key]
                break
                
        if cadence_value is not None:
            # Log the received cadence value for debugging
            logger.debug(f"Received cadence value: {cadence_value}")
            
            # Update max cadence if higher
            if cadence_value > self.summary_metrics.get('max_cadence', 0):
                self.summary_metrics['max_cadence'] = cadence_value
                logger.debug(f"Updated max cadence to: {cadence_value}")
        
        # Use average cadence directly from device if available and looks reasonable
        if 'average_cadence' in data and data['average_cadence'] is not None and data['average_cadence'] > 0:
            self.summary_metrics['avg_cadence'] = data['average_cadence']
            logger.debug(f"Using device-reported average cadence: {data['average_cadence']}")
        # Otherwise calculate from instantaneous values
        elif cadence_value is not None:
            # Collect all non-zero cadence values
            cadence_values = []
            for d in self.data_points:
                for key in cadence_keys:
                    if key in d and d[key] is not None and d[key] > 0:
                        cadence_values.append(d[key])
                        break
                        
            if cadence_values:
                avg_cadence = sum(cadence_values) / len(cadence_values)
                self.summary_metrics['avg_cadence'] = avg_cadence
                logger.debug(f"Calculated average cadence from {len(cadence_values)} data points: {avg_cadence}")
        
        # Update speed metrics - check instantaneous values only
        if 'instant_speed' in data or 'instantaneous_speed' in data or 'speed' in data:
            # Get the instantaneous speed value from various possible keys
            speed = data.get('instant_speed', data.get('instantaneous_speed', data.get('speed', 0)))
            
            # Log speed value for diagnostics
            logger.debug(f"Received instantaneous speed: {speed} km/h")
            
            # Update max speed if higher
            if speed > self.summary_metrics.get('max_speed', 0):
                self.summary_metrics['max_speed'] = speed
          # IMPROVED: Calculate average speed from instantaneous values with outlier filtering
        # Ignore device-reported average_speed completely as it's often inaccurate
        speed_values = []
        for d in self.data_points:
            for key in ['instant_speed', 'instantaneous_speed', 'speed']:
                if key in d and d[key] is not None and d[key] > 0:  # Only include positive values
                    speed_values.append(d[key])
                    break
        
        if speed_values:
            # Basic outlier removal - filter out values more than 2 standard deviations from mean
            if len(speed_values) > 4:  # Only apply filtering if we have enough data points
                mean_speed = sum(speed_values) / len(speed_values)
                std_dev = (sum((x - mean_speed) ** 2 for x in speed_values) / len(speed_values)) ** 0.5
                
                # Filter out outliers
                filtered_speeds = [s for s in speed_values if abs(s - mean_speed) <= 2 * std_dev]
                
                if filtered_speeds:  # Ensure we still have values after filtering
                    avg_calculated_speed = sum(filtered_speeds) / len(filtered_speeds)
                    logger.info(f"Calculated average speed from {len(filtered_speeds)} filtered data points " +
                              f"(removed {len(speed_values) - len(filtered_speeds)} outliers): {avg_calculated_speed} km/h")
                else:
                    # Fall back to simple average if filtering removed all points
                    avg_calculated_speed = sum(speed_values) / len(speed_values)
                    logger.info(f"Falling back to unfiltered average speed from {len(speed_values)} data points: " +
                              f"{avg_calculated_speed} km/h")
            else:
                # Simple average for small number of data points
                avg_calculated_speed = sum(speed_values) / len(speed_values)
                logger.info(f"Calculated average speed from {len(speed_values)} data points: {avg_calculated_speed} km/h")
            
            self.summary_metrics['avg_speed'] = avg_calculated_speed
            
            # If data contains a device-reported average_speed, log for debugging
            if 'average_speed' in data and data['average_speed'] is not None:
                logger.info(f"Device-reported average speed: {data['average_speed']} km/h (not used)")
    
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
    
    def get_workout_summary_metrics(self) -> Dict[str, Any]:
        """
        Get the summary metrics for the active workout.
        
        Returns:
            Dictionary of summary metrics or empty dict if no active workout
        """
        if not self.active_workout_id:
            return {}
        
        # Make a copy of the summary metrics to avoid external modification
        summary = self.summary_metrics.copy()
        
        # Calculate elapsed time
        if self.workout_start_time:
            elapsed_seconds = (datetime.now() - self.workout_start_time).total_seconds()
            summary['elapsed_time'] = int(elapsed_seconds)
        
        # Add workout type
        if self.workout_type:
            summary['workout_type'] = self.workout_type
        
        # Round average values for display
        for key in summary:
            if key.startswith('avg_'):
                summary[key] = round(summary[key], 2)
                
        # Calculate estimated VO2 max if we have heart rate and user weight data
        if summary.get('avg_heart_rate', 0) > 0 and summary.get('avg_power', 0) > 0:
            user_profile = self.get_user_profile()
            if user_profile and 'weight_kg' in user_profile:
                weight_kg = user_profile['weight_kg']
                avg_hr = summary['avg_heart_rate']
                avg_power = summary['avg_power']
                
                # Only calculate if HR is sufficiently high (exercise intensity)
                if avg_hr > 120:
                    # Estimation formula: VO2 = (Power in watts / Weight in kg) * 10.8 + 7
                    estimated_vo2 = (avg_power / weight_kg) * 10.8 + 7
                    summary['estimated_vo2max'] = round(estimated_vo2, 1)
        
        return summary
    
    def _calculate_summary_metrics(self) -> None:
        """Calculate final summary metrics for the workout."""
        # Most metrics are already calculated incrementally
        # This method can be used for any final calculations
        
        # Round average values
        for key in self.summary_metrics:
            if key.startswith('avg_'):
                self.summary_metrics[key] = round(self.summary_metrics[key], 2)
    
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
    
    def update_workout_fit_file(self, workout_id: int, fit_file_path: str) -> bool:
        """
        Update the FIT file path for a workout.
        
        Args:
            workout_id: Workout ID
            fit_file_path: Path to the generated FIT file
            
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Updating workout {workout_id} with FIT file path: {fit_file_path}")
        return self.database.update_workout_fit_path(workout_id, fit_file_path)
    
    def delete_workout(self, workout_id: int) -> bool:
        """
        Delete a workout and its associated data.
        
        Args:
            workout_id: ID of the workout to delete
            
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Deleting workout {workout_id}")
        
        # Check if this is the active workout
        if self.active_workout_id == workout_id:
            logger.warning(f"Cannot delete active workout {workout_id}. Ending it first.")
            self.end_workout()
        
        # Get the workout info before deletion (for fit file cleanup)
        workout_info = self.database.get_workout(workout_id)
        
        # Delete the workout from the database
        success = self.database.delete_workout(workout_id)
        
        if success and workout_info and workout_info.get('fit_file_path'):
            # Try to delete associated FIT file if it exists
            fit_file_path = workout_info['fit_file_path']
            try:
                if os.path.exists(fit_file_path):
                    os.remove(fit_file_path)
                    logger.info(f"Deleted FIT file: {fit_file_path}")
            except Exception as e:
                # Log but don't fail if file deletion fails
                logger.warning(f"Could not delete FIT file {fit_file_path}: {str(e)}")
        
        # Notify status
        self._notify_status("workout_deleted", {"workout_id": workout_id, "success": success})
        
        return success


# Example usage
if __name__ == "__main__":
    import asyncio
    from ..ftms.ftms_manager import FTMSDeviceManager
    
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
