#!/usr/bin/env python3
"""
FIT File Timestamp Analyzer

This script checks a FIT file to see if multiple datapoints share the same timestamp.
"""

import os
import sys
from datetime import datetime, timedelta
import collections
from typing import List, Dict, Any

try:
    import fitdecode
except ImportError:
    print("fitdecode package not found. Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "fitdecode"])
    import fitdecode

def analyze_fit_file(fit_file_path: str) -> None:
    """
    Analyze a FIT file to check for duplicate timestamps in record messages.
    
    Args:
        fit_file_path: Path to the FIT file
    """
    print(f"Analyzing FIT file: {fit_file_path}")
    
    if not os.path.exists(fit_file_path):
        print(f"ERROR: File not found: {fit_file_path}")
        return
    
    timestamps = []
    timestamp_to_records = collections.defaultdict(list)
    raw_timestamps = []
    
    with fitdecode.FitReader(fit_file_path) as fit:
        for frame in fit:
            if isinstance(frame, fitdecode.records.FitDataMessage):
                if frame.name == 'record':
                    # Get timestamp if available
                    timestamp = None
                    for field in frame.fields:
                        if field.name == 'timestamp':
                            timestamp = field.value
                            raw_timestamps.append(timestamp)  # Store raw value
                            break
                    
                    if timestamp:
                        timestamp_str = str(timestamp)
                        timestamps.append(timestamp_str)
                        
                        # Store record data with this timestamp
                        record_data = {}
                        for field in frame.fields:
                            record_data[field.name] = field.value
                        timestamp_to_records[timestamp_str].append(record_data)
    
    # Analyze timestamps
    if not timestamps:
        print("No record messages with timestamps found in the file.")
        return
    
    unique_timestamps = set(timestamps)
    
    print(f"Total record messages: {len(timestamps)}")
    print(f"Unique timestamps: {len(unique_timestamps)}")
    
    if len(unique_timestamps) < len(timestamps):
        print("DUPLICATE TIMESTAMPS DETECTED!")
        
        # Count occurrences of each timestamp
        timestamp_counts = collections.Counter(timestamps)
        
        # Print the most common timestamps and how many times they appear
        print("\nMost common timestamps and their occurrences:")
        for ts, count in timestamp_counts.most_common(5):  # Show top 5 most common
            if count > 1:  # Only show duplicates
                print(f"Timestamp: {ts} - Occurrences: {count}")
                
                # Print example records with this timestamp
                print("Example records with this timestamp:")
                for i, record in enumerate(timestamp_to_records[ts][:2]):  # Show up to 2 examples
                    print(f"  Record {i+1}: {record}")
                print()
    else:
        print("SUCCESS: All timestamps are unique!")
    
    # Calculate time span of the workout using raw timestamps
    try:
        # Check if we have datetime objects
        if raw_timestamps and isinstance(raw_timestamps[0], datetime) and isinstance(raw_timestamps[-1], datetime):
            first_ts = raw_timestamps[0]
            last_ts = raw_timestamps[-1]
            time_diff = last_ts - first_ts
            print(f"\nWorkout timespan (using datetime objects): {time_diff}")
            print(f"First timestamp: {first_ts}")
            print(f"Last timestamp: {last_ts}")
            
            # Calculate sampling rate (datapoints per second)
            duration_seconds = time_diff.total_seconds()
            if duration_seconds > 0:
                sampling_rate = len(timestamps) / duration_seconds
                print(f"Average sampling rate: {sampling_rate:.2f} datapoints per second")
            
            # Show intervals between samples
            if len(raw_timestamps) > 1:
                print("\nTime intervals between consecutive samples (first 5):")
                for i in range(min(5, len(raw_timestamps)-1)):
                    interval = raw_timestamps[i+1] - raw_timestamps[i]
                    print(f"  Interval {i+1}: {interval.total_seconds():.2f} seconds")
        else:
            # Try numeric timestamps (seconds since epoch)
            numeric_timestamps = []
            for ts in raw_timestamps:
                if isinstance(ts, (int, float)):
                    numeric_timestamps.append(ts)
                
            if numeric_timestamps:
                first_ts = min(numeric_timestamps)
                last_ts = max(numeric_timestamps)
                time_diff = last_ts - first_ts
                
                print(f"\nWorkout timespan (using numeric timestamps): {time_diff:.2f} seconds")
                print(f"First timestamp (numeric): {first_ts}")
                print(f"Last timestamp (numeric): {last_ts}")
                
                # Calculate sampling rate
                if time_diff > 0:
                    sampling_rate = len(numeric_timestamps) / time_diff
                    print(f"Average sampling rate: {sampling_rate:.2f} datapoints per second")
                
                # Show intervals between samples
                if len(numeric_timestamps) > 1:
                    numeric_timestamps.sort()
                    print("\nTime intervals between consecutive samples (first 5):")
                    for i in range(min(5, len(numeric_timestamps)-1)):
                        interval = numeric_timestamps[i+1] - numeric_timestamps[i]
                        print(f"  Interval {i+1}: {interval:.2f} seconds")
    except Exception as e:
        print(f"Could not calculate workout timespan: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Use the latest FIT file in the fit_files directory
    fit_files_dir = os.path.join(os.getcwd(), "fit_files")
    
    if not os.path.exists(fit_files_dir):
        print(f"ERROR: Directory not found: {fit_files_dir}")
        sys.exit(1)
    
    fit_files = [f for f in os.listdir(fit_files_dir) if f.endswith('.fit')]
    
    if not fit_files:
        print(f"ERROR: No FIT files found in {fit_files_dir}")
        sys.exit(1)
    
    # Sort by file modification time (newest first)
    fit_files.sort(key=lambda f: os.path.getmtime(os.path.join(fit_files_dir, f)), reverse=True)
    
    latest_fit_file = os.path.join(fit_files_dir, fit_files[0])
    print(f"Latest FIT file: {latest_fit_file}")
    
    analyze_fit_file(latest_fit_file)