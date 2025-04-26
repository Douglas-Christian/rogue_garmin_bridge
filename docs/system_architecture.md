# Rogue to Garmin Bridge System Architecture

## Overview

The Rogue to Garmin Bridge is a Python application designed to run on a Raspberry Pi 2. It connects to Rogue Echo Bike and Rower equipment via Bluetooth Low Energy (BLE) using the FTMS (Fitness Machine Service) standard, collects workout metrics, and converts them to the Garmin FIT file format for upload to Garmin Connect. The application includes a web-based user interface for configuration, monitoring, and managing workout data.

## System Components

The system consists of the following major components:

1. **FTMS Connectivity Module**: Handles Bluetooth connection to Rogue Echo equipment
2. **Data Collection and Processing Module**: Collects and processes workout metrics
3. **FIT File Conversion Module**: Converts workout data to Garmin FIT format
4. **Web Frontend Interface**: Provides user interface for the application
5. **Database**: Stores configuration and workout data

## Component Details

### 1. FTMS Connectivity Module

**Purpose**: Establish and maintain Bluetooth connections to Rogue Echo Bike and Rower equipment.

**Key Features**:
- Bluetooth device discovery and connection
- FTMS protocol implementation
- Connection status monitoring
- Automatic reconnection handling

**Technologies**:
- Python 3.x
- Bleak library for cross-platform BLE connectivity
- pycycling library for FTMS protocol support

**Interfaces**:
- Provides real-time FTMS data to the Data Collection module
- Reports connection status to the Web Frontend

### 2. Data Collection and Processing Module

**Purpose**: Collect, process, and store workout metrics from the FTMS Connectivity Module.

**Key Features**:
- Real-time data collection from FTMS devices
- Data validation and processing
- Workout session management (start, pause, stop)
- Temporary data storage during workouts
- Persistent storage of completed workouts

**Technologies**:
- Python 3.x
- SQLite for local data storage

**Interfaces**:
- Receives data from FTMS Connectivity Module
- Provides processed data to FIT File Conversion Module
- Stores and retrieves data from the Database
- Provides workout data to Web Frontend

### 3. FIT File Conversion Module

**Purpose**: Convert processed workout data to Garmin FIT file format.

**Key Features**:
- Creation of FIT files according to Garmin specifications
- Support for required FIT message types (File ID, Activity, Session, Lap, Record)
- Inclusion of necessary data fields for VO2 max calculations
- FIT file validation

**Technologies**:
- Python 3.x
- fit-tool library for FIT file creation and validation
- python-fitparse library for FIT file parsing (if needed)

**Interfaces**:
- Receives processed workout data from Data Collection Module
- Provides FIT files to Web Frontend for download
- Optionally uploads FIT files directly to Garmin Connect

### 4. Web Frontend Interface

**Purpose**: Provide a user-friendly interface for configuring the system, monitoring connections, viewing workout data, and managing FIT files.

**Key Features**:
- Device connection status and management
- Real-time workout data visualization
- Workout history and statistics
- FIT file download and Garmin Connect upload options
- System configuration

**Technologies**:
- Flask (Python web framework)
- HTML, CSS, JavaScript
- Bootstrap for responsive design
- Chart.js for data visualization

**Interfaces**:
- Displays data from all other modules
- Provides user controls for system functions
- Handles user authentication (if needed)

### 5. Database

**Purpose**: Store system configuration, device information, and workout data.

**Key Features**:
- Configuration storage
- Device information storage
- Workout session storage
- User preferences (if applicable)

**Technologies**:
- SQLite (lightweight, file-based database)

**Interfaces**:
- Used by all other modules for data persistence

## Data Flow

1. **Device Discovery and Connection**:
   - Web Frontend initiates device discovery
   - FTMS Connectivity Module discovers and connects to Rogue Echo equipment
   - Connection status reported to Web Frontend

2. **Workout Data Collection**:
   - FTMS Connectivity Module receives real-time data from Rogue Echo equipment
   - Data Collection Module processes and stores the data
   - Real-time metrics displayed on Web Frontend

3. **FIT File Creation**:
   - User initiates FIT file creation via Web Frontend
   - Data Collection Module provides workout data to FIT File Conversion Module
   - FIT File Conversion Module creates a valid FIT file
   - FIT file made available for download via Web Frontend

4. **Garmin Connect Upload**:
   - User initiates upload via Web Frontend
   - FIT file uploaded to Garmin Connect (either automatically or manually)
   - Upload status reported to Web Frontend

## Deployment Architecture

The application will be deployed on a Raspberry Pi 2 with the following components:

1. **Hardware**:
   - Raspberry Pi 2
   - Bluetooth adapter (built-in or external if needed)
   - Power supply
   - Optional: Case, display

2. **Software Environment**:
   - Raspberry Pi OS (Lite or Desktop)
   - Python 3.x
   - Required Python libraries
   - Web server (Flask development server or production-ready server like Gunicorn)

3. **Network**:
   - Local network connectivity for web interface access
   - Internet connectivity for Garmin Connect uploads

## Security Considerations

1. **Local Network Security**:
   - Web interface accessible only on local network by default
   - Optional user authentication for web interface

2. **Data Privacy**:
   - Workout data stored locally on Raspberry Pi
   - No data shared with third parties except when explicitly uploading to Garmin Connect
   - Garmin Connect credentials stored securely (if automatic upload is implemented)

## Future Expansion Possibilities

1. **Additional Equipment Support**:
   - Support for other FTMS-compatible fitness equipment

2. **Enhanced Analytics**:
   - Advanced workout analysis and performance tracking

3. **Multi-User Support**:
   - Profiles for multiple users with separate workout history and Garmin accounts

4. **Integration with Other Platforms**:
   - Support for other fitness platforms beyond Garmin Connect

5. **Mobile Application**:
   - Companion mobile app for remote monitoring and control
