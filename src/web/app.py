#!/usr/bin/env python3
"""
Flask web application for the Rogue Garmin Bridge.
This provides a web interface for managing devices and workouts.
"""

import os
import time
import argparse
from flask import Flask, render_template, request, jsonify, redirect, url_for
import threading
import sys
import importlib  # Add importlib for module reloading

# Add the project root to the path so we can use absolute imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
# Force reload modules to avoid stale imports
import src.ftms.ftms_manager
importlib.reload(src.ftms.ftms_manager)
import src.ftms.ftms_simulator
importlib.reload(src.ftms.ftms_simulator)

from src.data.workout_manager import WorkoutManager
from src.data.database import Database
from src.ftms.ftms_manager import FTMSDeviceManager
from src.utils.logging_config import get_component_logger

# Parse command line arguments
parser = argparse.ArgumentParser(description='Start the Rogue Garmin Bridge web application')
parser.add_argument('--use-simulator', action='store_true', help='Use the FTMS device simulator instead of real devices')
parser.add_argument('--device-type', default='bike', choices=['bike', 'rower'], help='Type of device to simulate (bike or rower)')
args = parser.parse_args()

# Get component logger
logger = get_component_logger('web')

# Initialize Flask app
app = Flask(__name__)

# Create database and workout manager
db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'src', 'data', 'rogue_garmin.db')
db = Database(db_path)
workout_manager = WorkoutManager(db)

# Start FTMS device manager in a separate thread
logger.info(f"Initializing FTMSDeviceManager with use_simulator={args.use_simulator}, device_type={args.device_type}")
ftms_manager = FTMSDeviceManager(workout_manager, use_simulator=args.use_simulator, device_type=args.device_type)
ftms_thread = threading.Thread(target=ftms_manager.start_scanning, daemon=True)
ftms_thread.start()

if args.use_simulator:
    logger.info(f"Using FTMS device simulator for {args.device_type}")
else:
    logger.info("Using real FTMS devices")

logger.info("Flask application initialized. FTMS scanning thread started.")

# Routes
@app.route('/')
def index():
    """Render the main page."""
    return render_template('index.html')

@app.route('/devices')
def devices():
    """Render the devices page."""
    return render_template('devices.html')

@app.route('/workout')
def workout():
    """Render the workout page."""
    return render_template('workout.html')

@app.route('/history')
def history():
    """Render the workout history page."""
    return render_template('history.html')

@app.route('/settings')
def settings():
    """Render the settings page."""
    return render_template('settings.html')

# API routes
@app.route('/api/discover', methods=['POST'])
def discover_devices():
    """Discover FTMS devices."""
    try:
        devices = ftms_manager.discover_devices()
        return jsonify({'success': True, 'devices': devices})
    except Exception as e:
        logger.error(f"Error discovering devices: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/settings', methods=['GET', 'POST'])
def api_settings():
    """Get or update application settings."""
    try:
        settings_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'settings.json')
        
        if request.method == 'POST':
            # Update settings
            settings = request.json
            
            # Load existing settings if file exists
            existing_settings = {}
            if os.path.exists(settings_file):
                try:
                    with open(settings_file, 'r') as f:
                        existing_settings = importlib.import_module('json').load(f)
                except Exception as e:
                    logger.error(f"Error loading existing settings: {str(e)}")
            
            # Update settings with new values
            existing_settings.update(settings)
            
            # Save settings
            with open(settings_file, 'w') as f:
                importlib.import_module('json').dump(existing_settings, f)
            
            # Apply settings if needed
            if 'use_simulator' in settings:
                ftms_manager.use_simulator = settings['use_simulator']
            
            return jsonify({'success': True})
        else:
            # Get settings
            if os.path.exists(settings_file):
                try:
                    with open(settings_file, 'r') as f:
                        settings = importlib.import_module('json').load(f)
                    return jsonify({'success': True, 'settings': settings})
                except Exception as e:
                    logger.error(f"Error loading settings: {str(e)}")
                    return jsonify({'success': False, 'error': str(e)})
            else:
                # Return default settings if file doesn't exist
                return jsonify({'success': True, 'settings': {'use_simulator': False}})
    except Exception as e:
        logger.error(f"Error processing settings: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/user_profile', methods=['GET', 'POST'])
def api_user_profile():
    """Get or update user profile."""
    try:
        profile_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'user_profile.json')
        
        if request.method == 'POST':
            # Update profile
            profile = request.json
            
            # Load existing profile if file exists
            existing_profile = {}
            if os.path.exists(profile_file):
                try:
                    with open(profile_file, 'r') as f:
                        existing_profile = importlib.import_module('json').load(f)
                except Exception as e:
                    logger.error(f"Error loading existing profile: {str(e)}")
            
            # Update profile with new values
            existing_profile.update(profile)
            
            # Save profile
            with open(profile_file, 'w') as f:
                importlib.import_module('json').dump(existing_profile, f)
            
            return jsonify({'success': True})
        else:
            # Get profile
            if os.path.exists(profile_file):
                try:
                    with open(profile_file, 'r') as f:
                        profile = importlib.import_module('json').load(f)
                    return jsonify({'success': True, 'profile': profile})
                except Exception as e:
                    logger.error(f"Error loading profile: {str(e)}")
                    return jsonify({'success': False, 'error': str(e)})
            else:
                # Return empty profile if file doesn't exist
                return jsonify({'success': True, 'profile': {}})
    except Exception as e:
        logger.error(f"Error processing user profile: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/connect', methods=['POST'])
def connect_device():
    """Connect to an FTMS device."""
    try:
        device_address = request.json.get('address')
        if not device_address:
            return jsonify({'success': False, 'error': 'Device address is required'})
        
        success = ftms_manager.connect(device_address)
        return jsonify({'success': success})
    except Exception as e:
        logger.error(f"Error connecting to device: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/disconnect', methods=['POST'])
def disconnect_device():
    """Disconnect from the current FTMS device."""
    try:
        success = ftms_manager.disconnect()
        return jsonify({'success': success})
    except Exception as e:
        logger.error(f"Error disconnecting from device: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/status')
def get_status():
    """Get current status."""
    status = {
        'device_status': ftms_manager.device_status,
        'connected_device': ftms_manager.connected_device,
        'workout_active': workout_manager.active_workout_id is not None
    }
    return jsonify(status)

@app.route('/api/start_workout', methods=['POST'])
def start_workout():
    """Start a new workout."""
    try:
        device_id = request.json.get('device_id')
        workout_type = request.json.get('workout_type', 'bike')  # Default to 'bike' if not provided
        workout_id = workout_manager.start_workout(device_id, workout_type)
        return jsonify({'success': True, 'workout_id': workout_id})
    except Exception as e:
        logger.error(f"Error starting workout: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/end_workout', methods=['POST'])
def end_workout():
    """End the current workout."""
    try:
        workout_id = request.json.get('workout_id', workout_manager.active_workout_id)
        success = workout_manager.end_workout(workout_id)
        return jsonify({'success': success})
    except Exception as e:
        logger.error(f"Error ending workout: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/workouts')
def get_workouts():
    """Get workout history."""
    try:
        workouts = workout_manager.get_workouts()
        return jsonify({'success': True, 'workouts': workouts})
    except Exception as e:
        logger.error(f"Error getting workouts: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/workout/<int:workout_id>')
def get_workout(workout_id):
    """Get workout details."""
    try:
        workout = workout_manager.get_workout(workout_id)
        if not workout:
            return jsonify({'success': False, 'error': 'Workout not found'})
        return jsonify({'success': True, 'workout': workout})
    except Exception as e:
        logger.error(f"Error getting workout details: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

# Run the app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)