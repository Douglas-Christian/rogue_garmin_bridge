#!/usr/bin/env python3
"""
Database Module for Rogue to Garmin Bridge

This module handles database operations for storing workout data,
device information, and application configuration.
"""

import os
import sqlite3
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('database')

class Database:
    """
    Database class for managing SQLite database operations.
    """
    
    def __init__(self, db_path: str):
        """
        Initialize the database.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        
        # Create database directory if it doesn't exist
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Initialize database
        self._connect()
        self._create_tables()
        self._disconnect()
    
    def _connect(self) -> None:
        """Connect to the SQLite database."""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row  # Return rows as dictionaries
            self.cursor = self.conn.cursor()
            logger.debug("Connected to database")
        except sqlite3.Error as e:
            logger.error(f"Error connecting to database: {str(e)}")
            raise
    
    def _disconnect(self) -> None:
        """Disconnect from the SQLite database."""
        if self.conn:
            self.conn.close()
            self.conn = None
            self.cursor = None
            logger.debug("Disconnected from database")
    
    def _create_tables(self) -> None:
        """Create database tables if they don't exist."""
        try:
            # Devices table
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS devices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    address TEXT UNIQUE,
                    name TEXT,
                    device_type TEXT,
                    last_connected TEXT,
                    metadata TEXT
                )
            ''')
            
            # Workouts table
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS workouts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id INTEGER,
                    start_time TEXT,
                    end_time TEXT,
                    duration INTEGER,
                    workout_type TEXT,
                    summary TEXT,
                    fit_file_path TEXT,
                    uploaded_to_garmin INTEGER DEFAULT 0,
                    FOREIGN KEY (device_id) REFERENCES devices (id)
                )
            ''')
            
            # Workout data table
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS workout_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    workout_id INTEGER,
                    timestamp TEXT,
                    data TEXT,
                    FOREIGN KEY (workout_id) REFERENCES workouts (id)
                )
            ''')
            
            # Configuration table
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS configuration (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            ''')
            
            # User profile table
            self.cursor.execute('''
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
            
            self.conn.commit()
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
            self._connect()
            
            # Convert metadata to JSON string
            metadata_json = json.dumps(metadata) if metadata else '{}'
            
            # Check if device already exists
            self.cursor.execute(
                "SELECT id FROM devices WHERE address = ?",
                (address,)
            )
            result = self.cursor.fetchone()
            
            if result:
                # Update existing device
                device_id = result['id']
                self.cursor.execute(
                    "UPDATE devices SET name = ?, device_type = ?, last_connected = ?, metadata = ? WHERE id = ?",
                    (name, device_type, datetime.now().isoformat(), metadata_json, device_id)
                )
            else:
                # Insert new device
                self.cursor.execute(
                    "INSERT INTO devices (address, name, device_type, last_connected, metadata) VALUES (?, ?, ?, ?, ?)",
                    (address, name, device_type, datetime.now().isoformat(), metadata_json)
                )
                device_id = self.cursor.lastrowid
            
            self.conn.commit()
            logger.info(f"Device {name} ({address}) {'updated' if result else 'added'} with ID {device_id}")
            return device_id
        except sqlite3.Error as e:
            logger.error(f"Error adding device: {str(e)}")
            raise
        finally:
            self._disconnect()
    
    def get_devices(self) -> List[Dict[str, Any]]:
        """
        Get all devices from the database.
        
        Returns:
            List of device dictionaries
        """
        try:
            self._connect()
            self.cursor.execute("SELECT * FROM devices")
            devices = [dict(row) for row in self.cursor.fetchall()]
            
            # Parse metadata JSON
            for device in devices:
                device['metadata'] = json.loads(device['metadata'])
            
            return devices
        except sqlite3.Error as e:
            logger.error(f"Error getting devices: {str(e)}")
            return []
        finally:
            self._disconnect()
    
    def get_device(self, device_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a device by ID.
        
        Args:
            device_id: Device ID
            
        Returns:
            Device dictionary or None if not found
        """
        try:
            self._connect()
            self.cursor.execute("SELECT * FROM devices WHERE id = ?", (device_id,))
            device = self.cursor.fetchone()
            
            if device:
                device_dict = dict(device)
                device_dict['metadata'] = json.loads(device_dict['metadata'])
                return device_dict
            return None
        except sqlite3.Error as e:
            logger.error(f"Error getting device: {str(e)}")
            return None
        finally:
            self._disconnect()
    
    def start_workout(self, device_id: int, workout_type: str) -> int:
        """
        Start a new workout session.
        
        Args:
            device_id: Device ID
            workout_type: Type of workout (bike, rower, etc.)
            
        Returns:
            Workout ID
        """
        try:
            self._connect()
            start_time = datetime.now().isoformat()
            
            self.cursor.execute(
                "INSERT INTO workouts (device_id, start_time, workout_type, summary) VALUES (?, ?, ?, ?)",
                (device_id, start_time, workout_type, '{}')
            )
            workout_id = self.cursor.lastrowid
            
            self.conn.commit()
            logger.info(f"Started workout {workout_id} with device {device_id}")
            return workout_id
        except sqlite3.Error as e:
            logger.error(f"Error starting workout: {str(e)}")
            raise
        finally:
            self._disconnect()
    
    def end_workout(self, workout_id: int, summary: Dict[str, Any] = None, fit_file_path: str = None) -> bool:
        """
        End a workout session.
        
        Args:
            workout_id: Workout ID
            summary: Workout summary data
            fit_file_path: Path to generated FIT file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self._connect()
            
            # Get start time
            self.cursor.execute("SELECT start_time FROM workouts WHERE id = ?", (workout_id,))
            result = self.cursor.fetchone()
            
            if not result:
                logger.error(f"Workout {workout_id} not found")
                return False
            
            start_time = datetime.fromisoformat(result['start_time'])
            end_time = datetime.now()
            duration = int((end_time - start_time).total_seconds())
            
            # Convert summary to JSON string
            summary_json = json.dumps(summary) if summary else '{}'
            
            self.cursor.execute(
                "UPDATE workouts SET end_time = ?, duration = ?, summary = ?, fit_file_path = ? WHERE id = ?",
                (end_time.isoformat(), duration, summary_json, fit_file_path, workout_id)
            )
            
            self.conn.commit()
            logger.info(f"Ended workout {workout_id}, duration: {duration}s")
            return True
        except sqlite3.Error as e:
            logger.error(f"Error ending workout: {str(e)}")
            return False
        finally:
            self._disconnect()
    
    def add_workout_data(self, workout_id: int, timestamp: datetime, data: Dict[str, Any]) -> bool:
        """
        Add data point to a workout session.
        
        Args:
            workout_id: Workout ID
            timestamp: Data timestamp (absolute datetime object)
            data: Workout data
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self._connect()
            
            # Convert data to JSON string
            data_json = json.dumps(data)
            
            # Convert timestamp to ISO 8601 string
            timestamp_iso = timestamp.isoformat()
            
            self.cursor.execute(
                "INSERT INTO workout_data (workout_id, timestamp, data) VALUES (?, ?, ?)",
                (workout_id, timestamp_iso, data_json)
            )
            
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Error adding workout data: {str(e)}")
            return False
        finally:
            self._disconnect()
    
    def get_workout(self, workout_id: int) -> Optional[Dict[str, Any]]:
        """
        Get workout information.
        
        Args:
            workout_id: Workout ID
            
        Returns:
            Workout dictionary or None if not found
        """
        try:
            self._connect()
            self.cursor.execute("SELECT * FROM workouts WHERE id = ?", (workout_id,))
            workout = self.cursor.fetchone()
            
            if workout:
                workout_dict = dict(workout)
                workout_dict['summary'] = json.loads(workout_dict['summary'])
                return workout_dict
            return None
        except sqlite3.Error as e:
            logger.error(f"Error getting workout: {str(e)}")
            return None
        finally:
            self._disconnect()
    
    def get_workout_data(self, workout_id: int) -> List[Dict[str, Any]]:
        """
        Get all data points for a workout.
        
        Args:
            workout_id: Workout ID
            
        Returns:
            List of workout data dictionaries
        """
        try:
            self._connect()
            self.cursor.execute(
                "SELECT * FROM workout_data WHERE workout_id = ? ORDER BY timestamp",
                (workout_id,)
            )
            data_points = []
            
            for row in self.cursor.fetchall():
                data_point = dict(row)
                # Convert timestamp string back to datetime object
                data_point["timestamp"] = datetime.fromisoformat(data_point["timestamp"])
                data_point["data"] = json.loads(data_point["data"])
                data_points.append(data_point)
            
            return data_points
        except sqlite3.Error as e:
            logger.error(f"Error getting workout data: {str(e)}")
            return []
        finally:
            self._disconnect()
    
    def get_workout_data_optimized(self, workout_id: int) -> List[Dict[str, Any]]:
        """
        Get workout data points optimized for FIT conversion.
        
        This method uses a single efficient query that retrieves and formats
        the data points with the exact fields needed for FIT conversion.
        
        Args:
            workout_id: Workout ID
            
        Returns:
            List of workout data dictionaries with optimized structure
        """
        try:
            self._connect()
            
            # Use a single SQL query to extract all needed fields directly
            query = """
            SELECT 
                timestamp,
                json_extract(data, '$.instantaneous_power') as instantaneous_power,
                json_extract(data, '$.heart_rate') as heart_rate,
                json_extract(data, '$.total_distance') as total_distance,
                json_extract(data, '$.instantaneous_cadence') as instantaneous_cadence,
                json_extract(data, '$.instantaneous_speed') as instantaneous_speed,
                json_extract(data, '$.stroke_rate') as stroke_rate
            FROM workout_data
            WHERE workout_id = ?
            ORDER BY timestamp ASC
            """
            
            self.cursor.execute(query, (workout_id,))
            
            data_points = []
            for row in self.cursor.fetchall():
                # Convert timestamp string to datetime object
                timestamp = datetime.fromisoformat(row['timestamp'])
                
                # Create data point with exact structure needed for FIT conversion
                data_point = {
                    'timestamp': timestamp,
                    'instantaneous_power': int(row['instantaneous_power'] or 0),
                    'heart_rate': int(row['heart_rate'] or 0),
                    'total_distance': float(row['total_distance'] or 0),
                    'instantaneous_cadence': int(row['instantaneous_cadence'] or 0),
                    'instantaneous_speed': float(row['instantaneous_speed'] or 0),
                    'stroke_rate': int(row['stroke_rate'] or 0)
                }
                
                data_points.append(data_point)
            
            return data_points
        except sqlite3.Error as e:
            logger.error(f"Error getting optimized workout data: {str(e)}")
            return []
        finally:
            self._disconnect()
    
    def get_workouts(self, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get recent workouts.
        
        Args:
            limit: Maximum number of workouts to return
            offset: Offset for pagination
            
        Returns:
            List of workout dictionaries
        """
        try:
            self._connect()
            # Use LEFT JOIN instead of INNER JOIN to include workouts with missing device data
            self.cursor.execute(
                """
                SELECT w.*, d.name as device_name, d.device_type 
                FROM workouts w
                LEFT JOIN devices d ON w.device_id = d.id
                ORDER BY w.start_time DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset)
            )
            workouts = []
            
            for row in self.cursor.fetchall():
                workout = dict(row)
                # Make sure none of the key values are None to avoid JSON parsing errors
                if workout['summary'] is not None:
                    workout['summary'] = json.loads(workout['summary'])
                else:
                    workout['summary'] = {}
                
                # Add default device info if missing
                if workout.get('device_name') is None:
                    workout['device_name'] = 'Unknown Device'
                if workout.get('device_type') is None:
                    workout['device_type'] = 'unknown'
                    
                workouts.append(workout)
            
            # Log what we found
            logger.info(f"Retrieved {len(workouts)} workouts from database")
            
            return workouts
        except sqlite3.Error as e:
            logger.error(f"Error getting workouts: {str(e)}")
            return []
        finally:
            self._disconnect()
    
    def get_workouts_without_fit_files(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get workouts that don't have associated FIT files.
        
        Args:
            limit: Maximum number of workouts to return (None for all)
            
        Returns:
            List of workout dictionaries
        """
        try:
            self._connect()
            
            query = """
            SELECT w.*, d.name as device_name, d.device_type 
            FROM workouts w
            LEFT JOIN devices d ON w.device_id = d.id
            WHERE (w.fit_file_path IS NULL OR w.fit_file_path = '')
            AND w.end_time IS NOT NULL
            ORDER BY w.start_time DESC
            """
            
            if limit is not None:
                query += f" LIMIT {int(limit)}"
            
            self.cursor.execute(query)
            
            workouts = []
            for row in self.cursor.fetchall():
                workout = dict(row)
                
                # Make sure none of the key values are None to avoid JSON parsing errors
                if workout['summary'] is not None:
                    workout['summary'] = json.loads(workout['summary'])
                else:
                    workout['summary'] = {}
                
                # Add default device info if missing
                if workout.get('device_name') is None:
                    workout['device_name'] = 'Unknown Device'
                if workout.get('device_type') is None:
                    workout['device_type'] = 'unknown'
                    
                workouts.append(workout)
            
            return workouts
        except sqlite3.Error as e:
            logger.error(f"Error getting workouts without FIT files: {str(e)}")
            return []
        finally:
            self._disconnect()
    
    def update_workout_fit_path(self, workout_id: int, fit_file_path: str) -> bool:
        """
        Update the FIT file path for a workout.
        
        Args:
            workout_id: Workout ID
            fit_file_path: Path to the FIT file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self._connect()
            
            self.cursor.execute(
                "UPDATE workouts SET fit_file_path = ? WHERE id = ?",
                (fit_file_path, workout_id)
            )
            
            self.conn.commit()
            logger.info(f"Updated FIT file path for workout {workout_id}: {fit_file_path}")
            return True
        except sqlite3.Error as e:
            logger.error(f"Error updating workout FIT file path: {str(e)}")
            return False
        finally:
            self._disconnect()
    
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
            self._connect()
            
            # Convert value to JSON string
            value_json = json.dumps(value)
            
            self.cursor.execute(
                "INSERT OR REPLACE INTO configuration (key, value) VALUES (?, ?)",
                (key, value_json)
            )
            
            self.conn.commit()
            logger.debug(f"Set config {key} = {value}")
            return True
        except sqlite3.Error as e:
            logger.error(f"Error setting config: {str(e)}")
            return False
        finally:
            self._disconnect()
    
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
            self._connect()
            self.cursor.execute("SELECT value FROM configuration WHERE key = ?", (key,))
            result = self.cursor.fetchone()
            
            if result:
                return json.loads(result['value'])
            return default
        except sqlite3.Error as e:
            logger.error(f"Error getting config: {str(e)}")
            return default
        finally:
            self._disconnect()
    
    def set_user_profile(self, profile: Dict[str, Any]) -> bool:
        """
        Set user profile information.
        
        Args:
            profile: User profile dictionary
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self._connect()
            
            # Check if profile exists
            self.cursor.execute("SELECT COUNT(*) as count FROM user_profile")
            count = self.cursor.fetchone()['count']
            
            if count > 0:
                # Update existing profile
                self.cursor.execute(
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
                self.cursor.execute(
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
            
            self.conn.commit()
            logger.info("User profile updated")
            return True
        except sqlite3.Error as e:
            logger.error(f"Error setting user profile: {str(e)}")
            return False
        finally:
            self._disconnect()
    
    def get_user_profile(self) -> Optional[Dict[str, Any]]:
        """
        Get user profile information.
        
        Returns:
            User profile dictionary or None if not found
        """
        try:
            self._connect()
            self.cursor.execute("SELECT * FROM user_profile LIMIT 1")
            profile = self.cursor.fetchone()
            
            if profile:
                return dict(profile)
            return None
        except sqlite3.Error as e:
            logger.error(f"Error getting user profile: {str(e)}")
            return None
        finally:
            self._disconnect()
    
    def mark_workout_uploaded(self, workout_id: int) -> bool:
        """
        Mark a workout as uploaded to Garmin Connect.
        
        Args:
            workout_id: Workout ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self._connect()
            self.cursor.execute(
                "UPDATE workouts SET uploaded_to_garmin = 1 WHERE id = ?",
                (workout_id,)
            )
            self.conn.commit()
            logger.info(f"Workout {workout_id} marked as uploaded to Garmin Connect")
            return True
        except sqlite3.Error as e:
            logger.error(f"Error marking workout as uploaded: {str(e)}")
            return False
        finally:
            self._disconnect()


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
