# Rogue to Garmin Bridge Data Flow Diagram

## Overview

This document describes the data flow between components in the Rogue to Garmin Bridge application. The data flow is organized by the main processes that occur during the application's operation.

## 1. Device Discovery and Connection

```
+----------------+         +-------------------+         +----------------+
|                |  Scan   |                   | Device  |                |
| Web Frontend   +-------->+ FTMS Connectivity | List    | Web Frontend   |
|                |         | Module            +-------->+                |
+----------------+         +-------------------+         +----------------+
                                    |
                                    | Connect
                                    v
                           +-------------------+
                           |                   |
                           | Rogue Echo Device |
                           |                   |
                           +-------------------+
                                    |
                                    | Status
                                    v
+----------------+         +-------------------+
|                | Status  |                   |
| Web Frontend   <---------+ FTMS Connectivity |
|                |         | Module            |
+----------------+         +-------------------+
```

## 2. Workout Data Collection

```
+-------------------+         +-------------------+
|                   | FTMS    |                   |
| Rogue Echo Device | Data    | FTMS Connectivity |
|                   +-------->+ Module            |
+-------------------+         +-------------------+
                                      |
                                      | Raw Data
                                      v
                              +-------------------+
                              |                   |
                              | Data Collection   |
                              | Module            |
                              +-------------------+
                                      |
                      +---------------+---------------+
                      |               |               |
                      v               v               v
            +-------------------+ +----------+ +----------------+
            |                   | |          | |                |
            | Database          | | Real-time| | Web Frontend   |
            | (Workout Storage) | | Display  | | (Visualization)|
            +-------------------+ +----------+ +----------------+
```

## 3. FIT File Creation

```
+----------------+         +-------------------+
|                | Request |                   |
| Web Frontend   +-------->+ FIT Conversion    |
|                |         | Module            |
+----------------+         +-------------------+
                                    |
                                    | Request Data
                                    v
                           +-------------------+
                           |                   |
                           | Data Collection   |
                           | Module            |
                           +-------------------+
                                    |
                                    | Workout Data
                                    v
                           +-------------------+
                           |                   |
                           | FIT Conversion    |
                           | Module            |
                           +-------------------+
                                    |
                                    | FIT File
                                    v
                           +-------------------+
                           |                   |
                           | Web Frontend      |
                           | (Download)        |
                           +-------------------+
```

## 4. Garmin Connect Upload

```
+----------------+         +-------------------+
|                | Upload  |                   |
| Web Frontend   +-------->+ FIT Conversion    |
| (User Action)  |         | Module            |
+----------------+         +-------------------+
                                    |
                                    | FIT File
                                    v
                           +-------------------+
                           |                   |
                           | Garmin Connect    |
                           | API               |
                           +-------------------+
                                    |
                                    | Status
                                    v
                           +-------------------+
                           |                   |
                           | Web Frontend      |
                           | (Status Display)  |
                           +-------------------+
```

## 5. Configuration Management

```
+----------------+         +-------------------+
|                | Update  |                   |
| Web Frontend   +-------->+ Configuration     |
| (User Input)   |         | Manager           |
+----------------+         +-------------------+
                                    |
                                    | Store
                                    v
                           +-------------------+
                           |                   |
                           | Database          |
                           | (Config Storage)  |
                           +-------------------+
                                    |
                                    | Load
                                    v
                           +-------------------+
                           |                   |
                           | All Application   |
                           | Modules           |
                           +-------------------+
```

## Data Types

### FTMS Data (from Rogue Echo devices)
- Power (watts)
- Cadence (RPM)
- Speed
- Distance
- Heart rate (if available)
- Resistance level
- Elapsed time
- Calories burned
- Equipment-specific metrics

### Processed Workout Data
- Timestamp
- All FTMS metrics
- Calculated metrics (e.g., pace, average power)
- Session metadata (start time, duration, equipment type)

### FIT File Data
- File ID message
- Activity message
- Session message
- Lap messages
- Record messages (containing timestamp, position, heart rate, cadence, power, etc.)
- Device info messages

### Configuration Data
- Bluetooth device preferences
- User profile information (weight, height, age, gender)
- Garmin Connect credentials (if automatic upload is enabled)
- Display preferences
- Default settings
