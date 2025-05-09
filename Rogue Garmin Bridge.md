# Rogue Garmin Bridge

A Python application that bridges Rogue fitness equipment (Echo Bike and Rower) to Garmin Connect, allowing seamless tracking and analysis of your workouts.

## Overview

Rogue Garmin Bridge connects to Rogue Echo Bike and Rower equipment (Rower support enhanced with `pyftms`) via Bluetooth Low Energy (BLE) using the Fitness Machine Service (FTMS) standard. It collects workout metrics, processes the data, and converts it to the Garmin FIT file format for manual upload to Garmin Connect. The application includes a web-based user interface for configuration, monitoring, and managing workout data.

![Rogue Garmin Bridge UI](https://private-us-east-1.manuscdn.com/sessionFile/V9jWlI9Latcf2GVTTp7FDJ/sandbox/2fvioG0Sd15fI25fgqHBqB-images_1746789771103_na1fn_L2hvbWUvdWJ1bnR1L3JvZ3VlX2dhcm1pbl9icmlkZ2VfcHlmdG1zX2ltcGwvZG9jcy9pbWFnZXMvdWlfc2NyZWVuc2hvdA.png?Policy=eyJTdGF0ZW1lbnQiOlt7IlJlc291cmNlIjoiaHR0cHM6Ly9wcml2YXRlLXVzLWVhc3QtMS5tYW51c2Nkbi5jb20vc2Vzc2lvbkZpbGUvVjlqV2xJOUxhdGNmMkdWVFRwN0ZESi9zYW5kYm94LzJmdmlvRzBTZDE1ZkkyNWZncUhCcUItaW1hZ2VzXzE3NDY3ODk3NzExMDNfbmExZm5fTDJodmJXVXZkV0oxYm5SMUwzSnZaM1ZsWDJkaGNtMXBibDlpY21sa1oyVmZjSGxtZEcxelgybHRjR3d2Wkc5amN5OXBiV0ZuWlhNdmRXbGZjMk55WldWdWMyaHZkQS5wbmciLCJDb25kaXRpb24iOnsiRGF0ZUxlc3NUaGFuIjp7IkFXUzpFcG9jaFRpbWUiOjE3NjcyMjU2MDB9fX1dfQ__&Key-Pair-Id=K2HSFNDJXOU9YS&Signature=tLxrBnjd9eIl8zNm6YVdY2QkrtCLuDtYwwQ15XS5DgDEJ6q6tu5O8-4q~M88uWGyREp6JPlnyU-~07C6yPOuAwREGTnGuProHYToKl7tkUtrfwzhtv26MSTVpj4vcEdzK~sMERgs-eVN1cC7poQllmxPJzKT0TLrfxodqtsZPnZdhwZjEIZwzcFDzMgOTOfI~m-ko6N2jN3rJcUdF-goEIcUcDaGwLvFiUgAotBVSdKfBU1K89SgdqT2UFXWnSXg5bDdQ8G4gEWQ8mfJbvjxb6hzA5TCvucHwv0j1Db6ngD0lXFQypOpTtMwcV3D2UCsbdeEume2KCUnolwze7LB~Q__)

## Features

- **FTMS Bluetooth Connectivity**: Connect to Rogue Echo Bike and Rower equipment via BLE using `pyftms` for robust FTMS communication.
- **Real-time Workout Tracking**: Monitor power, heart rate, cadence/stroke rate, speed, distance, and calories in real-time.
- **Workout History**: View past workout details with performance metrics and charts.
- **FIT File Generation**: Convert workout data to Garmin FIT format with proper device identification for manual upload.
- **Training Load Calculation**: Generated FIT files correctly report training load in Garmin Connect.
- **Speed Data Analysis**: Improved speed calculations and display in workout history.
- **Web Interface**: User-friendly interface for monitoring, configuring, and managing workouts.
- **FTMS Device Simulator**: Test functionality without physical hardware (development mode).

## System Requirements

- Python 3.12+ (due to `pyftms` dependency)
- Bluetooth adapter with BLE support
- Operating System: Windows, macOS, or Linux (Raspberry Pi compatible)
- Web browser for accessing the user interface

## Installation

### Prerequisites

- Python 3.12 or higher
- pip (Python package installer)
- Git (optional, for cloning the repository)

### Installation Steps

1. Clone the repository (or download and extract the ZIP file):
   ```
   git clone https://github.com/Douglas-Christian/rogue_garmin_bridge.git
   cd rogue_garmin_bridge
   ```

2. Create and activate a virtual environment (optional but recommended):
   ```
   python3.12 -m venv .venv
   # On Windows:
   .venv\Scripts\activate
   # On macOS/Linux:
   source .venv/bin/activate
   ```

3. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

### Starting the Application

1. Navigate to the project directory:
   ```
   cd rogue_garmin_bridge
   ```

2. Start the web application (ensure you are using Python 3.12):
   ```
   python3.12 src/web/app.py
   ```

3. Open a web browser and navigate to:
   ```
   http://localhost:5000
   ```

### Connecting to Rogue Equipment

1. Put your Rogue device in connection mode:
   - **For Echo Bike**: Press and hold the "Connect" button for 2 seconds until you hear two beeps. The Bluetooth and ANT+ icons should flash on the console to indicate it's ready to pair.
   - **For Echo Rower**: From the home screen, select the "Connect" option, then choose "Connect to App". The console will search for an application to pair with over BLE.

2. Navigate to the "Devices" page in the web interface
3. Click "Scan for Devices" to discover available Rogue equipment
4. Select your device from the list and click "Connect"
5. Once connected, the device status will show as "Connected" and the Bluetooth icon on your device's console should stop flashing and remain solid

### Starting a Workout

1. Navigate to the "Workout" page
2. Click "Start Workout" to begin tracking
3. Your workout metrics will be displayed in real-time
4. Click "End Workout" when finished

### Viewing Workout History

1. Navigate to the "History" page
2. Browse through your past workouts
3. Click on a workout to view detailed metrics and charts
4. View speed data visualizations instead of distance for more useful analysis

### Uploading to Garmin Connect

1. Navigate to the "History" page
2. Select a workout from the list
3. Click the "FIT" button to generate and download the FIT file
4. Manually upload the downloaded FIT file to Garmin Connect via their website or desktop application.

## Recent Improvements

### May 2025 Updates

- **Migration to `pyftms`**: Replaced `pycycling` with `pyftms` for more robust and specialized FTMS communication, particularly improving rower support.
- **Python 3.12 Requirement**: Updated project to require Python 3.12 due to `pyftms` dependencies.
- **Removal of Direct Garmin Connect Upload**: The feature for direct automated upload to Garmin Connect has been removed due to complexities with 2FA and API changes. Users now download FIT files for manual upload.
- **Proper Training Load Calculation**: FIT files now properly report training load in Garmin Connect by using appropriate device identification
- **Improved Speed Metrics**: Fixed issues with average speed calculation and reporting in FIT files
- **Enhanced Workout Visualization**: Added speed charts in workout history for better performance analysis
- **FIT File Analysis Tools**: Added tools for analyzing and comparing FIT files to ensure compatibility with Garmin Connect

## Project Structure

- `src/ftms/`: Bluetooth connectivity and FTMS protocol implementation (using `pyftms`).
- `src/data/`: Data collection, processing, and storage
- `src/fit/`: FIT file conversion logic.
- `src/web/`: Web interface (Flask application)
- `docs/`: Project documentation
- `fit_files/`: Generated FIT files from workouts (if configured to save locally, though typically downloaded by user)
- `tools/`: Utility scripts for analysis and troubleshooting

## Configuration

Configuration options are available in the web interface under "Settings" or can be set via environment variables:

- `PORT`: The port to run the application on (default: 5000)
- `DEBUG`: Set to "True" to enable debug mode (default: False)
- `DATABASE_URL`: URL for the database (default: SQLite database in the data directory)
- `SECRET_KEY`: Secret key for session encryption (required for production)

## Development

### FTMS Device Simulator

For development without physical hardware, the application includes an FTMS device simulator:

1. Start the application with the simulator flag (using Python 3.12):
   ```
   python3.12 src/web/app.py --use-simulator
   ```

2. The simulator will appear as a device that can be connected to from the web interface

3. For detailed instructions on using the simulator to test workouts, please see the [Testing with the FTMS Simulator](docs/testing_with_simulator.md) documentation.

### FIT File Analysis

The project includes tools for analyzing FIT files:

- `compare_fit_files.py`: Compare device identification and other metadata between FIT files
- `compare_speed_fields.py`: Analyze speed data in FIT files for troubleshooting

### Running Tests

```
pytest
```

## Troubleshooting

### Common Issues

- **Bluetooth Connection Problems**: Ensure your Bluetooth adapter supports BLE and is enabled. Ensure `bluez` (Linux) or appropriate BLE drivers are installed and working.
- **Device Not Found**: Make sure your Rogue equipment is powered on and in Bluetooth pairing mode
- **Incorrect Speed Data**: If speed is not showing in Garmin Connect, check your FIT files using the analysis tools

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Rogue Fitness for their FTMS-compatible equipment
- The Garmin Connect team for their fitness platform
- All contributors to the Python libraries used in this project, especially the `pyftms` and `bleak` libraries.

