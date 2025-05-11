#!/usr/bin/env python3
"""
FIT Processor Module for Rogue to Garmin Bridge

This module handles the optimized conversion of workout data to FIT format.
"""

import logging
import os
from typing import Dict, List, Any, Optional
from datetime import datetime

from ..data.database import Database
from .fit_converter import FITConverter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('fit_processor')

class FITProcessor:
    """
    Efficiently processes and converts workout data to FIT format.
    """
    
    def __init__(self, db_path: str, fit_output_dir: str = None):
        """
        Initialize the FIT processor.
        
        Args:
            db_path: Path to the SQLite database file
            fit_output_dir: Directory to save FIT files (optional)
        """
        self.database = Database(db_path)
        
        # If fit_output_dir is not provided, use default directory
        if fit_output_dir is None:
            fit_output_dir = os.path.abspath(os.path.join(
                os.path.dirname(__file__), "..", "..", "fit_files"
            ))
        
        self.fit_converter = FITConverter(output_dir=fit_output_dir)
    
    def process_workout(self, workout_id: int, user_profile: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Process a workout and convert it to FIT format.
        
        Args:
            workout_id: ID of the workout to process
            user_profile: User profile information (optional)
            
        Returns:
            Path to the generated FIT file or None if processing failed
        """
        # 1. Get workout metadata
        workout = self.database.get_workout(workout_id)
        if not workout:
            logger.error(f"Workout {workout_id} not found")
            return None
        
        # 2. Get workout data points using an optimized database query
        data_points = self.database.get_workout_data_optimized(workout_id)
        if not data_points:
            logger.error(f"No data points found for workout {workout_id}")
            return None
        
        # 3. Prepare data in the structure expected by fit_converter
        processed_data = self._structure_data_for_fit(workout, data_points)
        
        # 4. Convert to FIT file
        fit_file_path = self.fit_converter.convert_workout(processed_data, user_profile)
        
        # 5. Update workout record with FIT file path
        if fit_file_path:
            self.database.update_workout_fit_path(workout_id, fit_file_path)
            logger.info(f"Successfully created FIT file for workout {workout_id}: {fit_file_path}")
        else:
            logger.error(f"Failed to create FIT file for workout {workout_id}")
        
        return fit_file_path
    
    def process_all_workouts(self, limit: int = None, user_profile: Optional[Dict[str, Any]] = None) -> List[str]:
        """
        Process multiple workouts and convert them to FIT format.
        
        Args:
            limit: Maximum number of workouts to process (optional)
            user_profile: User profile information (optional)
            
        Returns:
            List of paths to the generated FIT files
        """
        # Get workouts without FIT files
        workouts = self.database.get_workouts_without_fit_files(limit)
        
        fit_files = []
        for workout in workouts:
            fit_file_path = self.process_workout(workout['id'], user_profile)
            if fit_file_path:
                fit_files.append(fit_file_path)
        
        return fit_files
    
    def _structure_data_for_fit(self, workout: Dict[str, Any], data_points: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Structure workout data for FIT converter.
        
        Args:
            workout: Workout metadata
            data_points: List of workout data points
            
        Returns:
            Structured data for FIT converter
        """
        # Extract workout type
        workout_type = workout.get('workout_type', 'bike')
        
        # Extract data series
        data_series = self._extract_data_series(workout_type, data_points)
        
        # If summary exists in workout as string, parse it
        summary = {}
        if 'summary' in workout:
            if isinstance(workout['summary'], str):
                try:
                    import json
                    summary = json.loads(workout['summary'])
                except Exception as e:
                    logger.error(f"Error parsing summary JSON: {str(e)}")
            else:
                summary = workout['summary']
        
        # Create structured data
        structured_data = {
            'workout_type': workout_type,
            'start_time': workout['start_time'],
            'total_duration': workout.get('duration', 0),
            'data_series': data_series
        }
        
        # Add summary metrics
        metrics_mapping = {
            'total_distance': 'total_distance',
            'total_calories': 'total_calories',
            'avg_power': 'avg_power',
            'max_power': 'max_power',
            'avg_heart_rate': 'avg_heart_rate',
            'max_heart_rate': 'max_heart_rate',
            'estimated_vo2max': 'estimated_vo2max'  # Add VO2max mapping
        }
        
        # Add common metrics from summary or calculate if not available
        for fit_key, db_key in metrics_mapping.items():
            structured_data[fit_key] = summary.get(db_key, 0)
        
        # Add workout type specific metrics
        if workout_type == 'bike':
            bike_metrics = {
                'avg_cadence': 'avg_cadence',
                'max_cadence': 'max_cadence',
                'max_speed': 'max_speed'
            }
            for fit_key, db_key in bike_metrics.items():
                structured_data[fit_key] = summary.get(db_key, 0)
                
            # For avg_speed, always use the calculated value from the summary
            # This ensures we ignore the incorrect Echo bike reported value
            structured_data['avg_speed'] = summary.get('avg_speed', 0)
            
            # If we don't have a valid average speed in the summary, calculate it from data points
            if structured_data['avg_speed'] <= 0 and data_series.get('speeds'):
                valid_speeds = [s for s in data_series['speeds'] if s > 0]
                if valid_speeds:
                    structured_data['avg_speed'] = sum(valid_speeds) / len(valid_speeds)
                    logger.info(f"Calculated average speed for FIT file: {structured_data['avg_speed']} km/h")
                
        elif workout_type == 'rower':
            rower_metrics = {
                'avg_cadence': 'avg_stroke_rate',
                'max_cadence': 'max_stroke_rate',
                'total_strokes': 'total_strokes'
            }
            for fit_key, db_key in rower_metrics.items():
                structured_data[fit_key] = summary.get(db_key, 0)
        
        # Calculate normalized power if not in summary
        if 'normalized_power' not in structured_data and len(data_series.get('powers', [])) > 0:
            powers = data_series['powers']
            if powers and any(powers):
                # Simple estimation of normalized power (fourth-root of mean of fourth powers)
                # This is a simplified algorithm - real implementation may be more complex
                non_zero_powers = [p for p in powers if p > 0]
                if non_zero_powers:
                    fourth_powers = [p**4 for p in non_zero_powers]
                    mean_fourth_power = sum(fourth_powers) / len(fourth_powers)
                    structured_data['normalized_power'] = round(mean_fourth_power**(1/4), 0)
        
        return structured_data
    
    def _extract_data_series(self, workout_type: str, data_points: List[Dict[str, Any]]) -> Dict[str, List[Any]]:
        """
        Extract data series from data points for use in FIT file.
        
        Args:
            workout_type: Type of workout ('bike' or 'rower')
            data_points: List of data points
            
        Returns:
            Dictionary of data series
        """
        # Initialize data series with empty lists
        series = {
            'timestamps': [],
            'absolute_timestamps': [],
            'powers': [],
            'cadences': [],
            'speeds': [],
            'heart_rates': [],
            'distances': [],
            'stroke_rates': [],
            'average_powers': [],
            'average_cadences': [],
            'average_speeds': []
        }
        
        # Extract data for each timestamp
        for point in data_points:
            # Extract timestamp
            if 'timestamp' in point:
                # Store the relative timestamp (seconds from start)
                series['timestamps'].append(point['timestamp'])
                
                # If we have an absolute timestamp, store it too
                if 'absolute_timestamp' in point:
                    series['absolute_timestamps'].append(point['absolute_timestamp'])
            
            # Add common metrics - check multiple possible field names
            # For power, check various field names with fallback
            power = point.get('instant_power', 
                      point.get('instantaneous_power', 
                      point.get('power', 0)))
            # Ensure power is always included - very important!
            series['powers'].append(power if power is not None else 0)
            
            # For cadence, check various field names with fallback (moved outside workout_type check)
            cadence = point.get('instant_cadence', 
                       point.get('instantaneous_cadence', 
                       point.get('cadence', 0)))
            # Ensure cadence is always included
            series['cadences'].append(cadence if cadence is not None else 0)
            
            # For speed, check various field names with fallback (moved outside workout_type check)
            speed = point.get('instant_speed', 
                     point.get('instantaneous_speed', 
                     point.get('speed', 0)))
            # Ensure speed is always included
            series['speeds'].append(speed if speed is not None else 0)
            
            # Heart rate
            series['heart_rates'].append(point.get('heart_rate', 0) or 0)  # Convert None to 0
            
            # Distance
            series['distances'].append(point.get('total_distance', 0) or 0)  # Convert None to 0
            
            # Add average values for all workout types
            series['average_powers'].append(point.get('average_power', power) or 0)
            series['average_cadences'].append(point.get('average_cadence', cadence) or 0)
            
            # Skip device-reported average_speed and leave it for recalculation later
            # This ensures we don't use the incorrect values from the Echo bike
            series['average_speeds'].append(point.get('average_speed', 0) or 0)
            
            # Always add stroke rate (will be 0 for non-rowers)
            series['stroke_rates'].append(point.get('stroke_rate', 0) or 0)
        
        # Calculate the average speed ourselves if this is a bike workout
        if workout_type == 'bike' and series['speeds']:
            # Calculate a proper average speed from the instantaneous speed values
            valid_speeds = [s for s in series['speeds'] if s > 0]
            if valid_speeds:
                avg_calculated_speed = sum(valid_speeds) / len(valid_speeds)
                logger.info(f"Calculated average speed from {len(valid_speeds)} data points: {avg_calculated_speed} km/h")
                
                # Store this calculated average in the structured data for use in FIT file
                # We'll add it to the return value of _structure_data_for_fit in the next step
            else:
                logger.warning("No valid speed values found to calculate average speed")
        
        # Log some debug info about the data series
        logger.info(f"Extracted data series - points: {len(series['timestamps'])}, powers: {len(series['powers'])}, speeds: {len(series['speeds'])}, cadences: {len(series['cadences'])}")
        logger.debug(f"First 3 power values: {series['powers'][:3]}")
        logger.debug(f"First 3 speed values: {series['speeds'][:3]}")
        logger.debug(f"First 3 cadence values: {series['cadences'][:3]}")
        
        return series


# Example usage
if __name__ == "__main__":
    import sys
    import json
    
    # Get database path from command line or use default
    db_path = sys.argv[1] if len(sys.argv) > 1 else "../../src/data/rogue_garmin.db"
    db_path = os.path.abspath(db_path)
    
    # Get output directory from command line or use default
    fit_output_dir = sys.argv[2] if len(sys.argv) > 2 else "../../fit_files"
    fit_output_dir = os.path.abspath(fit_output_dir)
    
    # Create FIT processor
    processor = FITProcessor(db_path, fit_output_dir)
    
    # Get user profile
    user_profile_path = os.path.abspath("../../user_profile.json")
    user_profile = None
    if os.path.exists(user_profile_path):
        with open(user_profile_path, 'r') as f:
            user_profile = json.load(f)
    
    # Process all workouts without FIT files
    fit_files = processor.process_all_workouts(user_profile=user_profile)
    
    print(f"Processed {len(fit_files)} workouts:")
    for fit_file in fit_files:
        print(f"  - {fit_file}")