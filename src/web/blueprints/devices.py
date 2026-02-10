#!/usr/bin/env python3
"""Blueprint for device discovery, connection, and status endpoints."""

import asyncio
from flask import Blueprint, request, jsonify

from src.utils.logging_config import get_component_logger
from src.web.helpers import DeviceInfo

logger = get_component_logger('web.devices')

devices_bp = Blueprint('devices', __name__)


def _get_managers():
    """Lazily import the shared managers initialised in app.py."""
    from src.web.app import ftms_manager, workout_manager, background_loop
    return ftms_manager, workout_manager, background_loop


# ----- Discovery -----

@devices_bp.route('/api/discover', methods=['POST'])
def discover_devices():
    """Discover FTMS devices."""
    ftms_manager, _, background_loop = _get_managers()

    logger.debug(
        "/api/discover called. background_loop is %s. Loop running: %s",
        'set' if background_loop else 'None',
        background_loop.is_running() if background_loop else 'N/A',
    )
    try:
        if not background_loop or not background_loop.is_running():
            logger.error("Asyncio background loop is not running.")
            return jsonify({'success': False, 'error': 'Asyncio loop not running'})

        future = asyncio.run_coroutine_threadsafe(ftms_manager.discover_devices(), background_loop)
        devices_dict = future.result(timeout=10)

        serializable_devices = []
        if isinstance(devices_dict, dict):
            for address, dev_info in devices_dict.items():
                name = None
                if hasattr(dev_info, 'name'):
                    name = dev_info.name
                elif isinstance(dev_info, dict) and 'name' in dev_info:
                    name = dev_info['name']

                if name and address:
                    serializable_devices.append({'name': name, 'address': address})
                else:
                    logger.warning("Could not serialize device with address %s: %s", address, dev_info)
        else:
            logger.warning("discover_devices returned unexpected type: %s", type(devices_dict))

        return jsonify({'success': True, 'devices': serializable_devices})
    except asyncio.TimeoutError:
        logger.error("Device discovery timed out.")
        return jsonify({'success': False, 'error': 'Device discovery timed out'})
    except Exception as e:
        logger.error("Error discovering devices: %s", e, exc_info=True)
        return jsonify({'success': False, 'error': str(e)})


# ----- Connect / Disconnect -----

@devices_bp.route('/api/connect', methods=['POST'])
def connect_device():
    """Connect to an FTMS device."""
    ftms_manager, _, background_loop = _get_managers()

    device_address = request.json.get('address')
    device_type = request.json.get('device_type', 'auto')
    logger.debug(
        "/api/connect called for %s with device_type %s.", device_address, device_type,
    )
    try:
        if not device_address:
            return jsonify({'success': False, 'error': 'Device address is required'})

        if not background_loop or not background_loop.is_running():
            logger.error("Asyncio background loop is not running.")
            return jsonify({'success': False, 'error': 'Asyncio loop not running'})

        logger.info("Scheduling connect task for %s (device_type: %s).", device_address, device_type)
        future = asyncio.run_coroutine_threadsafe(
            ftms_manager.connect(device_address, device_type), background_loop,
        )
        success = future.result(timeout=40)
        logger.info("Connect task for %s completed with result: %s", device_address, success)
        return jsonify({'success': success})
    except asyncio.TimeoutError:
        logger.error("Connection to %s timed out.", device_address)
        return jsonify({'success': False, 'error': 'Connection timed out'})
    except Exception as e:
        logger.error("Error connecting to device %s: %s", device_address, e, exc_info=True)
        return jsonify({'success': False, 'error': str(e)})


@devices_bp.route('/api/disconnect', methods=['POST'])
def disconnect_device():
    """Disconnect from the current FTMS device."""
    ftms_manager, _, background_loop = _get_managers()

    try:
        if not background_loop or not background_loop.is_running():
            logger.error("Asyncio background loop is not running.")
            return jsonify({'success': False, 'error': 'Asyncio loop not running'})

        logger.info("Scheduling disconnect task on the background loop.")
        future = asyncio.run_coroutine_threadsafe(ftms_manager.disconnect(), background_loop)
        success = future.result(timeout=10)
        logger.info("Disconnect task completed with result: %s", success)
        return jsonify({'success': success})
    except asyncio.TimeoutError:
        logger.error("Device disconnection timed out.")
        return jsonify({'success': False, 'error': 'Disconnection timed out'})
    except Exception as e:
        logger.error("Error disconnecting from device: %s", e, exc_info=True)
        return jsonify({'success': False, 'error': str(e)})


# ----- Status -----

@devices_bp.route('/api/status')
def get_status():
    """Get current device + workout status."""
    ftms_manager, workout_manager, _ = _get_managers()

    logger.debug("FTMS Manager device_status: %s", ftms_manager.device_status)
    logger.debug("Workout Manager active_workout_id: %s", workout_manager.active_workout_id)

    device_info = DeviceInfo.from_any(ftms_manager.connected_device)
    connected_device_dict = device_info.to_dict() if device_info else None
    device_name = device_info.name if device_info else None

    status = {
        'device_status': ftms_manager.device_status,
        'connected_device': connected_device_dict,
        'connected_device_address': getattr(ftms_manager, 'connected_device_address', None),
        'device_name': device_name,
        'workout_active': workout_manager.active_workout_id is not None,
        'is_simulated': ftms_manager.use_simulator,
    }

    if hasattr(ftms_manager, 'latest_data') and ftms_manager.latest_data:
        latest_data = ftms_manager.latest_data.copy()
        if workout_manager.active_workout_id:
            latest_data['workout_id'] = workout_manager.active_workout_id
            try:
                summary = workout_manager.get_workout_summary_metrics()
                if summary:
                    latest_data['workout_summary'] = summary
            except Exception as e:
                logger.error("Error getting workout summary: %s", e)
        status['latest_data'] = latest_data

    return jsonify(status)
