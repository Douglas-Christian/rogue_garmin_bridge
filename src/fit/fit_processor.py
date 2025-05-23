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
        Structure workout data in the format expected by fit_converter.
        
        This method efficiently transforms data points into the exact structure
        needed by the fit_converter, avoiding redundant transformations.
        
        Args:
            workout: Workout metadata
            data_points: Workout data points
            
        Returns:
            Structured data for fit_converter
        """
        # Extract data series in a single pass
        # Use 'workout_type' as the field name instead of 'type'
        workout_type = workout.get('workout_type', 'bike')  # Default to 'bike' if not found
        data_series = self._extract_data_series(data_points, workout_type)
        
        # Get the summary from the workout metadata or calculate if not available
        summary = workout.get('summary', {})
        
        # Prepare the basic structure with required fields
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
            'max_heart_rate': 'max_heart_rate'
        }
        
        # Add common metrics from summary or calculate if not available
        for fit_key, db_key in metrics_mapping.items():
            structured_data[fit_key] = summary.get(db_key, 0)
        
        # Add workout type specific metrics
        if workout_type == 'bike':
            bike_metrics = {
                'avg_cadence': 'avg_cadence',
                'max_cadence': 'max_cadence',
                'avg_speed': 'avg_speed',
                'max_speed': 'max_speed'
            }
            for fit_key, db_key in bike_metrics.items():
                structured_data[fit_key] = summary.get(db_key, 0)
                
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
    
    def _extract_data_series(self, data_points: List[Dict[str, Any]], workout_type: str) -> Dict[str, List]:
        """
        Extract data series from data points in an optimized way.
        
        This method efficiently extracts all needed data series in a single pass through
        the data points, avoiding multiple iterations.
        
        Args:
            data_points: Workout data points
            workout_type: Type of workout (bike, rower)
            
        Returns:
            Dictionary of data series
        """
        # Initialize all series
        series = {
            'timestamps': [],
            'absolute_timestamps': [],
            'powers': [],
            'heart_rates': [],
            'distances': []
        }
        
        # Add workout type specific series
        if workout_type == 'bike':
            series.update({
                'cadences': [],
                'speeds': []
            })
        elif workout_type == 'rower':
            series.update({
                'stroke_rates': []
            })
        
        # Process all data points in a single pass
        start_time = data_points[0]['timestamp'] if data_points else None
        
        for point in data_points:
            # Handle timestamps
            abs_ts = point['timestamp']
            series['absolute_timestamps'].append(abs_ts)
            
            # Relative timestamp in seconds from start
            if start_time:
                rel_ts = (abs_ts - start_time).total_seconds()
                series['timestamps'].append(rel_ts)
            
            # Add common metrics
            series['powers'].append(point.get('instantaneous_power', 0))
            series['heart_rates'].append(point.get('heart_rate', 0))
            series['distances'].append(point.get('total_distance', 0))
            
            # Add workout type specific metrics
            if workout_type == 'bike':
                series['cadences'].append(point.get('instantaneous_cadence', 0))
                series['speeds'].append(point.get('instantaneous_speed', 0))
            elif workout_type == 'rower':
                series['stroke_rates'].append(point.get('stroke_rate', 0))
        
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