#!/usr/bin/env python3
"""
Test script to verify the fix for the FIT file timestamp issue
"""

import os
import sys
from datetime import datetime, timezone

# Add the project root to the path for imports
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.fit.fit_converter import FITConverter, create_file_id_message
from fit_tool.fit_file_builder import FitFileBuilder

# Set up logging
from src.utils.logging_config import get_component_logger
logger = get_component_logger('test_fit')

def test_file_id_creation():
    """Test that we can create a valid FileIdMessage"""
    logger.info("Testing FileIdMessage creation")
    
    # Create a builder
    builder = FitFileBuilder()
    
    # Test our fixed create_file_id_message function
    result = create_file_id_message(builder)
    
    logger.info(f"FileIdMessage creation result: {result}")
    return result

def test_full_fit_conversion():
    """Test a full workout conversion to FIT"""
    logger.info("Testing full FIT file conversion")
    
    # Create sample workout data
    workout_data = {
        'workout_type': 'bike',
        'start_time': datetime.now(timezone.utc),
        'total_duration': 60,
        'total_distance': 500,
        'total_calories': 50,
        'avg_power': 150,
        'max_power': 200,
        'normalized_power': 160,
        'avg_cadence': 80,
        'max_cadence': 100,
        'avg_heart_rate': 130,
        'max_heart_rate': 150,
        'avg_speed': 25,
        'max_speed': 30,
        'data_series': {
            'timestamps': [i for i in range(0, 61)],
            'powers': [150 for _ in range(61)],
            'cadences': [80 for _ in range(61)],
            'heart_rates': [130 for _ in range(61)],
            'speeds': [25 for _ in range(61)],
            'distances': [i * (500/60) for i in range(61)]
        }
    }
    
    # Create output directory if it doesn't exist
    os.makedirs("fit_files", exist_ok=True)
    
    # Create converter
    converter = FITConverter("fit_files")
    
    # Try to convert the workout
    fit_file_path = converter.convert_workout(workout_data)
    
    # Log result
    if fit_file_path:
        logger.info(f"Successfully created FIT file: {fit_file_path}")
        return True
    else:
        logger.error("Failed to create FIT file")
        return False

if __name__ == "__main__":
    # Test just the FileIdMessage creation
    file_id_result = test_file_id_creation()
    
    if file_id_result:
        logger.info("FileIdMessage creation succeeded! The fix is working.")
    else:
        logger.error("FileIdMessage creation failed! The fix did not work.")
        sys.exit(1)
    
    # Test a full workout conversion
    conversion_result = test_full_fit_conversion()
    
    if conversion_result:
        logger.info("Full FIT conversion succeeded! The fix is working end-to-end.")
    else:
        logger.error("Full FIT conversion failed! The fix did not solve all problems.")
        sys.exit(1)
    
    logger.info("All tests passed! The timestamp issue has been fixed.")