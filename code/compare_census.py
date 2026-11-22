"""Hour 20, steps 2 and 4: compare my census (data/census_mine.csv) with the pilot table
(data/stations_7floods_v3.csv) gauge by gauge on dark1h, then give big-rise and small-rise numbers.

Usage (from the repo root):
    python -I code/compare_census.py

Gauges that are only in my census (the 7 lakes, springs and estuary found in Hour 19) are listed
but left out of the agreement percentage, because the pilot has no row to compare them with.
"""
import csv

MINE, PILOT = "data/census_mine.csv", "data/stations_7floods_v3.csv"


def load(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return {(r["event"], r["site"]): r for r in csv.DictReader(f)}


mine, pilot = load(MINE), load(PILOT)
both = sorted(set(mine) & set(pilot))
only_mine = sorted(set(mine) - set(pilot))
only_pilot = sorted(set(pilot) - set(mine))

same = [k for k in both if mine[k]["dark1h"] == pilot[k]["dark1h"]]
diff = [k for k in both if k not in same]
print(f"Gauges in both tables: {len(both)}")
print(f"Agree on dark1h: {len(same)} of {len(both)} = {100 * len(same) / len(both):.1f}%  (target: at least 95%)")

print(f"\nDisagreements ({len(diff)}):")
for k in diff:
    m, p = mine[k], pilot[k]
    print(f"  {k[0]:12s} {k[1]:10s} mine dark1h={m['dark1h']} pilot={p['dark1h']} | "
          f"rise mine {m['rise_ft']} / pilot {p['rise_ft']} | gap mine {m['gap_h'] or '-'} h / pilot {p['gap_h'] or '-'} h")

print(f"\nOnly in my census (not compared): {len(only_mine)}  {[k[1] for k in only_mine]}")
print(f"Only in pilot (missing from mine): {len(only_pilot)}  {[k[1] for k in only_pilot]}")


def rise_bins(table, keys, label):
    big = [k for k in keys if float(table[k]["rise_ft"] or 0) >= 20]
    small = [k for k in keys if table[k]["rise_ft"] != "" and float(table[k]["rise_ft"]) < 5]
    bd = sum(int(table[k]["dark1h"] or 0) for k in big)
    sd = sum(int(table[k]["dark1h"] or 0) for k in small)
    print(f"  {label:6s} big rises (20 ft or more): {bd} of {len(big)} dark | small rises (under 5 ft): {sd} of {len(small)} dark")


print("\nStep 4, dark by size of rise (gauges in both tables only):")
rise_bins(mine, both, "Mine:")
rise_bins(pilot, both, "Pilot:")