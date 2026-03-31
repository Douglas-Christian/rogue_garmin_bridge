# User Manual

This comprehensive user manual covers all features and functionality of the Rogue Garmin Bridge application.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Device Management](#device-management)
3. [Workout Monitoring](#workout-monitoring)
4. [Workout History & Analytics](#workout-history--analytics)
5. [Settings & Configuration](#settings--configuration)
6. [FIT File Management](#fit-file-management)
7. [Advanced Features](#advanced-features)
8. [Tips & Best Practices](#tips--best-practices)

## Getting Started

### First Launch

1. **Start the Application**
   ```bash
   python src/web/app.py
   ```

2. **Access Web Interface**
   - Open your web browser
   - Navigate to `http://localhost:5000`
   - You'll see the main dashboard

3. **Initial Setup Wizard**
   - Complete your user profile
   - Set unit preferences (metric/imperial)
   - Configure basic workout settings

### Main Navigation

The application features a clean, intuitive interface with four main sections:

- **Dashboard**: Overview of recent activity and system status
- **Devices**: Equipment connection and management
- **Workout**: Real-time workout monitoring and control
- **History**: Past workout analysis and data management
- **Settings**: Configuration and preferences

## Device Management

### Connecting Your Equipment

#### Rogue Echo Bike Setup

1. **Prepare the Bike**
   - Ensure the bike is powered on
   - Press and hold the "Connect" button for 2 seconds
   - You'll hear confirmation beeps when ready

2. **Pair via Web Interface**
   - Navigate to the "Devices" page
   - Click "Discover Devices"
   - Select "Rogue Echo Bike" from the list
   - Click "Connect"

#### Rogue Echo Rower Setup

1. **Prepare the Rower**
   - Power on the rower display
   - Navigate to: Menu → Connect → Connect to App
   - The display will show "Searching for App"

2. **Pair via Web Interface**
   - Navigate to the "Devices" page
   - Click "Discover Devices"
   - The rower will appear as **"ROGUE CONSOLE XXXXXX"** (not "Rogue Echo Rower")
   - **Important**: Change the **Device Type** dropdown to **"Rower"** before connecting
   - Click "Connect"

   > The Rogue Echo Rower's BLE name does not contain the word "rower", so the app cannot auto-detect it. You must manually select Rower from the Device Type dropdown or rower-specific metrics (stroke rate, etc.) will not be recorded correctly.

### Device Status Indicators

The Devices page provides comprehensive status information:

- **Connection Status**: Connected, Disconnected, Connecting, Error
- **Signal Strength**: Real-time BLE signal quality (Excellent, Good, Fair, Poor)
- **Data Rate**: Current data transmission rate
- **Battery Level**: Equipment battery status (if available)
- **Last Seen**: Timestamp of last successful communication

### Connection Management Features

#### Auto-Reconnection
- Automatic reconnection attempts with exponential backoff
- Configurable retry intervals and maximum attempts
- User notification of reconnection status

#### Connection Quality Monitoring
- Real-time signal strength monitoring
- Data transmission rate tracking
- Connection stability metrics
- Automatic quality alerts

#### Device Diagnostics
- Built-in system health checks
- Bluetooth adapter status verification
- Equipment compatibility testing
- Troubleshooting recommendations

### Troubleshooting Connection Issues

#### Device Not Found
1. Verify equipment is in pairing mode
2. Check Bluetooth is enabled on your computer
3. Ensure equipment is within range (typically 10 meters)
4. Try restarting the discovery process

#### Connection Drops
1. Check signal strength indicators
2. Move closer to equipment if signal is weak
3. Verify no interference from other devices
4. Use auto-reconnection feature

#### Poor Data Quality
1. Monitor connection quality metrics
2. Check for physical obstructions
3. Verify equipment firmware is up to date
4. Consider Bluetooth adapter upgrade if needed

## Workout Monitoring

### Starting a Workout

1. **Ensure Device Connection**
   - Verify your equipment shows "Connected" status
   - Check signal strength is "Good" or better

2. **Begin Workout Session**
   - Navigate to the "Workout" page
   - Click "Start Workout"
   - Begin exercising on your equipment

3. **Monitor Real-time Data**
   - View live metrics updating every second
   - Watch interactive charts for data trends
   - Monitor workout phase indicators

### Real-time Metrics Display

#### Common Metrics (Both Devices)
- **Power**: Current and average power output (watts)
- **Heart Rate**: Current and average heart rate (BPM)
- **Calories**: Estimated calorie burn
- **Distance**: Total distance covered
- **Duration**: Elapsed workout time

#### Bike-Specific Metrics
- **Cadence**: Pedaling rate (RPM)
- **Speed**: Current and average speed (km/h or mph)

#### Rower-Specific Metrics
- **Stroke Rate**: Strokes per minute
- **Stroke Count**: Total strokes completed
- **Split Time**: Time per 500m (rowing standard)

### Interactive Charts

#### Real-time Data Visualization
- **Power Chart**: Power output over time with smoothing options
- **Heart Rate Chart**: Heart rate progression with zone indicators
- **Combined Metrics**: Multiple metrics on single chart
- **Zoom and Pan**: Interactive chart navigation

#### Chart Features
- **Data Decimation**: Optimized rendering for smooth performance
- **Customizable Time Windows**: 1min, 5min, 15min, full workout
- **Metric Selection**: Show/hide specific data series
- **Export Options**: Save charts as images

### Workout Phases

The application automatically detects and displays workout phases:

#### Phase Detection
- **Warm-up**: Low intensity start (typically first 5-10 minutes)
- **Main Workout**: Primary exercise period
- **Intervals**: High/low intensity alternating periods
- **Cool-down**: Low intensity finish (typically last 5-10 minutes)

#### Phase Indicators
- Visual phase markers on charts
- Current phase display in metrics panel
- Phase-specific performance analysis
- Automatic phase transition notifications

### Workout Controls

#### During Workout
- **Pause/Resume**: Temporarily pause data collection
- **Add Marker**: Mark significant points in workout
- **View Stats**: Real-time performance statistics
- **End Workout**: Complete and save workout session

#### Data Recording Options
- **Recording Interval**: 1-second (default) or custom intervals
- **Data Smoothing**: Power smoothing for cleaner charts
- **Auto-pause**: Automatic pause when no activity detected
- **Manual Lap Markers**: Create custom workout segments

## Workout History & Analytics

### Viewing Workout History

1. **Access History Page**
   - Navigate to "History" from main menu
   - View chronological list of all workouts

2. **Filter and Search**
   - **Date Range**: Select specific time periods
   - **Device Type**: Filter by bike or rower workouts
   - **Duration**: Filter by workout length
   - **Search**: Find workouts by notes or tags

### Detailed Workout Analysis

#### Workout Summary
- **Basic Metrics**: Duration, distance, calories, average power
- **Performance Metrics**: Peak power, average heart rate, training load
- **Equipment Info**: Device type, connection quality during workout
- **Environmental Data**: Date, time, workout notes

#### Interactive Charts
- **Power Analysis**: Power distribution, peak intervals, smoothing options
- **Heart Rate Analysis**: HR zones, recovery patterns, peak HR
- **Pace/Speed Analysis**: Speed variations, acceleration patterns
- **Combined Analysis**: Multiple metrics with correlation analysis

#### Advanced Analytics
- **Power Zones**: Time spent in different power zones
- **Training Load**: Estimated training stress and recovery time
- **Performance Trends**: Progress tracking over time
- **Comparative Analysis**: Compare with previous workouts

### Workout Comparison

#### Side-by-Side Comparison
1. **Select Workouts**: Choose 2-4 workouts to compare
2. **Comparison View**: Side-by-side metrics and charts
3. **Performance Analysis**: Identify improvements and patterns
4. **Export Comparison**: Save comparison reports

#### Comparison Features
- **Metric Comparison**: Direct comparison of key metrics
- **Chart Overlay**: Overlay multiple workout charts
- **Performance Trends**: Track progress over time
- **Statistical Analysis**: Correlation and trend analysis

### Data Export Options

#### Export Formats
- **FIT Files**: Garmin Connect compatible format
- **CSV**: Spreadsheet-compatible data export
- **JSON**: Raw data for custom analysis
- **PDF Reports**: Formatted workout summaries

#### Export Features
- **Date Range Selection**: Export multiple workouts
- **Metric Selection**: Choose specific data fields
- **Chart Export**: Include charts in exports
- **Batch Export**: Export multiple workouts simultaneously

## Settings & Configuration

### User Profile Management

#### Personal Information
- **Basic Info**: Name, age, gender, weight, height
- **Fitness Level**: Beginner, intermediate, advanced
- **Goals**: Weight loss, endurance, strength, general fitness
- **Medical Info**: Heart rate zones, maximum heart rate

#### Unit Preferences
- **Distance**: Kilometers or miles (applies to speed and distance in workout and history views)
- **Weight**: Kilograms or pounds
- **Temperature**: Celsius or Fahrenheit
- **Power**: Watts (standard for both systems)

### VO2 Max Estimation

The application estimates VO2 Max during workouts using heart rate and power data. To get a VO2 Max reading:

#### Requirements
1. **Age** — set in User Profile (used to calculate max HR as 220 − age if not set manually)
2. **Weight** — set in User Profile (required for power-to-weight calculation)
3. **Heart Rate Monitor** — a HR monitor must be connected and transmitting data
4. **Sustained Effort** — your **average heart rate for the workout** must exceed **70% of your max HR**

#### Improving Accuracy
- Set your actual **Max Heart Rate** in Settings rather than relying on the 220 − age estimate
- Set your **Resting Heart Rate** for a more accurate heart rate reserve calculation
- Maintain a steady effort rather than short hard bursts; the threshold is based on your workout average HR, not a momentary peak

#### Example
If you are 40 years old: estimated max HR = 180 bpm, 70% threshold = 126 bpm. Your average HR across the full workout must stay above 126 bpm for a VO2 Max estimate to appear.

### Workout Preferences

#### Default Settings
- **Auto-start**: Automatically begin recording when activity detected
- **Auto-pause**: Pause recording when activity stops
- **Recording Interval**: Data collection frequency (1-10 seconds)
- **Workout Timeout**: Maximum workout duration

#### Data Processing
- **Power Smoothing**: Smoothing algorithm for power data
- **Heart Rate Smoothing**: Filter for heart rate spikes
- **Speed Calculation**: Method for speed calculation
- **Calorie Calculation**: Algorithm for calorie estimation

### System Configuration

#### Connection Settings
- **Connection Timeout**: Maximum time to wait for device connection
- **Reconnection Attempts**: Number of automatic reconnection tries
- **Signal Threshold**: Minimum acceptable signal strength
- **Data Quality Threshold**: Minimum data quality for recording

#### Performance Settings
- **Chart Update Rate**: Frequency of real-time chart updates
- **Data Retention**: How long to keep workout data
- **Cache Settings**: Client-side caching preferences
- **Memory Management**: Automatic cleanup settings

### Data Management

#### Backup and Restore
- **Automatic Backups**: Scheduled backup creation
- **Manual Backup**: On-demand backup creation
- **Backup Location**: Local or cloud storage options
- **Restore Options**: Full or selective data restoration

#### Storage Management
- **Storage Monitoring**: Track disk space usage
- **Data Cleanup**: Remove old logs and temporary files
- **Archive Options**: Compress old workout data
- **Export Before Cleanup**: Automatic export before deletion

#### Privacy Settings
- **Data Anonymization**: Remove personal identifiers
- **Sharing Preferences**: Control data sharing options
- **Export Restrictions**: Limit data export capabilities
- **Audit Logging**: Track data access and modifications

## FIT File Management

### Understanding FIT Files

FIT (Flexible and Interoperable Data Transfer) files are the standard format used by Garmin Connect and other fitness platforms. The application generates FIT files that include:

- **Activity Data**: Complete workout metrics and timeline
- **Device Information**: Equipment identification for proper training load calculation
- **Training Metrics**: Power zones, heart rate zones, training stress
- **Compatibility Data**: Ensures proper Garmin Connect integration

### Generating FIT Files

#### From Workout History
1. **Select Workout**: Choose workout from history page
2. **Generate FIT**: Click "Generate FIT File" button
3. **Download**: File automatically downloads to your browser's download folder
4. **Upload to Garmin**: Manually upload to Garmin Connect

#### Batch Generation
1. **Select Multiple Workouts**: Use checkboxes to select workouts
2. **Batch Generate**: Click "Generate All FIT Files"
3. **Download ZIP**: All FIT files packaged in single download
4. **Individual Upload**: Upload each file to Garmin Connect

### FIT File Validation

#### Built-in Validation
- **Format Compliance**: Ensures FIT file format standards
- **Data Integrity**: Validates all required fields are present
- **Garmin Compatibility**: Tests compatibility with Garmin Connect
- **Training Load Accuracy**: Verifies training load calculations

#### Validation Tools
- **FIT Analyzer**: Detailed analysis of generated FIT files
- **Comparison Tool**: Compare generated files with reference files
- **Error Detection**: Identify and report FIT file issues
- **Repair Options**: Automatic fixing of common issues

### Garmin Connect Integration

#### Upload Process
1. **Generate FIT File**: From workout history
2. **Access Garmin Connect**: Log into your Garmin Connect account
3. **Manual Upload**: Use Garmin Connect's import feature
4. **Verify Upload**: Confirm workout appears correctly

#### Training Load Integration
- **Proper Device ID**: Ensures training load calculations
- **Sport Type Mapping**: Correct activity type assignment
- **Intensity Metrics**: Accurate intensity and stress calculations
- **Recovery Recommendations**: Proper recovery time suggestions

## Advanced Features

### FTMS Device Simulator

For testing and development without physical equipment:

#### Enabling Simulator Mode
```bash
# Start with bike simulator
python src/web/app.py --use-simulator --device-type bike

# Start with rower simulator
python src/web/app.py --use-simulator --device-type rower
```

#### Simulator Features
- **Realistic Data**: Based on actual workout patterns
- **Configurable Scenarios**: Different workout types and intensities
- **Error Injection**: Test error handling and recovery
- **Performance Testing**: Validate system under various conditions

### API Access

The application provides REST API endpoints for advanced integration:

#### Workout Data API
- `GET /api/workouts`: List all workouts
- `GET /api/workouts/{id}`: Get specific workout details
- `POST /api/workouts`: Create new workout (for integrations)
- `DELETE /api/workouts/{id}`: Delete workout

#### Device Status API
- `GET /api/devices`: List connected devices
- `GET /api/devices/{id}/status`: Get device status
- `POST /api/devices/{id}/connect`: Connect to device
- `POST /api/devices/{id}/disconnect`: Disconnect device

#### Real-time Data API
- `GET /api/live-data`: Current workout data
- WebSocket endpoint for real-time updates
- Server-sent events for live metrics

### Custom Integrations

#### Webhook Support
- Configure webhooks for workout completion
- Send data to external systems
- Custom notification systems
- Third-party platform integration

#### Data Export Automation
- Scheduled exports to cloud storage
- Automatic FIT file generation
- Custom data format support
- Integration with fitness platforms

## Tips & Best Practices

### Optimal Setup

#### Equipment Placement
- Keep computer within 10 meters of equipment
- Avoid physical obstructions between devices
- Minimize interference from other Bluetooth devices
- Ensure stable power supply for equipment

#### Performance Optimization
- Close unnecessary applications during workouts
- Use wired internet connection when possible
- Regularly update application and dependencies
- Monitor system resources during long workouts

### Workout Best Practices

#### Pre-Workout
- Verify device connection before starting
- Check signal strength indicators
- Ensure adequate storage space
- Set workout goals and preferences

#### During Workout
- Monitor connection quality indicators
- Use pause feature for breaks longer than 30 seconds
- Add markers for significant workout points
- Keep equipment within optimal range

#### Post-Workout
- Allow data processing to complete before closing
- Generate FIT files promptly after workout
- Review workout data for accuracy
- Back up important workout data

### Data Management

#### Regular Maintenance
- Perform weekly data backups
- Clean up old log files monthly
- Update application regularly
- Monitor storage usage

#### Quality Assurance
- Review workout data for anomalies
- Validate FIT files before Garmin upload
- Compare metrics with equipment displays
- Report persistent data quality issues

### Troubleshooting Tips

#### Connection Issues
- Restart Bluetooth service if connections fail
- Clear Bluetooth cache on Windows systems
- Update Bluetooth drivers regularly
- Use built-in diagnostic tools

#### Performance Issues
- Monitor system resources during workouts
- Reduce chart update frequency if needed
- Clear browser cache for web interface issues
- Restart application for memory issues

#### Data Issues
- Validate workout data after each session
- Use data repair tools for corrupted files
- Export data before major updates
- Keep backup copies of important workouts

## Getting Help

### Built-in Help
- **Diagnostic Tools**: Available in Devices page
- **Troubleshooting Guides**: Integrated help system
- **Error Messages**: Detailed error descriptions and solutions
- **Status Indicators**: Real-time system health information

### Documentation
- **Installation Guide**: Complete setup instructions
- **Troubleshooting Guide**: Common issues and solutions
- **API Documentation**: For advanced integrations
- **Developer Guide**: For customization and development

### Support Resources
- **GitHub Issues**: Report bugs and request features
- **Community Forums**: User discussions and tips
- **Video Tutorials**: Visual guides for key features
- **FAQ**: Frequently asked questions and answers