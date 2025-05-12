#!/usr/bin/env python3
"""
FIT File Converter Module for Rogue to Garmin Bridge

This module handles conversion of processed workout data to Garmin FIT format.
"""

import os
import logging
import time
import traceback
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
from fit_tool.profile.profile_type import (
    FileType, Manufacturer, Sport, SubSport, 
    Event, EventType, LapTrigger, SessionTrigger
)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Changed to DEBUG for more detailed logs
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('fit_converter')

# FIT timestamp constants
# NOTE: fit_tool expects timestamps in milliseconds since Unix epoch (1970-01-01)
# It applies an offset of -631065600000 ms and a scale of 0.001 internally
FIT_EPOCH_OFFSET_MS = 631065600000  # Milliseconds from Unix epoch to FIT epoch

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
    
    def convert_workout(self, processed_data, user_profile=None):
        """
        Convert a processed workout to a FIT file.
        
        Args:
            processed_data: Dictionary of processed workout data
            user_profile: User profile information (optional)
            
        Returns:
            Path to the generated FIT file
        """
        try:
            # Extract data elements from processed data
            workout_type = processed_data.get('workout_type', 'bike')
            if not workout_type:
                workout_type = 'bike'  # Default to bike if not specified
            
            start_time = processed_data.get('start_time')
            total_duration = float(processed_data.get('total_duration', 0))
            total_distance = float(processed_data.get('total_distance', 0))
            total_calories = int(processed_data.get('total_calories', 0))
            avg_power = float(processed_data.get('avg_power', 0))
            max_power = float(processed_data.get('max_power', 0))
            avg_heart_rate = float(processed_data.get('avg_heart_rate', 0))
            max_heart_rate = float(processed_data.get('max_heart_rate', 0))
            avg_cadence = float(processed_data.get('avg_cadence', 0))
            max_cadence = float(processed_data.get('max_cadence', 0))
            avg_speed = float(processed_data.get('avg_speed', 0))
            max_speed = float(processed_data.get('max_speed', 0))
            normalized_power = float(processed_data.get('normalized_power', 0))
            total_strokes = int(processed_data.get('total_strokes', 0))
            
            # Get data series (timestamps and values)
            data_series = processed_data.get('data_series', {})
            
            # Ensure all required arrays exist and have valid lengths
            timestamps = data_series.get('timestamps', [])
            if not timestamps:
                logger.error("No timestamps found in data series")
                return None
                
            # Get the number of data points from timestamps
            num_data_points = len(timestamps)
            
            # Ensure all arrays are initialized with proper length
            absolute_timestamps = data_series.get('absolute_timestamps', [])
            powers = self._ensure_array_exists(data_series.get('powers', []), num_data_points)
            heart_rates = self._ensure_array_exists(data_series.get('heart_rates', []), num_data_points)
            cadences = self._ensure_array_exists(data_series.get('cadences', []), num_data_points)
            speeds = self._ensure_array_exists(data_series.get('speeds', []), num_data_points)
            distances = self._ensure_array_exists(data_series.get('distances', []), num_data_points)
            
            logger.info(f"Processing {workout_type} workout with {num_data_points} data points")
            logger.info(f"Data arrays - Powers: {len(powers)}, Cadences: {len(cadences)}, Speeds: {len(speeds)}")
            
            # Create a FIT file builder
            builder = FitFileBuilder()
            
            # Get start_time from processed_data, defaulting to now if not present or invalid
            start_time_input = processed_data.get('start_time')
            unix_start_timestamp_ms = self._get_utc_timestamp_ms(start_time_input)
            # For base_datetime_utc if needed for relative offsets later
            start_time_dt_utc = datetime.fromtimestamp(unix_start_timestamp_ms / 1000.0, timezone.utc)
            logger.debug(f"Processed start_time_input: '{start_time_input}', Resulting unix_start_timestamp_ms: {unix_start_timestamp_ms}, start_time_dt_utc: {start_time_dt_utc.isoformat()}")

            # --- BEGIN MODIFICATIONS for Device Identification (Step 002a) ---
            # File ID Message
            file_id_mesg = FileIdMessage()
            file_id_mesg.type = FileType.ACTIVITY
            try:
                # Try to use the Manufacturer enum if 'ZWIFT' is defined in fit_tool.profile.profile_type.Manufacturer
                file_id_mesg.manufacturer = Manufacturer.ZWIFT 
            except AttributeError:
                logger.warning("Manufacturer.ZWIFT not found in fit_tool's enum. Using integer ID 281 for Zwift.")
                file_id_mesg.manufacturer = 281 # Zwift's integer Manufacturer ID
            file_id_mesg.product = 3907 # Zwift product ID from fitfiletools.fit example
            
            # Using serial number from processed_data if available, else default to example's value (305419896)
            # Ensure this is appropriate for the project's needs (e.g., actual device SN or consistent bridge SN)
            file_id_mesg.serial_number = processed_data.get('serial_number', 305419896) 
            file_id_mesg.time_created = unix_start_timestamp_ms # This is Unix ms, fit_tool handles FIT epoch conversion

            builder.add(file_id_mesg)
            logger.debug(f"Added FileIdMessage: Manufacturer={file_id_mesg.manufacturer}, Product={file_id_mesg.product}, SN={file_id_mesg.serial_number}")

            # Device Info Message
            device_info_mesg = DeviceInfoMessage()
            device_info_mesg.timestamp = unix_start_timestamp_ms # Timestamp of this message creation
            # device_info_mesg.device_index = 0 # Default device_index is 0. 'creator' (value 0) is common.
            try:
                device_info_mesg.manufacturer = Manufacturer.ZWIFT
            except AttributeError:
                device_info_mesg.manufacturer = 281
            device_info_mesg.product = 3907
            device_info_mesg.serial_number = processed_data.get('serial_number', 305419896)
            
            # Software and hardware versions from example or make configurable
            # FIT software_version is often scaled (e.g., v1.00 stored as 100). Example JSON showed 100.0.
            device_info_mesg.software_version = processed_data.get('software_version_scaled', 100.0) 
            device_info_mesg.hardware_version = processed_data.get('hardware_version', 1)
            # product_name can be set if desired and supported by fit_tool
            # device_info_mesg.product_name = b"Rogue Garmin Bridge" # Example, ensure bytes if required

            builder.add(device_info_mesg)
            logger.debug(f"Added DeviceInfoMessage: Manufacturer={device_info_mesg.manufacturer}, Product={device_info_mesg.product}, SN={device_info_mesg.serial_number}")

            # --- BEGIN MODIFICATIONS for Event (Timer Start) Message (Step 002c part 1) ---
            event_mesg_start = EventMessage()
            event_mesg_start.timestamp = unix_start_timestamp_ms
            event_mesg_start.event = Event.TIMER
            event_mesg_start.event_type = EventType.START
            builder.add(event_mesg_start)
            logger.debug(f"Added EventMessage (Timer START) at {unix_start_timestamp_ms}")
            # --- END MODIFICATIONS for Event (Timer Start) Message (Step 002c part 1) ---
            # --- END MODIFICATIONS for Device Identification (Step 002a) ---

            # --- BEGIN MODIFICATIONS for Record Messages (Step 002b) ---
            logger.info(f"Starting to add {num_data_points} record messages.")
            if not absolute_timestamps or len(absolute_timestamps) != num_data_points:
                logger.error("Absolute timestamps are missing or do not match number of data points. Cannot create record messages.")
            else:
                for i in range(num_data_points):
                    record_mesg = RecordMessage()
                                      # Timestamp for the record using the new helper
                    # absolute_timestamps[i] is expected to be a datetime string, datetime object, or Unix timestamp in seconds.
                    record_timestamp_input = absolute_timestamps[i] if absolute_timestamps and i < len(absolute_timestamps) else None

                    if record_timestamp_input is not None:
                        record_mesg.timestamp = self._get_utc_timestamp_ms(record_timestamp_input)
                    else:
                        # Fallback to relative timestamp if absolute is not available
                        # timestamps[i] is assumed to be a relative offset in seconds from the start_time_dt_utc
                        logger.warning(f"Absolute timestamp for record {i} is missing or invalid. Using relative offset {timestamps[i]}s from start_time_dt_utc.")
                        record_mesg.timestamp = self._get_utc_timestamp_ms(timestamps[i], base_datetime_utc=start_time_dt_utc)
                    if powers and i < len(powers) and powers[i] is not None:
                        record_mesg.power = int(powers[i])
                    if heart_rates and i < len(heart_rates) and heart_rates[i] is not None:
                        record_mesg.heart_rate = int(heart_rates[i])
                    if cadences and i < len(cadences) and cadences[i] is not None:
                        record_mesg.cadence = int(cadences[i])
                    if speeds and i < len(speeds) and speeds[i] is not None:
                        record_mesg.speed = float(speeds[i]) # Speed in m/s
                        record_mesg.enhanced_speed = float(speeds[i]) # Also set enhanced_speed
                    if distances and i < len(distances) and distances[i] is not None:
                        record_mesg.distance = float(distances[i]) # Distance in meters               if distances and i < len(distances) and distances[i] is not None:
                        record_mesg.distance = float(distances[i]) # Distance in meters
                    
                    builder.add(record_mesg)
                    if (i + 1) % 100 == 0 or (i + 1) == num_data_points: # Log progress
                        logger.debug(f"Added record message {i+1}/{num_data_points}")
            logger.info("Finished adding record messages.")
            # --- END MODIFICATIONS for Record Messages (Step 002b) ---

            # --- BEGIN MODIFICATIONS for Lap, Session, Activity, and Event (Timer Stop) Messages (Step 002c part 2) ---
            
            # Calculate end timestamp (last absolute_timestamp or start_time + total_duration)
            if absolute_timestamps:
                unix_end_timestamp_ms = int(absolute_timestamps[-1].timestamp() * 1000) if isinstance(absolute_timestamps[-1], datetime) else int(absolute_timestamps[-1] * 1000)
            else:
                unix_end_timestamp_ms = unix_start_timestamp_ms + int(total_duration * 1000)

            # Event Message (Timer Stop)
            event_mesg_stop = EventMessage()
            event_mesg_stop.timestamp = unix_end_timestamp_ms
            event_mesg_stop.event = Event.TIMER
            event_mesg_stop.event_type = EventType.STOP
            builder.add(event_mesg_stop)
            logger.debug(f"Added EventMessage (Timer STOP) at {unix_end_timestamp_ms}")

            # Lap Message (assuming a single lap for the entire activity)
            lap_mesg = LapMessage()
            lap_mesg.timestamp = unix_end_timestamp_ms # Lap end time
            lap_mesg.start_time = unix_start_timestamp_ms
            lap_mesg.total_elapsed_time = total_duration * 1000 # ms
            lap_mesg.total_timer_time = total_duration * 1000 # ms
            lap_mesg.event = Event.LAP 
            lap_mesg.event_type = EventType.STOP 
            lap_mesg.lap_trigger = LapTrigger.MANUAL # Or other appropriate trigger

            if avg_speed is not None: lap_mesg.avg_speed = float(avg_speed)
            if max_speed is not None: lap_mesg.max_speed = float(max_speed)
            if total_distance is not None: lap_mesg.total_distance = float(total_distance)
            if total_calories is not None: lap_mesg.total_calories = int(total_calories)
            if avg_power is not None: lap_mesg.avg_power = int(avg_power)
            if max_power is not None: lap_mesg.max_power = int(max_power)
            if normalized_power is not None and normalized_power > 0: lap_mesg.normalized_power = int(normalized_power)
            if avg_cadence is not None: lap_mesg.avg_cadence = int(avg_cadence)
            if max_cadence is not None: lap_mesg.max_cadence = int(max_cadence)
            if avg_heart_rate is not None: lap_mesg.avg_heart_rate = int(avg_heart_rate)
            if max_heart_rate is not None: lap_mesg.max_heart_rate = int(max_heart_rate)
            # Determine sport for lap message based on workout_type
            if workout_type == 'bike':
                lap_mesg.sport = Sport.CYCLING
            elif workout_type == 'run':
                lap_mesg.sport = Sport.RUNNING
            # Add other sports as needed
            else:
                lap_mesg.sport = Sport.GENERIC # Default sport

            builder.add(lap_mesg)
            logger.debug("Added LapMessage")

            # Session Message
            session_mesg = SessionMessage()
            session_mesg.timestamp = unix_end_timestamp_ms # Session end time
            session_mesg.start_time = unix_start_timestamp_ms
            session_mesg.total_elapsed_time = total_duration * 1000 # ms
            session_mesg.total_timer_time = total_duration * 1000 # ms
            session_mesg.event = Event.SESSION
            session_mesg.event_type = EventType.STOP
            session_mesg.trigger = SessionTrigger.ACTIVITY_END

            if workout_type == 'bike':
                session_mesg.sport = Sport.CYCLING
                session_mesg.sub_sport = SubSport.INDOOR_CYCLING # Or other as appropriate
            elif workout_type == 'run':
                session_mesg.sport = Sport.RUNNING
                session_mesg.sub_sport = SubSport.TREADMILL # Or other as appropriate
            # Add other sports as needed
            else:
                session_mesg.sport = Sport.GENERIC
                session_mesg.sub_sport = SubSport.GENERIC

            if avg_speed is not None: session_mesg.avg_speed = float(avg_speed)
            if max_speed is not None: session_mesg.max_speed = float(max_speed)
            if total_distance is not None: session_mesg.total_distance = float(total_distance)
            if total_calories is not None: session_mesg.total_calories = int(total_calories)
            if avg_power is not None: session_mesg.avg_power = int(avg_power)
            if max_power is not None: session_mesg.max_power = int(max_power)
            if normalized_power is not None and normalized_power > 0: session_mesg.normalized_power = int(normalized_power)
            if avg_cadence is not None: session_mesg.avg_cadence = int(avg_cadence)
            if max_cadence is not None: session_mesg.max_cadence = int(max_cadence)
            if avg_heart_rate is not None: session_mesg.avg_heart_rate = int(avg_heart_rate)
            if max_heart_rate is not None: session_mesg.max_heart_rate = int(max_heart_rate)
            # TSS and IF if available and calculable
            # session_mesg.training_stress_score = processed_data.get('tss', 0)
            # session_mesg.intensity_factor = processed_data.get('if', 0)

            builder.add(session_mesg)
            logger.debug("Added SessionMessage")

            # Activity Message
            activity_mesg = ActivityMessage()
            activity_mesg.timestamp = unix_start_timestamp_ms # Timestamp of the activity start
            activity_mesg.total_timer_time = total_duration * 1000 # ms
            activity_mesg.num_sessions = 1
            activity_mesg.type = Event.ACTIVITY # This should be ActivityType, but fit_tool might use Event enum value
            activity_mesg.event = Event.ACTIVITY
            activity_mesg.event_type = EventType.STOP
            builder.add(activity_mesg)
            logger.debug("Added ActivityMessage")

            # --- END MODIFICATIONS for Lap, Session, Activity, and Event (Timer Stop) Messages (Step 002c part 2) ---

            # Finalize and write the FIT file
            unix_start_timestamp_sec = unix_start_timestamp_ms // 1000 # Define unix_start_timestamp_sec
            file_name = f"{workout_type}_{datetime.fromtimestamp(unix_start_timestamp_sec).strftime('%Y%m%d_%H%M%S')}.fit"
            output_path = os.path.join(self.output_dir, file_name)
            
            fit_file = builder.build()
            fit_file.to_file(output_path)
            logger.info(f"FIT file successfully created: {output_path}")
            return output_path
            
            # Debug output
            logger.debug(f"Start time: {start_time}")
            logger.debug(f"Unix timestamp (seconds): {unix_start_timestamp_sec}")
            logger.debug(f"Unix timestamp (milliseconds): {unix_start_timestamp_ms}")
            
            # ...existing code...
            
        except Exception as e:
            logger.error(f"Error converting workout to FIT: {str(e)}")
            logger.error(traceback.format_exc())
            return None


    def _get_utc_timestamp_ms(self, time_input: Any, base_datetime_utc: Optional[datetime] = None) -> int:
        """
        Converts various time inputs (datetime string, datetime object, numeric seconds offset,
        or numeric Unix timestamp in seconds) to UTC Unix timestamp in milliseconds.
        If time_input is a numeric offset (and not a large Unix timestamp), base_datetime_utc should be provided.
        """
        dt_obj = None
        if isinstance(time_input, str):
            try:
                processed_time_input = time_input
                if processed_time_input.endswith('Z'):
                    processed_time_input = processed_time_input[:-1] + '+00:00'
                dt_obj = datetime.fromisoformat(processed_time_input)
            except ValueError:
                logger.warning(f"Could not parse datetime string: '{time_input}'. Using current UTC time as fallback.")
                dt_obj = datetime.now(timezone.utc)
        elif isinstance(time_input, datetime):
            dt_obj = time_input
        elif isinstance(time_input, (int, float)):
            # Heuristic: if timestamp is very large, assume it's already Unix seconds.
            # Otherwise, if base_datetime_utc is provided, assume it's an offset in seconds.
            if time_input > 946684800:  # Approx. year 2000-01-01 in Unix seconds
                dt_obj = datetime.fromtimestamp(time_input, timezone.utc)
            elif base_datetime_utc:
                dt_obj = base_datetime_utc + timedelta(seconds=time_input)
            else:
                logger.warning(f"Numeric time input {time_input} is ambiguous without base_datetime_utc. Using current UTC time as fallback.")
                dt_obj = datetime.now(timezone.utc)
        else:
            if time_input is None:
                 logger.warning(f"Time input is None. Using current UTC time as fallback.")
            else:
                logger.warning(f"Invalid time input type: {type(time_input)}. Using current UTC time as fallback.")
            dt_obj = datetime.now(timezone.utc)

        # Ensure the datetime object is timezone-aware and in UTC
        if dt_obj.tzinfo is None or dt_obj.tzinfo.utcoffset(dt_obj) is None:
            # Naive datetime, assume it's UTC as per typical internal handling, or make it UTC
            dt_obj = dt_obj.replace(tzinfo=timezone.utc)
        elif dt_obj.tzinfo != timezone.utc:
            # Timezone-aware but not UTC, convert to UTC
            dt_obj = dt_obj.astimezone(timezone.utc)
        
        return int(dt_obj.timestamp() * 1000)


    def _ensure_array_exists(self, array, expected_length):
        """
        Ensure an array exists and has the expected length.
        If the array doesn't exist or has the wrong length, create a new array with zeros.
        
        Args:
            array: The array to check
            expected_length: The expected length of the array
            
        Returns:
            An array with the expected length
        """
        if not array:
            # Array doesn't exist, create a new one with zeros
            logger.warning(f"Array doesn't exist, creating empty array of length {expected_length}")
            return [0] * expected_length
            
        if len(array) < expected_length:
            # Array is too short, pad with zeros
            logger.warning(f"Array is too short (has {len(array)}, expected {expected_length}), padding with zeros")
            return array + [0] * (expected_length - len(array))
            
        if len(array) > expected_length:
            # Array is too long, truncate
            logger.warning(f"Array is too long (has {len(array)}, expected {expected_length}), truncating")
            return array[:expected_length]
            
        # Array is the correct length
        return array

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
