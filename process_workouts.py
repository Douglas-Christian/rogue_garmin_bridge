#!/usr/bin/env python3
"""
Process Workouts Utility

This script processes existing workouts to generate FIT files.
It can be used to:
1. Process a specific workout by ID
2. Process all workouts without FIT files
3. Regenerate FIT files for all workouts (with --force option)
"""

import os
import sys
import json
import argparse
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('process_workouts')

def load_user_profile() -> Optional[Dict[str, Any]]:
    """Load user profile from user_profile.json file."""
    profile_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "user_profile.json"))
    if not os.path.exists(profile_path):
        logger.warning(f"User profile not found at {profile_path}")
        return None
    
    try:
        with open(profile_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading user profile: {str(e)}")
        return None

def process_workouts(
    db_path: str, 
    workout_id: Optional[int] = None, 
    force: bool = False, 
    limit: Optional[int] = None
) -> List[str]:
    """
    Process workouts to generate FIT files.
    
    Args:
        db_path: Path to the SQLite database file
        workout_id: ID of a specific workout to process (optional)
        force: If True, regenerate FIT files even if they already exist
        limit: Maximum number of workouts to process (optional)
        
    Returns:
        List of paths to the generated FIT files
    """
    # Ensure the db_path is absolute
    db_path = os.path.abspath(db_path)
    
    # Define the output directory for FIT files
    fit_output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "fit_files"))
    os.makedirs(fit_output_dir, exist_ok=True)
    
    # Import here to avoid circular imports
    from src.fit.fit_processor import FITProcessor
    
    # Load user profile
    user_profile = load_user_profile()
    
    # Create FIT processor
    processor = FITProcessor(db_path, fit_output_dir)
    
    fit_files = []
    
    # Process a specific workout
    if workout_id is not None:
        logger.info(f"Processing workout ID: {workout_id}")
        fit_file_path = processor.process_workout(workout_id, user_profile)
        if fit_file_path:
            fit_files.append(fit_file_path)
            logger.info(f"Generated FIT file: {fit_file_path}")
    
    # Process all workouts without FIT files
    elif force:
        # Get all workouts (including those with FIT files)
        from src.data.database import Database
        db = Database(db_path)
        workouts = db.get_workouts(limit=999999 if limit is None else limit)
        
        logger.info(f"Processing all {len(workouts)} workouts (force mode)")
        
        for workout in workouts:
            workout_id = workout['id']
            logger.info(f"Processing workout ID: {workout_id}")
            
            fit_file_path = processor.process_workout(workout_id, user_profile)
            if fit_file_path:
                fit_files.append(fit_file_path)
                logger.info(f"Generated FIT file: {fit_file_path}")
    
    # Process all workouts without FIT files
    else:
        workouts = processor.database.get_workouts_without_fit_files(limit)
        
        if not workouts:
            logger.info("No workouts without FIT files found")
        else:
            logger.info(f"Processing {len(workouts)} workouts without FIT files")
            
            for workout in workouts:
                workout_id = workout['id']
                logger.info(f"Processing workout ID: {workout_id}")
                
                fit_file_path = processor.process_workout(workout_id, user_profile)
                if fit_file_path:
                    fit_files.append(fit_file_path)
                    logger.info(f"Generated FIT file: {fit_file_path}")
    
    return fit_files

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Process workouts to generate FIT files")
    parser.add_argument("--db", type=str, default="src/data/rogue_garmin.db", help="Path to the SQLite database file")
    parser.add_argument("--id", type=int, help="ID of a specific workout to process")
    parser.add_argument("--force", action="store_true", help="Regenerate FIT files even if they already exist")
    parser.add_argument("--limit", type=int, help="Maximum number of workouts to process")
    
    args = parser.parse_args()
    
    # Process workouts
    fit_files = process_workouts(
        db_path=args.db,
        workout_id=args.id,
        force=args.force,
        limit=args.limit
    )
    
    # Print summary
    if fit_files:
        print(f"\nProcessed {len(fit_files)} workouts:")
        for fit_file in fit_files:
            print(f"  - {fit_file}")
    else:
        print("\nNo FIT files were generated.")

if __name__ == "__main__":
    main()