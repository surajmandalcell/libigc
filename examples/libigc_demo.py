#!/usr/bin/env -S uv run --script
#
# This script demonstrates how to use the libigc library to parse an IGC file,
# extract flight details, and dump thermals and flight data to various output formats.
#
# If you have `uv` installed, this script can be run directly by just calling:
#     ./libigc_demo.py <input_file.igc> [<task_file>]
# `uv` will automatically install the required dependencies and run the script.
#
# /// script
# dependencies = ["libigc"]
# ///

import argparse
import sys
from itertools import zip_longest
from pathlib import Path

from libigc.core import Flight
import libigc.lib.dumpers as dumpers
from libigc.task import Task


def print_flight_details(flight: Flight):
    print(f"Flight: {flight}")
    print(f"Takeoff: {flight.takeoff_fix}")
    thermals = flight.thermals
    glides = flight.glides

    for i, (glide, thermal) in enumerate(zip_longest(glides, thermals)):
        if glide is not None:
            print(f"  glide[{i}]: {glide}")
        if thermal is not None:
            print(f"  thermal[{i}]: {thermal}")

    print(f"Landing: {flight.landing_fix}")


def dump_flight(flight: Flight, input_file: str, output_dir: Path | None = None):
    input_file_path = Path(input_file).expanduser().absolute()
    input_file_stem = input_file_path.stem

    wpt_file = f"{input_file_stem}-thermals.wpt"
    cup_file = f"{input_file_stem}-thermals.cup"
    thermals_csv_file = f"{input_file_stem}-thermals.csv"
    flight_csv_file = f"{input_file_stem}-flight.csv"
    kml_file = f"{input_file_stem}-flight.kml"

    if output_dir:
        output_dir = output_dir.expanduser().absolute()
        output_dir.mkdir(parents=True, exist_ok=True)
        wpt_file = str(output_dir / wpt_file)
        cup_file = str(output_dir / cup_file)
        thermals_csv_file = str(output_dir / thermals_csv_file)
        flight_csv_file = str(output_dir / flight_csv_file)
        kml_file = str(output_dir / kml_file)

    print(f"Dumping thermals to {wpt_file}, {cup_file} and {thermals_csv_file}")
    dumpers.dump_thermals_to_wpt_file(flight, wpt_file, True)
    dumpers.dump_thermals_to_cup_file(flight, cup_file)

    print(f"Dumping flight to {kml_file} and {flight_csv_file}")
    dumpers.dump_flight_to_csv(flight, flight_csv_file, thermals_csv_file)
    dumpers.dump_flight_to_kml(flight, kml_file)


def argparser():
    parser = argparse.ArgumentParser(description="Demo usage of the libigc library.")
    parser.add_argument(
        "input_file",
        type=str,
        help="Path to the input IGC file.",
    )
    parser.add_argument(
        "task_file",
        type=str,
        nargs="?",
        default=None,
        help="Optional path to the task LKT file.",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=None,
        help="Optional output directory for dumped files.",
    )
    return parser


def main():

    args = argparser().parse_args()
    input_file = args.input_file
    task_file = args.task_file

    flight = Flight.create_from_file(input_file)
    if not flight.valid:
        print("Provided flight is invalid:")
        print(flight.notes)
        sys.exit(1)

    print_flight_details(flight)
    dump_flight(flight, input_file, args.output_dir)

    if task_file:
        task = Task.create_from_lkt_file(task_file)
        reached_turnpoints = task.check_flight(flight)
        for t, fix in enumerate(reached_turnpoints):
            print(f"Turnpoint[{t}] achieved at: {fix.rawtime}")


if __name__ == "__main__":
    main()
