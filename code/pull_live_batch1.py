"""Download IEM HADS CSVs for one of the two gauge batches per event."""

import argparse
import csv
import re
from collections import Counter, defaultdict
from datetime import date, datetime, time, timezone
from email.utils import parsedate_to_datetime
from http.client import HTTPException
from pathlib import Path, PureWindowsPath
import sys
from tempfile import NamedTemporaryFile
from time import sleep
from urllib.error import HTTPError

CODE = Path(__file__).resolve().parent
DATA = CODE.parent / "data"
PAUSE_SECONDS = 2.5

# Python's -I option removes the script directory from the import path.
sys.path.insert(0, str(CODE))
from gd_fetch import iem_hads

try:
    from ntpath import isreserved
except ImportError:
    # Keep the Windows device-name check working on older Python versions.
    def isreserved(name):
        return PureWindowsPath(name).is_reserved()


def read_csv(path, required_columns, alternate_columns=()):
    with path.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        fields = set(reader.fieldnames or ())
        missing = set(required_columns) - fields
        if alternate_columns and not fields.intersection(alternate_columns):
            missing.add(" or ".join(alternate_columns))
        if missing:
            raise ValueError(f"{path.name} is missing columns: {', '.join(sorted(missing))}")
        return list(reader)


def utc_bound(value, end=False):
    value = (value or "").strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        # A date-only end includes the whole last UTC day.
        clock = time.max if end else time.min
        return datetime.combine(date.fromisoformat(value), clock, timezone.utc)
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    timestamp = datetime.fromisoformat(value)
    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(timezone.utc)


def mapped_event_stations(data, events):
    mapping = read_csv(data / "census_nwsli.csv", ("nwsli",), ("event", "site"))
    mapped = [
        row for row in mapping
        if row.get("mapping_status", "mapped") == "mapped" and (row["nwsli"] or "").strip()
    ]
    if not mapped:
        return
    if "event" in mapped[0]:
        for row in mapped:
            yield row["event"], row["nwsli"]
        return

    stations_by_site = {row["site"]: row["nwsli"] for row in mapped}
    latest = {}
    for row in read_csv(data / "raw" / "_census_log.csv", ("event", "site", "site_type", "status")):
        event, site = row["event"], row["site"]
        if site in stations_by_site and event in events and events[event].get("dev_or_test", "test") == "test":
            latest[event, site] = row
    for (event, site), row in latest.items():
        if row["site_type"] == "ST" and row["status"] == "ok":
            yield event, stations_by_site[site]


def batch_jobs(data, batch=1):
    windows = {}
    events = {}
    for row in read_csv(data / "events.csv", ("event", "start", "end")):
        event = (row["event"] or "").strip()
        if (not event or re.search(r'[<>:"/\\|?*\x00-\x1f]', event)
                or event.endswith(".") or isreserved(event)):
            raise ValueError(f"Invalid event folder name in events.csv: {event!r}")
        if event in windows:
            raise ValueError(f"Duplicate event in events.csv: {event}")
        try:
            start, end = utc_bound(row["start"]), utc_bound(row["end"], end=True)
        except ValueError as exc:
            raise ValueError(f"Invalid start or end in events.csv for {event}: {exc}") from exc
        if end <= start:
            raise ValueError(f"Event end must follow its start: {event}")
        windows[event] = start, end
        events[event] = row

    stations_by_event = defaultdict(set)
    for event, station in mapped_event_stations(data, events):
        event = (event or "").strip()
        station = station.strip().upper()
        if event not in windows:
            raise ValueError(f"Mapped station {station} has no event window for {event!r}")
        if not re.fullmatch(r"[A-Z0-9]+", station):
            raise ValueError(f"Invalid NWSLI for {event}: {station!r}")
        stations_by_event[event].add(station)

    return [
        (event, station, *windows[event])
        for event, stations in sorted(stations_by_event.items())
        for station in sorted(stations)[batch - 1::2]
    ]


def rate_limit_pause(error):
    retry_after = error.headers.get("Retry-After", "") if error.headers else ""
    if retry_after.isdecimal():
        return max(PAUSE_SECONDS, int(retry_after))
    if retry_after:
        try:
            resume_at = parsedate_to_datetime(retry_after).astimezone(timezone.utc)
            return max(PAUSE_SECONDS, (resume_at - datetime.now(timezone.utc)).total_seconds())
        except (ValueError, TypeError, OverflowError):
            pass
    return 5.0


def save_csv(destination, rows):
    destination.parent.mkdir(parents=True, exist_ok=True)
    file = NamedTemporaryFile(
        "w", encoding="utf-8", newline="", dir=destination.parent, suffix=".tmp", delete=False
    )
    temporary = Path(file.name)
    try:
        with file:
            writer = csv.writer(file)
            writer.writerow(("time_utc", "value_ft"))
            writer.writerows(rows)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DATA,
                        help="Directory containing events.csv, census_nwsli.csv, and the census log")
    parser.add_argument("--batch", type=int, choices=(1, 2), default=1,
                        help="Download the first or second half of each event")
    parser.add_argument("--dry-run", action="store_true",
                        help="List selected CSV paths without contacting IEM")
    args = parser.parse_args()
    try:
        jobs = batch_jobs(args.data_dir, args.batch)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Cannot prepare batch {args.batch}: {exc}\n")

    if not jobs:
        parser.exit(1, f"Cannot prepare batch {args.batch}: no mapped gauge-events were found.\n")
    n_events = len({event for event, _, _, _ in jobs})
    print(f"Batch {args.batch}: {len(jobs):,} mapped gauge-events across {n_events} events.", flush=True)
    counts = Counter()
    pause = 0
    for index, (event, station, start, end) in enumerate(jobs, 1):
        relative_path = Path("live") / event / f"{station}.csv"
        destination = args.data_dir / relative_path
        prefix = f"[{index}/{len(jobs)}] {relative_path.as_posix()}"
        if args.dry_run:
            print(prefix)
            continue
        if destination.is_file() and destination.stat().st_size > 0:
            counts["existing"] += 1
            print(f"{prefix}: already saved", flush=True)
            continue

        if pause:
            sleep(pause)
        # iem_hads already pauses after a CSV response. It returns early on no results.
        pause = PAUSE_SECONDS
        try:
            rows = iem_hads(
                station,
                start.isoformat().replace("+00:00", "Z"),
                end.isoformat().replace("+00:00", "Z"),
            )
            if not rows:
                counts["no record"] += 1
                print(f"{prefix}: no live record", flush=True)
                continue
            pause = 0
            save_csv(destination, rows)
        except (OSError, ValueError, HTTPException) as exc:
            if isinstance(exc, HTTPError) and exc.code == 429:
                pause = rate_limit_pause(exc)
            counts["failed"] += 1
            print(f"{prefix}: failed ({exc})", file=sys.stderr, flush=True)
        else:
            counts["saved"] += 1
            print(f"{prefix}: saved", flush=True)

    if not args.dry_run:
        print(f"Batch {args.batch} complete: {counts['saved']} saved, {counts['existing']} already saved, "
              f"{counts['no record']} no live record, {counts['failed']} failed.", flush=True)
    return int(counts["failed"] > 0)


if __name__ == "__main__":
    raise SystemExit(main())
