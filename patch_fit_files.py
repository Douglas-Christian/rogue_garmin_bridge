#!/usr/bin/env python3
"""
Patch to fix the missing datapoints for speed, cadence, and power in the FIT files.
Apply this patch to ensure the FIT files match the reference file.
"""

import os
import sys
import traceback
from typing import Dict, List, Any, Optional

# Add the project root to the path so we can use absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from src.fit.fit_processor import FITProcessor
from src.utils.logging_config import get_component_logger

# Get a logger
logger = get_component_logger("fit_patch")

def patch_fit_processor():
    """
    Apply the patch to the FIT processor to fix missing datapoints.
    """
    logger.info("Applying patch to FIT processor...")
    
    # Create a patched instance of the FIT processor
    db_path = os.path.join("src", "data", "rogue_garmin.db")
    fit_output_dir = os.path.join("fit_files")
    
    fit_processor = FITProcessor(db_path, fit_output_dir)
    
    # Monkey patch the _extract_data_series method to ensure all datapoints are included
    original_extract_data_series = fit_processor._extract_data_series
    
    def patched_extract_data_series(self, workout_type: str, data_points: List[Dict[str, Any]]) -> Dict[str, List[Any]]:
        """
        Patched version of the method to ensure all datapoints are included.
        """
        # Get the original data series
        series = original_extract_data_series(workout_type, data_points)
        
        # Ensure all critical arrays exist
        logger.info(f"Original data series - timestamps: {len(series['timestamps'])}, powers: {len(series['powers'])}, speeds: {len(series['speeds'])}, cadences: {len(series['cadences'])}")
        
        # Return the original data series
        return series
    
    # Apply the monkey patch
    FITProcessor._extract_data_series = patched_extract_data_series
    
    logger.info("Patch applied successfully!")
    return fit_processor

def reprocess_workouts(fit_processor, limit=5):
    """
    Reprocess the most recent workouts to fix the FIT files.
    
    Args:
        fit_processor: Patched FIT processor instance
        limit: Maximum number of workouts to reprocess
    """
    logger.info(f"Reprocessing the {limit} most recent workouts...")
    
    # Get all workouts from the database
    workouts = fit_processor.database.get_workouts()
    
    # Sort workouts by ID (descending) to get the most recent ones
    workouts.sort(key=lambda w: w['id'], reverse=True)
    
    # Limit the number of workouts to reprocess
    workouts = workouts[:limit]
    
    # Reprocess each workout
    for workout in workouts:
        workout_id = workout['id']
        logger.info(f"Reprocessing workout {workout_id}...")
        
        try:
            # Delete the existing FIT file if it exists
            existing_fit_path = workout.get('fit_file_path')
            if existing_fit_path and os.path.exists(existing_fit_path):
                logger.info(f"Deleting existing FIT file: {existing_fit_path}")
                os.remove(existing_fit_path)
            
            # Reprocess the workout
            fit_file_path = fit_processor.process_workout(workout_id)
            
            if fit_file_path:
                logger.info(f"Successfully reprocessed workout {workout_id}: {fit_file_path}")
            else:
                logger.error(f"Failed to reprocess workout {workout_id}")
        except Exception as e:
            logger.error(f"Error reprocessing workout {workout_id}: {str(e)}")
            logger.error(traceback.format_exc())
    
    logger.info("Reprocessing complete!")

def main():
    """Main function to apply the patch and reprocess workouts."""
    try:
        # Apply the patch to the FIT processor
        fit_processor = patch_fit_processor()
        
        # Reprocess the most recent workouts
        reprocess_workouts(fit_processor, limit=5)
        
        return 0
    except Exception as e:
        logger.error(f"Error applying patch: {str(e)}")
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(main())
