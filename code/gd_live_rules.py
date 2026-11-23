"""Pilot P9 live-feed rules (real time: each alarm uses only readings at or before the moment it fires).

recs: list of (t_ms, value_ft) sorted by time, from the Iowa State HADS live-feed copy.
These are the PILOT thresholds, chosen on the same 7 development floods they were scored on.
Re-tune on development floods only (Hour 'Tune thresholds ... then lock') before any test-flood use.

Change log
  Hour 27: spike alarms are now timed at the NEXT reading (the first moment the reversal is known),
           and the spike check now covers the second-to-last reading (was `i + 2 < len`, now `i + 1 < len`).
"""
from statistics import median

H = 3_600_000


def _median_interval_min(recs):
    iv = [(b[0] - a[0]) / 60000 for a, b in zip(recs, recs[1:])]
    return median(iv) if iv else None


def silent_alarms(recs, rise_ft=0.5, min_gap_min=60):
    """Gap of at least max(3 x usual interval, min_gap_min) right after the stage rose >= rise_ft in the previous hour.
    The alarm fires at last reading + that threshold: the first moment the silence is known in real time.
    Pilot: a 60-min floor fires AFTER the estimated Hunt crest; a 15-min floor fires 20 min before it."""
    out = []
    if len(recs) < 10:
        return out
    med = _median_interval_min(recs)
    for i in range(1, len(recs)):
        gap = (recs[i][0] - recs[i - 1][0]) / 60000
        thr = max(3 * med, min_gap_min)
        if gap >= thr:
            j = i - 1
            while j > 0 and recs[i - 1][0] - recs[j][0] < 55 * 60000:
                j -= 1
            span = recs[i - 1][0] - recs[j][0]
            rise = recs[i - 1][1] - recs[j][1]
            if rise >= rise_ft and span >= 45 * 60000:
                out.append({"t": recs[i - 1][0] + thr * 60000, "rise_ft": round(rise, 2)})
    return out


def implausible_alarms(recs, op_max=None, base_margin=150.0, spike_ft=15.0):
    """Negative values (< -0.5 ft), values above the gauge's USGS operational maximum (+1 ft),
    or one-step jumps > spike_ft that come straight back.
    A spike can only be confirmed when the next reading arrives, so spike alarms are timed at that
    next reading; the other checks need only the bad reading itself and are timed at it.
    The last reading cannot be checked for a spike (no next reading yet).
    Pilot lesson: 7 gauges had real crests ABOVE their published operational maximum,
    so op_max alone gives false alarms; consider ceiling = max(op_max, prior record) + margin."""
    out = []
    if len(recs) < 10:
        return out
    n0 = max(5, len(recs) // 5)
    base = sorted(v for _, v in recs[:n0])[n0 // 2]
    for i in range(1, len(recs)):
        v = recs[i][1]
        bad = None
        if v < -0.5:
            bad = "negative"
        elif op_max is not None and v > op_max + 1:
            bad = "above_op_max"
        elif op_max is None and v > base + base_margin:
            bad = "far_above_base"
        elif i + 1 < len(recs) and abs(v - recs[i - 1][1]) > spike_ft and abs(recs[i + 1][1] - recs[i - 1][1]) < 5:
            bad = "spike"
        if bad:
            t = recs[i + 1][0] if bad == "spike" else recs[i][0]
            out.append({"t": t, "v": v, "why": bad})
    return out


def frozen_alarms(recs, tol=0.1, dur_h=2.0, window_h=3.0, in_flood_ft=3.0, pre_rise_ft=1.0):
    """Readings within tol ft for >= dur_h hours (>= 6 readings), starting at least in_flood_ft above the
    pre-event level, right after a rise of >= pre_rise_ft in the previous window_h hours.
    Pilot lesson: caught 4 of 8 FROZEN gauges but also fired at 24 of 81 healthy big-rise gauges,
    because broad natural crests are also flat. Needs a neighbour check (upstream still rising)."""
    out = []
    if len(recs) < 20:
        return out
    n0 = max(5, int(len(recs) * 0.15))
    base = sorted(v for _, v in recs[:n0])[n0 // 2]
    s = 0
    for i in range(1, len(recs) + 1):
        brk = i == len(recs) or abs(recs[i][1] - recs[s][1]) > tol
        if brk:
            dur = (recs[i - 1][0] - recs[s][0]) / H
            if dur >= dur_h and i - s >= 6:
                k = s
                while k > 0 and recs[s][0] - recs[k][0] < window_h * H:
                    k -= 1
                pre = recs[s][1] - min(v for _, v in recs[k:s + 1])
                if recs[s][1] - base >= in_flood_ft and pre >= pre_rise_ft:
                    out.append({"t": recs[s][0] + dur_h * H, "v": recs[s][1], "dur_h": round(dur, 1)})
            s = i
    return out


if __name__ == "__main__":
    # self-test on synthetic series (15-min readings)
    q = 15 * 60000
    calm = [(i * q, 2.0 + 0.01 * (i % 3)) for i in range(40)]
    rise = [(40 * q + i * q, 2.0 + 1.0 * i) for i in range(8)]           # 1 ft per 15 min
    silent = calm + rise + [(48 * q + 30 * q, 12.0)]                       # ~7.75 h gap after rise
    assert len(silent_alarms(silent)) == 1
    stuck = calm + rise + [(48 * q + i * q, 9.0) for i in range(12)]       # 3 h stuck at 9.0 ft
    assert len(frozen_alarms(stuck)) == 1
    glitch = calm + [(41 * q, 1310.71)] + [(42 * q + i * q, 2.0) for i in range(5)]
    assert implausible_alarms(glitch, op_max=30)[0]["why"] == "above_op_max"
    assert implausible_alarms(glitch, op_max=30)[0]["t"] == 41 * q         # one reading is enough: timed at itself
    flash = calm + [(41 * q, 14.60), (42 * q, 26.06), (43 * q, 27.0), (44 * q, 27.5)]
    assert implausible_alarms(flash, op_max=60) == []                      # real 11 ft jump, no reversal
    # Hour 27 fixes: a spike in the second-to-last reading is caught, and timed when the next reading arrives
    spike = calm + [(40 * q, 20.0), (41 * q, 2.0)]
    a = implausible_alarms(spike, op_max=60)
    assert len(a) == 1 and a[0]["why"] == "spike", a
    assert a[0]["t"] == 41 * q, a                                          # not 40*q: reversal known only at 41*q
    print("gd_live_rules self-test passed")