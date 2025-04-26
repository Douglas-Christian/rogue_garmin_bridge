#!/usr/bin/env python3
"""
FIT File Converter Module for Rogue to Garmin Bridge

This module handles conversion of workout data to Garmin FIT format.
"""

import os
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta

from fit_tool.fit_file_builder import FitFileBuilder
from fit_tool.profile.messages.file_id_message import FileIdMessage
from fit_tool.profile.messages.device_info_message import DeviceInfoMessage
from fit_tool.profile.messages.event_message import EventMessage
from fit_tool.profile.messages.record_message import RecordMessage
from fit_tool.profile.messages.lap_message import LapMessage
from fit_tool.profile.messages.session_message import SessionMessage
from fit_tool.profile.messages.activity_message import ActivityMessage
from fit_tool.profile.profile_type import Sport, SubSport, LapTrigger, SessionTrigger, Event, EventType, Manufacturer, FileType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('fit_converter')

class FITConverter:
    """
    FIT File Converter class for converting workout data to Garmin FIT format.
    """
    
    def __init__(self, output_dir: str):
        """
        Initialize the FIT converter.
        
        Args:
            output_dir: Directory to save FIT files
        """
        self.output_dir = output_dir
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
    
    def convert_workout(self, workout_data: Dict[str, Any], user_profile: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Convert workout data to FIT file.
        
        Args:
            workout_data: Processed workout data
            user_profile: User profile data
            
        Returns:
            Path to generated FIT file or None if error
        """
        try:
            # Check workout type
            workout_type = workout_data.get('workout_type', '').lower()
            
            if workout_type == 'bike':
                return self.convert_bike_workout(workout_data, user_profile)
            elif workout_type == 'rower':
                return self.convert_rower_workout(workout_data, user_profile)
            else:
                logger.error(f"Unsupported workout type: {workout_type}")
                return None
        except Exception as e:
            logger.error(f"Error converting workout to FIT: {str(e)}")
            return None
    
    def convert_bike_workout(self, workout_data: Dict[str, Any], user_profile: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Convert bike workout data to FIT file.
        
        Args:
            workout_data: Processed workout data
            user_profile: User profile data
            
        Returns:
            Path to generated FIT file or None if error
        """
        try:
            # Extract data series
            data_series = workout_data.get('data_series', {})
            
            # Extract arrays from data series (ensure these are defined)
            timestamps = data_series.get('timestamps', [])
            absolute_timestamps = data_series.get('absolute_timestamps', [])
            powers = data_series.get('powers', [])
            cadences = data_series.get('cadences', [])
            heart_rates = data_series.get('heart_rates', [])
            speeds = data_series.get('speeds', [])
            distances = data_series.get('distances', [])
            
            # Extract summary metrics
            start_time = workout_data.get('start_time', datetime.now())
            total_duration = workout_data.get('total_duration', 0)
            total_distance = workout_data.get('total_distance', 0)
            total_calories = workout_data.get('total_calories', 0)
            avg_power = workout_data.get('avg_power', 0)
            max_power = workout_data.get('max_power', 0)
            normalized_power = workout_data.get('normalized_power', 0)
            avg_cadence = workout_data.get('avg_cadence', 0)
            max_cadence = workout_data.get('max_cadence', 0)
            avg_heart_rate = workout_data.get('avg_heart_rate', 0)
            max_heart_rate = workout_data.get('max_heart_rate', 0)
            avg_speed = workout_data.get('avg_speed', 0)
            max_speed = workout_data.get('max_speed', 0)
            
            # Create FIT file builder
            builder = FitFileBuilder()
            
            # Convert start time to timestamp
            if isinstance(start_time, datetime):
                start_timestamp = int(start_time.timestamp())
            else:
                start_timestamp = int(datetime.now().timestamp())
            
            # Add File ID message
            file_id_msg = FileIdMessage()
            file_id_msg.type = FileType.ACTIVITY
            file_id_msg.manufacturer = Manufacturer.DEVELOPMENT
            file_id_msg.product = 0
            file_id_msg.time_created = start_timestamp
            builder.add(file_id_msg)
            
            # Add Device Info message
            device_info_msg = DeviceInfoMessage()
            device_info_msg.timestamp = start_timestamp
            device_info_msg.manufacturer = Manufacturer.DEVELOPMENT
            device_info_msg.product = 0
            device_info_msg.device_index = 0
            device_info_msg.serial_number = 0
            device_info_msg.software_version = 100
            device_info_msg.hardware_version = 1
            builder.add(device_info_msg)
            
            # Add Event message (start)
            event_msg = EventMessage()
            event_msg.timestamp = start_timestamp
            event_msg.event = Event.TIMER
            event_msg.event_type = EventType.START
            builder.add(event_msg)
            
            # Add Record messages
            for i in range(len(timestamps)):
                # Calculate timestamp
                if i < len(absolute_timestamps) and isinstance(absolute_timestamps[i], datetime):
                    timestamp = int(absolute_timestamps[i].timestamp())
                else:
                    timestamp = start_timestamp + (timestamps[i] if i < len(timestamps) else 0)
                
                # Create record message
                record_msg = RecordMessage()
                record_msg.timestamp = timestamp
                
                # Set power
                if i < len(powers):
                    record_msg.power = int(powers[i])
                
                # Set cadence
                if i < len(cadences):
                    record_msg.cadence = int(cadences[i])
                
                # Set heart rate
                if i < len(heart_rates) and heart_rates[i] > 0:
                    record_msg.heart_rate = int(heart_rates[i])
                
                # Set speed
                if i < len(speeds):
                    # Convert km/h to m/s
                    record_msg.speed = float(speeds[i]) / 3.6
                
                # Set distance
                if i < len(distances):
                    record_msg.distance = float(distances[i])
                
                builder.add(record_msg)
            
            # Add Lap message
            lap_msg = LapMessage()
            lap_msg.timestamp = start_timestamp + total_duration
            lap_msg.start_time = start_timestamp
            lap_msg.total_elapsed_time = float(total_duration)
            lap_msg.total_timer_time = float(total_duration)
            lap_msg.total_distance = float(total_distance)
            lap_msg.total_calories = int(total_calories)
            lap_msg.avg_power = int(avg_power)
            lap_msg.max_power = int(max_power)
            lap_msg.avg_cadence = int(avg_cadence)
            lap_msg.max_cadence = int(max_cadence)
            if avg_heart_rate > 0:
                lap_msg.avg_heart_rate = int(avg_heart_rate)
            if max_heart_rate > 0:
                lap_msg.max_heart_rate = int(max_heart_rate)
            lap_msg.avg_speed = float(avg_speed) / 3.6  # Convert km/h to m/s
            lap_msg.max_speed = float(max_speed) / 3.6  # Convert km/h to m/s
            lap_msg.lap_trigger = LapTrigger.SESSION_END
            lap_msg.sport = Sport.CYCLING
            builder.add(lap_msg)
            
            # Add Session message
            session_msg = SessionMessage()
            session_msg.timestamp = start_timestamp + total_duration
            session_msg.start_time = start_timestamp
            session_msg.total_elapsed_time = float(total_duration)
            session_msg.total_timer_time = float(total_duration)
            session_msg.total_distance = float(total_distance)
            session_msg.total_calories = int(total_calories)
            session_msg.avg_power = int(avg_power)
            session_msg.max_power = int(max_power)
            session_msg.avg_cadence = int(avg_cadence)
            session_msg.max_cadence = int(max_cadence)
            if avg_heart_rate > 0:
                session_msg.avg_heart_rate = int(avg_heart_rate)
            if max_heart_rate > 0:
                session_msg.max_heart_rate = int(max_heart_rate)
            session_msg.avg_speed = float(avg_speed) / 3.6  # Convert km/h to m/s
            session_msg.max_speed = float(max_speed) / 3.6  # Convert km/h to m/s
            session_msg.first_lap_index = 0
            session_msg.num_laps = 1
            session_msg.trigger = SessionTrigger.ACTIVITY_END
            session_msg.sport = Sport.CYCLING
            session_msg.sub_sport = SubSport.INDOOR_CYCLING
            
            # Add normalized power if available
            if normalized_power > 0:
                session_msg.normalized_power = int(normalized_power)
            
            # Add user profile data if available
            if user_profile:
                if 'weight' in user_profile:
                    # Convert kg to g
                    session_msg.total_weight = int(user_profile['weight'] * 1000)
                
                if 'gender' in user_profile:
                    session_msg.gender = 0 if user_profile['gender'].lower() == 'female' else 1
                
                if 'age' in user_profile:
                    session_msg.age = user_profile['age']
            
            builder.add(session_msg)
            
            # Add Activity message
            activity_msg = ActivityMessage()
            activity_msg.timestamp = start_timestamp + total_duration
            activity_msg.total_timer_time = float(total_duration)
            activity_msg.num_sessions = 1
            activity_msg.type = 0  # Manual activity
            activity_msg.event = Event.ACTIVITY
            activity_msg.event_type = EventType.STOP
            builder.add(activity_msg)
            
            # Generate filename
            timestamp_str = datetime.fromtimestamp(start_timestamp).strftime('%Y%m%d_%H%M%S')
            filename = f"indoor_cycling_{timestamp_str}.fit"
            filepath = os.path.join(self.output_dir, filename)
            
            # Build and save FIT file
            fit_file = builder.build()
            fit_file.to_file(filepath)
            
            logger.info(f"Created FIT file: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error converting bike workout to FIT: {str(e)}")
            return None
    
    def convert_rower_workout(self, workout_data: Dict[str, Any], user_profile: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Convert rower workout data to FIT file.
        
        Args:
            workout_data: Processed workout data
            user_profile: User profile data
            
        Returns:
            Path to generated FIT file or None if error
        """
        try:
            # Extract data series
            data_series = workout_data.get('data_series', {})
            
            # Extract arrays from data series (ensure these are defined)
            timestamps = data_series.get('timestamps', [])
            absolute_timestamps = data_series.get('absolute_timestamps', [])
            powers = data_series.get('powers', [])
            stroke_rates = data_series.get('stroke_rates', [])
            heart_rates = data_series.get('heart_rates', [])
            distances = data_series.get('distances', [])
            
            # Extract summary metrics
            start_time = workout_data.get('start_time', datetime.now())
            total_duration = workout_data.get('total_duration', 0)
            total_distance = workout_data.get('total_distance', 0)
            total_calories = workout_data.get('total_calories', 0)
            avg_power = workout_data.get('avg_power', 0)
            max_power = workout_data.get('max_power', 0)
            normalized_power = workout_data.get('normalized_power', 0)
            avg_stroke_rate = workout_data.get('avg_stroke_rate', 0)
            max_stroke_rate = workout_data.get('max_stroke_rate', 0)
            avg_heart_rate = workout_data.get('avg_heart_rate', 0)
            max_heart_rate = workout_data.get('max_heart_rate', 0)
            total_strokes = workout_data.get('total_strokes', 0)
            
            # Create FIT file builder
            builder = FitFileBuilder()
            
            # Convert start time to timestamp
            if isinstance(start_time, datetime):
                start_timestamp = int(start_time.timestamp())
            else:
                start_timestamp = int(datetime.now().timestamp())
            
            # Add File ID message
            file_id_msg = FileIdMessage()
            file_id_msg.type = FileType.ACTIVITY
            file_id_msg.manufacturer = Manufacturer.DEVELOPMENT
            file_id_msg.product = 0
            file_id_msg.time_created = start_timestamp
            builder.add(file_id_msg)
            
            # Add Device Info message
            device_info_msg = DeviceInfoMessage()
            device_info_msg.timestamp = start_timestamp
            device_info_msg.manufacturer = Manufacturer.DEVELOPMENT
            device_info_msg.product = 0
            device_info_msg.device_index = 0
            device_info_msg.serial_number = 0
            device_info_msg.software_version = 100
            device_info_msg.hardware_version = 1
            builder.add(device_info_msg)
            
            # Add Event message (start)
            event_msg = EventMessage()
            event_msg.timestamp = start_timestamp
            event_msg.event = Event.TIMER
            event_msg.event_type = EventType.START
            builder.add(event_msg)
            
            # Add Record messages
            for i in range(len(timestamps)):
                # Calculate timestamp
                if i < len(absolute_timestamps) and isinstance(absolute_timestamps[i], datetime):
                    timestamp = int(absolute_timestamps[i].timestamp())
                else:
                    timestamp = start_timestamp + (timestamps[i] if i < len(timestamps) else 0)
                
                # Create record message
                record_msg = RecordMessage()
                record_msg.timestamp = timestamp
                
                # Set power
                if i < len(powers):
                    record_msg.power = int(powers[i])
                
                # Set cadence (stroke rate)
                if i < len(stroke_rates):
                    record_msg.cadence = int(stroke_rates[i])
                
                # Set heart rate
                if i < len(heart_rates) and heart_rates[i] > 0:
                    record_msg.heart_rate = int(heart_rates[i])
                
                # Set distance
                if i < len(distances):
                    record_msg.distance = float(distances[i])
                
                builder.add(record_msg)
            
            # Add Lap message
            lap_msg = LapMessage()
            lap_msg.timestamp = start_timestamp + total_duration
            lap_msg.start_time = start_timestamp
            lap_msg.total_elapsed_time = float(total_duration)
            lap_msg.total_timer_time = float(total_duration)
            lap_msg.total_distance = float(total_distance)
            lap_msg.total_calories = int(total_calories)
            lap_msg.avg_power = int(avg_power)
            lap_msg.max_power = int(max_power)
            lap_msg.avg_cadence = int(avg_stroke_rate)  # Use stroke rate as cadence
            lap_msg.max_cadence = int(max_stroke_rate)  # Use stroke rate as cadence
            if avg_heart_rate > 0:
                lap_msg.avg_heart_rate = int(avg_heart_rate)
            if max_heart_rate > 0:
                lap_msg.max_heart_rate = int(max_heart_rate)
            lap_msg.total_cycles = int(total_strokes)  # Use strokes as cycles
            lap_msg.lap_trigger = LapTrigger.SESSION_END
            lap_msg.sport = Sport.ROWING
            builder.add(lap_msg)
            
            # Add Session message
            session_msg = SessionMessage()
            session_msg.timestamp = start_timestamp + total_duration
            session_msg.start_time = start_timestamp
            session_msg.total_elapsed_time = float(total_duration)
            session_msg.total_timer_time = float(total_duration)
            session_msg.total_distance = float(total_distance)
            session_msg.total_calories = int(total_calories)
            session_msg.avg_power = int(avg_power)
            session_msg.max_power = int(max_power)
            session_msg.avg_cadence = int(avg_stroke_rate)  # Use stroke rate as cadence
            session_msg.max_cadence = int(max_stroke_rate)  # Use stroke rate as cadence
            if avg_heart_rate > 0:
                session_msg.avg_heart_rate = int(avg_heart_rate)
            if max_heart_rate > 0:
                session_msg.max_heart_rate = int(max_heart_rate)
            session_msg.total_cycles = int(total_strokes)  # Use strokes as cycles
            session_msg.first_lap_index = 0
            session_msg.num_laps = 1
            session_msg.trigger = SessionTrigger.ACTIVITY_END
            session_msg.sport = Sport.ROWING
            session_msg.sub_sport = SubSport.INDOOR_ROWING
            
            # Add normalized power if available
            if normalized_power > 0:
                session_msg.normalized_power = int(normalized_power)
            
            # Add user profile data if available
            if user_profile:
                if 'weight' in user_profile:
                    # Convert kg to g
                    session_msg.total_weight = int(user_profile['weight'] * 1000)
                
                if 'gender' in user_profile:
                    session_msg.gender = 0 if user_profile['gender'].lower() == 'female' else 1
                
                if 'age' in user_profile:
                    session_msg.age = user_profile['age']
            
            builder.add(session_msg)
            
            # Add Activity message
            activity_msg = ActivityMessage()
            activity_msg.timestamp = start_timestamp + total_duration
            activity_msg.total_timer_time = float(total_duration)
            activity_msg.num_sessions = 1
            activity_msg.type = 0  # Manual activity
            activity_msg.event = Event.ACTIVITY
            activity_msg.event_type = EventType.STOP
            builder.add(activity_msg)
            
            # Generate filename
            timestamp_str = datetime.fromtimestamp(start_timestamp).strftime('%Y%m%d_%H%M%S')
            filename = f"indoor_rowing_{timestamp_str}.fit"
            filepath = os.path.join(self.output_dir, filename)
            
            # Build and save FIT file
            fit_file = builder.build()
            fit_file.to_file(filepath)
            
            logger.info(f"Created FIT file: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error converting rower workout to FIT: {str(e)}")
            return None


# Example usage
if __name__ == "__main__":
    from datetime import datetime
    
    # Create sample processed data
    processed_data = {
        'workout_type': 'bike',
        'start_time': datetime.now(),
        'total_duration': 60,
        'total_distance': 500,
        'total_calories': 50,
        'avg_power': 150,
        'max_power': 200,
        'normalized_power': 160,
        'avg_cadence': 80,
        'max_cadence': 100,
        'avg_heart_rate': 130,
        'max_heart_rate': 150,
        'avg_speed': 25,
        'max_speed': 30,
        'data_series': {
            'timestamps': [0, 10, 20, 30, 40, 50, 60],
            'absolute_timestamps': [
                datetime.now(),
                datetime.now() + timedelta(seconds=10),
                datetime.now() + timedelta(seconds=20),
                datetime.now() + timedelta(seconds=30),
                datetime.now() + timedelta(seconds=40),
                datetime.now() + timedelta(seconds=50),
                datetime.now() + timedelta(seconds=60)
            ],
            'powers': [100, 120, 140, 160, 180, 200, 150],
            'cadences': [70, 75, 80, 85, 90, 95, 80],
            'heart_rates': [110, 120, 130, 140, 145, 150, 140],
            'speeds': [20, 22, 24, 26, 28, 30, 25],
            'distances': [0, 60, 130, 210, 300, 400, 500]
        }
    }
    
    # Create user profile
    user_profile = {
        'name': 'John Doe',
        'age': 35,
        'weight': 75.0,
        'height': 180.0,
        'gender': 'male',
        'max_heart_rate': 185,
        'resting_heart_rate': 60,
        'ftp': 250
    }
    
    # Create FIT converter
    converter = FITConverter("./fit_files")
    
    # Convert workout to FIT
    fit_file_path = converter.convert_workout(processed_data, user_profile)
    
    print(f"FIT file created: {fit_file_path}")
