#!/usr/bin/env python3
"""
Convert Workout to FIT Utility

This script allows you to select a workout from the database and convert it to a FIT file.
It's useful for manual conversions or troubleshooting FIT file generation.
"""

import os
import sys
import json
import sqlite3
from datetime import datetime
from typing import Dict, List, Any, Optional

# Add the project root to the path so we can import project modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import project modules
from src.data.database import Database
from src.fit.fit_converter import FITConverter

def get_workouts(db_path: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Get recent workouts from the database."""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get workouts with device info
        cursor.execute(
            """
            SELECT w.*, d.name as device_name, d.device_type 
            FROM workouts w
            LEFT JOIN devices d ON w.device_id = d.id
            ORDER BY w.start_time DESC
            LIMIT ?
            """,
            (limit,)
        )
        
        workouts = []
        for row in cursor.fetchall():
            workout = dict(row)
            
            # Parse summary if it's a string
            if 'summary' in workout and workout['summary'] and isinstance(workout['summary'], str):
                try:
                    workout['summary'] = json.loads(workout['summary'])
                except json.JSONDecodeError:
                    workout['summary'] = {}
            
            # Add device info defaults if missing
            if workout.get('device_name') is None:
                workout['device_name'] = 'Unknown Device'
            if workout.get('device_type') is None:
                workout['device_type'] = 'unknown'
                
            workouts.append(workout)
            
        return workouts
    except sqlite3.Error as e:
        print(f"Error getting workouts: {str(e)}")
        return []
    finally:
        if conn:
            conn.close()

def get_workout_data(db_path: str, workout_id: int) -> List[Dict[str, Any]]:
    """Get all data points for a workout."""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT timestamp, data 
            FROM workout_data 
            WHERE workout_id = ? 
            ORDER BY timestamp
            """, 
            (workout_id,)
        )
        
        data_points = []
        for row in cursor.fetchall():
            data_point = {}
            
            # Convert timestamp string to datetime object
            data_point["timestamp"] = datetime.fromisoformat(row['timestamp'])
            
            # Parse data JSON
            if row['data']:
                try:
                    data_point["data"] = json.loads(row['data'])
                except json.JSONDecodeError:
                    data_point["data"] = {}
            else:
                data_point["data"] = {}
                
            data_points.append(data_point)
            
        return data_points
    except sqlite3.Error as e:
        print(f"Error getting workout data: {str(e)}")
        return []
    finally:
        if conn:
            conn.close()

def get_user_profile() -> Optional[Dict[str, Any]]:
    """Get user profile from user_profile.json."""
    profile_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'user_profile.json')
    
    if os.path.exists(profile_path):
        try:
            with open(profile_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading user profile: {str(e)}")
    
    return None

def prepare_workout_data(workout: Dict[str, Any], workout_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Prepare workout data for FIT conversion."""
    # Extract summary metrics from workout
    summary = workout.get('summary', {})
    
    # Create processed data structure
    processed_data = {
        'workout_type': workout.get('workout_type', 'bike'),
        'start_time': workout.get('start_time'),
        'total_duration': workout.get('duration', 0),
        'data_series': {
            'timestamps': [],
            'absolute_timestamps': [],
            'powers': [],
            'cadences': [],
            'heart_rates': [],
            'speeds': [],
            'distances': [],
            'stroke_rates': []  # For rowers
        }
    }
    
    # Add summary metrics
    processed_data.update({
        'total_distance': summary.get('total_distance', 0),
        'total_calories': summary.get('total_calories', 0),
        'avg_power': summary.get('avg_power', 0),
        'max_power': summary.get('max_power', 0),
        'normalized_power': summary.get('normalized_power', 0),
        'avg_heart_rate': summary.get('avg_heart_rate', 0),
        'max_heart_rate': summary.get('max_heart_rate', 0),
        'avg_speed': summary.get('avg_speed', 0),
        'max_speed': summary.get('max_speed', 0)
    })
    
    # Add workout-type specific metrics
    if processed_data['workout_type'] == 'bike':
        processed_data.update({
            'avg_cadence': summary.get('avg_cadence', 0),
            'max_cadence': summary.get('max_cadence', 0)
        })
    elif processed_data['workout_type'] == 'rower':
        processed_data.update({
            'avg_stroke_rate': summary.get('avg_stroke_rate', 0),
            'max_stroke_rate': summary.get('max_stroke_rate', 0),
            'total_strokes': summary.get('total_strokes', 0)
        })
    
    # Process workout data points
    start_time = None
    if workout.get('start_time'):
        try:
            start_time = datetime.fromisoformat(workout['start_time'])
        except (ValueError, TypeError):
            start_time = None
    
    # Extract data series
    for point in workout_data:
        # Add absolute timestamp
        timestamp = point.get('timestamp')
        if timestamp:
            processed_data['data_series']['absolute_timestamps'].append(timestamp)
            
            # Calculate relative timestamp (seconds from start)
            if start_time:
                relative_seconds = (timestamp - start_time).total_seconds()
                processed_data['data_series']['timestamps'].append(relative_seconds)
            else:
                # If no start time, use index as relative timestamp
                processed_data['data_series']['timestamps'].append(len(processed_data['data_series']['timestamps']))
        
        # Extract data metrics
        data = point.get('data', {})
        
        # Extract power
        power = data.get('instant_power', data.get('instantaneous_power', data.get('power', 0)))
        processed_data['data_series']['powers'].append(power)
        
        # Extract cadence or stroke rate
        if processed_data['workout_type'] == 'bike':
            cadence = data.get('instant_cadence', data.get('instantaneous_cadence', data.get('cadence', 0)))
            processed_data['data_series']['cadences'].append(cadence)
        elif processed_data['workout_type'] == 'rower':
            stroke_rate = data.get('stroke_rate', 0)
            processed_data['data_series']['cadences'].append(stroke_rate)
            processed_data['data_series']['stroke_rates'].append(stroke_rate)
        
        # Extract heart rate
        heart_rate = data.get('heart_rate', 0)
        processed_data['data_series']['heart_rates'].append(heart_rate)
        
        # Extract speed
        speed = data.get('instant_speed', data.get('instantaneous_speed', data.get('speed', 0)))
        processed_data['data_series']['speeds'].append(speed)
        
        # Extract distance
        distance = data.get('total_distance', data.get('distance', 0))
        processed_data['data_series']['distances'].append(distance)
    
    return processed_data

def display_workouts(workouts: List[Dict[str, Any]]) -> None:
    """Display a list of workouts."""
    print("\n=== Available Workouts ===")
    print(f"{'ID':<4} {'Date':<20} {'Type':<10} {'Duration':<10} {'Distance':<10} {'Device':<20}")
    print("-" * 80)
    
    for workout in workouts:
        # Format start time
        start_time = workout.get('start_time', '')
        if start_time:
            try:
                start_time = datetime.fromisoformat(start_time).strftime('%Y-%m-%d %H:%M:%S')
            except (ValueError, TypeError):
                pass
            
        # Format duration
        duration = workout.get('duration', 0)
        if duration:
            hours = int(duration / 3600)
            minutes = int((duration % 3600) / 60)
            seconds = int(duration % 60)
            duration_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            duration_str = "00:00:00"
            
        # Format distance
        summary = workout.get('summary', {})
        if isinstance(summary, str):
            try:
                summary = json.loads(summary)
            except json.JSONDecodeError:
                summary = {}
                
        distance = summary.get('total_distance', 0)
        distance_str = f"{distance:.1f} m"
        
        # Format workout type
        workout_type = workout.get('workout_type', 'unknown')
        workout_type = workout_type.capitalize()
        
        # Display workout info
        print(f"{workout.get('id', ''):<4} {start_time:<20} {workout_type:<10} {duration_str:<10} {distance_str:<10} {workout.get('device_name', 'Unknown'):<20}")

def main() -> None:
    """Main function."""
    # Get database path
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src', 'data', 'rogue_garmin.db')
    if not os.path.exists(db_path):
        print(f"Error: Database file not found at {db_path}")
        sys.exit(1)
    
    print(f"Using database: {db_path}")
    
    # Get recent workouts
    workouts = get_workouts(db_path)
    
    if not workouts:
        print("No workouts found in database")
        sys.exit(1)
    
    # Display workouts
    display_workouts(workouts)
    
    # Prompt for workout ID
    try:
        workout_id = int(input("\nEnter workout ID to convert to FIT: "))
    except ValueError:
        print("Invalid input. Please enter a numeric workout ID.")
        sys.exit(1)
    
    # Find selected workout
    selected_workout = None
    for workout in workouts:
        if workout.get('id') == workout_id:
            selected_workout = workout
            break
    
    if not selected_workout:
        print(f"Workout with ID {workout_id} not found.")
        sys.exit(1)
    
    # Get workout data
    workout_data = get_workout_data(db_path, workout_id)
    
    if not workout_data:
        print(f"No data points found for workout {workout_id}")
        sys.exit(1)
    
    print(f"Found {len(workout_data)} data points for workout {workout_id}")
    
    # Get user profile
    user_profile = get_user_profile()
    
    # Prepare workout data for FIT conversion
    processed_data = prepare_workout_data(selected_workout, workout_data)
    
    # Define output directory for FIT files
    fit_output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fit_files')
    os.makedirs(fit_output_dir, exist_ok=True)
    
    # Create FIT converter
    converter = FITConverter(fit_output_dir)
    
    # Convert workout to FIT
    print(f"Converting workout {workout_id} to FIT...")
    fit_file_path = converter.convert_workout(processed_data, user_profile)
    
    if fit_file_path:
        print(f"Successfully created FIT file: {fit_file_path}")
        
        # Update workout with FIT file path
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE workouts SET fit_file_path = ? WHERE id = ?",
                (fit_file_path, workout_id)
            )
            conn.commit()
            conn.close()
            print(f"Updated workout {workout_id} with FIT file path")
        except sqlite3.Error as e:
            print(f"Error updating workout with FIT file path: {str(e)}")
    else:
        print(f"Failed to create FIT file for workout {workout_id}")

if __name__ == "__main__":
    main()