"""Validation of gap rule v2: draw 10 NEW gauges, plot them for blind hand-labelling.

Run from the project folder, after run_census (v1/v2) has written data/census_v1_v2.csv:
    python -I code/run_hand_plots2.py            # draw, download live feeds, plot
    python -I code/run_hand_plots2.py --dry-run  # only show which plots will be made (no rule calls)

Sample (seed 2027, big-rise gauges only, the 20 gauges in data/hand_sample.csv excluded):
    5 at random from gauges v2 NEWLY calls dark (v1 healthy -> v2 dark): tests the new rules
    5 at random from gauges v2 calls healthy: tests what v2 still misses
Outputs
    figs/hand2/v01.png ... v10.png   plots, shuffled, titled with the number only
    data/hand2_labels.csv            blank sheet to fill in (never overwritten)
    data/hand2_gaps.txt              every gap >= 60 min in each plot's archive and live feed (your gap check)
    data/hand2_sample.csv            ANSWER KEY with v1/v2 calls: do not open until all 10 are labelled
Blinding: unlike round 1, every plot shows the WHOLE flood window (no zoom on the rule's gap), so the
plot itself does not hint at the rule's call. The y-axis is fitted to the archive so high-datum gauges
are not squashed; off-chart live readings are marked on the edge. Lines break at gaps >= 60 min.
"""
import argparse, csv, json, os, subprocess, sys
import pandas as pd

SEED, N_NEW, N_HEALTHY = 2027, 5, 5
PY = [sys.executable, "-I"]
EVENTS = {  # window start UTC, window end UTC, x-axis time zone (same as round 1 and the census)
    "harvey":   ("2017-08-25T00:00Z", "2017-09-02T06:00Z", "America/Chicago"),
    "helene":   ("2024-09-25T00:00Z", "2024-10-01T06:00Z", "America/New_York"),
    "kentucky": ("2022-07-26T00:00Z", "2022-08-01T06:00Z", "America/New_York"),
    "texas":    ("2025-07-03T00:00Z", "2025-07-08T06:00Z", "America/Chicago"),
    "vermont":  ("2023-07-09T00:00Z", "2023-07-15T06:00Z", "America/New_York"),
    "waverly":  ("2021-08-20T00:00Z", "2021-08-25T06:00Z", "America/Chicago"),
}


def draw():
    c = pd.read_csv("data/census_v1_v2.csv", dtype={"site": str})
    tab = pd.read_csv("data/stations_7floods_v3.csv", dtype={"site": str})[["event", "site", "rise_ft"]]
    c = c.merge(tab.rename(columns={"rise_ft": "table_rise_ft"}), on=["event", "site"])
    c = c[(c.table_rise_ft >= 20) & (c.error.fillna("") == "")]
    done = set(pd.read_csv("data/hand_sample.csv", dtype={"site": str}).site)
    c = c[~c.site.isin(done)]
    new = c[(c.v1_dark == 0) & (c.v2_dark == 1)].sort_values("site")
    healthy = c[c.v2_dark == 0].sort_values("site")
    if len(new) < N_NEW:
        sys.exit(f"only {len(new)} unlabelled v1->v2 gauges; lower N_NEW")
    s = pd.concat([new.sample(N_NEW, random_state=SEED).assign(pool="v2_new_dark"),
                   healthy.sample(N_HEALTHY, random_state=SEED).assign(pool="v2_healthy")])
    s = s.sample(frac=1, random_state=SEED).reset_index(drop=True)
    s.insert(0, "hand_id", [f"v{i:02d}" for i in range(1, len(s) + 1)])
    s.insert(3, "nwsli", s.site.map(json.load(open("data/usgs_to_nwsli_map.json"))))
    return s


def series(path):
    d = pd.read_csv(path)
    t = pd.to_datetime(d["time_utc"], utc=True, format="ISO8601")
    v = pd.to_numeric(d["value_ft"], errors="coerce")
    return pd.Series(v.values, index=t).dropna().sort_index()


def gaps(s, label, f):
    dt = s.index.to_series().diff()
    for t, g in dt[dt >= pd.Timedelta(minutes=60)].items():
        f.write(f"  {label}: {t - g:%Y-%m-%d %H:%M} -> {t:%Y-%m-%d %H:%M} UTC  ({g.total_seconds() / 60:.0f} min)\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    s = draw()
    print(s[["hand_id", "event", "site", "nwsli"]].to_string(index=False))   # no rule calls: stay blind
    if a.dry_run:
        return
    s.to_csv("data/hand2_sample.csv", index=False)
    if not os.path.exists("data/hand2_labels.csv"):
        with open("data/hand2_labels.csv", "w", newline="") as f:
            w = csv.writer(f); w.writerow(["hand_id", "label", "borderline", "reason"])
            w.writerows([[h, "", "", ""] for h in sorted(s.hand_id)])
    os.makedirs("data/hand", exist_ok=True)
    with open("data/hand2_gaps.txt", "w") as gf:
        for r in s.sort_values("hand_id").itertuples():
            start, end, tz = EVENTS[r.event]
            arch = f"data/raw/{r.event}/{r.site}.csv"                     # downloaded by run_census
            live = f"data/hand/{r.nwsli}_iem.csv" if isinstance(r.nwsli, str) else None
            if live and not (os.path.exists(live) and os.path.getsize(live) > 40):
                with open(live, "w", encoding="utf-8", newline="") as f:
                    subprocess.run(PY + ["code/gd_fetch.py", "iem", r.nwsli, start, end], stdout=f, check=True)
            A = series(arch)
            A = A[(A.index >= pd.Timestamp(start)) & (A.index <= pd.Timestamp(end))]
            lo, hi = A.min(), A.max()
            pad = max(1.0, 0.1 * (hi - lo))
            gf.write(f"{r.hand_id}\n")
            gaps(A, "archive", gf)
            if live and os.path.getsize(live) > 40:
                L = series(live)
                gaps(L[(L.index >= pd.Timestamp(start)) & (L.index <= pd.Timestamp(end))], "live   ", gf)
            else:
                gf.write("  live   : NO LIVE-FEED DATA\n")
            cmd = PY + ["code/plot_gauge.py", "--archive", arch, "--title", f"Gauge {r.hand_id}",
                        "--start", start, "--end", end, "--tz", tz, "--gap-min", "59",
                        "--ymin", f"{max(0, lo - pad):.1f}", "--ymax", f"{hi + pad:.1f}",
                        "--out", f"figs/hand2/{r.hand_id}.png"]
            if live and os.path.getsize(live) > 40:
                cmd += ["--live", live]
            subprocess.run(cmd, check=True)
    print("\nPlots in figs/hand2/, gap list in data/hand2_gaps.txt, labels go in data/hand2_labels.csv")


if __name__ == "__main__":
    main()