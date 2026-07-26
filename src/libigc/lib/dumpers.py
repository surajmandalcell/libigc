from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple

import simplekml

if TYPE_CHECKING:
    # ------------------------------------------------------------------
    # `Flight` is needed only for type hints. Importing it at runtime
    # would make this module depend on the import order inside
    # `libigc/__init__.py` (a circular import waiting to happen), so it
    # is guarded behind TYPE_CHECKING, same as in `gnss_fix.py`.
    # ------------------------------------------------------------------
    from libigc.core import Flight


class DegreeMinuteSecond(NamedTuple):
    """A named tuple to represent degrees, minutes and seconds."""

    hemisphere: str
    degrees: float
    minutes: float
    seconds: float


def _degrees_float_to_degrees_minutes_seconds(
    dd: float, *, long: bool = False
) -> DegreeMinuteSecond:
    """Converts from floating point degrees to degrees/minutes/seconds.

    Args:
        dd: a float, degrees to be converted
        long: a bool, argument used to calculate the hemisphere; True for
        longitude, False for latitude

    Returns:
        A DegreeMinuteSecond namedtuple with hemisphere, degrees, minutes and
        floating point seconds elements.
    """
    negative = dd < 0
    dd = abs(dd)
    minutes, seconds = divmod(dd * 3600, 60)
    degrees, minutes = divmod(minutes, 60)
    if long:
        hemisphere = "E"
    else:
        hemisphere = "N"

    if negative:
        if long:
            hemisphere = "W"
        else:
            hemisphere = "S"

    return DegreeMinuteSecond(hemisphere, degrees, minutes, seconds)


def dump_thermals_to_wpt_file(
    flight: Flight, wptfilename_local: str, endpoints: bool = False
):
    """Dump flight's thermals to a .wpt file in Geo format.

    Args:
        flight: an igc_lib.Flight, the flight to be written
        wptfilename_local: File to be written. If it exists it will be overwritten.
        endpoints: optional argument. If true thermal endpoints as well
        as startpoints will be written with suffix END in the waypoint label.
    """
    wptfilename = Path(wptfilename_local).expanduser().absolute()
    with wptfilename.open("w") as wpt:
        wpt.write("$FormatGEO\n")

        for x, _thermal in enumerate(flight.thermals):
            lat = _degrees_float_to_degrees_minutes_seconds(
                flight.thermals[x].enter_fix.lat, long=False
            )
            lon = _degrees_float_to_degrees_minutes_seconds(
                flight.thermals[x].enter_fix.lon, long=True
            )
            wpt.write(f"{x:02d}        ")
            wpt.write(
                f"{lat.hemisphere} {int(lat.degrees):02d} "
                f"{int(lat.minutes):02d} {lat.seconds:05.2f}    "
            )
            wpt.write(
                f"{lon.hemisphere} {int(lon.degrees):03d} "
                f"{int(lon.minutes):02d} {lon.seconds:05.2f}     "
            )
            wpt.write(f"          {int(flight.thermals[x].enter_fix.gnss_alt)}\n")

            if endpoints:
                lat = _degrees_float_to_degrees_minutes_seconds(
                    flight.thermals[x].exit_fix.lat, long=False
                )
                lon = _degrees_float_to_degrees_minutes_seconds(
                    flight.thermals[x].exit_fix.lon, long=True
                )
                wpt.write(f"{x:02d}END     ")
                wpt.write(
                    f"{lat.hemisphere} {int(lat.degrees):02d} "
                    f"{int(lat.minutes):02d} {lat.seconds:05.2f}    "
                )
                wpt.write(
                    f"{lon.hemisphere} {int(lon.degrees):03d} "
                    f"{int(lon.minutes):02d} {lon.seconds:05.2f}     "
                )
                wpt.write(f"          {int(flight.thermals[x].exit_fix.gnss_alt)}\n")


def dump_thermals_to_cup_file(flight: Flight, cup_filename_local: str):
    """Dump flight's thermals to a .cup file (SeeYou).

    Args:
        flight: an igc_lib.Flight, the flight to be written
        cup_filename_local: a string, the name of the file to be written.
    """
    cup_filename = Path(cup_filename_local).expanduser().absolute()
    with cup_filename.open("wt") as wpt:
        wpt.write("name,code,country,lat,")
        wpt.write("lon,elev,style,rwdir,rwlen,freq,desc,userdata,pics\n")

        def write_fix(name, fix):
            lat = _degrees_float_to_degrees_minutes_seconds(fix.lat, long=False)
            lon = _degrees_float_to_degrees_minutes_seconds(fix.lon, long=True)
            lat_seconds = int(round(lat.seconds / 60.0 * 1000.0))
            lon_seconds = int(round(lon.seconds / 60.0 * 1000.0))
            wpt.write(
                f'"{name}",,,{int(lat.degrees):02d}{int(lat.minutes):02d}'
                f".{lat_seconds:03d}{lat.hemisphere},"
            )
            wpt.write(
                f"{int(lon.degrees):03d}{int(lon.minutes):02d}"
                f".{lon_seconds:03d}{lon.hemisphere},{fix.gnss_alt:f}m,,,,,,,"
            )
            wpt.write("\n")

        for i, thermal in enumerate(flight.thermals):
            write_fix(f"{i:02d}", thermal.enter_fix)
            write_fix(f"{i:02d}_END", thermal.exit_fix)


def dump_flight_to_kml(flight: Flight, kml_filename_local: str):
    """Dumps the flight to KML format.

    Args:
        flight: an igc_lib.Flight, the flight to be saved
        kml_filename_local: a string, the name of the output file
    """
    assert flight.valid
    kml = simplekml.Kml()

    def add_point(name, fix):
        kml.newpoint(name=name, coords=[(fix.lon, fix.lat)])

    coords = []
    for fix in flight.fixes:
        coords.append((fix.lon, fix.lat))
    kml.newlinestring(coords=coords)

    add_point(name="Takeoff", fix=flight.takeoff_fix)
    add_point(name="Landing", fix=flight.landing_fix)

    for i, thermal in enumerate(flight.thermals):
        add_point(name=f"thermal_{i:02d}", fix=thermal.enter_fix)
        add_point(name=f"thermal_{i:02d}_END", fix=thermal.exit_fix)

    kml_filename = Path(kml_filename_local).expanduser().absolute()
    kml.save(kml_filename.as_posix())


def dump_flight_to_csv(
    flight: Flight, track_filename_local: str, thermals_filename_local: str
):
    """Dumps flight data to CSV files.

    Args:
        flight: an igc_lib.Flight, the flight to be written
        track_filename_local: a string, the name of the output CSV with track data
        thermals_filename_local: a string, the name of the output CSV with thermal data
    """
    track_filename = Path(track_filename_local).expanduser().absolute()
    with track_filename.open("wt") as csv:
        csv.write(
            "timestamp,lat,lon,bearing,bearing_change_rate,"
            "ground_speed,flying,circling\n"
        )
        for fix in flight.fixes:
            csv.write(
                f"{fix.timestamp:f},{fix.lat:f},{fix.lon:f},{fix.bearing:f},"
                f"{fix.bearing_change_rate:f},{fix.ground_speed:f},"
                f"{fix.flying},{fix.circling}\n"
            )

    thermals_filename = Path(thermals_filename_local).expanduser().absolute()
    with thermals_filename.open("wt") as csv:
        csv.write("timestamp_enter,timestamp_exit\n")
        for thermal in flight.thermals:
            csv.write(
                f"{thermal.enter_fix.timestamp:f},{thermal.exit_fix.timestamp:f}\n"
            )
