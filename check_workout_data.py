#!/usr/bin/env python3
"""
Database inspection script to check workout data counts.
"""

from src.data.database import Database

def main():
    """Count workouts and data points in the database."""
    # Connect to the database
    db = Database('src/data/rogue_garmin.db')
    
    # Get all workouts
    workouts = db.get_workouts(limit=1000)
    print(f'Total workout records: {len(workouts)}')
    
    # Count data points for each workout
    print('Workout data counts:')
    for workout in workouts[:50]:  # Limit to first 50 workouts
        workout_id = workout['id']
        data_points = db.get_workout_data(workout_id)
        count = len(data_points)
        print(f'  Workout {workout_id}: {count} data points')
        
        # If there are data points, print details of the first one
        if count > 0:
            first_point = data_points[0]
            print(f'    First data point - timestamp: {first_point["timestamp"]}, data keys: {list(first_point["data"].keys())}')

if __name__ == '__main__':
    main()