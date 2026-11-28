"""Hour 47: classify archive gaps and scan live feeds using archive rule v2.

Writes one row per gauge-event to data/census_live.csv.
JSON columns preserve individual gap results.
"""

import csv
import json
import math
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile

CODE = Path(__file__).resolve().parent
DATA = CODE.parent / "data"
sys.path.insert(0, str(CODE))

from gd_gaps import analyze, regular_series
from gd_live import NoLiveData, classify
from run_census import load as load_archive

UTC = timezone.utc
EXTRA = [
    "nwsli", "mapping_status", "live_data_status", "live_readings",
    "crest_source", "live_class", "archive_gap_results_json",
    "live_gap_status", "live_dark_gap_count", "live_only_gap_count",
    "live_gap_results_json", "review_note",
]


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as source:
        return list(csv.DictReader(source))


def indexed(rows, keys):
    result = {}
    for row in rows:
        key = tuple(row[name].strip() for name in keys)
        if key in result:
            raise ValueError(f"Duplicate key: {key}")
        result[key] = row
    return result


def utc_ms(text):
    stamp = datetime.fromisoformat(text.strip().replace("Z", "+00:00"))
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=UTC)
    return round(stamp.timestamp() * 1000)


def utc_label(time):
    return datetime.fromtimestamp(time / 1000, UTC).isoformat().replace(
        "+00:00", "Z"
    )


def pilot_code(code):
    status, _, qualifiers = (code or "").partition("|")
    status = status.strip()
    if status.lower().startswith("approved"):
        base = "A"
    elif status.lower().startswith("provisional"):
        base = "P"
    else:
        return status
    return base + (" e" if "ESTIMATED" in qualifiers.upper() else "")


def gap_details(gap):
    return {
        "start_utc": utc_label(gap.start),
        "end_utc": utc_label(gap.end),
        "hours": (gap.end - gap.start) / 3_600_000,
        "open_end": gap.open_end,
        "spans_peak": gap.spans_peak,
        "in_rise": gap.in_rise,
    }


def get_live(event, site, mapping, uses, start, end):
    entry = mapping.get((site,))
    if entry is None:
        return [], "", "missing", "UNRESOLVED", "Missing crosswalk entry."

    station = entry["nwsli"].strip().upper()
    status = entry["mapping_status"].strip().lower()
    if status == "unmapped":
        return [], "", status, "NO_LIVE_DATA", "No mapped NWS station ID."
    if status != "mapped" or not station or uses[event, station] > 1:
        return [], station, status, "UNRESOLVED", "Review station mapping."

    path = DATA / "live" / event / f"{station}.csv"
    if not path.is_file():
        return [], station, status, "UNRESOLVED", f"Missing live file: {path}"

    values = {}
    try:
        for row in read_csv(path):
            time = utc_ms(row["time_utc"])
            raw = (row["value_ft"] or "").strip()
            if not start <= time <= end or not raw:
                continue
            value = float(raw)
            if not math.isfinite(value):
                continue
            if time in values and values[time] != value:
                raise ValueError(f"Conflicting stages at {utc_label(time)}")
            values[time] = value
    except (OSError, ValueError, KeyError) as error:
        return [], station, status, "UNRESOLVED", str(error)

    records = [(time, value, "") for time, value in sorted(values.items())]
    if not records:
        return (
            [], station, status, "NO_LIVE_DATA",
            "Saved file has no numeric stage readings in the event window.",
        )
    return records, station, status, "ok", ""


def process(row, window, mapping, uses):
    event, site = row["event"], row["site"]
    start, end = window
    archive = [
        (time, value, pilot_code(code))
        for time, value, code in load_archive(
            str(DATA / "raw" / event / f"{site}.csv")
        )
    ]
    if any(time < start or time > end for time, _, _ in archive):
        raise ValueError("Archive timestamps fall outside the event window.")
    if any(value is not None and not math.isfinite(value)
           for _, value, _ in archive):
        raise ValueError("Non-finite archive stage.")

    result = analyze(archive, version=2, window_end_ms=end)
    gaps = result.dark_gaps if result else []
    if result is None:
        if row["status"] != "too_few_readings":
            raise ValueError("Archive status differs from Hour 46.")
    else:
        expected = {
            "n_readings": result.n,
            "n_dark_gaps": len(gaps),
            "dark1h": int(result.dark1),
            "dark3h": int(result.dark3),
        }
        if row["status"] != "ok" or any(
            int(row[name]) != value for name, value in expected.items()
        ):
            raise ValueError("Archive results differ from Hour 46.")
        if abs(float(row["max_ft"]) - result.max_ft) > 1e-9:
            raise ValueError("Archive maximum differs from Hour 46.")

    live, station, mapping_status, status, note = get_live(
        event, site, mapping, uses, start, end
    )
    notes = [note] if note else []
    classified = []
    for gap in gaps:
        item = gap_details(gap)
        item["class"] = status
        if status == "ok":
            try:
                item["class"] = classify(gap, live, result.max_ft)
            except NoLiveData as error:
                item["class"] = "NO_LIVE_DATA"
                item["reason"] = str(error)
            except ValueError as error:
                item["class"] = "UNRESOLVED"
                item["reason"] = str(error)
                notes.append(str(error))
        else:
            item["reason"] = note
        classified.append(item)

    representative = ""
    if gaps:
        selected = max(
            range(len(gaps)),
            key=lambda i: (gaps[i].spans_peak, gaps[i].hours),
        )
        representative = classified[selected]["class"]

    live_gaps = []
    scan_status = status
    gap_count = only_count = ""
    if status == "ok":
        scan = analyze(live, version=2, window_end_ms=end)
        if scan is None:
            scan_status = "too_few_readings"
            notes.append("Fewer than 10 numeric readings for the live gap scan.")
        else:
            scan_status = "ok"
            regular, _, cadence = regular_series(archive)
            threshold = max(60, 3.5 * cadence) * 60_000
            missing = [
                (a[0], b[0])
                for a, b in zip(regular, regular[1:])
                if b[0] - a[0] >= threshold
            ]
            for gap in scan.dark_gaps:
                item = gap_details(gap)
                if any(a < gap.end and b > gap.start for a, b in missing):
                    relation = "ARCHIVE_GAP_OVERLAP"
                elif (
                    len(regular) < 2
                    or regular[0][0] > gap.start
                    or regular[-1][0] < gap.end
                ):
                    relation = "ARCHIVE_COVERAGE_UNKNOWN"
                else:
                    relation = "LIVE_ONLY"
                item["archive_relation"] = relation
                live_gaps.append(item)
            gap_count = len(live_gaps)
            only_count = sum(
                item["archive_relation"] == "LIVE_ONLY" for item in live_gaps
            )

    return dict(
        row,
        nwsli=station,
        mapping_status=mapping_status,
        live_data_status=status,
        live_readings=len(live),
        crest_source="archive_event_max_ft",
        live_class=representative,
        archive_gap_results_json=json.dumps(classified, separators=(",", ":")),
        live_gap_status=scan_status,
        live_dark_gap_count=gap_count,
        live_only_gap_count=only_count,
        live_gap_results_json=json.dumps(live_gaps, separators=(",", ":")),
        review_note=" | ".join(dict.fromkeys(notes)),
    )


def main():
    output = DATA / "census_live.csv"
    if output.exists():
        raise FileExistsError(f"Output already exists: {output}")

    rows = read_csv(DATA / "census_archive.csv")
    if not rows:
        raise ValueError("The archive census is empty.")
    indexed(rows, ("event", "site"))
    if any(row["archive_rule_version"].strip() != "2" for row in rows):
        raise ValueError("Expected archive rule version 2.")

    events = indexed(read_csv(DATA / "events.csv"), ("event",))
    windows = {}
    for (event,), row in events.items():
        if row["dev_or_test"].strip().lower() == "test":
            end = datetime.fromisoformat(row["end"].strip()) + timedelta(days=1)
            windows[event] = utc_ms(row["start"]), utc_ms(end.isoformat())
            if windows[event][1] <= windows[event][0]:
                raise ValueError(f"Invalid date window: {event}")
    if {row["event"] for row in rows} != set(windows):
        raise ValueError("Archive census and test-event list differ.")

    audit = DATA / "hour42_outage_summary.csv"
    if not audit.exists():
        audit = DATA / "outage_summary.csv"
    audit_rows = read_csv(audit)
    if not set(windows).issubset({row["event"] for row in audit_rows}):
        raise ValueError("Network-outage audit is missing events.")
    if any(int(row["excluded_minutes"]) > 0
           for row in audit_rows if row["event"] in windows):
        raise ValueError("Apply the recorded network-outage exclusions first.")

    mapping = indexed(read_csv(DATA / "census_nwsli.csv"), ("site",))
    uses = Counter()
    for row in rows:
        entry = mapping.get((row["site"],))
        if entry and entry["mapping_status"].strip().lower() == "mapped":
            uses[row["event"], entry["nwsli"].strip().upper()] += 1

    counts = defaultdict(Counter)
    written = notes_count = 0
    temporary = None
    try:
        with NamedTemporaryFile(
            "w", encoding="utf-8", newline="", dir=DATA,
            prefix="census_live_", suffix=".tmp", delete=False,
        ) as destination:
            temporary = Path(destination.name)
            writer = csv.DictWriter(destination, fieldnames=list(rows[0]) + EXTRA)
            writer.writeheader()
            for row in sorted(rows, key=lambda r: (r["event"], r["site"])):
                try:
                    result = process(row, windows[row["event"]], mapping, uses)
                except (OSError, ValueError, KeyError) as error:
                    raise RuntimeError(
                        f"{row['event']} / {row['site']}: {error}"
                    ) from error
                writer.writerow(result)
                written += 1
                notes_count += bool(result["review_note"])
                if result["live_class"]:
                    counts[row["event"]][result["live_class"]] += 1
                if written % 100 == 0 or written == len(rows):
                    print(f"Processed {written:,}/{len(rows):,}", flush=True)

        if written != len(rows):
            raise RuntimeError("Output row count mismatch.")
        if output.exists():
            raise FileExistsError(f"Output appeared during the run: {output}")
        os.replace(temporary, output)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)

    print("\nClasses per event, using the representative archive gap:")
    for event in sorted(windows):
        tally = counts[event]
        text = ", ".join(f"{label}={n}" for label, n in sorted(tally.items()))
        print(f"{event}: {text or 'No archive-dark gauges'}")
        if tally and set(tally) == {"IMPLAUSIBLE"}:
            print("  CHECK UNITS AND DATUM: all classes are IMPLAUSIBLE.")

    print(f"\nSaved {output}")
    print(f"Events: {len(windows)}")
    print(f"Expected rows: {len(rows):,}")
    print(f"Written rows: {written:,}")
    print("Row count: PASS")
    print(f"Rows with notes: {notes_count:,}")


if __name__ == "__main__":
    main()