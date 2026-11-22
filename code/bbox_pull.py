"""Hour 18: pull gage height for every USGS gauge inside a bounding box, from the new OGC API.

Uses the 'continuous' collection's bbox filter (checked 17 Nov 2026: a box around Hunt returned
Hunt, North Fork, Kerrville and Guadalupe above Bear Creek), so one paged query covers a whole flood
instead of one query per gauge.

Writes one CSV per gauge to data/raw/<event>/<site>.csv with the SAME columns as gd_fetch.py
(time_utc, value_ft, code), so gd_gaps.analyze() and run_census.py can read either.

Sites with more than one gage-height time series (e.g. two sensors or two datums): the API returns
all of them under one site number. Each reading carries a time_series_id, so the series are kept
apart. One series goes in <site>.csv (see choose_series for how it is picked; a hand choice in
data/series_choices.csv wins); the others go in
data/raw/<event>/extra_series/<site>__<time_series_id>.csv (run_census.py ignores that folder).
Every multi-series site is listed in _pull_summary.json with which series was chosen and why.
(Fix added 21 Nov 2026: before this, 6 pilot gauges had two series mixed in one file.)

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
TS_META = OGC.replace("/continuous/items", "/time-series-metadata/items")
CHOICES = "data/series_choices.csv"


def pull_bbox(bbox: str, start: str, end: str, param: str = "00065", log=print):
    """Return ({site: {time_series_id: [(time, value, code), ...]}}, pages, rows, seconds)."""
    key = os.environ.get("USGS_API_KEY")
    if not key:
        log("WARNING: USGS_API_KEY not set; you will hit the low anonymous rate limit.")
    headers = {"X-Api-Key": key} if key else {}
    q = {"bbox": bbox, "parameter_code": param, "time": f"{start}/{end}", "f": "json", "limit": str(LIMIT)}
    url = OGC + "?" + urllib.parse.urlencode(q)

    sites: dict[str, dict] = defaultdict(lambda: defaultdict(list))
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
            ts = p.get("time_series_id") or "unknown"
            sites[site][ts].append((p["time"], float(v) if v not in (None, "") else None, code))
        url = next((l["href"] for l in j.get("links", []) if l.get("rel") == "next"), None)
        log(f"  page {pages}: {len(feats)} rows, {len(sites)} gauges so far")
        if len(feats) == LIMIT and not url:
            log("  WARNING: full page but no 'next' link. You may be missing data; check the API docs.")
    for series in sites.values():
        for recs in series.values():
            recs.sort()
    return {k: dict(v) for k, v in sites.items()}, pages, rows, time.time() - t0


def ts_metadata(ts_id: str, headers: dict) -> dict:
    """Look up one time series' metadata (primary flag, sublocation, description)."""
    try:
        j = json.loads(_get(f"{TS_META}/{urllib.parse.quote(ts_id)}?f=json", headers))
        return j.get("properties", {})
    except Exception as e:                                   # metadata is a helper; never stop the pull
        return {"error": repr(e)}


def load_choices(path: str = CHOICES) -> dict:
    """Hand-made series choices: data/series_choices.csv with columns site,time_series_id,reason."""
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8-sig", newline="") as fh:
        return {r["site"].strip(): (r["time_series_id"].strip(), r.get("reason", "").strip()) for r in csv.DictReader(fh)}


def choose_series(site: str, series: dict, headers: dict, choices: dict, log=print):
    """Pick the series for <site>.csv. Returns (chosen_ts_id, info_for_summary).

    Order: (1) a hand choice in data/series_choices.csv; (2) the only series USGS flags primary;
    (3) the only series whose description says 'Primary Sensor'; (4) otherwise the series with the
    most readings, marked CHECK BY HAND.
    """
    if len(series) == 1:
        return next(iter(series)), None
    info = {}
    for ts in series:
        m = ts_metadata(ts, headers)
        info[ts] = dict(n_readings=len(series[ts]), primary=m.get("primary"),
                        sublocation=m.get("sublocation_identifier"),
                        description=m.get("web_description"), error=m.get("error"))
    flagged = [ts for ts in series if str(info[ts]["primary"] or "").strip().lower() == "primary"]
    desc_primary = [ts for ts in series
                    if "primary sensor" in str(info[ts]["description"] or "").lower()]
    if site in choices and choices[site][0] in series:
        chosen, why = choices[site][0], f"hand choice in series_choices.csv: {choices[site][1]}"
    elif len(flagged) == 1:
        chosen, why = flagged[0], "the only series flagged primary by USGS"
    elif len(desc_primary) == 1:
        chosen, why = desc_primary[0], "USGS description says 'Primary Sensor'"
    else:
        chosen = max(series, key=lambda ts: len(series[ts]))
        why = "no single primary series; kept the one with most readings. CHECK BY HAND"
    log(f"  {site}: {len(series)} gage-height series; kept {chosen} ({why})")
    return chosen, dict(chosen=chosen, why=why, series=info)


def write_csv(path: str, recs: list) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["time_utc", "value_ft", "code"])
        w.writerows(recs)


def save(sites: dict, outdir: str, headers: dict) -> dict:
    """Write <site>.csv (one series) per gauge; extra series to extra_series/. Return multi-series info."""
    os.makedirs(outdir, exist_ok=True)
    multi, choices = {}, load_choices()
    for site, series in sites.items():
        chosen, info = choose_series(site, series, headers, choices)
        write_csv(os.path.join(outdir, f"{site}.csv"), series[chosen])
        if info:
            multi[site] = info
            os.makedirs(os.path.join(outdir, "extra_series"), exist_ok=True)
            for ts, recs in series.items():
                if ts != chosen:
                    safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in ts)
                    write_csv(os.path.join(outdir, "extra_series", f"{site}__{safe}.csv"), recs)
    return multi


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
    key = os.environ.get("USGS_API_KEY")
    multi = save(sites, outdir, {"X-Api-Key": key} if key else {})

    with_data = sum(1 for ser in sites.values() if any(v is not None for recs in ser.values() for _, v, _ in recs))
    summary = dict(event=a.event, bbox=a.bbox, start=a.start, end=a.end, param=a.param,
                   pages=pages, rows=rows, seconds=round(secs, 1),
                   gauges=len(sites), gauges_with_data=with_data,
                   multi_series_sites=multi,
                   pulled_at_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    with open(os.path.join(outdir, "_pull_summary.json"), "w") as fh:
        json.dump(summary, fh, indent=2)

    print(f"\nDone: {with_data} gauges with data ({len(sites)} returned), {rows} rows, "
          f"{pages} pages, {secs:.1f} s")
    if multi:
        print(f"{len(multi)} gauge(s) had more than one gage-height series: {sorted(multi)} (details in _pull_summary.json)")
    print(f"Saved to {outdir}/  (summary in _pull_summary.json; copy these numbers to your logbook)")


if __name__ == "__main__":
    main()