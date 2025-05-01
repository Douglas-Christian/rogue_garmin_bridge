#!/usr/bin/env python3
"""
Migration script to convert all timestamp values in the database to float type.
This ensures consistent data types for timestamp fields and eliminates the need
for the string-to-float conversion workarounds.
"""

import os
import sys
import sqlite3
import logging
from datetime import datetime, timezone

# Add the project root to the path so we can use absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.utils.logging_config import get_component_logger
from src.data.database import Database

# Set up logging
logger = get_component_logger('timestamp_migration')

def convert_to_float(timestamp_val):
    """
    Convert a timestamp value to float.
    Handles:
    - Float values (returns as is)
    - Int values (converts to float)
    - String representations of float/int values
    - ISO format timestamp strings
    
    Args:
        timestamp_val: The timestamp value to convert
        
    Returns:
        float: The timestamp as a float
        None: If conversion fails
    """
    if timestamp_val is None:
        return None
        
    if isinstance(timestamp_val, (float, int)):
        return float(timestamp_val)
    
    # Try direct float conversion first
    try:
        return float(timestamp_val)
    except (ValueError, TypeError):
        pass
    
    # Try ISO format string
    try:
        dt = datetime.fromisoformat(timestamp_val.replace('Z', '+00:00'))
        return dt.timestamp()
    except (ValueError, AttributeError):
        pass
    
    # Try other common formats
    formats = [
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%dT%H:%M:%S.%f',
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d %H:%M:%S.%f'
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(timestamp_val, fmt)
            dt = dt.replace(tzinfo=timezone.utc)
            return dt.timestamp()
        except (ValueError, TypeError):
            continue
    
    logger.warning(f"Could not convert timestamp value: {timestamp_val}")
    return None

def is_number_value(val):
    """
    Check if a value is a proper number (int or float) or can be converted to one.
    This helps handle SQLite's type conversion behavior.
    
    Args:
        val: The value to check
        
    Returns:
        bool: True if the value is a number or can be converted to a number
    """
    if isinstance(val, (int, float)):
        return True
    
    try:
        float(val)
        return True
    except (ValueError, TypeError):
        return False

def migrate_timestamps():
    """
    Convert all timestamp values in the database to float type.
    """
    # Get database path from the Database class
    db_path = os.path.join(os.path.dirname(__file__), 'rogue_garmin.db')
    
    logger.info(f"Starting timestamp migration for database at {db_path}")
    
    # Connect directly to the database for this migration
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Migrate timestamps in workouts table
    logger.info("Migrating timestamps in workouts table...")
    
    # Get all workouts
    cursor.execute("SELECT id, start_time, end_time FROM workouts")
    workouts = cursor.fetchall()
    
    migrated_count = 0
    for workout in workouts:
        workout_id = workout['id']
        start_time = workout['start_time']
        end_time = workout['end_time']
        
        # Check if start_time needs conversion - if it's not a number value
        if start_time is not None and not is_number_value(start_time):
            new_start_time = convert_to_float(start_time)
            if new_start_time is not None:
                logger.info(f"Converting start_time for workout {workout_id} from {start_time} to {new_start_time}")
                cursor.execute(
                    "UPDATE workouts SET start_time = ? WHERE id = ?",
                    (new_start_time, workout_id)
                )
                migrated_count += 1
            else:
                logger.warning(f"Could not convert start_time '{start_time}' to float for workout {workout_id}")
        elif start_time is not None:
            # Ensure values are stored as actual float values in the database
            new_start_time = float(start_time)
            cursor.execute(
                "UPDATE workouts SET start_time = ? WHERE id = ?",
                (new_start_time, workout_id)
            )
        
        # Check if end_time needs conversion - if it's not a number value
        if end_time is not None and not is_number_value(end_time):
            new_end_time = convert_to_float(end_time)
            if new_end_time is not None:
                logger.info(f"Converting end_time for workout {workout_id} from {end_time} to {new_end_time}")
                cursor.execute(
                    "UPDATE workouts SET end_time = ? WHERE id = ?",
                    (new_end_time, workout_id)
                )
                migrated_count += 1
            else:
                logger.warning(f"Could not convert end_time '{end_time}' to float for workout {workout_id}")
        elif end_time is not None:
            # Ensure values are stored as actual float values in the database
            new_end_time = float(end_time)
            cursor.execute(
                "UPDATE workouts SET end_time = ? WHERE id = ?",
                (new_end_time, workout_id)
            )
    
    # Migrate timestamps in workout_data table
    logger.info("Migrating timestamps in workout_data table...")
    
    # Get all workout data entries
    cursor.execute("SELECT id, workout_id, timestamp FROM workout_data")
    data_points = cursor.fetchall()
    
    for data_point in data_points:
        data_id = data_point['id']
        workout_id = data_point['workout_id']
        timestamp = data_point['timestamp']
        
        # Check if timestamp needs conversion - if it's not a number value
        if timestamp is not None and not is_number_value(timestamp):
            new_timestamp = convert_to_float(timestamp)
            if new_timestamp is not None:
                logger.info(f"Converting timestamp for data point {data_id} (workout {workout_id}) from {timestamp} to {new_timestamp}")
                cursor.execute(
                    "UPDATE workout_data SET timestamp = ? WHERE id = ?",
                    (new_timestamp, data_id)
                )
                migrated_count += 1
            else:
                logger.warning(f"Could not convert timestamp '{timestamp}' to float for data point {data_id}")
        elif timestamp is not None:
            # Ensure values are stored as actual float values in the database
            new_timestamp = float(timestamp)
            cursor.execute(
                "UPDATE workout_data SET timestamp = ? WHERE id = ?",
                (new_timestamp, data_id)
            )
    
    # Commit changes
    conn.commit()
    
    logger.info(f"Timestamp migration completed. Converted {migrated_count} timestamp values to float.")

if __name__ == "__main__":
    migrate_timestamps()