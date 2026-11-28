import argparse
import csv
import math
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path


DATA = Path(__file__).resolve().parents[1] / "data"
UTC = timezone.utc
MINUTE = timedelta(minutes=1)


def read_rows(path):
    with path.open(encoding="utf-8-sig", newline="") as source:
        yield from csv.DictReader(source)


def utc_time(text):
    stamp = datetime.fromisoformat(text.strip().replace("Z", "+00:00"))
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=UTC)
    return stamp.astimezone(UTC)


def utc_label(stamp):
    return stamp.strftime("%Y-%m-%dT%H:%MZ")


def event_gauges():
    latest = {}
    for row in read_rows(DATA / "raw" / "_census_log.csv"):
        event = row["event"].strip()
        site = row["site"].strip()
        key = (event, site)
        logged = utc_time(row["logged_at_utc"])
        if key not in latest or logged >= latest[key][0]:
            latest[key] = (logged, row)

    by_event = defaultdict(set)
    for (event, site), (_, row) in latest.items():
        site_type = row["site_type"].strip().upper()
        status = row["status"].strip().lower()
        if site_type == "ST" and status == "ok":
            by_event[event].add(site)
    return by_event


def station_mapping():
    mapping = {}
    for row in read_rows(DATA / "census_nwsli.csv"):
        station = row["nwsli"].strip().upper()
        if row["mapping_status"].strip().lower() == "mapped" and station:
            mapping[row["site"].strip()] = station
    return mapping


def valid_readings(path):
    with path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        if not {"time_utc", "value_ft"}.issubset(reader.fieldnames or []):
            raise ValueError(f"{path}: expected columns time_utc and value_ft")

        readings = set()
        for row in reader:
            try:
                value = float(row["value_ft"] or "")
            except ValueError:
                continue
            if math.isfinite(value):
                readings.add(utc_time(row["time_utc"]))
    return sorted(readings)


def infer_cadence(readings):
    gaps = Counter()
    for previous, current in zip(readings, readings[1:]):
        minutes = math.floor((current - previous) / MINUTE + 0.5)
        if minutes >= 1:
            gaps[minutes] += 1

    if not gaps:
        return None
    minutes, count = gaps.most_common(1)[0]
    if count >= 2 and 2 * count > len(readings) - 1:
        return minutes
    return None


def add_interval(changes, start, stop, event_start):
    """Count UTC minute marks in [start, stop), clipped to the event."""
    left = max(0, math.ceil((start - event_start) / MINUTE))
    right = min(len(changes) - 1, math.ceil((stop - event_start) / MINUTE))
    if left < right:
        changes[left] += 1
        changes[right] -= 1


def count_event(event, start, stop, sites, mapping, cadence_override, grace, writer):
    minutes = int((stop - start) / MINUTE)
    known_changes = [0] * (minutes + 1)
    silent_changes = [0] * (minutes + 1)
    station_uses = Counter(mapping[site] for site in sites if site in mapping)
    folder = DATA / "live" / event
    files = {path.stem.upper(): path for path in folder.glob("*.csv")}
    usable = 0

    for site in sorted(sites):
        station = mapping.get(site)
        # A shared live series cannot independently confirm two gauges.
        if station not in files or station_uses[station] != 1:
            continue

        readings = valid_readings(files[station])
        if not readings:
            continue
        cadence = cadence_override or infer_cadence(readings)
        if cadence is None:
            continue

        allowed = timedelta(minutes=cadence + grace)
        if readings[0] >= stop or readings[-1] + allowed <= start:
            continue

        usable += 1
        add_interval(known_changes, readings[0], readings[-1] + allowed, start)

        for previous, following in zip(readings, readings[1:]):
            due = previous + allowed
            if due < following:
                add_interval(silent_changes, due, following, start)

    total = len(sites)
    needed = (4 * total + 4) // 5  # Round 80% of the gauge count up.
    known = silent = peak = excluded = unresolved = episodes = 0
    previous_flag = False
    peak_time = ""

    for index in range(minutes):
        known += known_changes[index]
        silent += silent_changes[index]
        unknown = total - known
        stamp = utc_label(start + index * MINUTE)
        flagged = silent >= needed
        uncertain = not flagged and silent + unknown >= needed

        if silent > peak or index == 0:
            peak, peak_time = silent, stamp
        excluded += int(flagged)
        unresolved += int(uncertain)
        episodes += int(flagged and not previous_flag)
        previous_flag = flagged

        writer.writerow([
            event, stamp, total, known - silent, silent, unknown,
            needed, int(flagged), int(uncertain),
        ])

    print(
        f"{event}: {usable}/{total} gauges with usable live data, "
        f"peak {peak}/{total} confirmed silent, "
        f"{excluded} minutes excluded in {episodes} outage periods, "
        f"{unresolved} minutes unresolved."
    )
    return [
        event, total, usable, needed, peak, peak_time,
        excluded, episodes, unresolved,
    ]


def main():
    parser = argparse.ArgumentParser(description="Hour 42 archive outage check")
    parser.add_argument("--cadence-minutes", type=int)
    parser.add_argument("--grace-minutes", type=int, default=0)
    args = parser.parse_args()
    if args.cadence_minutes is not None and args.cadence_minutes < 1:
        parser.error("--cadence-minutes must be positive")
    if args.grace_minutes < 0:
        parser.error("--grace-minutes must be zero or greater")

    gauges = event_gauges()
    events = []
    for row in read_rows(DATA / "events.csv"):
        if row["dev_or_test"].strip().lower() != "test":
            continue
        event = row["event"].strip()
        start = utc_time(row["start"])
        stop = utc_time(row["end"]) + timedelta(days=1)
        if stop <= start:
            raise SystemExit(f"Invalid date range for event {event!r}")
        events.append((event, start, stop))

    if not events:
        raise SystemExit("No test events found in events.csv.")

    unmatched = [event for event, _, _ in events if not gauges.get(event)]
    if unmatched:
        raise SystemExit(
            "No eligible census gauges matched these event names: "
            + ", ".join(repr(event) for event in unmatched)
        )

    mapping = station_mapping()
    minute_path = DATA / "hour42_outage_minutes.csv"
    summary_path = DATA / "hour42_outage_summary.csv"

    with minute_path.open("w", encoding="utf-8", newline="") as minute_file, \
         summary_path.open("w", encoding="utf-8", newline="") as summary_file:
        minute_writer = csv.writer(minute_file)
        summary_writer = csv.writer(summary_file)
        minute_writer.writerow([
            "event", "minute_utc", "event_gauges", "gauges_live",
            "gauges_confirmed_silent", "gauges_unknown", "gauges_needed_for_80pct",
            "exclude_from_gauge_failures", "threshold_unresolved",
        ])
        summary_writer.writerow([
            "event", "event_gauges", "gauges_with_usable_live_series",
            "gauges_needed_for_80pct", "peak_simultaneously_silent",
            "first_peak_minute_utc", "excluded_minutes", "outage_periods",
            "unresolved_minutes",
        ])

        for event, start, stop in events:
            result = count_event(
                event, start, stop, gauges[event], mapping,
                args.cadence_minutes, args.grace_minutes, minute_writer,
            )
            summary_writer.writerow(result)


if __name__ == "__main__":
    main()