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
FIT_EPOCH_OFFSET_MS = 631065600000  # Milliseconds from Unix epoch to FIT epoch (1970-01-01 to 1989-12-31)

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
        os.makedirs(output_dir, exist_ok=True)
    
    def _get_utc_timestamp_ms(self, time_input: Any, base_datetime_utc: Optional[datetime] = None) -> int:
        """
        Converts various time inputs to UTC Unix timestamp in milliseconds.
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
            if time_input > 946684800:  # Approx. year 2000-01-01 in Unix seconds, likely a full timestamp
                dt_obj = datetime.fromtimestamp(time_input, timezone.utc)
            elif base_datetime_utc:
                dt_obj = base_datetime_utc + timedelta(seconds=time_input)
            else:
                logger.warning(f"Numeric time input {time_input} is ambiguous. Using current UTC time as fallback.")
                dt_obj = datetime.now(timezone.utc)
        else:
            logger.warning(f"Invalid time input type: {type(time_input)}. Using current UTC time as fallback.")
            dt_obj = datetime.now(timezone.utc)

        if dt_obj.tzinfo is None or dt_obj.tzinfo.utcoffset(dt_obj) is None:
            dt_obj = dt_obj.replace(tzinfo=timezone.utc)
        elif dt_obj.tzinfo != timezone.utc:
            dt_obj = dt_obj.astimezone(timezone.utc)
        
        return int(dt_obj.timestamp() * 1000)

    def _ensure_array_exists(self, array, expected_length):
        if not array:
            logger.warning(f"Array doesn't exist, creating empty array of length {expected_length}")
            return [None] * expected_length # Use None for missing data points
        if len(array) < expected_length:
            logger.warning(f"Array is too short (has {len(array)}, expected {expected_length}), padding with Nones")
            return array + [None] * (expected_length - len(array))
        if len(array) > expected_length:
            logger.warning(f"Array is too long (has {len(array)}, expected {expected_length}), truncating")
            return array[:expected_length]
        return array

    def convert_workout(self, processed_data, user_profile=None):
        try:
            workout_type = processed_data.get('workout_type', 'bike')
            start_time_input = processed_data.get('start_time')
            total_duration = float(processed_data.get('total_duration', 0))
            total_distance = float(processed_data.get('total_distance', 0))
            total_calories = int(processed_data.get('total_calories', 0))
            avg_power = processed_data.get('avg_power') # Keep as None if not present
            max_power = processed_data.get('max_power')
            avg_heart_rate = processed_data.get('avg_heart_rate')
            max_heart_rate = processed_data.get('max_heart_rate')
            avg_cadence = processed_data.get('avg_cadence')
            max_cadence = processed_data.get('max_cadence')
            avg_speed = processed_data.get('avg_speed')
            max_speed = processed_data.get('max_speed')
            normalized_power = processed_data.get('normalized_power')

            data_series = processed_data.get('data_series', {})
            timestamps_rel_sec = data_series.get('timestamps', []) # Relative timestamps for num_data_points
            absolute_timestamps_input = data_series.get('absolute_timestamps', []) # Absolute timestamps for records

            if not timestamps_rel_sec and not absolute_timestamps_input:
                logger.error("No timestamps (relative or absolute) found in data series. Cannot determine num_data_points or create records.")
                return None
            
            # Prefer absolute_timestamps for num_data_points if available, else use relative
            num_data_points = len(absolute_timestamps_input) if absolute_timestamps_input else len(timestamps_rel_sec)
            if num_data_points == 0:
                logger.error("Zero data points found. Cannot create meaningful FIT file.")
                return None

            logger.info(f"Processing {workout_type} workout with {num_data_points} data points.")

            powers = self._ensure_array_exists(data_series.get('powers'), num_data_points)
            heart_rates = self._ensure_array_exists(data_series.get('heart_rates'), num_data_points)
            cadences = self._ensure_array_exists(data_series.get('cadences'), num_data_points)
            speeds = self._ensure_array_exists(data_series.get('speeds'), num_data_points)
            distances = self._ensure_array_exists(data_series.get('distances'), num_data_points)

            builder = FitFileBuilder(auto_define=True)
            
            unix_start_timestamp_ms = self._get_utc_timestamp_ms(start_time_input if start_time_input else absolute_timestamps_input[0] if absolute_timestamps_input else datetime.now(timezone.utc))
            start_time_dt_utc = datetime.fromtimestamp(unix_start_timestamp_ms / 1000.0, timezone.utc)

            file_id_mesg = FileIdMessage()
            file_id_mesg.type = FileType.ACTIVITY
            try: file_id_mesg.manufacturer = Manufacturer.ZWIFT
            except AttributeError: file_id_mesg.manufacturer = 281 # Zwift's ID
            file_id_mesg.product = 3907
            file_id_mesg.serial_number = processed_data.get('serial_number', 305419896)
            file_id_mesg.time_created = unix_start_timestamp_ms
            builder.add(file_id_mesg)

            device_info_mesg = DeviceInfoMessage()
            device_info_mesg.timestamp = unix_start_timestamp_ms
            try: device_info_mesg.manufacturer = Manufacturer.ZWIFT
            except AttributeError: device_info_mesg.manufacturer = 281
            device_info_mesg.product = 3907
            device_info_mesg.serial_number = processed_data.get('serial_number', 305419896)
            device_info_mesg.software_version = processed_data.get('software_version_scaled', 100.0)
            device_info_mesg.hardware_version = processed_data.get('hardware_version', 1)
            builder.add(device_info_mesg)

            event_mesg_start = EventMessage()
            event_mesg_start.timestamp = unix_start_timestamp_ms
            event_mesg_start.event = Event.TIMER
            event_mesg_start.event_type = EventType.START
            builder.add(event_mesg_start)

            if not absolute_timestamps_input or len(absolute_timestamps_input) != num_data_points:
                logger.warning("Absolute timestamps are missing or length inconsistent. Record messages might be incomplete or use relative timing.")
                # Fallback logic for current_abs_ts_input
                if not absolute_timestamps_input and timestamps_rel_sec: # Case: absolute_timestamps_input is empty/None, but timestamps_rel_sec exists
                    logger.info("Attempting to derive absolute timestamps from 'timestamps_rel_sec' as 'absolute_timestamps_input' is missing.")
                    all_numeric = all(isinstance(ts, (int, float)) for ts in timestamps_rel_sec)
                    all_datetime = all(isinstance(ts, datetime) for ts in timestamps_rel_sec)

                    if all_numeric:
                        logger.info("All 'timestamps_rel_sec' are numeric. Calculating absolute timestamps from relative offsets using 'start_time_dt_utc'.")
                        current_abs_ts_input = [start_time_dt_utc + timedelta(seconds=ts_rel) for ts_rel in timestamps_rel_sec]
                    elif all_datetime:
                        logger.info("All 'timestamps_rel_sec' are datetime objects. Using them directly as absolute timestamps.")
                        current_abs_ts_input = timestamps_rel_sec
                    else:
                        logger.error("'timestamps_rel_sec' contains mixed or unsupported types when 'absolute_timestamps_input' is missing. Attempting to process individually.")
                        processed_ts_input = []
                        for idx, ts_rel_item in enumerate(timestamps_rel_sec):
                            if isinstance(ts_rel_item, (int, float)):
                                processed_ts_input.append(start_time_dt_utc + timedelta(seconds=ts_rel_item))
                            elif isinstance(ts_rel_item, datetime):
                                processed_ts_input.append(ts_rel_item)
                            else:
                                logger.warning(f"Unsupported type {type(ts_rel_item)} at index {idx} in 'timestamps_rel_sec' during fallback. Using None.")
                                processed_ts_input.append(None)
                        current_abs_ts_input = processed_ts_input
                        # Ensure length matches num_data_points
                        if len(current_abs_ts_input) != num_data_points:
                             logger.warning(f"Length of processed timestamps ({len(current_abs_ts_input)}) from 'timestamps_rel_sec' fallback does not match num_data_points ({num_data_points}). Padding/truncating.")
                             current_abs_ts_input = self._ensure_array_exists(current_abs_ts_input, num_data_points)
                
                elif not absolute_timestamps_input and not timestamps_rel_sec: # Case: Both are empty/None
                     logger.error("Both 'absolute_timestamps_input' and 'timestamps_rel_sec' are empty. Cannot determine record timestamps. Falling back to Nones.")
                     current_abs_ts_input = [None] * num_data_points
                
                elif not timestamps_rel_sec: # Case: absolute_timestamps_input was inconsistent AND timestamps_rel_sec is empty
                    logger.warning("'absolute_timestamps_input' was inconsistent and 'timestamps_rel_sec' is also empty. Falling back to Nones for record timestamps.")
                    current_abs_ts_input = [None] * num_data_points
                else: # Should ideally not be reached if absolute_timestamps_input was bad and timestamps_rel_sec was present (covered by first 'if')
                    logger.error("Unexpected state in timestamp fallback logic when 'absolute_timestamps_input' was inconsistent. Defaulting to Nones for record timestamps.")
                    current_abs_ts_input = [None] * num_data_points
            else:
                current_abs_ts_input = absolute_timestamps_input
            
            logger.info(f"Starting to add {num_data_points} record messages.")
            for i in range(num_data_points):
                record_mesg = RecordMessage()
                record_timestamp_ms = self._get_utc_timestamp_ms(current_abs_ts_input[i], base_datetime_utc=start_time_dt_utc)
                record_mesg.timestamp = record_timestamp_ms

                if powers[i] is not None: record_mesg.power = int(powers[i])
                if heart_rates[i] is not None: record_mesg.heart_rate = int(heart_rates[i])
                if cadences[i] is not None: record_mesg.cadence = int(cadences[i])
                if speeds[i] is not None: 
                    record_mesg.speed = float(speeds[i])
                    record_mesg.enhanced_speed = float(speeds[i])
                if distances[i] is not None: record_mesg.distance = float(distances[i])
                builder.add(record_mesg)
            logger.info("Finished adding record messages.")

            # Calculate end timestamp
            if absolute_timestamps_input and absolute_timestamps_input[-1] is not None:
                unix_end_timestamp_ms = self._get_utc_timestamp_ms(absolute_timestamps_input[-1])
            elif total_duration > 0:
                unix_end_timestamp_ms = unix_start_timestamp_ms + int(total_duration * 1000)
            else: # Estimate from last record if possible, else just use start + small duration
                last_record_ts = builder.messages[-1].timestamp if builder.messages and hasattr(builder.messages[-1], 'timestamp') else unix_start_timestamp_ms
                unix_end_timestamp_ms = last_record_ts if last_record_ts > unix_start_timestamp_ms else unix_start_timestamp_ms + 1000
            
            event_mesg_stop = EventMessage()
            event_mesg_stop.timestamp = unix_end_timestamp_ms
            event_mesg_stop.event = Event.TIMER
            event_mesg_stop.event_type = EventType.STOP
            builder.add(event_mesg_stop)

            lap_mesg = LapMessage()
            lap_mesg.timestamp = unix_end_timestamp_ms
            lap_mesg.start_time = unix_start_timestamp_ms
            lap_mesg.total_elapsed_time = (unix_end_timestamp_ms - unix_start_timestamp_ms) # fit_tool expects ms for this field directly
            lap_mesg.total_timer_time = (unix_end_timestamp_ms - unix_start_timestamp_ms)
            lap_mesg.event = Event.LAP
            lap_mesg.event_type = EventType.STOP
            lap_mesg.lap_trigger = LapTrigger.MANUAL
            if avg_speed is not None: lap_mesg.avg_speed = float(avg_speed)
            if max_speed is not None: lap_mesg.max_speed = float(max_speed)
            if total_distance is not None: lap_mesg.total_distance = float(total_distance)
            if total_calories is not None: lap_mesg.total_calories = int(total_calories)
            if avg_power is not None: lap_mesg.avg_power = int(avg_power)
            if max_power is not None: lap_mesg.max_power = int(max_power)
            if normalized_power is not None and normalized_power > 0 : lap_mesg.normalized_power = int(normalized_power)
            if avg_cadence is not None: lap_mesg.avg_cadence = int(avg_cadence)
            if max_cadence is not None: lap_mesg.max_cadence = int(max_cadence)
            if avg_heart_rate is not None: lap_mesg.avg_heart_rate = int(avg_heart_rate)
            if max_heart_rate is not None: lap_mesg.max_heart_rate = int(max_heart_rate)
            if workout_type == 'bike': lap_mesg.sport = Sport.CYCLING
            elif workout_type == 'run': lap_mesg.sport = Sport.RUNNING
            else: lap_mesg.sport = Sport.GENERIC
            builder.add(lap_mesg)

            session_mesg = SessionMessage()
            session_mesg.timestamp = unix_end_timestamp_ms
            session_mesg.start_time = unix_start_timestamp_ms
            session_mesg.total_elapsed_time = (unix_end_timestamp_ms - unix_start_timestamp_ms)
            session_mesg.total_timer_time = (unix_end_timestamp_ms - unix_start_timestamp_ms)
            session_mesg.event = Event.SESSION
            session_mesg.event_type = EventType.STOP
            session_mesg.trigger = SessionTrigger.ACTIVITY_END
            if workout_type == 'bike': 
                session_mesg.sport = Sport.CYCLING
                session_mesg.sub_sport = SubSport.INDOOR_CYCLING
            elif workout_type == 'run': 
                session_mesg.sport = Sport.RUNNING
                session_mesg.sub_sport = SubSport.TREADMILL
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
            builder.add(session_mesg)

            activity_mesg = ActivityMessage()
            activity_mesg.timestamp = unix_start_timestamp_ms # Activity timestamp is start of activity
            activity_mesg.total_timer_time = (unix_end_timestamp_ms - unix_start_timestamp_ms)
            activity_mesg.num_sessions = 1
            activity_mesg.type = Event.ACTIVITY # fit_tool might use Event enum for ActivityType
            activity_mesg.event = Event.ACTIVITY
            activity_mesg.event_type = EventType.STOP
            builder.add(activity_mesg)

            unix_start_timestamp_sec_for_filename = unix_start_timestamp_ms // 1000
            file_name = f"{workout_type}_{datetime.fromtimestamp(unix_start_timestamp_sec_for_filename).strftime('%Y%m%d_%H%M%S')}.fit"
            output_path = os.path.join(self.output_dir, file_name)
            
            fit_file = builder.build()
            fit_file.to_file(output_path)
            logger.info(f"FIT file successfully created: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error converting workout to FIT: {str(e)}")
            logger.error(traceback.format_exc())
            return None

# Example usage (remains for testing, not part of the class)
if __name__ == "__main__":
    # ... (example usage code can be kept as is or removed if not needed for deployment)
    pass # Placeholder for example usage if kept

