"""Combine your decisions sheet with the high-water-mark counts and lower-48 boxes.

1. In Excel, save your decisions sheet (the one with 'decision' and 'reason' columns) as
   data/events_decisions.csv  (File > Save As > CSV UTF-8).
2. Run from the project folder:
       python -I code/stn_merge_decisions.py
   or name your file:
       python -I code/stn_merge_decisions.py --decisions data/my_sheet.csv

Keeps every column and every decision you typed, and adds (from data/raw/stn_hwms/*.json, no downloads):
  n_riverine_surv_l48    surveyed lower-48 marks whose environment is Riverine
  n_noncoastal_surv_l48  surveyed lower-48 marks whose environment is anything except Coastal
                         (Riverine, Urban, Rural, blank...)
  environments           marks by environment, e.g. "Riverine 659; Urban 17; Rural 5"
  l48_west/south/east/north  box from lower-48 marks only, plus 0.25 deg each side
Writes data/events_decisions_merged.csv. Your input file is not changed.
"""
import argparse, csv, json, os
from collections import Counter

PAD = 0.25
L48 = {"alabama", "arizona", "arkansas", "california", "colorado", "connecticut", "delaware",
       "district of columbia", "florida", "georgia", "idaho", "illinois", "indiana", "iowa",
       "kansas", "kentucky", "louisiana", "maine", "maryland", "massachusetts", "michigan",
       "minnesota", "mississippi", "missouri", "montana", "nebraska", "nevada", "new hampshire",
       "new jersey", "new mexico", "new york", "north carolina", "north dakota", "ohio", "oklahoma",
       "oregon", "pennsylvania", "rhode island", "south carolina", "south dakota", "tennessee",
       "texas", "utah", "vermont", "virginia", "washington", "west virginia", "wisconsin", "wyoming"}
NEW = ["n_riverine_surv_l48", "n_noncoastal_surv_l48", "environments",
       "l48_west", "l48_south", "l48_east", "l48_north"]


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def read_table(path):
    raw = open(path, "rb").read()
    text = raw.decode("utf-16") if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else raw.decode("utf-8-sig", errors="replace")
    first = text.splitlines()[0] if text else ""
    delim = "\t" if first.count("\t") > first.count(",") else ","
    return list(csv.DictReader(text.splitlines(), delimiter=delim))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--decisions", default="data/events_decisions.csv")
    a = ap.parse_args()
    if not os.path.exists(a.decisions):
        raise SystemExit(f"{a.decisions} not found. Save your decisions sheet there as CSV first.")
    rows = read_table(a.decisions)
    if not rows or "event_id" not in rows[0]:
        raise SystemExit("Couldn't find an 'event_id' column; check the file has the header row.")
    missing = []
    for r in rows:
        for c in NEW:
            r[c] = ""
        eid = (r.get("event_id") or "").strip()
        path = f"data/raw/stn_hwms/{eid}.json"
        if not eid or not os.path.exists(path):
            missing.append(eid)
            continue
        hwms = json.load(open(path, encoding="utf-8"))
        if isinstance(hwms, dict):
            hwms = next((v for v in hwms.values() if isinstance(v, list)), [])
        l48 = [h for h in hwms if (h.get("state_name") or "").strip().lower() in L48]
        surv = [h for h in l48 if num(h.get("elev_ft")) is not None]
        env = lambda h: (h.get("environment") or "").strip().lower()
        r["n_riverine_surv_l48"] = sum(1 for h in surv if env(h) == "riverine")
        r["n_noncoastal_surv_l48"] = sum(1 for h in surv if env(h) != "coastal")
        r["environments"] = "; ".join(f"{e or '(blank)'} {n}" for e, n in
                                      Counter((h.get("environment") or "").strip() for h in hwms).most_common())
        pts = [(num(h.get("latitude_dd")), num(h.get("longitude_dd"))) for h in l48]
        pts = [(la, lo) for la, lo in pts if la is not None and lo is not None]
        if pts:
            r["l48_west"] = round(min(lo for _, lo in pts) - PAD, 4)
            r["l48_south"] = round(min(la for la, _ in pts) - PAD, 4)
            r["l48_east"] = round(max(lo for _, lo in pts) + PAD, 4)
            r["l48_north"] = round(max(la for la, _ in pts) + PAD, 4)
    cols = list(rows[0].keys())
    with open("data/events_decisions_merged.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    dec_col = next((c for c in cols if c.lower().startswith("decision")), None)
    if dec_col:
        print("Decisions so far:", dict(Counter((r[dec_col] or "(blank)").strip() for r in rows)))
    if missing:
        print("No raw file for event_id(s):", ", ".join(m or "(blank)" for m in missing))
    print(f"{len(rows)} rows written to data/events_decisions_merged.csv")


if __name__ == "__main__":
    main()