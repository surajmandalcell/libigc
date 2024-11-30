from __future__ import print_function

import re
import collections
import datetime
import math
from pathlib2 import Path

from .lib import viterbi
from .lib import geo
from .gnss_fix import GNSSFix
from .thermal import Thermal
from .glide import Glide
from .task import Task, Turnpoint
from .flight_parsing_config import FlightParsingConfig
from .utils import _strip_non_printable_chars, _rawtime_float_to_hms

class Flight:
    """Parses IGC file, detects thermals and checks for record anomalies.

    Before using an instance of Flight check the `valid` attribute. An
    invalid Flight instance is not usable. For an explaination why is
    a Flight invalid see the `notes` attribute.

    General attributes:
        valid: a bool, whether the supplied record is considered valid
        notes: a list of strings, warnings and errors encountered while
        parsing/validating the file
        fixes: a list of GNSSFix objects, one per each valid B record
        thermals: a list of Thermal objects, the detected thermals
        glides: a list of Glide objects, the glides between thermals
        takeoff_fix: a GNSSFix object, the fix at which takeoff was detected
        landing_fix: a GNSSFix object, the fix at which landing was detected

    IGC metadata attributes (some might be missing if the flight does not
    define them):
        glider_type: a string, the declared glider type
        competition_class: a string, the declared competition class
        fr_manuf_code: a string, the flight recorder manufaturer code
        fr_uniq_id: a string, the flight recorded unique id
        i_record: a string, the I record (describing B record extensions)
        fr_firmware_version: a string, the version of the recorder firmware
        fr_hardware_version: a string, the version of the recorder hardware
        fr_recorder_type: a string, the type of the recorder
        fr_gps_receiver: a string, the used GPS receiver
        fr_pressure_sensor: a string, the used pressure sensor

    Other attributes:
        alt_source: a string, the chosen altitude sensor,
        either "PRESS" or "GNSS"
        press_alt_valid: a bool, whether the pressure altitude sensor is OK
        gnss_alt_valid: a bool, whether the GNSS altitude sensor is OK
    """

    @staticmethod
    def create_from_file(filename, config_class=FlightParsingConfig):
        """Creates an instance of Flight from a given file.

        Args:
            filename: a string, the name of the input IGC file
            config_class: a class that implements FlightParsingConfig

        Returns:
            An instance of Flight built from the supplied IGC file.
        """
        config = config_class()
        fixes = []
        a_records = []
        i_records = []
        h_records = []
        abs_filename = Path(filename).expanduser().absolute()
        with abs_filename.open('r', encoding="ISO-8859-1") as flight_file:
            for line in flight_file:
                line = line.replace(r"\n", "").replace(r"\r", "")
                if not line:
                    continue
                if line[0] == 'A':
                    a_records.append(line)
                elif line[0] == 'B':
                    fix = GNSSFix.build_from_B_record(line, index=len(fixes))
                    if fix is not None:
                        if fixes and math.fabs(fix.rawtime - fixes[-1].rawtime) < 1e-5:
                            # The time did not change since the previous fix.
                            # Ignore this fix.
                            pass
                        else:
                            fixes.append(fix)
                elif line[0] == 'I':
                    i_records.append(line)
                elif line[0] == 'H':
                    h_records.append(line)
                else:
                    # Do not parse any other types of IGC records
                    pass
        flight = Flight(fixes, a_records, h_records, i_records, config)
        return flight

    def __init__(self, fixes, a_records, h_records, i_records, config):
        """Initializer of the Flight class. Do not use directly."""
        self._config = config
        self.fixes = fixes
        self.valid = True
        self.notes = []
        if len(fixes) < self._config.min_fixes:
            self.notes.append(
                "Error: This file has %d fixes, less than "
                "the minimum %d." % (len(fixes), self._config.min_fixes))
            self.valid = False
            return

        self._check_altitudes()
        if not self.valid:
            return

        self._check_fix_rawtime()
        if not self.valid:
            return

        if self.press_alt_valid:
            self.alt_source = "PRESS"
        elif self.gnss_alt_valid:
            self.alt_source = "GNSS"
        else:
            self.notes.append(
                "Error: neither pressure nor gnss altitude is valid.")
            self.valid = False
            return

        if a_records:
            self._parse_a_records(a_records)
        if i_records:
            self._parse_i_records(i_records)
        if h_records:
            self._parse_h_records(h_records)

        if not hasattr(self, 'date_timestamp'):
            self.notes.append("Error: no date record (HFDTE) in the file")
            self.valid = False
            return

        for fix in self.fixes:
            fix.set_flight(self)

        self._compute_ground_speeds()
        self._compute_flight()
        self._compute_takeoff_landing()
        if not hasattr(self, 'takeoff_fix'):
            self.notes.append("Error: did not detect takeoff.")
            self.valid = False
            return

        self._compute_bearings()
        self._compute_bearing_change_rates()
        self._compute_circling()
        self._find_thermals()

    def _parse_a_records(self, a_records):
        """Parses the IGC A record.

        A record contains the flight recorder manufacturer ID and
        device unique ID.
        """
        self.fr_manuf_code = _strip_non_printable_chars(a_records[0][1:4])
        self.fr_uniq_id = _strip_non_printable_chars(a_records[0][4:7])

    def _parse_i_records(self, i_records):
        """Parses the IGC I records.

        I records contain a description of extensions used in B records.
        """
        self.i_record = _strip_non_printable_chars(" ".join(i_records))

    def _parse_h_records(self, h_records):
        """Parses the IGC H records.

        H records (header records) contain a lot of interesting metadata
        about the file, such as the date of the flight, name of the pilot,
        glider type, competition class, recorder accuracy and more.
        Consult the IGC manual for details.
        """
        for record in h_records:
            self._parse_h_record(record)

    def _parse_h_record(self, record):
        if record[0:5] == 'HFDTE':
            match = re.match(
                r"(?:HFDTE|HFDTEDATE:[ ]*)(\d\d)(\d\d)(\d\d)",
                record,
                flags=re.IGNORECASE,
            )
            if match:
                dd, mm, yy = [_strip_non_printable_chars(group) for group in match.groups()]
                year = int(2000 + int(yy))
                month = int(mm)
                day = int(dd)
                if 1 <= month <= 12 and 1 <= day <= 31:
                    epoch = datetime.datetime(year=1970, month=1, day=1)
                    date = datetime.datetime(year=year, month=month, day=day)
                    self.date_timestamp = (date - epoch).total_seconds()
        elif record[0:5] == 'HFGTY':
            match = re.match(
                'HFGTY[ ]*GLIDER[ ]*TYPE[ ]*:[ ]*(.*)',
                record, flags=re.IGNORECASE)
            if match:
                (self.glider_type,) = map(
                    _strip_non_printable_chars, match.groups())
        elif record[0:5] == 'HFRFW' or record[0:5] == 'HFRHW':
            match = re.match(
                'HFR[FH]W[ ]*FIRMWARE[ ]*VERSION[ ]*:[ ]*(.*)',
                record, flags=re.IGNORECASE)
            if match:
                (self.fr_firmware_version,) = map(
                    _strip_non_printable_chars, match.groups())
            match = re.match(
                'HFR[FH]W[ ]*HARDWARE[ ]*VERSION[ ]*:[ ]*(.*)',
                record, flags=re.IGNORECASE)
            if match:
                (self.fr_hardware_version,) = map(
                    _strip_non_printable_chars, match.groups())
        elif record[0:5] == 'HFFTY':
            match = re.match(
                'HFFTY[ ]*FR[ ]*TYPE[ ]*:[ ]*(.*)',
                record, flags=re.IGNORECASE)
            if match:
                (self.fr_recorder_type,) = map(_strip_non_printable_chars,
                                               match.groups())
        elif record[0:5] == 'HFGPS':
            match = re.match(
                'HFGPS(?:[: ]|(?:GPS))*(.*)',
                record, flags=re.IGNORECASE)
            if match:
                (self.fr_gps_receiver,) = map(_strip_non_printable_chars,
                                              match.groups())
        elif record[0:5] == 'HFPRS':
            match = re.match(
                'HFPRS[ ]*PRESS[ ]*ALT[ ]*SENSOR[ ]*:[ ]*(.*)',
                record, flags=re.IGNORECASE)
            if match:
                (self.fr_pressure_sensor,) = map(_strip_non_printable_chars,
                                                 match.groups())
        elif record[0:5] == 'HFCCL':
            match = re.match(
                'HFCCL[ ]*COMPETITION[ ]*CLASS[ ]*:[ ]*(.*)',
                record, flags=re.IGNORECASE)
            if match:
                (self.competition_class,) = map(_strip_non_printable_chars,
                                                match.groups())

    def __str__(self):
        descr = "Flight(valid=%s, fixes: %d" % (
            str(self.valid), len(self.fixes))
        if hasattr(self, 'thermals'):
            descr += ", thermals: %d" % len(self.thermals)
        descr += ")"
        return descr

    def _check_altitudes(self):
        press_alt_violations_num = 0
        gnss_alt_violations_num = 0
        press_huge_changes_num = 0
        gnss_huge_changes_num = 0
        press_chgs_sum = 0.0
        gnss_chgs_sum = 0.0
        for i in range(len(self.fixes) - 1):
            press_alt_delta = math.fabs(
                self.fixes[i+1].press_alt - self.fixes[i].press_alt)
            gnss_alt_delta = math.fabs(
                self.fixes[i+1].gnss_alt - self.fixes[i].gnss_alt)
            rawtime_delta = math.fabs(
                self.fixes[i+1].rawtime - self.fixes[i].rawtime)
            if rawtime_delta > 0.5:
                if (press_alt_delta / rawtime_delta >
                        self._config.max_alt_change_rate):
                    press_huge_changes_num += 1
                else:
                    press_chgs_sum += press_alt_delta
                if (gnss_alt_delta / rawtime_delta >
                        self._config.max_alt_change_rate):
                    gnss_huge_changes_num += 1
                else:
                    gnss_chgs_sum += gnss_alt_delta
            if (self.fixes[i].press_alt > self._config.max_alt
                    or self.fixes[i].press_alt < self._config.min_alt):
                press_alt_violations_num += 1
            if (self.fixes[i].gnss_alt > self._config.max_alt or
                    self.fixes[i].gnss_alt < self._config.min_alt):
                gnss_alt_violations_num += 1
        press_chgs_avg = press_chgs_sum / float(len(self.fixes) - 1)
        gnss_chgs_avg = gnss_chgs_sum / float(len(self.fixes) - 1)

        press_alt_ok = True
        if press_chgs_avg < self._config.min_avg_abs_alt_change:
            self.notes.append(
                "Warning: average pressure altitude change between fixes "
                "is: %f. It is lower than the minimum: %f."
                % (press_chgs_avg, self._config.min_avg_abs_alt_change))
            press_alt_ok = False

        if press_huge_changes_num > self._config.max_alt_change_violations:
            self.notes.append(
                "Warning: too many high changes in pressure altitude: %d. "
                "Maximum allowed: %d."
                % (press_huge_changes_num,
                   self._config.max_alt_change_violations))
            press_alt_ok = False

        if press_alt_violations_num > 0:
            self.notes.append(
                "Warning: pressure altitude limits exceeded in %d fixes."
                % (press_alt_violations_num))
            press_alt_ok = False

        gnss_alt_ok = True
        if gnss_chgs_avg < self._config.min_avg_abs_alt_change:
            self.notes.append(
                "Warning: average gnss altitude change between fixes is: %f. "
                "It is lower than the minimum: %f."
                % (gnss_chgs_avg, self._config.min_avg_abs_alt_change))
            gnss_alt_ok = False

        if gnss_huge_changes_num > self._config.max_alt_change_violations:
            self.notes.append(
                "Warning: too many high changes in gnss altitude: %d. "
                "Maximum allowed: %d."
                % (gnss_huge_changes_num,
                   self._config.max_alt_change_violations))
            gnss_alt_ok = False

        if gnss_alt_violations_num > 0:
            self.notes.append(
                "Warning: gnss altitude limits exceeded in %d fixes." %
                gnss_alt_violations_num)
            gnss_alt_ok = False

        self.press_alt_valid = press_alt_ok
        self.gnss_alt_valid = gnss_alt_ok

    def _check_fix_rawtime(self):
        """Checks for rawtime anomalies, fixes 0:00 UTC crossing.

        The B records do not have fully qualified timestamps (just the current
        time in UTC), therefore flights that cross 0:00 UTC need special
        handling.
        """
        DAY = 24.0 * 60.0 * 60.0
        days_added = 0
        rawtime_to_add = 0.0
        rawtime_between_fix_exceeded = 0
        for i in range(1, len(self.fixes)):
            f0 = self.fixes[i-1]
            f1 = self.fixes[i]
            f1.rawtime += rawtime_to_add

            if (f0.rawtime > f1.rawtime and
                    f1.rawtime + DAY < f0.rawtime + 200.0):
                # Day switch
                days_added += 1
                rawtime_to_add += DAY
                f1.rawtime += DAY

            time_change = f1.rawtime - f0.rawtime
            if time_change < self._config.min_seconds_between_fixes - 1e-5:
                rawtime_between_fix_exceeded += 1
            if time_change > self._config.max_seconds_between_fixes + 1e-5:
                rawtime_between_fix_exceeded += 1

        if rawtime_between_fix_exceeded > self._config.max_time_violations:
            self.notes.append(
                "Error: too many fixes intervals exceed time between fixes "
                "constraints. Allowed %d fixes, found %d fixes."
                % (self._config.max_time_violations,
                   rawtime_between_fix_exceeded))
            self.valid = False
        if days_added > self._config.max_new_days_in_flight:
            self.notes.append(
                "Error: too many times did the flight cross the UTC 0:00 "
                "barrier. Allowed %d times, found %d times."
                % (self._config.max_new_days_in_flight, days_added))
            self.valid = False

    def _compute_ground_speeds(self):
        """Adds ground speed info (km/h) to self.fixes."""
        self.fixes[0].gsp = 0.0
        for i in range(1, len(self.fixes)):
            dist = self.fixes[i].distance_to(self.fixes[i-1])
            rawtime = self.fixes[i].rawtime - self.fixes[i-1].rawtime
            if math.fabs(rawtime) < 1e-5:
                self.fixes[i].gsp = 0.0
            else:
                self.fixes[i].gsp = dist/rawtime*3600.0

    def _flying_emissions(self):
        """Generates raw flying/not flying emissions from ground speed.

        Standing (i.e. not flying) is encoded as 0, flying is encoded as 1.
        Exported to a separate function to be used in Baum-Welch parameters
        learning.
        """
        emissions = []
        for fix in self.fixes:
            if fix.gsp > self._config.min_gsp_flight:
                emissions.append(1)
            else:
                emissions.append(0)

        return emissions

    def _compute_flight(self):
        """Adds boolean flag .flying to self.fixes.

        Two pass:
          1. Viterbi decoder
          2. Only emit landings (0) if the downtime is more than
             _config.min_landing_time (or it's the end of the log).
        """
        # Step 1: the Viterbi decoder
        emissions = self._flying_emissions()
        decoder = viterbi.SimpleViterbiDecoder(
            # More likely to start the log standing, i.e. not in flight
            init_probs=[0.80, 0.20],
            transition_probs=[
                [0.9995, 0.0005],  # transitions from standing
                [0.0005, 0.9995],  # transitions from flying
            ],
            emission_probs=[
                [0.8, 0.2],  # emissions from standing
                [0.2, 0.8],  # emissions from flying
            ])

        outputs = decoder.decode(emissions)

        # Step 2: apply _config.min_landing_time.
        ignore_next_downtime = False
        apply_next_downtime = False
        for i, (fix, output) in enumerate(zip(self.fixes, outputs)):
            if output == 1:
                fix.flying = True
                # We're in flying mode, therefore reset all expectations
                # about what's happening in the next down mode.
                ignore_next_downtime = False
                apply_next_downtime = False
            else:
                if apply_next_downtime or ignore_next_downtime:
                    if apply_next_downtime:
                        fix.flying = False
                    else:
                        fix.flying = True
                else:
                    # We need to determine whether to apply_next_downtime
                    # or to ignore_next_downtime. This requires a scan into
                    # upcoming fixes. Find the next fix on which
                    # the Viterbi decoder said "flying".
                    j = i + 1
                    while j < len(self.fixes):
                        upcoming_fix_decoded = outputs[j]
                        if upcoming_fix_decoded == 1:
                            break
                        j += 1

                    if j == len(self.fixes):
                        # No such fix, end of log. Then apply.
                        apply_next_downtime = True
                        fix.flying = False
                    else:
                        # Found next flying fix.
                        upcoming_fix = self.fixes[j]
                        upcoming_fix_time_ahead = upcoming_fix.rawtime - fix.rawtime
                        # If it's far enough into the future of then apply.
                        if upcoming_fix_time_ahead >= self._config.min_landing_time:
                            apply_next_downtime = True
                            fix.flying = False
                        else:
                            ignore_next_downtime = True
                            fix.flying = True

    def _compute_takeoff_landing(self):
        """Finds the takeoff and landing fixes in the log.

        Takeoff fix is the first fix in the flying mode. Landing fix
        is the next fix after the last fix in the flying mode or the
        last fix in the file.
        """
        takeoff_fix = None
        landing_fix = None
        was_flying = False
        for fix in self.fixes:
            if fix.flying and takeoff_fix is None:
                takeoff_fix = fix
            if not fix.flying and was_flying:
                landing_fix = fix
                if self._config.which_flight_to_pick == "first":
                    # User requested to select just the first flight in the log,
                    # terminate now.
                    break
            was_flying = fix.flying

        if takeoff_fix is None:
            # No takeoff found.
            return

        if landing_fix is None:
            # Landing on the last fix
            landing_fix = self.fixes[-1]

        self.takeoff_fix = takeoff_fix
        self.landing_fix = landing_fix

    def _compute_bearings(self):
        """Adds bearing info to self.fixes."""
        for i in range(len(self.fixes) - 1):
            self.fixes[i].bearing = self.fixes[i].bearing_to(self.fixes[i+1])
        self.fixes[-1].bearing = self.fixes[-2].bearing

    def _compute_bearing_change_rates(self):
        """Adds bearing change rate info to self.fixes.

        Computing bearing change rate between neighboring fixes proved
        itself to be noisy on tracks recorded with minimum interval (1 second).
        Therefore we compute rates between points that are at least
        min_time_for_bearing_change seconds apart.
        """
        def find_prev_fix(curr_fix):
            """Computes the previous fix to be used in bearing rate change."""
            prev_fix = None
            for i in range(curr_fix - 1, 0, -1):
                time_dist = math.fabs(
                    self.fixes[curr_fix].timestamp - self.fixes[i].timestamp
                )
                if time_dist > self._config.min_time_for_bearing_change - 1e-7:
                    prev_fix = i
                    break
            return prev_fix

        def normalize_bearing_change(change):
            """Normalizes bearing change to handle 0/360 crossing properly."""
            while change > 180.0:
                change -= 360.0
            while change < -180.0:
                change += 360.0
            return change

        for curr_fix in range(len(self.fixes)):
            prev_fix = find_prev_fix(curr_fix)

            if prev_fix is None:
                self.fixes[curr_fix].bearing_change_rate = 0.0
                continue

            bearing_change = normalize_bearing_change(
                self.fixes[curr_fix].bearing - self.fixes[prev_fix].bearing
            )

            time_change = (
                self.fixes[curr_fix].timestamp - self.fixes[prev_fix].timestamp
            )

            # Avoid division by zero
            if abs(time_change) < 1e-7:
                self.fixes[curr_fix].bearing_change_rate = 0.0
            else:
                # Positive rate means turning right, negative means turning left
                change_rate = bearing_change / time_change
                self.fixes[curr_fix].bearing_change_rate = change_rate

    def _circling_emissions(self):
        """Generates raw circling/straight emissions from bearing change.

        Staight flight is encoded as 0, circling is encoded as 1. Exported
        to a separate function to be used in Baum-Welch parameters learning.
        """
        emissions = []
        for fix in self.fixes:
            bearing_change = math.fabs(fix.bearing_change_rate)
            bearing_change_enough = (
                bearing_change > self._config.min_bearing_change_circling)
            if fix.flying and bearing_change_enough:
                emissions.append(1)
            else:
                emissions.append(0)
        return emissions

    def _compute_circling(self):
        """Adds .circling to self.fixes."""
        emissions = self._circling_emissions()
        decoder = viterbi.SimpleViterbiDecoder(
            # More likely to start in straight flight than in circling
            init_probs=[0.80, 0.20],
            transition_probs=[
                [0.982, 0.018],  # transitions from straight flight
                [0.030, 0.970],  # transitions from circling
            ],
            emission_probs=[
                [0.942, 0.058],  # emissions from straight flight
                [0.093, 0.907],  # emissions from circling
            ])

        output = decoder.decode(emissions)

        for i in range(len(self.fixes)):
            self.fixes[i].circling = (output[i] == 1)

    def _find_thermals(self):
        """Go through the fixes and find the thermals.

        Every point not in a thermal is put into a glide.If we get to end of
        the fixes and there is still an open glide (i.e. flight not finishing
        in a valid thermal) the glide will be closed.
        """
        takeoff_index = self.takeoff_fix.index
        landing_index = self.landing_fix.index
        flight_fixes = self.fixes[takeoff_index:landing_index + 1]

        self.thermals = []
        self.glides = []
        circling_now = False
        gliding_now = False
        first_fix = None
        first_glide_fix = None
        last_glide_fix = None
        distance = 0.0
        for fix in flight_fixes:
            if not circling_now and fix.circling:
                # Just started circling
                circling_now = True
                first_fix = fix
                distance_start_circling = distance
            elif circling_now and not fix.circling:
                # Just ended circling
                circling_now = False
                thermal = Thermal(first_fix, fix)
                if (thermal.time_change() >
                        self._config.min_time_for_thermal - 1e-5):
                    self.thermals.append(thermal)
                    # glide ends at start of thermal
                    glide = Glide(first_glide_fix, first_fix,
                                  distance_start_circling)
                    self.glides.append(glide)
                    gliding_now = False

            if gliding_now:
                distance = distance + fix.distance_to(last_glide_fix)
                last_glide_fix = fix
            else:
                # just started gliding
                first_glide_fix = fix
                last_glide_fix = fix
                gliding_now = True
                distance = 0.0

        if gliding_now:
            glide = Glide(first_glide_fix, last_glide_fix, distance)
            self.glides.append(glide)
