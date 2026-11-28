"""Retrospective Part 3 live-feed classifier. Times are UTC milliseconds."""
from collections import deque
from math import isfinite
from statistics import median

MINUTE = 60_000
EPS = 1e-9


class NoLiveData(ValueError):
    """The supplied station record contains no numeric stage observations."""


def _numeric_series(rows):
    by_time = {}
    for time, raw, *_ in rows:
        if raw is None or raw == "":
            continue
        value = float(raw)
        if not isfinite(value):
            continue
        if time in by_time and by_time[time] != value:
            raise ValueError(f"Conflicting stages at timestamp {time}")
        by_time[time] = value
    return sorted(by_time.items())


def _cadence(series, start, end, minutes):
    if minutes is not None:
        interval = float(minutes) * MINUTE
        if not isfinite(interval) or interval <= 0:
            raise ValueError("cadence_minutes must be positive and finite")
        return interval
    outside = []
    all_steps = []
    for (a, _), (b, _) in zip(series, series[1:]):
        all_steps.append(b - a)
        if b <= start or a >= end:
            outside.append(b - a)
    steps = outside if len(outside) >= 2 else all_steps
    if len(steps) < 2:
        raise ValueError("Supply cadence_minutes for a sparse station record")
    return median(steps)


def _flat_support(points, crest, cadence):
    """Largest number of readings in one qualifying two-hour plateau."""
    lows, highs = deque(), deque()
    left = best = 0
    max_break = max(3 * cadence, 45 * MINUTE)
    for i, (time, value) in enumerate(points):
        if i and time - points[i - 1][0] >= max_break:
            left = i
            lows.clear()
            highs.clear()
        if value < 0 or value == 1310.71 or crest - value < 0.5 - EPS:
            left = i + 1
            lows.clear()
            highs.clear()
            continue

        while lows and points[lows[-1]][1] >= value:
            lows.pop()
        while highs and points[highs[-1]][1] <= value:
            highs.pop()
        lows.append(i)
        highs.append(i)
        while points[highs[0]][1] - points[lows[0]][1] > 0.10 + EPS:
            left = min(lows[0], highs[0]) + 1
            while lows and lows[0] < left:
                lows.popleft()
            while highs and highs[0] < left:
                highs.popleft()
        if time - points[left][0] >= 120 * MINUTE:
            best = max(best, i - left + 1)
    return best


def classify(archive_gap, live_series, crest, *, cadence_minutes=None):
    """Classify one gap using (time_ms, stage_ft) tuples for the full event.

    archive_gap is a gd_gaps.Gap. crest is the reference stage in feet
    on the same datum. Pass None for a documented missing station record.
    Catch NoLiveData upstream to record NO_LIVE_DATA.
    """
    start, end = archive_gap.start, archive_gap.end
    if end <= start:
        raise ValueError("Gap end must follow its start")
    series = _numeric_series(() if live_series is None else live_series)
    if not series:
        raise NoLiveData("No numeric stage observations for the station")
    points = [(t, v) for t, v in series
              if start < t < end or (archive_gap.open_end and t == end)]
    if not points:
        return "SILENT"
    crest = float(crest)
    if not isfinite(crest):
        raise ValueError("The crest must be finite")
    cadence = _cadence(series, start, end, cadence_minutes)
    coverage = len(points) * cadence / (end - start)
    plausible = [v for _, v in points
                 if v >= 0 and v != 1310.71 and v - crest < 10 - EPS]
    flat = _flat_support(points, crest, cadence)
    bad = len(points) - len(plausible)

    # Resolve overlapping evidence using the dominant reported pattern.
    if flat and 2 * flat >= len(points):
        return "FROZEN"
    if coverage < 0.20:
        return "SILENT"
    if bad:
        return "IMPLAUSIBLE"
    if max(plausible) > min(plausible) and crest - max(plausible) > 2 + EPS:
        return "UNDER_READ"
    if flat:
        return "FROZEN"
    return "LIVE_PRESENT"