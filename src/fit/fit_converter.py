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
    
    def _unix_to_fit_timestamp_ms(self, unix_timestamp_seconds: int) -> int:
        """
        Convert Unix timestamp (seconds) to fit_tool format (milliseconds).
        
        Args:
            unix_timestamp_seconds: Unix timestamp in seconds
            
        Returns:
            Timestamp in milliseconds since Unix epoch (1970-01-01)
        """
        # Convert seconds to milliseconds - fit_tool will apply the offset and scale
        return unix_timestamp_seconds * 1000
    
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
            
            # Also get the average values if available in data series
            average_powers = data_series.get('average_powers', [])
            average_cadences = data_series.get('average_cadences', [])
            average_speeds = data_series.get('average_speeds', [])
            
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
            
            # Convert start_time to Unix timestamp in seconds
            if isinstance(start_time, datetime):
                unix_start_timestamp_sec = int(start_time.timestamp())
            elif isinstance(start_time, str):
                # Try to parse the string as a datetime
                try:
                    unix_start_timestamp_sec = int(datetime.fromisoformat(start_time).timestamp())
                except ValueError:
                    logger.warning(f"Could not parse start_time string: {start_time}")
                    unix_start_timestamp_sec = int(time.time())
            else:
                unix_start_timestamp_sec = int(time.time())
            
            # Convert Unix timestamp (seconds) to fit_tool format (milliseconds)
            unix_start_timestamp_ms = self._unix_to_fit_timestamp_ms(unix_start_timestamp_sec)
            
            # Debug output
            logger.debug(f"Start time: {start_time}")
            logger.debug(f"Unix timestamp (seconds): {unix_start_timestamp_sec}")
            logger.debug(f"Unix timestamp (milliseconds): {unix_start_timestamp_ms}")
            
            # Add File ID message
            try:
                file_id_msg = FileIdMessage()
                file_id_msg.type = FileType.ACTIVITY
                file_id_msg.manufacturer = Manufacturer.DEVELOPMENT.value
                file_id_msg.product = 0
                file_id_msg.time_created = unix_start_timestamp_ms  # Milliseconds since Unix epoch
                file_id_msg.serial_number = 0x12345678
                builder.add(file_id_msg)
                logger.debug(f"Added File ID message with time_created: {unix_start_timestamp_ms} ms")
            except Exception as e:
                logger.error(f"Error creating File ID message: {str(e)}")
                logger.error(traceback.format_exc())
                raise
            
            # Add Device Info message
            try:
                device_info_msg = DeviceInfoMessage()
                device_info_msg.timestamp = unix_start_timestamp_ms  # Milliseconds since Unix epoch
                device_info_msg.manufacturer = Manufacturer.DEVELOPMENT.value
                device_info_msg.product = 0
                device_info_msg.device_index = 0
                device_info_msg.serial_number = 0x12345678
                device_info_msg.software_version = 100
                device_info_msg.hardware_version = 1
                builder.add(device_info_msg)
                logger.debug("Added Device Info message")
            except Exception as e:
                logger.error(f"Error creating Device Info message: {str(e)}")
                logger.error(traceback.format_exc())
                raise
            
            # Add Event message (start)
            try:
                event_msg = EventMessage()
                event_msg.timestamp = unix_start_timestamp_ms  # Milliseconds since Unix epoch
                event_msg.event = Event.TIMER
                event_msg.event_type = EventType.START
                builder.add(event_msg)
                logger.debug("Added Event (start) message")
            except Exception as e:
                logger.error(f"Error creating Event (start) message: {str(e)}")
                logger.error(traceback.format_exc())
                raise
            
            # Add Record messages
            try:
                for i in range(len(timestamps)):
                    record_msg = RecordMessage()
                    
                    # Set timestamp in milliseconds
                    if i < len(absolute_timestamps):
                        timestamp_obj = absolute_timestamps[i]
                        if isinstance(timestamp_obj, datetime):
                            unix_record_timestamp_sec = int(timestamp_obj.timestamp())
                            unix_record_timestamp_ms = self._unix_to_fit_timestamp_ms(unix_record_timestamp_sec)
                            record_msg.timestamp = unix_record_timestamp_ms
                            logger.debug(f"Record {i}: Using absolute timestamp {timestamp_obj} -> {unix_record_timestamp_ms} ms")
                        else:
                            logger.warning(f"Record {i}: Invalid absolute timestamp type: {type(timestamp_obj)}")
                            # Use relative timestamp as fallback
                            unix_record_timestamp_ms = unix_start_timestamp_ms + int(timestamps[i] * 1000)
                            record_msg.timestamp = unix_record_timestamp_ms
                            logger.debug(f"Record {i}: Using fallback relative timestamp -> {unix_record_timestamp_ms} ms")
                    else:
                        # Use relative timestamp (seconds) converted to milliseconds
                        unix_record_timestamp_ms = unix_start_timestamp_ms + int(timestamps[i] * 1000)
                        record_msg.timestamp = unix_record_timestamp_ms
                        logger.debug(f"Record {i}: Using relative timestamp {timestamps[i]} sec -> {unix_record_timestamp_ms} ms")
                    
                    # Set power - use instantaneous power for record messages
                    if i < len(powers):
                        record_msg.power = int(powers[i])
                    
                    # Set cadence - use instantaneous cadence for record messages
                    if i < len(cadences):
                        record_msg.cadence = int(cadences[i])
                    
                    # Set heart rate
                    if i < len(heart_rates) and heart_rates[i] > 0:
                        record_msg.heart_rate = int(heart_rates[i])
                    
                    # Set speed - use instantaneous speed for record messages
                    if i < len(speeds):
                        # Convert km/h to m/s (using proper conversion, no extra scaling)
                        record_msg.speed = int(speeds[i] * 1000 / 3600)
                    
                    # Set distance
                    if i < len(distances):
                        record_msg.distance = float(distances[i])
                    
                    builder.add(record_msg)
                
                logger.debug(f"Added {len(timestamps)} Record messages")
            except Exception as e:
                logger.error(f"Error creating Record messages: {str(e)}")
                logger.error(traceback.format_exc())
                raise
            
            # Add Event message (stop)
            try:
                unix_end_timestamp_sec = unix_start_timestamp_sec + int(total_duration)
                unix_end_timestamp_ms = self._unix_to_fit_timestamp_ms(unix_end_timestamp_sec)
                
                event_msg = EventMessage()
                event_msg.timestamp = unix_end_timestamp_ms  # Milliseconds since Unix epoch
                event_msg.event = Event.TIMER
                event_msg.event_type = EventType.STOP
                builder.add(event_msg)
                logger.debug(f"Added Event (stop) message with timestamp: {unix_end_timestamp_ms} ms")
            except Exception as e:
                logger.error(f"Error creating Event (stop) message: {str(e)}")
                logger.error(traceback.format_exc())
                raise
            
            # Add Lap message
            try:
                lap_msg = LapMessage()
                lap_msg.timestamp = unix_end_timestamp_ms  # Milliseconds since Unix epoch
                lap_msg.start_time = unix_start_timestamp_ms  # Milliseconds since Unix epoch
                lap_msg.total_elapsed_time = float(total_duration)
                lap_msg.total_timer_time = float(total_duration)
                lap_msg.total_distance = float(total_distance)
                lap_msg.total_calories = int(total_calories)
                
                # Use average power from data if available
                lap_msg.avg_power = int(avg_power)
                
                lap_msg.max_power = int(max_power)
                
                # Use average cadence from data if available
                lap_msg.avg_cadence = int(avg_cadence)
                
                lap_msg.max_cadence = int(max_cadence)
                
                if avg_heart_rate > 0:
                    lap_msg.avg_heart_rate = int(avg_heart_rate)
                if max_heart_rate > 0:
                    lap_msg.max_heart_rate = int(max_heart_rate)
                
                # Use average speed from data if available - ensure proper scaling for Garmin Connect
                if avg_speed > 0:
                    # Convert km/h to m/s (no extra scaling needed)
                    lap_msg.avg_speed = int(avg_speed * 1000 / 3600)  # Convert km/h to m/s
                
                if max_speed > 0:
                    lap_msg.max_speed = int(max_speed * 1000 / 3600)  # Same conversion for max_speed
                
                lap_msg.lap_trigger = LapTrigger.SESSION_END
                lap_msg.sport = Sport.CYCLING
                builder.add(lap_msg)
                logger.debug("Added Lap message")
                logger.debug(f"Lap avg_speed: {lap_msg.avg_speed}, from {avg_speed} km/h")
            except Exception as e:
                logger.error(f"Error creating Lap message: {str(e)}")
                logger.error(traceback.format_exc())
                raise
            
            # Add Session message
            try:
                session_msg = SessionMessage()
                session_msg.timestamp = unix_end_timestamp_ms  # Milliseconds since Unix epoch
                session_msg.start_time = unix_start_timestamp_ms  # Milliseconds since Unix epoch
                session_msg.total_elapsed_time = float(total_duration)
                session_msg.total_timer_time = float(total_duration)
                session_msg.total_distance = float(total_distance)
                session_msg.total_calories = int(total_calories)
                
                # Use the summary average power, which may be directly from the device
                session_msg.avg_power = int(avg_power)
                
                session_msg.max_power = int(max_power)
                
                # Use the summary average cadence, which may be directly from the device
                session_msg.avg_cadence = int(avg_cadence)
                
                session_msg.max_cadence = int(max_cadence)
                
                if avg_heart_rate > 0:
                    session_msg.avg_heart_rate = int(avg_heart_rate)
                if max_heart_rate > 0:
                    session_msg.max_heart_rate = int(max_heart_rate)
                
                # Use the summary average speed, which may be directly from the device
                # Properly scale for Garmin Connect compatibility
                if avg_speed > 0:
                    # Convert km/h to m/s (no extra scaling needed)
                    session_msg.avg_speed = int(avg_speed * 1000 / 3600)  # Convert km/h to m/s
                
                if max_speed > 0:
                    session_msg.max_speed = int(max_speed * 1000 / 3600)  # Same conversion for max_speed
                
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
                    if 'weight_kg' in user_profile:
                        # Convert kg to g
                        session_msg.total_weight = int(user_profile['weight_kg'] * 1000)
                    elif 'weight' in user_profile:
                        # Convert kg to g
                        session_msg.total_weight = int(user_profile['weight'] * 1000)
                    
                    if 'gender' in user_profile:
                        session_msg.gender = 0 if user_profile['gender'].lower() == 'female' else 1
                    
                    if 'age' in user_profile:
                        session_msg.age = user_profile['age']
                
                builder.add(session_msg)
                logger.debug("Added Session message")
                logger.debug(f"Session avg_speed: {session_msg.avg_speed}, from {avg_speed} km/h")
            except Exception as e:
                logger.error(f"Error creating Session message: {str(e)}")
                logger.error(traceback.format_exc())
                raise
            
            # Add Activity message
            try:
                activity_msg = ActivityMessage()
                activity_msg.timestamp = unix_end_timestamp_ms  # Milliseconds since Unix epoch
                activity_msg.total_timer_time = float(total_duration)
                activity_msg.num_sessions = 1
                activity_msg.type = 0  # Manual activity
                activity_msg.event = Event.ACTIVITY
                activity_msg.event_type = EventType.STOP
                builder.add(activity_msg)
                logger.debug("Added Activity message")
            except Exception as e:
                logger.error(f"Error creating Activity message: {str(e)}")
                logger.error(traceback.format_exc())
                raise
            
            # Generate filename using datetime (from Unix timestamp)
            timestamp_str = datetime.fromtimestamp(unix_start_timestamp_sec).strftime('%Y%m%d_%H%M%S')
            filename = f"indoor_cycling_{timestamp_str}.fit"
            filepath = os.path.join(self.output_dir, filename)
            
            # Build and save FIT file
            try:
                fit_file = builder.build()
                fit_file.to_file(filepath)
                logger.info(f"Created FIT file: {filepath}")
                return filepath
            except Exception as e:
                logger.error(f"Error building/saving FIT file: {str(e)}")
                logger.error(traceback.format_exc())
                raise
            
        except Exception as e:
            logger.error(f"Error converting bike workout to FIT: {str(e)}")
            logger.error(traceback.format_exc())
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
            
            # Convert start_time to Unix timestamp in seconds
            if isinstance(start_time, datetime):
                unix_start_timestamp_sec = int(start_time.timestamp())
            elif isinstance(start_time, str):
                # Try to parse the string as a datetime
                try:
                    unix_start_timestamp_sec = int(datetime.fromisoformat(start_time).timestamp())
                except ValueError:
                    logger.warning(f"Could not parse start_time string: {start_time}")
                    unix_start_timestamp_sec = int(time.time())
            else:
                unix_start_timestamp_sec = int(time.time())
            
            # Convert Unix timestamp (seconds) to fit_tool format (milliseconds)
            unix_start_timestamp_ms = self._unix_to_fit_timestamp_ms(unix_start_timestamp_sec)
            
            # Debug output
            logger.debug(f"Start time: {start_time}")
            logger.debug(f"Unix timestamp (seconds): {unix_start_timestamp_sec}")
            logger.debug(f"Unix timestamp (milliseconds): {unix_start_timestamp_ms}")
            
            # Add File ID message
            try:
                file_id_msg = FileIdMessage()
                file_id_msg.type = FileType.ACTIVITY
                file_id_msg.manufacturer = Manufacturer.DEVELOPMENT.value
                file_id_msg.product = 0
                file_id_msg.time_created = unix_start_timestamp_ms  # Milliseconds since Unix epoch
                file_id_msg.serial_number = 0x12345678
                builder.add(file_id_msg)
                logger.debug(f"Added File ID message with time_created: {unix_start_timestamp_ms} ms")
            except Exception as e:
                logger.error(f"Error creating File ID message: {str(e)}")
                logger.error(traceback.format_exc())
                raise
            
            # Add Device Info message
            try:
                device_info_msg = DeviceInfoMessage()
                device_info_msg.timestamp = unix_start_timestamp_ms  # Milliseconds since Unix epoch
                device_info_msg.manufacturer = Manufacturer.DEVELOPMENT.value
                device_info_msg.product = 0
                device_info_msg.device_index = 0
                device_info_msg.serial_number = 0x12345678
                device_info_msg.software_version = 100
                device_info_msg.hardware_version = 1
                builder.add(device_info_msg)
                logger.debug("Added Device Info message")
            except Exception as e:
                logger.error(f"Error creating Device Info message: {str(e)}")
                logger.error(traceback.format_exc())
                raise
            
            # Add Event message (start)
            try:
                event_msg = EventMessage()
                event_msg.timestamp = unix_start_timestamp_ms  # Milliseconds since Unix epoch
                event_msg.event = Event.TIMER
                event_msg.event_type = EventType.START
                builder.add(event_msg)
                logger.debug("Added Event (start) message")
            except Exception as e:
                logger.error(f"Error creating Event (start) message: {str(e)}")
                logger.error(traceback.format_exc())
                raise
            
            # Add Record messages
            try:
                for i in range(len(timestamps)):
                    record_msg = RecordMessage()
                    
                    # Set timestamp in milliseconds
                    if i < len(absolute_timestamps):
                        timestamp_obj = absolute_timestamps[i]
                        if isinstance(timestamp_obj, datetime):
                            unix_record_timestamp_sec = int(timestamp_obj.timestamp())
                            unix_record_timestamp_ms = self._unix_to_fit_timestamp_ms(unix_record_timestamp_sec)
                            record_msg.timestamp = unix_record_timestamp_ms
                            logger.debug(f"Record {i}: Using absolute timestamp {timestamp_obj} -> {unix_record_timestamp_ms} ms")
                        else:
                            logger.warning(f"Record {i}: Invalid absolute timestamp type: {type(timestamp_obj)}")
                            # Use relative timestamp as fallback
                            unix_record_timestamp_ms = unix_start_timestamp_ms + int(timestamps[i] * 1000)
                            record_msg.timestamp = unix_record_timestamp_ms
                            logger.debug(f"Record {i}: Using fallback relative timestamp -> {unix_record_timestamp_ms} ms")
                    else:
                        # Use relative timestamp (seconds) converted to milliseconds
                        unix_record_timestamp_ms = unix_start_timestamp_ms + int(timestamps[i] * 1000)
                        record_msg.timestamp = unix_record_timestamp_ms
                        logger.debug(f"Record {i}: Using relative timestamp {timestamps[i]} sec -> {unix_record_timestamp_ms} ms")
                    
                    # Set power
                    if i < len(powers):
                        record_msg.power = int(powers[i])
                    
                    # Set cadence (stroke rate for rowing)
                    if i < len(stroke_rates):
                        record_msg.cadence = int(stroke_rates[i])
                    
                    # Set heart rate
                    if i < len(heart_rates) and heart_rates[i] > 0:
                        record_msg.heart_rate = int(heart_rates[i])
                    
                    # Set distance
                    if i < len(distances):
                        record_msg.distance = float(distances[i])
                    
                    builder.add(record_msg)
                
                logger.debug(f"Added {len(timestamps)} Record messages")
            except Exception as e:
                logger.error(f"Error creating Record messages: {str(e)}")
                logger.error(traceback.format_exc())
                raise
            
            # Add Event message (stop)
            try:
                unix_end_timestamp_sec = unix_start_timestamp_sec + int(total_duration)
                unix_end_timestamp_ms = self._unix_to_fit_timestamp_ms(unix_end_timestamp_sec)
                
                event_msg = EventMessage()
                event_msg.timestamp = unix_end_timestamp_ms  # Milliseconds since Unix epoch
                event_msg.event = Event.TIMER
                event_msg.event_type = EventType.STOP
                builder.add(event_msg)
                logger.debug(f"Added Event (stop) message with timestamp: {unix_end_timestamp_ms} ms")
            except Exception as e:
                logger.error(f"Error creating Event (stop) message: {str(e)}")
                logger.error(traceback.format_exc())
                raise
            
            # Add Lap message
            try:
                lap_msg = LapMessage()
                lap_msg.timestamp = unix_end_timestamp_ms  # Milliseconds since Unix epoch
                lap_msg.start_time = unix_start_timestamp_ms  # Milliseconds since Unix epoch
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
                
                # If we have an average speed for the rowing workout
                avg_speed = processed_data.get('avg_speed', 0)
                max_speed = processed_data.get('max_speed', 0)
                
                if avg_speed > 0:
                    # Convert km/h to m/s (no extra scaling needed)
                    lap_msg.avg_speed = int(avg_speed * 1000 / 3600)  # Convert km/h to m/s
                
                if max_speed > 0:
                    lap_msg.max_speed = int(max_speed * 1000 / 3600)  # Same conversion for max_speed
                
                lap_msg.total_cycles = int(total_strokes)  # Use strokes as cycles
                lap_msg.lap_trigger = LapTrigger.SESSION_END
                lap_msg.sport = Sport.ROWING
                builder.add(lap_msg)
                logger.debug("Added Lap message")
                if avg_speed > 0:
                    logger.debug(f"Lap avg_speed: {lap_msg.avg_speed}, from {avg_speed} km/h")
            except Exception as e:
                logger.error(f"Error creating Lap message: {str(e)}")
                logger.error(traceback.format_exc())
                raise
            
            # Add Session message
            try:
                session_msg = SessionMessage()
                session_msg.timestamp = unix_end_timestamp_ms  # Milliseconds since Unix epoch
                session_msg.start_time = unix_start_timestamp_ms  # Milliseconds since Unix epoch
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
                
                # If we have an average speed for the rowing workout
                avg_speed = processed_data.get('avg_speed', 0)
                max_speed = processed_data.get('max_speed', 0)
                
                if avg_speed > 0:
                    # Convert km/h to m/s (no extra scaling needed)
                    session_msg.avg_speed = int(avg_speed * 1000 / 3600)  # Convert km/h to m/s
                
                if max_speed > 0:
                    session_msg.max_speed = int(max_speed * 1000 / 3600)  # Same conversion for max_speed
                
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
                    if 'weight_kg' in user_profile:
                        # Convert kg to g
                        session_msg.total_weight = int(user_profile['weight_kg'] * 1000)
                    elif 'weight' in user_profile:
                        # Convert kg to g
                        session_msg.total_weight = int(user_profile['weight'] * 1000)
                    
                    if 'gender' in user_profile:
                        session_msg.gender = 0 if user_profile['gender'].lower() == 'female' else 1
                    
                    if 'age' in user_profile:
                        session_msg.age = user_profile['age']
                
                builder.add(session_msg)
                logger.debug("Added Session message")
                if avg_speed > 0:
                    logger.debug(f"Session avg_speed: {session_msg.avg_speed}, from {avg_speed} km/h")
            except Exception as e:
                logger.error(f"Error creating Session message: {str(e)}")
                logger.error(traceback.format_exc())
                raise
            
            # Add Activity message
            try:
                activity_msg = ActivityMessage()
                activity_msg.timestamp = unix_end_timestamp_ms  # Milliseconds since Unix epoch
                activity_msg.total_timer_time = float(total_duration)
                activity_msg.num_sessions = 1
                activity_msg.type = 0  # Manual activity
                activity_msg.event = Event.ACTIVITY
                activity_msg.event_type = EventType.STOP
                builder.add(activity_msg)
                logger.debug("Added Activity message")
            except Exception as e:
                logger.error(f"Error creating Activity message: {str(e)}")
                logger.error(traceback.format_exc())
                raise
            
            # Generate filename using datetime (from Unix timestamp)
            timestamp_str = datetime.fromtimestamp(unix_start_timestamp_sec).strftime('%Y%m%d_%H%M%S')
            filename = f"indoor_rowing_{timestamp_str}.fit"
            filepath = os.path.join(self.output_dir, filename)
            
            # Build and save FIT file
            try:
                fit_file = builder.build()
                fit_file.to_file(filepath)
                logger.info(f"Created FIT file: {filepath}")
                return filepath
            except Exception as e:
                logger.error(f"Error building/saving FIT file: {str(e)}")
                logger.error(traceback.format_exc())
                raise
            
        except Exception as e:
            logger.error(f"Error converting rower workout to FIT: {str(e)}")
            logger.error(traceback.format_exc())
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
