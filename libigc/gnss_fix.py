import re
from .lib import geo
from libigc.utils import _rawtime_float_to_hms


class GNSSFix:
    """Stores single GNSS flight recorder fix (a B-record).

    Raw attributes (i.e. attributes read directly from the B record):
        rawtime: a float, time since last midnight, UTC, seconds
        lat: a float, latitude in degrees
        lon: a float, longitude in degrees
        validity: a string, GPS validity information from flight recorder
        press_alt: a float, pressure altitude, meters
        gnss_alt: a float, GNSS altitude, meters
        extras: a string, B record extensions

    Derived attributes:
        index: an integer, the position of the fix in the IGC file
        timestamp: a float, true timestamp (since epoch), UTC, seconds
        alt: a float, either press_alt or gnss_alt
        gsp: a float, current ground speed, km/h
        bearing: a float, aircraft bearing, in degrees
        bearing_change_rate: a float, bearing change rate, degrees/second
        flying: a bool, whether this fix is during a flight
        circling: a bool, whether this fix is inside a thermal
    """

    @staticmethod
    def build_from_B_record(B_record_line, index):
        """Creates GNSSFix object from IGC B-record line.

        Args:
            B_record_line: a string, B record line from an IGC file
            index: the zero-based position of the fix in the parent IGC file

        Returns:
            The created GNSSFix object
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
        (hours, minutes, seconds,
         lat_deg, lat_min, lat_min_dec, lat_sign,
         lon_deg, lon_min, lon_min_dec, lon_sign,
         validity, press_alt, gnss_alt,
         extras) = match.groups()

        rawtime = (float(hours)*60.0 + float(minutes))*60.0 + float(seconds)

        lat = float(lat_deg)
        lat += float(lat_min) / 60.0
        lat += float(lat_min_dec) / 1000.0 / 60.0
        if lat_sign == 'S':
            lat = -lat

        lon = float(lon_deg)
        lon += float(lon_min) / 60.0
        lon += float(lon_min_dec) / 1000.0 / 60.0
        if lon_sign == 'W':
            lon = -lon

        press_alt = float(press_alt)
        gnss_alt = float(gnss_alt)

        return GNSSFix(rawtime, lat, lon, validity, press_alt, gnss_alt,
                       index, extras)

    def __init__(self, rawtime, lat, lon, validity, press_alt, gnss_alt,
                 index, extras):
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

    def set_flight(self, flight):
        """Sets parent Flight object."""
        self.flight = flight
        if self.flight.alt_source == "PRESS":
            self.alt = self.press_alt
        elif self.flight.alt_source == "GNSS":
            self.alt = self.gnss_alt
        else:
            assert(False)
        self.timestamp = self.rawtime + flight.date_timestamp

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return (
            "GNSSFix(rawtime=%02d:%02d:%02d, lat=%f, lon=%f, press_alt=%.1f, gnss_alt=%.1f)" %
            (_rawtime_float_to_hms(self.rawtime) +
             (self.lat, self.lon, self.press_alt, self.gnss_alt)))

    def bearing_to(self, other):
        """Computes bearing in degrees to another GNSSFix."""
        return geo.bearing_to(self.lat, self.lon, other.lat, other.lon)

    def distance_to(self, other):
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
            lat_sign = 'S'
        else:
            lat = self.lat
            lat_sign = 'N'
        lat = int(round(lat*60000.0))
        lat_deg = lat / 60000
        lat_min = (lat % 60000) / 1000
        lat_min_dec = lat % 1000

        if self.lon < 0.0:
            lon = -self.lon
            lon_sign = 'W'
        else:
            lon = self.lon
            lon_sign = 'E'
        lon = int(round(lon*60000.0))
        lon_deg = lon / 60000
        lon_min = (lon % 60000) / 1000
        lon_min_dec = lon % 1000

        validity = self.validity
        press_alt = int(self.press_alt)
        gnss_alt = int(self.gnss_alt)
        extras = self.extras

        return (
            "B" +
            "%02d%02d%02d" % (hours, minutes, seconds) +
            "%02d%02d%03d%s" % (lat_deg, lat_min, lat_min_dec, lat_sign) +
            "%03d%02d%03d%s" % (lon_deg, lon_min, lon_min_dec, lon_sign) +
            validity +
            "%05d%05d" % (press_alt, gnss_alt) +
            extras)
