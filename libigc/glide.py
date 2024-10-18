import math


class Glide:
    """Represents a single glide detected in a flight.

    Glides are portions of the recorded track between thermals.

    Attributes:
        enter_fix: a GNSSFix, entry point of the glide
        exit_fix: a GNSSFix, exit point of the glide
        track_length: a float, the total length, in kilometers, of the recorded
        track, between the entry point and the exit point; note that this is
        not the same as the distance between these points
    """

    def __init__(self, enter_fix, exit_fix, track_length):
        self.enter_fix = enter_fix
        self.exit_fix = exit_fix
        self.track_length = track_length

    def time_change(self):
        """Returns the time spent in the glide, seconds."""
        return self.exit_fix.timestamp - self.enter_fix.timestamp

    def speed(self):
        """Returns the average speed in the glide, km/h."""
        return self.track_length / (self.time_change() / 3600.0)

    def alt_change(self):
        """Return the overall altitude change in the glide, meters."""
        return self.exit_fix.alt - self.enter_fix.alt

    def glide_ratio(self):
        """Returns the L/D of the glide."""
        if math.fabs(self.alt_change()) < 1e-7:
            return 0.0
        return (self.track_length * 1000.0) / self.alt_change()

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        hms = _rawtime_float_to_hms(self.time_change())
        return (
            ("Glide(dist=%.2f km, avg_speed=%.2f kph, "
             "avg L/D=%.2f duration=%dm %ds)") % (
                self.track_length, self.speed(), self.glide_ratio(),
                hms.minutes, hms.seconds))

