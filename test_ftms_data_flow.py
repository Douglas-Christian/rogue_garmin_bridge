#!/usr/bin/env python3
"""
Test script to verify FTMS datapoint storage logic.
This script simulates what happens when datapoints come in from an FTMS device.
"""

import time
import json
import random
from datetime import datetime
from src.data.database import Database
from src.data.workout_manager import WorkoutManager
from src.ftms.ftms_manager import FTMSDeviceManager

def test_ftms_data_flow():
    """Test the flow of data from FTMS to workout manager to database."""
    print("=== Testing FTMS Data Flow ===")
    
    # Set up the components
    db_path = 'src/data/rogue_garmin.db'
    print(f"Connecting to database at {db_path}")
    db = Database(db_path)
    
    # Create WorkoutManager with the database
    workout_manager = WorkoutManager(db_path)
      # Create FTMSDeviceManager with the workout manager
    ftms_manager = FTMSDeviceManager(workout_manager, use_simulator=True)
    
    # Create a test device if it doesn't exist
    devices = db.get_devices()
    if not devices:
        print("No devices found, creating test device")
        device_id = db.add_device(
            address="TEST:FTMS:DEVICE",
            name="Test FTMS Device",
            device_type="bike",
            metadata={"test": True}
        )
    else:
        device_id = devices[0]['id']
        print(f"Using existing device: {devices[0]['name']} (ID: {device_id})")
    
    # Start a workout
    print(f"Starting workout with device ID {device_id}")
    workout_id = workout_manager.start_workout(device_id, "bike")
    
    # Make sure to set the connected device in FTMS manager to simulate a connected device
    ftms_manager.connected_device = {
        "address": "TEST:FTMS:DEVICE",
        "name": "Test FTMS Device",
        "device_type": "bike"
    }
    ftms_manager.device_status = "connected"
    print(f"Started workout with ID {workout_id}")
    
    # Verify workout is active
    print(f"Active workout ID: {workout_manager.active_workout_id}")
    
    # Simulate FTMS data - send 5 data points
    print("\nSimulating FTMS data points:")
    for i in range(5):        # Create a simulated data point
        data = {
            "device_type": "bike",
            "timestamp": datetime.now().isoformat(),
            "instantaneous_speed": random.uniform(15.0, 25.0),  # Changed from "speed" to "instantaneous_speed"
            "power": random.randint(100, 250),
            "cadence": random.randint(70, 100),
            "heart_rate": random.randint(120, 160),
            "distance": i * 50.0,
            "total_energy": i * 5.0,
            "resistance_level": random.randint(1, 10),
            "test_index": i
        }
        
        print(f"  Sending data point {i+1}/5 to FTMS manager")
        
        # Call _handle_ftms_data directly to simulate data coming from FTMS device
        ftms_manager._handle_ftms_data(data)
        
        # Add a small delay between data points
        time.sleep(0.2)
    
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
    success = workout_manager.end_workout()
    print(f"Workout ended: {'SUCCESS' if success else 'FAILED'}")
    
    return workout_id, len(stored_data)

if __name__ == "__main__":
    workout_id, data_count = test_ftms_data_flow()
    print(f"\nTest summary: Added {data_count} data points to workout {workout_id}")
    
    if data_count == 0:
        print("\n=== DIAGNOSTICS ===")
        print("No data points were stored. This could be caused by:")
        print("1. Logic error in FTMS manager data handling")
        print("2. Issue with workout manager's add_data_point method")
        print("3. Database error when adding data points")
        print("\nCheck the logs for more details about the failures.")
