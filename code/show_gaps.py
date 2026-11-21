"""Print the gap-rule result for one of my USGS downloads.
Usage: python -I code/show_gaps.py data/mine_hunt.csv"""
import csv, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from datetime import datetime, timezone
from gd_gaps import analyze, max_rise_1h

def utc(ms):
    return datetime.fromtimestamp(ms / 1000, timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

path = sys.argv[1]
with open(path, encoding="utf-8-sig", newline="") as f:
    rows = [r for r in csv.DictReader(f) if r["time_utc"]]
recs = [(int(datetime.fromisoformat(r["time_utc"]).timestamp() * 1000),
         float(r["value_ft"]) if r["value_ft"] else None, r["code"]) for r in rows]

res = analyze(recs)
print(f"{path}: {res.n} readings, usual interval {res.median_interval_min:g} min, "
      f"rise {res.rise_ft} ft, crest {res.max_ft} ft at {utc(res.t_max)}, 1-h rise {max_rise_1h(recs)} ft")
for t, v, c in res.inserted:
    print(f"  inserted value: {v} ft at {utc(t)} ({c})")
for g in res.dark_gaps:
    print(f"  DARK gap: {utc(g.start)} to {utc(g.end)} = {g.hours} h, last reading {g.v_before} ft, "
          f"deficit {g.deficit_ft} ft, rose {g.rate30_ft} ft in prior 30 min")
if not res.dark_gaps:
    print("  no dark gaps")