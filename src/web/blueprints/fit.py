#!/usr/bin/env python3
"""Blueprint for FIT file conversion, listing, and download endpoints."""

import os
import json
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, send_from_directory

from src.utils.logging_config import get_component_logger
from src.web.helpers import fit_files_dir, profile_path, load_json_file, is_safe_path

logger = get_component_logger('web.fit')

fit_bp = Blueprint('fit', __name__)


def _get_managers():
    from src.web.app import workout_manager
    return workout_manager


# ----- Conversion -----

@fit_bp.route('/api/convert_fit/<int:workout_id>', methods=['POST'])
def convert_workout_to_fit(workout_id):
    """Convert workout to FIT file and return the file path."""
    workout_manager = _get_managers()
    try:
        from src.fit.fit_converter import FITConverter

        workout = workout_manager.get_workout(workout_id)
        if not workout:
            return jsonify({'success': False, 'error': 'Workout not found'})

        if 'summary' in workout and isinstance(workout.get('summary'), str):
            try:
                workout['summary'] = json.loads(workout['summary'])
            except Exception:
                workout['summary'] = {}

        workout_data = workout_manager.get_workout_data(workout_id)

        user_profile = load_json_file(profile_path()) or None

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
                'stroke_rates': [],
            },
        }

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
                'max_speed': summary.get('max_speed', 0),
            })
            if processed_data['workout_type'] == 'bike':
                processed_data.update({
                    'avg_cadence': summary.get('avg_cadence', 0),
                    'max_cadence': summary.get('max_cadence', 0),
                })
            elif processed_data['workout_type'] == 'rower':
                processed_data.update({
                    'avg_stroke_rate': summary.get('avg_stroke_rate', 0),
                    'max_stroke_rate': summary.get('max_stroke_rate', 0),
                    'total_strokes': summary.get('total_strokes', 0),
                })

        # Build absolute timestamps
        absolute_timestamps = []
        start_time_obj = None
        if workout.get('start_time'):
            try:
                st = workout['start_time']
                start_time_obj = datetime.fromisoformat(st) if isinstance(st, str) else st
            except Exception as e:
                logger.error("Error parsing start time: %s", e)

        for data_point in workout_data:
            timestamp = data_point.get('timestamp')
            if isinstance(timestamp, str):
                try:
                    absolute_timestamps.append(datetime.fromisoformat(timestamp))
                except Exception:
                    if start_time_obj:
                        idx = len(processed_data['data_series']['timestamps'])
                        absolute_timestamps.append(start_time_obj + timedelta(seconds=idx))
            elif isinstance(timestamp, datetime):
                absolute_timestamps.append(timestamp)
            elif start_time_obj:
                idx = len(processed_data['data_series']['timestamps'])
                absolute_timestamps.append(start_time_obj + timedelta(seconds=idx))

            processed_data['data_series']['timestamps'].append(
                len(processed_data['data_series']['timestamps'])
            )

            data = data_point.get('data', {})
            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except Exception:
                    data = {}

            power = data.get('instant_power', data.get('instantaneous_power', data.get('power', 0)))
            processed_data['data_series']['powers'].append(power)

            if processed_data['workout_type'] == 'bike':
                cadence = data.get('instant_cadence', data.get('instantaneous_cadence', data.get('cadence', 0)))
                processed_data['data_series']['cadences'].append(cadence)
            elif processed_data['workout_type'] == 'rower':
                stroke_rate = data.get('stroke_rate', 0)
                processed_data['data_series']['cadences'].append(stroke_rate)
                processed_data['data_series']['stroke_rates'].append(stroke_rate)

            processed_data['data_series']['heart_rates'].append(data.get('heart_rate', 0))

            speed = data.get('instant_speed', data.get('instantaneous_speed', data.get('speed', 0)))
            processed_data['data_series']['speeds'].append(speed)

            distance = data.get('total_distance', data.get('distance', 0))
            processed_data['data_series']['distances'].append(distance)

        processed_data['data_series']['absolute_timestamps'] = absolute_timestamps

        output_dir = fit_files_dir()
        os.makedirs(output_dir, exist_ok=True)
        converter = FITConverter(output_dir)

        logger.info(
            "Converting workout %d to FIT — type=%s, duration=%s, points=%d",
            workout_id, processed_data['workout_type'],
            processed_data['total_duration'],
            len(processed_data['data_series']['timestamps']),
        )

        fit_file_path = converter.convert_workout(processed_data, user_profile)

        if fit_file_path:
            fit_file_name = os.path.basename(fit_file_path)
            try:
                workout_manager.update_workout_fit_file(workout_id, fit_file_path)
            except Exception as e:
                logger.error("Error updating workout with FIT file path: %s", e)
            return jsonify({'success': True, 'fit_file_path': fit_file_path, 'fit_file_name': fit_file_name})
        else:
            logger.error("FIT conversion returned None for workout %d", workout_id)
            return jsonify({'success': False, 'error': 'Failed to create FIT file'})
    except Exception as e:
        logger.error("Error converting workout to FIT: %s", e, exc_info=True)
        return jsonify({'success': False, 'error': str(e)})


# ----- Serving / Download -----

@fit_bp.route('/fit_files/<path:filename>')
def serve_fit_file(filename):
    """Serve FIT files from the fit_files directory."""
    output_dir = fit_files_dir()
    logger.info("Serving FIT file: %s from %s", filename, output_dir)
    return send_from_directory(output_dir, filename, as_attachment=True)


@fit_bp.route('/api/download_fit/<path:filename>')
def download_fit_file(filename):
    """Download FIT file via API endpoint."""
    try:
        output_dir = fit_files_dir()
        if not is_safe_path(output_dir, filename):
            logger.warning("Path traversal attempt blocked: %s", filename)
            return jsonify({'success': False, 'error': 'Invalid filename'}), 400

        file_path = os.path.realpath(os.path.join(output_dir, filename))
        if not os.path.exists(file_path):
            logger.warning("FIT file not found: %s", filename)
            return jsonify({'success': False, 'error': 'File not found'}), 404

        logger.info("Downloading FIT file: %s", filename)
        return send_from_directory(output_dir, filename, as_attachment=True)
    except Exception as e:
        logger.error("Error downloading FIT file %s: %s", filename, e)
        return jsonify({'success': False, 'error': str(e)}), 500


# ----- Listing -----

@fit_bp.route('/api/fit_files')
def list_fit_files():
    """List available FIT files."""
    try:
        output_dir = fit_files_dir()
        if not os.path.exists(output_dir):
            return jsonify({'success': True, 'files': []})

        files = []
        for fn in os.listdir(output_dir):
            if fn.endswith('.fit'):
                fp = os.path.join(output_dir, fn)
                stat = os.stat(fp)
                files.append({'filename': fn, 'size': stat.st_size, 'modified': stat.st_mtime})

        files.sort(key=lambda x: x['modified'], reverse=True)
        return jsonify({'success': True, 'files': files})
    except Exception as e:
        logger.error("Error listing FIT files: %s", e)
        return jsonify({'success': False, 'error': str(e)})
