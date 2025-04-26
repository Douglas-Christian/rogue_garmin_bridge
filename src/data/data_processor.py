#!/usr/bin/env python3
"""
Data Processing Module for Rogue to Garmin Bridge

This module handles data processing and analysis for workout data,
including calculating metrics and preparing data for FIT file conversion.
"""

import logging
import math
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('data_processor')

class DataProcessor:
    """
    Class for processing and analyzing workout data.
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
                            workout_type: str, 
                            start_time: datetime) -> Dict[str, Any]:
        """
        Process raw workout data to prepare for FIT file conversion.
        
        Args:
            workout_data: List of workout data points
            workout_type: Type of workout (bike, rower, etc.)
            start_time: Start time of the workout
            
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
            return self._process_bike_data(workout_data, start_time)
        elif workout_type == 'rower':
            return self._process_rower_data(workout_data, start_time)
        else:
            logger.warning(f"Unknown workout type: {workout_type}")
            return {}
    
    def _process_bike_data(self, workout_data: List[Dict[str, Any]], 
                          start_time: datetime) -> Dict[str, Any]:
        """
        Process bike workout data.
        
        Args:
            workout_data: List of bike workout data points
            start_time: Start time of the workout
            
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
        
        # Generate absolute timestamps for each data point
        absolute_timestamps = [start_time + timedelta(seconds=ts) for ts in timestamps]
        
        # Prepare processed data
        processed_data = {
            'workout_type': 'bike',
            'start_time': start_time,
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
                'absolute_timestamps': absolute_timestamps,
                'powers': powers,
                'cadences': cadences,
                'heart_rates': heart_rates,
                'speeds': speeds,
                'distances': distances
            }
        }
        
        return processed_data
    
    def _process_rower_data(self, workout_data: List[Dict[str, Any]], 
                           start_time: datetime) -> Dict[str, Any]:
        """
        Process rower workout data.
        
        Args:
            workout_data: List of rower workout data points
            start_time: Start time of the workout
            
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
        
        # Generate absolute timestamps for each data point
        absolute_timestamps = [start_time + timedelta(seconds=ts) for ts in timestamps]
        
        # Prepare processed data
        processed_data = {
            'workout_type': 'rower',
            'start_time': start_time,
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
                'absolute_timestamps': absolute_timestamps,
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
        avg_hr = work
(Content truncated due to size limit. Use line ranges to read in chunks)