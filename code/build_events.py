"""Build data/events.csv (the final flood list) from your decisions sheet.

Run from the project folder:
    python -I code/build_events.py
    python -I code/build_events.py --decisions data/events_decisions.csv

Takes every row whose decision is 'keep' (test flood) or 'dev' (development flood) and writes:
  event, event_id, dev_or_test, start, end, west, south, east, north, n_hwm, source, notes
  - start/end      = window_start / window_end (already padded by 1 day)
  - west..north    = the lower-48 box (l48_*), already widened by 0.25 deg
  - n_hwm          = surveyed, lower-48, non-coastal marks (blank for NOAA-only floods)
  - source         = STN, or NOAA Part B for floods with no STN event
  - notes          = your reason column
Dev floods are named with their pilot names (harvey, helene, ...) so they match run_census.py.
Stops with a list of problems if any kept row is missing a window or box, or has bad values.
"""
import argparse, csv, re, sys
from datetime import date


def read_table(path):
    raw = open(path, "rb").read()
    text = raw.decode("utf-16") if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else raw.decode("utf-8-sig", "replace")
    first = text.splitlines()[0]
    return list(csv.DictReader(text.splitlines(), delimiter="\t" if first.count("\t") > first.count(",") else ","))


def parse_day(x):
    """YYYY-MM-DD, YYYY-M-D, or Excel's M/D/YYYY."""
    x = (x or "").strip().split("T")[0].split(" ")[0]
    m = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", x)
    if m:
        return date(int(m[1]), int(m[2]), int(m[3]))
    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", x)
    if m:
        return date(int(m[3]), int(m[1]), int(m[2]))
    raise ValueError(x)


def slug(name):
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--decisions", default="data/events_decisions.csv")
    a = ap.parse_args()
    rows = read_table(a.decisions)
    dec = next(c for c in rows[0] if c and c.lower().startswith("decision"))

    out, problems = [], []
    for r in rows:
        d = (r.get(dec) or "").strip().lower()
        if d not in ("keep", "dev"):
            continue
        eid, name = (r.get("event_id") or "").strip(), (r.get("name") or "").strip()
        label = f"{eid or '(no id)'} {name}"
        try:
            start, end = parse_day(r.get("window_start")), parse_day(r.get("window_end"))
        except (ValueError, KeyError, AttributeError):
            problems.append(f"{label}: window_start/window_end missing or not a date "
                            f"({r.get('window_start')!r}, {r.get('window_end')!r})")
            continue
        try:
            w, s, e, n = (float(r[k]) for k in ("l48_west", "l48_south", "l48_east", "l48_north"))
        except (ValueError, KeyError, TypeError):
            problems.append(f"{label}: lower-48 box (l48_west/south/east/north) missing")
            continue
        if not eid:
            problems.append(f"{label}: event_id is blank")
        if end < start:
            problems.append(f"{label}: window ends before it starts")
        if not (w < e and s < n and -125.5 <= w and e <= -66 and 24 <= s and n <= 50):
            problems.append(f"{label}: box looks wrong (west {w}, south {s}, east {e}, north {n})")
        dev_name = (r.get("dev_flood") or "").strip()
        if d == "dev" and not dev_name:
            problems.append(f"{label}: marked dev but dev_flood is blank")
        out.append(dict(
            event=dev_name if d == "dev" else slug(name),
            event_id=eid, dev_or_test="dev" if d == "dev" else "test",
            start=start, end=end, west=w, south=s, east=e, north=n,
            n_hwm=r.get("n_noncoastal_surv_l48", ""),
            source="NOAA Part B" if eid.upper().startswith("NOAA") else "STN",
            notes=(r.get("reason") or "").strip()))

    if problems:
        print("Fix these in your decisions sheet, then run again:")
        for p in problems:
            print("  -", p)
        sys.exit(1)
    events = [o["event"] for o in out]
    dupes = {x for x in events if events.count(x) > 1}
    if dupes:
        sys.exit(f"Two floods have the same name: {', '.join(sorted(dupes))}")

    out.sort(key=lambda o: (o["dev_or_test"], o["start"]))
    cols = ["event", "event_id", "dev_or_test", "start", "end", "west", "south", "east", "north",
            "n_hwm", "source", "notes"]
    with open("data/events.csv", "w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=cols)
        wr.writeheader()
        wr.writerows(out)
    nd = sum(o["dev_or_test"] == "dev" for o in out)
    print(f"{len(out)} floods: {nd} dev, {len(out) - nd} test\n")
    for o in out:
        print(f"  {o['dev_or_test']:<4} {o['event']:<46} {o['start']} to {o['end']}  {o['source']}")
    print("\nwrote data/events.csv")


if __name__ == "__main__":
    main()