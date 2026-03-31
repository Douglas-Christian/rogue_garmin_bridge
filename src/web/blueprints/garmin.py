#!/usr/bin/env python3
"""Blueprint for Garmin Connect authentication and FIT file upload."""

import os
import shutil
import threading

from flask import Blueprint, request, jsonify

from src.utils.logging_config import get_component_logger

logger = get_component_logger('garmin')

garmin_bp = Blueprint('garmin', __name__)

# OAuth token storage directory (gitignored)
TOKEN_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
    'src', 'data', 'garmin_tokens',
)

# Server-side MFA state (single-user app, in-memory is fine)
_pending_mfa = {'client': None, 'state': None}
_pending_mfa_lock = threading.Lock()


def _friendly_error(exc):
    """Return a readable error message for common Garmin HTTP errors."""
    msg = str(exc)
    if '429' in msg:
        return ('Too many login attempts — Garmin is rate-limiting this IP. '
                'Wait a few minutes, then try again.')
    if '401' in msg or '403' in msg:
        return 'Invalid username or password.'
    if '503' in msg or '502' in msg:
        return 'Garmin Connect is temporarily unavailable. Try again shortly.'
    return msg


def _get_authenticated_client():
    """Return a loaded garth Client if tokens are stored, else None."""
    if not os.path.exists(TOKEN_DIR):
        return None
    try:
        import garth
        client = garth.Client()
        client.load(TOKEN_DIR)
        if client.oauth2_token:
            return client
        return None
    except Exception as e:
        logger.warning("Could not load Garmin tokens: %s", e)
        return None


# ----- Status -----

@garmin_bp.route('/api/garmin/status', methods=['GET'])
def garmin_status():
    """Check whether valid Garmin Connect tokens are stored."""
    client = _get_authenticated_client()
    return jsonify({'success': True, 'connected': client is not None})


# ----- Auth -----

@garmin_bp.route('/api/garmin/connect', methods=['POST'])
def garmin_connect():
    """
    Phase 1 of authentication.

    POST body: {"username": "...", "password": "..."}

    Returns:
      {"success": true, "connected": true}          — authenticated, no MFA needed
      {"success": false, "status": "mfa_required"}  — MFA code needed (call /api/garmin/mfa)
      {"success": false, "error": "..."}             — failure
    """
    data = request.json or {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    if not username or not password:
        return jsonify({'success': False, 'error': 'Username and password are required.'})

    try:
        import garth
        client = garth.Client()
        oauth1, oauth2 = client.login(username, password, return_on_mfa=True)

        if oauth1 == 'needs_mfa':
            # oauth2 holds the server-side state dict needed to complete login
            with _pending_mfa_lock:
                _pending_mfa['client'] = client
                _pending_mfa['state'] = oauth2
            logger.info("Garmin auth: MFA required for %s", username)
            return jsonify({'success': False, 'status': 'mfa_required'})

        # No MFA — tokens are already set on client by login()
        os.makedirs(TOKEN_DIR, exist_ok=True)
        client.dump(TOKEN_DIR)
        logger.info("Garmin authenticated successfully for %s (no MFA)", username)
        return jsonify({'success': True, 'connected': True})

    except Exception as e:
        logger.error("Garmin connect error: %s", e, exc_info=True)
        return jsonify({'success': False, 'error': _friendly_error(e)})


@garmin_bp.route('/api/garmin/mfa', methods=['POST'])
def garmin_mfa():
    """
    Phase 2: complete MFA-protected authentication.

    POST body: {"mfa_code": "123456"}
    """
    data = request.json or {}
    mfa_code = data.get('mfa_code', '').strip()

    if not mfa_code:
        return jsonify({'success': False, 'error': 'MFA code is required.'})

    with _pending_mfa_lock:
        client = _pending_mfa.get('client')
        state = _pending_mfa.get('state')

    if not client or not state:
        return jsonify({
            'success': False,
            'error': 'No pending authentication session. Please enter your credentials again.',
        })

    try:
        client.resume_login(state, mfa_code)

        os.makedirs(TOKEN_DIR, exist_ok=True)
        client.dump(TOKEN_DIR)

        with _pending_mfa_lock:
            _pending_mfa['client'] = None
            _pending_mfa['state'] = None

        logger.info("Garmin MFA authentication completed successfully")
        return jsonify({'success': True, 'connected': True})

    except Exception as e:
        logger.error("Garmin MFA error: %s", e, exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Invalid MFA code or session expired. Please try connecting again.',
        })


@garmin_bp.route('/api/garmin/disconnect', methods=['POST'])
def garmin_disconnect():
    """Remove stored Garmin Connect tokens."""
    try:
        if os.path.exists(TOKEN_DIR):
            shutil.rmtree(TOKEN_DIR)

        with _pending_mfa_lock:
            _pending_mfa['client'] = None
            _pending_mfa['state'] = None

        logger.info("Garmin tokens removed")
        return jsonify({'success': True})
    except Exception as e:
        logger.error("Garmin disconnect error: %s", e)
        return jsonify({'success': False, 'error': str(e)})


# ----- Upload -----

@garmin_bp.route('/api/garmin/upload/<int:workout_id>', methods=['POST'])
def garmin_upload(workout_id):
    """
    Upload a workout's FIT file to Garmin Connect.
    Generates the FIT file first if it does not already exist.
    """
    if not _get_authenticated_client():
        return jsonify({
            'success': False,
            'error': 'Not connected to Garmin Connect. Please authenticate in Settings.',
        })

    success, error = _upload_workout_to_garmin(workout_id)
    if success:
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': error})


def _upload_workout_to_garmin(workout_id):
    """
    Upload a workout's FIT file to Garmin Connect.
    Returns (True, None) on success or (False, error_message) on failure.
    Safe to call from background threads — does not use Flask request context.
    """
    client = _get_authenticated_client()
    if not client:
        return False, 'Not connected to Garmin Connect'

    try:
        from src.web.app import workout_manager
        import json as _json
        from src.fit.fit_converter import FITConverter
        from src.web.helpers import fit_files_dir, load_json_file, profile_path

        workout = workout_manager.get_workout(workout_id)
        if not workout:
            return False, 'Workout not found'

        fit_path = workout.get('fit_file_path')

        # Generate FIT file if missing or file was deleted
        if not fit_path or not os.path.exists(fit_path):
            if 'summary' in workout and isinstance(workout.get('summary'), str):
                try:
                    workout['summary'] = _json.loads(workout['summary'])
                except Exception:
                    workout['summary'] = {}

            workout_data = workout_manager.get_workout_data(workout_id)
            user_profile = load_json_file(profile_path()) or None

            processed_data = _build_processed_data(workout, workout_data)

            output_dir = fit_files_dir()
            os.makedirs(output_dir, exist_ok=True)
            converter = FITConverter(output_dir)
            fit_path = converter.convert_workout(processed_data, user_profile)

            if not fit_path:
                return False, 'Failed to generate FIT file'

            workout_manager.update_workout_fit_file(workout_id, fit_path)

        logger.info("Uploading workout %d FIT file to Garmin Connect: %s", workout_id, fit_path)
        with open(fit_path, 'rb') as f:
            result = client.upload(f)

        logger.info("Garmin upload result for workout %d: %s", workout_id, result)
        return True, None

    except Exception as e:
        logger.error("Garmin upload error for workout %d: %s", workout_id, e, exc_info=True)
        return False, str(e)


def _build_processed_data(workout, workout_data):
    """Build processed_data dict from raw workout and data points (mirrors fit.py logic)."""
    from datetime import datetime, timedelta

    summary = workout.get('summary') or {}
    workout_type = workout.get('workout_type', 'bike')

    processed_data = {
        'workout_type': workout_type,
        'start_time': workout.get('start_time'),
        'total_duration': workout.get('duration', 0),
        'total_distance': summary.get('total_distance', 0),
        'total_calories': summary.get('total_calories', 0),
        'avg_power': summary.get('avg_power', 0),
        'max_power': summary.get('max_power', 0),
        'normalized_power': summary.get('normalized_power', 0),
        'avg_heart_rate': summary.get('avg_heart_rate', 0),
        'max_heart_rate': summary.get('max_heart_rate', 0),
        'avg_speed': summary.get('avg_speed', 0),
        'max_speed': summary.get('max_speed', 0),
        'data_series': {
            'timestamps': [],
            'powers': [],
            'cadences': [],
            'heart_rates': [],
            'speeds': [],
            'distances': [],
            'stroke_rates': [],
            'absolute_timestamps': [],
        },
    }

    if workout_type == 'bike':
        processed_data['avg_cadence'] = summary.get('avg_cadence', 0)
        processed_data['max_cadence'] = summary.get('max_cadence', 0)
    elif workout_type == 'rower':
        processed_data['avg_stroke_rate'] = summary.get('avg_stroke_rate', 0)
        processed_data['max_stroke_rate'] = summary.get('max_stroke_rate', 0)
        processed_data['total_strokes'] = summary.get('total_strokes', 0)

    start_time_obj = None
    if workout.get('start_time'):
        try:
            st = workout['start_time']
            start_time_obj = datetime.fromisoformat(st) if isinstance(st, str) else st
        except Exception:
            pass

    import json as _json
    for data_point in workout_data:
        timestamp = data_point.get('timestamp')
        if isinstance(timestamp, str):
            try:
                processed_data['data_series']['absolute_timestamps'].append(
                    datetime.fromisoformat(timestamp)
                )
            except Exception:
                if start_time_obj:
                    idx = len(processed_data['data_series']['timestamps'])
                    processed_data['data_series']['absolute_timestamps'].append(
                        start_time_obj + timedelta(seconds=idx)
                    )
        elif isinstance(timestamp, datetime):
            processed_data['data_series']['absolute_timestamps'].append(timestamp)
        elif start_time_obj:
            idx = len(processed_data['data_series']['timestamps'])
            processed_data['data_series']['absolute_timestamps'].append(
                start_time_obj + timedelta(seconds=idx)
            )

        processed_data['data_series']['timestamps'].append(
            len(processed_data['data_series']['timestamps'])
        )

        data = data_point.get('data', {})
        if isinstance(data, str):
            try:
                data = _json.loads(data)
            except Exception:
                data = {}

        processed_data['data_series']['powers'].append(
            data.get('instant_power', data.get('instantaneous_power', data.get('power', 0)))
        )
        processed_data['data_series']['heart_rates'].append(data.get('heart_rate', 0))
        processed_data['data_series']['speeds'].append(
            data.get('instant_speed', data.get('instantaneous_speed', data.get('speed', 0)))
        )
        processed_data['data_series']['distances'].append(
            data.get('total_distance', data.get('distance', 0))
        )

        if workout_type == 'bike':
            processed_data['data_series']['cadences'].append(
                data.get('instant_cadence', data.get('instantaneous_cadence', data.get('cadence', 0)))
            )
        elif workout_type == 'rower':
            sr = data.get('stroke_rate', 0)
            processed_data['data_series']['cadences'].append(sr)
            processed_data['data_series']['stroke_rates'].append(sr)

    return processed_data
