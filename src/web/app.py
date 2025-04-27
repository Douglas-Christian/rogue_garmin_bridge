#!/usr/bin/env python3
"""
Web Application for Rogue to Garmin Bridge

This module provides a Flask web application for the Rogue to Garmin Bridge,
allowing users to connect to Rogue Echo equipment, view workout data,
and convert/upload workouts to Garmin Connect.
"""

import os
import json
import asyncio
import threading
import logging
import secrets
import argparse
from datetime import datetime
from typing import Dict, List, Any, Optional

from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, session

# Import project modules
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ftms.ftms_manager import FTMSDeviceManager
from data.workout_manager import WorkoutManager
from data.data_processor import DataProcessor
from fit.fit_converter import FITConverter
from fit.garmin_uploader import GarminUploader

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Change from INFO to DEBUG
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('web_app')

# Parse command line arguments
parser = argparse.ArgumentParser(description='Start the Rogue Garmin Bridge web application')
parser.add_argument('--use-simulator', action='store_true', help='Use simulated devices instead of real ones')
args = parser.parse_args()

# Create Flask app
app = Flask(__name__)
app.secret_key = secrets.token_hex(16)  # Generate a secure secret key for sessions
app.config['SESSION_TYPE'] = 'filesystem'  # Use filesystem session storage for persistence
app.config['SESSION_PERMANENT'] = True     # Make sessions persistent

# Configuration
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'rogue_garmin.db')
FIT_OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'fit_files')

# Create output directories if they don't exist
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
os.makedirs(FIT_OUTPUT_DIR, exist_ok=True)

# Initialize components
ftms_manager = None
workout_manager = None
data_processor = None
fit_converter = None
garmin_uploader = None

# Global state
current_workout_id = None
current_device_id = None
latest_data = {}
device_status = "disconnected"
use_simulator = args.use_simulator  # Use the command line argument value
is_simulation_running = False  # Track if a simulation is running
connected_device_address = None  # Track the connected device address
connected_device_name = None  # Track the connected device name

# Initialize components
def init_components():
    global ftms_manager, workout_manager, data_processor, fit_converter, garmin_uploader, device_status
    
    # Create FTMS manager
    ftms_manager = FTMSDeviceManager(use_simulator=use_simulator)
    
    # Create workout manager
    workout_manager = WorkoutManager(DB_PATH, ftms_manager)
    
    # Create data processor
    data_processor = DataProcessor()
    
    # Create FIT converter
    fit_converter = FITConverter(FIT_OUTPUT_DIR)
    
    # Create Garmin uploader
    garmin_uploader = GarminUploader()
    
    # Register callbacks
    ftms_manager.register_status_callback(handle_ftms_status)
    ftms_manager.register_data_callback(handle_ftms_data)
    workout_manager.register_status_callback(handle_workout_status)
    workout_manager.register_data_callback(handle_workout_data)
    
    # Load user profile
    user_profile = workout_manager.get_user_profile()
    if user_profile:
        data_processor.set_user_profile(user_profile)
    
    # Reset connection status
    device_status = "disconnected"
    
    logger.info(f"Components initialized. Simulator mode: {use_simulator}")

# Handle FTMS status updates
def handle_ftms_status(status: str, data: Any):
    global device_status, connected_device_address, connected_device_name, is_simulation_running
    logger.info(f"FTMS status: {status}")
    
    if status == "connected" and hasattr(data, "address"):
        # Update global state
        device_status = "connected"
        connected_device_address = data.address
        connected_device_name = data.name if hasattr(data, "name") else "Unknown Device"
        is_simulation_running = use_simulator
        
        # Store in session with explicit commit
        session['device_status'] = device_status
        session['connected_device_address'] = connected_device_address
        session['connected_device_name'] = connected_device_name
        session['is_simulation_running'] = is_simulation_running
        session.modified = True
        
        logger.info(f"Device connected and stored in session: {connected_device_name} ({connected_device_address})")
    elif status == "disconnected":
        # Update global state
        device_status = "disconnected"
        connected_device_address = None
        connected_device_name = None
        is_simulation_running = False
        
        # Clear from session with explicit commit
        session['device_status'] = "disconnected"
        session.pop('connected_device_address', None)
        session.pop('connected_device_name', None)
        session.pop('is_simulation_running', None)
        session.modified = True
        
        logger.info("Device disconnected, session updated")
    elif status == "machine_status":
        # This is an important status to log but doesn't change our connection state
        logger.info(f"Machine status update received: {data}")
        # Re-trigger the connected status to ensure UI consistency
        if connected_device_address:
            session['device_status'] = "connected"
            session.modified = True

# Handle FTMS data
def handle_ftms_data(data: Dict[str, Any]):
    global latest_data
    logger.debug(f"FTMS data received: {data}")
    # Store the data directly in latest_data so it's available for status API calls
    latest_data = data
    # The rest of the data handling is done by workout_manager via its own callback

# Handle workout status updates
def handle_workout_status(status: str, data: Any):
    global current_workout_id
    logger.info(f"Workout status: {status}")
    
    if status == 'workout_started':
        current_workout_id = data.get('workout_id')
        session['current_workout_id'] = current_workout_id
        session.modified = True
    elif status == 'workout_ended':
        current_workout_id = None
        session.pop('current_workout_id', None)
        session.modified = True

# Handle workout data
def handle_workout_data(data: Dict[str, Any]):
    global latest_data
    logger.debug(f"Workout data: {data}")
    latest_data = data

# Run async tasks in a separate thread
def run_async_task(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)

# Initialize components on startup
init_components()

# Basic session management to maintain device connections 
@app.before_request
def check_device_connection():
    global connected_device_address, connected_device_name, device_status
    
    # Skip for static file requests
    if request.path.startswith('/static/'):
        return
    
    # Log request path for debugging
    logger.info(f"Request for {request.path}")
    
    # Get device connection info from session
    stored_device_address = session.get('connected_device_address')
    stored_device_name = session.get('connected_device_name')
    stored_device_status = session.get('device_status')
    
    # Simple connection state update from session
    if stored_device_status == "connected" and stored_device_address:
        # Keep global state in sync with session
        if connected_device_address != stored_device_address or device_status != "connected":
            logger.info(f"Updating connection state from session for {stored_device_name} ({stored_device_address})")
            connected_device_address = stored_device_address
            connected_device_name = stored_device_name
            device_status = "connected"

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
        # Run device discovery in a separate thread
        devices = run_async_task(ftms_manager.discover_devices())
        
        # Convert devices to a serializable format
        device_list = []
        for addr, device in devices.items():
            device_list.append({
                'address': addr,
                'name': device.name if hasattr(device, 'name') else 'Unknown',
                'rssi': device.rssi if hasattr(device, 'rssi') else 0
            })
        
        return jsonify({'success': True, 'devices': device_list})
    except Exception as e:
        logger.error(f"Error discovering devices: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/connect', methods=['POST'])
def connect_device():
    """Connect to an FTMS device."""
    try:
        device_address = request.json.get('address')
        if not device_address:
            return jsonify({'success': False, 'error': 'Device address is required'})
        
        # Connect to device in a separate thread
        success = run_async_task(ftms_manager.connect(device_address))
        
        return jsonify({'success': success})
    except Exception as e:
        logger.error(f"Error connecting to device: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/disconnect', methods=['POST'])
def disconnect_device():
    """Disconnect from the current FTMS device."""
    try:
        # Disconnect from device in a separate thread
        success = run_async_task(ftms_manager.disconnect())
        
        # Clear session data
        session.pop('connected_device_address', None)
        session.pop('connected_device_name', None)
        session.pop('is_simulation_running', None)
        session['device_status'] = "disconnected"
        session.modified = True
        
        return jsonify({'success': success})
    except Exception as e:
        logger.error(f"Error disconnecting from device: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/status')
def get_status():
    """Get current status."""
    global device_status, latest_data, current_workout_id, connected_device_address, connected_device_name
    
    # Log current values for debugging
    logger.info(f"Status request - Current state: status={device_status}, device={connected_device_name}")
    
    # Check session values for consistency
    stored_status = session.get('device_status', 'disconnected')
    stored_address = session.get('connected_device_address')
    stored_name = session.get('connected_device_name')
    
    # If session shows connected but our globals don't, update globals from session
    if stored_status == 'connected' and stored_address and (device_status != 'connected' or not connected_device_address):
        logger.info(f"Updating connection state from session: {stored_name} ({stored_address})")
        device_status = 'connected'
        connected_device_address = stored_address
        connected_device_name = stored_name
    
    # Build status response
    status = {
        'device_status': device_status,
        'device_name': connected_device_name,
        'workout_active': current_workout_id is not None,
        'workout_id': current_workout_id,
        'connected_device_address': connected_device_address,
        'is_simulated': use_simulator and connected_device_address is not None
    }
    
    # Include latest data if available
    if latest_data and isinstance(latest_data, dict):
        # Make a copy to avoid modifying the original
        status['latest_data'] = latest_data.copy()
        
        # If device info not in latest_data but we have it globally, add it
        if 'device_name' not in status['latest_data'] and connected_device_name:
            status['latest_data']['device_name'] = connected_device_name
        if 'device_address' not in status['latest_data'] and connected_device_address:
            status['latest_data']['device_address'] = connected_device_address
    else:
        status['latest_data'] = {}
    
    return jsonify(status)

@app.route('/api/start_workout', methods=['POST'])
def start_workout():
    """Start a new workout."""
    try:
        device_id = request.json.get('device_id')
        
        # Determine workout type based on connected device if not provided
        workout_type = request.json.get('workout_type')
        if not workout_type and connected_device_name:
            # Determine workout type from device name
            if 'bike' in connected_device_name.lower():
                workout_type = 'bike'
            elif 'rower' in connected_device_name.lower():
                workout_type = 'rower'
            else:
                workout_type = 'bike'  # Default to bike if we can't determine
            logger.info(f"Determined workout type from device name: {workout_type}")
        elif not workout_type:
            workout_type = 'bike'  # Default to bike if we can't determine
        
        if not device_id:
            # Get the first device from the database
            devices = workout_manager.get_devices()
            if devices:
                device_id = devices[0]['id']
            else:
                return jsonify({'success': False, 'error': 'No devices available'})
        
        # Start workout
        workout_id = workout_manager.start_workout(device_id, workout_type)
        
        return jsonify({'success': True, 'workout_id': workout_id})
    except Exception as e:
        logger.error(f"Error starting workout: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/end_workout', methods=['POST'])
def end_workout():
    """End the current workout."""
    try:
        workout_id = request.json.get('workout_id', current_workout_id)
        
        if not workout_id:
            return jsonify({'success': False, 'error': 'No active workout'})
        
        # End workout
        success = workout_manager.end_workout(workout_id)
        
        return jsonify({'success': success})
    except Exception as e:
        logger.error(f"Error ending workout: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/workouts')
def get_workouts():
    """Get workout history."""
    try:
        limit = request.args.get('limit', 10, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Get workouts
        workouts = workout_manager.get_workouts(limit, offset)
        
        return jsonify({'success': True, 'workouts': workouts})
    except Exception as e:
        logger.error(f"Error getting workouts: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/workout/<int:workout_id>')
def get_workout(workout_id):
    """Get workout details."""
    try:
        # Get workout
        workout = workout_manager.get_workout(workout_id)
        
        if not workout:
            return jsonify({'success': False, 'error': 'Workout not found'})
        
        # Get workout data
        data = workout_manager.get_workout_data(workout_id)
        
        # Process workout data
        start_time = datetime.fromisoformat(workout['start_time']) if workout.get('start_time') else datetime.now()
        processed_data = data_processor.process_workout_data(
            [d['data'] for d in data],
            workout['workout_type'],
            start_time
        )
        
        # Estimate VO2 max
        vo2max = data_processor.estimate_vo2max(processed_data)
        if vo2max:
            processed_data['vo2max'] = vo2max
        
        return jsonify({
            'success': True,
            'workout': workout,
            'processed_data': processed_data
        })
    except Exception as e:
        logger.error(f"Error getting workout details: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/convert_fit/<int:workout_id>', methods=['POST'])
def convert_to_fit(workout_id):
    """Convert workout to FIT file."""
    try:
        # Get workout
        workout = workout_manager.get_workout(workout_id)
        
        if not workout:
            return jsonify({'success': False, 'error': 'Workout not found'})
        
        # Get workout data
        data = workout_manager.get_workout_data(workout_id)
        
        # Process workout data
        start_time = datetime.fromisoformat(workout['start_time']) if workout.get('start_time') else datetime.now()
        processed_data = data_processor.process_workout_data(
            [d['data'] for d in data],
            workout['workout_type'],
            start_time
        )
        
        # Get user profile
        user_profile = workout_manager.get_user_profile()
        
        # Convert to FIT
        fit_file_path = fit_converter.convert_workout(processed_data, user_profile)
        
        if not fit_file_path:
            return jsonify({'success': False, 'error': 'Failed to create FIT file'})
        
        # Update workout with FIT file path
        workout_manager.database.end_workout(workout_id, fit_file_path=fit_file_path)
        
        return jsonify({
            'success': True,
            'fit_file_path': fit_file_path,
            'fit_file_name': os.path.basename(fit_file_path)
        })
    except Exception as e:
        logger.error(f"Error converting workout to FIT: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/download_fit/<int:workout_id>')
def download_fit(workout_id):
    """Download FIT file for a workout."""
    try:
        # Get workout
        workout = workout_manager.get_workout(workout_id)
        
        if not workout:
            return jsonify({'success': False, 'error': 'Workout not found'})
        
        fit_file_path = workout.get('fit_file_path')
        
        if not fit_file_path or not os.path.exists(fit_file_path):
            # Try to create FIT file
            return redirect(url_for('convert_to_fit', workout_id=workout_id))
        
        # Send file
        return send_file(
            fit_file_path,
            as_attachment=True,
            download_name=os.path.basename(fit_file_path)
        )
    except Exception as e:
        logger.error(f"Error downloading FIT file: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/upload_garmin/<int:workout_id>', methods=['POST'])
def upload_to_garmin(workout_id):
    """Upload workout to Garmin Connect."""
    try:
        # Get workout
        workout = workout_manager.get_workout(workout_id)
        
        if not workout:
            return jsonify({'success': False, 'error': 'Workout not found'})
        
        fit_file_path = workout.get('fit_file_path')
        
        if not fit_file_path or not os.path.exists(fit_file_path):
            # Try to create FIT file
            result = convert_to_fit(workout_id)
            result_data = json.loads(result.get_data(as_text=True))
            
            if not result_data.get('success'):
                return jsonify({'success': False, 'error': 'Failed to create FIT file'})
            
            fit_file_path = result_data.get('fit_file_path')
        
        # Get user profile for Garmin credentials
        user_profile = workout_manager.get_user_profile()
        
        if not user_profile or not user_profile.get('garmin_username') or not user_profile.get('garmin_password'):
            return jsonify({'success': False, 'error': 'Garmin Connect credentials not configured'})
        
        # Authenticate with Garmin Connect
        auth_success = garmin_uploader.authenticate(
            user_profile.get('garmin_username'),
            user_profile.get('garmin_password')
        )
        
        if not auth_success:
            return jsonify({'success': False, 'error': 'Failed to authenticate with Garmin Connect'})
        
        # Upload FIT file
        upload_success, activity_id = garmin_uploader.upload_fit_file(fit_file_path)
        
        if not upload_success:
            return jsonify({'success': False, 'error': 'Failed to upload to Garmin Connect'})
        
        # Mark workout as uploaded
        workout_manager.database.mark_workout_uploaded(workout_id)
        
        return jsonify({
            'success': True,
            'activity_id': activity_id
        })
    except Exception as e:
        logger.error(f"Error uploading to Garmin Connect: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/user_profile', methods=['GET', 'POST'])
def user_profile():
    """Get or update user profile."""
    if request.method == 'GET':
        try:
            # Get user profile
            profile = workout_manager.get_user_profile()
            
            if not profile:
                return jsonify({'success': True, 'profile': {}})
            
            # Remove sensitive data
            if 'garmin_password' in profile:
                profile['garmin_password'] = '********' if profile['garmin_password'] else ''
            
            return jsonify({'success': True, 'profile': profile})
        except Exception as e:
            logger.error(f"Error getting user profile: {str(e)}")
            return jsonify({'success': False, 'error': str(e)})
    else:  # POST
        try:
            profile_data = request.json
            
            # Handle password
            if profile_data.get('garmin_password') == '********':
                # Password unchanged, get original from database
                current_profile = workout_manager.get_user_profile()
                if current_profile and current_profile.get('garmin_password'):
                    profile_data['garmin_password'] = current_profile['garmin_password']
            
            # Update user profile
            success = workout_manager.set_user_profile(profile_data)
            
            # Update data processor
            if success:
                data_processor.set_user_profile(profile_data)
            
            return jsonify({'success': success})
        except Exception as e:
            logger.error(f"Error updating user profile: {str(e)}")
            return jsonify({'success': False, 'error': str(e)})

@app.route('/api/settings', methods=['GET', 'POST'])
def app_settings():
    """Get or update application settings."""
    global use_simulator
    
    if request.method == 'GET':
        try:
            # Get settings
            settings = {
                'use_simulator': use_simulator
            }
            
            return jsonify({'success': True, 'settings': settings})
        except Exception as e:
            logger.error(f"Error getting settings: {str(e)}")
            return jsonify({'success': False, 'error': str(e)})
    else:  # POST
        try:
            settings_data = request.json
            
            # Update settings
            if 'use_simulator' in settings_data:
                use_simulator = settings_data['use_simulator']
                
                # Reinitialize components if simulator setting changed
                init_components()
            
            return jsonify({'success': True})
        except Exception as e:
            logger.error(f"Error updating settings: {str(e)}")
            return jsonify({'success': False, 'error': str(e)})

@app.route('/api/data/<int:workout_id>', methods=['GET'])
def get_workout_data(workout_id):
    """Get workout data points for a specific workout."""
    try:
        # Get workout data
        data = workout_manager.get_workout_data(workout_id)
        
        if not data:
            return jsonify({'success': False, 'error': 'No workout data found'})
        
        # Return raw data points
        return jsonify({
            'success': True,
            'workout_id': workout_id,
            'data_points': data
        })
    except Exception as e:
        logger.error(f"Error getting workout data: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

# Run the app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)