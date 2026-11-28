"""Census: run gap rule v1 and v2 on every gauge in data/stations_7floods_v3.csv (Hour 8 + v2 check).

Run from the project folder (the one containing code/ and data/):
    python -I code/run_census.py                 # big-rise gauges only (rise >= 20 ft): the 116
    python -I code/run_census.py --min-rise 0    # all 387 gauges
Downloads each gauge's USGS archive once into data/raw/<event>/<site>.csv (re-runs skip existing files),
then writes data/census_v1_v2.csv and prints:
  - X/N dark under v1 vs Y/N under v2
  - every gauge where v1 and v2 disagree, with the v2 rule that caused it (in_rise / open_end)
  - agreement of your re-run v1 with the pilot table's dark1h column (the Hour 8 reproduction check)

NOTE on qualifier codes: the new USGS API returns approval_status "Approved"/"Provisional" and qualifiers
such as ESTIMATED. gd_fetch.py joins them into one string, and "Approved" contains a lowercase 'e', which
rule 1 (drop codes containing 'e') would read as "estimated" and throw away every approved reading.
This script converts codes back to the pilot's style first: "A"/"P", plus " e" only when a qualifier says
ESTIMATED (or a legacy code already had 'e'). Write this in your logbook.
"""
import argparse, csv, os, sys
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gd_fetch import usgs_continuous
from gd_gaps import analyze

EVENTS = {  # window start/end UTC; same windows as run_hand_plots.py (dates from guide Part 3)
    "harvey":      ("2017-08-25T00:00:00Z", "2017-09-02T06:00:00Z"),
    "helene":      ("2024-09-25T00:00:00Z", "2024-10-01T06:00:00Z"),
    "kentucky":    ("2022-07-26T00:00:00Z", "2022-08-01T06:00:00Z"),
    "texas":       ("2025-07-03T00:00:00Z", "2025-07-08T06:00:00Z"),
    "vermont":     ("2023-07-09T00:00:00Z", "2023-07-15T06:00:00Z"),
    "waverly":     ("2021-08-20T00:00:00Z", "2021-08-25T06:00:00Z"),
    "yellowstone": ("2022-06-11T00:00:00Z", "2022-06-17T06:00:00Z"),
}


def pilot_code(code: str) -> str:
    """'Approved|ESTIMATED' -> 'A e', 'Provisional' -> 'P', legacy 'A e' -> 'A e'."""
    status, _, quals = (code or "").partition("|")
    s = status.strip()
    if s.lower().startswith("approved"):
        base = "A"
    elif s.lower().startswith("provisional"):
        base = "P"
    else:
        return s                       # legacy WaterServices code ('A', 'P', 'A e'): already pilot style
    return base + (" e" if "ESTIMATED" in quals.replace("+", "").upper() else "")


def load(event, site):
    path = f"data/raw/{event}/{site}.csv"
    if not (os.path.exists(path) and os.path.getsize(path) > 30):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        rows = usgs_continuous(site, *EVENTS[event])
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f); w.writerow(["time_utc", "value_ft", "code"]); w.writerows(rows)
    d = pd.read_csv(path, dtype={"code": str}, keep_default_na=False)
    t = pd.to_datetime(d["time_utc"], utc=True, format="ISO8601")   # some times carry microseconds
    v = pd.to_numeric(d["value_ft"], errors="coerce")
    ms = (t - pd.Timestamp("1970-01-01", tz="UTC")) // pd.Timedelta(milliseconds=1)
    return [(int(a), None if pd.isna(b) else float(b), pilot_code(c)) for a, b, c in zip(ms, v, d["code"])]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-rise", type=float, default=20, help="pilot-table rise_ft cutoff (default 20)")
    a = ap.parse_args()
    tab = pd.read_csv("data/stations_7floods_v3.csv", dtype={"site": str})
    tab = tab[tab.rise_ft >= a.min_rise]
    out = []
    for k, r in enumerate(tab.itertuples(), 1):
        print(f"[{k}/{len(tab)}] {r.event} {r.site}", flush=True)
        try:
            recs = load(r.event, r.site)
        except Exception as e:                                         # keep going; report at the end
            out.append(dict(event=r.event, site=r.site, error=str(e)[:120])); continue
        end_ms = int(pd.Timestamp(EVENTS[r.event][1]).value // 1_000_000)
        r1, r2 = analyze(recs), analyze(recs, version=2, window_end_ms=end_ms)
        if r1 is None:
            out.append(dict(event=r.event, site=r.site, error="fewer than 10 readings")); continue
        v1_spans = {(g.start, g.end) for g in r1.dark_gaps}
        new = [g for g in r2.dark_gaps if (g.start, g.end) not in v1_spans]
        why = sorted({"open_end" if g.open_end else "in_rise" for g in new})
        out.append(dict(event=r.event, site=r.site, rise_ft=r2.rise_ft, max_ft=r2.max_ft, n=r2.n,
                        v1_dark=int(r1.dark1), v2_dark=int(r2.dark1),
                        v1_dark3h=int(r1.dark3), v2_dark3h=int(r2.dark3),
                        v2_new_gaps="+".join(why), table_dark1h=int(r.dark1h), error=""))
    res = pd.DataFrame(out)
    for c in ("v1_dark", "v2_dark", "v1_dark3h", "v2_dark3h", "table_dark1h", "n"):
        if c in res:
            res[c] = res[c].astype("Int64")                            # blanks stay blank, not 1.0/0.0
    res.to_csv("data/census_v1_v2.csv", index=False)

    ok = res[res.error.fillna("") == ""]
    bad = res[res.error.fillna("") != ""]
    n = len(ok)
    print(f"\nGauges analysed: {n} of {len(res)} (rise >= {a.min_rise} ft in the pilot table)")
    print(f"Dark (gap >= 60 min) under v1: {int(ok.v1_dark.sum())}/{n}   under v2: {int(ok.v2_dark.sum())}/{n}")
    print(f"Dark for >= 3 h under v1: {int(ok.v1_dark3h.sum())}/{n}   under v2: {int(ok.v2_dark3h.sum())}/{n}")
    agree = (ok.v1_dark == ok.table_dark1h).mean() * 100 if n else 0
    print(f"Your v1 vs pilot table dark1h: {agree:.1f}% agree (target >= 95%)")
    diff = ok[ok.v1_dark != ok.v2_dark]
    print(f"\nv1 and v2 disagree on {len(diff)} gauge(s):")
    if len(diff):
        print(diff[["event", "site", "rise_ft", "v1_dark", "v2_dark", "v2_new_gaps"]].to_string(index=False))
    if len(bad):
        print(f"\n{len(bad)} gauge(s) not analysed (see the error column):")
        print(bad[["event", "site", "error"]].to_string(index=False))
    print("\nwrote data/census_v1_v2.csv")


if __name__ == "__main__":
    main()