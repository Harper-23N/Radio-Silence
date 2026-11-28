"""Hour 25 - Verify pilot P8 (equipment limits and NWS flood stage).

Three sub-commands, one per guide step:

  python -I code/verify_p8.py urls              Step 1a: print the 10 browser links (open each by hand)
  python -I code/verify_p8.py fetch             Step 1b + 2: download the same 10 JSONs, pull out every
                                                threshold and any dates, compare with the CSV
  python -I code/verify_p8.py rates             Step 3: recompute the P8 rates from the pilot table
  python -I code/verify_p8.py rates --thresholds data/p8_check/thresholds_flood_time.csv
  python -I code/verify_p8.py rates --thresholds data/p8_check/thresholds_flood_time.csv --exclude data/p8_check/post_flood_sites.txt
                                                Step 3 sensitivity: same, dropping gauges you flagged
                                                'possibly post-flood'

Run from the RadioSilence folder. Needs only the Python standard library.
Set USGS_API_KEY first (same key as gd_fetch.py); without it you may be rate-limited.
"""
from __future__ import annotations
import csv, json, math, os, re, sys, time, urllib.error, urllib.parse, urllib.request

META = "https://api.waterdata.usgs.gov/ogcapi/v1/collections/time-series-metadata/items"
UA = {"User-Agent": "GaugeDark student science-fair project (contact via your school email)"}
OUT = "data/p8_check"

# The 10 gauges. Chosen on purpose to cover every kind of case, not at random:
SAMPLE = [
    ("08165500", "texas",    "Hunt: went dark, last reading 29.45 ft vs limit 60 ft"),
    ("08166200", "texas",    "Kerrville: complete record (control)"),
    ("08166250", "texas",    "Center Point: went dark, no flood stage in CSV"),
    ("08167500", "texas",    "label carries a date (10/2012): test of Step 2"),
    ("08104590", "texas",    "radar label variant; crest above limit; went dark"),
    ("03466500", "helene",   "crest 66.03 ft ABOVE limit 60 ft but stayed alive"),
    ("03463300", "helene",   "limit 12.63 ft is BELOW flood stage 14 ft: suspicious"),
    ("03209500", "kentucky", "'Equipment Limit' label variant"),
    ("08068000", "harvey",   "large stage numbers (limit 160 ft, flood 115.8 ft)"),
    ("08072050", "harvey",   "went dark, crest 28.72 ft just under limit 29 ft"),
]

# Pilot flood windows (from the guide's flood-box table). A threshold dated after the start
# may not have existed during the flood.
FLOOD_WINDOW = {"texas": ("2025-07-03", "2025-07-07"), "helene": ("2024-09-25", "2024-09-30"),
                "kentucky": ("2022-07-26", "2022-07-31"), "vermont": ("2023-07-09", "2023-07-14"),
                "harvey": ("2017-08-25", "2017-09-01"), "waverly": ("2021-08-20", "2021-08-24"),
                "yellowstone": ("2022-06-11", "2022-06-16")}
FLOOD_START = {k: v[0] for k, v in FLOOD_WINDOW.items()}


def periods_of(entry: dict) -> list[dict]:
    """USGS layout (seen 23 Nov 2026): {"Name":..., "Periods":[{"StartTime","EndTime","AppliedTime",
    "ReferenceValue", ...}]}. Returns the periods with dates cut to YYYY-MM-DD."""
    out = []
    for p in entry.get("Periods") or []:
        if p.get("ReferenceValue") is None:
            continue
        out.append({"start": str(p.get("StartTime", ""))[:10], "end": str(p.get("EndTime", ""))[:10],
                    "applied": str(p.get("AppliedTime", ""))[:10], "value": float(p["ReferenceValue"])})
    return out


def at_flood(entries: list[dict], event: str):
    """For a list of threshold entries, return (value in effect at flood start, note).
    note says if a period boundary falls inside the flood, or if the in-effect period was only
    entered into the USGS system (AppliedTime) after the flood."""
    a, b = FLOOD_WINDOW[event]
    vals, notes = [], []
    for e in entries:
        for p in periods_of(e["obj"]):
            if p["start"] <= a < p["end"] or (p["start"] == "0001-01-01" and a < p["end"]):
                vals.append(p["value"])
                if p["start"] == "0001-01-01":
                    notes.append(f"{e['label']}: undated start")
                if p["applied"] > b:
                    notes.append(f"{e['label']}: entered {p['applied']}, after flood")
            if a < p["start"] <= b or a < p["end"] < b:
                notes.append(f"{e['label']}: limit changed DURING flood ({p['start']} to {p['end']})")
    return (vals[0] if len(set(vals)) == 1 else ";".join(map(str, vals))) if vals else "", "; ".join(notes)


def period_table(entries: list[dict]) -> str:
    return " | ".join(f"{e['label'][:30]}: " + ", ".join(f"{p['value']} [{p['start']} to {p['end']}, entered {p['applied']}]"
                      for p in periods_of(e["obj"])) for e in entries)

OPMAX = re.compile(r"operational.*(max|high)|(max|high).*operational|equipment limit", re.I)
FLOOD = re.compile(r"flood\s*stage", re.I)
DATE = re.compile(r"\b(\d{4}-\d{2}-\d{2})|\b(\d{1,2})/(\d{4})\b|\b(\d{1,2})/(\d{1,2})/(\d{4})\b")


def url_for(site: str) -> str:
    q = {"monitoring_location_id": f"USGS-{site}", "parameter_code": "00065", "f": "json"}
    return META + "?" + urllib.parse.urlencode(q)


def get_json(url: str) -> dict:
    h = dict(UA)
    if os.environ.get("USGS_API_KEY"):
        h["X-Api-Key"] = os.environ["USGS_API_KEY"]
    for k in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=60) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and k < 4:
                time.sleep(10 * (k + 1)); continue
            raise
    raise RuntimeError("unreachable")


def dates_in(text: str) -> list[str]:
    """Any date written in a string, as YYYY-MM-DD (month-only dates become day 01)."""
    out = []
    for m in DATE.finditer(text):
        if m.group(1):
            out.append(m.group(1))
        elif m.group(2):
            out.append(f"{m.group(3)}-{int(m.group(2)):02d}-01")
        else:
            out.append(f"{m.group(6)}-{int(m.group(4)):02d}-{int(m.group(5)):02d}")
    return [d for d in out if "1900" < d < "2100"]        # drop open-ended placeholders like 9999-12-31


def find_thresholds(obj, path="") -> list[dict]:
    """Walk the whole JSON and return every object whose name/label mentions an operational limit or
    flood stage, with the numbers and dates found inside it. Written to survive small changes in the
    API's layout, because the exact nesting of 'thresholds' was not confirmed from here."""
    found = []
    if isinstance(obj, str) and obj.strip().startswith(("[", "{")):
        try:
            obj = json.loads(obj)
        except ValueError:
            return found
    if isinstance(obj, dict):
        label = " ".join(str(v) for k, v in obj.items()
                         if isinstance(v, str) and k.lower() in ("name", "label", "type", "description",
                                                                  "threshold_name", "reference_code"))
        kind = "op_max" if OPMAX.search(label) and not re.search(r"min", label, re.I) else "flood" if FLOOD.search(label) else None
        if kind:
            flat = json.dumps(obj)
            nums = [float(x) for x in re.findall(r'"(?:value|Value|ReferenceValue|threshold_value)"\s*:\s*"?(-?\d+\.?\d*)', flat)]
            found.append({"kind": kind, "label": label.strip(), "values": nums,
                          "dates": sorted(set(dates_in(flat))), "path": path, "raw": flat, "obj": obj})
        else:
            for k, v in obj.items():
                found += find_thresholds(v, f"{path}/{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            found += find_thresholds(v, f"{path}[{i}]")
    return found


def same(a: str, b) -> str:
    if a in ("", None) and b in ("", None):
        return "both blank"
    if a in ("", None) or b in ("", None):
        return "MISMATCH"
    if isinstance(b, str) and ";" in b:
        return "SEVERAL LIMITS"
    return "yes" if abs(float(a) - float(b)) < 0.005 else "MISMATCH"


def cmd_urls():
    for site, event, why in SAMPLE:
        print(f"# {site} ({event}) - {why}\n{url_for(site)}\n")


def cmd_fetch(refetch: bool = False):
    os.makedirs(f"{OUT}/raw", exist_ok=True)
    csvv = {r["site"]: r for r in csv.DictReader(open("data/gauge_thresholds_usgs.csv"))}
    rows = []
    for site, event, why in SAMPLE:
        raw = f"{OUT}/raw/{site}.json"
        if refetch or not os.path.exists(raw):            # reuse saved pages; add --refetch to download again
            json.dump(get_json(url_for(site)), open(raw, "w"), indent=1); time.sleep(1)
        j = json.load(open(raw))
        hits = []
        for f in j.get("features", []):
            p = f.get("properties", {})
            hits += find_thresholds(p.get("thresholds", p), "properties")
        op = [h for h in hits if h["kind"] == "op_max"]
        fl = [h for h in hits if h["kind"] == "flood"]
        op_f, op_note = at_flood(op, event)
        fl_f, fl_note = at_flood(fl, event)
        c = csvv.get(site, {})
        rows.append({
            "site": site, "event": event, "flood_window": "/".join(FLOOD_WINDOW[event]), "why_chosen": why,
            "op_max_csv": c.get("op_max_ft", ""), "op_max_at_flood": op_f, "op_max_match": same(c.get("op_max_ft", ""), op_f),
            "flood_csv": c.get("nws_flood_stage_ft", ""), "flood_at_flood": fl_f, "flood_match": same(c.get("nws_flood_stage_ft", ""), fl_f),
            "notes": "; ".join(x for x in (op_note, fl_note) if x),
            "op_max_periods": period_table(op), "flood_periods": period_table(fl),
            "hand_op_max": "", "hand_flood": "", "possibly_post_flood": "", "note": "",
        })
        r = rows[-1]
        print(f"{site} ({event}): op max CSV {r['op_max_csv'] or '-':>6} at flood {str(op_f) or '-':>6} [{r['op_max_match']}]   "
              f"flood stage CSV {r['flood_csv'] or '-':>6} at flood {str(fl_f) or '-':>6} [{r['flood_match']}]")
        for e in op + fl:
            for p in periods_of(e["obj"]):
                print(f"     {e['label'][:38]:<38} {p['value']:>7}  {p['start']} to {p['end']}  (entered {p['applied']})")
        if r["notes"]:
            print(f"     NOTE: {r['notes']}")
        if not hits:
            print(f"   !! no threshold found by the parser; open {raw} and look by hand")
    with open(f"{OUT}/verify10.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
    print(f"\nSaved {OUT}/verify10.csv. Fill hand_op_max, hand_flood and possibly_post_flood from the browser.")


def wilson(k: int, n: int, z: float = 1.96) -> str:
    if n == 0:
        return "n/a"
    p = k / n; d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return f"{100*(c-h):.0f}-{100*(c+h):.0f}%"


def fisher_two_sided(a, b, c, d) -> tuple[float, float]:
    """2x2 table [[a,b],[c,d]] -> (odds ratio, two-sided p). Standard library only."""
    n1, n2, m1, n = a + b, c + d, a + c, a + b + c + d
    lc = lambda x, y: math.lgamma(x + 1) - math.lgamma(y + 1) - math.lgamma(x - y + 1)
    pr = lambda x: math.exp(lc(n1, x) + lc(n2, m1 - x) - lc(n, m1))
    p0 = pr(a)
    p = sum(pr(x) for x in range(max(0, m1 - n2), min(n1, m1) + 1) if pr(x) <= p0 * (1 + 1e-7))
    orr = (a * d) / (b * c) if b * c else float("inf")
    return orr, min(1.0, p)


def cmd_rates(exclude_file: str | None, thresholds: str = "data/gauge_thresholds_usgs.csv"):
    st = {(r["event"], r["site"]): r for r in csv.DictReader(open("data/stations_7floods_v3.csv"))}
    wl = [(r["name"], r["site"]) for r in csv.DictReader(open("data/watchlist.csv"))]
    th = {r["site"]: r for r in csv.DictReader(open(thresholds))}
    print(f"Thresholds from {thresholds}")
    skip = set(open(exclude_file).read().split()) if exclude_file else set()
    big = [st[k] for k in wl if k in st]                       # 116 big-rise gauges
    have = [r for r in big if th.get(r["site"], {}).get("op_max_ft") and r["site"] not in skip]
    lim = lambda r: float(th[r["site"]]["op_max_ft"])
    dark = lambda r: r["dark1h"] == "1"                       # pilot definition: >= 1 h dark gap
    above = [r for r in have if float(r["max_ft"]) >= lim(r)]
    below = [r for r in have if float(r["max_ft"]) < lim(r)]
    a, c = sum(map(dark, above)), sum(map(dark, below))
    D = [r for r in have if dark(r)]
    last_below = [r for r in D if r["stage_last_reading"] and float(r["stage_last_reading"]) < lim(r)]
    crest_below = [r for r in D if float(r["max_ft"]) < lim(r)]
    orr, p = fisher_two_sided(a, len(above) - a, c, len(below) - c)
    print(f"Big-rise gauges: {len(big)}; with an operational max: {len(have)}"
          + (f" (after excluding {len(skip)} flagged)" if skip else ""))
    print(f"Dark when crest reached the limit:  {a} of {len(above)}  ({100*a/max(1,len(above)):.0f}%, Wilson {wilson(a,len(above))})   pilot: 7 of 13")
    print(f"Dark when crest stayed below it:    {c} of {len(below)}  ({100*c/max(1,len(below)):.0f}%, Wilson {wilson(c,len(below))})   pilot: 20 of 92")
    print(f"Fisher (not clustered by flood):    odds ratio {orr:.1f}, p = {p:.3f}   pilot: 4.2, p = 0.036")
    print(f"Dark gauges whose LAST reading was below the limit: {len(last_below)} of {len(D)}   pilot: 23 of 27")
    print(f"Dark gauges whose CREST never reached the limit:    {len(crest_below)} of {len(D)}   pilot: 20 of 27")
    print("\nDark gauges with crest at/above the limit:")
    for r in above:
        if dark(r):
            print(f"  {r['event']:<9} {r['site']:<11} crest {r['max_ft']:>7}  limit {lim(r):>6}  last reading {r['stage_last_reading'] or '-'}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "urls":
        cmd_urls()
    elif cmd == "fetch":
        cmd_fetch("--refetch" in sys.argv)
    elif cmd == "rates":
        arg = lambda k: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else None
        cmd_rates(arg("--exclude"), arg("--thresholds") or "data/gauge_thresholds_usgs.csv")
    else:
        print(__doc__)