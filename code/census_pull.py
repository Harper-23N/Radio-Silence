"""Census downloader: pull gage height for every flood in data/events.csv.

Loops over data/events.csv and, for each flood, runs the same bounding-box pull as bbox_pull.py
(same paging, same handling of sites with two gage-height series), saving
data/raw/<event>/<site>.csv  plus  data/raw/<event>/_pull_summary.json.

Run from the project folder (needs USGS_API_KEY, like bbox_pull.py):
    python -I code/census_pull.py --list                                 # show the plan, pull nothing
    python -I code/census_pull.py --only 2023_idalia,2021_ida,2024_debby # Hour 34 test (short, wide, long)
    python -I code/census_pull.py                                        # pull every TEST flood

Window: from the event's start date 00:00 UTC to the day after its end date 00:00 UTC
(events.csv dates already include the 1-day padding; see build_events.py). Box: west,south,east,north.

Checks before anything is pulled (the script stops and lists every problem):
  - every box has west < east and south < north and lies in the lower 48 (lon -126..-66, lat 24..50)
  - start <= end, dev_or_test is 'dev' or 'test', event names are unique

Stream sites only (prereg.md: "Include only USGS site type ST"):
  Everything in the box with gage height is still downloaded (so excluded sites stay as evidence),
  but each site is marked site_type ST or not_ST in the log and the summary, using one extra query to
  the monitoring-locations collection (bbox + site_type_code=ST). The census analysis must keep only
  ST rows. If that query returns no stream sites while gauges were found, the event is NOT marked
  finished, because the filter probably did not work.

Caching (safe to restart):
  - An event is finished when its _pull_summary.json exists. It is written LAST (and atomically), so
    a crash in the middle leaves no summary and the event is pulled again next time.
  - A finished event with the same box and window is skipped.
  - A finished event with a DIFFERENT box or window is NOT overwritten (warning); use --force.
    An unreadable summary counts as "different", so it is never overwritten without --force.
  - Before saving a new pull, any existing folder for that event (an old box, or a crashed run) is
    renamed to <event>__replaced_<time>, so old gauge files can never mix with the new pull.
  - Development floods are skipped unless --include-dev: their data/raw/<event>/ folders already hold
    the pilot pulls (Hour 19), with the pilot boxes, and must not be overwritten.
  - An event that returns 0 gauges is logged as no_gauges and NOT marked finished (wrong box or dates?).

Log: data/raw/_census_log.csv gets one row per gauge per pull (event, site, site type, readings,
series kept, status) plus one row per event-level problem. Nothing here looks at gaps or outages.
"""
from __future__ import annotations
import argparse, csv, json, os, sys, time, urllib.parse
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bbox_pull import pull_bbox, save, LIMIT
from gd_fetch import OGC, _get

EVENTS = "data/events.csv"
RAW = "data/raw"
LOG = os.path.join(RAW, "_census_log.csv")
LOG_COLS = ["logged_at_utc", "event", "site", "site_type", "n_readings", "n_with_value", "series_kept",
            "status", "note"]
MON_LOC = OGC.replace("/continuous/items", "/monitoring-locations/items")
LON_RANGE, LAT_RANGE = (-126.0, -66.0), (24.0, 50.0)      # lower 48 plus the 0.25 deg widening


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def log_rows(rows):
    os.makedirs(RAW, exist_ok=True)
    new = not os.path.exists(LOG)
    with open(LOG, "a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=LOG_COLS)
        if new:
            w.writeheader()
        w.writerows(rows)


def load_events(path=EVENTS):
    """Read events.csv, add bbox/t0/t1, and stop with a list of problems if any row looks wrong."""
    with open(path, encoding="utf-8-sig", newline="") as fh:
        evs = list(csv.DictReader(fh))
    problems, seen = [], set()
    for i, e in enumerate(evs, start=2):                     # row 1 is the header
        name = (e.get("event") or "").strip()
        label = f"row {i} ({name or 'no name'})"
        e["event"] = name
        if not name:
            problems.append(f"{label}: event name is blank")
        elif name in seen:
            problems.append(f"{label}: event name used twice")
        seen.add(name)
        kind = (e.get("dev_or_test") or "").strip().lower()
        if kind not in ("dev", "test"):
            problems.append(f"{label}: dev_or_test is {e.get('dev_or_test')!r}, expected 'dev' or 'test'")
        e["dev_or_test"] = kind
        try:
            w, s, ea, n = (float(e[k]) for k in ("west", "south", "east", "north"))
        except (TypeError, ValueError):
            problems.append(f"{label}: box has a blank or non-number value")
            continue
        if not (w < ea and s < n):
            problems.append(f"{label}: box needs west < east and south < north (got {w},{s},{ea},{n})")
        if not all(LON_RANGE[0] <= x <= LON_RANGE[1] for x in (w, ea)) or \
           not all(LAT_RANGE[0] <= y <= LAT_RANGE[1] for y in (s, n)):
            problems.append(f"{label}: box {w},{s},{ea},{n} is outside the lower 48 (lon/lat swapped?)")
        try:
            d0, d1 = date.fromisoformat(e["start"].strip()), date.fromisoformat(e["end"].strip())
        except (AttributeError, ValueError):
            problems.append(f"{label}: start/end must be YYYY-MM-DD (got {e.get('start')!r}, {e.get('end')!r})")
            continue
        if d1 < d0:
            problems.append(f"{label}: end {d1} is before start {d0}")
        e["bbox"] = ",".join(str(x) for x in (w, s, ea, n))
        e["t0"] = f"{d0}T00:00:00Z"
        e["t1"] = f"{d1 + timedelta(days=1)}T00:00:00Z"
    if problems:
        sys.exit(f"{path} has {len(problems)} problem(s); nothing was pulled:\n  " + "\n  ".join(problems))
    return evs


def status_of(e):
    """('new' | 'done' | 'different', summary or None)."""
    p = os.path.join(RAW, e["event"], "_pull_summary.json")
    if not os.path.exists(p):
        return "new", None
    try:
        with open(p, encoding="utf-8") as fh:
            s = json.load(fh)
    except ValueError as ex:                   # half-written or non-UTF-8 file: never overwrite silently
        return "different", {"error": repr(ex)}
    same = (s.get("bbox") == e["bbox"] and s.get("start") == e["t0"] and s.get("end") == e["t1"])
    return ("done" if same else "different"), s


def stream_sites(bbox, headers):
    """Site numbers in the box whose USGS site type is ST (stream), from monitoring-locations."""
    q = {"bbox": bbox, "site_type_code": "ST", "f": "json", "limit": str(LIMIT)}
    url, out = MON_LOC + "?" + urllib.parse.urlencode(q), set()
    while url:
        j = json.loads(_get(url, headers))
        for f in j.get("features", []):
            p = f.get("properties") or {}
            sid = str(f.get("id") or p.get("id") or p.get("monitoring_location_id") or "")
            if sid:
                out.add(sid.replace("USGS-", ""))
        url = next((l["href"] for l in j.get("links", []) if l.get("rel") == "next"), None)
    return out


def pull_event(e, headers, tries=3):
    """Stream-site list + bbox pull, retried as a whole. Returns (st_sites, sites, pages, rows, secs, warnings)."""
    for attempt in range(1, tries + 1):
        warns = []

        def plog(msg):                         # print bbox_pull's progress, keep its warnings
            print(msg, flush=True)
            if "WARNING" in msg:
                warns.append(msg.strip())
        try:
            st = stream_sites(e["bbox"], headers)
            sites, pages, rows, secs = pull_bbox(e["bbox"], e["t0"], e["t1"], log=plog)
            return st, sites, pages, rows, secs, warns
        except Exception as ex:                # network or rate-limit trouble: wait and retry
            if attempt == tries:
                raise
            wait = 60 * attempt
            print(f"  error ({ex!r}); retry {attempt + 1}/{tries} in {wait} s", flush=True)
            time.sleep(wait)


def event_problem(e, status, note):
    print(f"  {status.upper()}: {note}", flush=True)
    log_rows([dict(logged_at_utc=now(), event=e["event"], site="", status=status, note=note[:300])])


def write_summary(outdir, summary):
    path = os.path.join(outdir, "_pull_summary.json")
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)
    os.replace(tmp, path)                      # the summary appears all at once or not at all


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", help="comma-separated event names from events.csv")
    ap.add_argument("--include-dev", action="store_true", help="also pull development floods (see notes)")
    ap.add_argument("--force", action="store_true", help="re-pull events whose box or window changed")
    ap.add_argument("--list", action="store_true", help="show the plan and stop")
    a = ap.parse_args()

    evs = load_events()
    if a.only:
        want = {x.strip() for x in a.only.split(",") if x.strip()}
        unknown = want - {e["event"] for e in evs}
        if unknown:
            sys.exit(f"Not in {EVENTS}: {', '.join(sorted(unknown))}")
        evs = [e for e in evs if e["event"] in want]
    if not a.include_dev:
        dev = [e["event"] for e in evs if e["dev_or_test"] == "dev"]
        if dev:
            print(f"Skipping {len(dev)} development flood(s) ({', '.join(dev)}): their pilot pulls are "
                  f"already in data/raw (use --include-dev to change that).")
        evs = [e for e in evs if e["dev_or_test"] != "dev"]

    plan = []
    for e in evs:
        st, s = status_of(e)
        if st == "new":
            action = "pull"
        elif st == "done":
            action = "skip (already pulled)"
        elif a.force:
            action = "pull (--force)"
        elif s and "error" in s and len(s) == 1:
            action = "SKIP: summary file is unreadable (use --force to re-pull)"
        else:
            action = "SKIP: folder exists with a different box/window (use --force to re-pull)"
        plan.append((e, action))
    print(f"{len(plan)} event(s):")
    for e, action in plan:
        print(f"  {e['event']:<44} {e['start']} to {e['end']}  box {e['bbox']}  -> {action}")
    if a.list:
        return

    key = os.environ.get("USGS_API_KEY")
    if not key and any(act.startswith("pull") for _, act in plan):
        sys.exit("USGS_API_KEY is not set. Set it first (see gd_fetch.py); without it the census "
                 "would run into the low anonymous rate limit.")
    headers = {"X-Api-Key": key} if key else {}
    t_all = time.time()
    done = failed = 0
    for e, action in plan:
        if not action.startswith("pull"):
            continue
        print(f"\n=== {e['event']} ===", flush=True)
        try:
            st_sites, sites, pages, rows, secs, warns = pull_event(e, headers)
        except Exception as ex:
            event_problem(e, "event_failed", repr(ex))
            failed += 1
            continue
        if not sites:
            event_problem(e, "no_gauges", f"0 gauges returned for box {e['bbox']}, {e['t0']} to {e['t1']}; "
                                          f"check this event's box and dates in {EVENTS}")
            failed += 1
            continue
        if not st_sites:
            event_problem(e, "stream_check_failed", f"{len(sites)} gauges returned but the monitoring-locations "
                                                    f"query found no stream (ST) sites in the box; the site-type "
                                                    f"filter probably did not work. Not marked finished.")
            failed += 1
            continue

        outdir = os.path.join(RAW, e["event"])
        if os.path.isdir(outdir):              # old box, or a crashed run: keep it, but out of the way
            old = f"{outdir}__replaced_{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}"
            try:
                os.rename(outdir, old)
            except OSError as ex:              # e.g. a CSV in it is open in Excel
                event_problem(e, "event_failed", f"could not move old folder {outdir} aside ({ex!r}); "
                                                 f"close any open files in it and re-run")
                failed += 1
                continue
            print(f"  moved the old folder to {old}", flush=True)

        multi = save(sites, outdir, headers)
        entries = []
        for site, series in sorted(sites.items()):
            kept = multi[site]["chosen"] if site in multi else next(iter(series))
            recs = series[kept]
            n_val = sum(1 for _, v, _ in recs if v is not None)
            notes = [f"{len(series)} series"] if len(series) > 1 else []
            if len(recs) >= LIMIT:
                notes.append(f"{len(recs)} readings (>= {LIMIT}): check this gauge is complete")
            entries.append(dict(logged_at_utc=now(), event=e["event"], site=site,
                                site_type="ST" if site in st_sites else "not_ST",
                                n_readings=len(recs), n_with_value=n_val, series_kept=kept,
                                status="ok" if n_val else "no_values", note="; ".join(notes)))
        log_rows(entries)
        not_st = sorted(x["site"] for x in entries if x["site_type"] != "ST")
        summary = dict(event=e["event"], event_id=e.get("event_id"), dev_or_test=e["dev_or_test"],
                       bbox=e["bbox"], start=e["t0"], end=e["t1"], param="00065",
                       pages=pages, rows=rows, seconds=round(secs, 1),
                       seconds_per_page=round(secs / pages, 2) if pages else None,
                       gauges=len(sites),
                       gauges_with_data=sum(1 for x in entries if x["status"] == "ok"),
                       stream_gauges_with_data=sum(1 for x in entries
                                                   if x["status"] == "ok" and x["site_type"] == "ST"),
                       non_stream_sites=not_st,
                       multi_series_sites=multi,
                       pull_warnings=warns,          # e.g. bbox_pull's "full page but no 'next' link"
                       pulled_at_utc=now())
        write_summary(outdir, summary)
        done += 1
        print(f"  {summary['gauges_with_data']} gauges with data ({len(sites)} returned, "
              f"{summary['stream_gauges_with_data']} of them stream sites), {rows} rows, {pages} pages, "
              f"{secs:.1f} s", flush=True)
        if not_st:
            print(f"  {len(not_st)} non-stream site(s) downloaded but marked not_ST: {', '.join(not_st)}")
        for w in warns:
            print(f"  !! {w}")

    print(f"\nFinished: {done} pulled, {failed} failed, {time.time() - t_all:.0f} s in total. Log: {LOG}")
    if failed:
        print("Re-run the same command to retry failed events; finished ones are skipped.")


if __name__ == "__main__":
    main()