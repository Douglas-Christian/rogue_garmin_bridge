#!/usr/bin/env python3
"""
Script to compare speed-related fields in two FIT files.
"""

import os
import sys
from fit_tool.fit_file import FitFile
from fit_tool.profile.messages.lap_message import LapMessage
from fit_tool.profile.messages.session_message import SessionMessage
from fit_tool.profile.messages.record_message import RecordMessage

def analyze_speed_data(fit_file, file_path):
    """Analyze speed data in a FIT file."""
    print(f"\nAnalyzing speed data in: {os.path.basename(file_path)}")
    print("=" * 80)
    
    # Extract all messages
    messages = []
    for record in fit_file.records:
        message = record.message
        messages.append(message)
    
    # Analyze lap messages
    lap_messages = [msg for msg in messages if isinstance(msg, LapMessage)]
    if lap_messages:
        print("\nLap Message Speed Data:")
        for i, lap in enumerate(lap_messages):
            print(f"  Lap #{i+1}:")
            
            # Check avg_speed
            if hasattr(lap, 'avg_speed') and lap.avg_speed is not None:
                # Convert from m/s to km/h
                avg_speed_kmh = lap.avg_speed * 3.6
                print(f"    avg_speed: {lap.avg_speed} m/s ({avg_speed_kmh:.2f} km/h)")
            else:
                print(f"    avg_speed: Not present")
                
            # Check max_speed
            if hasattr(lap, 'max_speed') and lap.max_speed is not None:
                # Convert from m/s to km/h
                max_speed_kmh = lap.max_speed * 3.6
                print(f"    max_speed: {lap.max_speed} m/s ({max_speed_kmh:.2f} km/h)")
            else:
                print(f"    max_speed: Not present")
                
            # Check enhanced_avg_speed
            if hasattr(lap, 'enhanced_avg_speed') and lap.enhanced_avg_speed is not None:
                # Convert from m/s to km/h
                enhanced_avg_speed_kmh = lap.enhanced_avg_speed * 3.6
                print(f"    enhanced_avg_speed: {lap.enhanced_avg_speed} m/s ({enhanced_avg_speed_kmh:.2f} km/h)")
            else:
                print(f"    enhanced_avg_speed: Not present")
                
            # Check enhanced_max_speed
            if hasattr(lap, 'enhanced_max_speed') and lap.enhanced_max_speed is not None:
                # Convert from m/s to km/h
                enhanced_max_speed_kmh = lap.enhanced_max_speed * 3.6
                print(f"    enhanced_max_speed: {lap.enhanced_max_speed} m/s ({enhanced_max_speed_kmh:.2f} km/h)")
            else:
                print(f"    enhanced_max_speed: Not present")
    else:
        print("\nNo Lap Messages found")
    
    # Analyze session messages
    session_messages = [msg for msg in messages if isinstance(msg, SessionMessage)]
    if session_messages:
        print("\nSession Message Speed Data:")
        for i, session in enumerate(session_messages):
            print(f"  Session #{i+1}:")
            
            # Check avg_speed
            if hasattr(session, 'avg_speed') and session.avg_speed is not None:
                # Convert from m/s to km/h
                avg_speed_kmh = session.avg_speed * 3.6
                print(f"    avg_speed: {session.avg_speed} m/s ({avg_speed_kmh:.2f} km/h)")
            else:
                print(f"    avg_speed: Not present")
                
            # Check max_speed
            if hasattr(session, 'max_speed') and session.max_speed is not None:
                # Convert from m/s to km/h
                max_speed_kmh = session.max_speed * 3.6
                print(f"    max_speed: {session.max_speed} m/s ({max_speed_kmh:.2f} km/h)")
            else:
                print(f"    max_speed: Not present")
                
            # Check enhanced_avg_speed
            if hasattr(session, 'enhanced_avg_speed') and session.enhanced_avg_speed is not None:
                # Convert from m/s to km/h
                enhanced_avg_speed_kmh = session.enhanced_avg_speed * 3.6
                print(f"    enhanced_avg_speed: {session.enhanced_avg_speed} m/s ({enhanced_avg_speed_kmh:.2f} km/h)")
            else:
                print(f"    enhanced_avg_speed: Not present")
                
            # Check enhanced_max_speed
            if hasattr(session, 'enhanced_max_speed') and session.enhanced_max_speed is not None:
                # Convert from m/s to km/h
                enhanced_max_speed_kmh = session.enhanced_max_speed * 3.6
                print(f"    enhanced_max_speed: {session.enhanced_max_speed} m/s ({enhanced_max_speed_kmh:.2f} km/h)")
            else:
                print(f"    enhanced_max_speed: Not present")
    else:
        print("\nNo Session Messages found")
    
    # Analyze record messages for speed data
    record_messages = [msg for msg in messages if isinstance(msg, RecordMessage)]
    if record_messages:
        speeds = [r.speed for r in record_messages if hasattr(r, 'speed') and r.speed is not None]
        
        # Calculate statistics from instantaneous speeds
        if speeds:
            avg_speed = sum(speeds) / len(speeds)
            max_speed = max(speeds)
            avg_speed_kmh = avg_speed * 3.6
            max_speed_kmh = max_speed * 3.6
            
            print(f"\nRecord Message Speed Data (from {len(speeds)} points):")
            print(f"  Calculated avg_speed: {avg_speed:.2f} m/s ({avg_speed_kmh:.2f} km/h)")
            print(f"  Calculated max_speed: {max_speed:.2f} m/s ({max_speed_kmh:.2f} km/h)")
            
            # Show sample of individual speeds
            print(f"\nSample of instantaneous speeds (first 5):")
            for i, speed in enumerate(speeds[:5]):
                speed_kmh = speed * 3.6
                print(f"  Record #{i+1}: {speed:.2f} m/s ({speed_kmh:.2f} km/h)")
        else:
            print("\nNo speed data found in Record messages")
    else:
        print("\nNo Record Messages found")


def main():
    # Define the FIT files to compare (the ones you specified)
    working_fit_file = os.path.abspath("fit_files/indoor_cycling_20250503_144550.fit")
    non_working_fit_file = os.path.abspath("fit_files/indoor_cycling_20250503_150300.fit")
    
    print(f"Working FIT file path: {working_fit_file}")
    print(f"Non-working FIT file path: {non_working_fit_file}")
    
    # Ensure both files exist
    if not os.path.exists(working_fit_file):
        print(f"Error: Working FIT file not found: {working_fit_file}")
        return
    if not os.path.exists(non_working_fit_file):
        print(f"Error: Non-working FIT file not found: {non_working_fit_file}")
        return
    
    # Load and analyze the working FIT file
    try:
        working_fit = FitFile.from_file(working_fit_file)
        analyze_speed_data(working_fit, working_fit_file)
    except Exception as e:
        print(f"Error analyzing working file: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 80 + "\n")
    
    # Load and analyze the non-working FIT file
    try:
        non_working_fit = FitFile.from_file(non_working_fit_file)
        analyze_speed_data(non_working_fit, non_working_fit_file)
    except Exception as e:
        print(f"Error analyzing non-working file: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()