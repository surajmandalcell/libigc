"""Cross-checks libigc against an independent implementation.

Every other test in this suite asserts against values produced by libigc
itself, or against hand-picked constants. That catches regressions but not a
formula that has been wrong from the start. These tests re-derive the same
quantities in `tests/oracle.py` from the IGC spec and from first principles,
using deliberately different techniques, and require the two to agree across
every B record in every test file.
"""

import glob
import os
import unittest
from decimal import Decimal

from libigc.core import Flight
from libigc.gnss_fix import GNSSFix
from libigc.lib import dumpers, geo
from tests import oracle

TEST_FILES = sorted(
    glob.glob(os.path.join(os.path.dirname(__file__), "testfiles", "*.igc"))
)


def _flights():
    for path in TEST_FILES:
        flight = Flight.create_from_file(path)
        if flight.valid:
            yield os.path.basename(path), flight


class TestBRecordParsingAgainstOracle(unittest.TestCase):
    def testEveryBRecordInEveryTestFile(self):
        checked = 0
        for path in TEST_FILES:
            with open(path, errors="replace") as handle:
                for line in handle:
                    line = line.rstrip("\r\n")
                    want = oracle.parse_b_record(line)
                    if want is None:
                        continue
                    checked += 1
                    got = GNSSFix.build_from_B_record(line, 0)
                    self.assertIsNotNone(got, line)
                    self.assertAlmostEqual(want["rawtime"], got.rawtime, places=9)
                    self.assertLess(
                        abs(Decimal(repr(got.lat)) - want["lat"]), Decimal("1e-9"), line
                    )
                    self.assertLess(
                        abs(Decimal(repr(got.lon)) - want["lon"]), Decimal("1e-9"), line
                    )
                    self.assertEqual(want["validity"], str(got.validity), line)
                    self.assertEqual(want["press_alt"], got.press_alt, line)
                    self.assertEqual(want["gnss_alt"], got.gnss_alt, line)
                    self.assertEqual(want["extras"], got.extras, line)
        self.assertGreater(checked, 20000)


class TestGeoAgainstOracle(unittest.TestCase):
    # Published great circle distances. These anchor the module to the real
    # world, not just to a second derivation of the same idea.
    REFERENCE_KM = [
        ("London-New York", 51.5074, -0.1278, 40.7128, -74.0060, 5570.0),
        ("Sydney-Tokyo", -33.8688, 151.2093, 35.6895, 139.6917, 7823.0),
        ("Quito-Nairobi", -0.1807, -78.4678, -1.2921, 36.8219, 12816.0),
    ]

    def testPublishedDistances(self):
        for name, lat1, lon1, lat2, lon2, published in self.REFERENCE_KM:
            got = geo.earth_distance(lat1, lon1, lat2, lon2)
            self.assertLess(abs(got - published) / published, 0.005, name)

    def testDistanceAndBearingAlongRealTracks(self):
        for name, flight in _flights():
            for i in range(0, len(flight.fixes) - 1, 37):
                a, b = flight.fixes[i], flight.fixes[i + 1]
                want = oracle.earth_distance_km(a.lat, a.lon, b.lat, b.lon)
                got = geo.earth_distance(a.lat, a.lon, b.lat, b.lon)
                self.assertLess(abs(got - want), 1e-9 + 1e-9 * want, name)

                want = oracle.initial_bearing(a.lat, a.lon, b.lat, b.lon)
                got = geo.bearing_to(a.lat, a.lon, b.lat, b.lon)
                self.assertLess(abs(got - want), 1e-9, name)

    def testSphereAngleAgainstBearingDifference(self):
        cases = [
            (0.0, 10.0, 0.0, 0.0, -20.0, 0.0, 90.0),
            (0.0, 5.0, 0.0, 0.0, 0.0, -5.0, 180.0),
        ]
        for lat1, lon1, lat, lon, lat2, lon2, expected in cases:
            got = geo.sphere_angle(lat1, lon1, lat, lon, lat2, lon2)
            want = oracle.vertex_angle(lat1, lon1, lat, lon, lat2, lon2)
            self.assertAlmostEqual(expected, got, places=6)
            self.assertAlmostEqual(want, got, places=6)


class TestDerivedValuesAgainstOracle(unittest.TestCase):
    def testGroundSpeedAndTimestamp(self):
        for name, flight in _flights():
            for i in range(1, len(flight.fixes), 53):
                a, b = flight.fixes[i - 1], flight.fixes[i]
                dt = b.rawtime - a.rawtime
                want = (
                    0.0
                    if abs(dt) < 1e-5
                    else oracle.earth_distance_km(a.lat, a.lon, b.lat, b.lon)
                    / dt
                    * 3600.0
                )
                self.assertLess(abs(b.ground_speed - want), 1e-6 + 1e-9 * want, name)
                self.assertEqual(b.ground_speed, b.gsp)
                self.assertAlmostEqual(
                    b.rawtime + flight.date_timestamp, b.timestamp, places=6
                )

    def testHfdteDates(self):
        checked = 0
        for path in TEST_FILES:
            with open(path, errors="replace") as handle:
                header = [
                    ln.rstrip("\r\n") for ln in handle if ln[0:5].upper() == "HFDTE"
                ]
            if not header:
                continue
            want = oracle.parse_hfdte(header[0])
            flight = Flight.create_from_file(path)
            if want is None or not flight.valid:
                continue
            checked += 1
            self.assertEqual(want, flight.date_timestamp, header[0])
        self.assertGreater(checked, 0)

    def testThermalAndGlideMetrics(self):
        for _name, flight in _flights():
            for thermal in flight.thermals:
                dt = thermal.exit_fix.timestamp - thermal.enter_fix.timestamp
                dalt = thermal.exit_fix.alt - thermal.enter_fix.alt
                self.assertAlmostEqual(dt, thermal.time_change(), places=6)
                self.assertAlmostEqual(dalt, thermal.alt_change(), places=6)
                if dt:
                    self.assertAlmostEqual(
                        dalt / dt, thermal.vertical_velocity(), places=9
                    )
            for glide in flight.glides:
                dt = glide.exit_fix.timestamp - glide.enter_fix.timestamp
                self.assertAlmostEqual(dt, glide.time_change(), places=6)
                self.assertAlmostEqual(
                    glide.track_length / (dt / 3600.0), glide.speed(), places=6
                )


class TestExportFieldsAgainstOracle(unittest.TestCase):
    def testWptAndCupCoordinatesAndBRecordClock(self):
        for name, flight in _flights():
            for fix in flight.fixes[::29]:
                lat = dumpers._degrees_float_to_degrees_minutes_seconds(fix.lat, 6000)
                lon = dumpers._degrees_float_to_degrees_minutes_seconds(
                    fix.lon, 6000, long=True
                )
                got = (
                    f"{lat.hemisphere} {lat.degrees:02d} {lat.minutes:02d} "
                    f"{lat.units // 100:02d}.{lat.units % 100:02d}"
                )
                self.assertEqual(oracle.wpt_coord(fix.lat, False), got, name)
                got = (
                    f"{lon.hemisphere} {lon.degrees:03d} {lon.minutes:02d} "
                    f"{lon.units // 100:02d}.{lon.units % 100:02d}"
                )
                self.assertEqual(oracle.wpt_coord(fix.lon, True), got, name)

                lat = dumpers._degrees_float_to_degrees_minutes_seconds(fix.lat, 1000)
                lon = dumpers._degrees_float_to_degrees_minutes_seconds(
                    fix.lon, 1000, long=True
                )
                got = (
                    f"{lat.degrees:02d}{lat.minutes:02d}"
                    f".{lat.units:03d}{lat.hemisphere}"
                )
                self.assertEqual(oracle.cup_coord(fix.lat, False), got, name)
                got = (
                    f"{lon.degrees:03d}{lon.minutes:02d}"
                    f".{lon.units:03d}{lon.hemisphere}"
                )
                self.assertEqual(oracle.cup_coord(fix.lon, True), got, name)

                self.assertEqual(
                    oracle.b_record_time(fix.rawtime), fix.to_B_record()[1:7], name
                )


if __name__ == "__main__":
    unittest.main()
