"""Build the candidate flood list (Hour 31) from the USGS STN services.

Run from the project folder (the one containing code/ and data/):
    python -I code/stn_event_list.py
    python -I code/stn_event_list.py --hwm-url "https://.../filteredhwms/?event={id}&format=json"
--hwm-url is the high-water-mark address copied from the Flood Event Viewer's Network tab,
with the event number replaced by {id}.

What it does, for every STN event that starts in 2017-2025:
  1. downloads the event's high-water marks (HWMs) from
     https://api.waterdata.usgs.gov/stnservices/filteredhwms/?event=<id>&format=json
     and saves the raw JSON in data/raw/stn_hwms/<id>.json (re-runs reuse saved files)
  2. counts the marks: all marks, and marks with a surveyed elevation
  3. counts how many marks lie in the lower 48 (rough lat/lon box)
  4. draws the pre-registered box: rectangle around the marks, plus 0.25 deg each side
  5. applies the pre-registered window: event start to end, plus 1 day each side;
     flags events with no end date or longer than 14 days (-> NOAA episode dates)
  6. marks the 7 development floods
Writes data/events_candidates.csv. It does NOT apply the >= 50 rule or drop anything:
open the CSV and apply the rule yourself, so every decision is yours and visible.

Uses no gauge or outage data. Prints the field names of the first mark it sees, so you
can check which columns hold latitude, longitude and elevation.
"""
import csv, json, os, sys, time, urllib.request
from datetime import datetime, timedelta

BASE = "https://api.waterdata.usgs.gov/stnservices"
DEV = {180: "harvey", 311: "waverly", 319: "yellowstone", 321: "kentucky",
       334: "vermont", 346: "helene", 357: "texas"}
PAD_DEG, PAD_DAYS, MAX_DAYS = 0.25, 1, 14
RAW = "data/raw/stn_hwms"


def get_json(url):
    hdr = {"User-Agent": "RadioSilence student project"}
    if os.environ.get("USGS_API_KEY"):
        hdr["X-Api-Key"] = os.environ["USGS_API_KEY"]
    with urllib.request.urlopen(urllib.request.Request(url, headers=hdr), timeout=120) as r:
        return json.loads(r.read())


def pick(keys, *words):
    """First field name containing all the given words (case-insensitive)."""
    for k in keys:
        if all(w in k.lower() for w in words):
            return k
    return None


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def day(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00")) if s else None


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--hwm-url", default=BASE + "/filteredhwms/?event={id}&format=json",
                    help="high-water-mark URL with {id} where the event number goes")
    a = ap.parse_args()
    if "{id}" not in a.hwm_url:
        sys.exit("--hwm-url must contain {id} where the event number goes")
    os.makedirs(RAW, exist_ok=True)
    events = get_json(f"{BASE}/events/")
    cand = [e for e in events if e.get("start_date") and "2017-01-01" <= e["start_date"][:10] <= "2025-12-31"]
    cand.sort(key=lambda e: e["start_date"])
    print(f"{len(events)} STN events in total; {len(cand)} start in 2017-2025\n")

    fields_shown = False
    rows = []
    for k, e in enumerate(cand, 1):
        eid = e["id"]
        path = f"{RAW}/{eid}.json"
        if os.path.exists(path):
            hwms = json.load(open(path, encoding="utf-8"))
        else:
            try:
                hwms = get_json(a.hwm_url.replace("{id}", str(eid)))
            except Exception as ex:
                print(f"[{k}/{len(cand)}] {eid} {e['name']}: ERROR {ex!r}")
                rows.append(dict(event_id=eid, name=e["name"], error=str(ex)[:100]))
                if len(rows) == 3 and all(r.get("error") for r in rows):
                    sys.exit("The first 3 events all failed, so the high-water-mark URL is probably wrong.\n"
                             "Copy the full filteredhwms URL from the viewer's Network tab and pass it with --hwm-url.")
                continue
            json.dump(hwms, open(path, "w", encoding="utf-8"))
            time.sleep(1)
        if isinstance(hwms, dict):                      # some services wrap the list
            hwms = next((v for v in hwms.values() if isinstance(v, list)), [])

        keys = list(hwms[0].keys()) if hwms else []
        if hwms and not fields_shown:
            print("Fields in a high-water mark record:\n  " + ", ".join(keys) + "\n")
            fields_shown = True
        lat_k = pick(keys, "lat")
        lon_k = pick(keys, "lon")
        elev_k = pick(keys, "elev")

        pts = [(num(h.get(lat_k)), num(h.get(lon_k))) for h in hwms] if lat_k and lon_k else []
        pts = [(la, lo) for la, lo in pts if la is not None and lo is not None]
        l48 = [(la, lo) for la, lo in pts if 24.4 <= la <= 49.5 and -125.0 <= lo <= -66.9]
        n_surv = sum(1 for h in hwms if elev_k and num(h.get(elev_k)) is not None)

        start, end = day(e.get("start_date")), day(e.get("end_date"))
        days = (end - start).days if start and end else None
        window_note = ("no end date -> NOAA episode dates" if end is None else
                       f"longer than {MAX_DAYS} days -> NOAA episode dates" if days > MAX_DAYS else "STN dates")
        row = dict(
            event_id=eid, name=e["name"], event_type=e.get("event_type"),
            stn_start=e.get("start_date"), stn_end=e.get("end_date") or "", stn_days=days if days is not None else "",
            window_start=(start - timedelta(days=PAD_DAYS)).date() if start and window_note == "STN dates" else "",
            window_end=(end + timedelta(days=PAD_DAYS)).date() if end and window_note == "STN dates" else "",
            window_note=window_note,
            n_hwm=len(hwms), n_hwm_surveyed=n_surv, n_hwm_with_coords=len(pts), n_hwm_lower48=len(l48),
            west=round(min(lo for _, lo in pts) - PAD_DEG, 4) if pts else "",
            south=round(min(la for la, _ in pts) - PAD_DEG, 4) if pts else "",
            east=round(max(lo for _, lo in pts) + PAD_DEG, 4) if pts else "",
            north=round(max(la for la, _ in pts) + PAD_DEG, 4) if pts else "",
            dev_flood=DEV.get(eid, ""), error="")
        rows.append(row)
        print(f"[{k}/{len(cand)}] {eid:>4} {e['name'][:42]:<42} marks={len(hwms):>5}  lower48={len(l48):>5}  {window_note}")

    cols = ["event_id", "name", "event_type", "stn_start", "stn_end", "stn_days", "window_start", "window_end",
            "window_note", "n_hwm", "n_hwm_surveyed", "n_hwm_with_coords", "n_hwm_lower48",
            "west", "south", "east", "north", "dev_flood", "error"]
    with open("data/events_candidates.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    n50 = sum(1 for r in rows if isinstance(r.get("n_hwm"), int) and r["n_hwm"] >= 50)
    print(f"\n{n50} of {len(rows)} events have 50+ high-water marks (before the lower-48 and other checks)")
    print("wrote data/events_candidates.csv  (apply your rule in it; nothing has been dropped)")
    if not fields_shown:
        print("No marks were returned for any event: check the URL in a browser and paste the result.")
        sys.exit(1)


if __name__ == "__main__":
    main()