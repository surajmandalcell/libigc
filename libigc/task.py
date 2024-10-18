import xml.dom.minidom
from collections import defaultdict
from .lib import geo

class Turnpoint:
    """A single turnpoint in a Task.

    Attributes:
        lat: a float, latitude in degrees
        lon: a float, longitude in degrees
        radius: a float, radius of cylinder or line in km
        kind: type of turnpoint; "start_exit", "start_enter", "cylinder",
        "End_of_speed_section", "goal_cylinder", "goal_line"
    """

    def __init__(self, lat, lon, radius, kind):
        self.lat = lat
        self.lon = lon
        self.radius = radius
        self.kind = kind
        assert kind in ["start_exit", "start_enter", "cylinder",
                        "End_of_speed_section", "goal_cylinder",
                        "goal_line"], \
            "turnpoint type is not valid: %r" % kind

    def in_radius(self, fix):
        """Checks whether the provided GNSSFix is within the radius"""
        distance = geo.earth_distance(self.lat, self.lon, fix.lat, fix.lon)
        return distance < self.radius



class Task:
    """Stores a single flight task definition

    Checks if a Flight has achieved the turnpoints in the Task.

    Attributes:
        turnpoints: A list of Turnpoint objects.
        start_time: Raw time (seconds past midnight). The time the race starts.
                    The pilots must start at or after this time.
        end_time: Raw time (seconds past midnight). The time the race ends.
                  The pilots must finish the race at or before this time.
                  No credit is given for distance covered after this time.
    """

    @staticmethod
    def create_from_lkt_file(filename):
        """ Creates Task from LK8000 task file, which is in xml format.
            LK8000 does not have End of Speed Section or task finish time.
            For the goal, at the moment, Turnpoints can't handle goal cones or
            lines, for this reason we default to goal_cylinder.
        """

        # Open XML document using minidom parser
        DOMTree = xml.dom.minidom.parse(filename)
        task = DOMTree.documentElement

        # Get the taskpoints, waypoints and time gate
        # TODO: add code to handle if these tags are missing.
        taskpoints = task.getElementsByTagName("taskpoints")[0]
        waypoints = task.getElementsByTagName("waypoints")[0]
        gate = task.getElementsByTagName("time-gate")[0]
        tpoints = taskpoints.getElementsByTagName("point")
        wpoints = waypoints.getElementsByTagName("point")
        start_time = gate.getAttribute("open-time")

        start_hours, start_minutes = start_time.split(':')
        start_time = int(start_hours) * 3600 + int(start_minutes) * 60
        end_time = 23*3600 + 59*60 + 59  # default end_time of 23:59:59

        # Create a dictionary of names and a list of longitudes and latitudes
        # as the waypoints co-ordinates are stored separate to turnpoint
        # details.
        coords = defaultdict(list)

        for point in wpoints:
            name = point.getAttribute("name")
            longitude = float(point.getAttribute("longitude"))
            latitude = float(point.getAttribute("latitude"))
            coords[name].append(longitude)
            coords[name].append(latitude)

        # Create list of turnpoints
        turnpoints = []
        for point in tpoints:
            lat = coords[point.getAttribute("name")][1]
            lon = coords[point.getAttribute("name")][0]
            radius = float(point.getAttribute("radius"))/1000

            if point == tpoints[0]:
                # It is the first turnpoint, the start
                if point.getAttribute("Exit") == "true":
                    kind = "start_exit"
                else:
                    kind = "start_enter"
            else:
                if point == tpoints[-1]:
                    # It is the last turnpoint, i.e. the goal
                    if point.getAttribute("type") == "line":
                        # TODO(kuaka): change to 'line' once we can process it
                        kind = "goal_cylinder"
                    else:
                        kind = "goal_cylinder"
                else:
                    # All turnpoints other than the 1st and the last are
                    # "cylinders". In theory they could be
                    # "End_of_speed_section" but this is not supported by
                    # LK8000. For paragliders it would be safe to assume
                    # that the 2nd to last is always "End_of_speed_section".
                    kind = "cylinder"

            turnpoint = Turnpoint(lat, lon, radius, kind)
            turnpoints.append(turnpoint)
        task = Task(turnpoints, start_time, end_time)
        return task

    def __init__(self, turnpoints, start_time, end_time):
        self.turnpoints = turnpoints
        self.start_time = start_time
        self.end_time = end_time

    def check_flight(self, flight):
        """ Checks a Flight object against the task.

            Args:
                flight: a Flight object

            Returns:
                a list of GNSSFixes of when turnpoints were achieved.
        """
        reached_turnpoints = []
        proceed_to_start = False
        t = 0
        for fix in flight.fixes:
            if t >= len(self.turnpoints):
                # Pilot has arrived in goal (last turnpoint) so we can stop.
                break

            if self.end_time < fix.rawtime:
                # Task has ended
                break

            # Pilot must have at least 1 fix inside the start after the start
            # time, then exit.
            if self.turnpoints[t].kind == "start_exit":
                if proceed_to_start:
                    if not self.turnpoints[t].in_radius(fix):
                        reached_turnpoints.append(fix)  # pilot has started
                        t += 1
                if fix.rawtime > self.start_time and not proceed_to_start:
                    if self.turnpoints[t].in_radius(fix):
                        # Pilot is inside start after the start time.
                        proceed_to_start = True

            # Pilot must have at least 1 fix outside the start after
            # the start time, then enter.
            elif self.turnpoints[t].kind == "start_enter":
                if proceed_to_start:
                    if self.turnpoints[t].in_radius(fix):
                        # Pilot has started
                        reached_turnpoints.append(fix)
                        t += 1
                if fix.rawtime > self.start_time and not proceed_to_start:
                    if not self.turnpoints[t].in_radius(fix):
                        # Pilot is outside start after the start time.
                        proceed_to_start = True

            elif self.turnpoints[t].kind in ["cylinder",
                                             "End_of_speed_section",
                                             "goal_cylinder"]:
                if self.turnpoints[t].in_radius(fix):
                    # pilot has achieved turnpoint
                    reached_turnpoints.append(fix)
                    t += 1
            else:
                assert False, (
                    "Unknown turnpoint kind: %s" % self.turnpoints[t].kind)

        return reached_turnpoints
