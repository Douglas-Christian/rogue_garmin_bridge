# Fix for fit_converter.py

import os
import sys
import shutil
from datetime import datetime

# Add the project root to the path so we can use absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

def backup_file(file_path):
    """Create a backup of a file before modifying it."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    backup_path = f"{file_path}.{timestamp}.bak"
    shutil.copy2(file_path, backup_path)
    print(f"Created backup: {backup_path}")
    return backup_path

def fix_record_message_creation():
    """
    Fix the record message creation in fit_converter.py to ensure speed, cadence, and power are always included.
    
    This function modifies the Record message creation code to always include speed, cadence, and power in every
    record message, even if the data is missing or zero.
    """
    file_path = os.path.join("src", "fit", "fit_converter.py")
    
    # Create a backup of the original file
    backup_file(file_path)
    
    # Read the file content
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Find the Record message creation section
    # This is a simplified approach - in a real implementation, we'd use a proper Python parser
    # to avoid modifying code in unexpected ways
    
    # Look for patterns that indicate Record message creation
    record_msg_patterns = [
        "record_msg = RecordMessage()",
        "for i in range(len(timestamps)):",
    ]
    
    # Create the fixed code snippet
    fixed_record_code = """
                    # Set power - use instantaneous power for record messages
                    # Always include power (even if missing or zero)
                    record_msg.power = int(powers[i]) if i < len(powers) else 0
                    
                    # Set cadence - use instantaneous cadence for record messages
                    # Always include cadence (even if missing or zero)
                    record_msg.cadence = int(cadences[i]) if i < len(cadences) else 0
                    
                    # Set heart rate
                    if i < len(heart_rates) and heart_rates[i] > 0:
                        record_msg.heart_rate = int(heart_rates[i])
                    
                    # Set speed - use instantaneous speed for record messages
                    # Always include speed (even if missing or zero)
                    if i < len(speeds):
                        # Convert km/h to m/s (using proper conversion, no extra scaling)
                        speed_ms = speeds[i] * 1000 / 3600  # km/h to m/s conversion
                        record_msg.speed = int(speed_ms)
                        all_speeds.append(speeds[i])  # Store for average calculation
                    else:
                        # Default to zero speed if no data available
                        record_msg.speed = 0
                        all_speeds.append(0)
                    
                    # Set distance
                    if i < len(distances):
                        record_msg.distance = float(distances[i])
    """
    
    # Find the existing code for Record message field setting
    start_pattern = "# Set power - use instantaneous power for record messages"
    end_pattern = "# Set distance"
    
    # Replace the code
    if start_pattern in content and end_pattern in content:
        start_idx = content.find(start_pattern)
        # Find the end pattern after the start pattern
        end_search_content = content[start_idx:]
        end_pattern_offset = end_search_content.find(end_pattern)
        end_idx = start_idx + end_pattern_offset + len(end_pattern)
        
        # Only replace up to the end pattern to keep the rest of the line
        replaced_content = content[:start_idx] + fixed_record_code + content[end_idx:]
        
        # Write the updated content back to the file
        with open(file_path, 'w') as f:
            f.write(replaced_content)
        
        print(f"Successfully updated {file_path}")
        print("Record message creation code has been fixed to always include speed, cadence, and power.")
        return True
    else:
        print(f"Could not find the record message creation section in {file_path}")
        print("Please modify the file manually to ensure speed, cadence, and power are always included.")
        return False

if __name__ == "__main__":
    print("Starting FIT converter fix...")
    success = fix_record_message_creation()
    if success:
        print("Fix completed successfully!")
    else:
        print("Fix could not be applied automatically. Please check the code manually.")
