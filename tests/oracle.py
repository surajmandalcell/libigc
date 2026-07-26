"""Independent oracle for libigc.

Everything here is written from the IGC spec (FAI Sporting Code Section 3,
Annex A) and from first principles, deliberately using different techniques
than the library: fixed-offset string slicing instead of a regex, Decimal
instead of binary floats for the coordinate arithmetic, and the spherical law
of cosines / Vincenty instead of haversine.

If the library and this file agree, two independent derivations agree.
"""

import math
from datetime import date as _date
from decimal import Decimal, getcontext

getcontext().prec = 40


# --------------------------------------------------------------------------
# B record, parsed by fixed column offsets straight out of the spec:
#   B HHMMSS DDMMmmm N DDDMMmmm E V PPPPP GGGGG <extensions>
#   0 1....6 7....13 14 15...22 23 24 25..29 30..34 35...
# --------------------------------------------------------------------------
def parse_b_record(line):
    if not line.startswith("B") or len(line) < 35:
        return None
    try:
        hh, mm, ss = int(line[1:3]), int(line[3:5]), int(line[5:7])
        lat_d, lat_m, lat_mmm = int(line[7:9]), int(line[9:11]), int(line[11:14])
        lat_hem = line[14]
        lon_d, lon_m, lon_mmm = int(line[15:18]), int(line[18:20]), int(line[20:23])
        lon_hem = line[23]
        validity = line[24]
        press = int(line[25:30])
        gnss = int(line[30:35])
    except ValueError:
        return None
    if lat_hem not in "NS" or lon_hem not in "EW" or validity not in "AV":
        return None

    # Decimal keeps the minutes-to-degrees division exact to 40 digits, so any
    # disagreement is the library's binary float error, not this file's.
    lat = Decimal(lat_d) + (Decimal(lat_m) + Decimal(lat_mmm) / 1000) / 60
    lon = Decimal(lon_d) + (Decimal(lon_m) + Decimal(lon_mmm) / 1000) / 60
    if lat_hem == "S":
        lat = -lat
    if lon_hem == "W":
        lon = -lon

    return {
        "rawtime": hh * 3600 + mm * 60 + ss,
        "lat": lat,
        "lon": lon,
        "validity": validity,
        "press_alt": press,
        "gnss_alt": gnss,
        "extras": line[35:],
    }


def parse_hfdte(line):
    """HFDTE DDMMYY, or the newer HFDTEDATE:DDMMYY,NN form."""
    body = line[5:]
    if body.upper().startswith("DATE:"):
        body = body[5:].lstrip()
    digits = "".join(c for c in body[:6] if c.isdigit())
    if len(digits) != 6:
        return None
    dd, mm, yy = int(digits[0:2]), int(digits[2:4]), int(digits[4:6])
    if not (1 <= mm <= 12 and 1 <= dd <= 31):
        return None
    return (_date(2000 + yy, mm, dd) - _date(1970, 1, 1)).days * 86400


# --------------------------------------------------------------------------
# Spherical geometry, by different formulas than the library uses.
# --------------------------------------------------------------------------
EARTH_RADIUS_KM = 6371.0


def central_angle_vincenty(lat1, lon1, lat2, lon2):
    """Vincenty's great-circle formula. Stable at both small and large angles,
    unlike the law of cosines, and derived differently from haversine."""
    p1, l1, p2, l2 = map(math.radians, (lat1, lon1, lat2, lon2))
    dl = l2 - l1
    num = math.hypot(
        math.cos(p2) * math.sin(dl),
        math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl),
    )
    den = math.sin(p1) * math.sin(p2) + math.cos(p1) * math.cos(p2) * math.cos(dl)
    return math.atan2(num, den)


def central_angle_dot(lat1, lon1, lat2, lon2):
    """Third derivation: angle between the two 3D unit vectors."""
    p1, l1, p2, l2 = map(math.radians, (lat1, lon1, lat2, lon2))
    v1 = (math.cos(p1) * math.cos(l1), math.cos(p1) * math.sin(l1), math.sin(p1))
    v2 = (math.cos(p2) * math.cos(l2), math.cos(p2) * math.sin(l2), math.sin(p2))
    dot = sum(a * b for a, b in zip(v1, v2, strict=True))
    cross = math.sqrt(
        (v1[1] * v2[2] - v1[2] * v2[1]) ** 2
        + (v1[2] * v2[0] - v1[0] * v2[2]) ** 2
        + (v1[0] * v2[1] - v1[1] * v2[0]) ** 2
    )
    return math.atan2(cross, dot)


def earth_distance_km(lat1, lon1, lat2, lon2):
    return EARTH_RADIUS_KM * central_angle_vincenty(lat1, lon1, lat2, lon2)


def initial_bearing(lat1, lon1, lat2, lon2):
    """Signed initial bearing in degrees, north = 0, east = +90."""
    p1, l1, p2, l2 = map(math.radians, (lat1, lon1, lat2, lon2))
    dl = l2 - l1
    return math.degrees(
        math.atan2(
            math.sin(dl) * math.cos(p2),
            math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl),
        )
    )


def vertex_angle(lat1, lon1, lat, lon, lat2, lon2):
    """Angle at the vertex, computed as the difference of two bearings rather
    than by the spherical law of cosines the library uses."""
    b1 = initial_bearing(lat, lon, lat1, lon1)
    b2 = initial_bearing(lat, lon, lat2, lon2)
    d = abs(b1 - b2) % 360.0
    return 360.0 - d if d > 180.0 else d


# --------------------------------------------------------------------------
# Export field rendering, per format spec.
# --------------------------------------------------------------------------
def dms_units(dd, units_per_minute):
    """Exact split using Decimal, no binary float rounding anywhere."""
    neg = dd < 0
    upd = 60 * units_per_minute
    total = int(
        (abs(Decimal(str(dd))) * upd).to_integral_value(rounding="ROUND_HALF_EVEN")
    )
    degrees, rest = divmod(total, upd)
    minutes, units = divmod(rest, units_per_minute)
    return neg, degrees, minutes, units


def wpt_coord(dd, long):
    neg, d, m, u = dms_units(dd, 6000)
    hem = ("W" if neg else "E") if long else ("S" if neg else "N")
    width = 3 if long else 2
    return f"{hem} {d:0{width}d} {m:02d} {u // 100:02d}.{u % 100:02d}"


def cup_coord(dd, long):
    neg, d, m, u = dms_units(dd, 1000)
    hem = ("W" if neg else "E") if long else ("S" if neg else "N")
    width = 3 if long else 2
    return f"{d:0{width}d}{m:02d}.{u:03d}{hem}"


def b_record_time(rawtime):
    t = int(rawtime) % 86400
    return f"{t // 3600:02d}{t // 60 % 60:02d}{t % 60:02d}"
