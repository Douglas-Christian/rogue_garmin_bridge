#!/usr/bin/env python3
"""
Data Processor Module for Rogue to Garmin Bridge

This module processes raw data from FTMS devices into a format suitable for storage and export.
"""

import os
import sys
import json
from typing import Dict, List, Any, Optional

# Add the project root to the path so we can use absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.utils.logging_config import get_component_logger

# Get component logger
logger = get_component_logger('data_flow')

class DataProcessor:
    """
    Processes raw FTMS data into a structured format for storage and analysis.
    Handles data normalization, unit conversion, and validation.
    """
    
    def __init__(self, user_profile: Optional[Dict[str, Any]] = None):
        """
        Initialize the data processor.
        
        Args:
            user_profile: User profile information (optional)
        """
        self.user_profile = user_profile or {}
    
    def set_user_profile(self, user_profile: Dict[str, Any]) -> None:
        """
        Set user profile information.
        
        Args:
            user_profile: User profile dictionary
        """
        self.user_profile = user_profile
    
    def process_workout_data(self, workout_data: List[Dict[str, Any]], 
                            workout_type: str) -> Dict[str, Any]:
        """
        Process raw workout data to prepare for FIT file conversion.
        
        Args:
            workout_data: List of workout data points
            workout_type: Type of workout (bike, rower, etc.)
            
        Returns:
            Dictionary of processed workout data
        """
        if not workout_data:
            logger.warning("No workout data to process")
            return {}
        
        # Sort data by timestamp
        workout_data = sorted(workout_data, key=lambda x: x.get('timestamp', 0))
        
        # Process based on workout type
        if workout_type == 'bike':
            return self._process_bike_data(workout_data)
        elif workout_type == 'rower':
            return self._process_rower_data(workout_data)
        else:
            logger.warning(f"Unknown workout type: {workout_type}")
            return {}
    
    def _process_bike_data(self, workout_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Process bike workout data.
        
        Args:
            workout_data: List of bike workout data points
            
        Returns:
            Dictionary of processed bike workout data
        """
        # Extract relevant data series
        timestamps = []
        powers = []
        cadences = []
        heart_rates = []
        speeds = []
        distances = []
        
        for data_point in workout_data:
            timestamp = data_point.get('timestamp', 0)
            timestamps.append(timestamp)
            
            # Extract power data
            power = data_point.get('instantaneous_power', data_point.get('power', 0))
            powers.append(power)
            
            # Extract cadence data
            cadence = data_point.get('instantaneous_cadence', data_point.get('cadence', 0))
            cadences.append(cadence)
            
            # Extract heart rate data
            heart_rate = data_point.get('heart_rate', 0)
            heart_rates.append(heart_rate)
            
            # Extract speed data
            speed = data_point.get('instantaneous_speed', data_point.get('speed', 0))
            speeds.append(speed)
            
            # Extract distance data
            distance = data_point.get('total_distance', data_point.get('distance', 0))
            distances.append(distance)
        
        # Calculate derived metrics
        total_duration = max(timestamps) if timestamps else 0
        avg_power = sum(powers) / len(powers) if powers else 0
        max_power = max(powers) if powers else 0
        avg_cadence = sum(cadences) / len(cadences) if cadences else 0
        max_cadence = max(cadences) if cadences else 0
        avg_heart_rate = sum(heart_rates) / len(heart_rates) if heart_rates else 0
        max_heart_rate = max(heart_rates) if heart_rates else 0
        avg_speed = sum(speeds) / len(speeds) if speeds else 0
        max_speed = max(speeds) if speeds else 0
        total_distance = max(distances) if distances else 0
        
        # Calculate calories if not provided
        total_calories = self._calculate_calories_bike(
            avg_power, total_duration, workout_data[-1].get('total_energy', 0)
        )
        
        # Calculate training effect metrics
        training_stress_score = self._calculate_tss(powers, timestamps)
        intensity_factor = self._calculate_intensity_factor(avg_power)
        normalized_power = self._calculate_normalized_power(powers)
        
        # Prepare processed data
        processed_data = {
            'workout_type': 'bike',
            'total_duration': total_duration,
            'total_distance': total_distance,
            'total_calories': total_calories,
            'avg_power': avg_power,
            'max_power': max_power,
            'normalized_power': normalized_power,
            'avg_cadence': avg_cadence,
            'max_cadence': max_cadence,
            'avg_heart_rate': avg_heart_rate,
            'max_heart_rate': max_heart_rate,
            'avg_speed': avg_speed,
            'max_speed': max_speed,
            'training_stress_score': training_stress_score,
            'intensity_factor': intensity_factor,
            'data_series': {
                'timestamps': timestamps,
                'powers': powers,
                'cadences': cadences,
                'heart_rates': heart_rates,
                'speeds': speeds,
                'distances': distances
            }
        }
        
        return processed_data
    
    def _process_rower_data(self, workout_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Process rower workout data.
        
        Args:
            workout_data: List of rower workout data points
            
        Returns:
            Dictionary of processed rower workout data
        """
        # Extract relevant data series
        timestamps = []
        powers = []
        stroke_rates = []
        heart_rates = []
        distances = []
        stroke_counts = []
        
        for data_point in workout_data:
            timestamp = data_point.get('timestamp', 0)
            timestamps.append(timestamp)
            
            # Extract power data
            power = data_point.get('instantaneous_power', data_point.get('power', 0))
            powers.append(power)
            
            # Extract stroke rate data
            stroke_rate = data_point.get('stroke_rate', 0)
            stroke_rates.append(stroke_rate)
            
            # Extract heart rate data
            heart_rate = data_point.get('heart_rate', 0)
            heart_rates.append(heart_rate)
            
            # Extract distance data
            distance = data_point.get('total_distance', data_point.get('distance', 0))
            distances.append(distance)
            
            # Extract stroke count data
            stroke_count = data_point.get('stroke_count', 0)
            stroke_counts.append(stroke_count)
        
        # Calculate derived metrics
        total_duration = max(timestamps) if timestamps else 0
        avg_power = sum(powers) / len(powers) if powers else 0
        max_power = max(powers) if powers else 0
        avg_stroke_rate = sum(stroke_rates) / len(stroke_rates) if stroke_rates else 0
        max_stroke_rate = max(stroke_rates) if stroke_rates else 0
        avg_heart_rate = sum(heart_rates) / len(heart_rates) if heart_rates else 0
        max_heart_rate = max(heart_rates) if heart_rates else 0
        total_distance = max(distances) if distances else 0
        total_strokes = max(stroke_counts) if stroke_counts else 0
        
        # Calculate calories if not provided
        total_calories = self._calculate_calories_rower(
            avg_power, total_duration, workout_data[-1].get('total_energy', 0)
        )
        
        # Calculate pace (time per 500m)
        avg_pace = self._calculate_pace(total_distance, total_duration)
        
        # Calculate training effect metrics
        training_stress_score = self._calculate_tss(powers, timestamps)
        intensity_factor = self._calculate_intensity_factor(avg_power)
        normalized_power = self._calculate_normalized_power(powers)
        
        # Prepare processed data
        processed_data = {
            'workout_type': 'rower',
            'total_duration': total_duration,
            'total_distance': total_distance,
            'total_calories': total_calories,
            'total_strokes': total_strokes,
            'avg_power': avg_power,
            'max_power': max_power,
            'normalized_power': normalized_power,
            'avg_stroke_rate': avg_stroke_rate,
            'max_stroke_rate': max_stroke_rate,
            'avg_heart_rate': avg_heart_rate,
            'max_heart_rate': max_heart_rate,
            'avg_pace': avg_pace,
            'training_stress_score': training_stress_score,
            'intensity_factor': intensity_factor,
            'data_series': {
                'timestamps': timestamps,
                'powers': powers,
                'stroke_rates': stroke_rates,
                'heart_rates': heart_rates,
                'distances': distances,
                'stroke_counts': stroke_counts
            }
        }
        
        return processed_data
    
    def _calculate_calories_bike(self, avg_power: float, duration: int, 
                               reported_calories: int) -> int:
        """
        Calculate calories burned during a bike workout.
        
        Args:
            avg_power: Average power in watts
            duration: Duration in seconds
            reported_calories: Calories reported by the device
            
        Returns:
            Estimated calories burned
        """
        if reported_calories > 0:
            return reported_calories
        
        # Simple estimation: 1 watt for 1 hour = ~3.6 kcal
        # So power * duration_in_hours * 3.6 = calories
        duration_hours = duration / 3600
        estimated_calories = int(avg_power * duration_hours * 3.6)
        
        return max(1, estimated_calories)
    
    def _calculate_calories_rower(self, avg_power: float, duration: int, 
                                reported_calories: int) -> int:
        """
        Calculate calories burned during a rowing workout.
        
        Args:
            avg_power: Average power in watts
            duration: Duration in seconds
            reported_calories: Calories reported by the device
            
        Returns:
            Estimated calories burned
        """
        if reported_calories > 0:
            return reported_calories
        
        # Simple estimation: 1 watt for 1 hour = ~4 kcal for rowing
        # (slightly higher than cycling due to more muscle engagement)
        duration_hours = duration / 3600
        estimated_calories = int(avg_power * duration_hours * 4)
        
        return max(1, estimated_calories)
    
    def _calculate_pace(self, distance: float, duration: int) -> float:
        """
        Calculate pace as time per 500m for rowing.
        
        Args:
            distance: Distance in meters
            duration: Duration in seconds
            
        Returns:
            Pace in seconds per 500m
        """
        if distance <= 0:
            return 0
        
        # Calculate seconds per meter
        seconds_per_meter = duration / distance
        
        # Convert to seconds per 500m
        pace = seconds_per_meter * 500
        
        return pace
    
    def _calculate_normalized_power(self, powers: List[float]) -> float:
        """
        Calculate normalized power.
        
        Args:
            powers: List of power values
            
        Returns:
            Normalized power
        """
        if not powers or len(powers) < 30:  # Need at least 30 seconds of data
            return 0
        
        # Use 30-second rolling average
        rolling_avg_powers = []
        window_size = 30
        
        for i in range(len(powers) - window_size + 1):
            window = powers[i:i+window_size]
            rolling_avg_powers.append(sum(window) / window_size)
        
        # Raise to 4th power, average, then take 4th root
        fourth_powers = [pow(p, 4) for p in rolling_avg_powers]
        avg_fourth_power = sum(fourth_powers) / len(fourth_powers)
        normalized_power = pow(avg_fourth_power, 0.25)
        
        return round(normalized_power, 1)
    
    def _calculate_intensity_factor(self, avg_power: float) -> float:
        """
        Calculate intensity factor.
        
        Args:
            avg_power: Average power
            
        Returns:
            Intensity factor
        """
        # Get FTP from user profile or use default
        ftp = self.user_profile.get('ftp', 200)  # Default FTP of 200W
        
        if ftp <= 0:
            return 0
        
        intensity_factor = avg_power / ftp
        
        return round(intensity_factor, 2)
    
    def _calculate_tss(self, powers: List[float], timestamps: List[int]) -> float:
        """
        Calculate Training Stress Score (TSS).
        
        Args:
            powers: List of power values
            timestamps: List of timestamps
            
        Returns:
            Training Stress Score
        """
        if not powers or not timestamps:
            return 0
        
        # Get FTP from user profile or use default
        ftp = self.user_profile.get('ftp', 200)  # Default FTP of 200W
        
        if ftp <= 0:
            return 0
        
        # Calculate normalized power
        normalized_power = self._calculate_normalized_power(powers)
        
        # Calculate intensity factor
        intensity_factor = normalized_power / ftp
        
        # Calculate duration in hours
        duration_hours = max(timestamps) / 3600
        
        # Calculate TSS
        tss = 100 * duration_hours * intensity_factor * intensity_factor
        
        return round(tss, 1)
    
    def estimate_vo2max(self, workout_data: Dict[str, Any]) -> Optional[float]:
        """
        Estimate VO2 max based on workout data.
        
        Args:
            workout_data: Processed workout data
            
        Returns:
            Estimated VO2 max or None if not enough data
        """
        # Check if we have heart rate data
        if not workout_data.get('avg_heart_rate'):
            logger.warning("No heart rate data available for VO2 max estimation")
            return None
        
        # Get user profile data
        age = self.user_profile.get('age', 30)
        weight = self.user_profile.get('weight', 70)  # kg
        gender = self.user_profile.get('gender', 'male')
        resting_hr = self.user_profile.get('resting_heart_rate', 60)
        
        # Get workout data
        avg_hr = workout_data.get('avg_heart_rate', 0)
        max_hr = workout_data.get('max_heart_rate', 0)
        
        # Calculate max heart rate if not available
        if max_hr <= 0:
            max_hr = 220 - age
        
        # Check if heart rate was elevated enough for VO2 max calculation
        # (70% of max heart rate for at least 10 minutes)
        hr_threshold = 0.7 * max_hr
        
        if avg_hr < hr_threshold:
            logger.warning(f"Average heart rate ({avg_hr}) below threshold ({hr_threshold}) for VO2 max estimation")
            return None
        
        # Calculate VO2 max using heart rate reserve method
        hr_reserve = max_hr - resting_hr
        vo2max = 15.3 * (max_hr / resting_hr)
        
        # Adjust for gender
        if gender.lower() == 'female':
            vo2max *= 0.9
        
        # Adjust for power if available (bike only)
        if workout_data.get('workout_type') == 'bike' and workout_data.get('avg_power'):
            avg_power = workout_data.get('avg_power', 0)
            power_to_weight = avg_power / weight
            
            # Simple adjustment based on power-to-weight ratio
            vo2max_from_power = power_to_weight * 10.8 + 7
            
            # Blend the two estimates
            vo2max = (vo2max + vo2max_from_power) / 2
        
        return round(vo2max, 1)


# Example usage
if __name__ == "__main__":
    # Create sample workout data
    bike_data = [
        {'timestamp': 0, 'instantaneous_power': 150, 'instantaneous_cadence': 80, 'heart_rate': 120, 'instantaneous_speed': 25, 'total_distance': 0},
        {'timestamp': 10, 'instantaneous_power': 160, 'instantaneous_cadence': 85, 'heart_rate': 125, 'instantaneous_speed': 26, 'total_distance': 72},
        {'timestamp': 20, 'instantaneous_power': 170, 'instantaneous_cadence': 90, 'heart_rate': 130, 'instantaneous_speed': 27, 'total_distance': 147},
        {'timestamp': 30, 'instantaneous_power': 180, 'instantaneous_cadence': 95, 'heart_rate': 135, 'instantaneous_speed': 28, 'total_distance': 225},
        {'timestamp': 40, 'instantaneous_power': 190, 'instantaneous_cadence': 100, 'heart_rate': 140, 'instantaneous_speed': 29, 'total_distance': 306},
        {'timestamp': 50, 'instantaneous_power': 200, 'instantaneous_cadence': 105, 'heart_rate': 145, 'instantaneous_speed': 30, 'total_distance': 390},
        {'timestamp': 60, 'instantaneous_power': 210, 'instantaneous_cadence': 110, 'heart_rate': 150, 'instantaneous_speed': 31, 'total_distance': 477},
    ]
    
    # Create user profile
    user_profile = {
        'name': 'John Doe',
        'age': 35,
        'weight': 75.0,
        'height': 180.0,
        'gender': 'male',
        'max_heart_rate': 185,
        'resting_heart_rate': 60,
        'ftp': 250
    }
    
    # Create data processor
    processor = DataProcessor(user_profile)
    
    # Process bike data
    processed_bike_data = processor.process_workout_data(
        bike_data, 'bike'
    )
    
    # Estimate VO2 max
    vo2max = processor.estimate_vo2max(processed_bike_data)
    
    print(f"Processed bike data: {processed_bike_data}")
    print(f"Estimated VO2 max: {vo2max}")