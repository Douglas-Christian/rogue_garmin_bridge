#!/usr/bin/env python3
"""
Script to check workout data in the database.
"""

import sys
import json
import traceback
from datetime import datetime
from src.data.database import Database

def analyze_workouts():
    """Analyze workouts in the database."""
    try:
        print("=== Analyzing Workouts in Database ===")
        
        # Connect to database
        db_path = 'src/data/rogue_garmin.db'
        print(f"Connecting to database at {db_path}")
        db = Database(db_path)
        
        # Get all workouts
        workouts = db.get_workouts()
        print(f"Total workouts in database: {len(workouts)}")
        
        # Filter for bike workouts
        bike_workouts = [w for w in workouts if w.get('device_type') == 'bike']
        print(f"Echo bike workouts: {len(bike_workouts)}")
        
        # Analyze each bike workout
        for workout in bike_workouts:
            workout_id = workout['id']
            start_time = workout['start_time']
            device_type = workout.get('device_type', 'unknown')
            
            # Get data points for this workout
            data_points = db.get_workout_data(workout_id)
            
            print(f"\nWorkout {workout_id}:")
            print(f"  Start time: {start_time}")
            print(f"  Device type: {device_type}")
            print(f"  Data points: {len(data_points)}")
            
            if data_points:
                print(f"  First data point timestamp: {data_points[0]['timestamp']}")
                print(f"  Last data point timestamp: {data_points[-1]['timestamp']}")
                
                # Show some sample data
                if len(data_points) > 0:
                    print("\n  Sample data point:")
                    sample = data_points[0]
                    data = sample['data']
                    if isinstance(data, str):
                        try:
                            data = json.loads(data)
                        except json.JSONDecodeError:
                            print("  (Error decoding JSON data)")
                    
                    for key, value in data.items():
                        print(f"    {key}: {value}")
            else:
                print("  No data points found!")
    except Exception as e:
        print(f"Error analyzing workouts: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    analyze_workouts()
