#!/usr/bin/env python3
"""
Database Module for Rogue to Garmin Bridge

This module handles the SQLite database operations for storing workout data.
"""

import sqlite3
import os
import json
import time
from datetime import datetime, timezone
import sys
import threading
from typing import Dict, List, Optional, Any

# Add the project root to the path so we can use absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.utils.logging_config import get_component_logger

# Get component logger
logger = get_component_logger('database')

class Database:
    """
    SQLite database handler for the Rogue Garmin Bridge.
    Manages workout data storage and retrieval with thread-safe connections.
    """
    
    def __init__(self, db_path: str):
        """
        Initialize the database.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        # Thread-local storage for connections
        self.local = threading.local()
        
        # Create database directory if it doesn't exist
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Initialize database - create tables once
        with self._get_connection() as conn:
            self._create_tables(conn)
    
    def _get_connection(self):
        """
        Get a thread-local connection to the database.
        Each thread gets its own connection to avoid SQLite threading issues.
        
        Returns:
            SQLite connection object
        """
        # Create a new connection for this thread if it doesn't exist
        if not hasattr(self.local, 'conn') or self.local.conn is None:
            try:
                logger.debug(f"Creating new database connection for thread {threading.get_ident()}")
                self.local.conn = sqlite3.connect(self.db_path)
                self.local.conn.row_factory = sqlite3.Row  # Return rows as dictionaries
            except sqlite3.Error as e:
                logger.error(f"Error connecting to database: {str(e)}")
                raise
        
        return self.local.conn
    
    def _create_tables(self, conn) -> None:
        """
        Create database tables if they don't exist.
        
        Args:
            conn: SQLite connection
        """
        try:
            cursor = conn.cursor()
            
            # Devices table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS devices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    address TEXT UNIQUE,
                    name TEXT,
                    device_type TEXT,
                    last_connected REAL,
                    metadata TEXT
                )
            ''')
            
            # Workouts table - using REAL for timestamp fields to store Unix timestamps
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS workouts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id INTEGER,
                    start_time REAL,
                    end_time REAL,
                    duration INTEGER,
                    workout_type TEXT,
                    summary TEXT,
                    fit_file_path TEXT,
                    uploaded_to_garmin INTEGER DEFAULT 0,
                    FOREIGN KEY (device_id) REFERENCES devices (id)
                )
            ''')
            
            # Workout data table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS workout_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    workout_id INTEGER,
                    timestamp REAL,  /* Using REAL to support fractional seconds */
                    data TEXT,
                    FOREIGN KEY (workout_id) REFERENCES workouts (id)
                )
            ''')
            
            # Configuration table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS configuration (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            ''')
            
            # User profile table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_profile (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    age INTEGER,
                    weight REAL,
                    height REAL,
                    gender TEXT,
                    max_heart_rate INTEGER,
                    resting_heart_rate INTEGER,
                    garmin_username TEXT,
                    garmin_password TEXT
                )
            ''')
            
            conn.commit()
            logger.info("Database tables created")
        except sqlite3.Error as e:
            logger.error(f"Error creating tables: {str(e)}")
            raise
    
    def add_device(self, address: str, name: str, device_type: str, metadata: Dict[str, Any] = None) -> int:
        """
        Add a device to the database.
        
        Args:
            address: Device BLE address
            name: Device name
            device_type: Device type (bike, rower, etc.)
            metadata: Additional device metadata
            
        Returns:
            Device ID
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Convert metadata to JSON string
            metadata_json = json.dumps(metadata) if metadata else '{}'
            
            # Check if device already exists
            cursor.execute(
                "SELECT id FROM devices WHERE address = ?",
                (address,)
            )
            result = cursor.fetchone()
            
            # Get current Unix timestamp
            current_time = time.time()
            
            if result:
                # Update existing device
                device_id = result['id']
                cursor.execute(
                    "UPDATE devices SET name = ?, device_type = ?, last_connected = ?, metadata = ? WHERE id = ?",
                    (name, device_type, current_time, metadata_json, device_id)
                )
            else:
                # Insert new device
                cursor.execute(
                    "INSERT INTO devices (address, name, device_type, last_connected, metadata) VALUES (?, ?, ?, ?, ?)",
                    (address, name, device_type, current_time, metadata_json)
                )
                device_id = cursor.lastrowid
            
            conn.commit()
            logger.info(f"Device {name} ({address}) {'updated' if result else 'added'} with ID {device_id}")
            return device_id
        except sqlite3.Error as e:
            logger.error(f"Error adding device: {str(e)}")
            raise
    
    def get_devices(self) -> List[Dict[str, Any]]:
        """
        Get all devices from the database.
        
        Returns:
            List of device dictionaries
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM devices")
            devices = [dict(row) for row in cursor.fetchall()]
            
            # Parse metadata JSON
            for device in devices:
                device['metadata'] = json.loads(device['metadata'])
            
            return devices
        except sqlite3.Error as e:
            logger.error(f"Error getting devices: {str(e)}")
            return []
    
    def get_device(self, device_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a device by ID.
        
        Args:
            device_id: Device ID
            
        Returns:
            Device dictionary or None if not found
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM devices WHERE id = ?", (device_id,))
            device = cursor.fetchone()
            
            if device:
                device_dict = dict(device)
                device_dict['metadata'] = json.loads(device_dict['metadata'])
                return device_dict
            return None
        except sqlite3.Error as e:
            logger.error(f"Error getting device: {str(e)}")
            return None
    
    def start_workout(self, device_id: int, workout_type: str, start_time: float = None) -> int:
        """
        Start a new workout session.
        
        Args:
            device_id: Device ID
            workout_type: Type of workout (bike, rower, etc.)
            start_time: Unix timestamp of workout start (optional, defaults to current time)
            
        Returns:
            Workout ID
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Use provided timestamp or current time
            current_timestamp = start_time if start_time is not None else time.time()
            
            cursor.execute(
                "INSERT INTO workouts (device_id, start_time, workout_type, summary) VALUES (?, ?, ?, ?)",
                (device_id, current_timestamp, workout_type, '{}')
            )
            workout_id = cursor.lastrowid
            
            conn.commit()
            logger.info(f"Started workout {workout_id} with device {device_id}")
            return workout_id
        except sqlite3.Error as e:
            logger.error(f"Error starting workout: {str(e)}")
            raise
    
    def end_workout(self, workout_id, end_time=None):
        """
        End a workout by updating its end_time.
        
        Args:
            workout_id (int): The ID of the workout to end
            end_time (float, optional): The end time (timestamp) of the workout. 
                                        If not provided, current time is used.
                                        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Use current time if end_time not provided
            if end_time is None:
                end_time = time.time()
                
            # Get the workout to update
            cursor.execute(
                "SELECT id, start_time FROM workouts WHERE id = ?", 
                (workout_id,)
            )
            result = cursor.fetchone()
            
            if not result:
                logger.error(f"No workout found with ID {workout_id}")
                return False
                
            # Get the workout start time
            start_time = result['start_time']
                
            # Calculate duration
            duration = end_time - start_time
            
            # Update the workout with end time and duration
            cursor.execute(
                "UPDATE workouts SET end_time = ?, duration = ? WHERE id = ?",
                (end_time, duration, workout_id)
            )
            conn.commit()
            
            logger.info(f"Ended workout {workout_id} with duration {duration:.2f} seconds")
            return True
            
        except sqlite3.Error as e:
            logger.error(f"Error ending workout: {str(e)}")
            return False
    
    def add_workout_data(self, workout_id: int, timestamp: float, data: Dict[str, Any]) -> bool:
        """
        Add data point to a workout session.

        Args:
            workout_id: Workout ID
            timestamp: Data timestamp (seconds since workout start)
            data: Workout data

        Returns:
            True if successful, False otherwise
        """
        thread_id = threading.get_ident()
        logger.info(f"Adding data point for workout {workout_id} at timestamp {timestamp:.6f} in thread {thread_id}")
        
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # Verify workout exists
            cursor.execute("SELECT id FROM workouts WHERE id = ?", (workout_id,))
            workout = cursor.fetchone()
            if not workout:
                logger.error(f"Cannot add data point: Workout {workout_id} does not exist")
                return False

            # Convert data to JSON string
            data_json = json.dumps(data)

            # Insert data point - using REPLACE to handle any potential timestamp duplicates
            cursor.execute(
                """
                INSERT OR REPLACE INTO workout_data (workout_id, timestamp, data)
                VALUES (?, ?, ?)
                """,
                (workout_id, timestamp, data_json)
            )

            conn.commit()
            logger.info(f"Successfully added data point for workout {workout_id} at timestamp {timestamp:.6f}")
            return True
        except sqlite3.Error as e:
            logger.error(f"Error adding workout data for workout {workout_id}, timestamp {timestamp}: {str(e)}")
            # Attempt to rollback if needed
            try:
                conn.rollback()
            except Exception as rollback_error:
                logger.error(f"Error during rollback: {str(rollback_error)}")
            return False
    
    def get_workout(self, workout_id: int) -> Optional[Dict[str, Any]]:
        """
        Get workout information.
        
        Args:
            workout_id: Workout ID
            
        Returns:
            Workout dictionary or None if not found
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM workouts WHERE id = ?", (workout_id,))
            workout = cursor.fetchone()
            
            if workout:
                workout_dict = dict(workout)
                
                # Add ISO-formatted timestamps for UI display
                if workout_dict['start_time'] is not None:
                    try:
                        # Convert string to float if needed
                        start_time = float(workout_dict['start_time']) if isinstance(workout_dict['start_time'], str) else workout_dict['start_time']
                        workout_dict['start_time_iso'] = datetime.fromtimestamp(
                            start_time, tz=timezone.utc
                        ).isoformat()
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Could not convert start_time to timestamp: {e}")
                        workout_dict['start_time_iso'] = "Unknown"
                
                if workout_dict['end_time'] is not None:
                    try:
                        # Convert string to float if needed
                        end_time = float(workout_dict['end_time']) if isinstance(workout_dict['end_time'], str) else workout_dict['end_time']
                        workout_dict['end_time_iso'] = datetime.fromtimestamp(
                            end_time, tz=timezone.utc
                        ).isoformat()
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Could not convert end_time to timestamp: {e}")
                        workout_dict['end_time_iso'] = "Unknown"
                
                # Parse JSON summary
                if workout_dict['summary']:
                    try:
                        workout_dict['summary'] = json.loads(workout_dict['summary'])
                    except (json.JSONDecodeError, TypeError):
                        workout_dict['summary'] = {}
                else:
                    workout_dict['summary'] = {}
                
                return workout_dict
            return None
        except sqlite3.Error as e:
            logger.error(f"Error getting workout: {str(e)}")
            return None
    
    def get_workout_data(self, workout_id: int) -> List[Dict[str, Any]]:
        """
        Get all data points for a workout.
        
        Args:
            workout_id: Workout ID
            
        Returns:
            List of workout data dictionaries
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Get workout data points ordered by timestamp
            cursor.execute(
                """
                SELECT * FROM workout_data
                WHERE workout_id = ?
                ORDER BY timestamp ASC
                """,
                (workout_id,)
            )
            
            data_points = []
            for row in cursor.fetchall():
                data_point = dict(row)
                
                # Parse JSON data
                if data_point['data']:
                    data_point['data'] = json.loads(data_point['data'])
                else:
                    data_point['data'] = {}
                
                data_points.append(data_point)
            
            return data_points
        except sqlite3.Error as e:
            logger.error(f"Error getting workout data: {str(e)}")
            return []
    
    def get_workouts(self, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get recent workouts.
        
        Args:
            limit: Maximum number of workouts to return
            offset: Offset for pagination
            
        Returns:
            List of workouts
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT * FROM workouts ORDER BY start_time DESC LIMIT ? OFFSET ?",
                (limit, offset)
            )
            
            workouts = []
            for workout in cursor.fetchall():
                workout = dict(workout)
                
                # Try to add device name from device table
                if workout.get('device_id') is not None:
                    cursor.execute(
                        "SELECT name, device_type FROM devices WHERE id = ?", 
                        (workout['device_id'],)
                    )
                    device = cursor.fetchone()
                    if device:
                        workout['device_name'] = device['name']
                        workout['device_type'] = device['device_type']
                    else:
                        # Try to use the device_id as device_name if it's a string (like a MAC address)
                        device_id = workout.get('device_id')
                        if isinstance(device_id, str):
                            workout['device_name'] = f"Device {device_id}"
                        else:
                            workout['device_name'] = "Unknown Device"
                
                # If device_type is NULL, add a default based on workout_type
                if workout.get('device_type') is None:
                    workout['device_type'] = workout.get('workout_type', 'unknown')
                
                # Add ISO-formatted timestamps for UI display
                if workout['start_time'] is not None:
                    try:
                        # Convert string to float if needed
                        start_time = float(workout['start_time']) if isinstance(workout['start_time'], str) else workout['start_time']
                        workout['start_time_iso'] = datetime.fromtimestamp(
                            start_time, tz=timezone.utc
                        ).isoformat()
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Could not convert start_time to timestamp: {e}")
                        workout['start_time_iso'] = "Unknown"
                
                if workout['end_time'] is not None:
                    try:
                        # Convert string to float if needed
                        end_time = float(workout['end_time']) if isinstance(workout['end_time'], str) else workout['end_time']
                        workout['end_time_iso'] = datetime.fromtimestamp(
                            end_time, tz=timezone.utc
                        ).isoformat()
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Could not convert end_time to timestamp: {e}")
                        workout['end_time_iso'] = "Unknown"
                
                # Parse JSON summary
                if workout['summary']:
                    try:
                        workout['summary'] = json.loads(workout['summary'])
                    except (json.JSONDecodeError, TypeError):
                        workout['summary'] = {}
                else:
                    workout['summary'] = {}
                
                workouts.append(workout)
            
            return workouts
        except sqlite3.Error as e:
            logger.error(f"Error getting workouts: {str(e)}")
            return []
    
    def set_config(self, key: str, value: Any) -> bool:
        """
        Set a configuration value.
        
        Args:
            key: Configuration key
            value: Configuration value (will be converted to JSON)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Convert value to JSON string
            value_json = json.dumps(value)
            
            cursor.execute(
                "INSERT OR REPLACE INTO configuration (key, value) VALUES (?, ?)",
                (key, value_json)
            )
            
            conn.commit()
            logger.debug(f"Set config {key} = {value}")
            return True
        except sqlite3.Error as e:
            logger.error(f"Error setting config: {str(e)}")
            return False
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT value FROM configuration WHERE key = ?", (key,))
            result = cursor.fetchone()
            
            if result:
                return json.loads(result['value'])
            return default
        except sqlite3.Error as e:
            logger.error(f"Error getting config: {str(e)}")
            return default
    
    def set_user_profile(self, profile: Dict[str, Any]) -> bool:
        """
        Set user profile information.
        
        Args:
            profile: User profile dictionary
            
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Check if profile exists
            cursor.execute("SELECT COUNT(*) as count FROM user_profile")
            count = cursor.fetchone()['count']
            
            if count > 0:
                # Update existing profile
                cursor.execute(
                    """
                    UPDATE user_profile SET 
                    name = ?, age = ?, weight = ?, height = ?, gender = ?,
                    max_heart_rate = ?, resting_heart_rate = ?,
                    garmin_username = ?, garmin_password = ?
                    WHERE id = 1
                    """,
                    (
                        profile.get('name', ''),
                        profile.get('age', 0),
                        profile.get('weight', 0.0),
                        profile.get('height', 0.0),
                        profile.get('gender', ''),
                        profile.get('max_heart_rate', 0),
                        profile.get('resting_heart_rate', 0),
                        profile.get('garmin_username', ''),
                        profile.get('garmin_password', '')
                    )
                )
            else:
                # Insert new profile
                cursor.execute(
                    """
                    INSERT INTO user_profile 
                    (name, age, weight, height, gender, max_heart_rate, resting_heart_rate, garmin_username, garmin_password)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        profile.get('name', ''),
                        profile.get('age', 0),
                        profile.get('weight', 0.0),
                        profile.get('height', 0.0),
                        profile.get('gender', ''),
                        profile.get('max_heart_rate', 0),
                        profile.get('resting_heart_rate', 0),
                        profile.get('garmin_username', ''),
                        profile.get('garmin_password', '')
                    )
                )
            
            conn.commit()
            logger.info("User profile updated")
            return True
        except sqlite3.Error as e:
            logger.error(f"Error setting user profile: {str(e)}")
            return False
    
    def get_user_profile(self) -> Optional[Dict[str, Any]]:
        """
        Get user profile information.
        
        Returns:
            User profile dictionary or None if not found
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM user_profile LIMIT 1")
            profile = cursor.fetchone()
            
            if profile:
                return dict(profile)
            return None
        except sqlite3.Error as e:
            logger.error(f"Error getting user profile: {str(e)}")
            return None
    
    def mark_workout_uploaded(self, workout_id: int) -> bool:
        """
        Mark a workout as uploaded to Garmin Connect.
        
        Args:
            workout_id: Workout ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                "UPDATE workouts SET uploaded_to_garmin = 1 WHERE id = ?",
                (workout_id,)
            )
            conn.commit()
            logger.info(f"Workout {workout_id} marked as uploaded to Garmin Connect")
            return True
        except sqlite3.Error as e:
            logger.error(f"Error marking workout as uploaded: {str(e)}")
            return False


# Example usage
if __name__ == "__main__":
    db = Database("test.db")
    
    # Add a device
    device_id = db.add_device(
        address="00:11:22:33:44:55",
        name="Test Bike",
        device_type="bike",
        metadata={"manufacturer": "Rogue", "model": "Echo Bike"}
    )
    
    # Start a workout
    workout_id = db.start_workout(device_id, "bike")
    
    # Add some workout data
    db.add_workout_data(workout_id, 0, {"power": 150, "cadence": 80, "heart_rate": 120})
    db.add_workout_data(workout_id, 1, {"power": 155, "cadence": 82, "heart_rate": 122})
    db.add_workout_data(workout_id, 2, {"power": 160, "cadence": 85, "heart_rate": 125})
    
    # End the workout
    db.end_workout(workout_id, {"avg_power": 155, "avg_cadence": 82, "avg_heart_rate": 122})
    
    # Get workout data
    data = db.get_workout_data(workout_id)
    print(f"Workout data: {data}")
    
    # Set user profile
    db.set_user_profile({
        "name": "John Doe",
        "age": 35,
        "weight": 75.0,
        "height": 180.0,
        "gender": "male",
        "max_heart_rate": 185,
        "resting_heart_rate": 60
    })
    
    # Get user profile
    profile = db.get_user_profile()
    print(f"User profile: {profile}")