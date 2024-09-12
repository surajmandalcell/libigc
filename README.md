# libigc Library Documentation

## Table of Contents
1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Basic Usage](#basic-usage)
4. [Flight Analysis](#flight-analysis)
5. [Dumping Flight Data](#dumping-flight-data)
6. [Working with Tasks](#working-with-tasks)
7. [Command-line Usage](#command-line-usage)
8. [API Reference](#api-reference)
9. [Contributing](#contributing)
10. [License](#license)
11. [Additional Information](#additional-information)
12. [Original Author](#original-author)

## Introduction

libigc is a Python library designed to parse and analyze IGC (International Gliding Commission) flight recorder logs. It provides functionality to detect thermals, analyze flight patterns, and extract valuable information from glider flight data.

### Features
- Parses IGC files and extracts flight data
- Detects takeoff and landing
- Identifies thermals and glides
- Calculates various flight statistics
- Supports task validation
- Provides data export in various formats (WPT, CUP, KML, CSV)

## Installation

You can install libigc using pip:

```bash
pip install libigc
```

## Basic Usage

Here's a simple example of how to use libigc to parse an IGC file and extract basic flight information:

```python
from libigc import Flight

# Parse an IGC file
flight = Flight.create_from_file("path/to/your/file.igc")

# Check if the flight is valid
if flight.valid:
    print("Flight is valid")
    print(f"Takeoff time: {flight.takeoff_fix.timestamp}")
    print(f"Landing time: {flight.landing_fix.timestamp}")
    print(f"Number of thermals: {len(flight.thermals)}")
else:
    print("Flight is invalid")
    print("Reasons:", flight.notes)
```

## Flight Analysis

libigc provides various methods to analyze flight data:

```python
# Iterate through thermals
for i, thermal in enumerate(flight.thermals):
    print(f"Thermal {i+1}:")
    print(f"  Start time: {thermal.enter_fix.timestamp}")
    print(f"  End time: {thermal.exit_fix.timestamp}")
    print(f"  Duration: {thermal.time_change()} seconds")
    print(f"  Altitude gain: {thermal.alt_change()} meters")
    print(f"  Average vertical velocity: {thermal.vertical_velocity():.2f} m/s")

# Analyze glides
for i, glide in enumerate(flight.glides):
    print(f"Glide {i+1}:")
    print(f"  Start time: {glide.enter_fix.timestamp}")
    print(f"  End time: {glide.exit_fix.timestamp}")
    print(f"  Duration: {glide.time_change()} seconds")
    print(f"  Distance: {glide.track_length:.2f} km")
    print(f"  Average speed: {glide.speed():.2f} km/h")
    print(f"  Glide ratio: {glide.glide_ratio():.2f}")

# Access individual fixes
for fix in flight.fixes:
    print(f"Time: {fix.timestamp}, Lat: {fix.lat}, Lon: {fix.lon}, Alt: {fix.alt}")
```

## Dumping Flight Data

libigc provides functions to export flight data in various formats:

```python
from libigc.lib.dumpers import (
    dump_thermals_to_wpt_file,
    dump_thermals_to_cup_file,
    dump_flight_to_kml,
    dump_flight_to_csv
)

# Dump thermals to a .wpt file
dump_thermals_to_wpt_file(flight, "thermals.wpt")

# Dump thermals to a .cup file (SeeYou format)
dump_thermals_to_cup_file(flight, "thermals.cup")

# Dump flight to KML format
dump_flight_to_kml(flight, "flight.kml")

# Dump flight data to CSV files
dump_flight_to_csv(flight, "track.csv", "thermals.csv")
```

## Working with Tasks

libigc supports parsing and validating flight tasks:

```python
from libigc import Task, Turnpoint

# Create a task from an LK8000 task file
task = Task.create_from_lkt_file("task.lkt")

# Or create a task manually
turnpoints = [
    Turnpoint(lat=50.0, lon=14.0, radius=3.0, kind="start_exit"),
    Turnpoint(lat=51.0, lon=15.0, radius=0.5, kind="cylinder"),
    Turnpoint(lat=52.0, lon=16.0, radius=3.0, kind="goal_cylinder")
]
task = Task(turnpoints, start_time=36000, end_time=64800)  # 10:00 to 18:00

# Check if the flight completed the task
reached_turnpoints = task.check_flight(flight)
if len(reached_turnpoints) == len(task.turnpoints):
    print("Task completed!")
else:
    print(f"Reached {len(reached_turnpoints)} out of {len(task.turnpoints)} turnpoints")
```

## Command-line Usage

libigc comes with a demo script that can be run from the command line:

```bash
python -m libigc.examples.libigc_demo path/to/your/file.igc
```

This will print a summary of the flight and save thermal and track data to CSV files.

## API Reference

### Flight Class

The `Flight` class is the main entry point for working with IGC files.

#### Methods:
- `create_from_file(filename)`: Creates a Flight object from an IGC file.
- `_check_altitudes()`: Validates altitude data.
- `_compute_ground_speeds()`: Calculates ground speeds.
- `_compute_flight()`: Determines flying status for each fix.
- `_compute_circling()`: Detects circling (thermalling) behavior.
- `_find_thermals()`: Identifies thermal segments in the flight.

#### Attributes:
- `fixes`: List of GNSSFix objects.
- `thermals`: List of Thermal objects.
- `glides`: List of Glide objects.
- `takeoff_fix`: GNSSFix object representing takeoff.
- `landing_fix`: GNSSFix object representing landing.
- `alt_source`: Altitude data source ("PRESS" or "GNSS").
- `valid`: Boolean indicating if the flight data is valid.
- `notes`: List of notes about the flight data validity.

### GNSSFix Class

Represents a single fix in the IGC file.

#### Attributes:
- `timestamp`: Unix timestamp of the fix.
- `lat`: Latitude in degrees.
- `lon`: Longitude in degrees.
- `alt`: Altitude in meters.
- `gsp`: Ground speed in km/h.
- `bearing`: Aircraft bearing in degrees.
- `bearing_change_rate`: Rate of bearing change in degrees/second.
- `flying`: Boolean indicating if the aircraft is flying at this fix.
- `circling`: Boolean indicating if the aircraft is circling at this fix.

### Thermal Class

Represents a thermal detected in the flight.

#### Methods:
- `time_change()`: Duration of the thermal in seconds.
- `alt_change()`: Altitude gained in the thermal in meters.
- `vertical_velocity()`: Average vertical velocity in m/s.

#### Attributes:
- `enter_fix`: GNSSFix object at the start of the thermal.
- `exit_fix`: GNSSFix object at the end of the thermal.

### Glide Class

Represents a glide between thermals.

#### Methods:
- `time_change()`: Duration of the glide in seconds.
- `speed()`: Average ground speed during the glide in km/h.
- `alt_change()`: Altitude change during the glide in meters.
- `glide_ratio()`: Glide ratio (distance traveled / altitude lost).

#### Attributes:
- `enter_fix`: GNSSFix object at the start of the glide.
- `exit_fix`: GNSSFix object at the end of the glide.
- `track_length`: Total track length of the glide in kilometers.

### Task Class

Represents a flight task.

#### Methods:
- `create_from_lkt_file(filename)`: Creates a Task object from an LK8000 task file.
- `check_flight(flight)`: Checks if a Flight object has completed the task.

#### Attributes:
- `turnpoints`: List of Turnpoint objects.
- `start_time`: Task start time (seconds past midnight).
- `end_time`: Task end time (seconds past midnight).

### Turnpoint Class

Represents a single turnpoint in a task.

#### Methods:
- `in_radius(fix)`: Checks if a GNSSFix is within the turnpoint's radius.

#### Attributes:
- `lat`: Latitude of the turnpoint in degrees.
- `lon`: Longitude of the turnpoint in degrees.
- `radius`: Radius of the turnpoint cylinder in kilometers.
- `kind`: Type of turnpoint (e.g., "start_exit", "cylinder", "goal_cylinder").

## Contributing

If you find an IGC file that libigc doesn't handle correctly, please open an issue on the GitHub repository. Include the problematic IGC file and a description of the expected behavior.

To contribute code:

1. Fork the repository.
2. Create a new branch for your feature or bug fix.
3. Write tests for your changes.
4. Implement your changes.
5. Run the test suite to ensure all tests pass.
6. Submit a pull request with a clear description of your changes.

## License

libigc is released under the MIT License. See the LICENSE file in the repository for full details.

## Additional Information

To publish to PyPI, you'll need to:

- Register an account on PyPI
- Install twine: `pip install twine`
- Do `bumpversion patch --allow-dirty` (or minor/major) to update the version number in `setup.py`
- Build your distribution: `python setup.py sdist bdist_wheel`
- Upload to PyPI: `twine upload dist/*`

## Original Author

- [Marcin Osowski](https://github.com/marcin-osowski)
