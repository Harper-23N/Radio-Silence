"""Kill test, part 1: draw a random hand-check sample and plot every gauge in it.

Run from the project folder (the one containing code/ and data/):
    python -I code/run_hand_plots.py            # draw sample, download, plot
    python -I code/run_hand_plots.py --dry-run  # only draw and print the sample

What it does
1. Takes every big-rise gauge (rise >= 20 ft) in data/stations_7floods_v3.csv: 32 called dark by the
   rule (v1rule_dark = 1) and 84 called healthy.
2. Draws 10 dark + 10 healthy AT RANDOM with a fixed seed, spread across floods (quotas below), so
   nobody (myself included) chose which gauges get checked. Same seed -> same sample every time.
3. Writes the sample to data/hand_sample.csv (with the rule's call) and a blank
   data/hand_labels.csv (no rule call, so you label blind).
4. Downloads archive + live feed once into data/hand/ and plots each to figs/hand/hNN.png.
   File names and titles show only a number, not the site or the rule's call.
Yellowstone has no gauge that rose 20 ft or more, so it cannot be in this sample.
"""
import argparse, csv, os, subprocess, sys, json
from datetime import datetime, timedelta
import pandas as pd

SEED = 2026
QUOTA = {  # how many to draw per flood; at least 1 from every flood that has any
    1: {"harvey": 3, "helene": 3, "kentucky": 1, "texas": 2, "vermont": 1},   # rule says dark (32)
    0: {"harvey": 4, "helene": 2, "kentucky": 1, "texas": 2, "waverly": 1},   # rule says healthy (84)
}
EVENTS = {  # window start UTC, window end UTC, x-axis time zone (dates from guide Part 3)
    "harvey":   ("2017-08-25T00:00Z", "2017-09-02T06:00Z", "America/Chicago"),
    "helene":   ("2024-09-25T00:00Z", "2024-10-01T06:00Z", "America/New_York"),
    "kentucky": ("2022-07-26T00:00Z", "2022-08-01T06:00Z", "America/New_York"),
    "texas":    ("2025-07-03T00:00Z", "2025-07-08T06:00Z", "America/Chicago"),
    "vermont":  ("2023-07-09T00:00Z", "2023-07-15T06:00Z", "America/New_York"),
    "waverly":  ("2021-08-20T00:00Z", "2021-08-25T06:00Z", "America/Chicago"),
}
PAD_H = 12  # hours shown either side of a gap
PY = [sys.executable, "-I"]


def draw():
    d = pd.read_csv("data/stations_7floods_v3.csv", dtype={"site": str})
    big = d[d.rise_ft >= 20]
    parts = []
    for call, quota in QUOTA.items():
        for ev, n in quota.items():
            pool = big[(big.v1rule_dark == call) & (big.event == ev)].sort_values("site")
            parts.append(pool.sample(n=n, random_state=SEED))
    s = pd.concat(parts).sample(frac=1, random_state=SEED).reset_index(drop=True)  # shuffle order
    s.insert(0, "hand_id", [f"h{i:02d}" for i in range(1, len(s) + 1)])
    nwsli = json.load(open("data/usgs_to_nwsli_map.json"))
    s.insert(3, "nwsli", s.site.map(nwsli))
    return s


def fetch(kind, sid, a, b, path):
    if os.path.exists(path) and os.path.getsize(path) > 40:
        return
    if kind == "usgs":
        a, b = a.replace("Z", ":00Z"), b.replace("Z", ":00Z")
    with open(path, "w", encoding="utf-8", newline="") as f:   # direct write: no PowerShell UTF-16
        subprocess.run(PY + ["code/gd_fetch.py", kind, sid, a, b], stdout=f, check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    s = draw()
    print(s[["hand_id", "event", "site", "nwsli"]].to_string(index=False))   # no rule call: stay blind
    if a.dry_run:
        return
    s.to_csv("data/hand_sample.csv", index=False)
    if not os.path.exists("data/hand_labels.csv"):                  # never overwrite your labels
        with open("data/hand_labels.csv", "w", newline="") as f:
            w = csv.writer(f); w.writerow(["hand_id", "label", "reason"])
            w.writerows([[h, "", ""] for h in sorted(s.hand_id)])
    os.makedirs("data/hand", exist_ok=True)
    for r in s.itertuples():
        start, end, tz = EVENTS[r.event]
        arch, live = f"data/hand/{r.site}_usgs.csv", f"data/hand/{r.nwsli}_iem.csv"
        fetch("usgs", r.site, start, end, arch)
        fetch("iem", r.nwsli, start, end, live)
        if isinstance(r.gap_start_utc, str):                       # zoom on the gap if there is one
            g = datetime.strptime(r.gap_start_utc, "%Y-%m-%d %H:%M")
            start = (g - timedelta(hours=PAD_H)).strftime("%Y-%m-%dT%H:%MZ")
            end = (g + timedelta(hours=r.gap_h + PAD_H)).strftime("%Y-%m-%dT%H:%MZ")
        subprocess.run(PY + ["code/plot_gauge.py", "--archive", arch, "--live", live,
                             "--title", f"Gauge {r.hand_id}", "--start", start, "--end", end,
                             "--tz", tz, "--out", f"figs/hand/{r.hand_id}.png"], check=True)


if __name__ == "__main__":
    main()