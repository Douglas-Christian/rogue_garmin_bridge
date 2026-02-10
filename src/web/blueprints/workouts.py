#!/usr/bin/env python3
"""Blueprint for workout lifecycle and history endpoints."""

import json
from flask import Blueprint, request, jsonify

from src.utils.logging_config import get_component_logger
from src.web.helpers import DeviceInfo

logger = get_component_logger('web.workouts')

workouts_bp = Blueprint('workouts', __name__)


def _get_managers():
    from src.web.app import ftms_manager, workout_manager, db
    return ftms_manager, workout_manager, db


# ----- Start / End -----

@workouts_bp.route('/api/start_workout', methods=['POST'])
def start_workout():
    """Start a new workout."""
    ftms_manager, workout_manager, _ = _get_managers()
    try:
        device_address = request.json.get('device_id')
        logger.info("Starting workout for device address: %s", device_address)

        if not device_address:
            return jsonify({'success': False, 'error': 'Device address is missing.'})

        device_id = None
        if hasattr(workout_manager.database, 'get_device_id_by_address'):
            device_id = workout_manager.database.get_device_id_by_address(device_address)
        else:
            try:
                conn = workout_manager.database._get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM devices WHERE address = ?", (device_address,))
                result = cursor.fetchone()
                device_id = result['id'] if result else None
            except Exception as db_error:
                logger.error("Error querying device by address: %s", db_error)

        if device_id is None:
            device_info = DeviceInfo.from_any(ftms_manager.connected_device)
            device_name = device_info.name if device_info else 'Unknown Device'

            dev_type = 'bike'
            if device_name and 'rower' in device_name.lower():
                dev_type = 'rower'

            device_id = workout_manager.database.add_device(
                address=device_address,
                name=device_name,
                device_type=dev_type,
                metadata={},
            )
            if device_id is None:
                return jsonify({'success': False, 'error': f'Failed to add device {device_address} to database.'})

        workout_type = request.json.get('workout_type', 'bike')
        workout_id = workout_manager.start_workout(device_id, workout_type)
        logger.info("Workout started with ID: %s", workout_id)
        return jsonify({'success': True, 'workout_id': workout_id})
    except Exception as e:
        logger.error("Error starting workout: %s", e, exc_info=True)
        return jsonify({'success': False, 'error': str(e)})


@workouts_bp.route('/api/end_workout', methods=['POST'])
def end_workout():
    """End the current workout."""
    _, workout_manager, _ = _get_managers()
    try:
        success = workout_manager.end_workout()
        return jsonify({'success': success})
    except Exception as e:
        logger.error("Error ending workout: %s", e)
        return jsonify({'success': False, 'error': str(e)})


# ----- History & Details -----

@workouts_bp.route('/api/workouts')
def get_workouts():
    """Get workout history."""
    _, workout_manager, db = _get_managers()
    try:
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)

        workouts = workout_manager.get_workouts(limit, offset)

        for workout in workouts:
            if 'summary' in workout:
                if isinstance(workout['summary'], str):
                    try:
                        workout['summary'] = json.loads(workout['summary'])
                    except Exception:
                        workout['summary'] = {}
                elif workout['summary'] is None:
                    workout['summary'] = {}
            else:
                workout['summary'] = {}

        if not workouts:
            logger.warning("No workouts found in database")
            return jsonify({'success': True, 'workouts': []})

        return jsonify({'success': True, 'workouts': workouts})
    except Exception as e:
        logger.error("Error getting workouts: %s", e, exc_info=True)
        return jsonify({'success': False, 'error': str(e)})


@workouts_bp.route('/api/workout/<int:workout_id>', methods=['GET', 'DELETE'])
def workout_operations(workout_id):
    """Get or delete workout details."""
    _, workout_manager, _ = _get_managers()
    try:
        if request.method == 'DELETE':
            success = workout_manager.delete_workout(workout_id)
            return jsonify({'success': success})

        # GET — full workout with data series
        workout = workout_manager.get_workout(workout_id)
        if not workout:
            return jsonify({'success': False, 'error': 'Workout not found'})

        workout_data = workout_manager.get_workout_data(workout_id)

        timestamps, powers, cadences, heart_rates, speeds, distances = [], [], [], [], [], []
        for dp in workout_data:
            data = dp.get('data', {})
            timestamps.append(dp.get('timestamp', 0))
            powers.append(data.get('instant_power', data.get('instantaneous_power', data.get('power', 0))))
            cadences.append(data.get('instant_cadence', data.get('instantaneous_cadence', data.get('cadence', 0))))
            heart_rates.append(data.get('heart_rate', 0))
            speeds.append(data.get('instant_speed', data.get('instantaneous_speed', data.get('speed', 0))))
            distances.append(data.get('total_distance', data.get('distance', 0)))

        if hasattr(workout, 'keys'):
            workout = dict(workout)

        if 'summary' in workout and workout['summary']:
            if isinstance(workout['summary'], str):
                try:
                    workout['summary'] = json.loads(workout['summary'])
                except Exception:
                    pass

        workout['data_series'] = {
            'timestamps': timestamps,
            'powers': powers,
            'cadences': cadences,
            'heart_rates': heart_rates,
            'speeds': speeds,
            'distances': distances,
        }

        for key, values in workout['data_series'].items():
            if key != 'timestamps':
                try:
                    workout['data_series'][key] = [float(v) if v is not None else 0 for v in values]
                except (ValueError, TypeError):
                    pass

        workout['data_point_count'] = len(workout_data)

        # Fill in missing summary metrics
        if 'summary' in workout and workout['summary']:
            summary = workout['summary']
            if 'avg_cadence' not in summary and cadences:
                non_none = list(filter(None, cadences))
                summary['avg_cadence'] = sum(non_none) / len(non_none) if non_none else 0
            if 'avg_power' not in summary and powers:
                non_none = list(filter(None, powers))
                summary['avg_power'] = sum(non_none) / len(non_none) if non_none else 0
            if 'avg_speed' not in summary and speeds:
                non_none = list(filter(None, speeds))
                summary['avg_speed'] = sum(non_none) / len(non_none) if non_none else 0

        return jsonify({'success': True, 'workout': workout})
    except Exception as e:
        logger.error("Error in workout operations: %s", e, exc_info=True)
        return jsonify({'success': False, 'error': str(e)})
