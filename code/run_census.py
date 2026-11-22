"""Hour 20: run the gap rule on every raw CSV and write one row per gauge.

Reads  data/raw/<event>/<site>.csv  (made by bbox_pull.py)
Writes data/census_mine.csv  with the same columns as data/stations_7floods_v3.csv

Usage (from the repo root):
    python -I code/run_census.py                 # all events in data/raw
    python -I code/run_census.py texas helene    # only these events

Notes on matching the pilot table:
- One row per gauge. If a gauge has several dark gaps, the gap columns describe ONE of them:
  the gap that contains the crest if there is one, otherwise the longest. (Hunt 08165500 and
  Center Point 08166250 in the pilot table follow this.) n_dark_gaps tells you how many there were.
- v1rule_dark is left blank: it came from an older version of the rule that is not in gd_gaps.py.
- Gauges with fewer than 10 numeric readings get analyze() = None; they are written with
  status=too_few_readings so you can see them instead of losing them silently.
"""
from __future__ import annotations
import csv, os, sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gd_gaps import analyze, max_rise_1h

RAW = "data/raw"
OUT = "data/census_mine.csv"
COLUMNS = ["event", "site", "rise_ft", "max_ft", "med_int_min", "n_inserted", "max_rise_1h_ft",
           "dark1h", "dark3h", "peak_in_gap", "gap_h", "gap_start_utc", "stage_last_reading",
           "stage_after", "deficit_ft", "rate30_ft", "v1rule_dark"]
EXTRA = ["n_readings", "n_dark_gaps", "status"]          # added at the end; not in the pilot table


def load(path):
    """Read one bbox_pull.py CSV into (time_ms, value, code) tuples."""
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = [r for r in csv.DictReader(f) if r.get("time_utc")]
    out = []
    for r in rows:
        t = datetime.fromisoformat(r["time_utc"].replace("Z", "+00:00"))
        v = float(r["value_ft"]) if r["value_ft"] not in ("", None) else None
        out.append((int(t.timestamp() * 1000), v, r.get("code", "")))
    return out


def utc_min(ms):
    return datetime.fromtimestamp(ms / 1000, timezone.utc).strftime("%Y-%m-%d %H:%M")


def row_for(event, site, recs):
    row = dict.fromkeys(COLUMNS + EXTRA, "")
    row.update(event=event, site=site, n_readings=sum(1 for _, v, _ in recs if v is not None))
    res = analyze(recs)
    if res is None:
        row["status"] = "too_few_readings"
        return row
    row.update(rise_ft=res.rise_ft, max_ft=res.max_ft, med_int_min=f"{res.median_interval_min:g}",
               n_inserted=len(res.inserted), max_rise_1h_ft=max_rise_1h(recs),
               dark1h=int(res.dark1), dark3h=int(res.dark3),
               n_dark_gaps=len(res.dark_gaps), status="ok", peak_in_gap=0)
    if res.dark_gaps:
        g = max(res.dark_gaps, key=lambda g: (g.spans_peak, g.hours))   # crest gap first, else longest
        row.update(peak_in_gap=int(g.spans_peak), gap_h=g.hours, gap_start_utc=utc_min(g.start),
                   stage_last_reading=g.v_before, stage_after=g.v_after, deficit_ft=g.deficit_ft,
                   rate30_ft="" if g.rate30_ft is None else g.rate30_ft)
    return row


def main():
    events = sys.argv[1:] or sorted(d for d in os.listdir(RAW) if os.path.isdir(os.path.join(RAW, d)))
    rows = []
    for ev in events:
        folder = os.path.join(RAW, ev)
        files = sorted(f for f in os.listdir(folder) if f.endswith(".csv"))
        for f in files:
            rows.append(row_for(ev, f[:-4], load(os.path.join(folder, f))))
        dark = sum(1 for r in rows if r["event"] == ev and r["dark1h"] == 1)
        print(f"{ev:12s} {len(files):4d} gauges, {dark:3d} dark (1 h rule)")
    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS + EXTRA)
        w.writeheader()
        w.writerows(rows)
    skipped = sum(1 for r in rows if r["status"] != "ok")
    print(f"\nWrote {len(rows)} rows to {OUT} ({skipped} with too few readings)")


if __name__ == "__main__":
    main()