import os
import shutil
import tempfile
import unittest

from libigc import core as libigc
from libigc.lib import dumpers
from tests.test_utils import get_test_data_path


class TestDegreesSplit(unittest.TestCase):
    """The split has to carry, or the fixed width export fields overflow."""

    def split(self, dd, units_per_minute, long=False):
        return dumpers._degrees_float_to_degrees_minutes_seconds(
            dd, units_per_minute, long=long
        )

    def testCarriesIntoMinutes(self):
        # 16.65 degrees is exactly 16 deg 39 min. Rounding the seconds at
        # format time instead used to render this as 16 38 60.00.
        split = self.split(16.65, 6000)
        self.assertEqual((16, 39, 0), (split.degrees, split.minutes, split.units))

    def testCarriesIntoMinutesForCupUnits(self):
        # 0.049995 degrees rounds up to a whole 3 minutes. Rounding at format
        # time used to render the thousandths field as "1000", four digits in
        # a three digit slot.
        split = self.split(0.049995, 1000)
        self.assertEqual((0, 3, 0), (split.degrees, split.minutes, split.units))

    def testUnitsNeverReachAWholeMinute(self):
        # Sweep for any value that would overflow the sub-minute field.
        for units_per_minute in (6000, 1000):
            for i in range(200000):
                split = self.split(i * 90.0 / 200000, units_per_minute)
                self.assertLess(split.units, units_per_minute)
                self.assertLess(split.minutes, 60)

    def testHemispheres(self):
        self.assertEqual("N", self.split(1.0, 1000).hemisphere)
        self.assertEqual("S", self.split(-1.0, 1000).hemisphere)
        self.assertEqual("E", self.split(1.0, 1000, long=True).hemisphere)
        self.assertEqual("W", self.split(-1.0, 1000, long=True).hemisphere)


class TestDumpers(unittest.TestCase):
    def setUp(self):
        igc_file = get_test_data_path("napret.igc")
        self.flight = libigc.Flight.create_from_file(igc_file)
        self.tmp_output_dir = tempfile.mkdtemp()

    def tearDown(self):
        # Best-effort removal of temporary output files
        shutil.rmtree(self.tmp_output_dir, ignore_errors=True)

    def assertFileNotEmpty(self, filename):
        self.assertTrue(os.path.isfile(filename))
        self.assertGreater(os.path.getsize(filename), 0)

    def testWptDumpNotEmpty(self):
        tmp_wpt_file = os.path.join(self.tmp_output_dir, "thermals.wpt")
        dumpers.dump_thermals_to_wpt_file(self.flight, tmp_wpt_file)
        self.assertFileNotEmpty(tmp_wpt_file)

    def testCupDumpNotEmpty(self):
        tmp_cup_file = os.path.join(self.tmp_output_dir, "thermals.cup")
        dumpers.dump_thermals_to_cup_file(self.flight, tmp_cup_file)
        self.assertFileNotEmpty(tmp_cup_file)

    def testKmlDumpNotEmpty(self):
        tmp_kml_file = os.path.join(self.tmp_output_dir, "flight.kml")
        dumpers.dump_flight_to_kml(self.flight, tmp_kml_file)
        self.assertFileNotEmpty(tmp_kml_file)

    def testCsvDumpsNotEmpty(self):
        tmp_csv_track = os.path.join(self.tmp_output_dir, "flight.csv")
        tmp_csv_thermals = os.path.join(self.tmp_output_dir, "thermals.csv")
        dumpers.dump_flight_to_csv(self.flight, tmp_csv_track, tmp_csv_thermals)
        self.assertFileNotEmpty(tmp_csv_track)
        self.assertFileNotEmpty(tmp_csv_thermals)
