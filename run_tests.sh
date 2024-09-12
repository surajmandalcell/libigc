#!/bin/bash
set -e

# Change to the directory containing this script
cd "$(dirname "$0")"

echo "Running tests with python3"
if [ -z "$1" ]; then
    # No argument provided - run all tests
    python3 -m unittest discover tests
else
    python3 -m unittest tests.$1
fi