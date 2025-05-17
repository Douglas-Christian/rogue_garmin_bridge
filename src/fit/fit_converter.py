"""
FIT File Converter Module for Rogue to Garmin Bridge

This module handles conversion of processed workout data to Garmin FIT format.
"""

import os
import logging
import traceback
import math # For rounding
from typing import Dict, List, Any, Optional
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
    Event, EventType, LapTrigger, SessionTrigger, ActivityType
)

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("fit_converter")

# FIT epoch constant for specific fields like activity_mesg.local_timestamp
FIT_EPOCH_DATETIME_UTC = datetime(1989, 12, 31, 0, 0, 0, tzinfo=timezone.utc)

class FITConverter:
    """
    Class for converting processed workout data to Garmin FIT format.
    """
    
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def _ensure_datetime_utc(self, time_input: Any, base_datetime_utc: Optional[datetime] = None) -> Optional[datetime]:
        dt_obj = None
        if isinstance(time_input, datetime):
            dt_obj = time_input
        elif isinstance(time_input, str):
            try:
                processed_time_input = time_input
                if processed_time_input.endswith("Z"):
                    processed_time_input = processed_time_input[:-1] + "+00:00"
                dt_obj = datetime.fromisoformat(processed_time_input)
            except ValueError:
                logger.warning(f"Could not parse datetime string: {time_input}.")
                return None
        elif isinstance(time_input, (int, float)):
            if time_input > 946684800: # Approx. 2000-01-01 in seconds
                try:
                    if time_input > 946684800000: # Approx. 2000-01-01 in milliseconds
                         dt_obj = datetime.fromtimestamp(time_input / 1000.0, timezone.utc)
                    else:
                         dt_obj = datetime.fromtimestamp(time_input, timezone.utc)
                except (OSError, OverflowError):
                    logger.warning(f"Could not convert Unix timestamp: {time_input}")
                    return None
            elif base_datetime_utc: # Assume it's a relative offset in seconds
                dt_obj = base_datetime_utc + timedelta(seconds=time_input)
            else:
                logger.warning(f"Numeric time input {time_input} is ambiguous without a base datetime.")
                return None
        else:
            logger.warning(f"Invalid time input type: {type(time_input)}.")
            return None

        if dt_obj is None: return None

        if dt_obj.tzinfo is None or dt_obj.tzinfo.utcoffset(dt_obj) is None:
            dt_obj = dt_obj.replace(tzinfo=timezone.utc)
        elif dt_obj.tzinfo != timezone.utc:
            dt_obj = dt_obj.astimezone(timezone.utc)
        return dt_obj

    def _datetime_to_unix_epoch_milliseconds(self, dt_obj: Optional[datetime]) -> Optional[int]:
        """Converts a UTC datetime object to integer milliseconds since Unix epoch."""
        if dt_obj is None: return None
        if dt_obj.tzinfo is None or dt_obj.tzinfo.utcoffset(dt_obj) is None:
            dt_obj_utc = dt_obj.replace(tzinfo=timezone.utc)
        elif dt_obj.tzinfo != timezone.utc:
            dt_obj_utc = dt_obj.astimezone(timezone.utc)
        else:
            dt_obj_utc = dt_obj
        return math.ceil(dt_obj_utc.timestamp() * 1000)

    def _datetime_to_fit_epoch_seconds_for_local(self, dt_obj: Optional[datetime]) -> Optional[int]:
        """Converts a UTC datetime object to integer seconds since FIT epoch (for local_timestamp field)."""
        if dt_obj is None: return None
        if dt_obj.tzinfo is None or dt_obj.tzinfo.utcoffset(dt_obj) is None:
            dt_obj_utc = dt_obj.replace(tzinfo=timezone.utc)
        elif dt_obj.tzinfo != timezone.utc:
            dt_obj_utc = dt_obj.astimezone(timezone.utc)
        else:
            dt_obj_utc = dt_obj
        
        if dt_obj_utc < FIT_EPOCH_DATETIME_UTC:
            logger.error(f"Cannot convert datetime {dt_obj_utc} to FIT epoch seconds as it's before FIT epoch {FIT_EPOCH_DATETIME_UTC}")
            return 0
        return int((dt_obj_utc - FIT_EPOCH_DATETIME_UTC).total_seconds())

    def _ensure_array_exists(self, array, expected_length):
        if not array:
            return [None] * expected_length
        if len(array) < expected_length:
            return array + [None] * (expected_length - len(array))
        if len(array) > expected_length:
            return array[:expected_length]
        return array

    def convert_workout(self, processed_data, user_profile=None):
        try:
            workout_type = processed_data.get("workout_type", "bike")
            start_time_metadata_input = processed_data.get("start_time")
            
            total_duration_from_data = float(processed_data.get("total_duration", 0))
            total_distance = float(processed_data.get("total_distance", 0))
            total_calories = int(processed_data.get("total_calories", 0))
            avg_power = processed_data.get("avg_power")
            max_power = processed_data.get("max_power")
            avg_heart_rate = processed_data.get("avg_heart_rate")
            max_heart_rate = processed_data.get("max_heart_rate")
            avg_cadence = processed_data.get("avg_cadence")
            max_cadence = processed_data.get("max_cadence")
            avg_speed = processed_data.get("avg_speed") 
            max_speed = processed_data.get("max_speed") 
            normalized_power = processed_data.get("normalized_power")

            data_series = processed_data.get("data_series", {})
            timestamps_rel_sec = data_series.get("timestamps", [])
            absolute_timestamps_input = data_series.get("absolute_timestamps", [])

            if not absolute_timestamps_input and not timestamps_rel_sec:
                logger.error("No timestamps found. Cannot create FIT file.")
                return None
            
            num_data_points = len(absolute_timestamps_input) if absolute_timestamps_input else len(timestamps_rel_sec)
            if num_data_points == 0:
                logger.error("Zero data points. Cannot create FIT file.")
                return None

            logger.info(f"Processing {workout_type} workout with {num_data_points} data points.")

            powers = self._ensure_array_exists(data_series.get("powers"), num_data_points)
            heart_rates = self._ensure_array_exists(data_series.get("heart_rates"), num_data_points)
            cadences = self._ensure_array_exists(data_series.get("cadences"), num_data_points)
            speeds = self._ensure_array_exists(data_series.get("speeds"), num_data_points)
            distances = self._ensure_array_exists(data_series.get("distances"), num_data_points)

            start_time_dt_utc = None
            if absolute_timestamps_input and absolute_timestamps_input[0] is not None:
                start_time_dt_utc = self._ensure_datetime_utc(absolute_timestamps_input[0])
            
            if not start_time_dt_utc:
                start_time_dt_utc = self._ensure_datetime_utc(start_time_metadata_input)
            
            if not start_time_dt_utc:
                logger.warning("Could not determine a valid start time. Using current UTC time.")
                start_time_dt_utc = datetime.now(timezone.utc)
            logger.info(f"Activity start time (UTC): {start_time_dt_utc}")

            record_datetimes: List[Optional[datetime]] = [None] * num_data_points
            if absolute_timestamps_input:
                for i in range(num_data_points):
                    record_datetimes[i] = self._ensure_datetime_utc(absolute_timestamps_input[i], base_datetime_utc=start_time_dt_utc)
            elif timestamps_rel_sec:
                for i in range(num_data_points):
                    record_datetimes[i] = self._ensure_datetime_utc(timestamps_rel_sec[i], base_datetime_utc=start_time_dt_utc)
            
            valid_records_indices = [i for i, dt in enumerate(record_datetimes) if dt is not None]
            if not valid_records_indices:
                logger.error("No valid record timestamps. Cannot create FIT file.")
                return None
            
            first_valid_record_dt = record_datetimes[valid_records_indices[0]]
            if first_valid_record_dt and first_valid_record_dt < start_time_dt_utc:
                logger.info(f"Adjusting activity start time from {start_time_dt_utc} to {first_valid_record_dt}.")
                start_time_dt_utc = first_valid_record_dt
            
            actual_total_duration_seconds = 0.0
            last_valid_record_dt = record_datetimes[valid_records_indices[-1]]

            if total_duration_from_data > 0:
                actual_total_duration_seconds = total_duration_from_data
            elif first_valid_record_dt and last_valid_record_dt:
                actual_total_duration_seconds = (last_valid_record_dt - first_valid_record_dt).total_seconds()
            
            if actual_total_duration_seconds <= 0:
                actual_total_duration_seconds = float(len(valid_records_indices))
                logger.warning(f"Total duration invalid, estimated to {actual_total_duration_seconds}s.")

            end_time_dt_utc = start_time_dt_utc + timedelta(seconds=actual_total_duration_seconds)

            unix_ms_start_time = self._datetime_to_unix_epoch_milliseconds(start_time_dt_utc)
            unix_ms_end_time = self._datetime_to_unix_epoch_milliseconds(end_time_dt_utc)

            if unix_ms_start_time is None:
                logger.error("Could not convert start_time_dt_utc to Unix ms. Aborting.")
                return None

            builder = FitFileBuilder(auto_define=True)

            file_id_mesg = FileIdMessage()
            file_id_mesg.type = FileType.ACTIVITY
            try: file_id_mesg.manufacturer = Manufacturer.ZWIFT
            except AttributeError: file_id_mesg.manufacturer = 281
            file_id_mesg.product = 3907
            file_id_mesg.serial_number = processed_data.get("serial_number", 123456789)
            file_id_mesg.time_created = unix_ms_start_time
            builder.add(file_id_mesg)

            device_info_mesg = DeviceInfoMessage()
            device_info_mesg.timestamp = unix_ms_start_time
            try: device_info_mesg.manufacturer = Manufacturer.ZWIFT
            except AttributeError: device_info_mesg.manufacturer = 281
            device_info_mesg.product = 3907
            device_info_mesg.serial_number = processed_data.get("serial_number", 123456789)
            device_info_mesg.software_version = processed_data.get("software_version_scaled", 100.0)
            device_info_mesg.hardware_version = processed_data.get("hardware_version", 1)
            builder.add(device_info_mesg)

            event_mesg_start = EventMessage()

            event_mesg_start.timestamp = unix_ms_start_time
            event_mesg_start.event = Event.TIMER
            event_mesg_start.event_type = EventType.START
            builder.add(event_mesg_start)
            
            for i in valid_records_indices:
                record_dt = record_datetimes[i]
                unix_ms_record_time = self._datetime_to_unix_epoch_milliseconds(record_dt)
                if unix_ms_record_time is None:
                    continue

                record_mesg = RecordMessage()
                record_mesg.timestamp = unix_ms_record_time
                if powers[i] is not None: record_mesg.power = int(powers[i])
                if heart_rates[i] is not None: record_mesg.heart_rate = int(heart_rates[i])
                if cadences[i] is not None: record_mesg.cadence = int(cadences[i])
                if speeds[i] is not None:
                    # Convert from km/h to m/s (FIT files require speed in m/s)
                    current_speed_kmh = float(speeds[i])
                    current_speed_mps = current_speed_kmh / 3.6  # Convert km/h to m/s
                    record_mesg.speed = current_speed_mps
                    record_mesg.enhanced_speed = current_speed_mps
                if distances[i] is not None: record_mesg.distance = float(distances[i])
                builder.add(record_mesg)

            unix_ms_event_stop_time = unix_ms_end_time
            if unix_ms_event_stop_time is None:
                logger.warning("unix_ms_end_time is None, using last valid record time for stop event.")
                last_valid_unix_ms_record_time = self._datetime_to_unix_epoch_milliseconds(record_datetimes[valid_records_indices[-1]])
                unix_ms_event_stop_time = last_valid_unix_ms_record_time if last_valid_unix_ms_record_time is not None else unix_ms_start_time
            
            event_mesg_stop = EventMessage()
            event_mesg_stop.timestamp = unix_ms_event_stop_time
            event_mesg_stop.event = Event.TIMER
            event_mesg_stop.event_type = EventType.STOP
            builder.add(event_mesg_stop)

            lap_mesg = LapMessage()
            lap_mesg.timestamp = unix_ms_event_stop_time
            lap_mesg.start_time = unix_ms_start_time
            lap_mesg.total_elapsed_time = actual_total_duration_seconds
            lap_mesg.total_timer_time = actual_total_duration_seconds
            lap_mesg.event = Event.LAP
            lap_mesg.event_type = EventType.STOP
            lap_mesg.lap_trigger = LapTrigger.MANUAL
            if avg_speed is not None:
                # Convert from km/h to m/s (FIT files require speed in m/s)
                avg_speed_kmh = float(avg_speed)
                avg_speed_mps = avg_speed_kmh / 3.6  # Convert km/h to m/s
                lap_mesg.avg_speed = avg_speed_mps
            if max_speed is not None:
                # Convert from km/h to m/s (FIT files require speed in m/s)
                max_speed_kmh = float(max_speed)
                max_speed_mps = max_speed_kmh / 3.6  # Convert km/h to m/s
                lap_mesg.max_speed = max_speed_mps
            if total_distance is not None: lap_mesg.total_distance = float(total_distance)
            if total_calories is not None: lap_mesg.total_calories = int(total_calories)
            if avg_power is not None: lap_mesg.avg_power = int(avg_power)
            if max_power is not None: lap_mesg.max_power = int(max_power)
            if normalized_power is not None and normalized_power > 0 : lap_mesg.normalized_power = int(normalized_power)
            if avg_cadence is not None: lap_mesg.avg_cadence = int(avg_cadence)
            if max_cadence is not None: lap_mesg.max_cadence = int(max_cadence)
            if avg_heart_rate is not None: lap_mesg.avg_heart_rate = int(avg_heart_rate)
            if max_heart_rate is not None: lap_mesg.max_heart_rate = int(max_heart_rate)
            if workout_type == "bike":
                lap_mesg.sport = Sport.CYCLING
                try:
                    lap_mesg.sub_sport = SubSport.INDOOR_CYCLING
                    logger.info("Set LapMessage SubSport to INDOOR_CYCLING.")
                except AttributeError:
                    logger.warning("SubSport.INDOOR_CYCLING not found for LapMessage. Trying SubSport.VIRTUAL_ACTIVITY.")
                    try:
                        lap_mesg.sub_sport = SubSport.VIRTUAL_ACTIVITY
                        logger.info("Set LapMessage SubSport to VIRTUAL_ACTIVITY.")
                    except AttributeError:
                        logger.warning("SubSport.VIRTUAL_ACTIVITY not found for LapMessage. Trying SubSport.ROAD.")
                        try:
                            lap_mesg.sub_sport = SubSport.ROAD # Original fallback
                            logger.info("Set LapMessage SubSport to ROAD.")
                        except AttributeError:
                            logger.warning("SubSport.ROAD not found for LapMessage. Using integer value 11 (Indoor Cycling).")
                            lap_mesg.sub_sport = 11 # Fallback to int for Indoor Cycling sub_sport
            # else: handle other workout types if necessary
            builder.add(lap_mesg)

            session_mesg = SessionMessage()
            session_mesg.timestamp = unix_ms_event_stop_time
            session_mesg.start_time = unix_ms_start_time
            session_mesg.total_elapsed_time = actual_total_duration_seconds
            session_mesg.total_timer_time = actual_total_duration_seconds
            session_mesg.event = Event.SESSION
            session_mesg.event_type = EventType.STOP
            session_mesg.trigger = SessionTrigger.ACTIVITY_END
            if avg_speed is not None:
                # Convert from km/h to m/s (FIT files require speed in m/s)
                avg_speed_kmh = float(avg_speed)
                avg_speed_mps = avg_speed_kmh / 3.6  # Convert km/h to m/s
                session_mesg.avg_speed = avg_speed_mps
            if max_speed is not None:
                # Convert from km/h to m/s (FIT files require speed in m/s)
                max_speed_kmh = float(max_speed)
                max_speed_mps = max_speed_kmh / 3.6  # Convert km/h to m/s
                session_mesg.max_speed = max_speed_mps
            if total_distance is not None: session_mesg.total_distance = float(total_distance)
            if total_calories is not None: session_mesg.total_calories = int(total_calories)
            if avg_power is not None: session_mesg.avg_power = int(avg_power)
            if max_power is not None: session_mesg.max_power = int(max_power)
            if normalized_power is not None and normalized_power > 0 : session_mesg.normalized_power = int(normalized_power)
            if avg_cadence is not None: session_mesg.avg_cadence = int(avg_cadence)
            if max_cadence is not None: session_mesg.max_cadence = int(max_cadence)
            if avg_heart_rate is not None: session_mesg.avg_heart_rate = int(avg_heart_rate)
            if max_heart_rate is not None: session_mesg.max_heart_rate = int(max_heart_rate)
            if workout_type == "bike":
                session_mesg.sport = Sport.CYCLING
                try:
                    session_mesg.sub_sport = SubSport.INDOOR_CYCLING
                    logger.info("Set SessionMessage SubSport to INDOOR_CYCLING.")
                except AttributeError:
                    logger.warning("SubSport.INDOOR_CYCLING not found for SessionMessage. Trying SubSport.VIRTUAL_ACTIVITY.")
                    try:
                        session_mesg.sub_sport = SubSport.VIRTUAL_ACTIVITY
                        logger.info("Set SessionMessage SubSport to VIRTUAL_ACTIVITY.")
                    except AttributeError:
                        logger.warning("SubSport.VIRTUAL_ACTIVITY not found for SessionMessage. Trying SubSport.ROAD.")
                        try:
                            session_mesg.sub_sport = SubSport.ROAD # Original fallback
                            logger.info("Set SessionMessage SubSport to ROAD.")
                        except AttributeError:
                            logger.warning("SubSport.ROAD not found for SessionMessage. Using integer value 11 (Indoor Cycling).")
                            session_mesg.sub_sport = 11 # Fallback to int for Indoor Cycling sub_sport
            # else: handle other workout types if necessary
            builder.add(session_mesg)

            activity_mesg = ActivityMessage()
            activity_mesg.timestamp = unix_ms_start_time
            activity_mesg.total_timer_time = actual_total_duration_seconds
            activity_mesg.num_sessions = 1
            # Set ActivityType based on workout_type
            if workout_type == "bike":
                try:
                    activity_mesg.type = ActivityType.INDOOR_CYCLING
                    logger.info("Set ActivityType to INDOOR_CYCLING for bike workout.")
                except AttributeError:
                    logger.warning("ActivityType.INDOOR_CYCLING not found. Trying ActivityType.CYCLING.")
                    try:
                        activity_mesg.type = ActivityType.CYCLING
                        logger.info("Set ActivityType to CYCLING for bike workout.")
                    except AttributeError:
                        logger.warning("ActivityType.CYCLING not found. Using integer value 11 (Indoor Cycling) for bike workout.")
                        activity_mesg.type = 11 # Standard FIT value for Indoor Cycling
            else:
                # For other workout types, attempt to use a specific type or fallback to GENERAL
                try:
                    activity_mesg.type = ActivityType.GENERAL # Default for non-bike or if specific type is not handled
                    logger.info(f"Set ActivityType to GENERAL for workout_type '{workout_type}'.")
                except AttributeError:
                    logger.warning(f"ActivityType.GENERAL not found for workout_type '{workout_type}', using integer value 0.")
                    activity_mesg.type = 0 # Fallback to generic

            activity_mesg.event = Event.ACTIVITY
            activity_mesg.event_type = EventType.STOP
            
            local_midnight_dt = start_time_dt_utc.replace(hour=0, minute=0, second=0, microsecond=0)
            activity_mesg.local_timestamp = self._datetime_to_fit_epoch_seconds_for_local(local_midnight_dt)
            builder.add(activity_mesg)

            file_name_base = f"{workout_type}_{start_time_dt_utc.strftime("%Y%m%d_%H%M%S")}"
            output_path = os.path.join(self.output_dir, f"{file_name_base}.fit")
            
            fit_file = builder.build()
            fit_file.to_file(output_path)

            logger.info(f"FIT file successfully created: {output_path}")
            return output_path
        
        except Exception as e:
            logger.error(f"FIT Conversion Exception: {e}")
            logger.error(f"Full Traceback Below:\n{traceback.format_exc()}")
            return None

if __name__ == "__main__":
    converter = FITConverter(output_dir="./generated_fit_files")
    sample_start_time = datetime.now(timezone.utc) - timedelta(minutes=30)
    num_points = 180
    sample_processed_data = {
        "workout_type": "bike",
        "total_duration": float(num_points),
        "total_distance": 5000.0,
        "total_calories": 200,
        "avg_power": 150,
        "max_power": 300,
        "avg_heart_rate": 140,
        "max_heart_rate": 160,
        "avg_cadence": 85,
        "max_cadence": 100,
        "avg_speed": 27.7,
        "max_speed": 30.5,
        "data_series": {
            "absolute_timestamps": [(sample_start_time + timedelta(seconds=i)).isoformat() for i in range(num_points)],
            "powers": [100 + (i % 50) for i in range(num_points)],
            "heart_rates": [120 + (i % 40) for i in range(num_points)],
            "cadences": [80 + (i % 10) for i in range(num_points)],
            "speeds": [(25.0 + (i % 5)) for i in range(num_points)],
            "distances": [(float(i) * (5000.0 / float(num_points))) for i in range(num_points)]
        }
    }
    
    fit_file_path = converter.convert_workout(sample_processed_data)
    if fit_file_path:
        print(f"Test FIT file generated: {fit_file_path}")
    else:
        print("Test FIT file generation failed.")

