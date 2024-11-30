import math
from libigc.utils import _rawtime_float_to_hms

class Thermal:
    """Represents a single thermal detected in a flight.

    Attributes:
        enter_fix: a GNSSFix, entry point of the thermal
        exit_fix: a GNSSFix, exit point of the thermal
    """
    def __init__(self, enter_fix, exit_fix):
        self.enter_fix = enter_fix
        self.exit_fix = exit_fix

    def time_change(self):
        """Returns the time spent in the thermal, seconds."""
        return self.exit_fix.rawtime - self.enter_fix.rawtime

    def alt_change(self):
        """Returns the altitude gained/lost in the thermal, meters."""
        return self.exit_fix.alt - self.enter_fix.alt

    def vertical_velocity(self):
        """Returns average vertical velocity in the thermal, m/s."""
        if math.fabs(self.time_change()) < 1e-7:
            return 0.0
        return self.alt_change() / self.time_change()

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        hms = _rawtime_float_to_hms(self.time_change())
        return ("Thermal(vertical_velocity=%.2f m/s, duration=%dm %ds)" %
                (self.vertical_velocity(), hms.minutes, hms.seconds))
