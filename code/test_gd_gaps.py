"""Tests for gd_gaps.py using the real Hunt, TX record (USGS 08165500 / NWS HNTT2), 4-5 July 2025,
as served by the Iowa Environmental Mesonet HADS archive on 16 Nov 2026 (values identical to the USGS archive),
plus synthetic series for the v2 rule changes (logbook 22 Nov 2026).
Run:  python -I -m pytest code/test_gd_gaps.py   (or just: python -I code/test_gd_gaps.py)
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from datetime import datetime, timezone
from gd_gaps import analyze, max_rise_1h

def ms(s):
    return int(datetime.strptime(s, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc).timestamp() * 1000)

HUNT = [("2025-07-04 06:00",7.68),("2025-07-04 06:05",7.68),("2025-07-04 06:10",7.69),("2025-07-04 06:15",7.69),
("2025-07-04 06:20",7.7),("2025-07-04 06:25",7.71),("2025-07-04 06:30",7.71),("2025-07-04 06:35",7.72),("2025-07-04 06:40",7.75),
("2025-07-04 06:45",7.78),("2025-07-04 06:50",7.83),("2025-07-04 06:55",7.89),("2025-07-04 07:00",7.98),("2025-07-04 07:05",8.13),
("2025-07-04 07:10",8.27),("2025-07-04 07:15",8.4),("2025-07-04 07:20",8.54),("2025-07-04 07:25",8.7),("2025-07-04 07:30",8.82),
("2025-07-04 07:35",8.93),("2025-07-04 07:40",9.0),("2025-07-04 07:45",9.06),("2025-07-04 07:50",9.15),("2025-07-04 07:55",9.41),
("2025-07-04 08:00",10.1),("2025-07-04 08:05",11.03),("2025-07-04 08:10",11.93),("2025-07-04 08:15",13.03),("2025-07-04 08:20",13.99),
("2025-07-04 08:25",14.94),("2025-07-04 08:30",15.9),("2025-07-04 08:35",16.81),("2025-07-04 08:40",17.52),("2025-07-04 08:45",18.39),
("2025-07-04 08:50",19.35),("2025-07-04 08:55",20.3),("2025-07-04 09:00",21.11),("2025-07-04 09:05",21.99),("2025-07-04 09:10",22.85),
("2025-07-04 09:15",23.73),("2025-07-04 09:20",24.7),("2025-07-04 09:25",26.92),("2025-07-04 09:30",28.21),("2025-07-04 09:35",29.45),
("2025-07-04 10:10",37.52),
("2025-07-05 20:35",8.89),("2025-07-05 20:45",8.89),("2025-07-05 20:50",8.88),("2025-07-05 20:55",8.88),("2025-07-05 21:00",8.87),
("2025-07-05 21:05",8.87),("2025-07-05 21:10",8.87),("2025-07-05 21:15",8.87),("2025-07-05 21:20",8.86),("2025-07-05 21:25",8.86)]

RECS = [(ms(t), v, "A") for t, v in HUNT]

def test_hunt():
    r = analyze(RECS)
    assert r is not None and r.dark1 and r.dark3
    g = max(r.dark_gaps, key=lambda g: g.hours)
    assert g.v_before == 29.45                       # last real reading, 4:35 am CDT
    assert abs(g.hours - 35.0) < 0.01                # 09:35Z 4 Jul -> 20:35Z 5 Jul
    assert abs(g.deficit_ft - 8.07) < 0.01           # 37.52 crest - 29.45
    assert g.spans_peak and g.n_inserted_inside == 1 # 37.52 crest sits inside the gap
    assert len(r.inserted) == 1 and r.inserted[0][1] == 37.52
    assert max_rise_1h(RECS) == 12.64                # 09:35 29.45 - 08:35 16.81 (inserted crest excluded)

def test_estimated_values_do_not_hide_gap():
    recs = RECS + [(ms("2025-07-04 15:00"), 20.0, "A e")]
    r = analyze(recs)
    assert r.dark1                                    # estimated fill does not count as a live reading


# ---------- rule v2 (logbook 22 Nov 2026) ----------
# Synthetic series shaped like hand-check gauges; they test the rule's logic only.

def series(start, n, f, step_min=15):
    t0 = ms(start)
    return [(t0 + k * step_min * 60_000, round(f(k), 2), "A") for k in range(n)]

def test_v2_open_ended_silence_h15():
    """h15 (USGS 03466500): archive stops on the rise, inserted crest 75 min later, one lone reading
    2.5 days later. v1 finds no gap because no regular reading follows."""
    rise = series("2024-09-27 15:00", 48, lambda k: 42 + 22.5 * (k / 47) ** 2)
    assert rise[-1][0] == ms("2024-09-28 02:45")
    recs = rise + [(ms("2024-09-28 04:00"), 66.03, "A"), (ms("2024-09-30 14:45"), 44.6, "A")]
    assert not analyze(recs).dark1
    end = ms("2024-10-01 06:00")
    v2 = analyze(recs, version=2, window_end_ms=end)
    assert v2.dark1 and v2.dark3
    g = v2.dark_gaps[0]
    assert g.open_end and g.v_after is None and g.end == end
    assert g.spans_peak and g.v_before == 64.5 and abs(g.deficit_ft - 1.53) < 0.01
    assert g.n_inserted_inside == 2
    assert analyze(recs, version=2).dark1

def test_v2_gap_in_slow_rise_h14():
    """h14 (USGS 08078000): 75-min gap in a slow rise past half the rise; v1 misses it, v2 catches it.
    Control: the same gap before the half-rise level stays healthy."""
    f = lambda k: 10 + 0.1 * k if k <= 240 else 34 - 0.05 * (k - 240)
    full = series("2017-08-26 00:00", 340, f)
    def drop(recs, k0):
        return [r for i, r in enumerate(recs) if not (k0 <= i < k0 + 4)]
    late, early = drop(full, 160), drop(full, 40)
    assert not analyze(late).dark1
    r = analyze(late, version=2)
    assert r.dark1 and not r.dark3
    g = r.dark_gaps[0]
    assert g.in_rise and not g.rising and not g.spans_peak and not g.open_end
    assert abs(g.hours - 1.25) < 0.01 and g.rate30_ft is not None and g.rate30_ft <= 0.3
    assert not analyze(early, version=2).dark1

def test_v2_data_ending_early_after_crest_h10():
    """h10 (USGS 08167500): data ends 6 h before the window end after the crest: not an outage."""
    def f(k):
        h = k / 4
        if h < 48: return 1.5
        if h < 52: return 1.5 + 28.5 * (h - 48) / 4
        if h < 100: return 30.0 - 25.0 * (h - 52) / 48
        return 5.0 + 0.8 * (h - 100)
    recs = series("2025-07-03 00:00", 4 * 120 + 1, f)
    r = analyze(recs, version=2, window_end_ms=ms("2025-07-08 06:00"))
    assert r.all_gaps == 1 and not r.dark1

def test_v2_keeps_v1_results_on_hunt():
    r1, r2 = analyze(RECS), analyze(RECS, version=2, window_end_ms=ms("2025-07-05 21:25"))
    assert r2.dark1 and r2.dark3
    g1 = max(r1.dark_gaps, key=lambda g: g.hours); g2 = max(r2.dark_gaps, key=lambda g: g.hours)
    assert (g1.start, g1.end, g1.deficit_ft) == (g2.start, g2.end, g2.deficit_ft)

def test_v2_new_api_codes():
    """Approved readings are kept by v2 too (the 21 Nov fix); Approved|ESTIMATED ones are dropped."""
    recs = [(t, v, "Approved") for t, v, _ in RECS]
    assert analyze(recs, version=2, window_end_ms=ms("2025-07-05 21:25")).dark1
    est = [(t, v, "Approved|ESTIMATED") for t, v, _ in RECS]
    assert analyze(est, version=2) is not None and not analyze(est, version=2).dark1

def test_v2_known_blind_spot():
    """Documents a known limit of frozen v2 (28 Nov 2026): a gauge that goes silent for good AT its
    highest reading, with no inserted crest, is NOT dark. If this test ever fails, the rule changed."""
    calm = [(ms("2025-07-04 00:00") + k * 900_000, 2.0, "A") for k in range(40)]
    rise = [(calm[-1][0] + (k + 1) * 900_000, 2.0 + 1.0 * (k + 1), "A") for k in range(20)]
    r = analyze(calm + rise, version=2, window_end_ms=rise[-1][0] + 48 * 3_600_000)
    assert r.all_gaps == 1 and not r.dark1

if __name__ == "__main__":
    test_hunt(); test_estimated_values_do_not_hide_gap()
    test_v2_open_ended_silence_h15(); test_v2_gap_in_slow_rise_h14(); test_v2_data_ending_early_after_crest_h10()
    test_v2_keeps_v1_results_on_hunt(); test_v2_new_api_codes(); test_v2_known_blind_spot()
    print("all tests passed")
