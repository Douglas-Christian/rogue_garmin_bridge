# Rogue Garmin Bridge - Data Flow Documentation

## Overview

This document describes the flow of data through the Rogue Garmin Bridge application, covering both real device and simulator modes. It outlines the expected behavior at each stage of the data flow and serves as a reference for understanding and modifying the system.

## System Components

The Rogue Garmin Bridge consists of the following key components:

1. **FTMS Module**:
   - `ftms_manager.py`: Manages connections to fitness equipment
   - `ftms_connector.py`: Handles BLE connections for real devices
   - `ftms_simulator.py`: Provides simulated device data

2. **Data Module**:
   - `workout_manager.py`: Manages workout sessions and data processing
   - `database.py`: Handles data storage in SQLite

3. **Web Interface**:
   - `app.py`: Flask web application providing the UI
   - Web templates and static assets

4. **FIT Export**:
   - `fit_converter.py`: Converts workout data to Garmin FIT format
   - `garmin_uploader.py`: Uploads FIT files to Garmin Connect

## Core Data Flow

### 1. Device Connection Flow

**Normal Device Mode:**
1. User launches application via web interface
2. App requests available FTMS devices through `ftms_manager.discover_devices()`
3. Real BLE devices are discovered via `ftms_connector.discover_devices()`
4. User selects a device in the web interface
5. Connection established via `ftms_manager.connect(device_address)`
6. Connected device notifications begin streaming data automatically

**Simulator Mode:**
1. User launches application via web interface with simulator enabled
2. Simulated devices are created in `ftms_manager.discover_devices()`
3. User selects a simulated device in the web interface
4. Connection established via `ftms_manager.connect(device_address)`
5. Simulator starts running but doesn't send workout data yet
6. Simulator awaits explicit workout start command

### 2. Workout Data Generation Flow

**Normal Device Mode:**
1. User starts a workout in the web interface
2. `workout_manager.start_workout()` is called
3. A new workout record is created in the database
4. Real device continues sending data at its own rate (typically 1Hz)
5. Data flows from device → ftms_connector → ftms_manager → workout_manager → database

**Simulator Mode:**
1. User starts a workout in the web interface
2. `workout_manager.start_workout()` is called
3. Workout manager notifies FTMS manager via `notify_workout_start()`
4. FTMS manager notifies the active simulator via `start_workout()`
5. Simulator sets `workout_active = True` and begins generating data at 1Hz
6. Data flows from simulator → ftms_manager → workout_manager → database
7. Each data point has a unique timestamp with microsecond precision to prevent collisions

### 3. Data Processing Flow

In both modes, once data reaches the workout manager:

1. Raw data arrives at `workout_manager._handle_ftms_data()`
2. Data is validated and enhanced:
   - Timestamps are normalized and made unique with microsecond precision
   - Missing fields are filled with defaults or calculated values
   - Data is copied to prevent modification issues
3. Data is stored in the database via `database.add_workout_data()`
4. Summary metrics are updated in memory via `_update_summary_metrics()`
5. UI is notified of new data via registered callbacks

### 4. Workout End Flow

**Normal Device Mode:**
1. User ends the workout in the web interface
2. `workout_manager.end_workout()` is called
3. Final summary metrics are calculated
4. Workout is marked as complete in the database
5. Real device continues streaming data but it's no longer stored

**Simulator Mode:**
1. User ends the workout in the web interface
2. `workout_manager.end_workout()` is called
3. Workout manager notifies FTMS manager via `notify_workout_end()`
4. FTMS manager finds the active simulator and calls `end_workout()`
5. Simulator sets `workout_active = False` to stop data generation
6. A final data point is generated and sent to mark the workout completion
7. Final summary metrics are calculated
8. Workout is marked as complete in the database

## Critical Path Analysis

### Critical Path: Start Workout → Data Flow → End Workout

The most critical data flow path is:

1. **Web UI** → `/api/start_workout` endpoint in `app.py`
2. **App** → `workout_manager.start_workout()`
3. **Workout Manager** → `ftms_manager.notify_workout_start()` (simulator mode)
4. **FTMS Manager** → `simulator.start_workout()`
5. **Simulator** → Begins generating data at 1Hz while `workout_active = True`
6. **Simulator** → `ftms_manager._handle_data()` receives simulated data
7. **FTMS Manager** → `workout_manager._handle_ftms_data()` processes data
8. **Workout Manager** → `database.add_workout_data()` stores data
9. **Web UI** → `/api/end_workout` endpoint in `app.py`
10. **App** → `workout_manager.end_workout()`
11. **Workout Manager** → `ftms_manager.notify_workout_end()` (simulator mode)
12. **FTMS Manager** → `simulator.end_workout()`
13. **Simulator** → Sets `workout_active = False`, stops generating data

### Known Issues and Solutions



## Expected Behaviors

### Simulator Mode

1. When the app starts in simulator mode:
   - Simulated devices should appear in the device list
   - No data should be generated until a workout is started

2. When a workout starts:
   - Simulator should begin generating data at 1Hz (one point per second)
   - Each data point should have unique timestamps with microsecond precision
   - Web UI should update with the latest metrics

3. When a workout ends:
   - Simulator should stop generating data immediately
   - A final data point should be sent to complete the workout
   - Database should contain a complete set of data points for the workout's duration

4. When the app is restarted:
   - Previous workout data should be available in the history
   - Simulator state should reset properly

### Normal Device Mode

1. When the app starts with normal devices:
   - Real FTMS-compatible devices should be discovered via BLE
   - Connection should be established when a device is selected

2. When a workout starts:
   - Data should flow from the real device at its native rate
   - Each data point should be stored with unique timestamps

3. When a workout ends:
   - The workout should be marked as complete in the database
   - Data should still flow from the device if it's still sending, but not be stored

## Debugging Flow Issues

When diagnosing data flow issues:

1. Check logs with `[DATA_FLOW]` markers to trace data through the system
2. Verify the simulator state flags: `running` and `workout_active`
3. Check database for timestamp uniqueness and data point completeness
4. Use the database inspector notebook to visualize workout data and verify completeness