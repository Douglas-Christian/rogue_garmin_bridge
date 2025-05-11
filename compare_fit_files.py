#!/usr/bin/env python3
"""
Script to compare two FIT files with focus on device identification and training load-related fields.
Also compares speed, power, and cadence data points to help debug Garmin Connect import issues.
"""

import os
import sys
from fit_tool.fit_file import FitFile
from fit_tool.profile.messages.file_id_message import FileIdMessage
from fit_tool.profile.messages.device_info_message import DeviceInfoMessage
from fit_tool.profile.messages.session_message import SessionMessage
from fit_tool.profile.messages.record_message import RecordMessage
from fit_tool.profile.profile_type import Manufacturer
import argparse
from collections import Counter


def print_message_field(message, field_name, indent=0):
    """Print a field from a message with appropriate indentation."""
    if hasattr(message, field_name):
        value = getattr(message, field_name)
        if field_name == 'manufacturer' and isinstance(value, int):
            try:
                manufacturer_name = Manufacturer(value).name
                print(f"{' ' * indent}{field_name}: {value} ({manufacturer_name})")
                return
            except:
                pass
        print(f"{' ' * indent}{field_name}: {value}")
    else:
        print(f"{' ' * indent}{field_name}: Not present")


def print_device_info(fit_file, file_path):
    """Print device identification information from a FIT file."""
    print(f"\nAnalyzing FIT file: {os.path.basename(file_path)}")
    print("=" * 80)
    
    # Get all messages from the FIT file
    messages = []
    for record in fit_file.records:
        message = record.message
        messages.append(message)
    
        for msg in file_id_messages:
            print_message_field(msg, 'type', 4)
            print_message_field(msg, 'manufacturer', 4)
            print_message_field(msg, 'product', 4)
            print_message_field(msg, 'serial_number', 4)
            print_message_field(msg, 'time_created', 4)
            print_message_field(msg, 'number', 4)
    else:
        print("\nNo File ID Message found")
    
    # Look for DeviceInfoMessage
    device_info_messages = [msg for msg in messages if isinstance(msg, DeviceInfoMessage)]
    if device_info_messages:
        print("\nDevice Info Messages:")
        for i, msg in enumerate(device_info_messages):
            print(f"\n  Device Info #{i+1}:")
            print_message_field(msg, 'device_index', 4)
            print_message_field(msg, 'manufacturer', 4)
            print_message_field(msg, 'product', 4)
            print_message_field(msg, 'product_name', 4)
            print_message_field(msg, 'serial_number', 4)
            print_message_field(msg, 'hardware_version', 4)
            print_message_field(msg, 'software_version', 4)
            print_message_field(msg, 'device_type', 4)
            print_message_field(msg, 'source_type', 4)
    else:
        print("\nNo Device Info Messages found")
    
    # Look for SessionMessage to check for training load relevant fields
    session_messages = [msg for msg in messages if isinstance(msg, SessionMessage)]
    if session_messages:
        print("\nSession Message (Training Load Relevant Fields):")
        for msg in session_messages:
            print_message_field(msg, 'sport', 4)
            print_message_field(msg, 'sub_sport', 4)
            print_message_field(msg, 'total_training_effect', 4)
            print_message_field(msg, 'total_anaerobic_training_effect', 4)
            print_message_field(msg, 'threshold_power', 4)
            print_message_field(msg, 'normalized_power', 4)
            print_message_field(msg, 'training_stress_score', 4)
            print_message_field(msg, 'intensity_factor', 4)
            
            # Not directly training load but relevant
            print_message_field(msg, 'avg_power', 4)
            print_message_field(msg, 'max_power', 4)
            print_message_field(msg, 'total_work', 4)
            print_message_field(msg, 'avg_heart_rate', 4)
            print_message_field(msg, 'max_heart_rate', 4)
    else:
        print("\nNo Session Messages found")


def analyze_all_messages(fit_file, file_path):
    """Print all message types present in the FIT file."""
    message_types = {}
    
    # Get all messages from the FIT file
    for record in fit_file.records:
        message = record.message
        message_type = type(message).__name__
        if message_type not in message_types:
            message_types[message_type] = 0
        message_types[message_type] += 1
    
    print(f"\nAll Message Types in {os.path.basename(file_path)}:")
    for msg_type, count in sorted(message_types.items()):
        print(f"  {msg_type}: {count}")


def main():
    # Define the full paths to the FIT files using absolute paths
    reference_fit_file = os.path.abspath(os.path.join("fit_files", "fitfiletools.fit"))
    generated_fit_file = os.path.abspath(os.path.join("fit_files", "indoor_cycling_20250503_171737.fit"))
    
    print(f"Reference FIT file path: {reference_fit_file}")
    print(f"Generated FIT file path: {generated_fit_file}")
    
    # Ensure both files exist
    if not os.path.exists(reference_fit_file):
        print(f"Error: Reference FIT file not found: {reference_fit_file}")
        return
    if not os.path.exists(generated_fit_file):
        print(f"Error: Generated FIT file not found: {generated_fit_file}")
        return
    
    # Load and analyze the reference FIT file
    try:
        ref_fit = FitFile.from_file(reference_fit_file)
        print_device_info(ref_fit, reference_fit_file)
        analyze_all_messages(ref_fit, reference_fit_file)
    except Exception as e:
        print(f"Error analyzing reference file: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 80 + "\n")
    
    # Load and analyze the generated FIT file
    try:
        gen_fit = FitFile.from_file(generated_fit_file)
        print_device_info(gen_fit, generated_fit_file)
        analyze_all_messages(gen_fit, generated_fit_file)
    except Exception as e:
        print(f"Error analyzing generated file: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()