#!/usr/bin/env python3
"""
Flask web application for the Rogue Garmin Bridge.

This module handles application initialisation, manager wiring, the
background asyncio loop, and page-level template routes.  All API
endpoints live in dedicated blueprints under ``src.web.blueprints``.
"""

import os
import sys
import argparse
import asyncio
import threading

from flask import Flask, render_template

# Ensure the project root is on sys.path for absolute imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.data.workout_manager import WorkoutManager
from src.data.database import Database
from src.ftms.ftms_manager import FTMSDeviceManager
from src.utils.logging_config import get_component_logger

# ── Logging ─────────────────────────────────────────────────────────
logger = get_component_logger('web')

# ── Flask App ───────────────────────────────────────────────────────
app = Flask(__name__)

# ── CLI arguments (only when run directly) ──────────────────────────
use_simulator = False
device_type = 'bike'

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Start the Rogue Garmin Bridge web application')
    parser.add_argument('--use-simulator', action='store_true',
                        help='Use the FTMS device simulator instead of real devices')
    parser.add_argument('--device-type', default='bike', choices=['bike', 'rower'],
                        help='Type of device to simulate (bike or rower)')
    args = parser.parse_args()
    use_simulator = args.use_simulator
    device_type = args.device_type

# ── Core managers (shared with blueprints via lazy import) ──────────
db_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    'src', 'data', 'rogue_garmin.db',
)
db = Database(db_path)
workout_manager = WorkoutManager(db_path)

logger.info("Initializing FTMSDeviceManager with use_simulator=%s, device_type=%s",
            use_simulator, device_type)
ftms_manager = FTMSDeviceManager(workout_manager, use_simulator=use_simulator,
                                  device_type=device_type)

if use_simulator:
    logger.info("Using FTMS device simulator for %s", device_type)
else:
    logger.info("Using real FTMS devices")

logger.info("Flask application initialized. FTMS manager created.")

# ── Background asyncio loop ────────────────────────────────────────
background_loop = None
loop_thread = None


def start_asyncio_loop():
    """Start the asyncio event loop in a background thread."""
    global background_loop
    try:
        logger.info("Background thread started. Creating new event loop.")
        background_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(background_loop)
        logger.info("Starting background asyncio event loop run_forever.")
        background_loop.run_forever()
    except Exception as e:
        logger.error("Exception in background asyncio loop: %s", e, exc_info=True)
    finally:
        if background_loop and background_loop.is_running():
            logger.info("Stopping background asyncio event loop.")
            background_loop.stop()
        logger.info("Background asyncio loop finished.")
        background_loop = None


logger.info("Starting background asyncio loop thread...")
loop_thread = threading.Thread(target=start_asyncio_loop, daemon=True)
loop_thread.start()
logger.info("Background asyncio loop thread start initiated.")

# ── Register blueprints ────────────────────────────────────────────
from src.web.blueprints.devices import devices_bp       # noqa: E402
from src.web.blueprints.workouts import workouts_bp     # noqa: E402
from src.web.blueprints.fit import fit_bp               # noqa: E402
from src.web.blueprints.settings_bp import settings_bp  # noqa: E402
from src.web.blueprints.backup import backup_bp         # noqa: E402

app.register_blueprint(devices_bp)
app.register_blueprint(workouts_bp)
app.register_blueprint(fit_bp)
app.register_blueprint(settings_bp)
app.register_blueprint(backup_bp)

# ── Page routes (HTML templates) ───────────────────────────────────

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


# ── Entrypoint ─────────────────────────────────────────────────────
if __name__ == '__main__':
    debug = os.environ.get('FLASK_ENV', 'development') != 'production'
    app.run(host='0.0.0.0', port=5000, debug=debug)
