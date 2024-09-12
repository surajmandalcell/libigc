import os


def get_test_data_path(filename):
    """Returns the absolute path to a test data file."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(current_dir, "..", "testfiles", filename)
