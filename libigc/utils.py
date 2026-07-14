from typing import NamedTuple

class HourMinuteSecond(NamedTuple):
    """A named tuple to represent hours, minutes and seconds."""
    hours: int
    minutes: int
    seconds: int

def _strip_non_printable_chars(string: str):
    """Filters a string removing non-printable characters.

    Args:
        string: A string to be filtered.

    Returns:
        A string, where non-printable characters are removed.
    """
    printable = set("0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKL"
                    "MNOPQRSTUVWXYZ!\"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~ ")

    printable_string = [x for x in string if x in printable]
    return ''.join(printable_string)


def _rawtime_float_to_hms(timef: float):
    """Converts time from floating point seconds to hours/minutes/seconds.

    Args:
        timef: A floating point time in seconds to be converted

    Returns:
        A namedtuple with hours, minutes and seconds elements
    """
    time = int(round(timef))
    return HourMinuteSecond((time // 3600), (time % 3600) // 60, time % 60)