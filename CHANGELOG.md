# Changelog

## 1.2.0

### Fixed

- **`.cup` exports could write a malformed coordinate.** SeeYou `.cup` files use
  a fixed width `DDMM.mmm` field. A coordinate sitting just under a whole minute
  rounded the thousandths up to `1000`, four digits in a three digit slot, so a
  latitude of `0.049995` was written as `0002.1000N`. Any program reading the
  file parsed that row wrong. A sweep of 0 to 90 degrees hit the case 382 times
  in 2,000,000 samples.
- **`.wpt` exports could write an invalid seconds field.** The same missing carry
  produced `N 16 38 60.00` for a latitude of `16.65`, where the correct output is
  `N 16 39 00.00`.
- **`GNSSFix.to_B_record()` emitted an invalid hour for flights crossing midnight
  UTC.** `rawtime` keeps counting past 86400 once a flight crosses 0:00, but a B
  record carries a bare `HHMMSS` with no date, so the hour was written as `24`,
  `25` and upward. One of the bundled test flights produced `B240001...` for 5071
  of its 5367 fixes.

  All three had the same root cause: the angle or clock was split first and
  rounded afterwards, at the point of formatting, which throws the carry away.
  Rounding now happens once, into whole sub-minute or whole second units, and the
  split is integer arithmetic from there, so the carry cannot be lost.

- `Task.create_from_lkt_file()` raises `ValueError` on a malformed task file
  rather than asserting, so the check survives `python -O`.

### Changed, and worth reading before upgrading

- **`str()` of `AltitudeSource` and `FixValidity` changed.** They are now
  `enum.StrEnum` rather than `(str, Enum)`, so `str(AltitudeSource.PRESSURE)`
  returns `"PRESS"` instead of `"AltitudeSource.PRESSURE"`. Comparisons against
  plain strings are unaffected. Code that logs, serialises or writes these values
  will produce different text, almost certainly the text it wanted in the first
  place.
- **`DegreeMinuteSecond` changed shape.** Its fourth field is now `units`, a whole
  number of sub-minute units, rather than a floating point `seconds`, and
  `_degrees_float_to_degrees_minutes_seconds()` takes a new required
  `units_per_minute` argument. Both are internal helpers of the export code; the
  producing function has always been underscore-private.
- **Python 3.12 or newer is now required**, up from 3.9. Nothing in the library
  needs 3.12 today, so this is a maintenance decision rather than a technical one.
  Existing installs are unaffected: pip and uv will keep resolving 1.1.0 for older
  interpreters.

### Added

- `tests/oracle.py` and `tests/test_oracle.py` cross-check the library against an
  independent implementation derived from the IGC specification and from first
  principles, using deliberately different techniques: fixed column slicing rather
  than a regex, `Decimal` rather than binary floats for coordinate arithmetic,
  Vincenty and a 3D vector dot product rather than haversine, and bearing
  differences rather than the spherical law of cosines. Three published great
  circle distances anchor the geometry to the real world. It covers every B record
  in every bundled test file, `HFDTE` dates, distances, bearings, ground speeds,
  timestamps, thermal and glide metrics, and the `.wpt`, `.cup` and B record field
  rendering.

  The three defects above had all been present for a long time, and survived
  because the existing tests asserted against values the library itself produced.
- Continuous integration running lint and the test suite on Python 3.12, 3.13 and
  3.14, plus a packaging job that builds the wheel and sdist and runs
  `twine check`.
- `make lint` and `make format`.

### Packaging

- `setup.py`, `requirements.txt` and `.bumpversion.cfg` are replaced by
  `pyproject.toml`; `bumpversion` is replaced by `bump-my-version`.
- The sources moved to a `src/` layout.
- The build now requires `setuptools>=77`. The declared floor of 61 could not
  build the project at all, because `license = "MIT"` is PEP 639 syntax that
  setuptools only understood from 77 onward.
- The whole codebase is formatted and linted with ruff (rules `E`, `F`, `I`, `UP`,
  `B`).
- The example script no longer declares inline PEP 723 dependencies, so running it
  in a checkout exercises the working tree rather than whatever is on PyPI.
- Removed `tools/baum_welch_trainer.py`, which was Python 2 and imported
  `Bio.Alphabet`, dropped from BioPython in 1.78.

## 1.1.0 and earlier

No changelog was kept. See the git history.
