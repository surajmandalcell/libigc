import json
import sys
from pathlib import Path

try:
    import tkinter as tk
    from tkinter import filedialog
except ImportError:
    print("Error: tkinter is not installed.")
    sys.exit(1)

from libigc.core import Flight


def select_file_gui():
    try:
        current_dir = Path(__file__).parent.resolve()

        root = tk.Tk()
        root.withdraw()
        file_path = filedialog.askopenfilename(
            initialdir=current_dir,
            filetypes=[
                ("IGC files", "*.igc"),
                ("IGC files", "*.IGC"),
                ("All files", "*.*"),
            ],
            title="Select an IGC file",
        )

        if not file_path:
            print("No file selected. Exiting gracefully.")
            sys.exit(0)

        return file_path

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
    output = [f"Analyzed file: {igc_file_path}"]
    for attr in dir(flight):
        if not attr.startswith("_") and not callable(getattr(flight, attr)):
            value = getattr(flight, attr)
            output.append(f"{attr}: {value}")

    # Write the output to dist/test_output.txt
    output_path = Path("dist/test_output.txt")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w") as f:
        f.write("\n".join(output))

    # Write the raw output to dist/og.txt (more detailed)
    raw_output_path = Path("dist/og1.txt")
    with raw_output_path.open("w") as f:
        f.write(json.dumps(flight.__dict__, indent=4, default=str))

    print(f"Test output written to {output_path}")
    print(f"Raw output written to {raw_output_path}")


if __name__ == "__main__":
    test_igc_parser()
