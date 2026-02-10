#!/usr/bin/env python3
"""Blueprint for backup, restore, export, storage info, and cleanup endpoints."""

import csv
import io
import json
import math
import os
import glob as glob_mod
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify

from src.utils.logging_config import get_component_logger
from src.web.helpers import (
    project_path, profile_path, settings_path,
    load_json_file, save_json_file, fit_files_dir,
)

logger = get_component_logger('web.backup')

backup_bp = Blueprint('backup', __name__)


def _get_managers():
    from src.web.app import workout_manager, db
    return workout_manager, db


# ----- Helpers -----

def _format_size(size_bytes: int) -> str:
    if size_bytes == 0:
        return '0 B'
    size_names = ['B', 'KB', 'MB', 'GB']
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f'{s} {size_names[i]}'


# ----- Storage Info -----

@backup_bp.route('/api/storage_info')
def get_storage_info():
    """Get storage information for data management."""
    workout_manager, db = _get_managers()
    try:
        db_size = os.path.getsize(db.db_path) if os.path.exists(db.db_path) else 0
        workout_count = len(workout_manager.get_workouts(limit=10000) or [])

        log_dir = project_path('logs')
        log_size = 0
        for lf in glob_mod.glob(os.path.join(log_dir, '*.log')):
            if os.path.exists(lf):
                log_size += os.path.getsize(lf)

        fdir = fit_files_dir()
        fit_count = 0
        if os.path.exists(fdir):
            fit_count = len([f for f in os.listdir(fdir) if f.endswith('.fit')])

        return jsonify({
            'success': True,
            'storage': {
                'database_size': _format_size(db_size),
                'workout_count': workout_count,
                'log_size': _format_size(log_size),
                'fit_files_count': fit_count,
            },
        })
    except Exception as e:
        logger.error("Error getting storage info: %s", e)
        return jsonify({'success': False, 'error': str(e)})


# ----- Backup / Restore -----

@backup_bp.route('/api/backup', methods=['POST'])
def create_backup():
    """Create a backup of all user data."""
    workout_manager, _ = _get_managers()
    try:
        from flask import current_app

        backup_data = {
            'created_at': datetime.now().isoformat(),
            'version': '1.0',
            'user_profile': load_json_file(profile_path()),
            'settings': load_json_file(settings_path()),
            'workouts': [],
            'workout_data': [],
        }

        workouts = workout_manager.get_workouts(limit=10000) or []
        backup_data['workouts'] = workouts

        for workout in workouts:
            wd = workout_manager.get_workout_data(workout['id'])
            backup_data['workout_data'].append({'workout_id': workout['id'], 'data': wd})

        response = current_app.response_class(
            response=json.dumps(backup_data, indent=2),
            status=200,
            mimetype='application/json',
        )
        response.headers['Content-Disposition'] = (
            f'attachment; filename=rogue-garmin-backup-{datetime.now().strftime("%Y%m%d")}.json'
        )
        return response
    except Exception as e:
        logger.error("Error creating backup: %s", e)
        return jsonify({'success': False, 'error': str(e)})


@backup_bp.route('/api/restore', methods=['POST'])
def restore_backup():
    """Restore data from a backup file."""
    try:
        if 'backup_file' not in request.files:
            return jsonify({'success': False, 'error': 'No backup file provided'})

        file = request.files['backup_file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'})

        backup_data = json.loads(file.read().decode('utf-8'))

        if 'version' not in backup_data or 'created_at' not in backup_data:
            return jsonify({'success': False, 'error': 'Invalid backup file format'})

        if backup_data.get('user_profile'):
            save_json_file(profile_path(), backup_data['user_profile'])

        if backup_data.get('settings'):
            save_json_file(settings_path(), backup_data['settings'])

        return jsonify({'success': True, 'message': 'Backup restored successfully'})
    except Exception as e:
        logger.error("Error restoring backup: %s", e)
        return jsonify({'success': False, 'error': str(e)})


# ----- Export -----

@backup_bp.route('/api/export')
def export_data():
    """Export workout data in various formats."""
    workout_manager, _ = _get_managers()
    try:
        from flask import current_app

        format_type = request.args.get('format', 'json')
        date_range = request.args.get('date_range', 'all')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        workouts = workout_manager.get_workouts(limit=10000) or []

        if date_range != 'all':
            now = datetime.now()
            days_map = {'last-30': 30, 'last-90': 90, 'last-year': 365}
            if date_range in days_map:
                cutoff = now - timedelta(days=days_map[date_range])
                workouts = [w for w in workouts if datetime.fromisoformat(w['start_time']) >= cutoff]
            elif date_range == 'custom' and start_date and end_date:
                start = datetime.fromisoformat(start_date)
                end = datetime.fromisoformat(end_date)
                workouts = [w for w in workouts if start <= datetime.fromisoformat(w['start_time']) <= end]

        if format_type == 'json':
            response = current_app.response_class(
                response=json.dumps(workouts, indent=2),
                status=200,
                mimetype='application/json',
            )
            response.headers['Content-Disposition'] = f'attachment; filename=workout-data-{date_range}.json'

        elif format_type == 'csv':
            output = io.StringIO()
            if workouts:
                writer = csv.DictWriter(output, fieldnames=workouts[0].keys())
                writer.writeheader()
                writer.writerows(workouts)
            response = current_app.response_class(
                response=output.getvalue(),
                status=200,
                mimetype='text/csv',
            )
            response.headers['Content-Disposition'] = f'attachment; filename=workout-data-{date_range}.csv'
        else:
            return jsonify({'success': False, 'error': 'Unsupported export format'})

        return response
    except Exception as e:
        logger.error("Error exporting data: %s", e)
        return jsonify({'success': False, 'error': str(e)})


# ----- Cleanup -----

@backup_bp.route('/api/cleanup/<cleanup_type>', methods=['POST'])
def cleanup_data(cleanup_type):
    """Clean up old files and data."""
    try:
        files_removed = 0

        if cleanup_type == 'logs':
            log_dir = project_path('logs')
            cutoff_time = datetime.now() - timedelta(days=30)
            for lf in glob_mod.glob(os.path.join(log_dir, '*.log')):
                if os.path.exists(lf):
                    file_time = datetime.fromtimestamp(os.path.getmtime(lf))
                    if file_time < cutoff_time:
                        os.remove(lf)
                        files_removed += 1
        elif cleanup_type == 'temp':
            for td in (project_path('temp'), project_path('cache')):
                if os.path.exists(td):
                    for tf in glob_mod.glob(os.path.join(td, '*')):
                        if os.path.isfile(tf):
                            os.remove(tf)
                            files_removed += 1

        return jsonify({'success': True, 'files_removed': files_removed})
    except Exception as e:
        logger.error("Error during cleanup: %s", e)
        return jsonify({'success': False, 'error': str(e)})
