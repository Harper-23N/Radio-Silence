"""Plot one gauge for one event: archive series (blue), live-feed series (orange dashed), crest marked.

Inputs are the CSVs written by gd_fetch.py:
    archive  ->  python -I code/gd_fetch.py usgs 08166250 2025-07-04T00:00:00Z 2025-07-08T00:00:00Z > data/cp_usgs.csv
    live     ->  python -I code/gd_fetch.py iem  GCTT2    2025-07-04T05:00Z    2025-07-08T05:00Z     > data/cp_iem.csv
(Windows PowerShell saves `>` output as UTF-16; this script reads either encoding.)

Example (Center Point, 4 July 2025):
    python -I code/plot_gauge.py --archive data/mine_cp_usgs.csv --live data/mine_cp_iem.csv \
        --title "Center Point (08166250), 4 July 2025" --start 2025-07-04T05:00Z --end 2025-07-04T21:00Z \
        --out figs/cp_event.png

The crest defaults to the highest archive value (USGS's official peak, even if it was inserted later).
Override with --crest-ft and --crest-time (UTC) if your crest comes from a survey or another source.
Use --ymin/--ymax to zoom when a spike or a high datum (e.g. 110 ft) squashes the rise; readings
outside the range are drawn as ^/v markers on the edge and printed, never silently dropped.
--start/--end fix the x-axis to that window, so a crest outside it is not drawn and cannot widen the axis.
Lines break wherever readings are more than --gap-min minutes apart, so silences show as gaps and
are never drawn as if the river were measured through them. A gap of exactly --gap-min is NOT broken:
to see a 60-min gap, use a smaller --gap-min (e.g. 20 for 5- or 15-min data).
"""
from __future__ import annotations
import argparse, os, sys
from zoneinfo import ZoneInfo
import matplotlib
import matplotlib.colors
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

BLUE, ORANGE = "#2a78d6", "#eb6834"
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
plt.rcParams.update({"font.family": ["Inter", "DejaVu Sans"], "font.size": 9, "axes.edgecolor": GRID, "axes.labelcolor": INK2,
                     "xtick.color": INK2, "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True,
                     "figure.facecolor": SURF, "axes.facecolor": SURF, "savefig.facecolor": SURF})


def read_series(path: str) -> pd.Series:
    """Read a gd_fetch.py CSV (UTF-8 or UTF-16) into a UTC-indexed Series of stage in ft."""
    with open(path, "rb") as f:
        head = f.read(2)
    enc = "utf-16" if head in (b"\xff\xfe", b"\xfe\xff") else "utf-8-sig"
    d = pd.read_csv(path, encoding=enc)
    # ISO8601, not a guessed format: USGS mixes "...T11:15:00+00:00" with "...T11:15:00.470501+00:00"
    # (edited values), and IEM writes "2025-07-04 05:00" with no zone, which is UTC
    d["time_utc"] = pd.to_datetime(d["time_utc"], utc=True, format="ISO8601")
    d["value_ft"] = pd.to_numeric(d["value_ft"], errors="coerce")
    s = d.dropna(subset=["value_ft"]).set_index("time_utc")["value_ft"].sort_index()
    return s[~s.index.duplicated(keep="last")]


def with_breaks(s: pd.Series, gap_min: float) -> pd.Series:
    """Insert NaN between readings more than gap_min apart so matplotlib breaks the line."""
    if len(s) < 2:
        return s
    gaps = s.index.to_series().diff() > pd.Timedelta(minutes=gap_min)
    br = s.index[gaps.values] - pd.Timedelta(seconds=1)
    return pd.concat([s, pd.Series(np.nan, index=br)]).sort_index()


def isolated(s: pd.Series, gap_min: float) -> pd.Series:
    """Readings with no neighbour within gap_min: a line can't show them, so they get a dot."""
    t = s.index.to_series()
    g = pd.Timedelta(minutes=gap_min)
    lone = ((t.diff() > g) | t.diff().isna()) & ((t.diff(-1).abs() > g) | t.diff(-1).isna())
    return s[lone.values]


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--archive", required=True, help="USGS archive CSV from gd_fetch.py usgs")
    p.add_argument("--live", help="Iowa State live-feed CSV from gd_fetch.py iem (optional)")
    p.add_argument("--out", required=True, help="output image, e.g. figs/cp_event.png")
    p.add_argument("--title", default="", help="plot title")
    p.add_argument("--start", help="clip window start, UTC (e.g. 2025-07-04T05:00Z)")
    p.add_argument("--end", help="clip window end, UTC")
    p.add_argument("--crest-ft", type=float, help="crest stage to mark (default: archive maximum)")
    p.add_argument("--crest-time", help="crest time, UTC (needed with --crest-ft)")
    p.add_argument("--gap-min", type=float, default=60, help="break lines across gaps longer than this (default 60)")
    p.add_argument("--tz", default="America/Chicago", help="time zone for the x axis (default America/Chicago)")
    p.add_argument("--ymin", type=float, help="y-axis bottom in ft (default 0)")
    p.add_argument("--ymax", type=float, help="y-axis top in ft (default: highest value x 1.1)")
    p.add_argument("--archive-color", default=BLUE, help=f"archive line color, hex or name (default {BLUE})")
    p.add_argument("--live-color", default=ORANGE, help=f"live-feed line color, hex or name (default {ORANGE})")
    a = p.parse_args(argv)
    for c in (a.archive_color, a.live_color):
        if not matplotlib.colors.is_color_like(c):
            p.error(f"not a color: {c!r} (use a hex code like '#1b4f9c' or a name like 'navy')")

    arch = read_series(a.archive)
    live = read_series(a.live) if a.live else None
    if (a.crest_ft is None) != (a.crest_time is None):
        p.error("give --crest-ft and --crest-time together")

    # crest: from the full archive, before clipping, so a narrow window can't hide it
    if a.crest_ft is not None:
        t = pd.Timestamp(a.crest_time)
        crest_t = t.tz_convert("UTC") if t.tzinfo else t.tz_localize("UTC")
        crest_v, crest_src = a.crest_ft, "given"
    else:
        crest_t, crest_v, crest_src = arch.idxmax(), arch.max(), "archive"

    def clip(s):
        if s is None:
            return None
        if a.start: s = s[s.index >= pd.Timestamp(a.start)]
        if a.end:   s = s[s.index <= pd.Timestamp(a.end)]
        return s
    arch, live = clip(arch), clip(live)
    if arch.empty and (live is None or live.empty):
        sys.exit("no data in the chosen window")

    tz = ZoneInfo(a.tz)
    loc = lambda idx: idx.tz_convert(tz).tz_localize(None)      # matplotlib wants naive local times

    fig, ax = plt.subplots(figsize=(6.6, 3.1))
    if not arch.empty:
        b = with_breaks(arch, a.gap_min)
        ax.plot(loc(b.index), b.values, color=a.archive_color, lw=2, label="archive (USGS)")
        lone = isolated(arch, a.gap_min)
        ax.scatter(loc(lone.index), lone.values, s=10, color=a.archive_color, zorder=4)
    if live is not None and not live.empty:
        b = with_breaks(live, a.gap_min)
        ax.plot(loc(b.index), b.values, color=a.live_color, lw=1.5, ls=(0, (3, 2)), label="live feed (Iowa State HADS)")
        lone = isolated(live, a.gap_min)
        ax.scatter(loc(lone.index), lone.values, s=10, color=a.live_color, zorder=4)

    ct = loc(pd.DatetimeIndex([crest_t]))[0]
    ax.scatter([ct], [crest_v], s=40, facecolor=SURF, edgecolor=INK, lw=1.4, zorder=5)
    ax.annotate(f"crest {crest_v:.2f} ft\n{ct:%H:%M, %d %b}", (ct, crest_v), xytext=(8, -2), textcoords="offset points",
                va="top", fontsize=7.5, color=INK2)

    top = a.ymax if a.ymax is not None else max(crest_v, arch.max() if not arch.empty else 0,
                                                live.max() if live is not None and not live.empty else 0) * 1.1
    bot = a.ymin if a.ymin is not None else 0
    ax.set_ylim(bot, top)
    if a.start or a.end:                                          # keep a zoom zoomed: a crest outside it can't widen the axis
        x0 = loc(pd.DatetimeIndex([pd.Timestamp(a.start)]))[0] if a.start else None
        x1 = loc(pd.DatetimeIndex([pd.Timestamp(a.end)]))[0] if a.end else None
        ax.set_xlim(x0, x1)
    for s, c in ((arch, a.archive_color), (live, a.live_color)):     # off-chart readings: mark them, don't hide them
        if s is None or s.empty:
            continue
        for sel, y, m, word in ((s > top, top, "^", "above"), (s < bot, bot, "v", "below")):
            if sel.any():
                ax.scatter(loc(s.index[sel.values]), [y] * int(sel.sum()), marker=m, s=28, color=c,
                           clip_on=False, zorder=6)
                print(f"note: {int(sel.sum())} reading(s) {word} the chart, first {s[sel].iloc[0]:.2f} ft "
                      f"at {s[sel].index[0]:%Y-%m-%d %H:%M} UTC")
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(ax.xaxis.get_major_locator()))
    ax.set_xlabel(f"local time ({a.tz})"); ax.set_ylabel("gage height (ft)")
    if a.title:
        ax.set_title(a.title, loc="left", fontsize=10, color=INK, fontweight="semibold")
    ax.legend(frameon=False, fontsize=7.5, loc="upper left")
    fig.tight_layout()
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    fig.savefig(a.out, dpi=220); plt.close(fig)
    print(f"wrote {a.out}  (crest {crest_v:.2f} ft at {crest_t:%Y-%m-%d %H:%M} UTC, from {crest_src})")


if __name__ == "__main__":
    main()