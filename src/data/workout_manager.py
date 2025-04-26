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

from ..ftms.ftms_manager import FTMSDeviceManager
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
        
        # Calculate final summary metrics
        self._calculate_summary_metrics()
        
        # End workout in database
        success = self.database.end_workout(
            self.active_workout_id,
            summary=self.summary_metrics
        )
        
        if success:
            # Notify status
            self._notify_status('workout_ended', {
                'workout_id': self.active_workout_id,
                'device_id': self.active_device_id,
                'workout_type': self.workout_type,
                'duration': int(time.time() - self.workout_start_time),
                'summary': self.summary_metrics
            })
            
            logger.info(f"Ended workout {self.active_workout_id}")
            
            # Clear current workout state
            workout_id = self.active_workout_id
            self.active_workout_id = None
            self.active_device_id = None
            self.workout_start_time = None
            self.workout_type = None
            self.data_points = []
            self.summary_metrics = {}
            
            return True
        else:
            logger.error(f"Failed to end workout {self.active_workout_id}")
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
        # Most metrics ar
(Content truncated due to size limit. Use line ranges to read in chunks)