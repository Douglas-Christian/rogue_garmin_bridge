#!/usr/bin/env python3
"""
FIT File Analysis Script
This script compares the fitfiletools.fit reference file with generated FIT files
to identify differences and suggest improvements.
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import fitdecode
from datetime import datetime
import collections
from pathlib import Path
import traceback

def extract_fit_file_structure(fit_file_path):
    """
    Extract the structure and content of a FIT file
    
    Args:
        fit_file_path: Path to the FIT file
        
    Returns:
        Dictionary containing the structure of the FIT file
    """
    fit_structure = {
        'file_id': None,
        'file_creator': None,
        'event': [],
        'device_info': [],
        'user_profile': None,
        'sport': None,
        'zones_target': None,
        'record': [],
        'lap': [],
        'session': None,
        'activity': None,
        'other_messages': collections.defaultdict(list)
    }
    
    try:
        with fitdecode.FitReader(fit_file_path) as fit:
            for frame in fit:
                if isinstance(frame, fitdecode.FitDataMessage):
                    message_type = frame.name.lower()
                    
                    if message_type in fit_structure:
                        if isinstance(fit_structure[message_type], list):
                            # For list types, append the data
                            fields_dict = {field.name: field.value for field in frame.fields}
                            fit_structure[message_type].append(fields_dict)
                        else:
                            # For single-instance types, set the data
                            fields_dict = {field.name: field.value for field in frame.fields}
                            fit_structure[message_type] = fields_dict
                    else:
                        # For any other message types
                        fields_dict = {field.name: field.value for field in frame.fields}
                        fit_structure['other_messages'][message_type].append(fields_dict)
                        
        return fit_structure
    except Exception as e:
        print(f"Error analyzing {fit_file_path}: {e}")
        traceback.print_exc()
        return None

def analyze_message_field_presence(fit_structure):
    """
    Analyze which fields are present in which message types
    
    Args:
        fit_structure: Dictionary containing the structure of a FIT file
        
    Returns:
        Dictionary of field presence by message type
    """
    field_presence = {}
    
    # Analyze main message types
    for message_type, data in fit_structure.items():
        if message_type == 'other_messages':
            continue
            
        if data is None:
            field_presence[message_type] = {'present': False}
            continue
            
        field_presence[message_type] = {'present': True}
        
        if isinstance(data, list):
            # For list types, get unique fields from all records
            all_fields = set()
            for item in data:
                all_fields.update(item.keys())
                
            for field in all_fields:
                field_presence[message_type][field] = sum(1 for item in data if field in item)
        else:
            # For single-instance types
            for field in data.keys():
                field_presence[message_type][field] = 1
    
    # Analyze other message types
    for message_type, data_list in fit_structure['other_messages'].items():
        field_presence[message_type] = {'present': True}
        
        all_fields = set()
        for item in data_list:
            all_fields.update(item.keys())
            
        for field in all_fields:
            field_presence[message_type][field] = sum(1 for item in data_list if field in item)
    
    return field_presence

def records_to_dataframe(records):
    """
    Convert record data points to a pandas DataFrame
    
    Args:
        records: List of record dictionaries from a FIT file
        
    Returns:
        DataFrame containing the record data
    """
    if not records:
        return pd.DataFrame()
        
    df = pd.DataFrame(records)
    
    # Convert timestamp to datetime if present
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
    return df

def compare_field_presence(ref_fields, recent_fields, message_type):
    """Compare fields between reference and recent files for a specific message type"""
    if message_type not in ref_fields or message_type not in recent_fields:
        print(f"Message type '{message_type}' not present in both files")
        return
        
    ref_msg_fields = set(ref_fields[message_type].keys()) - {'present'}
    recent_msg_fields = set(recent_fields[message_type].keys()) - {'present'}
    
    print(f"\n--- {message_type.upper()} Message Type ---")
    print(f"Fields in reference but not in recent: {ref_msg_fields - recent_msg_fields}")
    print(f"Fields in recent but not in reference: {recent_msg_fields - ref_msg_fields}")
    print(f"Common fields: {ref_msg_fields.intersection(recent_msg_fields)}")

def main():
    # File paths
    fit_files_dir = Path('fit_files')
    reference_file = fit_files_dir / 'fitfiletools.fit'

    # Get the most recent workout files (last 5) - handle the file name issues
    recent_files = []
    for f in fit_files_dir.glob('indoor_cycling_*.fit'):
        if os.path.getsize(f) > 0:
            recent_files.append(f)
    
    recent_files = sorted(recent_files, key=os.path.getmtime, reverse=True)[:5]

    print(f"Reference file: {reference_file}")
    print("Recent files:")
    for f in recent_files:
        print(f"  - {f} ({os.path.getsize(f)} bytes)")

    # Analyze the reference file
    print("\nAnalyzing reference file...")
    reference_structure = extract_fit_file_structure(reference_file)
    if reference_structure:
        reference_fields = analyze_message_field_presence(reference_structure)
        
        # Analyze a recent file for comparison
        if recent_files:
            print(f"\nAnalyzing most recent file: {recent_files[0]}")
            recent_structure = extract_fit_file_structure(recent_files[0])
            
            if recent_structure:
                recent_fields = analyze_message_field_presence(recent_structure)

                # Compare available message types
                ref_msg_types = set(reference_fields.keys())
                recent_msg_types = set(recent_fields.keys())

                print("\nMessage type comparison:")
                print("Message types in reference but not in recent:", ref_msg_types - recent_msg_types)
                print("Message types in recent but not in reference:", recent_msg_types - ref_msg_types)
                print("Common message types:", ref_msg_types.intersection(recent_msg_types))

                # Compare important message types
                important_types = ['file_id', 'sport', 'record', 'lap', 'session', 'activity']
                for msg_type in important_types:
                    compare_field_presence(reference_fields, recent_fields, msg_type)

                # Convert record data to DataFrames
                ref_records_df = records_to_dataframe(reference_structure['record'])
                recent_records_df = records_to_dataframe(recent_structure['record'])

                # Print basic information about the record data
                print("\nRecord data comparison:")
                print("Reference Records:")
                print(f"  - Number of records: {len(ref_records_df)}")
                print(f"  - Columns: {list(ref_records_df.columns)}")
                if not ref_records_df.empty and 'timestamp' in ref_records_df.columns:
                    print(f"  - Time range: {ref_records_df['timestamp'].min()} to {ref_records_df['timestamp'].max()}")

                print("\nRecent Records:")
                print(f"  - Number of records: {len(recent_records_df)}")
                print(f"  - Columns: {list(recent_records_df.columns)}")
                if not recent_records_df.empty and 'timestamp' in recent_records_df.columns:
                    print(f"  - Time range: {recent_records_df['timestamp'].min()} to {recent_records_df['timestamp'].max()}")

                # Compare data sampling frequency
                if 'timestamp' in ref_records_df.columns and len(ref_records_df) > 1:
                    ref_diffs = ref_records_df['timestamp'].diff().dropna()
                    ref_avg_seconds = ref_diffs.mean().total_seconds()
                    print(f"\nReference sampling frequency: ~ every {ref_avg_seconds:.2f} seconds")
                    
                if 'timestamp' in recent_records_df.columns and len(recent_records_df) > 1:
                    recent_diffs = recent_records_df['timestamp'].diff().dropna()
                    recent_avg_seconds = recent_diffs.mean().total_seconds()
                    print(f"Recent sampling frequency: ~ every {recent_avg_seconds:.2f} seconds")

                # Compare Session data
                print("\n--- SESSION COMPARISON ---")
                if reference_structure['session'] and recent_structure['session']:
                    ref_session = reference_structure['session']
                    recent_session = recent_structure['session']
                    
                    # Find all unique keys
                    all_keys = set(ref_session.keys()).union(set(recent_session.keys()))
                    
                    for key in sorted(all_keys):
                        ref_val = ref_session.get(key, "MISSING")
                        recent_val = recent_session.get(key, "MISSING")
                        
                        # Only show differences
                        if ref_val != recent_val:
                            print(f"{key}:")
                            print(f"  - Reference: {ref_val}")
                            print(f"  - Recent: {recent_val}")
                else:
                    print("Session data not available in both files")

                # Compare Activity data
                print("\n--- ACTIVITY COMPARISON ---")
                if reference_structure['activity'] and recent_structure['activity']:
                    ref_activity = reference_structure['activity']
                    recent_activity = recent_structure['activity']
                    
                    # Find all unique keys
                    all_keys = set(ref_activity.keys()).union(set(recent_activity.keys()))
                    
                    for key in sorted(all_keys):
                        ref_val = ref_activity.get(key, "MISSING")
                        recent_val = recent_activity.get(key, "MISSING")
                        
                        # Only show differences
                        if ref_val != recent_val:
                            print(f"{key}:")
                            print(f"  - Reference: {ref_val}")
                            print(f"  - Recent: {recent_val}")
                else:
                    print("Activity data not available in both files")

                # Generate recommendations
                print("\nRECOMMENDATIONS FOR IMPROVING FIT FILE GENERATION:")
                
                # Check for missing message types
                missing_messages = set(reference_fields.keys()) - set(recent_fields.keys())
                if missing_messages:
                    print(f"1. Add the following missing message types: {', '.join(missing_messages)}")
                
                # Check for missing fields in common message types
                recommendation_num = 2
                common_message_types = set(reference_fields.keys()).intersection(set(recent_fields.keys()))
                for msg_type in common_message_types:
                    ref_fields_set = set(reference_fields[msg_type].keys()) - {'present'}
                    recent_fields_set = set(recent_fields[msg_type].keys()) - {'present'}
                    missing_fields = ref_fields_set - recent_fields_set
                    
                    if missing_fields:
                        print(f"{recommendation_num}. Add the following missing fields to the '{msg_type}' message: {', '.join(missing_fields)}")
                        recommendation_num += 1
                
                # Check for differences in session parameters
                if reference_structure['session'] and recent_structure['session']:
                    ref_session = reference_structure['session']
                    recent_session = recent_structure['session']
                    
                    # Sport type
                    if ref_session.get('sport') != recent_session.get('sport'):
                        print(f"{recommendation_num}. Set the sport type to '{ref_session.get('sport')}' instead of '{recent_session.get('sport')}'")
                        recommendation_num += 1
                    
                    # Sub sport
                    if ref_session.get('sub_sport') != recent_session.get('sub_sport'):
                        print(f"{recommendation_num}. Set the sub_sport to '{ref_session.get('sub_sport')}' instead of '{recent_session.get('sub_sport')}'")
                        recommendation_num += 1
                
                # Check data recording frequency
                if 'timestamp' in ref_records_df.columns and 'timestamp' in recent_records_df.columns:
                    if len(ref_records_df) > 1 and len(recent_records_df) > 1:
                        ref_diffs = ref_records_df['timestamp'].diff().dropna()
                        ref_avg_seconds = ref_diffs.mean().total_seconds()
                        
                        recent_diffs = recent_records_df['timestamp'].diff().dropna()
                        recent_avg_seconds = recent_diffs.mean().total_seconds()
                        
                        if abs(ref_avg_seconds - recent_avg_seconds) > 0.1:
                            print(f"{recommendation_num}. Adjust data recording frequency from every {recent_avg_seconds:.2f} seconds to every {ref_avg_seconds:.2f} seconds")
                            recommendation_num += 1

                # Extract implementation details
                print("\nIMPLEMENTATION DETAILS FROM REFERENCE FILE:")
                details = {}
                
                # Extract sport type and sub_sport
                if reference_structure['session']:
                    details['sport'] = reference_structure['session'].get('sport')
                    details['sub_sport'] = reference_structure['session'].get('sub_sport')
                
                # Extract manufacturer and product info
                if reference_structure['file_id']:
                    details['manufacturer'] = reference_structure['file_id'].get('manufacturer')
                    details['product'] = reference_structure['file_id'].get('product')
                    details['type'] = reference_structure['file_id'].get('type')
                
                # Extract recording interval
                if 'timestamp' in ref_records_df.columns and len(ref_records_df) > 1:
                    ref_diffs = ref_records_df['timestamp'].diff().dropna()
                    details['recording_interval_seconds'] = ref_diffs.mean().total_seconds()
                
                # Look for non-standard fields in the record data
                if reference_structure['record']:
                    standard_fields = {'timestamp', 'position_lat', 'position_long', 'altitude', 
                                    'heart_rate', 'cadence', 'distance', 'speed', 'power', 
                                    'temperature', 'enhanced_altitude', 'enhanced_speed'}
                    
                    non_standard = set()
                    for record in reference_structure['record']:
                        non_standard.update(set(record.keys()) - standard_fields)
                    
                    if non_standard:
                        details['non_standard_record_fields'] = list(non_standard)
                
                for key, value in details.items():
                    print(f"{key}: {value}")
            else:
                print("Failed to parse recent file structure")
        else:
            print("No recent files found for comparison")
    else:
        print("Failed to parse reference file structure")

if __name__ == "__main__":
    main()
