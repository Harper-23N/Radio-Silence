"""GaugeDark gap detector (Python port of the rule used in the Round 55 pilot).

Input: a list of (time_utc_ms, value_ft, qualifier_string) for ONE gauge and ONE flood window.
Output: a GaugeResult describing the gauge's flood rise and every "dark" gap.

Naming: "rule v1" here = the Round 55 pilot rule (the pilot JSON calls it "v3"). The column
v1rule_dark in data/stations_7floods_v3.csv is NOT this rule; it is Round 54's older rule.

Rule v1 (fixed before looking at results; change it only with a logbook entry):
  1. Keep numeric values; drop values marked estimated ("ESTIMATED" in the new API, "e" in old codes).
     Matching is by whole piece of the code, so "Approved" is NOT treated as estimated (fix 21 Nov 2026).
  2. Median reporting interval = median spacing of the remaining readings.
  3. "Inserted" point = a reading that (a) is cut off from BOTH neighbours by >= max(3*median, 45 min), or
     (b) is followed by a gap >= that threshold, arrives off-schedule (>= 1.5*median after the previous reading)
     and is higher than the previous reading. These are usually crests added later from high-water marks
     (USGS memo SW 2006.05 tells offices to insert surveyed peaks into the unit values).
  4. A gap = spacing between consecutive regular readings >= 60 min AND >= 3.5 * median interval.
  5. A gap is DARK if the stage rose > 0.3 ft in the 30 min before it began, OR the event maximum
     (including inserted crests) falls inside it.
  6. deficit_ft = event maximum - last regular reading before the gap ("how far below the crest it went silent").

Rule v2 (logbook 22 Nov 2026, after the 20-gauge hand-check; v1 is kept unchanged as version=1).
FROZEN after the round-2 validation; v2 is the rule used for the census.
  7. OPEN-ENDED SILENCE: if the last regular reading is followed by >= the rule-4 gap before the end of the
     window, that silence is a gap too (end = window_end_ms, or the last timestamp of any numeric reading if
     no window end is given). v1 needed a regular reading on both sides, so a gauge that went silent and
     never came back had no gap at all (hand-check gauge h15, USGS 03466500).
     An open-ended silence is DARK only if it starts before the event maximum (it covers the crest or starts
     in the rise period); the "rose > 0.3 ft" test (rule 5) is NOT applied to it. Otherwise data that simply
     ends a few hours before the window end while the river rises again after the flood counts as dark
     (census 22 Nov 2026: hand-check gauge h10, USGS 08167500, data ends 00:00Z, window ends 06:00Z).
     KNOWN BLIND SPOT (found 28 Nov 2026, not changed because v2 is frozen): a gauge that goes silent for
     good AT its highest reading, with no inserted crest afterwards, is not dark under rule 7.
     See test_v2_known_blind_spot in test_gd_gaps.py; report it in Limitations.
  8. RISE PERIOD: a gap is also DARK if it starts during the rise period: at or after the first regular
     reading at or above (minimum + half the total rise), and before the time of the event maximum.
     This matches the labelling card. v1 missed gaps during slow rises (< 0.3 ft per 30 min; gauge h14,
     USGS 08078000).
  Rules 1-6 are unchanged in v2. Each dark gap records which conditions fired (rising, spans_peak, in_rise)
  and whether it is open-ended, so v1 and v2 counts can be compared gauge by gauge.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from statistics import median

MIN = 60_000

# "ESTIMATED" confirmed 21 Nov 2026: new API writes "Approved|ESTIMATED"
# (seen on discharge at 5 ice-affected gauges, Jan 2024). "e" = old USGS style.
ESTIMATED_TOKENS = {"e", "ESTIMATED"}


def is_estimated(code):
    """True only if one whole piece of the code means 'estimated'."""
    pieces = (code or "").replace("+", "|").replace(" ", "|").split("|")
    return any(p.strip() in ESTIMATED_TOKENS for p in pieces)


@dataclass
class Gap:
    start: int
    end: int
    hours: float
    v_before: float
    v_after: float | None          # None when the gap runs to the end of the window (v2 rule 7)
    rising: bool
    spans_peak: bool
    deficit_ft: float
    rate30_ft: float | None
    n_inserted_inside: int
    in_rise: bool = False          # v2 rule 8 fired
    open_end: bool = False         # v2 rule 7: silence ran to the end of the window


@dataclass
class GaugeResult:
    n: int
    median_interval_min: float
    rise_ft: float
    max_ft: float
    t_max: int
    inserted: list = field(default_factory=list)
    dark_gaps: list = field(default_factory=list)
    all_gaps: int = 0
    version: int = 1

    @property
    def dark1(self):
        return len(self.dark_gaps) > 0

    @property
    def dark3(self):
        return any(g.hours >= 3 for g in self.dark_gaps)


def regular_series(recs):
    """Return (regular readings, inserted readings, median interval) from (t, v, code) tuples."""
    num = [(t, v, c or "") for t, v, c in recs if v is not None]
    tel = [r for r in num if not is_estimated(r[2])]
    tel.sort()
    if len(tel) < 3:
        return tel, [], 15.0
    med = median((tel[i][0] - tel[i - 1][0]) / MIN for i in range(1, len(tel)))
    thr = max(3 * med, 45)
    keep, ins = [], []
    for i, r in enumerate(tel):
        dp = (r[0] - tel[i - 1][0]) / MIN if i > 0 else 1e9
        dn = (tel[i + 1][0] - r[0]) / MIN if i < len(tel) - 1 else 1e9
        isolated = dp >= thr and dn >= thr
        offgrid = dn >= thr and i > 0 and dp >= 1.5 * med and r[1] >= tel[i - 1][1]
        (ins if (isolated or offgrid) else keep).append(r)
    return keep, ins, med


def analyze(recs, version: int = 1, window_end_ms: int | None = None) -> GaugeResult | None:
    """Run rule v1 (default, reproduces the pilot) or v2 (adds rules 7 and 8; see module docstring)."""
    if version not in (1, 2):
        raise ValueError("version must be 1 or 2")
    num = sorted((t, v, c) for t, v, c in recs if v is not None)
    if len(num) < 10:
        return None
    vmax = max(v for _, v, _ in num)
    vmin = min(v for _, v, _ in num)
    tmax = next(t for t, v, _ in num if v == vmax)
    reg, ins, med = regular_series(recs)
    res = GaugeResult(n=len(num), median_interval_min=med, rise_ft=round(vmax - vmin, 2), max_ft=vmax, t_max=tmax,
                      inserted=ins, version=version)
    if not reg:
        return res

    # v2 rule 8: rise period starts at the first regular reading at or above the half-rise level
    half = vmin + 0.5 * (vmax - vmin)
    t_half = next((t for t, v, _ in reg if v >= half and t < tmax), None)

    # candidate gaps: (index of reading before, start time, end time, value after or None)
    spans = [(i - 1, reg[i - 1][0], reg[i][0], reg[i][1]) for i in range(1, len(reg))]
    if version == 2:                                                   # rule 7: open-ended silence
        end = window_end_ms if window_end_ms is not None else max(t for t, _, _ in num)
        spans.append((len(reg) - 1, reg[-1][0], end, None))

    for ia, t0, t1, v_after in spans:
        g = (t1 - t0) / MIN
        if not (g >= 60 and g >= 3.5 * med):
            continue
        res.all_gaps += 1
        a = reg[ia]
        prev = next((reg[j] for j in range(ia, -1, -1) if a[0] - reg[j][0] >= 30 * MIN), None)
        rate30 = (a[1] - prev[1]) if prev else None
        rising = rate30 is not None and rate30 > 0.3
        open_end = v_after is None
        spans_peak = t0 < tmax < t1 or (open_end and t0 < tmax <= t1)
        in_rise = version == 2 and t_half is not None and t_half <= t0 < tmax
        dark = (spans_peak or in_rise) if open_end else (rising or spans_peak or in_rise)
        if dark:
            res.dark_gaps.append(Gap(t0, t1, round(g / 60, 2), a[1], v_after, rising, spans_peak,
                                     round(vmax - a[1], 2), None if rate30 is None else round(rate30, 2),
                                     sum(1 for p in ins if t0 < p[0] < t1), in_rise, open_end))
    return res


def max_rise_1h(recs) -> float:
    reg, _, _ = regular_series(recs)
    best, j = 0.0, 0
    for i in range(len(reg)):
        while j < i and reg[i][0] - reg[j][0] > 60 * MIN:
            j += 1
        if reg[i][0] - reg[j][0] >= 45 * MIN:
            best = max(best, reg[i][1] - reg[j][1])
    return round(best, 2)
