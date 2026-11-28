"""Hour 38: build data/site_meta.csv from the completed test-flood census."""

import calendar
import csv
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import urlencode, urljoin

# Python's -I option removes the script directory from the import path.
CODE = Path(__file__).resolve().parent
sys.path.insert(0, str(CODE))
from gd_fetch import _get  # Existing USGS helper with network and rate-limit retries.

DATA = CODE.parent / "data"
CACHE = DATA / "raw" / "_hour38_cache"
OUTPUT = DATA / "site_meta.csv"
BASE = "https://api.waterdata.usgs.gov/ogcapi/v1/collections"
FEET = {"ft", "feet", "foot"}
DATUM_FLAGS = {"DIFFDATUM", "DATUMCHANGE"}

FIELDS = [
    "event", "site", "event_start", "stage_series",
    "state", "huc", "latitude", "longitude", "drainage_area_sqmi",
    "op_min_ft", "op_max_ft", "flood_stage_ft",
    "prior_record_ft", "prior_peak_candidate_ft", "prior_record_date",
    "prior_peak_series", "prior_peak_qualifier", "notes",
]


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def number(value):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def features(collection, params, headers):
    query = urlencode({"f": "json", "limit": 1000, **params})
    url = f"{BASE}/{collection}/items?{query}"
    visited = set()
    result = []

    while url:
        if url in visited:
            raise RuntimeError(f"Repeated page in {collection}: {params}")
        visited.add(url)

        page = json.loads(_get(url, headers))
        result.extend(page["features"])
        following = next(
            (link["href"] for link in page.get("links", [])
             if link.get("rel") == "next"),
            None,
        )
        if following:
            url = urljoin(url, following)
        else:
            total = page.get("numberMatched")
            if isinstance(total, int) and total != len(result):
                raise RuntimeError(
                    f"{collection}: expected {total} records, got {len(result)}"
                )
            break

    return result


def site_data(site, headers):
    path = CACHE / f"{site}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))

    station = f"USGS-{site}"
    locations = features("monitoring-locations", {"id": station}, headers)
    params = {"monitoring_location_id": station, "parameter_code": "00065"}
    series = features("time-series-metadata", params, headers)
    peaks = features("peaks", params, headers)

    if len(locations) > 1 or any(f["id"] != station for f in locations):
        raise ValueError(f"Unexpected monitoring-location records for {station}")

    for feature in series + peaks:
        props = feature["properties"]
        if (props["monitoring_location_id"] != station
                or props["parameter_code"] != "00065"):
            raise ValueError(f"Unexpected site or parameter for {station}")

    payload = {
        "location": locations[0] if locations else {},
        "series": {f["id"]: f["properties"] for f in series},
        "peaks": [f["properties"] for f in peaks],
    }
    # A completed cache file contains all three responses for this site.
    with NamedTemporaryFile("w", dir=CACHE, delete=False, encoding="utf-8") as f:
        json.dump(payload, f, separators=(",", ":"))
        tmp = Path(f.name)
    tmp.replace(path)
    return payload


def threshold_kind(entry):
    label = " ".join(str(entry.get(k) or "") for k in ("Name", "ReferenceCode"))
    label = label.lower()

    if "operational" in label or "equipment limit" in label:
        if re.search(r"\b(min(?:imum)?|low|lower)\b", label):
            return "op_min_ft"
        if re.search(r"\b(max(?:imum)?|high|upper)\b", label):
            return "op_max_ft"
        if "equipment limit" in label:
            direction = str(entry.get("Type") or "").lower()
            return {
                "thresholdabove": "op_max_ft",
                "thresholdbelow": "op_min_ft",
            }.get(direction)

    if re.search(r"flood\s*stage", label):
        if not re.search(r"\b(action|moderate|major|record)\b", label):
            return "flood_stage_ft"
    return None


def instant(text):
    value = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if value.tzinfo is None:
        raise ValueError(f"Threshold timestamp lacks a timezone: {text}")
    return value


def thresholds(series, start, stop, notes):
    fields = {"op_min_ft": None, "op_max_ft": None, "flood_stage_ft": None}
    if not series or str(series.get("unit_of_measure")).lower() not in FEET:
        notes.add("selected stage series unavailable or units not feet")
        return fields

    entries = series.get("thresholds") or []
    if isinstance(entries, str):
        entries = json.loads(entries)

    values = defaultdict(set)
    for entry in entries or []:
        field = threshold_kind(entry)
        if not field:
            continue

        for period in entry.get("Periods") or []:
            value = number(period.get("ReferenceValue"))
            if value is None:
                continue

            begin = period.get("StartTime")
            if not begin:
                notes.add(f"{field}: missing effective start")
                continue

            left = instant(begin)
            finish = period.get("EndTime")
            right = instant(finish) if finish else None

            if start < left < stop or (right is not None and start < right < stop):
                notes.add(f"{field}: period boundary during flood")

            if left <= start and (right is None or start < right):
                values[field].add(value)
                if begin.startswith("0001-"):
                    notes.add(f"{field}: undated effective start")
                applied = period.get("AppliedTime")
                if applied and instant(applied) > start:
                    notes.add(f"{field}: entered after event start")

    for field, candidates in values.items():
        if len(candidates) == 1:
            fields[field] = next(iter(candidates))
        else:
            notes.add(f"{field}: conflicting values, review")

    return fields


def peak_date(record):
    """Return the latest possible date and a label preserving its precision."""
    year = record.get("year")
    if not year:
        return None, ""

    year = int(year)
    month = record.get("month")
    if not month:
        return date(year, 12, 31), str(year)

    month = int(month)
    day = record.get("day")
    if not day:
        last = calendar.monthrange(year, month)[1]
        return date(year, month, last), f"{year:04}-{month:02}"

    exact = date(year, month, int(day))
    return exact, exact.isoformat()


def qualifier_text(value):
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return str(value or "")


def prior_peak(payload, selected_id, cutoff, notes):
    annual = {
        sid: props for sid, props in payload["series"].items()
        if str(props.get("computation_identifier") or "").lower() == "max at event time"
        and str(props.get("computation_period_identifier") or "").lower() == "water year"
        and str(props.get("unit_of_measure") or "").lower() in FEET
    }
    linked = {
        sid for sid, props in annual.items()
        if props.get("parent_time_series_id") == selected_id
    }

    if linked:
        eligible = linked
    elif len(annual) == 1 and not next(iter(annual.values())).get("parent_time_series_id"):
        eligible = set(annual)
        notes.add("sole annual stage series has no parent link")
    else:
        notes.add("no comparable annual stage series identified")
        return {}

    candidates = []
    for peak in payload["peaks"]:
        sid = peak.get("time_series_id")
        if sid not in eligible:
            continue
        if str(peak.get("unit_of_measure") or "").lower() not in FEET:
            continue

        value = number(peak.get("value"))
        latest, label = peak_date(peak)
        if value is None or latest is None or latest >= cutoff:
            continue

        qualifier = qualifier_text(peak.get("qualifier"))
        codes = set(re.findall(r"[A-Z]+", qualifier.upper()))
        candidates.append((value, label, sid, qualifier, codes & DATUM_FLAGS))

    if not candidates:
        notes.add("no eligible peak definitely before event start")
        return {}

    maximum = max(row[0] for row in candidates)
    winners = [row for row in candidates if row[0] == maximum]
    flagged = [row for row in winners if row[4]]

    # Preserve a flagged observation as evidence if any tied maximum needs review.
    # Otherwise report the earliest date label among the tied maximum observations.
    chosen = min(flagged or winners, key=lambda row: (row[1], row[2], row[3]))
    if flagged:
        flags = sorted(set().union(*(row[4] for row in flagged)))
        notes.add(f"prior peak needs datum review: {', '.join(flags)}")
    if len(winners) > 1:
        notes.add(f"{len(winners)} observations tied for highest prior peak")

    return {
        "prior_record_ft": None if flagged else maximum,
        "prior_peak_candidate_ft": maximum,
        "prior_record_date": chosen[1],
        "prior_peak_series": chosen[2],
        "prior_peak_qualifier": chosen[3],
    }


def census_inputs():
    events = {
        row["event"]: row for row in read_csv(DATA / "events.csv")
        if row["dev_or_test"] == "test"
    }
    latest = {}
    for row in read_csv(DATA / "raw" / "_census_log.csv"):
        if row["event"] in events and row["site"]:
            latest[row["event"], row["site"]] = row

    by_site = defaultdict(list)
    for row in latest.values():
        if row["site_type"] == "ST" and row["status"] == "ok":
            by_site[row["site"]].append(row)

    if not by_site:
        raise SystemExit("No successful test-event stream gauges in the census log.")
    return events, by_site


def print_coverage(rows):
    events_per_site = Counter(row["site"] for row in rows)
    covered_per_site = Counter(
        row["site"] for row in rows if row.get("prior_record_ft") is not None
    )
    covered_events = sum(covered_per_site.values())
    total_sites = len(events_per_site)
    any_covered = len(covered_per_site)
    all_covered = sum(
        covered_per_site[site] == count for site, count in events_per_site.items()
    )

    print(f"Saved {OUTPUT}")
    print(f"Output: {len(rows):,} gauge-events across {total_sites:,} distinct gauges.")
    print(f"Gauge-events with a prior record: {covered_events:,}/{len(rows):,} "
          f"({covered_events / len(rows):.1%}).")
    print(f"Distinct gauges with a prior record for at least one event: "
          f"{any_covered:,}/{total_sites:,} ({any_covered / total_sites:.1%}).")
    print(f"Distinct gauges with a prior record for every one of their events: "
          f"{all_covered:,}/{total_sites:,} ({all_covered / total_sites:.1%}).")
    datum_review = sum(
        row.get("prior_peak_candidate_ft") is not None
        and row.get("prior_record_ft") is None
        for row in rows
    )
    print(f"Gauge-events with a candidate held for datum review: {datum_review:,}.")


def main():
    key = os.environ.get("USGS_API_KEY")
    if not key:
        raise SystemExit("USGS_API_KEY is missing in this PowerShell session.")

    events, by_site = census_inputs()
    headers = {"X-Api-Key": key}
    CACHE.mkdir(parents=True, exist_ok=True)
    rows = []

    for index, site in enumerate(sorted(by_site), 1):
        if index == 1 or index % 25 == 0:
            print(f"Gauge {index:,}/{len(by_site):,}: {site}", flush=True)
        try:
            payload = site_data(site, headers)
            location = payload["location"]
            props = location.get("properties") or {}
            coords = (location.get("geometry") or {}).get("coordinates") or [None, None]

            for logged in by_site[site]:
                event = events[logged["event"]]
                cutoff = date.fromisoformat(event["start"])
                start = datetime.combine(cutoff, time.min, timezone.utc)
                end_day = date.fromisoformat(event["end"]) + timedelta(days=1)
                stop = datetime.combine(end_day, time.min, timezone.utc)

                selected = logged["series_kept"]
                notes = set()
                if not location:
                    notes.add("missing monitoring location")
                limits = thresholds(payload["series"].get(selected), start, stop, notes)
                peak = prior_peak(payload, selected, cutoff, notes)
                rows.append({
                    "event": logged["event"],
                    "site": site,
                    "event_start": cutoff,
                    "stage_series": selected,
                    "state": props.get("state_name"),
                    "huc": props.get("hydrologic_unit_code"),
                    "latitude": coords[1],
                    "longitude": coords[0],
                    "drainage_area_sqmi": props.get("drainage_area"),
                    **limits,
                    **peak,
                    "notes": " | ".join(sorted(notes)),
                })
        except Exception as exc:
            raise RuntimeError(f"Hour 38 stopped at USGS site {site}.") from exc

    rows.sort(key=lambda row: (row["event"], row["site"]))
    with NamedTemporaryFile("w", dir=DATA, delete=False,
                            encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
        tmp = Path(f.name)

    # Publish the finished CSV only after all sites have been processed.
    tmp.replace(OUTPUT)
    print_coverage(rows)


if __name__ == "__main__":
    main()