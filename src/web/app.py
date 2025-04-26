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
from datetime import datetime
from typing import Dict, List, Any, Optional

from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for

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
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('web_app')

# Create Flask app
app = Flask(__name__)

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
use_simulator = False

# Initialize components
def init_components():
    global ftms_manager, workout_manager, data_processor, fit_converter, garmin_uploader
    
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

# Handle FTMS status updates
def handle_ftms_status(status: str, data: Any):
    global device_status
    logger.info(f"FTMS status: {status}")
    device_status = status

# Handle FTMS data
def handle_ftms_data(data: Dict[str, Any]):
    logger.debug(f"FTMS data: {data}")
    # Data will be handled by workout manager

# Handle workout status updates
def handle_workout_status(status: str, data: Any):
    global current_workout_id
    logger.info(f"Workout status: {status}")
    
    if status == 'workout_started':
        current_workout_id = data.get('workout_id')
    elif status == 'workout_ended':
        current_workout_id = None

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
        
        return jsonify({'success': success})
    except Exception as e:
        logger.error(f"Error disconnecting from device: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/status')
def get_status():
    """Get current status."""
    global device_status, latest_data, current_workout_id
    
    return jsonify({
        'device_status': device_status,
        'workout_active': current_workout_id is not None,
        'workout_id': current_workout_id,
        'latest_data': latest_data
    })

@app.route('/api/start_workout', methods=['POST'])
def start_workout():
    """Start a new workout."""
    try:
        device_id = request.json.get('device_id')
        workout_type = request.json.get('workout_type', 'unknown')
        
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

# Run the app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)