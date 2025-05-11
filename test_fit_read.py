import fitdecode
import os
from pathlib import Path

def main():
    # File paths
    fit_files_dir = Path('fit_files')
    reference_file = fit_files_dir / 'fitfiletools.fit'
    
    if not os.path.exists(reference_file):
        print(f"Reference file not found: {reference_file}")
        return
    
    print(f"File exists: {reference_file}, size: {os.path.getsize(reference_file)} bytes")
    
    try:
        with fitdecode.FitReader(reference_file) as fit:
            message_count = 0
            for frame in fit:
                if isinstance(frame, fitdecode.FitDataMessage):
                    message_count += 1
                    if message_count <= 3:  # Only show first 3 messages
                        print(f"Message: {frame.name}")
                        for field in frame.fields:
                            print(f"  - {field.name}: {field.value}")
            
            print(f"Total messages found: {message_count}")
    except Exception as e:
        print(f"Error reading FIT file: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
