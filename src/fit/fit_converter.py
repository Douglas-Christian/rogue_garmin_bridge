#!/usr/bin/env python3
"""
FIT File Converter Module for Rogue to Garmin Bridge

This module handles conversion of processed workout data to Garmin FIT format.
"""

import os
import logging
import time
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
from fit_tool.profile.profile_type import (
    FileType, Manufacturer, Sport, SubSport, 
    Event, EventType, LapTrigger, SessionTrigger
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('fit_converter')

class FITConverter:
    """
    Class for converting processed workout data to Garmin FIT format.
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
    
    def convert_workout(self, processed_data: Dict[str, Any], 
                       user_profile: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Convert processed workout data to FIT file.
        
        Args:
            processed_data: Processed workout data
            user_profile: User profile information (optional)
            
        Returns:
            Path to generated FIT file or None if conversion failed
        """
        if not processed_data:
            logger.warning("No processed data to convert")
            return None
        
        workout_type = processed_data.get('workout_type')
        
        if workout_type == 'bike':
            return self._convert_bike_workout(processed_data, user_profile)
        elif workout_type == 'rower':
            return self._convert_rower_workout(processed_data, user_profile)
        else:
            logger.warning(f"Unknown workout type: {workout_type}")
            return None
    
    def _convert_bike_workout(self, processed_data: Dict[str, Any], 
                            user_profile: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Convert bike workout data to FIT file.
        
        Args:
            processed_data: Processed bike workout data
            user_profile: User profile information (optional)
            
        Returns:
            Path to generated FIT file or None if conversion failed
        """
        try:
            # Create FIT file builder
            builder = FitFileBuilder()
            
            # Extract data series
            data_series = processed_data.get('data_series', {})
            timestamps = data_series.get('timestamps', [])
            absolute_timestamps = data_series.get('absolute_timestamps', [])
            powers = data_series.get('powers', [])
            cadences = data_series.get('cadences', [])
            heart_rates = data_series.get('heart_rates', [])
            speeds = data_series.get('speeds', [])
            distances = data_series.get('distances', [])
            
            if not timestamps or not absolute_timestamps:
                logger.warning("No timestamp data available")
                return None
            
            # Extract summary metrics
            start_time = processed_data.get('start_time')
            total_duration = processed_data.get('total_duration', 0)
            total_distance = processed_data.get('total_distance', 0)
            total_calories = processed_data.get('total_calories', 0)
            avg_power = processed_data.get('avg_power', 0)
            max_power = processed_data.get('max_power', 0)
            normalized_power = processed_data.get('normalized_power', 0)
            avg_cadence = processed_data.get('avg_cadence', 0)
            max_cadence = processed_data.get('max_cadence', 0)
            avg_heart_rate = processed_data.get('avg_heart_rate', 0)
            max_heart_rate = processed_data.get('max_heart_rate', 0)
            avg_speed = processed_data.get('avg_speed', 0)
            max_speed = processed_data.get('max_speed', 0)
            
            # Convert start_time to timestamp if it's a datetime
            if isinstance(start_time, datetime):
                start_timestamp = int(start_time.timestamp())
            else:
                start_timestamp = int(time.time())
            
            # Add File ID message
            file_id_msg = FileIdMessage()
            file_id_msg.type = FileType.ACTIVITY
            file_id_msg.manufacturer = Manufacturer.DEVELOPMENT.value
            file_id_msg.product = 0
            file_id_msg.time_created = start_timestamp
            file_id_msg.serial_number = 0x12345678
            builder.add(file_id_msg)
            
            # Add Device Info message
            device_info_msg = DeviceInfoMessage()
            device_info_msg.timestamp = start_timestamp
            device_info_msg.manufacturer = Manufacturer.DEVELOPMENT.value
            device_info_msg.product = 0
            device_info_msg.device_index = 0
            device_info_msg.serial_number = 0x12345678
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
                record_msg = RecordMessage()
                
                # Set timestamp
                if i < len(absolute_timestamps):
                    record_msg.timestamp = int(absolute_timestamps[i].timestamp())
                else:
                    record_msg.timestamp = start_timestamp + timestamps[i]
                
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
                    record_msg.speed = int(speeds[i] * 1000 / 3600)
                
                # Set distance
                if i < len(distances):
                    record_msg.distance = float(distances[i])
                
                builder.add(record_msg)
            
            # Add Event message (stop)
            event_msg = EventMessage()
            event_msg.timestamp = start_timestamp + total_duration
            event_msg.event = Event.TIMER
            event_msg.event_type = EventType.STOP
            builder.add(event_msg)
            
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
            lap_msg.avg_speed = int(avg_speed * 1000 / 3600)  # Convert km/h to m/s
            lap_msg.max_speed = int(max_speed * 1000 / 3600)  # Convert km/h to m/s
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
            session_msg.avg_speed = int(avg_speed * 1000 / 3600)  # Convert km/h to m/s
            session_msg.max_speed = int(max_speed * 1000 / 3600)  # Convert km/h to m/s
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
    
    def _convert_rower_workout(self, processed_data: Dict[str, Any], 
                             user_profile: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Convert rower workout data to FIT file.
        
        Args:
            processed_data: Processed rower workout data
            user_profile: User profile information (optional)
            
        Returns:
            Path to generated FIT file or None if conversion failed
        """
        try:
            # Create FIT file builder
            builder = FitFileBuilder()
            
            # Extract data series
            data_series = processed_data.get('data_series', {})
            timestamps = data_series.get('timestamps', [])
            absolute_timestamps = data_series.get('absolute_timestamps', [])
            powers = data_series.get('powers', [])
            stroke_rates = data_series.get('stroke_rates', [])
            heart_rates = data_series.get('heart_rates', [])
            distances = data_series.get('distances', [])
            
            if not timestamps or not absolute_timestamps:
                logger.warning("No timestamp data available")
                return None
            
            # Extract summary metrics
            start_time = processed_data.get('start_time')
            total_duration = processed_data.get('total_duration', 0)
            total_distance = processed_data.get('total_distance', 0)
            total_calories = processed_data.get('total_calories', 0)
            avg_power = processed_data.get('avg_power', 0)
            max_power = processed_data.get('max_power', 0)
            normalized_power = processed_data.get('normalized_power', 0)
            avg_stroke_rate = processed_data.get('avg_stroke_rate', 0)
            max_stroke_rate = processed_data.get('max_stroke_rate', 0)
            avg_heart_rate = processed_data.get('avg_heart_rate', 0)
            max_heart_rate = processed_data.get('max_heart_rate', 0)
            total_strokes = processed_data.get('total_strokes', 0)
            
            # Convert start_time to timestamp if it's a datetime
            if isinstance(start_time, datetime):
                start_timestamp = int(start_time.timestamp())
            else:
                start_timestamp = int(time.time())
            
            # Add File ID message
            file_id_msg = FileIdMessage()
            file_id_msg.type = FileType.ACTIVITY
            file_id_msg.manufacturer = Manufacturer.DEVELOPMENT.value
            file_id_msg.product = 0
            file_id_msg.time_created = start_timestamp
            file_id_msg.serial_number = 0x12345678
            builder.add(file_id_msg)
            
            # Add Device Info message
            device_info_msg = DeviceInfoMessage()
            device_info_msg.timestamp = start_timestamp
            device_info_msg.manufacturer = Manufacturer.DEVELOPMENT.value
            device_info_msg.product = 0
            device_info_msg.device_index = 0
            device_info_msg.serial_number = 0x12345678
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
                record_msg = RecordMessage()
                
                # Set timestamp
                if i < len(absolute_timestamps):
                    record_msg.timestamp = int(absolute_timestamps[i].timestamp())
                else:
                    record_msg.timestamp = start_timestamp + timestamps[i]
                
                # Set power
                if i < len(powers):
                    record_msg.power = int(powers[i])
(Content truncated due to size limit. Use line ranges to read in chunks)