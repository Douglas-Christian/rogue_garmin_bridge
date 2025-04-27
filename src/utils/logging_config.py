#!/usr/bin/env python3
"""
Centralized logging configuration for the Rogue Garmin Bridge application.

This module provides a consistent logging configuration across all components
of the application, including:
- Console logging for development
- File-based logging with rotation for production use
- Structured logging format for easier analysis
- Component-specific loggers for better categorization
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from pathlib import Path

# Base directory for logs
LOG_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../logs'))

# Ensure log directory exists
Path(LOG_DIR).mkdir(exist_ok=True, parents=True)

# Log file paths
MAIN_LOG_FILE = os.path.join(LOG_DIR, 'rogue_garmin_bridge.log')
ERROR_LOG_FILE = os.path.join(LOG_DIR, 'error.log')
DATA_FLOW_LOG_FILE = os.path.join(LOG_DIR, 'data_flow.log')
WEB_LOG_FILE = os.path.join(LOG_DIR, 'web.log')
BLE_LOG_FILE = os.path.join(LOG_DIR, 'bluetooth.log')
WORKOUT_LOG_FILE = os.path.join(LOG_DIR, 'workout.log')

# Max log file size (10 MB)
MAX_LOG_SIZE = 10 * 1024 * 1024
# Number of backup logs to keep
BACKUP_COUNT = 5

# Flag to indicate if logging has been configured
_logging_configured = False

# Format string for logs
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
# More detailed format for debugging
DEBUG_LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(pathname)s:%(lineno)d - %(message)s'

def configure_logging(debug=False):
    """
    Configure the global logging settings for the application.
    
    Args:
        debug: Whether to enable debug logging
    """
    global _logging_configured
    
    if _logging_configured:
        return
    
    # Set the format based on debug mode
    log_format = DEBUG_LOG_FORMAT if debug else LOG_FORMAT
    formatter = logging.Formatter(log_format)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if debug else logging.INFO)
    
    # Clear any existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.DEBUG if debug else logging.INFO)
    root_logger.addHandler(console_handler)
    
    # Main log file handler with rotation
    file_handler = RotatingFileHandler(
        MAIN_LOG_FILE, 
        maxBytes=MAX_LOG_SIZE, 
        backupCount=BACKUP_COUNT
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG if debug else logging.INFO)
    root_logger.addHandler(file_handler)
    
    # Error log file handler
    error_handler = RotatingFileHandler(
        ERROR_LOG_FILE, 
        maxBytes=MAX_LOG_SIZE, 
        backupCount=BACKUP_COUNT
    )
    error_handler.setFormatter(formatter)
    error_handler.setLevel(logging.ERROR)
    root_logger.addHandler(error_handler)
    
    # Create component-specific log handlers
    _configure_component_handlers(formatter, debug)
    
    # Mark logging as configured
    _logging_configured = True
    
    # Log startup message
    logging.info(f"Logging initialized at {datetime.now().isoformat()}")
    if debug:
        logging.info("Debug logging enabled")
    
    logging.info(f"Log files located at: {LOG_DIR}")

def _configure_component_handlers(formatter, debug):
    """
    Configure handlers for specific components.
    
    Args:
        formatter: Log formatter to use
        debug: Whether debug mode is enabled
    """
    # Data flow logging
    data_flow_handler = RotatingFileHandler(
        DATA_FLOW_LOG_FILE, 
        maxBytes=MAX_LOG_SIZE, 
        backupCount=BACKUP_COUNT
    )
    data_flow_handler.setFormatter(formatter)
    data_flow_handler.setLevel(logging.DEBUG if debug else logging.INFO)
    
    # Web logging
    web_handler = RotatingFileHandler(
        WEB_LOG_FILE, 
        maxBytes=MAX_LOG_SIZE, 
        backupCount=BACKUP_COUNT
    )
    web_handler.setFormatter(formatter)
    web_handler.setLevel(logging.DEBUG if debug else logging.INFO)
    
    # BLE logging
    ble_handler = RotatingFileHandler(
        BLE_LOG_FILE, 
        maxBytes=MAX_LOG_SIZE, 
        backupCount=BACKUP_COUNT
    )
    ble_handler.setFormatter(formatter)
    ble_handler.setLevel(logging.DEBUG if debug else logging.INFO)
    
    # Workout logging
    workout_handler = RotatingFileHandler(
        WORKOUT_LOG_FILE, 
        maxBytes=MAX_LOG_SIZE, 
        backupCount=BACKUP_COUNT
    )
    workout_handler.setFormatter(formatter)
    workout_handler.setLevel(logging.DEBUG if debug else logging.INFO)
    
    # Add handlers to component loggers
    component_handlers = {
        'data_flow': data_flow_handler,
        'web': web_handler,
        'ftms': ble_handler,
        'bluetooth': ble_handler,
        'workout_manager': workout_handler,
        'database': data_flow_handler,
        'fit_converter': data_flow_handler,
        'garmin_uploader': data_flow_handler,
    }
    
    for component, handler in component_handlers.items():
        logger = logging.getLogger(component)
        logger.addHandler(handler)
        # Make sure component loggers propagate to root logger as well
        logger.propagate = True

def get_component_logger(component_name):
    """
    Get a logger for a specific component.
    
    Args:
        component_name: Name of the component
        
    Returns:
        Logger instance for the component
    """
    # Make sure logging is configured
    if not _logging_configured:
        configure_logging()
    
    return logging.getLogger(component_name)

# Configure logging when the module is imported
configure_logging()