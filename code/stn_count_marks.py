"""Add mark counts and lower-48 boxes to data/events_candidates.csv.

Run from the project folder after stn_event_list.py:
    python -I code/stn_count_marks.py

Reads the raw files already saved in data/raw/stn_hwms/<event_id>.json (no downloads).
For each event it adds:
  n_surveyed_l48       marks with a measured elevation (elev_ft) in the lower 48
  n_riverine_surv_l48  the same, but only marks whose 'environment' is Riverine
  environments         count of marks by environment (e.g. Riverine 400; Coastal 50)
  states               count of marks by state
  l48_west/south/east/north
                       box drawn from LOWER-48 marks only, plus 0.25 deg each side
                       (the old west/south/east/north used every mark, e.g. Irma's reached Puerto Rico)
Lower 48 = state_name is a US state other than Alaska and Hawaii (DC counts).
Writes data/events_candidates_env.csv. Nothing is dropped.
"""
import csv, json, os
from collections import Counter

PAD = 0.25
L48 = {"alabama", "arizona", "arkansas", "california", "colorado", "connecticut", "delaware",
       "district of columbia", "florida", "georgia", "idaho", "illinois", "indiana", "iowa",
       "kansas", "kentucky", "louisiana", "maine", "maryland", "massachusetts", "michigan",
       "minnesota", "mississippi", "missouri", "montana", "nebraska", "nevada", "new hampshire",
       "new jersey", "new mexico", "new york", "north carolina", "north dakota", "ohio", "oklahoma",
       "oregon", "pennsylvania", "rhode island", "south carolina", "south dakota", "tennessee",
       "texas", "utah", "vermont", "virginia", "washington", "west virginia", "wisconsin", "wyoming"}
NOT_L48 = {"alaska", "hawaii", "puerto rico", "virgin islands", "u.s. virgin islands",
           "guam", "american samoa", "northern mariana islands"}


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def in_l48(h):
    return (h.get("state_name") or "").strip().lower() in L48


def main():
    rows = list(csv.DictReader(open("data/events_candidates.csv", encoding="utf-8-sig")))
    new_cols = ["n_surveyed_l48", "n_riverine_surv_l48", "environments", "states",
                "l48_west", "l48_south", "l48_east", "l48_north"]
    unknown = Counter()
    for r in rows:
        for c in new_cols:
            r[c] = ""
        path = f"data/raw/stn_hwms/{r['event_id']}.json"
        if not os.path.exists(path):
            continue
        hwms = json.load(open(path, encoding="utf-8"))
        if isinstance(hwms, dict):
            hwms = next((v for v in hwms.values() if isinstance(v, list)), [])
        states = Counter((h.get("state_name") or "").strip() for h in hwms)
        for s in states:
            if s and s.lower() not in L48 and s.lower() not in NOT_L48:
                unknown[s] += states[s]
        envs = Counter((h.get("environment") or "").strip() or "(blank)" for h in hwms)
        surv = [h for h in hwms if num(h.get("elev_ft")) is not None and in_l48(h)]
        r["n_surveyed_l48"] = len(surv)
        r["n_riverine_surv_l48"] = sum(1 for h in surv if (h.get("environment") or "").strip().lower() == "riverine")
        r["environments"] = "; ".join(f"{e} {n}" for e, n in envs.most_common())
        r["states"] = "; ".join(f"{s or '(blank)'} {n}" for s, n in states.most_common())
        pts = [(num(h.get("latitude_dd")), num(h.get("longitude_dd"))) for h in hwms if in_l48(h)]
        pts = [(la, lo) for la, lo in pts if la is not None and lo is not None]
        if pts:
            r["l48_west"] = round(min(lo for _, lo in pts) - PAD, 4)
            r["l48_south"] = round(min(la for la, _ in pts) - PAD, 4)
            r["l48_east"] = round(max(lo for _, lo in pts) + PAD, 4)
            r["l48_north"] = round(max(la for la, _ in pts) + PAD, 4)

    cols = list(rows[0].keys())
    with open("data/events_candidates_env.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)

    keep = [r for r in rows if isinstance(r["n_surveyed_l48"], int) and r["n_surveyed_l48"] >= 50]
    print(f"{len(keep)} of {len(rows)} events have 50+ surveyed lower-48 marks:\n")
    print(f"  {'id':>4}  {'name':<42} {'surv_l48':>8} {'riverine':>8}  environments")
    for r in keep:
        print(f"  {r['event_id']:>4}  {r['name'][:42]:<42} {r['n_surveyed_l48']:>8} "
              f"{r['n_riverine_surv_l48']:>8}  {r['environments']}")
    if unknown:
        print("\nState names not recognised (check these by hand):", dict(unknown))
    print("\nwrote data/events_candidates_env.csv")


if __name__ == "__main__":
    main()