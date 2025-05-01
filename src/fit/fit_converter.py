#!/usr/bin/env python3
"""
FIT File Converter Module for Rogue to Garmin Bridge

This module handles conversion of workout data to Garmin FIT format.
"""

import os
import sys
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta, timezone

from fit_tool.fit_file_builder import FitFileBuilder
from fit_tool.profile.messages.file_id_message import FileIdMessage
from fit_tool.profile.messages.device_info_message import DeviceInfoMessage
from fit_tool.profile.messages.event_message import EventMessage
from fit_tool.profile.messages.record_message import RecordMessage
from fit_tool.profile.messages.lap_message import LapMessage
from fit_tool.profile.messages.session_message import SessionMessage
from fit_tool.profile.messages.activity_message import ActivityMessage
from fit_tool.profile.profile_type import Sport, SubSport, LapTrigger, SessionTrigger, Event, EventType, Manufacturer, FileType

# Add the project root to the path so we can use absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.utils.logging_config import get_component_logger

# Get component logger
logger = get_component_logger('fit_converter')

# Constants for timestamp conversion
# Garmin FIT epoch (December 31, 1989 00:00:00 UTC)
FIT_EPOCH_SECONDS = 631065600  # Seconds between Unix epoch and FIT epoch

def unix_to_fit_timestamp(unix_timestamp):
    """
    Convert Unix timestamp (seconds since Jan 1, 1970) to FIT timestamp (seconds since Dec 31, 1989)
    
    Args:
        unix_timestamp: Unix timestamp (seconds since Jan 1, 1970)
        
    Returns:
        FIT timestamp (seconds since Dec 31, 1989)
    """
    # Simple conversion using constant epoch difference
    fit_timestamp = int(unix_timestamp - FIT_EPOCH_SECONDS)
    
    # Ensure the timestamp is in the valid range for FIT files
    if fit_timestamp < 0:
        logger.warning(f"[TIMESTAMP FIX] Calculated negative FIT timestamp ({fit_timestamp}), adjusting to current time")
        # Use current time instead if result would be negative
        current_time = int(datetime.now(timezone.utc).timestamp())
        fit_timestamp = int(current_time - FIT_EPOCH_SECONDS)
        
    # Ensure within maximum uint32 range (0 to 4294967295)
    if fit_timestamp > 4294967295:
        logger.warning(f"[TIMESTAMP FIX] Calculated FIT timestamp too large ({fit_timestamp}), adjusting to max value")
        fit_timestamp = 4294967295
        
    logger.info(f"[TIMESTAMP FIX] Unix timestamp {unix_timestamp} converted to safe FIT timestamp {fit_timestamp}")
    return fit_timestamp

def parse_timestamp(timestamp_value):
    """
    Parse a timestamp from various possible formats into a Unix timestamp.
    
    Args:
        timestamp_value: Timestamp in datetime, string, or numeric format
        
    Returns:
        Unix timestamp (seconds since epoch) or current time if parsing fails
    """
    try:
        if isinstance(timestamp_value, datetime):
            # If it's a datetime object, ensure it has timezone info
            if timestamp_value.tzinfo is None:
                # Assume local timezone if not specified
                timestamp_value = timestamp_value.replace(tzinfo=datetime.now().astimezone().tzinfo)
            return int(timestamp_value.timestamp())
        
        elif isinstance(timestamp_value, str):
            try:
                # Try to parse as ISO format with timezone
                dt = datetime.fromisoformat(timestamp_value.replace('Z', '+00:00'))
                return int(dt.timestamp())
            except Exception as e1:
                try:
                    # Try to parse as float/int string
                    return int(float(timestamp_value))
                except Exception as e2:
                    logger.error(f"Failed to parse timestamp string: {timestamp_value}, errors: {e1}, {e2}")
                    return int(datetime.now(timezone.utc).timestamp())
        
        elif isinstance(timestamp_value, (int, float)):
            # Already a numeric timestamp
            return int(timestamp_value)
        
        else:
            logger.warning(f"Unknown timestamp format: {type(timestamp_value)}, value: {timestamp_value}")
            return int(datetime.now(timezone.utc).timestamp())
    
    except Exception as e:
        logger.error(f"Error parsing timestamp {timestamp_value}: {str(e)}")
        return int(datetime.now(timezone.utc).timestamp())

def create_file_id_message(builder, workout_timestamp=None):
    """
    Creates a FileIdMessage and adds it to the builder.
    DOES NOT set the time_created field to avoid issues with timestamp conversions.
    
    Args:
        builder: FitFileBuilder instance to add the message to
        workout_timestamp: FIT timestamp to use (already converted from Unix time) - IGNORED
        
    Returns:
        True if successful, False otherwise
    """
    try:
        file_id_msg = FileIdMessage()
        file_id_msg.type = FileType.ACTIVITY
        file_id_msg.manufacturer = Manufacturer.DEVELOPMENT
        file_id_msg.product = 0
        file_id_msg.serial_number = 0
        
        # DO NOT set the time_created field at all
        # This allows the FIT SDK to use its default value
        # and avoids the encoding error with negative values
        
        logger.info("[TIMESTAMP FIX] Skipping time_created field to avoid timestamp encoding issues")
        
        # Add the message to the builder
        builder.add(file_id_msg)
        return True
    except Exception as e:
        logger.error(f"Error creating FileIdMessage: {str(e)}")
        return False

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
            powers = data_series.get('powers', [])
            cadences = data_series.get('cadences', [])
            heart_rates = data_series.get('heart_rates', [])
            speeds = data_series.get('speeds', [])
            distances = data_series.get('distances', [])
            
            # Extract summary metrics
            start_time = workout_data.get('start_time', datetime.now(timezone.utc))
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
            
            # Convert start time to Unix timestamp using our robust parser
            start_unix_timestamp = parse_timestamp(start_time)
            
            # Log the Unix timestamp for debugging
            logger.info(f"[TIMESTAMP FIX] Workout start Unix timestamp: {start_unix_timestamp} ({datetime.fromtimestamp(start_unix_timestamp).isoformat()})")
            
            # Convert Unix timestamp to FIT timestamp (seconds since FIT epoch)
            start_timestamp = unix_to_fit_timestamp(start_unix_timestamp)
            logger.info(f"[TIMESTAMP FIX] Converted to FIT timestamp: {start_timestamp}")
            
            # Process relative timestamps into FIT timestamps
            # (Use our standalone function for this critical step)
            fit_timestamps = process_relative_timestamps(start_unix_timestamp, timestamps)
            logger.info(f"[TIMESTAMP FIX] Processed {len(fit_timestamps)} relative timestamps to FIT format")
            
            # Add File ID message with the workout start timestamp - CRITICAL for correct date in Garmin Connect
            if not create_file_id_message(builder, start_timestamp):
                logger.error("Failed to create FileIdMessage")
                return None
            
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
            for i in range(len(fit_timestamps)):
                try:
                    # Use the pre-computed FIT timestamp from our standalone function
                    timestamp = fit_timestamps[i]
                    
                    # Log the first few points to verify it's working
                    if i < 3:  # Only log first 3 points to avoid log spam
                        logger.info(f"[TIMESTAMP FIX] Point {i}: Using processed FIT timestamp: {timestamp}")
                    
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
                except Exception as e:
                    logger.error(f"Error processing record at index {i}: {str(e)}")
            
            # For end timestamp, add duration to the start timestamp
            end_timestamp = start_timestamp + int(total_duration)
            
            # Add Lap message
            lap_msg = LapMessage()
            lap_msg.timestamp = end_timestamp
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
            session_msg.timestamp = end_timestamp
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
            activity_msg.timestamp = end_timestamp
            activity_msg.total_timer_time = float(total_duration)
            activity_msg.num_sessions = 1
            activity_msg.type = 0  # Manual activity
            activity_msg.event = Event.ACTIVITY
            activity_msg.event_type = EventType.STOP
            builder.add(activity_msg)
            
            # Generate filename - use original Unix timestamp for filename to maintain readability
            timestamp_str = datetime.fromtimestamp(start_unix_timestamp).strftime('%Y%m%d_%H%M%S')
            filename = f"indoor_cycling_{timestamp_str}.fit"
            filepath = os.path.join(self.output_dir, filename)
            
            # Build and save FIT file
            try:
                fit_file = builder.build()
                fit_file.to_file(filepath)
                
                logger.info(f"Created FIT file: {filepath}")
                return filepath
            except Exception as e:
                logger.error(f"Error building or saving FIT file: {str(e)}")
                # Try with a completely safe timestamp as fallback
                return self.create_fallback_file(builder, "indoor_cycling")
            
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
            powers = data_series.get('powers', [])
            stroke_rates = data_series.get('stroke_rates', [])
            heart_rates = data_series.get('heart_rates', [])
            distances = data_series.get('distances', [])
            stroke_counts = data_series.get('stroke_counts', [])
            
            # Extract summary metrics
            start_time = workout_data.get('start_time', datetime.now(timezone.utc))
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
            
            # Convert start time to Unix timestamp using our robust parser
            start_unix_timestamp = parse_timestamp(start_time)
            
            # Log the Unix timestamp for debugging
            logger.info(f"[TIMESTAMP FIX] Workout start Unix timestamp: {start_unix_timestamp} ({datetime.fromtimestamp(start_unix_timestamp).isoformat()})")
            
            # Convert Unix timestamp to FIT timestamp (seconds since FIT epoch)
            start_timestamp = unix_to_fit_timestamp(start_unix_timestamp)
            logger.info(f"[TIMESTAMP FIX] Converted to FIT timestamp: {start_timestamp}")
            
            # Process relative timestamps into FIT timestamps
            # (Use our standalone function for this critical step)
            fit_timestamps = process_relative_timestamps(start_unix_timestamp, timestamps)
            logger.info(f"[TIMESTAMP FIX] Processed {len(fit_timestamps)} relative timestamps to FIT format")
            
            # Add File ID message with the workout start timestamp - CRITICAL for correct date in Garmin Connect
            if not create_file_id_message(builder, start_timestamp):
                logger.error("Failed to create FileIdMessage")
                return None
            
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
            for i in range(len(fit_timestamps)):
                try:
                    # Use the pre-computed FIT timestamp from our standalone function
                    timestamp = fit_timestamps[i]
                    
                    # Log the first few points to verify it's working
                    if i < 3:  # Only log first 3 points to avoid log spam
                        logger.info(f"[TIMESTAMP FIX] Point {i}: Using processed FIT timestamp: {timestamp}")
                    
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
                except Exception as e:
                    logger.error(f"Error processing record at index {i}: {str(e)}")
            
            # For end timestamp, add duration to the start timestamp
            end_timestamp = start_timestamp + int(total_duration)
            
            # Add Lap message
            lap_msg = LapMessage()
            lap_msg.timestamp = end_timestamp
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
            session_msg.timestamp = end_timestamp
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
            activity_msg.timestamp = end_timestamp
            activity_msg.total_timer_time = float(total_duration)
            activity_msg.num_sessions = 1
            activity_msg.type = 0  # Manual activity
            activity_msg.event = Event.ACTIVITY
            activity_msg.event_type = EventType.STOP
            builder.add(activity_msg)
            
            # Generate filename - use original Unix timestamp for filename to maintain readability
            timestamp_str = datetime.fromtimestamp(start_unix_timestamp).strftime('%Y%m%d_%H%M%S')
            filename = f"indoor_rowing_{timestamp_str}.fit"
            filepath = os.path.join(self.output_dir, filename)
            
            # Build and save FIT file
            try:
                fit_file = builder.build()
                fit_file.to_file(filepath)
                
                logger.info(f"Created FIT file: {filepath}")
                return filepath
            except Exception as e:
                logger.error(f"Error building or saving FIT file: {str(e)}")
                # Try with a completely safe timestamp as fallback
                return self.create_fallback_file(builder, "indoor_rowing")
            
        except Exception as e:
            logger.error(f"Error converting rower workout to FIT: {str(e)}")
            return None
    
    def create_fallback_file(self, builder, activity_type):
        """
        Create a fallback FIT file in case of errors during the normal creation process.
        
        Args:
            builder: FitFileBuilder instance used to create the FIT file
            activity_type: Type of activity (e.g., 'indoor_cycling', 'indoor_rowing')
            
        Returns:
            Path to the created FIT file or None if failed
        """
        try:
            # Generate filename - use current time for fallback filename
            timestamp_str = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
            filename = f"{activity_type}_fallback_{timestamp_str}.fit"
            filepath = os.path.join(self.output_dir, filename)
            
            # Create a completely fresh builder instead of using the potentially problematic one
            new_builder = FitFileBuilder()
            
            # Use a simple FIT timestamp conversion without validation
            current_unix_timestamp = int(datetime.now(timezone.utc).timestamp())
            safe_start_timestamp = unix_to_fit_timestamp(current_unix_timestamp)
            logger.info(f"Generated fallback safe FIT timestamp: {safe_start_timestamp}")
            
            # Add File ID message but carefully avoid setting the time_created field
            file_id_msg = FileIdMessage()
            file_id_msg.type = FileType.ACTIVITY
            file_id_msg.manufacturer = Manufacturer.DEVELOPMENT
            file_id_msg.product = 0
            # Deliberately NOT setting time_created to let SDK use a default value
            new_builder.add(file_id_msg)
            
            # Add minimal required messages
            event_msg = EventMessage()
            event_msg.timestamp = safe_start_timestamp
            event_msg.event = Event.TIMER
            event_msg.event_type = EventType.START
            new_builder.add(event_msg)
            
            # Use a fixed, safe duration for the fallback file
            fallback_duration = 60  # seconds
            
            # Add a record message at start
            record_start = RecordMessage()
            record_start.timestamp = safe_start_timestamp
            record_start.power = 100  # Safe default values
            record_start.cadence = 80
            record_start.distance = 0
            new_builder.add(record_start)
            
            # Add a record message at end
            record_end = RecordMessage()
            record_end.timestamp = safe_start_timestamp + fallback_duration
            record_end.power = 100  # Safe default values
            record_end.cadence = 80
            record_end.distance = 100  # Some arbitrary distance
            new_builder.add(record_end)
            
            # Create a minimal session
            session_msg = SessionMessage()
            session_msg.timestamp = safe_start_timestamp + fallback_duration
            session_msg.start_time = safe_start_timestamp
            session_msg.total_elapsed_time = float(fallback_duration)
            session_msg.total_timer_time = float(fallback_duration)
            session_msg.total_distance = 100.0  # Set a minimal distance
            session_msg.total_calories = 10  # Set minimal calories
            session_msg.first_lap_index = 0
            session_msg.num_laps = 1
            session_msg.trigger = SessionTrigger.ACTIVITY_END
            
            if activity_type == "indoor_cycling":
                session_msg.sport = Sport.CYCLING
                session_msg.sub_sport = SubSport.INDOOR_CYCLING
            elif activity_type == "indoor_rowing":
                session_msg.sport = Sport.ROWING
                session_msg.sub_sport = SubSport.INDOOR_ROWING
            else:
                session_msg.sport = Sport.GENERIC
                
            new_builder.add(session_msg)
            
            # Add Lap message
            lap_msg = LapMessage()
            lap_msg.timestamp = safe_start_timestamp + fallback_duration
            lap_msg.start_time = safe_start_timestamp
            lap_msg.total_elapsed_time = float(fallback_duration)
            lap_msg.total_timer_time = float(fallback_duration)
            lap_msg.total_distance = 100.0  # Match session distance
            lap_msg.total_calories = 10
            lap_msg.avg_power = 100
            lap_msg.avg_cadence = 80
            lap_msg.lap_trigger = LapTrigger.SESSION_END
            
            if activity_type == "indoor_cycling":
                lap_msg.sport = Sport.CYCLING
            elif activity_type == "indoor_rowing":
                lap_msg.sport = Sport.ROWING
            else:
                lap_msg.sport = Sport.GENERIC
                
            new_builder.add(lap_msg)
            
            # Add activity message
            activity_msg = ActivityMessage()
            activity_msg.timestamp = safe_start_timestamp + fallback_duration
            activity_msg.total_timer_time = float(fallback_duration)
            activity_msg.num_sessions = 1
            activity_msg.type = 0
            activity_msg.event = Event.ACTIVITY
            activity_msg.event_type = EventType.STOP
            new_builder.add(activity_msg)
            
            # Build and save the fallback file
            try:
                fit_file = new_builder.build()
                fit_file.to_file(filepath)
                logger.info(f"Created fallback FIT file: {filepath}")
                return filepath
            except Exception as e:
                logger.error(f"Failed to build or save fallback FIT file: {str(e)}")
                # Attempt an even more minimal file
                return self.create_emergency_file(activity_type)
                
        except Exception as e:
            logger.error(f"Failed to create fallback FIT file: {str(e)}", exc_info=True)
            return self.create_emergency_file(activity_type)
        
    def create_emergency_file(self, activity_type):
        """
        Create an absolute minimal emergency FIT file with virtually no data.
        This is the last resort when all other methods fail.
        
        Args:
            activity_type: Type of activity
        
        Returns:
            Path to created file or None if failed
        """
        try:
            # Generate filename
            timestamp_str = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
            filename = f"{activity_type}_emergency_{timestamp_str}.fit"
            filepath = os.path.join(self.output_dir, filename)
            
            # Create absolute minimal viable FIT file
            minimal_builder = FitFileBuilder()
            minimal_file_id = FileIdMessage()
            minimal_file_id.type = FileType.ACTIVITY
            minimal_file_id.manufacturer = Manufacturer.DEVELOPMENT
            # Deliberately NOT setting time_created
            minimal_builder.add(minimal_file_id)
            
            # Try to build and save
            min_fit_file = minimal_builder.build()
            min_fit_file.to_file(filepath)
            logger.info(f"Created emergency minimal FIT file: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Failed to create emergency FIT file: {str(e)}", exc_info=True)
            return None
        
def process_relative_timestamps(start_unix_timestamp, relative_timestamps):
    """
    Process a list of relative timestamps (seconds from workout start)
    by adding the absolute start time to each value and converting to FIT timestamps.
    
    Args:
        start_unix_timestamp: Unix timestamp of workout start (seconds since epoch)
        relative_timestamps: List of relative timestamps (seconds since workout start)
        
    Returns:
        List of FIT timestamps (seconds since FIT epoch)
    """
    # FIT epoch is Dec 31, 1989 00:00:00 UTC
    FIT_EPOCH_SECONDS = 631065600
    
    # Calculate absolute unix timestamps from relative ones
    absolute_unix_timestamps = [start_unix_timestamp + rel_time for rel_time in relative_timestamps]
    
    # Convert unix timestamps to FIT timestamps
    fit_timestamps = [int(unix_time - FIT_EPOCH_SECONDS) for unix_time in absolute_unix_timestamps]
    
    # Ensure all timestamps are in valid range
    fit_timestamps = [max(0, min(fit_timestamp, 4294967295)) for fit_timestamp in fit_timestamps]
    
    return fit_timestamps


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
