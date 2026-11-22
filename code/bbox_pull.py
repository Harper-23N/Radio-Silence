"""Hour 18: pull gage height for every USGS gauge inside a bounding box, from the new OGC API.

Uses the 'continuous' collection's bbox filter (checked 17 Nov 2026: a box around Hunt returned
Hunt, North Fork, Kerrville and Guadalupe above Bear Creek), so one paged query covers a whole flood
instead of one query per gauge.

Writes one CSV per gauge to data/raw/<event>/<site>.csv with the SAME columns as gd_fetch.py
(time_utc, value_ft, code), so gd_gaps.analyze() and run_census.py can read either.

Usage (from the repo root):
    python -I code/bbox_pull.py texas -100.6,29.6,-97.8,31.4 2025-07-03T00:00:00Z 2025-07-08T00:00:00Z

bbox order is west,south,east,north (longitude,latitude,longitude,latitude).
Needs USGS_API_KEY in the environment (see gd_fetch.py).
"""
from __future__ import annotations
import argparse, csv, json, os, sys, time, urllib.parse
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # so -I can still find gd_fetch.py
from gd_fetch import OGC, _get

LIMIT = 10000


def pull_bbox(bbox: str, start: str, end: str, param: str = "00065", log=print):
    """Return ({site: [(time, value, code), ...]}, pages, rows, seconds)."""
    key = os.environ.get("USGS_API_KEY")
    if not key:
        log("WARNING: USGS_API_KEY not set; you will hit the low anonymous rate limit.")
    headers = {"X-Api-Key": key} if key else {}
    q = {"bbox": bbox, "parameter_code": param, "time": f"{start}/{end}", "f": "json", "limit": str(LIMIT)}
    url = OGC + "?" + urllib.parse.urlencode(q)

    sites: dict[str, list] = defaultdict(list)
    pages = rows = 0
    t0 = time.time()
    while url:
        j = json.loads(_get(url, headers))
        feats = j.get("features", [])
        pages += 1
        rows += len(feats)
        for f in feats:
            p = f["properties"]
            site = (p.get("monitoring_location_id") or "").replace("USGS-", "")
            v = p.get("value")
            code = (p.get("approval_status") or "") + ("|" + "+".join(p["qualifier"]) if p.get("qualifier") else "")
            sites[site].append((p["time"], float(v) if v not in (None, "") else None, code))
        url = next((l["href"] for l in j.get("links", []) if l.get("rel") == "next"), None)
        log(f"  page {pages}: {len(feats)} rows, {len(sites)} gauges so far")
        if len(feats) == LIMIT and not url:
            log("  WARNING: full page but no 'next' link. You may be missing data; check the API docs.")
    for s in sites.values():
        s.sort()
    return dict(sites), pages, rows, time.time() - t0


def save(sites: dict, outdir: str) -> None:
    os.makedirs(outdir, exist_ok=True)
    for site, recs in sites.items():
        with open(os.path.join(outdir, f"{site}.csv"), "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["time_utc", "value_ft", "code"])
            w.writerows(recs)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("event", help="short name for the flood, e.g. texas")
    ap.add_argument("bbox", help="west,south,east,north")
    ap.add_argument("start", help="e.g. 2025-07-03T00:00:00Z")
    ap.add_argument("end", help="e.g. 2025-07-08T00:00:00Z")
    ap.add_argument("--param", default="00065", help="USGS parameter code (default 00065, gage height)")
    ap.add_argument("--out", default="data/raw", help="parent folder (default data/raw)")
    a = ap.parse_args()

    w, s, e, n = (float(x) for x in a.bbox.split(","))
    if not (w < e and s < n):
        sys.exit("bbox must be west,south,east,north with west<east and south<north")

    print(f"Pulling {a.event}: bbox {a.bbox}, {a.start} to {a.end}, parameter {a.param}")
    sites, pages, rows, secs = pull_bbox(a.bbox, a.start, a.end, a.param)
    outdir = os.path.join(a.out, a.event)
    save(sites, outdir)

    with_data = sum(1 for r in sites.values() if any(v is not None for _, v, _ in r))
    summary = dict(event=a.event, bbox=a.bbox, start=a.start, end=a.end, param=a.param,
                   pages=pages, rows=rows, seconds=round(secs, 1),
                   gauges=len(sites), gauges_with_data=with_data,
                   pulled_at_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    with open(os.path.join(outdir, "_pull_summary.json"), "w") as fh:
        json.dump(summary, fh, indent=2)

    print(f"\nDone: {with_data} gauges with data ({len(sites)} returned), {rows} rows, "
          f"{pages} pages, {secs:.1f} s")
    print(f"Saved to {outdir}/  (summary in _pull_summary.json; copy these numbers to your logbook)")


if __name__ == "__main__":
    main()