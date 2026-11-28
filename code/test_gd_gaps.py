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
# Synthetic series shaped like two hand-check gauges. Real readings are not used here so the tests
# check the rule's logic only; shapes and times follow the plots in figs/hand/.

def series(start, n, f, step_min=15):
    t0 = ms(start)
    return [(t0 + k * step_min * 60_000, round(f(k), 2), "A") for k in range(n)]

def test_v2_open_ended_silence_h15():
    """h15 (USGS 03466500): archive stops on the rise at 02:45Z 28 Sep, inserted crest 75 min later,
    then only one isolated reading 2.5 days later. v1 finds no gap because no regular reading follows."""
    rise = series("2024-09-27 15:00", 48, lambda k: 42 + 22.5 * (k / 47) ** 2)    # 42 -> 64.5 ft, last 02:45Z
    assert rise[-1][0] == ms("2024-09-28 02:45")
    recs = rise + [(ms("2024-09-28 04:00"), 66.03, "A"),                          # inserted crest
                   (ms("2024-09-30 14:45"), 44.6, "A")]                           # lone reading
    v1 = analyze(recs)
    assert not v1.dark1                                     # the bug v2 fixes
    end = ms("2024-10-01 06:00")
    v2 = analyze(recs, version=2, window_end_ms=end)
    assert v2.dark1 and v2.dark3
    g = v2.dark_gaps[0]
    assert g.open_end and g.v_after is None and g.end == end
    assert g.spans_peak and g.v_before == 64.5 and abs(g.deficit_ft - 1.53) < 0.01
    assert g.n_inserted_inside == 2                         # crest + lone reading
    assert analyze(recs, version=2).dark1                   # no window end: falls back to the last reading

def test_v2_gap_in_slow_rise_h14():
    """h14 (USGS 08078000): 75-min archive gap while rising ~0.2 ft per 30 min, past half the rise,
    crest much later. v1 misses it (rate <= 0.3 ft, crest not inside); v2 catches it (rule 8).
    Control: the same gap BEFORE the half-rise level stays healthy in v2 (like h16's gaps)."""
    f = lambda k: 10 + 0.1 * k if k <= 240 else 34 - 0.05 * (k - 240)   # 0.4 ft/h to 34 ft at hour 60
    full = series("2017-08-26 00:00", 340, f)
    def drop(recs, k0):                                    # remove 4 readings -> 75-min gap
        return [r for i, r in enumerate(recs) if not (k0 <= i < k0 + 4)]
    late = drop(full, 160)                                 # hour 40, ~26 ft: inside the rise period
    early = drop(full, 40)                                 # hour 10, ~14 ft: before half the rise (22 ft)
    assert not analyze(late).dark1                         # v1 misses it
    r = analyze(late, version=2)
    assert r.dark1 and not r.dark3
    g = r.dark_gaps[0]
    assert g.in_rise and not g.rising and not g.spans_peak and not g.open_end
    assert abs(g.hours - 1.25) < 0.01 and g.rate30_ft is not None and g.rate30_ft <= 0.3
    assert not analyze(early, version=2).dark1             # control: gap before the rise period

def test_v2_data_ending_early_after_crest_h10():
    """h10 (USGS 08167500): continuous record, crest on 5 Jul, a second small rise on 7 Jul, and the USGS
    data simply ends at 00:00Z 8 Jul while the window runs to 06:00Z. That is not an outage."""
    def f(k):                                   # hours k/4 from 3 Jul 00:00Z
        h = k / 4
        if h < 48: return 1.5
        if h < 52: return 1.5 + 28.5 * (h - 48) / 4          # crest 30.0 at 5 Jul 04:00Z
        if h < 100: return 30.0 - 25.0 * (h - 52) / 48       # recession to 5.0
        return 5.0 + 0.8 * (h - 100)                         # rising again when the data ends
    recs = series("2025-07-03 00:00", 4 * 120 + 1, f)        # last reading 8 Jul 00:00Z
    assert recs[-1][0] == ms("2025-07-08 00:00")
    r = analyze(recs, version=2, window_end_ms=ms("2025-07-08 06:00"))
    assert r.all_gaps == 1 and not r.dark1                   # 6-h tail counted as a gap, but not dark

def test_v2_keeps_v1_results_on_hunt():
    """Hunt was dark under v1; v2 must agree and find the same 35-h gap."""
    r1, r2 = analyze(RECS), analyze(RECS, version=2, window_end_ms=ms("2025-07-05 21:25"))
    assert r2.dark1 and r2.dark3
    g1 = max(r1.dark_gaps, key=lambda g: g.hours); g2 = max(r2.dark_gaps, key=lambda g: g.hours)
    assert (g1.start, g1.end, g1.deficit_ft) == (g2.start, g2.end, g2.deficit_ft)

if __name__ == "__main__":
    test_hunt(); test_estimated_values_do_not_hide_gap()
    test_v2_open_ended_silence_h15(); test_v2_gap_in_slow_rise_h14(); test_v2_data_ending_early_after_crest_h10(); test_v2_keeps_v1_results_on_hunt()
    print("all tests passed")