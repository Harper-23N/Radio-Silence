"""NOAA Storm Events: windows for kept STN events, and the Part B deadly-flood list.

Run from the project folder:
    python -I code/noaa_episodes.py
    python -I code/noaa_episodes.py --decisions data/events_decisions_merged.csv

Downloads NOAA's yearly 'details' files for 2017-2025 (about 10-15 MB each) from
https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/ into data/raw/noaa/ (reused on re-runs).
Uses only Flood and Flash Flood records in the lower 48. Dates are the local dates NOAA reports.

Job 1, windows (pre-registered rule as logged in CHANGELOG):
  for each row whose decision is keep (dev floods keep their pilot windows) and whose window_note says 'NOAA episode dates',
  take all Flood/Flash Flood records that lie inside the row's lower-48 box (l48_*) and begin between
  the STN start date and the STN end date (or STN start + 30 days if there is no end date).
  NOAA window = earliest begin - 1 day to latest end + 1 day.  -> data/noaa_windows.csv
Job 2, Part B:
  one flood = one NOAA episode; deaths = DEATHS_DIRECT summed over its Flood/Flash Flood records;
  keep episodes with 10 or more. Box = record begin/end coordinates + 0.25 deg; window = earliest
  begin - 1 day to latest end + 1 day.  -> data/noaa_partB_episodes.csv
Nothing is dropped or merged automatically: you decide in your sheet.
"""
import argparse, csv, gzip, io, os, re, sys, urllib.request
from collections import defaultdict
from datetime import date, datetime, timedelta

URL = "https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/"
RAW = "data/raw/noaa"
YEARS = range(2017, 2026)
TYPES = {"flood", "flash flood"}
PAD_DEG, PAD_DAYS, NO_END_DAYS, MIN_DEATHS = 0.25, 1, 30, 10
L48 = {"ALABAMA", "ARIZONA", "ARKANSAS", "CALIFORNIA", "COLORADO", "CONNECTICUT", "DELAWARE",
       "DISTRICT OF COLUMBIA", "FLORIDA", "GEORGIA", "IDAHO", "ILLINOIS", "INDIANA", "IOWA", "KANSAS",
       "KENTUCKY", "LOUISIANA", "MAINE", "MARYLAND", "MASSACHUSETTS", "MICHIGAN", "MINNESOTA",
       "MISSISSIPPI", "MISSOURI", "MONTANA", "NEBRASKA", "NEVADA", "NEW HAMPSHIRE", "NEW JERSEY",
       "NEW MEXICO", "NEW YORK", "NORTH CAROLINA", "NORTH DAKOTA", "OHIO", "OKLAHOMA", "OREGON",
       "PENNSYLVANIA", "RHODE ISLAND", "SOUTH CAROLINA", "SOUTH DAKOTA", "TENNESSEE", "TEXAS", "UTAH",
       "VERMONT", "VIRGINIA", "WASHINGTON", "WEST VIRGINIA", "WISCONSIN", "WYOMING"}


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "RadioSilence student project"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return r.read()


def year_files():
    os.makedirs(RAW, exist_ok=True)
    have = {y: f for f in os.listdir(RAW) for y in YEARS if f.startswith(f"StormEvents_details-ftp_v1.0_d{y}_")}
    if len(have) < len(YEARS):
        index = fetch(URL).decode("utf-8", "replace")
        for y in YEARS:
            if y in have:
                continue
            names = sorted(set(re.findall(rf"StormEvents_details-ftp_v1\.0_d{y}_c\d+\.csv\.gz", index)))
            if not names:
                sys.exit(f"No details file for {y} in the NOAA index; check {URL}")
            print(f"downloading {names[-1]} ...", flush=True)
            open(f"{RAW}/{names[-1]}", "wb").write(fetch(URL + names[-1]))
            have[y] = names[-1]
    return [f"{RAW}/{have[y]}" for y in YEARS]


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def rec_dates(r):
    b = date(int(r["BEGIN_YEARMONTH"]) // 100, int(r["BEGIN_YEARMONTH"]) % 100, int(r["BEGIN_DAY"]))
    e = date(int(r["END_YEARMONTH"]) // 100, int(r["END_YEARMONTH"]) % 100, int(r["END_DAY"]))
    return b, e


def load_records():
    recs = []
    for path in year_files():
        with gzip.open(path, "rt", encoding="latin-1", newline="") as f:
            for r in csv.DictReader(f):
                if r["EVENT_TYPE"].strip().lower() not in TYPES or r["STATE"].strip().upper() not in L48:
                    continue
                try:
                    b, e = rec_dates(r)
                except (ValueError, KeyError):
                    continue
                pts = [(num(r.get("BEGIN_LAT")), num(r.get("BEGIN_LON"))), (num(r.get("END_LAT")), num(r.get("END_LON")))]
                pts = [(la, lo) for la, lo in pts if la is not None and lo is not None and la != 0]
                recs.append(dict(episode=r["EPISODE_ID"], state=r["STATE"].title(), type=r["EVENT_TYPE"],
                                 begin=b, end=e, pts=pts, county=r.get("CZ_NAME", "").title(),
                                 deaths=int(num(r.get("DEATHS_DIRECT")) or 0)))
    print(f"{len(recs)} Flood / Flash Flood records in the lower 48, 2017-2025\n")
    return recs


def read_table(path):
    raw = open(path, "rb").read()
    text = raw.decode("utf-16") if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else raw.decode("utf-8-sig", "replace")
    first = text.splitlines()[0]
    return list(csv.DictReader(text.splitlines(), delimiter="\t" if first.count("\t") > first.count(",") else ","))


def d(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00")).date() if s else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--decisions", default="data/events_decisions_merged.csv")
    a = ap.parse_args()
    recs = load_records()

    # Job 1: windows for kept/dev events that need NOAA dates
    rows = read_table(a.decisions)
    dec = next(c for c in rows[0] if c.lower().startswith("decision"))
    out1 = []
    for r in rows:
        if r[dec].strip().lower() != "keep" or "NOAA" not in r.get("window_note", ""):
            continue
        try:
            w, s, e, n = (float(r[k]) for k in ("l48_west", "l48_south", "l48_east", "l48_north"))
        except ValueError:
            out1.append(dict(event_id=r["event_id"], name=r["name"], note="no lower-48 box"))
            continue
        start = d(r["stn_start"])
        stop = d(r["stn_end"]) or start + timedelta(days=NO_END_DAYS)
        m = [x for x in recs if start <= x["begin"] <= stop
             and any(w <= lo <= e and s <= la <= n for la, lo in x["pts"])]
        if not m:
            out1.append(dict(event_id=r["event_id"], name=r["name"], stn_start=start, stn_end_used=stop,
                             n_records=0, note="no matching NOAA flood records -> drop under the rule"))
            continue
        b, en = min(x["begin"] for x in m), max(x["end"] for x in m)
        out1.append(dict(event_id=r["event_id"], name=r["name"], stn_start=start, stn_end_used=stop,
                         n_records=len(m), n_episodes=len({x["episode"] for x in m}),
                         noaa_first_begin=b, noaa_last_end=en, span_days=(en - b).days,
                         window_start=b - timedelta(days=PAD_DAYS), window_end=en + timedelta(days=PAD_DAYS),
                         states=", ".join(sorted({x["state"] for x in m})), note=""))
    c1 = ["event_id", "name", "stn_start", "stn_end_used", "n_records", "n_episodes", "noaa_first_begin",
          "noaa_last_end", "span_days", "window_start", "window_end", "states", "note"]
    with open("data/noaa_windows.csv", "w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=c1); wr.writeheader(); wr.writerows(out1)
    print("Job 1: NOAA windows for kept events")
    for o in out1:
        print(f"  {o['event_id']:>4} {o['name'][:40]:<40} records={o.get('n_records', ''):>5} "
              f"{o.get('window_start', '')} to {o.get('window_end', '')} ({o.get('span_days', '')} d) {o.get('note', '')}")

    # Job 2: Part B, episodes with 10+ direct flood deaths
    ep = defaultdict(list)
    for x in recs:
        ep[x["episode"]].append(x)
    out2 = []
    for eid, xs in ep.items():
        deaths = sum(x["deaths"] for x in xs)
        if deaths < MIN_DEATHS:
            continue
        pts = [p for x in xs for p in x["pts"]]
        b, en = min(x["begin"] for x in xs), max(x["end"] for x in xs)
        out2.append(dict(episode_id=eid, deaths_direct=deaths, n_records=len(xs),
                         states=", ".join(sorted({x["state"] for x in xs})),
                         counties=", ".join(sorted({x["county"] for x in xs}))[:200],
                         first_begin=b, last_end=en,
                         window_start=b - timedelta(days=PAD_DAYS), window_end=en + timedelta(days=PAD_DAYS),
                         n_records_without_coords=sum(1 for x in xs if not x["pts"]),
                         west=round(min(lo for _, lo in pts) - PAD_DEG, 4) if pts else "",
                         south=round(min(la for la, _ in pts) - PAD_DEG, 4) if pts else "",
                         east=round(max(lo for _, lo in pts) + PAD_DEG, 4) if pts else "",
                         north=round(max(la for la, _ in pts) + PAD_DEG, 4) if pts else ""))
    out2.sort(key=lambda o: o["first_begin"])
    c2 = list(out2[0].keys()) if out2 else ["episode_id"]
    with open("data/noaa_partB_episodes.csv", "w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=c2); wr.writeheader(); wr.writerows(out2)
    print(f"\nJob 2: {len(out2)} episodes with {MIN_DEATHS}+ direct flood deaths")
    for o in out2:
        print(f"  episode {o['episode_id']:>7}  {o['first_begin']} to {o['last_end']}  deaths={o['deaths_direct']:>3}  {o['states']}")
    print("\nwrote data/noaa_windows.csv and data/noaa_partB_episodes.csv")


if __name__ == "__main__":
    main()