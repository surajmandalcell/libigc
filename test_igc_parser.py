import os
import sys
from pathlib import Path

# Adjust this import path based on your actual project structure
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from libigc.core import Flight

def select_file_gui():
    try:
        current_dir = os.path.abspath(os.path.dirname(__file__))
        
        if sys.platform.startswith('win'):
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            file_path = filedialog.askopenfilename(
                initialdir=current_dir,
                filetypes=[
                    ("IGC files", "*.igc"),
                    ("IGC files", "*.IGC"),
                    ("All files", "*.*")
                ],
                title="Select an IGC file"
            )
        else:  # Assume WSL/Linux
            from tkinter import Tk
            from tkfilebrowser import askopenfilename
            root = Tk()
            root.withdraw()
            file_path = askopenfilename(
                initialdir=current_dir,
                filetypes=[
                    ("IGC files", "*.igc"),
                    ("IGC files", "*.IGC"),
                    ("All files", "*")
                ],
                title="Select an IGC file"
            )
        
        if not file_path:
            print("No file selected. Exiting gracefully.")
            sys.exit(0)
        
        return file_path
    except ImportError as e:
        print(f"Error importing GUI libraries: {e}")
        print("Please ensure tkinter and tkfilebrowser are installed.")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)

def test_igc_parser():
    # Try to use GUI file selection
    igc_file_path = select_file_gui()

    # Ensure the file exists
    if not Path(igc_file_path).exists():
        print(f"Error: File not found at {igc_file_path}")
        sys.exit(1)

    # Create a Flight object from the IGC file
    flight = Flight.create_from_file(igc_file_path)

    # Prepare the output
    output = []
    output.append(f"Analyzed file: {igc_file_path}")
    output.append(f"Flight validity: {flight.valid}")
    output.append(f"Number of fixes: {len(flight.fixes)}")
    
    if hasattr(flight, 'thermals'):
        output.append(f"Number of thermals: {len(flight.thermals)}")
    
    if hasattr(flight, 'glides'):
        output.append(f"Number of glides: {len(flight.glides)}")
    
    if hasattr(flight, 'takeoff_fix'):
        output.append(f"Takeoff time: {flight.takeoff_fix.rawtime}")
    
    if hasattr(flight, 'landing_fix'):
        output.append(f"Landing time: {flight.landing_fix.rawtime}")
    
    output.append("Flight notes:")
    for note in flight.notes:
        output.append(f"  - {note}")

    # Write the output to dist/test_output.txt
    output_path = Path('dist/test_output.txt')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open('w') as f:
        f.write('\n'.join(output))

    print(f"Test output written to {output_path}")

if __name__ == "__main__":
    test_igc_parser()