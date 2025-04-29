#!/usr/bin/env python3
"""
Test script to diagnose and fix workout data storage issues.
"""

import time
import json
import random
from datetime import datetime, timedelta
from src.data.database import Database

def test_add_workout_data():
    """Test adding workout data points to ensure they're stored correctly."""
    print("=== Testing Workout Data Storage ===")
    
    # Connect to database
    db_path = 'src/data/rogue_garmin.db'
    print(f"Connecting to database at {db_path}")
    db = Database(db_path)
    
    # Create a test device if it doesn't exist
    devices = db.get_devices()
    if not devices:
        print("No devices found, creating test device")
        device_id = db.add_device(
            address="TEST:DEVICE:ADDRESS",
            name="Test Device",
            device_type="bike",
            metadata={"test": True}
        )
    else:
        device_id = devices[0]['id']
        print(f"Using existing device: {devices[0]['name']} (ID: {device_id})")
    
    # Create a test workout
    print(f"Creating test workout with device ID {device_id}")
    workout_id = db.start_workout(device_id, "bike")
    print(f"Created test workout with ID {workout_id}")
    
    # Generate and add multiple data points
    print("Adding test data points...")
    start_time = datetime.now()
    
    # Add 10 data points with careful timing to ensure unique timestamps
    for i in range(10):
        # Generate timestamp with microsecond precision
        rel_timestamp = i + (random.randint(0, 999999) / 1000000.0)
        
        # Create test data
        data = {
            "instant_power": random.randint(50, 250),
            "instant_cadence": random.randint(60, 100),
            "heart_rate": random.randint(80, 160),
            "total_distance": i * 10.0,
            "total_energy": i * 5.0,
            "instant_speed": random.uniform(15.0, 25.0),
            "resistance_level": random.randint(1, 10),
            "test_index": i
        }
        
        # Print attempt details
        print(f"  Adding data point {i+1}/10: timestamp={rel_timestamp:.6f}, power={data['instant_power']}")
        
        # Try adding the data point and check success
        success = db.add_workout_data(workout_id, rel_timestamp, data)
        print(f"  -> {'SUCCESS' if success else 'FAILED'}")
        
        # Add a small delay to ensure timestamp uniqueness
        time.sleep(0.1)
    
    # Verify data points were stored
    print("\nVerifying stored data points...")
    stored_data = db.get_workout_data(workout_id)
    print(f"Found {len(stored_data)} data points for workout {workout_id}")
    
    if stored_data:
        print("\nFirst data point details:")
        first_point = stored_data[0]
        print(f"  Timestamp: {first_point['timestamp']}")
        print(f"  Data: {json.dumps(first_point['data'], indent=2)}")
    
    # End the workout
    print("\nEnding test workout")
    success = db.end_workout(workout_id)
    print(f"Workout ended: {'SUCCESS' if success else 'FAILED'}")
    
    return workout_id, len(stored_data)

if __name__ == "__main__":
    workout_id, data_count = test_add_workout_data()
    print(f"\nTest summary: Added {data_count} data points to workout {workout_id}")
    
    if data_count == 0:
        print("\n=== DIAGNOSTICS ===")
        print("No data points were stored. This could be caused by:")
        print("1. SQLite errors when adding data (check logs)")
        print("2. Timestamp collisions (unique constraint violation)")
        print("3. Transaction issues (not committing)")
        print("4. Database locking issues")
        print("\nCheck the logs for more details about the failures.")