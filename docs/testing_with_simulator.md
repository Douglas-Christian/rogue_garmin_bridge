# Testing with the FTMS Simulator

This document provides detailed instructions on how to use the FTMS (Fitness Machine Service) simulator for testing the Rogue Garmin Bridge application without physical hardware.

## Overview

The Rogue Garmin Bridge includes a robust simulation system that can mimic both Rogue Echo Bike and Rower equipment. This simulator generates realistic workout data including power, cadence/stroke rate, heart rate, speed, distance, and calories, allowing you to test all features of the application without connecting to actual physical devices.

## Starting the Application with the Simulator

To enable the simulator:

1. Start the application with the `--use-simulator` flag:
   ```
   python src/web/app.py --use-simulator
   ```

2. Alternatively, you can enable the simulator in the web interface:
   - Navigate to http://localhost:5000/settings
   - Enable the "Use Simulator" option
   - Save the settings
   - Restart the application

## Simulating a Complete Workout

### Using the Web Interface

1. **Connect to a Simulated Device**:
   - Navigate to the "Devices" page
   - Click "Scan for Devices"
   - You should see one or more simulated devices appear:
     * "Rogue Echo Bike (Simulated)"
     * "Rogue Echo Rower (Simulated)"
   - Click "Connect" next to the device you want to simulate

2. **Start a Simulated Workout**:
   - Navigate to the "Workout" page
   - Click "Start Workout"
   - The simulator will begin generating workout data in real-time
   - You'll see metrics updating on the page including:
     * Power (watts)
     * Cadence (for bike) or Stroke Rate (for rower)
     * Heart Rate
     * Speed
     * Distance
     * Calories

3. **Monitor the Simulated Workout**:
   - The charts will display simulated data with realistic variations
   - The workout duration will increase in real-time
   - Accumulated metrics (distance, calories) will increase over time

4. **End the Simulated Workout**:
   - Click "End Workout" when you want to finish testing
   - You'll be redirected to the workout history page
   - The completed workout will appear in your workout history

5. **Process the Simulated Workout Data**:
   - On the History page, click on the workout to view details
   - Click "Generate FIT" to create a FIT file from the simulated data
   - Click "Upload to Garmin" to test the Garmin Connect upload functionality

### Characteristics of Simulated Data

The simulator generates data with the following characteristics:

#### Bike Simulation

- **Cadence**: ~80 RPM with ±5 RPM variation
- **Power**: ~150 watts with ±20 watts variation
- **Speed**: ~25 km/h with ±3 km/h variation
- **Heart Rate**: Varies based on power output (~110-180 BPM)
- **Distance**: Calculated from speed and elapsed time
- **Calories**: Estimated based on power and duration

#### Rower Simulation

- **Stroke Rate**: ~25 SPM with ±3 SPM variation
- **Power**: ~180 watts with ±20 watts variation
- **Heart Rate**: Varies based on power output (~120-190 BPM)
- **Stroke Count**: Calculated from stroke rate and elapsed time
- **Distance**: Approximately 5 meters per second
- **Calories**: Estimated based on power and duration

## Programmatic Testing

For developers who want to test programmatically or create automated tests, the simulator can be used directly in code:

```python
import asyncio
from src.ftms.ftms_simulator import FTMSDeviceSimulator
from src.data.workout_manager import WorkoutManager

async def simulate_workout():
    # Create simulator (choose device type: "bike" or "rower")
    simulator = FTMSDeviceSimulator(device_type="bike")
    
    # Create workout manager with simulator
    workout_manager = WorkoutManager("test.db", simulator)
    
    # Register callbacks to see the data
    def data_callback(data):
        print(f"Data received: {data}")
    simulator.register_data_callback(data_callback)
    
    # Start simulation
    simulator.start_simulation()
    
    # Start workout
    workout_id = workout_manager.start_workout("simulated_device", "bike")
    
    # Let the workout run for a specific duration
    print("Workout running...")
    await asyncio.sleep(60)  # Run for 60 seconds
    
    # End workout
    workout_manager.end_workout(workout_id)
    
    # Stop simulation
    simulator.stop_simulation()
    
    # Retrieve and validate workout data
    workout = workout_manager.get_workout(workout_id)
    workout_data = workout_manager.get_workout_data(workout_id)
    print(f"Workout completed: {workout}")
    print(f"Data points collected: {len(workout_data)}")

# Run the simulation
asyncio.run(simulate_workout())
```

## Advanced Testing Scenarios

The simulator can be used to test various scenarios:

### 1. Testing Different Workout Durations

Simulate workouts of different durations to test data processing and FIT file generation:

- Very short workouts (< 1 minute)
- Medium workouts (10-30 minutes)
- Long workouts (> 60 minutes)

### 2. Testing Data Processing

Generate workouts with specific characteristics to validate calculations:

- Steady-state workouts with consistent power
- Interval workouts with alternating high/low power
- Progressive workouts with gradually increasing intensity

### 3. Testing Error Conditions

Simulate problematic conditions:

- Disconnect the device in the middle of a workout
- Reconnect after a brief disconnection
- Start/stop multiple workouts in succession

## Limitations of the Simulator

The simulator has some limitations to be aware of:

1. It doesn't perfectly replicate all attributes of real FTMS devices
2. The simulated data follows predictable patterns rather than true real-world variability
3. The simulator doesn't account for all possible Bluetooth connection issues

## Troubleshooting Simulator Issues

If you encounter problems with the simulator:

1. **Simulator device doesn't appear**:
   - Confirm the simulator flag was properly set
   - Check application logs for any initialization errors

2. **Simulator data doesn't update**:
   - The simulation loop may have crashed
   - Restart the application with the simulator flag

3. **Data looks unrealistic**:
   - The simulator is designed to provide reasonable but simulated values
   - Adjust the code in `ftms_simulator.py` if you need different data patterns