
class FlightParsingConfig(object):
    """Configuration for parsing an IGC file.

    Defines a set of parameters used to validate a file, and to detect
    thermals and flight mode. Details in comments.
    """

    #
    # Flight validation parameters.
    #

    # Minimum number of fixes in a file.
    min_fixes = 50

    # Maximum time between fixes, seconds.
    # Soft limit, some fixes are allowed to exceed.
    max_seconds_between_fixes = 50.0

    # Minimum time between fixes, seconds.
    # Soft limit, some fixes are allowed to exceed.
    min_seconds_between_fixes = 1.0

    # Maximum number of fixes exceeding time between fix constraints.
    max_time_violations = 10

    # Maximum number of times a file can cross the 0:00 UTC time.
    max_new_days_in_flight = 2

    # Minimum average of absolute values of altitude changes in a file.
    # This is needed to discover altitude sensors (either pressure or
    # gps) that report either always constant altitude, or almost
    # always constant altitude, and therefore are invalid. The unit
    # is meters/fix.
    min_avg_abs_alt_change = 0.01

    # Maximum altitude change per second between fixes, meters per second.
    # Soft limit, some fixes are allowed to exceed.
    max_alt_change_rate = 50.0

    # Maximum number of fixes that exceed the altitude change limit.
    max_alt_change_violations = 3

    # Absolute maximum altitude, meters.
    max_alt = 10000.0

    # Absolute minimum altitude, meters.
    min_alt = -600.0

    #
    # Flight detection parameters.
    #

    # Minimum ground speed to switch to flight mode, km/h.
    min_gsp_flight = 15.0

    # Minimum idle time (i.e. time with speed below min_gsp_flight) to switch
    # to landing, seconds. Exception: end of the file (tail fixes that
    # do not trigger the above condition), no limit is applied there.
    min_landing_time = 5.0 * 60.0

    # In case there are multiple continuous segments with ground
    # speed exceeding the limit, which one should be taken?
    # Available options:
    #   - "first": take the first segment, ignore the part after
    #     the first detected landing.
    #   - "concat": concatenate all segments; will include the down
    #     periods between segments (legacy behavior)
    which_flight_to_pick = "concat"

    #
    # Thermal detection parameters.
    #

    # Minimum bearing change to enter a thermal, deg/sec.
    min_bearing_change_circling = 6.0

    # Minimum time between fixes to calculate bearing change, seconds.
    # See the usage for a more detailed comment on why this is useful.
    min_time_for_bearing_change = 5.0

    # Minimum time to consider circling a thermal, seconds.
    min_time_for_thermal = 60.0

