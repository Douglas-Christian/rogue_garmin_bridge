#!/usr/bin/env python3
"""
Flask web application for the Rogue Garmin Bridge.
This provides a web interface for managing devices and workouts.
"""

import os
import time
import argparse
import asyncio
import threading
import logging # Add logging import
import sqlite3 # Add sqlite3 import for direct database access
from flask import Flask, render_template, request, jsonify, redirect, url_for
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
workout_manager = WorkoutManager(db_path)  # Pass the path string, not the Database object

# Start FTMS device manager
logger.info(f"Initializing FTMSDeviceManager with use_simulator={args.use_simulator}, device_type={args.device_type}")
ftms_manager = FTMSDeviceManager(workout_manager, use_simulator=args.use_simulator, device_type=args.device_type)

if args.use_simulator:
    logger.info(f"Using FTMS device simulator for {args.device_type}")
else:
    logger.info("Using real FTMS devices")

logger.info("Flask application initialized. FTMS manager created.")

# Global variable for the asyncio loop and the thread running it
background_loop = None
loop_thread = None

def start_asyncio_loop():
    """Starts the asyncio event loop in a separate thread."""
    global background_loop
    try:
        logger.info("Background thread started. Creating new event loop.")
        background_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(background_loop)
        logger.info("Starting background asyncio event loop run_forever.")
        background_loop.run_forever()
    except Exception as e:
        logger.error(f"Exception in background asyncio loop: {e}", exc_info=True)
    finally:
        if background_loop and background_loop.is_running():
            logger.info("Stopping background asyncio event loop.")
            background_loop.stop()
        logger.info("Background asyncio loop finished.")
        background_loop = None # Ensure it's None if loop stops

# Start the loop in a background thread when the app initializes
logger.info("Starting background asyncio loop thread...")
loop_thread = threading.Thread(target=start_asyncio_loop, daemon=True)
loop_thread.start()
logger.info("Background asyncio loop thread start initiated.")

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
    logger.debug(f"/api/discover called. background_loop is {'set' if background_loop else 'None'}. Loop running: {background_loop.is_running() if background_loop else 'N/A'}")
    try:
        if not background_loop or not background_loop.is_running():
             logger.error("Asyncio background loop is not running.")
             return jsonify({'success': False, 'error': 'Asyncio loop not running'})

        # Schedule the async discover_devices method on the background loop
        future = asyncio.run_coroutine_threadsafe(ftms_manager.discover_devices(), background_loop)
        devices_dict = future.result(timeout=10) # Wait for the result with timeout

        serializable_devices = []
        if isinstance(devices_dict, dict): # Check if it's a dictionary
            for address, dev_info in devices_dict.items(): # Iterate through dict items
                # dev_info could be an object or already a dict
                name = None
                if hasattr(dev_info, 'name'):
                    name = dev_info.name
                elif isinstance(dev_info, dict) and 'name' in dev_info:
                    name = dev_info['name']

                # Address is the key in the dictionary
                if name and address:
                    serializable_devices.append({'name': name, 'address': address})
                else:
                    logger.warning(f"Could not serialize device with address {address}: {dev_info}")
        else:
             logger.warning(f"discover_devices returned unexpected type: {type(devices_dict)}")

        return jsonify({'success': True, 'devices': serializable_devices})
    except asyncio.TimeoutError:
        logger.error("Device discovery timed out.")
        return jsonify({'success': False, 'error': 'Device discovery timed out'})
    except Exception as e:
        logger.error(f"Error discovering devices: {str(e)}", exc_info=True)
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
    device_address = request.json.get('address')
    logger.debug(f"/api/connect called for {device_address}. background_loop is {'set' if background_loop else 'None'}. Loop running: {background_loop.is_running() if background_loop else 'N/A'}")
    try:
        if not device_address:
            return jsonify({'success': False, 'error': 'Device address is required'})

        if not background_loop or not background_loop.is_running():
             logger.error("Asyncio background loop is not running.")
             return jsonify({'success': False, 'error': 'Asyncio loop not running'})

        # Schedule the async connect method on the background loop
        logger.info(f"Scheduling connect task for {device_address} on background loop.")
        future = asyncio.run_coroutine_threadsafe(ftms_manager.connect(device_address), background_loop)
        success = future.result(timeout=40) # Wait for the connection attempt to complete with timeout

        logger.info(f"Connect task for {device_address} completed with result: {success}")
        return jsonify({'success': success})
    except asyncio.TimeoutError:
        logger.error(f"Connection to {device_address} timed out.")
        return jsonify({'success': False, 'error': 'Connection timed out'})
    except Exception as e:
        logger.error(f"Error connecting to device {device_address}: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/disconnect', methods=['POST'])
def disconnect_device():
    """Disconnect from the current FTMS device."""
    logger.debug(f"/api/disconnect called. background_loop is {'set' if background_loop else 'None'}. Loop running: {background_loop.is_running() if background_loop else 'N/A'}")
    try:
        if not background_loop or not background_loop.is_running():
             logger.error("Asyncio background loop is not running.")
             return jsonify({'success': False, 'error': 'Asyncio loop not running'})

        # Schedule the async disconnect method on the background loop
        logger.info("Scheduling disconnect task on background loop.")
        future = asyncio.run_coroutine_threadsafe(ftms_manager.disconnect(), background_loop)
        success = future.result(timeout=10) # Wait for the result with timeout

        logger.info(f"Disconnect task completed with result: {success}")
        return jsonify({'success': success})
    except asyncio.TimeoutError:
        logger.error("Device disconnection timed out.")
        return jsonify({'success': False, 'error': 'Disconnection timed out'})
    except Exception as e:
        logger.error(f"Error disconnecting from device: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/status')
def get_status():
    """Get current status."""
    status = {
        'device_status': ftms_manager.device_status,
        # Serialize connected device info
        'connected_device': {
            'name': getattr(ftms_manager.connected_device, 'name', None),
            'address': getattr(ftms_manager.connected_device, 'address', None)
        } if ftms_manager.connected_device else None,
        'connected_device_address': getattr(ftms_manager, 'connected_device_address', None), # Keep this for compatibility if needed
        'device_name': getattr(ftms_manager.connected_device, 'name', None) if ftms_manager.connected_device else None, # Redundant but maybe used elsewhere
        'workout_active': workout_manager.active_workout_id is not None,
        'is_simulated': ftms_manager.use_simulator
    }
    
    # Include latest data if available
    if hasattr(ftms_manager, 'latest_data') and ftms_manager.latest_data:
        # Ensure latest_data is serializable (assuming it's already a dict)
        latest_data = ftms_manager.latest_data.copy()
        
        # Include the active workout ID
        if workout_manager.active_workout_id:
            latest_data['workout_id'] = workout_manager.active_workout_id
            
            # Add accumulated workout summary statistics
            try:
                # Get real-time summary metrics from workout_manager
                summary = workout_manager.get_workout_summary_metrics()
                if summary:
                    latest_data['workout_summary'] = summary
            except Exception as e:
                logger.error(f"Error getting workout summary: {str(e)}")
                
        status['latest_data'] = latest_data
        
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
        # Workout ID is not needed as end_workout() only ends the active workout
        success = workout_manager.end_workout()
        return jsonify({'success': success})
    except Exception as e:
        logger.error(f"Error ending workout: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/workouts')
def get_workouts():
    """Get workout history."""
    try:
        # Get query parameters for pagination
        limit = request.args.get('limit', 100, type=int)  # Increase default limit
        offset = request.args.get('offset', 0, type=int)
        
        logger.info(f"Getting workouts with limit={limit}, offset={offset}")
        
        # Get workouts from database
        workouts = workout_manager.get_workouts(limit, offset)
        
        # Log the result for debugging
        logger.info(f"Retrieved {len(workouts) if workouts else 0} workouts from database")
        
        # Process each workout to ensure summary is properly parsed
        for workout in workouts:
            # Ensure summary is a dictionary, not a string
            if 'summary' in workout:
                if isinstance(workout['summary'], str):
                    try:
                        import json
                        workout['summary'] = json.loads(workout['summary'])
                        logger.info(f"Parsed summary JSON string for workout {workout['id']}")
                    except Exception as e:
                        logger.error(f"Error parsing summary for workout {workout['id']}: {str(e)}")
                        workout['summary'] = {}  # Use empty dict if parsing fails
                elif workout['summary'] is None:
                    workout['summary'] = {}
            else:
                workout['summary'] = {}
                
        if not workouts:
            # Check if database has any workouts at all
            logger.warning("No workouts found in database")
            
            # For debugging, try to check for workouts using direct SQL
            try:
                conn = sqlite3.connect(db.db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM workouts")
                count = cursor.fetchone()[0]
                conn.close()
                
                logger.info(f"Database reports {count} workouts exist")
            except Exception as db_error:
                logger.error(f"Error checking database directly: {str(db_error)}")
            
            # Still return empty list with success=True
            return jsonify({'success': True, 'workouts': []})
            
        return jsonify({'success': True, 'workouts': workouts})
    except Exception as e:
        logger.error(f"Error getting workouts: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/workout/<int:workout_id>', methods=['GET', 'DELETE'])
def workout_operations(workout_id):
    """Get or delete workout details."""
    try:
        if request.method == 'DELETE':
            # Delete the workout
            success = workout_manager.delete_workout(workout_id)
            return jsonify({'success': success})
        else:
            # GET method - Get workout details
            # Get workout details
            workout = workout_manager.get_workout(workout_id)
            if not workout:
                return jsonify({'success': False, 'error': 'Workout not found'})
                
            # Get workout data points
            workout_data = workout_manager.get_workout_data(workout_id)
            
            # Process data for charts
            timestamps = []
            powers = []
            cadences = []
            heart_rates = []
            speeds = []
            distances = []
            
            for data_point in workout_data:
                # Extract the data from the data point structure
                data = data_point.get('data', {})
                
                # Add the timestamp (this should always be available)
                timestamps.append(data_point.get('timestamp', 0))
                
                # Extract metrics - check for different possible key names
                powers.append(data.get('instant_power', data.get('instantaneous_power', data.get('power', 0))))
                cadences.append(data.get('instant_cadence', data.get('instantaneous_cadence', data.get('cadence', 0))))
                heart_rates.append(data.get('heart_rate', 0))
                speeds.append(data.get('instant_speed', data.get('instantaneous_speed', data.get('speed', 0))))
                distances.append(data.get('total_distance', data.get('distance', 0)))
            
            # Convert workout to a regular dict if it's a sqlite Row
            if hasattr(workout, 'keys'):
                workout = dict(workout)
                
            # Handle summary data - ensure it's properly parsed from JSON if needed
            if 'summary' in workout and workout['summary']:
                if isinstance(workout['summary'], str):
                    try:
                        import json
                        workout['summary'] = json.loads(workout['summary'])
                        logger.info(f"Successfully parsed workout summary from JSON string for workout {workout_id}")
                    except Exception as e:
                        logger.error(f"Error parsing workout summary JSON for workout {workout_id}: {str(e)}")
                        # Keep the summary as is if it cannot be parsed
                
            # Add data series to workout
            workout['data_series'] = {
                'timestamps': timestamps,
                'powers': powers,
                'cadences': cadences,
                'heart_rates': heart_rates,
                'speeds': speeds,
                'distances': distances
            }
            
            # Add data point count for UI reference
            workout['data_point_count'] = len(workout_data)
            
            return jsonify({'success': True, 'workout': workout})
    except Exception as e:
        logger.error(f"Error in workout operations: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/convert_fit/<int:workout_id>', methods=['POST'])
def convert_workout_to_fit(workout_id):
    """Convert workout to FIT file and return the file path."""
    try:
        # Import the FIT converter
        from src.fit.fit_converter import FITConverter
        
        # Get workout details
        workout = workout_manager.get_workout(workout_id)
        
        if not workout:
            return jsonify({'success': False, 'error': 'Workout not found'})
        
        # Handle summary as JSON string if needed
        if 'summary' in workout and workout['summary'] and isinstance(workout['summary'], str):
            try:
                import json
                workout['summary'] = json.loads(workout['summary'])
                logger.info(f"Successfully parsed workout summary from JSON string for workout {workout_id}")
            except Exception as e:
                logger.error(f"Error parsing workout summary JSON for workout {workout_id}: {str(e)}")
                workout['summary'] = {} # Use empty dict if parsing fails
                
        # Get workout data points
        workout_data = workout_manager.get_workout_data(workout_id)
        
        # Get user profile
        user_profile = None
        profile_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'user_profile.json')
        if os.path.exists(profile_file):
            try:
                with open(profile_file, 'r') as f:
                    import json
                    user_profile = json.load(f)
            except Exception as e:
                logger.error(f"Error loading user profile: {str(e)}")
        
        # Create processed data for FIT converter
        processed_data = {
            'workout_type': workout.get('workout_type', 'bike'),
            'start_time': workout.get('start_time'),
            'total_duration': workout.get('duration', 0),
            'data_series': {
                'timestamps': [],
                'powers': [],
                'cadences': [],
                'heart_rates': [],
                'speeds': [],
                'distances': [],
                'stroke_rates': []  # Adding stroke_rates explicitly for rowers
            }
        }
        
        # Extract summary metrics
        if 'summary' in workout and workout['summary']:
            summary = workout['summary']
            processed_data.update({
                'total_distance': summary.get('total_distance', 0),
                'total_calories': summary.get('total_calories', 0),
                'avg_power': summary.get('avg_power', 0),
                'max_power': summary.get('max_power', 0),
                'normalized_power': summary.get('normalized_power', 0),
                'avg_heart_rate': summary.get('avg_heart_rate', 0),
                'max_heart_rate': summary.get('max_heart_rate', 0),
                'avg_speed': summary.get('avg_speed', 0),
                'max_speed': summary.get('max_speed', 0)
            })
            
            if processed_data['workout_type'] == 'bike':
                processed_data.update({
                    'avg_cadence': summary.get('avg_cadence', 0),
                    'max_cadence': summary.get('max_cadence', 0)
                })
            elif processed_data['workout_type'] == 'rower':
                processed_data.update({
                    'avg_stroke_rate': summary.get('avg_stroke_rate', 0),
                    'max_stroke_rate': summary.get('max_stroke_rate', 0),
                    'total_strokes': summary.get('total_strokes', 0)
                })
        
        # Process data points
        # Store the absolute timestamps separately (needed by FIT converter)
        absolute_timestamps = []
        
        # Calculate start time as datetime object for relative timestamps
        start_time_obj = None
        if workout.get('start_time'):
            try:
                from datetime import datetime
                if isinstance(workout['start_time'], str):
                    start_time_obj = datetime.fromisoformat(workout['start_time'])
                else:
                    start_time_obj = workout['start_time']
            except Exception as e:
                logger.error(f"Error parsing start time: {str(e)}")
        
        for data_point in workout_data:
            # Extract timestamp
            timestamp = data_point.get('timestamp')
            if timestamp and isinstance(timestamp, str):
                try:
                    from datetime import datetime
                    # Convert string timestamp to datetime object
                    timestamp_obj = datetime.fromisoformat(timestamp)
                    absolute_timestamps.append(timestamp_obj)
                except Exception as e:
                    logger.error(f"Error parsing timestamp: {str(e)}")
                    if start_time_obj:
                        # If we have a start time, calculate relative timestamps
                        from datetime import timedelta
                        relative_seconds = len(processed_data['data_series']['timestamps'])
                        timestamp_obj = start_time_obj + timedelta(seconds=relative_seconds)
                        absolute_timestamps.append(timestamp_obj)
            elif isinstance(timestamp, datetime):
                # Already a datetime object
                absolute_timestamps.append(timestamp)
            elif start_time_obj:
                # Use start time + sequence index as fallback
                from datetime import timedelta
                relative_seconds = len(processed_data['data_series']['timestamps'])
                timestamp_obj = start_time_obj + timedelta(seconds=relative_seconds)
                absolute_timestamps.append(timestamp_obj)
            
            processed_data['data_series']['timestamps'].append(len(processed_data['data_series']['timestamps']))
            
            # Extract data metrics
            data = data_point.get('data', {})
            
            # If data is a string (serialized JSON), parse it
            if isinstance(data, str):
                try:
                    import json
                    data = json.loads(data)
                    logger.info(f"Successfully parsed data point from JSON string")
                except Exception as e:
                    logger.error(f"Error parsing data point JSON: {str(e)}")
                    data = {}  # Use empty dict if parsing fails
                    
            # Extract power - check different possible key names
            power = data.get('instant_power', data.get('instantaneous_power', data.get('power', 0)))
            processed_data['data_series']['powers'].append(power)
            
            # Extract cadence or stroke rate
            if processed_data['workout_type'] == 'bike':
                cadence = data.get('instant_cadence', data.get('instantaneous_cadence', data.get('cadence', 0)))
                processed_data['data_series']['cadences'].append(cadence)
            elif processed_data['workout_type'] == 'rower':
                stroke_rate = data.get('stroke_rate', 0)
                processed_data['data_series']['cadences'].append(stroke_rate)
                processed_data['data_series']['stroke_rates'].append(stroke_rate)
            
            # Extract heart rate
            heart_rate = data.get('heart_rate', 0)
            processed_data['data_series']['heart_rates'].append(heart_rate)
            
            # Extract speed
            speed = data.get('instant_speed', data.get('instantaneous_speed', data.get('speed', 0)))
            processed_data['data_series']['speeds'].append(speed)
            
            # Extract distance
            distance = data.get('total_distance', data.get('distance', 0))
            processed_data['data_series']['distances'].append(distance)
        
        # Add absolute timestamps to processed data
        processed_data['data_series']['absolute_timestamps'] = absolute_timestamps
        
        # Create FIT converter with output directory
        fit_output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'fit_files')
        os.makedirs(fit_output_dir, exist_ok=True)
        converter = FITConverter(fit_output_dir)
        
        # Log what we're sending to the converter for debugging
        logger.info(f"Converting workout {workout_id} to FIT file")
        logger.info(f"Workout type: {processed_data['workout_type']}")
        logger.info(f"Duration: {processed_data['total_duration']}")
        logger.info(f"Data points: {len(processed_data['data_series']['timestamps'])}")
        
        # Convert workout to FIT file
        fit_file_path = converter.convert_workout(processed_data, user_profile)
        
        if fit_file_path:
            fit_file_name = os.path.basename(fit_file_path)
            
            # Store FIT file path in workout record
            try:
                workout_manager.update_workout_fit_file(workout_id, fit_file_path)
            except Exception as e:
                logger.error(f"Error updating workout with FIT file path: {str(e)}")
            
            return jsonify({'success': True, 'fit_file_path': fit_file_path, 'fit_file_name': fit_file_name})
        else:
            logger.error(f"FIT conversion returned None for workout {workout_id}")
            return jsonify({'success': False, 'error': 'Failed to create FIT file'})
            
    except Exception as e:
        logger.error(f"Error converting workout to FIT: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)})

# Run the app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)