"""Hour 46: run the archive gap rule (v1 AND the frozen v2) on every flood in data/events.csv.

Run from the repo root, after census_pull.py:
    python -I code/census_archive.py

Reads   data/events.csv, data/raw/<event>/<site>.csv, data/raw/<event>/_pull_summary.json,
        data/raw/_census_log.csv (site types)
Writes  data/census_archive.csv   one row per gauge-event

What it does differently from the Hour 20 run_census.py
  - v2 is the main rule (frozen 22 Nov 2026); v1 is kept in its own columns for comparison.
  - v2 rule 7 needs the window end: test floods use the end in _pull_summary.json (what was really
    pulled); development floods use the same window ends as the pilot census (DEV_END below), so the
    dev numbers can be compared with the 41/116 from 22 Nov.
  - site_type comes from the census pull log (ST or not_ST). Only ST rows count in the census
    (prereg.md). Dev floods were pulled before the filter existed, so their site_type is blank.
  - Only folders named in events.csv are read: '<event>__replaced_<time>' folders and extra_series/
    are ignored.
  - BLIND: it prints row counts only, never dark counts or rates for TEST floods (Hour 46 step 3).
"""
from __future__ import annotations
import csv, json, os, sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gd_gaps import analyze, max_rise_1h

RAW, EVENTS, OUT = "data/raw", "data/events.csv", "data/census_archive.csv"
LOG = os.path.join(RAW, "_census_log.csv")
DEV_END = {  # window ends used by the pilot v1/v2 census (22 Nov 2026)
    "harvey": "2017-09-02T06:00:00Z", "helene": "2024-10-01T06:00:00Z", "kentucky": "2022-08-01T06:00:00Z",
    "texas": "2025-07-08T06:00:00Z", "vermont": "2023-07-15T06:00:00Z", "waverly": "2021-08-25T06:00:00Z",
    "yellowstone": "2022-06-17T06:00:00Z",
}
COLS = ["event", "dev_or_test", "site", "site_type", "status", "n", "rise_ft", "max_ft", "med_int_min",
        "n_inserted", "max_rise_1h_ft", "v1_dark", "v1_dark3h", "v2_dark", "v2_dark3h", "v2_why",
        "gap_start_utc", "gap_h", "open_end", "stage_last_reading", "stage_after", "deficit_ft", "rate30_ft",
        "window_end_utc"]


def to_ms(s: str) -> int:
    return int(datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp() * 1000)


def utc(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, timezone.utc).strftime("%Y-%m-%d %H:%M")


def load(path: str):
    """One gauge CSV (time_utc, value_ft, code) -> [(time_ms, value or None, code)]."""
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = [r for r in csv.DictReader(f) if r.get("time_utc")]
    return [(to_ms(r["time_utc"]), float(r["value_ft"]) if r["value_ft"] not in ("", None) else None,
             r.get("code", "") or "") for r in rows]


def events():
    with open(EVENTS, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def window_end(e) -> str:
    p = os.path.join(RAW, e["event"], "_pull_summary.json")
    if e["dev_or_test"] == "test" and os.path.exists(p):
        return json.load(open(p, encoding="utf-8"))["end"]
    if e["event"] in DEV_END:
        return DEV_END[e["event"]]
    d = datetime.fromisoformat(e["end"]) + timedelta(days=1)          # census_pull's rule
    return d.strftime("%Y-%m-%dT00:00:00Z")


def site_types():
    out = {}
    if os.path.exists(LOG):
        with open(LOG, encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                if r.get("site"):
                    out[(r["event"], r["site"])] = r["site_type"]       # last pull wins
    return out


def row_for(e, site, recs, end_iso, stype):
    row = dict.fromkeys(COLS, "")
    row.update(event=e["event"], dev_or_test=e["dev_or_test"], site=site, site_type=stype, window_end_utc=end_iso)
    r1 = analyze(recs)
    r2 = analyze(recs, version=2, window_end_ms=to_ms(end_iso))
    if r2 is None:
        row.update(status="too_few_readings", n=sum(1 for _, v, _ in recs if v is not None))
        return row
    row.update(status="ok", n=r2.n, rise_ft=r2.rise_ft, max_ft=r2.max_ft, med_int_min=f"{r2.median_interval_min:g}",
               n_inserted=len(r2.inserted), max_rise_1h_ft=max_rise_1h(recs),
               v1_dark=int(r1.dark1), v1_dark3h=int(r1.dark3), v2_dark=int(r2.dark1), v2_dark3h=int(r2.dark3))
    if r2.dark_gaps:
        why = set()
        for g in r2.dark_gaps:
            why |= {k for k, on in (("rising", g.rising), ("spans_peak", g.spans_peak),
                                    ("in_rise", g.in_rise), ("open_end", g.open_end)) if on}
        g = max(r2.dark_gaps, key=lambda g: (g.spans_peak, g.hours))   # crest gap first, else longest
        row.update(v2_why="+".join(sorted(why)), gap_start_utc=utc(g.start), gap_h=g.hours, open_end=int(g.open_end),
                   stage_last_reading=g.v_before, stage_after="" if g.v_after is None else g.v_after,
                   deficit_ft=g.deficit_ft, rate30_ft="" if g.rate30_ft is None else g.rate30_ft)
    return row


def main():
    types = site_types()
    rows = []
    for e in events():
        folder = os.path.join(RAW, e["event"])
        if not os.path.isdir(folder):
            print(f"{e['event']:<44} MISSING folder {folder}")
            continue
        end_iso = window_end(e)
        files = sorted(f for f in os.listdir(folder) if f.endswith(".csv") and not f.startswith("_"))
        for f in files:
            site = f[:-4]
            rows.append(row_for(e, site, load(os.path.join(folder, f)), end_iso, types.get((e["event"], site), "")))
        mine = [r for r in rows if r["event"] == e["event"]]
        n_st = sum(r["site_type"] == "ST" for r in mine)
        line = f"{e['event']:<44} {e['dev_or_test']:<4} {len(mine):5d} gauges ({n_st} ST)"
        if e["dev_or_test"] == "dev":                                   # dev floods may be looked at
            big = [r for r in mine if r["status"] == "ok" and float(r["rise_ft"]) >= 20]
            line += (f" | big rise: v1 dark {sum(r['v1_dark'] for r in big)}/{len(big)}, "
                     f"v2 dark {sum(r['v2_dark'] for r in big)}/{len(big)}")
        print(line, flush=True)
    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)
    print(f"\nWrote {len(rows)} rows to {OUT} "
          f"({sum(r['status'] != 'ok' for r in rows)} with too few readings). Test-flood results not shown.")


if __name__ == "__main__":
    main()
