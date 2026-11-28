"""Plot archive vs live feed for the first N rows of data/live_feed_dark_gauges_classified.csv.

For each row this script:
  1. looks up the gap (gap_start_utc, gap_h) for that site+event in data/stations_7floods_v3.csv,
  2. downloads the USGS archive and the Iowa State live-feed copy for gap +/- --pad-h hours
     (with gd_fetch.py; files are cached in data/dark_rows/ so re-runs don't hit the APIs again),
  3. calls plot_gauge.py to draw it, shading the gap, and saves figs/dark_rows/<row>_<site>_<event>.png.

Run from the RadioSilence folder:
    python -I code/plot_dark_rows.py                 # first 18 rows
    python -I code/plot_dark_rows.py --rows 19-36    # rows 19 to 36 (row numbers count data rows, header excluded)
    python -I code/plot_dark_rows.py --refresh       # re-download instead of using the cache
    python -I code/plot_dark_rows.py --blind         # titles show "Row 5" only, so the AI label can't anchor you
    python -I code/plot_dark_rows.py --outages       # the 7 live-only outages (data/live_feed_only_outages.csv):
        # the LIVE feed went silent but the archive was filled in later; the live gap is shaded,
        # files are figs/dark_rows/out1_<site>_<event>.png ... out7_..., summary index_outages.csv
    python -I code/plot_dark_rows.py --recount data/my_live_labels.csv
        # no plotting: count your classes, compare with live_class, list every disagreement.
        # The file needs columns site, event, my_class (e.g. downloaded from Google Sheets as CSV;
        # extra columns are ignored). Blank my_class cells are reported, not counted.

Rows with no NWS ID (e.g. 0216239615) or no IEM data are still plotted, archive only.
Needs USGS_API_KEY in the environment (see gd_fetch.py).
"""
from __future__ import annotations
import argparse, csv, json, sys
from pathlib import Path

import pandas as pd

CODE = Path(__file__).resolve().parent
sys.path.insert(0, str(CODE))          # python -I leaves the script's folder off sys.path
import gd_fetch, plot_gauge            # noqa: E402

ROOT = CODE.parent
TZ = {"harvey": "America/Chicago", "texas": "America/Chicago", "waverly": "America/Chicago",   # same as round 2
      "helene": "America/New_York", "kentucky": "America/New_York", "vermont": "America/New_York",
      "yellowstone": "America/Denver"}


def iso(t: pd.Timestamp, usgs: bool) -> str:
    return t.strftime("%Y-%m-%dT%H:%M:%SZ" if usgs else "%Y-%m-%dT%H:%MZ")


def fetch(path: Path, header: list[str], rows_fn, refresh: bool) -> int:
    """Write a gd_fetch-style CSV (UTF-8) unless it is already cached. Returns the number of readings."""
    if path.exists() and not refresh:
        return sum(1 for _ in open(path, encoding="utf-8-sig")) - 1
    rows = rows_fn()
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    return len(rows)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--rows", default="18", help="N for the first N rows, or A-B for rows A to B (default 18)")
    p.add_argument("--pad-h", type=float, default=12, help="hours shown before and after the gap (default 12)")
    p.add_argument("--refresh", action="store_true", help="re-download even if cached")
    p.add_argument("--blind", action="store_true", help="title plots with the row number only (hides the AI label)")
    p.add_argument("--recount", metavar="LABELS_CSV", help="count your my_class labels against live_class; no plots")
    p.add_argument("--outages", action="store_true",
                   help="plot the 7 gauges in data/live_feed_only_outages.csv (live gap shaded) instead of the 36 rows")
    a = p.parse_args(argv)

    if a.outages:
        return outages(a)
    allrows = pd.read_csv(ROOT / "data/live_feed_dark_gauges_classified.csv", dtype={"site": str})
    if a.recount:
        return recount(allrows, a.recount)
    lo, _, hi = a.rows.partition("-")
    first, last = (int(lo), int(hi)) if hi else (1, int(lo))
    if not 1 <= first <= last <= len(allrows):
        p.error(f"--rows must be within 1-{len(allrows)}")
    cls = allrows.iloc[first - 1:last]
    st = pd.read_csv(ROOT / "data/stations_7floods_v3.csv", dtype={"site": str})
    nwsli = json.loads((ROOT / "data/usgs_to_nwsli_map.json").read_text())
    rows = cls.merge(st[["event", "site", "gap_start_utc", "gap_h"]], on=["event", "site"], how="left")

    cache, figs = ROOT / "data/dark_rows", ROOT / "figs/dark_rows"
    cache.mkdir(parents=True, exist_ok=True)
    figs.mkdir(parents=True, exist_ok=True)
    log = []

    for i, r in enumerate(rows.itertuples(index=False), start=first):   # i = row number in the full table
        print(f"\n[row {i}, {i - first + 1}/{len(rows)}] {r.site} {r.event} ({r.live_class})")
        if pd.isna(r.gap_start_utc):
            print("  skipped: no gap in stations_7floods_v3.csv")
            log.append(dict(row=i, site=r.site, event=r.event, status="no gap"))
            continue
        nws = nwsli.get(r.site)
        title = f"Row {i}" if a.blind else f"{r.site}{f' ({nws})' if nws else ''}, {r.event}: {r.live_class}, gap {float(r.gap_h):g} h"
        log.append(dict(row=i, live_class=r.live_class,
                        **plot_one(f"{i:02d}_{r.site}_{r.event}", r.site, r.event, nws, r.gap_start_utc, r.gap_h,
                                   title, "archive gap", a, cache, figs)))

    pd.DataFrame(log).to_csv(figs / f"index_rows{first}-{last}.csv", index=False)
    ok = sum(1 for x in log if x["status"] == "ok")
    print(f"\n{ok}/{len(rows)} plots written to {figs.relative_to(ROOT)}  (summary: index_rows{first}-{last}.csv)")


def outages(a):
    """The 7 gauges in data/live_feed_only_outages.csv: the LIVE feed went silent, the archive was filled in later."""
    o = pd.read_csv(ROOT / "data/live_feed_only_outages.csv", dtype={"site": str})
    cache, figs = ROOT / "data/dark_rows", ROOT / "figs/dark_rows"
    cache.mkdir(parents=True, exist_ok=True)
    figs.mkdir(parents=True, exist_ok=True)
    log = []
    for k, r in enumerate(o.itertuples(index=False), start=1):
        print(f"\n[outage {k}/{len(o)}] {r.site} ({r.nwsli}) {r.event}, live gap {r.live_gap_h:g} h")
        title = f"Outage {k}" if a.blind else f"{r.site} ({r.nwsli}), {r.event}: live gap {r.live_gap_h:g} h"
        log.append(dict(outage=k, **plot_one(f"out{k}_{r.site}_{r.event}", r.site, r.event, r.nwsli,
                                              r.live_gap_start_utc, r.live_gap_h, title, "live-feed gap",
                                              a, cache, figs)))
    pd.DataFrame(log).to_csv(figs / "index_outages.csv", index=False)
    ok = sum(1 for x in log if x["status"] == "ok")
    print(f"\n{ok}/{len(o)} plots written to {figs.relative_to(ROOT)}  (summary: index_outages.csv)")


def plot_one(tag, site, event, nws, gap_start_utc, gap_h, title, shade_label, a, cache, figs) -> dict:
    """Download (or reuse) archive + live for gap +/- pad, plot with the gap shaded. Returns a log entry."""
    g0 = pd.Timestamp(gap_start_utc, tz="UTC")
    g1 = g0 + pd.Timedelta(hours=float(gap_h))
    t0, t1 = g0 - pd.Timedelta(hours=a.pad_h), g1 + pd.Timedelta(hours=a.pad_h)
    base = dict(site=site, event=event, nwsli=nws or "", gap_start_utc=g0.strftime("%Y-%m-%d %H:%M"), gap_h=gap_h)

    arch = cache / f"{tag}_usgs.csv"
    try:
        n_a = fetch(arch, ["time_utc", "value_ft", "code"],
                    lambda: gd_fetch.usgs_continuous(site, iso(t0, True), iso(t1, True)), a.refresh)
    except Exception as e:                       # one bad site shouldn't stop the batch
        print(f"  USGS download failed: {e}")
        return dict(base, status=f"usgs error: {e}")
    if n_a == 0:
        print("  skipped: USGS returned no archive readings for this window")
        return dict(base, status="no archive data")

    live, n_l = None, 0
    if nws:
        live = cache / f"{tag}_iem.csv"
        try:
            n_l = fetch(live, ["time_utc", "value_ft"],
                        lambda: gd_fetch.iem_hads(nws, iso(t0, False), iso(t1, False)), a.refresh)
        except Exception as e:
            print(f"  IEM download failed ({e}); plotting archive only")
            n_l = 0
        if n_l == 0:
            live = None
    else:
        print("  no NWS ID for this site; plotting archive only")

    out = figs / f"{tag}.png"
    tz = TZ.get(event, "America/Chicago")
    args = ["--archive", str(arch), "--out", str(out), "--title", title,
            "--start", iso(t0, False), "--end", iso(t1, False), "--tz", tz,
            "--gap-min", "20"]               # 20, not plot_gauge's 60: a gap of exactly 60 min must still show
    if live:
        args += ["--live", str(live)]
    try:
        plot_with_gap(args, g0, g1, tz, shade_label)
    except Exception as e:                       # one unreadable file shouldn't stop the batch either
        print(f"  plot failed: {type(e).__name__}: {e}")
        return dict(base, status=f"plot error: {e}")
    return dict(base, n_archive=n_a, n_live=n_l, png=str(out.relative_to(ROOT)), status="ok")


CLASSES = ["SILENT", "FROZEN", "UNDER_READ", "IMPLAUSIBLE", "LIVE_PRESENT", "NO_LIVE_DATA"]


def recount(ai: pd.DataFrame, path: str):
    """Print your class counts next to live_class, the agreement, and each disagreement."""
    p = Path(path)
    p = p if p.is_absolute() or p.exists() else ROOT / p
    mine = pd.read_csv(p, dtype=str, encoding="utf-8-sig")
    mine.columns = [c.strip().lower() for c in mine.columns]
    if not {"site", "event", "my_class"} <= set(mine.columns):
        sys.exit(f"{p.name} needs columns site, event, my_class; it has {list(mine.columns)}")
    mine["site"] = mine["site"].str.strip()
    short = mine["site"].str.len() < 8                      # Sheets/Excel dropped the leading zero(s)?
    if short.any():
        sys.exit(f"these site numbers look too short (leading zeros lost?): {list(mine.loc[short, 'site'])}")
    mine["my_class"] = mine["my_class"].fillna("").str.strip().str.upper().str.replace(" ", "_")
    m = ai.merge(mine[["site", "event", "my_class"]], on=["site", "event"], how="left")
    m.insert(0, "row", range(1, len(m) + 1))
    blank = m[m.my_class.isna() | (m.my_class == "")]
    bad = m[~m.my_class.isin(CLASSES + [""]) & m.my_class.notna()]
    if len(bad):
        sys.exit("unknown class(es): " + ", ".join(f"row {r.row} '{r.my_class}'" for r in bad.itertuples())
                 + f"\nuse one of: {', '.join(CLASSES)}")
    done = m.drop(blank.index)
    print(f"{'class':<14}{'AI (all 36)':>12}{'AI (labelled rows)':>20}{'yours':>8}")
    for c in CLASSES:
        print(f"{c:<14}{(m.live_class == c).sum():>12}{(done.live_class == c).sum():>20}{(done.my_class == c).sum():>8}")
    print(f"{'total':<14}{len(m):>12}{len(done):>20}{len(done):>8}")
    agree = (done.my_class == done.live_class).sum()
    print(f"\nagreement: {agree} of {len(done)} labelled rows")
    if len(blank):
        print(f"not yet labelled ({len(blank)}): rows " + ", ".join(str(x) for x in blank.row))
    dis = done[done.my_class != done.live_class]
    for r in dis.itertuples():
        print(f"  row {r.row:>2}  {r.site:<11}{r.event:<9}AI {r.live_class:<13}-> yours {r.my_class}")


def plot_with_gap(args, g0, g1, tz_name, shade_label="archive gap"):
    """Run plot_gauge.main unchanged, shading the gap just before it saves the figure."""
    import matplotlib.pyplot as plt
    from zoneinfo import ZoneInfo
    tz = ZoneInfo(tz_name)                           # must match the --tz given to plot_gauge
    loc = lambda t: t.tz_convert(tz).tz_localize(None)
    real_save = plt.Figure.savefig

    def save(fig, *k, **kw):
        ax = fig.axes[0]
        ax.axvspan(loc(g0), loc(g1), color="#52514e", alpha=0.10, lw=0, zorder=0, label=shade_label)
        ax.legend(frameon=False, fontsize=7.5, loc="best")     # keep the legend off the rising limb
        return real_save(fig, *k, **kw)

    plt.Figure.savefig = save
    try:
        plot_gauge.main(args)
    finally:
        plt.Figure.savefig = real_save


if __name__ == "__main__":
    main()