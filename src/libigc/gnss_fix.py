from __future__ import annotations

import re
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # `core` imports `GNSSFix`, and we need `Flight` for type hinting.
    # This if TYPE_CHECKING block avoids circular import issues.
    from libigc.core import Flight
from libigc.utils import _rawtime_float_to_hms

from .lib import geo


class FixValidity(StrEnum):
    A = "A"  # valid 3D fix
    V = "V"  # nav warning (2D fix or position may be unreliable)


class AltitudeSource(StrEnum):
    PRESSURE = "PRESS"
    GNSS = "GNSS"


class GNSSFix:
    """Stores single GNSS flight recorder fix (a B-record).

    Raw attributes (i.e. attributes read directly from the B record):
        rawtime: a float, time since last midnight, UTC, seconds
        lat: a float, latitude in degrees
        lon: a float, longitude in degrees
        validity: a FixValidity, GPS validity information from flight recorder
        press_alt: a float, pressure altitude, meters
        gnss_alt: a float, GNSS altitude, meters
        extras: a string, B record extensions

    Derived attributes:
        index: an integer, the position of the fix in the IGC file
        timestamp: a float, true timestamp (since epoch), UTC, seconds
        alt: a float, either press_alt or gnss_alt
        ground_speed: a float, current ground speed, km/h
        bearing: a float, aircraft bearing, in degrees
        bearing_change_rate: a float, bearing change rate, degrees/second
        flying: a bool, whether this fix is during a flight
        circling: a bool, whether this fix is inside a thermal
    """

    index: int
    timestamp: float
    alt: float
    ground_speed: float
    bearing: float
    bearing_change_rate: float
    flying: bool
    circling: bool

    @staticmethod
    def build_from_B_record(B_record_line: str, index: int) -> GNSSFix | None:
        """Creates GNSSFix object from IGC B-record line.

        Args:
            B_record_line: a string, B record line from an IGC file
            index: the zero-based position of the fix in the parent IGC file

        Returns:
            The created GNSSFix object, or None if the line is not
            a valid B record.
        """
        match = re.match(
            r"^B"
            + r"(\d\d)(\d\d)(\d\d)"
            + r"(\d\d)(\d\d)(\d\d\d)([NS])"
            + r"(\d\d\d)(\d\d)(\d\d\d)([EW])"
            + r"([AV])"
            + r"([-\d]\d\d\d\d)"
            + r"([-\d]\d\d\d\d)"
            + r"([0-9a-zA-Z\-]*).*$",
            B_record_line,
        )
        if match is None:
            return None
        (
            hours,
            minutes,
            seconds,
            lat_deg,
            lat_min,
            lat_min_dec,
            lat_sign,
            lon_deg,
            lon_min,
            lon_min_dec,
            lon_sign,
            validity,
            press_alt,
            gnss_alt,
            extras,
        ) = match.groups()

        rawtime = (float(hours) * 60.0 + float(minutes)) * 60.0 + float(seconds)

        lat = float(lat_deg)
        lat += float(lat_min) / 60.0
        lat += float(lat_min_dec) / 1000.0 / 60.0
        if lat_sign == "S":
            lat = -lat

        lon = float(lon_deg)
        lon += float(lon_min) / 60.0
        lon += float(lon_min_dec) / 1000.0 / 60.0
        if lon_sign == "W":
            lon = -lon

        press_alt = float(press_alt)
        gnss_alt = float(gnss_alt)

        fix_validity = FixValidity(validity)

        return GNSSFix(
            rawtime, lat, lon, fix_validity, press_alt, gnss_alt, index, extras
        )

    def __init__(
        self,
        rawtime: float,
        lat: float,
        lon: float,
        validity: FixValidity,
        press_alt: float,
        gnss_alt: float,
        index: int,
        extras: str,
    ):
        """Initializer of GNSSFix. Not meant to be used directly."""
        self.rawtime = rawtime
        self.lat = lat
        self.lon = lon
        self.validity = validity
        self.press_alt = press_alt
        self.gnss_alt = gnss_alt
        self.index = index
        self.extras = extras
        self.flight = None

    # ------------------------------------------------------------------
    # Backwards compatibility: this attribute was called `gsp` before it
    # was renamed to `ground_speed`. Keep the old name as a read-only
    # alias so existing user code does not break; remove in a future
    # major release.
    # ------------------------------------------------------------------
    @property
    def gsp(self) -> float:
        return self.ground_speed

    def set_flight(self, flight: Flight):
        """Sets parent Flight object."""
        self.flight = flight
        if self.flight.alt_source == AltitudeSource.PRESSURE:
            self.alt = self.press_alt
        elif self.flight.alt_source == AltitudeSource.GNSS:
            self.alt = self.gnss_alt
        else:
            # This should never happen, but just in case, raise an exception.
            raise ValueError(f"Unknown altitude source: {self.flight.alt_source}.")
        self.timestamp = self.rawtime + flight.date_timestamp

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        hms = _rawtime_float_to_hms(self.rawtime)
        return (
            f"GNSSFix(rawtime={hms.hours:02d}:{hms.minutes:02d}:{hms.seconds:02d}, "
            f"lat={self.lat:f}, lon={self.lon:f}, "
            f"press_alt={self.press_alt:.1f}, gnss_alt={self.gnss_alt:.1f})"
        )

    def bearing_to(self, other: GNSSFix):
        """Computes bearing in degrees to another GNSSFix."""
        return geo.bearing_to(self.lat, self.lon, other.lat, other.lon)

    def distance_to(self, other: GNSSFix):
        """Computes great circle distance in kilometers to another GNSSFix."""
        return geo.earth_distance(self.lat, self.lon, other.lat, other.lon)

    def to_B_record(self):
        """Reconstructs an IGC B-record."""
        rawtime = int(self.rawtime)
        hours = rawtime / 3600
        minutes = (rawtime % 3600) / 60
        seconds = rawtime % 60

        if self.lat < 0.0:
            lat = -self.lat
            lat_sign = "S"
        else:
            lat = self.lat
            lat_sign = "N"
        lat = int(round(lat * 60000.0))
        lat_deg = lat / 60000
        lat_min = (lat % 60000) / 1000
        lat_min_dec = lat % 1000

        if self.lon < 0.0:
            lon = -self.lon
            lon_sign = "W"
        else:
            lon = self.lon
            lon_sign = "E"
        lon = int(round(lon * 60000.0))
        lon_deg = lon / 60000
        lon_min = (lon % 60000) / 1000
        lon_min_dec = lon % 1000

        validity = self.validity
        press_alt = int(self.press_alt)
        gnss_alt = int(self.gnss_alt)
        extras = self.extras

        return (
            "B"
            + f"{int(hours):02d}{int(minutes):02d}{int(seconds):02d}"
            + f"{int(lat_deg):02d}{int(lat_min):02d}{int(lat_min_dec):03d}{lat_sign}"
            + f"{int(lon_deg):03d}{int(lon_min):02d}{int(lon_min_dec):03d}{lon_sign}"
            + validity
            + f"{press_alt:05d}{gnss_alt:05d}"
            + extras
        )
