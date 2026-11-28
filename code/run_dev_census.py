"""Hour 48. Recompute the pilot comparisons from saved development records only.

Run: python -I code/run_dev_census.py
Reads RadioSilence beside this script's code folder or in ~/Downloads/RadioSilence.
Override with --project PATH_TO_RADIOSILENCE. Outputs default to data/ beside code/.
For a saved USGS CSV, its optional <site>.query.json records the completed
request: {"start": "<ISO timestamp>", "end": "<ISO timestamp>", "n_readings": 123}.
Use the number of rows returned for that CSV by the completed query.
Exit 0 means both pilot comparisons can be evaluated, 2 means inputs are incomplete,
and 1 means the run failed. The CSVs retain unresolved sites and cache diagnostics.
"""

import argparse
import csv
import json
import math
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from statistics import median
from tempfile import NamedTemporaryFile


COUNTS = dict(harvey=93, helene=84, kentucky=34, texas=89, vermont=45,
              waverly=14, yellowstone=28)
WRONG = {"FROZEN", "UNDER_READ", "IMPLAUSIBLE"}
CLASSES = WRONG | {"SILENT", "LIVE_PRESENT"}


def read_rows(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def index(rows):
    result = {}
    for row in rows:
        key = row["event"], row["site"]
        if key in result:
            raise ValueError(f"Repeated event/site key {key}")
        result[key] = row
    return result


def roster(data, windows):
    pilot = index(read_rows(data / "stations_7floods_v3.csv"))
    if Counter(event for event, _ in pilot) != COUNTS or set(windows) != set(COUNTS):
        raise ValueError("Expected the original 387 pilot rows across seven floods")
    if any(not re.fullmatch(r"[0-9]+", site) for _, site in pilot):
        raise ValueError("Invalid USGS site in the pilot roster")
    labels = index(read_rows(data / "live_feed_dark_gauges_classified.csv"))
    dark = {key for key, r in pilot.items() if int(r["dark1h"])}
    big = [r for r in pilot.values() if float(r["rise_ft"]) >= 20]
    tally = Counter(r["live_class"] for r in labels.values())
    if (len(big) != 116 or sum(int(r["dark1h"]) for r in big) != 28
            or dark != labels.keys() or len(dark) != 36 or tally["NO_LIVE_DATA"] != 3
            or sum(tally[c] for c in WRONG) != 16 or set(tally) - CLASSES - {"NO_LIVE_DATA"}):
        raise ValueError("Pilot reference tables disagree with the Hour 48 benchmarks")
    return pilot, labels


def query_receipt(path, rules):
    """Read the UTC-aware query bounds and original row count for one USGS file."""
    receipt = json.loads(path.read_text(encoding="utf-8-sig"))
    bounds = []
    for field in ("start", "end"):
        stamp = datetime.fromisoformat(receipt[field].replace("Z", "+00:00"))
        if stamp.utcoffset() is None:
            raise ValueError(f"{field} must include a time zone")
        bounds.append(rules.utc_ms(receipt[field]))
    count = receipt["n_readings"]
    if bounds[0] >= bounds[1] or type(count) is not int or count < 0:
        raise ValueError("expected increasing query dates and a nonnegative integer n_readings")
    return bounds[0], bounds[1], count


def cache_records(path, station, window, rules, query=None):
    """Keep null observations for coverage. Holes inside the window are detector inputs."""
    start, end = window
    if query is not None:
        query_start, query_end, expected_rows = query
        query_span = f"{rules.utc_label(query_start)} to {rules.utc_label(query_end)}"
        if query_start > start or query_end < end:
            return [], "unverified_window", f"saved query {query_span} does not cover the pilot window"
    with path.open("rb") as stream:
        bom = stream.read(2)
    encoding = "utf-16" if bom in (b"\xff\xfe", b"\xfe\xff") else "utf-8-sig"
    values = {}
    with path.open(encoding=encoding, newline="") as stream:
        reader = csv.DictReader(stream)
        fields = reader.fieldnames or []
        hads = station and {"station", "utc_valid"} <= set(fields)
        stages = [f for f in fields if f.startswith("HG")]
        if hads:
            if not stages:
                raise ValueError("IEM file has no HG stage column")
        elif not {"time_utc", "value_ft"} <= set(fields) or (not station and "code" not in fields):
            raise ValueError("unrecognized cache header")
        count = 0
        for row in reader:
            count += 1
            if hads and row["station"].strip().upper() != station:
                raise ValueError("unexpected IEM station")
            t = rules.utc_ms(row["utc_valid"] if hads else row["time_utc"])
            raw = next((row[f] for f in stages if row[f]), "") if hads else row["value_ft"]
            if raw is None or (not station and row["code"] is None):
                raise ValueError(f"truncated CSV row at line {reader.line_num}")
            if query is not None and not query_start <= t <= query_end:
                raise ValueError(f"reading {rules.utc_label(t)} outside saved query {query_span}")
            v = float(raw) if raw.strip() else None
            if v is not None and not math.isfinite(v):
                raise ValueError("non-finite stage")
            item = v, "" if station else rules.pilot_code(row["code"])
            if t in values and values[t] != item:
                raise ValueError(f"conflicting readings at {rules.utc_label(t)}")
            values[t] = item
    times = sorted(values)
    verified_count = query is not None and expected_rows is not None
    if verified_count and count != expected_rows:
        return [], "incomplete", f"saved query {query_span} recorded {expected_rows} rows, file has {count}"
    if not times:
        detail = f"saved query {query_span}, 0 rows verified" if verified_count else "header only"
        return [], "empty", detail
    inside = [t for t in times if start <= t <= end]
    span = f"{rules.utc_label(times[0])} to {rules.utc_label(times[-1])}"
    # A station can report off the hour. Allow strictly less than one usual
    # interval at either edge, capped at one hour so sparse files cannot pass.
    steps = [b - a for a, b in zip(inside, inside[1:])]
    tolerance = min(median(steps), 3_600_000) if steps else 1
    if not inside:
        return [], "unverified_window", span
    if verified_count:
        span += f" (saved query {query_span}, {count} rows verified)"
    elif times[0] - start >= tolerance or end - times[-1] >= tolerance:
        return [], "unverified_window", span
    else:
        span += " (coverage inferred from observation timestamps)"
    return [(t, *values[t]) for t in inside], "ok", span


def pick_cache(data, candidates, station, window, rules, raw_query=None):
    notes = []
    statuses = []
    for relative in candidates:
        path = data / relative
        if not path.is_file():
            continue
        receipt = path.with_suffix(".query.json")
        try:
            query = raw_query if relative.parts[0] == "raw" else None
            if not station and receipt.is_file():
                query = query_receipt(receipt, rules)
            records, status, detail = cache_records(path, station, window, rules, query)
        except (OSError, ValueError, KeyError, AttributeError, TypeError) as exc:
            records, status, detail = [], "invalid", str(exc)
        if not station and receipt.is_file():
            detail = f"{receipt.name}: {detail}"
        notes.append(f"{relative} [{status}] {detail}")
        statuses.append(status)
        if status == "ok":
            return records, status, str(relative), " | ".join(notes)
    status = next((s for s in ("invalid", "incomplete", "unverified_window", "empty") if s in statuses), "missing")
    return [], status, "", " | ".join(notes) or f"missing {candidates[0]}"


def classifications(result, live, live_status, rules):
    if result is None or not result.dark_gaps:
        return "", "", ""
    labels = []
    gaps = result.dark_gaps
    for gap in gaps:
        entry = rules.gap_details(gap)
        entry["class"] = "UNRESOLVED"
        if live_status == "ok":
            try:
                entry["class"] = rules.classify(gap, live, result.max_ft)
            except rules.NoLiveData:
                entry["class"] = "NO_LIVE_DATA"
            except ValueError as exc:
                entry["reason"] = str(exc)
        elif live_status in {"unmapped", "no_numeric_stage"}:
            entry["class"] = "NO_LIVE_DATA"
        else:
            entry["reason"] = live_status
        labels.append(entry)
    chosen = max(range(len(gaps)), key=lambda i: (gaps[i].spans_peak, gaps[i].hours))
    return labels[chosen]["class"], rules.utc_label(gaps[chosen].start), json.dumps(labels)


def live_scan(live, archive, end, rules):
    """Hour 47 live-only check: count a gap only when the archive spans it."""
    scan = rules.analyze(live, version=2, window_end_ms=end)
    if scan is None:
        return "too_few_readings", "", ""
    if archive is None:
        return "archive_unresolved", len(scan.dark_gaps), ""
    regular, _, cadence = rules.regular_series(archive)
    threshold = max(60, 3.5 * cadence) * 60_000
    missing = [(a[0], b[0]) for a, b in zip(regular, regular[1:]) if b[0] - a[0] >= threshold]
    only = sum(1 for g in scan.dark_gaps if len(regular) >= 2
               and regular[0][0] <= g.start and regular[-1][0] >= g.end
               and not any(a < g.end and b > g.start for a, b in missing))
    return "ok", len(scan.dark_gaps), only


def process(data, key, pilot, reference, hand_label, window, station, shared, multi_series, raw_query, rules):
    event, site = key
    prefix = dict(event=event, site=site)
    start, end = window
    snippets = sorted((data / "dark_rows").glob(f"*_{site}_{event}_usgs.csv"))
    paths = [Path("raw", event, site + ".csv")]
    # The site's older individual pulls may combine sensors. Only the bulk
    # cache carries the chosen series for a known multi-series site.
    if not multi_series:
        paths.append(Path("hand", site + "_usgs.csv"))
        paths.extend(p.relative_to(data) for p in snippets)
    archive, status, source, note = pick_cache(data, paths, None, window, rules, raw_query)
    results = [rules.analyze(archive, version=v, window_end_ms=end) for v in (1, 2)]
    first, second = results
    a = dict(prefix, start_utc=rules.utc_label(start), end_utc=rules.utc_label(end),
             pilot_rise_ft=pilot["rise_ft"], pilot_dark1h=pilot["dark1h"],
             archive_status="too_few_readings" if status == "ok" and first is None else status,
             archive_file=source, archive_cache_detail=note,
             rise_ft=first.rise_ft if first else "", max_ft=first.max_ft if first else "")
    if not station or shared:
        live, ls, source, note = [], "unmapped" if not station else "ambiguous_mapping", "", ""
    else:
        paths = [Path("live", event, station + ".csv"), Path("hand", station + "_iem.csv"),
                 Path("p9_check", "live", station + ".csv")]
        paths.extend(p.relative_to(data) for p in sorted((data / "dark_rows").glob(f"*_{site}_{event}_iem.csv")))
        live, ls, source, note = pick_cache(data, paths, station, window, rules)
        live = [r for r in live if r[1] is not None]
        if ls == "ok" and not live:
            ls = "no_numeric_stage"
    l = dict(prefix, nwsli=station, live_status=ls, live_file=source, live_cache_detail=note,
             pilot_live_class=reference.get("live_class", ""), pilot_gap_start_utc=pilot["gap_start_utc"],
             reviewed_live_class=hand_label)
    for version, res in enumerate(results, 1):
        a[f"v{version}_dark1h"] = int(res.dark1) if res else ""
        a[f"v{version}_n_dark_gaps"] = len(res.dark_gaps) if res else ""
        label, gap_start, details = classifications(res, live, ls, rules)
        l[f"v{version}_live_class"] = label
        l[f"v{version}_representative_start_utc"] = gap_start
        l[f"v{version}_gap_results_json"] = details
    why = set()
    if second:
        old = {(g.start, g.end) for g in first.dark_gaps}
        why = {"open_end" if g.open_end else "in_rise" for g in second.dark_gaps if (g.start, g.end) not in old}
    a["v2_added_gap_rules"] = "+".join(sorted(why))
    l["live_scan_status"], l["live_dark_gap_count"], l["live_only_gap_count"] = (
        live_scan(live, archive if first else None, end, rules) if ls == "ok" else (ls, "", ""))
    return a, l


def write_table(path, rows):
    tmp = None
    try:
        with NamedTemporaryFile("w", dir=path.parent, delete=False, encoding="utf-8", newline="") as f:
            tmp = Path(f.name)
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        tmp.replace(path)
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)


def report(rows):
    ok = [r for r in rows if r["archive_status"] == "ok"]
    big = [r for r in ok if r["rise_ft"] >= 20]
    print("Archive cache/status counts:", dict(Counter(r["archive_status"] for r in rows)))
    print("Live cache/status counts:", dict(Counter(r["live_status"] for r in rows)))
    print("Five-line Hour 48 note")
    print(f"1. {len(rows)} pilot rows in seven dev floods; {len(ok)} verified archive results.")
    unresolved = len(rows) - len(ok)
    mismatch = False
    for v in (1, 2):
        dark = f"v{v}_dark1h"
        label = f"v{v}_live_class"
        n = sum(r[dark] for r in big)
        classified = [r for r in ok if r[label] in CLASSES]
        wrong = sum(r[label] in WRONG for r in classified)
        unknown = sum(r[label] == "UNRESOLVED" for r in ok)
        no_record = sum(r[label] == "NO_LIVE_DATA" for r in ok)
        unresolved += unknown
        mismatch |= (n, len(big), wrong, len(classified)) != (28, 116, 16, 33)
        print(f"{v+1}. Archive v{v}: {n}/{len(big)} dark at recomputed rise >=20 ft "
              f"(pilot 28/116); live: {wrong}/{len(classified)} wrong-but-alive among classified "
              f"dark gauges of all rises (pilot 16/33); {unknown} unresolved, {no_record} no live record.")
    def identity(r):
        return f"{r['event']}/{r['site']}"
    archive_diff = [identity(r) for r in ok if r["v1_dark1h"] != int(r["pilot_dark1h"])]
    rise_diff = [identity(r) for r in ok if (r["rise_ft"] >= 20) != (float(r["pilot_rise_ft"]) >= 20)]
    paired = [r for r in ok if r["v1_live_class"] in CLASSES and r["pilot_live_class"] in CLASSES]
    live_diff = [r for r in paired if r["pilot_live_class"] != r["v1_live_class"]]
    changes = Counter(r["v2_added_gap_rules"] for r in ok if r["v1_dark1h"] != r["v2_dark1h"])
    print(f"4. Paired v1 disagreements: dark flag {len(archive_diff)}/{len(ok)}, "
          f"big-rise bin {len(rise_diff)}/{len(ok)}, live class {len(live_diff)}/{len(paired)}; "
          f"gauges newly dark under v2 by rule: {dict(changes)}.")
    if unresolved:
        print("5. Incomplete comparison: missing or unverified inputs limit the denominators. "
              "Check the row-level cache details before interpreting differences.")
    elif mismatch or archive_diff or live_diff or rise_diff:
        print("5. Review the paired differences and v2 gap rules before attributing differences to revisions.")
    else:
        print("5. Both pilot fractions and the paired v1 results agree.")
    for name, keys in (("v1 archive flag", archive_diff), ("rise bin", rise_diff)):
        if keys:
            print(f"{name} differs for: {', '.join(keys)}")
    for r in live_diff:
        print(f"{identity(r)}: pilot {r['pilot_live_class']} -> v1 {r['v1_live_class']}; "
              f"hand review {r['reviewed_live_class'] or 'unavailable'}.")
    return 2 if unresolved else 0


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path,
                        help="RadioSilence folder containing the pilot data and Hour 47 code")
    parser.add_argument("--output-dir", type=Path, default=root / "data",
                        help="Defaults to the data folder next to this script's code folder")
    args = parser.parse_args()
    project = args.project or (root if (root / "code/run_live_census.py").is_file()
                               else Path.home() / "Downloads/RadioSilence")
    data = project.resolve() / "data"
    if not (data.parent / "code/run_live_census.py").is_file():
        raise ValueError("Use --project to select the RadioSilence checkout with the Hour 47 code")
    print(f"Reading {data}; writing {args.output_dir.resolve()}")
    sys.path.insert(0, str(data.parent / "code"))
    import run_live_census as rules
    from run_census_v1v2 import EVENTS

    windows = {e: tuple(rules.utc_ms(t) for t in span) for e, span in EVENTS.items()}
    pilot, labels = roster(data, windows)
    review_path = data / "my_live_labels.csv"
    reviews = index(read_rows(review_path)) if review_path.is_file() else {}
    mapping = json.loads((data / "usgs_to_nwsli_map.json").read_text(encoding="utf-8-sig"))
    if any(not re.fullmatch(r"[A-Z0-9]+", station) for station in mapping.values()):
        raise ValueError("Invalid NWS station ID in pilot crosswalk")
    uses = Counter((event, mapping.get(site)) for event, site in pilot)
    multi = set()
    bulk_queries = {}
    selected_counts = {}
    for event in windows:
        path = data / "raw" / event / "_pull_summary.json"
        if path.is_file():
            summary = json.loads(path.read_text(encoding="utf-8-sig"))
            if summary["event"] != event:
                raise ValueError(f"Wrong event in {path}")
            choices = summary.get("multi_series_sites", {})
            multi.update((event, site) for site in choices)
            query_start, query_end = (rules.utc_ms(summary[field]) for field in ("start", "end"))
            bulk_queries[event] = query_start, query_end
            if query_start > windows[event][0] or query_end < windows[event][1]:
                print(f"{event}: bulk USGS request {summary['start']} .. {summary['end']}; "
                      f"pilot needs {EVENTS[event][0]} .. {EVENTS[event][1]}")
            if not summary.get("pull_warnings"):
                for site, choice in choices.items():
                    selected_counts[event, site] = choice["series"][choice["chosen"]]["n_readings"]
    archives, lives = [], []
    for key, row in sorted(pilot.items()):
        event, site = key
        station = mapping.get(site, "")
        query = (*bulk_queries[event], selected_counts.get(key)) if event in bulk_queries else None
        a, l = process(data, key, row, labels.get(key, {}), reviews.get(key, {}).get("my_class", ""),
                       windows[event], station, uses[event, station] > 1, key in multi, query, rules)
        archives.append(a)
        lives.append(l)
    arch, live = index(archives), index(lives)
    if arch.keys() != live.keys() or arch.keys() != pilot.keys():
        raise ValueError("Development tables do not have the same event/site keys")
    merged = [a | live[key] for key, a in arch.items()]
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    for name, rows in (("census_archive_dev", archives), ("census_live_dev", lives), ("census_dev_merged", merged)):
        write_table(out / f"{name}.csv", rows)
    return report(merged)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ImportError, KeyError, ValueError) as error:
        sys.exit(f"Cannot run development census: {error}")
