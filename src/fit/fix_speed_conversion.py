#!/usr/bin/env python3
"""
Script to fix speed unit conversion in FIT file converter

This script fixes the speed unit conversion issue in the FIT converter code:
- The application correctly stores speeds in kilometers per hour (km/h)
- The FIT file format requires speeds in meters per second (m/s)
- The current code doesn't perform the needed conversion, resulting in speeds 3.6x too high

This script adds the necessary conversion from km/h to m/s before storing values in FIT files.
"""

import os
import sys
import re
import shutil
from datetime import datetime

def backup_file(file_path):
    """Create a backup of a file before modifying it."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    backup_path = f"{file_path}.{timestamp}.bak"
    shutil.copy2(file_path, backup_path)
    print(f"Created backup: {backup_path}")
    return backup_path

def fix_speed_conversion():
    """
    Fix the speed unit conversion in fit_converter.py to properly convert km/h to m/s.
    
    The bug: Speeds are stored in km/h in the database but need to be converted to m/s for FIT files.
    Currently, the code directly assigns km/h values to FIT fields that expect m/s, making speeds 3.6x too high.
    """
    file_path = "fit_converter.py"
    
    # Make sure we're looking at the right file
    if not os.path.exists(file_path):
        file_path = os.path.join("src", "fit", "fit_converter.py")
        if not os.path.exists(file_path):
            print(f"Could not find {file_path}. Please run this script from the project root directory.")
            return False
    
    # Create a backup of the original file
    backup_file(file_path)
    
    # Read the file content
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Replace the instantaneous speed handling in record messages
    # Find the pattern: "if speeds[i] is not None:" followed by speed assignment
    record_speed_pattern = r'if speeds\[i\] is not None:[^\n]+\n[^\n]+speed = '
    record_speed_replacement = """if speeds[i] is not None:
                    # Convert from km/h to m/s (FIT files require speed in m/s)
                    current_speed_kmh = float(speeds[i])
                    current_speed_mps = current_speed_kmh / 3.6  # Convert km/h to m/s
                    record_mesg.speed = """
    
    content = re.sub(record_speed_pattern, record_speed_replacement, content)
    
    # Enhanced speed is always set after speed, so we need to modify that line too
    enhanced_speed_pattern = r'record_mesg\.enhanced_speed = current_speed_mps'
    if 'enhanced_speed' in content and enhanced_speed_pattern not in content:
        enhanced_speed_pattern = r'record_mesg\.enhanced_speed = \S+'
        content = re.sub(enhanced_speed_pattern, 'record_mesg.enhanced_speed = current_speed_mps', content)
    
    # Replace the avg_speed handling in lap message
    lap_avg_speed_pattern = r'if avg_speed is not None: lap_mesg\.avg_speed = float\(avg_speed\)'
    lap_avg_speed_replacement = """if avg_speed is not None: 
                # Convert from km/h to m/s (FIT files require speed in m/s)
                avg_speed_kmh = float(avg_speed)
                avg_speed_mps = avg_speed_kmh / 3.6  # Convert km/h to m/s
                lap_mesg.avg_speed = avg_speed_mps"""
    
    content = re.sub(lap_avg_speed_pattern, lap_avg_speed_replacement, content)
    
    # Replace the max_speed handling in lap message
    lap_max_speed_pattern = r'if max_speed is not None: lap_mesg\.max_speed = float\(max_speed\)'
    lap_max_speed_replacement = """if max_speed is not None: 
                # Convert from km/h to m/s (FIT files require speed in m/s)
                max_speed_kmh = float(max_speed)
                max_speed_mps = max_speed_kmh / 3.6  # Convert km/h to m/s
                lap_mesg.max_speed = max_speed_mps"""
    
    content = re.sub(lap_max_speed_pattern, lap_max_speed_replacement, content)
    
    # Replace the avg_speed handling in session message
    session_avg_speed_pattern = r'if avg_speed is not None: session_mesg\.avg_speed = float\(avg_speed\)'
    session_avg_speed_replacement = """if avg_speed is not None: 
                # Convert from km/h to m/s (FIT files require speed in m/s)
                avg_speed_kmh = float(avg_speed)
                avg_speed_mps = avg_speed_kmh / 3.6  # Convert km/h to m/s
                session_mesg.avg_speed = avg_speed_mps"""
    
    content = re.sub(session_avg_speed_pattern, session_avg_speed_replacement, content)
    
    # Replace the max_speed handling in session message
    session_max_speed_pattern = r'if max_speed is not None: session_mesg\.max_speed = float\(max_speed\)'
    session_max_speed_replacement = """if max_speed is not None: 
                # Convert from km/h to m/s (FIT files require speed in m/s)
                max_speed_kmh = float(max_speed)
                max_speed_mps = max_speed_kmh / 3.6  # Convert km/h to m/s
                session_mesg.max_speed = max_speed_mps"""
    
    content = re.sub(session_max_speed_pattern, session_max_speed_replacement, content)
    
    # Write the updated content back to the file
    with open(file_path, 'w') as f:
        f.write(content)
    
    # Find out how many changes were made
    changes = 0
    if record_speed_replacement in content:
        changes += 1
    if lap_avg_speed_replacement in content:
        changes += 1
    if lap_max_speed_replacement in content:
        changes += 1
    if session_avg_speed_replacement in content:
        changes += 1
    if session_max_speed_replacement in content:
        changes += 1
    
    if changes == 0:
        print("Warning: No changes were made. The patterns may not have matched.")
        print("Please check the fit_converter.py file manually.")
        return False
    else:
        print(f"Successfully updated {file_path}")
        print(f"Made {changes} changes to fix speed unit conversion from km/h to m/s.")
        return True

if __name__ == "__main__":
    print("Starting speed unit conversion fix...")
    success = fix_speed_conversion()
    if success:
        print("Fix completed successfully!")
    else:
        print("Fix could not be applied automatically. Please check the code manually.")
