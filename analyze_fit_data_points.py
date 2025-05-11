#!/usr/bin/env python3
"""
Script to analyze a reference FIT file and a recently generated FIT file to identify missing data points.
"""

import os
import sys
import fitdecode
import argparse
from collections import defaultdict

def extract_fit_file_data(fit_file_path):
    """
    Extract data from a FIT file for analysis.
    
    Args:
        fit_file_path: Path to the FIT file
        
    Returns:
        Dictionary with extracted data
    """
    fit_data = {
        'record_messages': [],
        'session': None
    }
    
    try:
        with fitdecode.FitReader(fit_file_path) as fit:
            for frame in fit:
                if isinstance(frame, fitdecode.FitDataMessage):
                    if frame.name.lower() == 'record':
                        fields_dict = {field.name: field.value for field in frame.fields}
                        fit_data['record_messages'].append(fields_dict)
                    elif frame.name.lower() == 'session':
                        fields_dict = {field.name: field.value for field in frame.fields}
                        fit_data['session'] = fields_dict
        
        return fit_data
    except Exception as e:
        print(f"Error analyzing {fit_file_path}: {e}")
        return None

def analyze_data_points(fit_data, field_name):
    """
    Analyze presence of a specific field in record messages.
    
    Args:
        fit_data: Dictionary with fit data
        field_name: Name of the field to analyze
        
    Returns:
        Dictionary with analysis results
    """
    if not fit_data or 'record_messages' not in fit_data:
        return {'total': 0, 'present': 0, 'percentage': 0, 'values': []}
    
    records = fit_data['record_messages']
    total = len(records)
    present = sum(1 for record in records if field_name in record and record[field_name] is not None)
    percentage = (present / total * 100) if total > 0 else 0
    
    # Get the actual values
    values = [record.get(field_name) for record in records if field_name in record and record[field_name] is not None]
    
    return {
        'total': total,
        'present': present,
        'percentage': percentage,
        'values': values[:5]  # Just the first 5 for display
    }

def analyze_session_data(fit_data, field_name):
    """
    Extract a field from the session message.
    
    Args:
        fit_data: Dictionary with fit data
        field_name: Name of the field to analyze
        
    Returns:
        The field value or None if not present
    """
    if not fit_data or 'session' not in fit_data or not fit_data['session']:
        return None
    
    return fit_data['session'].get(field_name)

def main():
    parser = argparse.ArgumentParser(description='Analyze FIT files for data point presence')
    parser.add_argument('reference_file', help='Path to the reference FIT file')
    parser.add_argument('generated_file', help='Path to a recently generated FIT file')
    args = parser.parse_args()
    
    # Extract data from the files
    reference_data = extract_fit_file_data(args.reference_file)
    generated_data = extract_fit_file_data(args.generated_file)
    
    if not reference_data or not generated_data:
        print("Error extracting data from one or both files")
        return 1
    
    # Fields to analyze
    fields = ['speed', 'cadence', 'power', 'heart_rate', 'distance']
    
    # Compare record message data points
    print("\n=== RECORD MESSAGE DATA POINTS ===")
    for field in fields:
        ref_analysis = analyze_data_points(reference_data, field)
        gen_analysis = analyze_data_points(generated_data, field)
        
        print(f"\nField: {field}")
        print(f"  Reference: {ref_analysis['present']}/{ref_analysis['total']} ({ref_analysis['percentage']:.1f}%)")
        print(f"  Generated: {gen_analysis['present']}/{gen_analysis['total']} ({gen_analysis['percentage']:.1f}%)")
        print(f"  Sample ref values: {ref_analysis['values']}")
        print(f"  Sample gen values: {gen_analysis['values']}")
    
    # Compare session data
    session_fields = ['avg_speed', 'avg_cadence', 'avg_power', 'max_speed', 'max_cadence', 'max_power']
    
    print("\n=== SESSION MESSAGE DATA ===")
    for field in session_fields:
        ref_value = analyze_session_data(reference_data, field)
        gen_value = analyze_session_data(generated_data, field)
        
        print(f"\nField: {field}")
        print(f"  Reference: {ref_value}")
        print(f"  Generated: {gen_value}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
