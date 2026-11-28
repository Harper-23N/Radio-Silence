"""DarkWatch: a live logger that records, every 15 minutes, the newest reading of each gauge on a watch list,
so you capture REAL-TIME outages (what forecasters actually saw) instead of the repaired archive.

Run it either
  (a) on your own computer:   python -I code/darkwatch.py data/watchlist.csv data/darkwatch_log_v2.csv
  (b) in the cloud: .github/workflows/darkwatch.yml, started every 15 min by cron-job.org (workflow_dispatch)

watchlist.csv columns: site,nwsli,name.
The log gets one row per gage-height TIME SERIES per poll:
    poll_time_utc, site, time_series_id, latest_obs_time_utc, latest_value_ft, minutes_since_obs
A gauge whose newest reading is missing gets one row with blank time_series_id and value.

Change 28 Nov 2026 (log v2): some sites have two or more gage-height series (two sensors or two datums).
The API returns one 'latest' row per series; v1 kept only whichever came last, so 4 watchlist gauges
switched between series from poll to poll (08101340: 12.94 / 4.51 / -0.08 ft; 08104590: 5.60 / 19.08 ft;
08167200: 5.26 / 12.99 ft; 08168770). v2 keeps every series in its own row, so each can be followed on
its own. The v1 log (data/darkwatch_log.csv, 21-28 Nov 2026) is kept unchanged; for those 4 sites its
values cannot be trusted.
Also new: each request is retried (HTTP 429/5xx and network drops) before a poll is given up, because
3 polls were lost to HTTP 429 on 27 Nov 2026. Failures still go to <log>.errors and never crash the run.
"""
from __future__ import annotations
import csv, http.client, json, os, sys, time, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timezone

LATEST = "https://api.waterdata.usgs.gov/ogcapi/v1/collections/latest-continuous/items"
COLS = ["poll_time_utc", "site", "time_series_id", "latest_obs_time_utc", "latest_value_ft", "minutes_since_obs"]
RETRY_WAITS = (15, 45)                                       # seconds; keeps a poll well inside 15 minutes


def get_json(url: str, hdr: dict) -> dict:
    for k in range(len(RETRY_WAITS) + 1):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=hdr), timeout=60) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503, 504) or k == len(RETRY_WAITS):
                raise
        except (urllib.error.URLError, TimeoutError, ConnectionError, http.client.HTTPException):
            if k == len(RETRY_WAITS):
                raise
        time.sleep(RETRY_WAITS[k])
    raise RuntimeError("unreachable")


def latest(sites: list[str]) -> dict[str, list[tuple[str, str, float | None]]]:
    """{site: [(time_series_id, obs_time, value), ...]} with one entry per gage-height series."""
    key = os.environ.get("USGS_API_KEY")
    hdr = {"User-Agent": "GaugeDark DarkWatch (student project)", **({"X-Api-Key": key} if key else {})}
    out: dict[str, list] = {}
    for i in range(0, len(sites), 50):                     # small batches keep URLs short
        chunk = sites[i:i + 50]
        q = {"monitoring_location_id": ",".join(f"USGS-{s}" for s in chunk), "parameter_code": "00065",
             "f": "json", "limit": "500"}
        url = LATEST + "?" + urllib.parse.urlencode(q)
        while url:
            j = get_json(url, hdr)
            for f in j.get("features", []):
                p = f["properties"]
                s = p["monitoring_location_id"].replace("USGS-", "")
                v = p.get("value")
                out.setdefault(s, []).append((p.get("time_series_id") or "", p["time"],
                                              float(v) if v not in (None, "") else None))
            url = next((l["href"] for l in j.get("links", []) if l.get("rel") == "next"), None)
        time.sleep(1)
    return out


def poll_once(watchlist: str, log: str):
    sites = [r["site"] for r in csv.DictReader(open(watchlist, encoding="utf-8-sig"))]
    now = datetime.now(timezone.utc)
    vals = latest(sites)
    new = not os.path.exists(log)
    with open(log, "a", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        if new:
            w.writerow(COLS)
        for s in sites:
            for ts, t, v in sorted(vals.get(s) or [("", None, None)], key=lambda x: x[0]):
                age = round((now - datetime.fromisoformat(t)).total_seconds() / 60, 1) if t else None
                w.writerow([now.isoformat(timespec="minutes"), s, ts, t, v, age])


if __name__ == "__main__":
    wl, lg = sys.argv[1], sys.argv[2]
    once = "--once" in sys.argv
    while True:
        try:
            poll_once(wl, lg)
        except Exception as e:                              # never crash the logger; record the failure
            with open(lg + ".errors", "a") as fh:
                fh.write(f"{datetime.now(timezone.utc).isoformat()} {e!r}\n")
        if once:
            break
        time.sleep(15 * 60)
