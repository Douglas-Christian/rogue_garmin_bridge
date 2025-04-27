#!/usr/bin/env python3
"""
Database Query Tool for Rogue to Garmin Bridge

This script helps examine the workout data stored in the SQLite database.
It provides detailed information about workouts, data points, and devices.
"""

import sqlite3
import json
import os
import sys
from datetime import datetime
import argparse
from src.utils.logging_config import get_component_logger

# Get logger from centralized logging system
logger = get_component_logger('database_query')

# Determine the database path
DB_PATH = os.path.join(os.path.dirname(__file__), 'rogue_garmin.db')

def connect_to_db():
    """Connect to the SQLite database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row  # This enables column access by name
        return conn
    except sqlite3.Error as e:
        logger.error(f"Database connection error: {e}")
        sys.exit(1)

def format_duration(seconds):
    """Format seconds into a readable duration string."""
    if seconds is None:
        return "In progress"
    
    minutes, sec = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    
    if hours > 0:
        return f"{hours}h {minutes}m {sec}s"
    elif minutes > 0:
        return f"{minutes}m {sec}s"
    else:
        return f"{sec}s"

def list_tables():
    """List all tables in the database."""
    logger.info("Listing database tables")
    conn = connect_to_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    print("\n=== DATABASE TABLES ===")
    for table in tables:
        print(f"- {table['name']}")
    
    conn.close()

def show_workouts(limit=10, include_data=False):
    """Show recent workouts in the database."""
    logger.info(f"Retrieving {limit} recent workouts")
    conn = connect_to_db()
    cursor = conn.cursor()
    
    print("\n=== RECENT WORKOUTS ===")
    cursor.execute("""
        SELECT w.id, w.device_id, d.name as device_name, w.start_time, w.end_time, 
               w.duration, w.workout_type, w.summary, w.fit_file_path, w.uploaded_to_garmin
        FROM workouts w
        LEFT JOIN devices d ON w.device_id = d.id
        ORDER BY w.start_time DESC
        LIMIT ?
    """, (limit,))
    
    workouts = cursor.fetchall()
    
    if not workouts:
        logger.info("No workouts found in the database")
        print("No workouts found in the database.")
        conn.close()
        return
    
    for workout in workouts:
        # Parse the summary JSON
        try:
            summary = json.loads(workout['summary']) if workout['summary'] else {}
        except json.JSONDecodeError:
            summary = {}
        
        # Format the output
        print(f"\nWorkout ID: {workout['id']}")
        print(f"Device: {workout['device_name']} (ID: {workout['device_id']})")
        print(f"Type: {workout['workout_type']}")
        print(f"Started: {workout['start_time']}")
        
        if workout['end_time']:
            print(f"Ended: {workout['end_time']}")
            print(f"Duration: {format_duration(workout['duration'])}")
        else:
            print("Status: In progress")
        
        if workout['fit_file_path']:
            print(f"FIT File: {workout['fit_file_path']}")
            
        if workout['uploaded_to_garmin']:
            print("Uploaded to Garmin: Yes")
        else:
            print("Uploaded to Garmin: No")
        
        # Display summary metrics if they exist
        if summary:
            print("\nSummary Metrics:")
            for key, value in summary.items():
                # Format the output based on the metric type
                if key == 'total_distance':
                    print(f"  Distance: {value:.2f} meters")
                elif key == 'total_calories':
                    print(f"  Calories: {value} kcal")
                elif key.startswith('avg_'):
                    metric_name = key[4:].replace('_', ' ').title()
                    print(f"  Avg {metric_name}: {value}")
                elif key.startswith('max_'):
                    metric_name = key[4:].replace('_', ' ').title()
                    print(f"  Max {metric_name}: {value}")
                elif key == 'estimated_vo2max':
                    print(f"  Estimated VO2max: {value} ml/kg/min")
                else:
                    print(f"  {key.replace('_', ' ').title()}: {value}")
        
        # Display data points if requested
        if include_data:
            print("\nData Points:")
            cursor.execute("""
                SELECT timestamp, data
                FROM workout_data
                WHERE workout_id = ?
                ORDER BY timestamp
                LIMIT 5
            """, (workout['id'],))
            
            data_points = cursor.fetchall()
            
            if data_points:
                for point in data_points:
                    try:
                        data = json.loads(point['data']) if point['data'] else {}
                        power = data.get('instantaneous_power', data.get('power', 'N/A'))
                        heart_rate = data.get('heart_rate', 'N/A')
                        cadence = data.get('instantaneous_cadence', data.get('cadence', data.get('stroke_rate', 'N/A')))
                        distance = data.get('total_distance', 'N/A')
                        calories = data.get('total_calories', data.get('total_energy', 'N/A'))
                        
                        print(f"  Time: {point['timestamp']}s, Power: {power}W, " +
                              f"HR: {heart_rate}, Cadence: {cadence}, " +
                              f"Distance: {distance}m, Calories: {calories}")
                    except json.JSONDecodeError:
                        print(f"  Time: {point['timestamp']}s (Data format error)")
                
                # Get the count of data points
                cursor.execute("""
                    SELECT COUNT(*) as count
                    FROM workout_data
                    WHERE workout_id = ?
                """, (workout['id'],))
                
                count = cursor.fetchone()['count']
                if count > 5:
                    print(f"  ... and {count - 5} more data points")
            else:
                print("  No data points recorded")
        
        print("-" * 50)
    
    conn.close()

def show_devices():
    """Show devices in the database."""
    logger.info("Retrieving devices from database")
    conn = connect_to_db()
    cursor = conn.cursor()
    
    print("\n=== DEVICES ===")
    cursor.execute("""
        SELECT id, address, name, device_type, metadata, last_connected
        FROM devices
        ORDER BY last_connected DESC
    """)
    
    devices = cursor.fetchall()
    
    if not devices:
        logger.info("No devices found in database")
        print("No devices found in the database.")
        conn.close()
        return
    
    for device in devices:
        # Parse the metadata JSON
        try:
            metadata = json.loads(device['metadata']) if device['metadata'] else {}
        except json.JSONDecodeError:
            metadata = {}
        
        # Format the output
        print(f"\nDevice ID: {device['id']}")
        print(f"Name: {device['name']}")
        print(f"Address: {device['address']}")
        print(f"Type: {device['device_type']}")
        print(f"Last Connected: {device['last_connected']}")
        
        if metadata:
            print("Metadata:")
            for key, value in metadata.items():
                print(f"  {key}: {value}")
        
        print("-" * 50)
    
    conn.close()

def show_user_profile():
    """Show user profile from the database."""
    logger.info("Retrieving user profile from database")
    conn = connect_to_db()
    cursor = conn.cursor()
    
    print("\n=== USER PROFILE ===")
    cursor.execute("""
        SELECT id, name, age, gender, weight as weight_kg, height as height_cm, 
               max_heart_rate, resting_heart_rate, garmin_username, garmin_password
        FROM user_profile
        LIMIT 1
    """)
    
    profile = cursor.fetchone()
    
    if not profile:
        logger.info("No user profile found in database")
        print("No user profile found in the database.")
        conn.close()
        return
    
    # Format the output
    print(f"User ID: {profile['id']}")
    print(f"Name: {profile['name']}")
    if profile['age']:
        print(f"Age: {profile['age']}")
    if profile['gender']:
        print(f"Gender: {profile['gender']}")
    if profile['weight_kg']:
        print(f"Weight: {profile['weight_kg']} kg")
    if profile['height_cm']:
        print(f"Height: {profile['height_cm']} cm")
    if profile['max_heart_rate']:
        print(f"Max Heart Rate: {profile['max_heart_rate']} bpm")
    if profile['resting_heart_rate']:
        print(f"Resting Heart Rate: {profile['resting_heart_rate']} bpm")
    if profile['garmin_username']:
        print(f"Garmin Account: {profile['garmin_username']}")
    
    conn.close()

def count_data_points():
    """Count data points for each workout."""
    logger.info("Counting data points for workouts")
    conn = connect_to_db()
    cursor = conn.cursor()
    
    print("\n=== WORKOUT DATA POINT COUNTS ===")
    cursor.execute("""
        SELECT w.id, w.start_time, w.workout_type, COUNT(wd.id) as data_point_count
        FROM workouts w
        LEFT JOIN workout_data wd ON w.id = wd.workout_id
        GROUP BY w.id
        ORDER BY w.start_time DESC
        LIMIT 20
    """)
    
    results = cursor.fetchall()
    
    if not results:
        logger.info("No workouts found in the database")
        print("No workouts found in the database.")
        conn.close()
        return
    
    print("Workout ID | Start Time | Type | Data Points")
    print("-" * 60)
    
    for result in results:
        print(f"{result['id']:10} | {result['start_time'][:19]} | {result['workout_type']:6} | {result['data_point_count']:5}")
    
    conn.close()

def analyze_workout(workout_id):
    """Analyze a specific workout in detail."""
    logger.info(f"Analyzing workout with ID {workout_id}")
    conn = connect_to_db()
    cursor = conn.cursor()
    
    print(f"\n=== DETAILED ANALYSIS OF WORKOUT {workout_id} ===")
    
    # Get workout info
    cursor.execute("""
        SELECT w.id, w.device_id, d.name as device_name, w.start_time, w.end_time, 
               w.duration, w.workout_type, w.summary, w.fit_file_path, w.uploaded_to_garmin
        FROM workouts w
        LEFT JOIN devices d ON w.device_id = d.id
        WHERE w.id = ?
    """, (workout_id,))
    
    workout = cursor.fetchone()
    
    if not workout:
        logger.warning(f"Workout ID {workout_id} not found in database")
        print(f"Workout ID {workout_id} not found.")
        conn.close()
        return
    
    # Parse the summary JSON
    try:
        summary = json.loads(workout['summary']) if workout['summary'] else {}
    except json.JSONDecodeError:
        logger.error(f"Failed to parse workout summary JSON for workout ID {workout_id}")
        summary = {}
    
    # Format the output
    print(f"Workout ID: {workout['id']}")
    print(f"Device: {workout['device_name']} (ID: {workout['device_id']})")
    print(f"Type: {workout['workout_type']}")
    print(f"Started: {workout['start_time']}")
    
    if workout['end_time']:
        print(f"Ended: {workout['end_time']}")
        print(f"Duration: {format_duration(workout['duration'])}")
    else:
        print("Status: In progress")
    
    if workout['fit_file_path']:
        print(f"FIT File: {workout['fit_file_path']}")
    
    if workout['uploaded_to_garmin']:
        print("Uploaded to Garmin: Yes")
    else:
        print("Uploaded to Garmin: No")
    
    # Display summary metrics if they exist
    if summary:
        print("\nSummary Metrics:")
        for key, value in summary.items():
            # Format the output based on the metric type
            if key == 'total_distance':
                print(f"  Distance: {value:.2f} meters")
            elif key == 'total_calories':
                print(f"  Calories: {value} kcal")
            elif key.startswith('avg_'):
                metric_name = key[4:].replace('_', ' ').title()
                print(f"  Avg {metric_name}: {value}")
            elif key.startswith('max_'):
                metric_name = key[4:].replace('_', ' ').title()
                print(f"  Max {metric_name}: {value}")
            elif key == 'estimated_vo2max':
                print(f"  Estimated VO2max: {value} ml/kg/min")
            else:
                print(f"  {key.replace('_', ' ').title()}: {value}")
    
    # Get data points
    cursor.execute("""
        SELECT timestamp, data
        FROM workout_data
        WHERE workout_id = ?
        ORDER BY timestamp
    """, (workout['id'],))
    
    data_points = cursor.fetchall()
    
    if not data_points:
        print("\nNo data points recorded for this workout.")
        conn.close()
        return
    
    # Analyze data points
    print(f"\nData Analysis ({len(data_points)} data points):")
    
    # Extract key metrics
    timestamps = []
    powers = []
    heart_rates = []
    cadences = []
    distances = []
    calories = []
    
    for point in data_points:
        try:
            data = json.loads(point['data']) if point['data'] else {}
            timestamps.append(point['timestamp'])
            
            # Extract metrics with fallbacks for different naming conventions
            powers.append(data.get('instantaneous_power', data.get('power', 0)))
            heart_rates.append(data.get('heart_rate', 0))
            cadences.append(data.get('instantaneous_cadence', data.get('cadence', data.get('stroke_rate', 0))))
            distances.append(data.get('total_distance', 0))
            calories.append(data.get('total_calories', data.get('total_energy', 0)))
        except json.JSONDecodeError:
            continue
    
    # Calculate metrics
    if powers:
        valid_powers = [p for p in powers if p > 0]
        if valid_powers:
            print(f"  Power: Min={min(valid_powers)}W, Max={max(valid_powers)}W, Avg={sum(valid_powers)/len(valid_powers):.1f}W")
            print(f"  Power Distribution: 0-100W: {len([p for p in powers if 0 < p <= 100])}, "
                  f"100-200W: {len([p for p in powers if 100 < p <= 200])}, "
                  f"200-300W: {len([p for p in powers if 200 < p <= 300])}, "
                  f"300W+: {len([p for p in powers if p > 300])}")
    
    if heart_rates:
        valid_hrs = [hr for hr in heart_rates if hr > 0]
        if valid_hrs:
            print(f"  Heart Rate: Min={min(valid_hrs)}bpm, Max={max(valid_hrs)}bpm, Avg={sum(valid_hrs)/len(valid_hrs):.1f}bpm")
    
    if cadences:
        valid_cadences = [c for c in cadences if c > 0]
        if valid_cadences:
            print(f"  Cadence: Min={min(valid_cadences)}, Max={max(valid_cadences)}, Avg={sum(valid_cadences)/len(valid_cadences):.1f}")
    
    if distances:
        # Check if distances are accumulating
        if len(distances) > 1:
            first_distance = distances[0]
            last_distance = distances[-1]
            if last_distance > first_distance:
                print(f"  Distance: Accumulating correctly from {first_distance:.1f}m to {last_distance:.1f}m")
            else:
                print(f"  Distance: NOT accumulating correctly. Start={first_distance:.1f}m, End={last_distance:.1f}m")
            
            # Check for resets
            distance_decreases = [i for i in range(1, len(distances)) if distances[i] < distances[i-1]]
            if distance_decreases:
                print(f"  WARNING: Distance resets detected at data points: {distance_decreases}")
    
    if calories:
        # Check if calories are accumulating
        if len(calories) > 1:
            first_calories = calories[0]
            last_calories = calories[-1]
            if last_calories > first_calories:
                print(f"  Calories: Accumulating correctly from {first_calories} to {last_calories}")
            else:
                print(f"  Calories: NOT accumulating correctly. Start={first_calories}, End={last_calories}")
            
            # Check for resets
            calorie_decreases = [i for i in range(1, len(calories)) if calories[i] < calories[i-1]]
            if calorie_decreases:
                print(f"  WARNING: Calorie resets detected at data points: {calorie_decreases}")
    
    # Data interval analysis
    if len(timestamps) > 1:
        intervals = [timestamps[i] - timestamps[i-1] for i in range(1, len(timestamps))]
        avg_interval = sum(intervals) / len(intervals)
        print(f"  Data Collection Rate: {1/avg_interval:.2f} points/second (every {avg_interval:.2f} seconds)")
    
    # Print some sample data points
    print("\nSample Data Points:")
    for i, idx in enumerate([0, min(10, len(data_points)-1), min(30, len(data_points)-1), len(data_points)-1]):
        if i < 4:  # Only print up to 4 samples
            try:
                point = data_points[idx]
                data = json.loads(point['data']) if point['data'] else {}
                power = data.get('instantaneous_power', data.get('power', 'N/A'))
                heart_rate = data.get('heart_rate', 'N/A')
                cadence = data.get('instantaneous_cadence', data.get('cadence', data.get('stroke_rate', 'N/A')))
                distance = data.get('total_distance', 'N/A')
                calories = data.get('total_calories', data.get('total_energy', 'N/A'))
                
                print(f"  {idx}: Time: {point['timestamp']}s, Power: {power}W, HR: {heart_rate}, "
                      f"Cadence: {cadence}, Distance: {distance}m, Calories: {calories}")
            except (json.JSONDecodeError, IndexError):
                pass
    
    conn.close()

def main():
    """Main function to parse arguments and run queries."""
    parser = argparse.ArgumentParser(description='Query the Rogue to Garmin Bridge database')
    parser.add_argument('--tables', action='store_true', help='List all tables in the database')
    parser.add_argument('--workouts', action='store_true', help='Show recent workouts')
    parser.add_argument('--limit', type=int, default=10, help='Number of workouts to show')
    parser.add_argument('--devices', action='store_true', help='Show devices')
    parser.add_argument('--profile', action='store_true', help='Show user profile')
    parser.add_argument('--counts', action='store_true', help='Count data points for each workout')
    parser.add_argument('--analyze', type=int, help='Analyze a specific workout by ID')
    parser.add_argument('--data', action='store_true', help='Include sample data points with workout listing')
    
    args = parser.parse_args()
    
    # If no arguments, show help
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)
    
    if args.tables:
        list_tables()
    
    if args.workouts:
        show_workouts(args.limit, args.data)
    
    if args.devices:
        show_devices()
    
    if args.profile:
        show_user_profile()
    
    if args.counts:
        count_data_points()
    
    if args.analyze is not None:
        analyze_workout(args.analyze)

if __name__ == "__main__":
    main()