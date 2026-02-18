#!/usr/bin/env python3
"""
Data Processing Error Handler and Validator

This module provides comprehensive data validation, outlier detection,
and error handling for FTMS workout data processing.
"""

import math
import statistics
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json
import os

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.utils.logging_config import get_component_logger

logger = get_component_logger('data_validator')

class DataQuality(Enum):
    """Data quality indicators"""
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"
    INVALID = "invalid"

class ValidationResult(Enum):
    """Validation result types"""
    VALID = "valid"
    CORRECTED = "corrected"
    INTERPOLATED = "interpolated"
    REJECTED = "rejected"

@dataclass
class ValidationThresholds:
    """Configurable validation thresholds for different device types"""
    # Bike thresholds
    bike_speed_min: float = 0.0
    bike_speed_max: float = 80.0  # km/h
    bike_cadence_min: float = 0.0
    bike_cadence_max: float = 200.0  # RPM
    bike_power_min: float = 0.0
    bike_power_max: float = 2000.0  # Watts
    
    # Rower thresholds
    rower_stroke_rate_min: float = 0.0
    rower_stroke_rate_max: float = 60.0  # strokes/min
    rower_power_min: float = 0.0
    rower_power_max: float = 1500.0  # Watts
    rower_pace_min: float = 60.0  # seconds per 500m
    rower_pace_max: float = 600.0  # seconds per 500m
    
    # Common thresholds
    heart_rate_min: float = 40.0
    heart_rate_max: float = 220.0  # BPM
    distance_max_jump: float = 1000.0  # meters per second (unrealistic jump)
    
    # Outlier detection
    outlier_std_multiplier: float = 3.0  # Standard deviations for outlier detection
    min_samples_for_outlier_detection: int = 10
    
    # Data quality thresholds
    excellent_quality_threshold: float = 0.95
    good_quality_threshold: float = 0.85
    acceptable_quality_threshold: float = 0.70

@dataclass
class DataPoint:
    """Represents a validated data point with quality information"""
    timestamp: datetime
    device_type: str
    original_data: Dict[str, Any]
    validated_data: Dict[str, Any]
    quality: DataQuality
    validation_result: ValidationResult
    corrections_applied: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    interpolated_fields: List[str] = field(default_factory=list)

class DataValidator:
    """
    Comprehensive data validator with outlier detection and error correction
    """
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize the data validator.
        
        Args:
            config_file: Optional path to configuration file with custom thresholds
        """
        self.thresholds = ValidationThresholds()
        self.historical_data: Dict[str, List[float]] = {}
        self.data_history: List[DataPoint] = []
        self.max_history_size = 1000
        
        # Load custom thresholds if provided
        if config_file and os.path.exists(config_file):
            self._load_thresholds(config_file)
        
        # Statistics tracking
        self.validation_stats = {
            'total_points': 0,
            'valid_points': 0,
            'corrected_points': 0,
            'interpolated_points': 0,
            'rejected_points': 0,
            'outliers_detected': 0
        }
        
        logger.info("Data validator initialized")
    
    def _load_thresholds(self, config_file: str):
        """Load validation thresholds from configuration file"""
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            # Update thresholds with values from config
            for key, value in config.get('validation_thresholds', {}).items():
                if hasattr(self.thresholds, key):
                    setattr(self.thresholds, key, value)
                    logger.debug(f"Updated threshold {key} = {value}")
            
            logger.info(f"Loaded validation thresholds from {config_file}")
        except Exception as e:
            logger.error(f"Error loading thresholds from {config_file}: {e}")
    
    def validate_data_point(self, data: Dict[str, Any]) -> DataPoint:
        """
        Validate a single data point with comprehensive error checking.
        
        Args:
            data: Raw data point from FTMS device
            
        Returns:
            DataPoint with validation results and corrections
        """
        self.validation_stats['total_points'] += 1
        
        timestamp = datetime.now()
        if 'timestamp' in data:
            try:
                if isinstance(data['timestamp'], str):
                    timestamp = datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00'))
                elif isinstance(data['timestamp'], datetime):
                    timestamp = data['timestamp']
            except Exception as e:
                logger.warning(f"Invalid timestamp format: {e}")
        
        device_type = data.get('device_type', 'unknown')
        original_data = data.copy()
        validated_data = data.copy()
        corrections = []
        warnings = []
        interpolated_fields = []
        
        # Validate based on device type
        if device_type == 'bike':
            validated_data, bike_corrections, bike_warnings, bike_interpolated = self._validate_bike_data(validated_data)
            corrections.extend(bike_corrections)
            warnings.extend(bike_warnings)
            interpolated_fields.extend(bike_interpolated)
        elif device_type == 'rower':
            validated_data, rower_corrections, rower_warnings, rower_interpolated = self._validate_rower_data(validated_data)
            corrections.extend(rower_corrections)
            warnings.extend(rower_warnings)
            interpolated_fields.extend(rower_interpolated)
        
        # Common validations
        validated_data, common_corrections, common_warnings, common_interpolated = self._validate_common_data(validated_data)
        corrections.extend(common_corrections)
        warnings.extend(common_warnings)
        interpolated_fields.extend(common_interpolated)
        
        # Outlier detection
        outlier_corrections, outlier_warnings = self._detect_outliers(validated_data, device_type)
        corrections.extend(outlier_corrections)
        warnings.extend(outlier_warnings)
        
        # Determine validation result and quality
        validation_result = ValidationResult.VALID
        if corrections:
            if interpolated_fields:
                validation_result = ValidationResult.INTERPOLATED
                self.validation_stats['interpolated_points'] += 1
            else:
                validation_result = ValidationResult.CORRECTED
                self.validation_stats['corrected_points'] += 1
        else:
            self.validation_stats['valid_points'] += 1
        
        # Calculate data quality
        quality = self._calculate_data_quality(original_data, validated_data, corrections, warnings)
        
        # Create validated data point
        data_point = DataPoint(
            timestamp=timestamp,
            device_type=device_type,
            original_data=original_data,
            validated_data=validated_data,
            quality=quality,
            validation_result=validation_result,
            corrections_applied=corrections,
            warnings=warnings,
            interpolated_fields=interpolated_fields
        )
        
        # Update historical data for outlier detection
        self._update_historical_data(validated_data, device_type)
        
        # Store in history (with size limit)
        self.data_history.append(data_point)
        if len(self.data_history) > self.max_history_size:
            self.data_history = self.data_history[-self.max_history_size:]
        
        # Log validation results
        if corrections or warnings:
            logger.info(f"Data validation - Quality: {quality.value}, "
                       f"Corrections: {len(corrections)}, Warnings: {len(warnings)}")
            if corrections:
                logger.debug(f"Corrections applied: {corrections}")
            if warnings:
                logger.debug(f"Warnings: {warnings}")
        
        return data_point
    
    def _validate_bike_data(self, data: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str], List[str], List[str]]:
        """Validate bike-specific data fields"""
        corrections = []
        warnings = []
        interpolated = []
        
        # Speed validation
        if 'speed' in data and data['speed'] is not None:
            speed = data['speed']
            if speed < self.thresholds.bike_speed_min:
                data['speed'] = max(0.0, speed)  # Don't allow negative speeds
                corrections.append(f"Speed corrected from {speed} to {data['speed']}")
            elif speed > self.thresholds.bike_speed_max:
                # Likely a unit conversion error or sensor malfunction
                if speed > 1000:  # Probably in different units
                    data['speed'] = speed / 100.0  # Convert from cm/h to km/h
                    corrections.append(f"Speed unit corrected from {speed} to {data['speed']}")
                else:
                    data['speed'] = self.thresholds.bike_speed_max
                    corrections.append(f"Speed capped from {speed} to {data['speed']}")
                    warnings.append("Unusually high speed detected")
        
        # Cadence validation
        if 'cadence' in data and data['cadence'] is not None:
            cadence = data['cadence']
            if cadence < self.thresholds.bike_cadence_min:
                data['cadence'] = 0.0
                corrections.append(f"Cadence corrected from {cadence} to 0")
            elif cadence > self.thresholds.bike_cadence_max:
                data['cadence'] = self.thresholds.bike_cadence_max
                corrections.append(f"Cadence capped from {cadence} to {data['cadence']}")
                warnings.append("Unusually high cadence detected")
        
        # Power validation
        if 'power' in data and data['power'] is not None:
            power = data['power']
            if power < self.thresholds.bike_power_min:
                data['power'] = 0.0
                corrections.append(f"Power corrected from {power} to 0")
            elif power > self.thresholds.bike_power_max:
                data['power'] = self.thresholds.bike_power_max
                corrections.append(f"Power capped from {power} to {data['power']}")
                warnings.append("Unusually high power detected")
        
        return data, corrections, warnings, interpolated
    
    def _validate_rower_data(self, data: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str], List[str], List[str]]:
        """Validate rower-specific data fields"""
        corrections = []
        warnings = []
        interpolated = []
        
        # Stroke rate validation
        if 'stroke_rate' in data and data['stroke_rate'] is not None:
            stroke_rate = data['stroke_rate']
            if stroke_rate < self.thresholds.rower_stroke_rate_min:
                data['stroke_rate'] = 0.0
                corrections.append(f"Stroke rate corrected from {stroke_rate} to 0")
            elif stroke_rate > self.thresholds.rower_stroke_rate_max:
                data['stroke_rate'] = self.thresholds.rower_stroke_rate_max
                corrections.append(f"Stroke rate capped from {stroke_rate} to {data['stroke_rate']}")
                warnings.append("Unusually high stroke rate detected")
        
        # Power validation
        if 'power' in data and data['power'] is not None:
            power = data['power']
            if power < self.thresholds.rower_power_min:
                data['power'] = 0.0
                corrections.append(f"Power corrected from {power} to 0")
            elif power > self.thresholds.rower_power_max:
                data['power'] = self.thresholds.rower_power_max
                corrections.append(f"Power capped from {power} to {data['power']}")
                warnings.append("Unusually high power detected")
        
        # Pace validation
        if 'pace' in data and data['pace'] is not None:
            pace = data['pace']
            if pace < self.thresholds.rower_pace_min:
                data['pace'] = self.thresholds.rower_pace_min
                corrections.append(f"Pace corrected from {pace} to {data['pace']}")
                warnings.append("Unusually fast pace detected")
            elif pace > self.thresholds.rower_pace_max:
                data['pace'] = self.thresholds.rower_pace_max
                corrections.append(f"Pace corrected from {pace} to {data['pace']}")
                warnings.append("Unusually slow pace detected")
        
        return data, corrections, warnings, interpolated
    
    def _validate_common_data(self, data: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str], List[str], List[str]]:
        """Validate common data fields across all device types"""
        corrections = []
        warnings = []
        interpolated = []
        
        # Heart rate validation
        if 'heart_rate' in data and data['heart_rate'] is not None:
            hr = data['heart_rate']
            if hr < self.thresholds.heart_rate_min:
                data['heart_rate'] = None  # Remove invalid heart rate
                corrections.append(f"Invalid heart rate {hr} removed")
            elif hr > self.thresholds.heart_rate_max:
                data['heart_rate'] = None  # Remove invalid heart rate
                corrections.append(f"Invalid heart rate {hr} removed")
                warnings.append("Heart rate sensor may be malfunctioning")
        
        # Distance validation (check for unrealistic jumps)
        if 'distance' in data and data['distance'] is not None:
            current_distance = data['distance']
            if len(self.data_history) > 0:
                last_point = self.data_history[-1]
                if 'distance' in last_point.validated_data and last_point.validated_data['distance'] is not None:
                    last_distance = last_point.validated_data['distance']
                    time_diff = (datetime.now() - last_point.timestamp).total_seconds()
                    
                    if time_diff > 0:
                        distance_jump = abs(current_distance - last_distance)
                        max_reasonable_jump = self.thresholds.distance_max_jump * time_diff
                        
                        if distance_jump > max_reasonable_jump:
                            # Interpolate the distance
                            data['distance'] = last_distance + (max_reasonable_jump * 0.5)
                            corrections.append(f"Distance jump corrected from {current_distance} to {data['distance']}")
                            interpolated.append('distance')
                            warnings.append("Large distance jump detected and corrected")
        
        return data, corrections, warnings, interpolated
    
    def _detect_outliers(self, data: Dict[str, Any], device_type: str) -> Tuple[List[str], List[str]]:
        """Detect and handle outliers using statistical methods"""
        corrections = []
        warnings = []
        
        # Only perform outlier detection if we have enough historical data
        if len(self.data_history) < self.thresholds.min_samples_for_outlier_detection:
            return corrections, warnings
        
        # Define fields to check for outliers based on device type
        fields_to_check = []
        if device_type == 'bike':
            fields_to_check = ['speed', 'cadence', 'power']
        elif device_type == 'rower':
            fields_to_check = ['stroke_rate', 'power', 'pace']
        
        fields_to_check.append('heart_rate')  # Common field
        
        for field in fields_to_check:
            if field in data and data[field] is not None:
                current_value = data[field]
                
                # Get historical values for this field
                historical_values = []
                for point in self.data_history[-50:]:  # Use last 50 points
                    if (point.device_type == device_type and 
                        field in point.validated_data and 
                        point.validated_data[field] is not None):
                        historical_values.append(point.validated_data[field])
                
                if len(historical_values) >= self.thresholds.min_samples_for_outlier_detection:
                    mean_val = statistics.mean(historical_values)
                    std_val = statistics.stdev(historical_values) if len(historical_values) > 1 else 0
                    
                    if std_val > 0:
                        z_score = abs(current_value - mean_val) / std_val
                        
                        if z_score > self.thresholds.outlier_std_multiplier:
                            # Log the outlier but do NOT replace the value —
                            # real fitness equipment data is reliable and
                            # replacing causes the display to "stick" on stale values.
                            warnings.append(f"Statistical outlier in {field}: {current_value} (z-score: {z_score:.2f})")
                            self.validation_stats['outliers_detected'] += 1
        
        return corrections, warnings
    
    def _calculate_data_quality(self, original: Dict[str, Any], validated: Dict[str, Any], 
                              corrections: List[str], warnings: List[str]) -> DataQuality:
        """Calculate overall data quality score"""
        
        # Start with perfect quality
        quality_score = 1.0
        
        # Reduce quality based on corrections and warnings
        quality_score -= len(corrections) * 0.05  # 5% per correction
        quality_score -= len(warnings) * 0.02    # 2% per warning
        
        # Check for missing critical fields
        critical_fields = ['power']  # Power is most important for fitness tracking
        for field in critical_fields:
            if field not in validated or validated[field] is None:
                quality_score -= 0.1  # 10% for missing critical field
        
        # Determine quality level
        if quality_score >= self.thresholds.excellent_quality_threshold:
            return DataQuality.EXCELLENT
        elif quality_score >= self.thresholds.good_quality_threshold:
            return DataQuality.GOOD
        elif quality_score >= self.thresholds.acceptable_quality_threshold:
            return DataQuality.ACCEPTABLE
        elif quality_score > 0:
            return DataQuality.POOR
        else:
            return DataQuality.INVALID
    
    def _update_historical_data(self, data: Dict[str, Any], device_type: str):
        """Update historical data for outlier detection"""
        for field, value in data.items():
            if value is not None and isinstance(value, (int, float)):
                key = f"{device_type}_{field}"
                if key not in self.historical_data:
                    self.historical_data[key] = []
                
                self.historical_data[key].append(value)
                
                # Keep only recent values to prevent memory issues
                if len(self.historical_data[key]) > 100:
                    self.historical_data[key] = self.historical_data[key][-100:]
    
    def interpolate_missing_data(self, data_points: List[DataPoint]) -> List[DataPoint]:
        """
        Interpolate missing data points in a sequence.
        
        Args:
            data_points: List of data points with potential gaps
            
        Returns:
            List of data points with interpolated values
        """
        if len(data_points) < 2:
            return data_points
        
        interpolated_points = []
        
        for i, point in enumerate(data_points):
            interpolated_points.append(point)
            
            # Check if we need to interpolate between this point and the next
            if i < len(data_points) - 1:
                next_point = data_points[i + 1]
                time_gap = (next_point.timestamp - point.timestamp).total_seconds()
                
                # If gap is more than 2 seconds, interpolate
                if time_gap > 2.0:
                    num_interpolated = int(time_gap) - 1
                    
                    for j in range(1, num_interpolated + 1):
                        # Calculate interpolated timestamp
                        interp_time = point.timestamp + timedelta(seconds=j)
                        
                        # Interpolate data values
                        interp_data = {}
                        for field in point.validated_data:
                            if (field in next_point.validated_data and 
                                point.validated_data[field] is not None and 
                                next_point.validated_data[field] is not None and
                                isinstance(point.validated_data[field], (int, float))):
                                
                                # Linear interpolation
                                start_val = point.validated_data[field]
                                end_val = next_point.validated_data[field]
                                ratio = j / (num_interpolated + 1)
                                interp_val = start_val + (end_val - start_val) * ratio
                                interp_data[field] = interp_val
                            else:
                                interp_data[field] = point.validated_data.get(field)
                        
                        # Create interpolated data point
                        interp_point = DataPoint(
                            timestamp=interp_time,
                            device_type=point.device_type,
                            original_data={},
                            validated_data=interp_data,
                            quality=DataQuality.ACCEPTABLE,
                            validation_result=ValidationResult.INTERPOLATED,
                            corrections_applied=[f"Interpolated data point {j}/{num_interpolated}"],
                            warnings=["Data point created by interpolation"],
                            interpolated_fields=list(interp_data.keys())
                        )
                        
                        interpolated_points.append(interp_point)
        
        return interpolated_points
    
    def get_validation_report(self) -> Dict[str, Any]:
        """
        Get a comprehensive validation report.
        
        Returns:
            Dictionary with validation statistics and quality metrics
        """
        total = self.validation_stats['total_points']
        if total == 0:
            return {"error": "No data points processed"}
        
        return {
            "total_points_processed": total,
            "validation_results": {
                "valid": self.validation_stats['valid_points'],
                "corrected": self.validation_stats['corrected_points'],
                "interpolated": self.validation_stats['interpolated_points'],
                "rejected": self.validation_stats['rejected_points']
            },
            "quality_metrics": {
                "valid_percentage": (self.validation_stats['valid_points'] / total) * 100,
                "correction_rate": (self.validation_stats['corrected_points'] / total) * 100,
                "interpolation_rate": (self.validation_stats['interpolated_points'] / total) * 100,
                "outliers_detected": self.validation_stats['outliers_detected']
            },
            "recent_quality_distribution": self._get_recent_quality_distribution(),
            "thresholds": {
                "bike_speed_range": [self.thresholds.bike_speed_min, self.thresholds.bike_speed_max],
                "bike_cadence_range": [self.thresholds.bike_cadence_min, self.thresholds.bike_cadence_max],
                "bike_power_range": [self.thresholds.bike_power_min, self.thresholds.bike_power_max],
                "rower_stroke_rate_range": [self.thresholds.rower_stroke_rate_min, self.thresholds.rower_stroke_rate_max],
                "rower_power_range": [self.thresholds.rower_power_min, self.thresholds.rower_power_max],
                "heart_rate_range": [self.thresholds.heart_rate_min, self.thresholds.heart_rate_max],
                "outlier_threshold": self.thresholds.outlier_std_multiplier
            }
        }
    
    def _get_recent_quality_distribution(self) -> Dict[str, int]:
        """Get distribution of data quality in recent data points"""
        recent_points = self.data_history[-100:]  # Last 100 points
        quality_counts = {quality.value: 0 for quality in DataQuality}
        
        for point in recent_points:
            quality_counts[point.quality.value] += 1
        
        return quality_counts
    
    def reset_statistics(self):
        """Reset validation statistics"""
        self.validation_stats = {
            'total_points': 0,
            'valid_points': 0,
            'corrected_points': 0,
            'interpolated_points': 0,
            'rejected_points': 0,
            'outliers_detected': 0
        }
        self.data_history.clear()
        self.historical_data.clear()
        logger.info("Validation statistics reset")