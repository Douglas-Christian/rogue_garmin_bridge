#!/usr/bin/env python3
"""
Script to manually fix the fit_converter.py file to properly convert speed units from km/h to m/s

This script applies direct replacements to the file to fix the speed unit conversion issues.
"""

import os
import shutil
from datetime import datetime

def backup_file(file_path):
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    backup_path = f"{file_path}.{timestamp}.bak"
    shutil.copy2(file_path, backup_path)
    print(f"Created backup: {backup_path}")
    return backup_path

def main():
    filepath = os.path.join("src", "fit", "fit_converter.py")
    if not os.path.exists(filepath):
        print(f"File {filepath} not found!")
        return
    
    # Create a backup
    backup_file(filepath)
    
    # Read the file
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Make modifications for record message
    content = content.replace(
        'if speeds[i] is not None:\n                    current_speed_mps = float(speeds[i])',
        'if speeds[i] is not None:\n                    # Convert from km/h to m/s (FIT files require speed in m/s)\n                    current_speed_kmh = float(speeds[i])\n                    current_speed_mps = current_speed_kmh / 3.6  # Convert km/h to m/s'
    )
    
    # Make modifications for lap message avg_speed
    content = content.replace(
        'if avg_speed is not None: lap_mesg.avg_speed = float(avg_speed)',
        'if avg_speed is not None: \n                # Convert from km/h to m/s (FIT files require speed in m/s)\n                avg_speed_kmh = float(avg_speed)\n                avg_speed_mps = avg_speed_kmh / 3.6  # Convert km/h to m/s\n                lap_mesg.avg_speed = avg_speed_mps'
    )
    
    # Make modifications for lap message max_speed
    content = content.replace(
        'if max_speed is not None: lap_mesg.max_speed = float(max_speed)',
        'if max_speed is not None: \n                # Convert from km/h to m/s (FIT files require speed in m/s)\n                max_speed_kmh = float(max_speed)\n                max_speed_mps = max_speed_kmh / 3.6  # Convert km/h to m/s\n                lap_mesg.max_speed = max_speed_mps'
    )
    
    # Make modifications for session message avg_speed
    content = content.replace(
        'if avg_speed is not None: session_mesg.avg_speed = float(avg_speed)',
        'if avg_speed is not None: \n                # Convert from km/h to m/s (FIT files require speed in m/s)\n                avg_speed_kmh = float(avg_speed)\n                avg_speed_mps = avg_speed_kmh / 3.6  # Convert km/h to m/s\n                session_mesg.avg_speed = avg_speed_mps'
    )
    
    # Make modifications for session message max_speed
    content = content.replace(
        'if max_speed is not None: session_mesg.max_speed = float(max_speed)',
        'if max_speed is not None: \n                # Convert from km/h to m/s (FIT files require speed in m/s)\n                max_speed_kmh = float(max_speed)\n                max_speed_mps = max_speed_kmh / 3.6  # Convert km/h to m/s\n                session_mesg.max_speed = max_speed_mps'
    )
    
    # Write the modified content back
    with open(filepath, 'w') as f:
        f.write(content)
    
    print(f"Successfully updated {filepath}")

if __name__ == "__main__":
    main()
