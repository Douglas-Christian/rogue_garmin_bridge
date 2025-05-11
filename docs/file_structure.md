# Rogue to Garmin Bridge - Project File Structure

This document outlines the file structure for the Rogue to Garmin Bridge project, which enables connecting Rogue Echo fitness equipment to Garmin Connect.

## Project Root Directory

The project is organized in the following directory structure:

```
rogue_garmin_bridge/
├── docs/                       # Documentation files
│   ├── system_architecture.md  # System architecture documentation
│   ├── data_flow_diagram.md    # Data flow documentation
│   └── project_plan.md         # Project plan and timeline
├── src/                        # Source code
│   ├── ftms/                   # FTMS connectivity module
│   │   ├── __init__.py         # Package initialization
│   │   ├── ftms_connector.py   # FTMS device connection handling
│   │   ├── ftms_simulator.py   # Simulator for testing without real devices
│   │   └── ftms_manager.py     # Unified interface for real/simulated devices
│   ├── data/                   # Data collection and processing module
│   │   ├── __init__.py         # Package initialization
│   │   ├── database.py         # Database operations
│   │   ├── workout_manager.py  # Workout session management
│   │   └── data_processor.py   # Data analysis and processing
│   ├── fit/                    # FIT file conversion module
│   │   ├── __init__.py         # Package initialization
│   │   ├── fit_converter.py    # Conversion to Garmin FIT format
│   │   └── garmin_uploader.py  # Garmin Connect upload functionality
│   └── web/                    # Web frontend interface
│       ├── app.py              # Flask web application
│       ├── templates/          # HTML templates
│       │   ├── layout.html     # Base template
│       │   ├── index.html      # Home page
│       │   ├── devices.html    # Device management page
│       │   ├── workout.html    # Workout tracking page
│       │   ├── history.html    # Workout history page
│       │   └── settings.html   # User settings page
│       └── static/             # Static assets
│           ├── css/            # CSS stylesheets
│           │   └── style.css   # Main stylesheet
│           └── js/             # JavaScript files
│               └── main.js     # Main JavaScript file
└── todo.md                     # Project todo list
```

## File Locations

Below is a list of all files in the project with their absolute paths:

### Documentation Files
- `/home/ubuntu/rogue_garmin_bridge/docs/system_architecture.md`
- `/home/ubuntu/rogue_garmin_bridge/docs/data_flow_diagram.md`
- `/home/ubuntu/rogue_garmin_bridge/docs/project_plan.md`

### FTMS Connectivity Module
- `/home/ubuntu/rogue_garmin_bridge/src/ftms/__init__.py`
- `/home/ubuntu/rogue_garmin_bridge/src/ftms/ftms_connector.py`
- `/home/ubuntu/rogue_garmin_bridge/src/ftms/ftms_simulator.py`
- `/home/ubuntu/rogue_garmin_bridge/src/ftms/ftms_manager.py`

### Data Collection and Processing Module
- `/home/ubuntu/rogue_garmin_bridge/src/data/__init__.py`
- `/home/ubuntu/rogue_garmin_bridge/src/data/database.py`
- `/home/ubuntu/rogue_garmin_bridge/src/data/workout_manager.py`
- `/home/ubuntu/rogue_garmin_bridge/src/data/data_processor.py`

### FIT File Conversion Module
- `/home/ubuntu/rogue_garmin_bridge/src/fit/__init__.py`
- `/home/ubuntu/rogue_garmin_bridge/src/fit/fit_converter.py`
- `/home/ubuntu/rogue_garmin_bridge/src/fit/garmin_uploader.py`

### Web Frontend Interface
- `/home/ubuntu/rogue_garmin_bridge/src/web/app.py`
- `/home/ubuntu/rogue_garmin_bridge/src/web/templates/layout.html`
- `/home/ubuntu/rogue_garmin_bridge/src/web/templates/index.html`
- `/home/ubuntu/rogue_garmin_bridge/src/web/templates/devices.html`
- `/home/ubuntu/rogue_garmin_bridge/src/web/templates/workout.html`
- `/home/ubuntu/rogue_garmin_bridge/src/web/templates/history.html`
- `/home/ubuntu/rogue_garmin_bridge/src/web/templates/settings.html`
- `/home/ubuntu/rogue_garmin_bridge/src/web/static/css/style.css`
- `/home/ubuntu/rogue_garmin_bridge/src/web/static/js/main.js`

### Project Management
- `/home/ubuntu/rogue_garmin_bridge/todo.md`

## Runtime Directories

The application will create the following directories at runtime:

- `/home/ubuntu/rogue_garmin_bridge/data/` - For the SQLite database file
- `/home/ubuntu/rogue_garmin_bridge/fit_files/` - For generated FIT files

## Installation and Setup

To set up the project on a Raspberry Pi 2:

1. Clone the repository to your Raspberry Pi
2. Install required dependencies:
   ```
   pip install flask bleak fit-tool
   ```
3. Run the application:
   ```
   cd /home/ubuntu/rogue_garmin_bridge/src/web
   python app.py
   ```
4. Access the web interface at `http://<raspberry-pi-ip>:5000`

## Deployment

The application is designed to run on a Raspberry Pi 2 connected to the same network as your Rogue Echo equipment. The web interface can be accessed from any device on the same network.
