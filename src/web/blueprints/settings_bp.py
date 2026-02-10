#!/usr/bin/env python3
"""Blueprint for application settings and user profile endpoints."""

import json
from flask import Blueprint, request, jsonify

from src.utils.logging_config import get_component_logger
from src.web.helpers import (
    settings_path, profile_path,
    load_json_file, save_json_file,
)

logger = get_component_logger('web.settings')

settings_bp = Blueprint('settings', __name__)


def _get_managers():
    from src.web.app import ftms_manager
    return ftms_manager


# ----- Settings -----

@settings_bp.route('/api/settings', methods=['GET', 'POST'])
def api_settings():
    """Get or update application settings."""
    ftms_manager = _get_managers()
    try:
        path = settings_path()

        if request.method == 'POST':
            new_settings = request.json
            existing = load_json_file(path)
            existing.update(new_settings)
            save_json_file(path, existing)

            if 'use_simulator' in new_settings:
                ftms_manager.use_simulator = new_settings['use_simulator']

            return jsonify({'success': True})
        else:
            settings = load_json_file(path, default={'use_simulator': False})
            return jsonify({'success': True, 'settings': settings})
    except Exception as e:
        logger.error("Error processing settings: %s", e)
        return jsonify({'success': False, 'error': str(e)})


# ----- User Profile -----

@settings_bp.route('/api/user_profile', methods=['GET', 'POST'])
def api_user_profile():
    """Get or update user profile."""
    try:
        path = profile_path()

        if request.method == 'POST':
            new_profile = request.json
            existing = load_json_file(path)
            existing.update(new_profile)
            save_json_file(path, existing)
            return jsonify({'success': True})
        else:
            profile = load_json_file(path)
            return jsonify({'success': True, 'profile': profile})
    except Exception as e:
        logger.error("Error processing user profile: %s", e)
        return jsonify({'success': False, 'error': str(e)})
