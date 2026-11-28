"""Which gap rule did my Hour 46 census use? (written 28 Nov 2026)

Run from the repo root:
    python -I code/check_hour46.py data/census_archive.csv
    (give the path of the file Hour 46 actually wrote, if it has another name)

For every row of that file it re-runs rule v1 and the frozen rule v2 on the same raw file
(data/raw/<event>/<site>.csv) and reports, for each column whose name contains 'dark',
how many rows agree with v1 and how many with v2. It also checks the file for rows that should
not be in the census: non-stream sites (not_ST in the pull log) and '__replaced_' folders.

It stays BLIND: it prints agreement counts and the IDs of rows that disagree, never how many
test-flood gauges are dark.
"""
from __future__ import annotations
import csv, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gd_gaps import analyze
from census_archive import load, to_ms, window_end, events, site_types, RAW


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "data/census_archive.csv"
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        sys.exit(f"{path} is empty")
    cols = [c for c in rows[0] if "dark" in c.lower()]
    print(f"{path}: {len(rows)} rows; columns checked: {cols or 'NONE (no column name contains dark)'}")
    ev = {e["event"]: e for e in events()}
    types = site_types()

    replaced = sorted({r["event"] for r in rows if "__replaced_" in r.get("event", "")})
    unknown = sorted({r["event"] for r in rows if r.get("event") not in ev} - set(replaced))
    not_st = [r for r in rows if types.get((r.get("event"), r.get("site"))) == "not_ST"]
    print(f"rows from '__replaced_' folders: {len(replaced)} events {replaced}")
    print(f"rows whose event is not in events.csv: {unknown}")
    print(f"rows for NON-stream sites (not_ST in the pull log): {len(not_st)}"
          + ("  <- the census must keep ST sites only" if not_st else ""))

    agree = {c: {"v1": 0, "v2": 0, "n": 0, "only_v1": [], "only_v2": [], "neither": []} for c in cols}
    skipped = 0
    for r in rows:
        e = ev.get(r.get("event"))
        p = os.path.join(RAW, r.get("event", ""), f"{r.get('site', '')}.csv")
        if not e or not os.path.exists(p):
            skipped += 1
            continue
        recs = load(p)
        r1, r2 = analyze(recs), analyze(recs, version=2, window_end_ms=to_ms(window_end(e)))
        if r1 is None:
            continue
        for c in cols:
            three = "3" in c                                   # dark3h-style column: compare with >= 3 h
            d1, d2 = (int(r1.dark3), int(r2.dark3)) if three else (int(r1.dark1), int(r2.dark1))
            try:
                mine = int(float(r[c]))
            except (TypeError, ValueError):
                continue
            a = agree[c]
            a["n"] += 1
            a["v1"] += mine == d1
            a["v2"] += mine == d2
            key = f"{r['event']}/{r['site']}"
            if mine == d1 and mine != d2:
                a["only_v1"].append(key)
            elif mine == d2 and mine != d1:
                a["only_v2"].append(key)
            elif mine != d1 and mine != d2:
                a["neither"].append(key)
    print(f"rows skipped (event not in events.csv or raw file missing): {skipped}\n")
    for c, a in agree.items():
        if not a["n"]:
            continue
        print(f"column '{c}' ({a['n']} rows): matches v1 on {a['v1']}, matches v2 on {a['v2']}")
        print(f"   rows only v1 explains: {len(a['only_v1'])}  {a['only_v1'][:10]}")
        print(f"   rows only v2 explains: {len(a['only_v2'])}  {a['only_v2'][:10]}")
        print(f"   rows neither explains: {len(a['neither'])}  {a['neither'][:10]}")
        if a["v1"] == a["n"] and a["v2"] == a["n"]:
            verdict = "can't tell: v1 and v2 agree on every one of these rows"
        elif a["v2"] == a["n"]:
            verdict = "made with rule v2"
        elif a["v1"] == a["n"]:
            verdict = "made with rule v1 -> re-run Hour 46 with code/census_archive.py"
        else:
            verdict = "unclear: some rows match neither rule (different window end, data or code?)"
        print(f"   -> {verdict}\n")


if __name__ == "__main__":
    main()
