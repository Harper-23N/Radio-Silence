"""Fill the existing Hour 38 cache in batches, then build data/site_meta.csv."""
import argparse
import http.client
import json
import os
import sys
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parent))
import site_meta as hour38

PAGE_SIZE = 10000
BATCH_SIZE = 25
LOC = "monitoring-locations"
META = "time-series-metadata"


def retry_delay(header, attempt):
    if header:
        if header.strip().isdigit():
            return max(1, int(header))
        try:
            when = parsedate_to_datetime(header)
            return max(1, int((when - datetime.now(timezone.utc)).total_seconds()) + 1)
        except (ValueError, TypeError, OverflowError):
            pass
    return min(300, 15 * 2 ** attempt)


def post_page(collection, query, headers):
    request = Request(
        f"{hour38.BASE}/{collection}/items?f=json&limit={PAGE_SIZE}",
        data=json.dumps(query).encode("utf-8"),
        headers={**headers, "Content-Type": "application/query-cql-json",
                 "Accept": "application/geo+json, application/json"},
        method="POST",
    )
    for attempt in range(8):
        try:
            with urlopen(request, timeout=120) as response:
                return json.load(response)
        except HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt == 7:
                raise
            delay = retry_delay(exc.headers.get("Retry-After"), attempt)
            reason = f"HTTP {exc.code}"
        except (URLError, TimeoutError, ConnectionError, http.client.HTTPException) as exc:
            if attempt == 7:
                raise
            delay = retry_delay(None, attempt)
            reason = type(exc).__name__
        print(f"{reason}; retrying in {delay} seconds", flush=True)
        time.sleep(delay)


def fetch_group(collection, sites, headers):
    field = "id" if collection == LOC else "monitoring_location_id"
    stations = [f"USGS-{site}" for site in sites]
    where = {"op": "in", "args": [{"property": field}, stations]}
    if collection != LOC:
        stage = {"op": "in", "args": [{"property": "parameter_code"}, ["00065"]]}
        where = {"op": "and", "args": [where, stage]}

    page = post_page(collection, where, headers)
    rows = page["features"]
    total = page.get("numberMatched")
    has_more = any(link.get("rel") == "next" for link in page.get("links", []))
    if (not has_more and len(rows) < PAGE_SIZE
            and (not isinstance(total, int) or total == len(rows))):
        return rows

    # Split large responses by station. For one station, use the existing pager.
    if len(sites) == 1:
        params = {field: stations[0]}
        if collection != LOC:
            params["parameter_code"] = "00065"
        return hour38.features(collection, params, headers)
    middle = len(sites) // 2
    return (fetch_group(collection, sites[:middle], headers)
            + fetch_group(collection, sites[middle:], headers))


def collect(sites, headers):
    grouped = {site: {"location": {}, "series": {}, "peaks": []} for site in sites}
    for collection in (LOC, META, "peaks"):
        for feature in fetch_group(collection, sites, headers):
            props = feature["properties"]
            station = feature["id"] if collection == LOC else props["monitoring_location_id"]
            site = station.removeprefix("USGS-")
            if station != f"USGS-{site}" or site not in grouped:
                raise ValueError(f"Unexpected station in {collection}: {station}")
            entry = grouped[site]
            if collection == LOC:
                if entry["location"]:
                    raise ValueError(f"Duplicate location for {station}")
                entry["location"] = feature
            elif props["parameter_code"] != "00065":
                raise ValueError(f"Unexpected parameter for {station}")
            elif collection == META:
                entry["series"][feature["id"]] = props
            else:
                entry["peaks"].append(props)
    return grouped


def save_new(site, payload):
    target = hour38.CACHE / f"{site}.json"
    if target.exists():
        return
    with NamedTemporaryFile("w", dir=hour38.CACHE, suffix=".tmp",
                            delete=False, encoding="utf-8") as f:
        temp = Path(f.name)
        try:
            json.dump(payload, f, separators=(",", ":"))
        except BaseException:
            f.close()
            temp.unlink(missing_ok=True)
            raise
    try:
        # On Windows rename raises FileExistsError if a completed target exists.
        temp.rename(target)
    except FileExistsError:
        pass
    finally:
        temp.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="show counts and exit")
    args = parser.parse_args()

    _, by_site = hour38.census_inputs()
    pending = [s for s in sorted(by_site) if not (hour38.CACHE / f"{s}.json").is_file()]
    total = len(by_site)
    done = total - len(pending)
    print(f"Reusing {done:,} cached gauges; {len(pending):,} remaining of {total:,}.",
          flush=True)
    if args.check:
        return

    key = os.environ.get("USGS_API_KEY")
    if not key:
        raise SystemExit("USGS_API_KEY is missing in this PowerShell session.")
    headers = {"X-Api-Key": key, "User-Agent": "RadioSilence Hour 38"}
    hour38.CACHE.mkdir(parents=True, exist_ok=True)

    for start in range(0, len(pending), BATCH_SIZE):
        sites = pending[start:start + BATCH_SIZE]
        payloads = collect(sites, headers)
        for site, payload in payloads.items():
            # Confirm an unexpected omission with the existing single-site lookup.
            if not payload["location"] or not payload["series"]:
                hour38.site_data(site, headers)
            else:
                save_new(site, payload)
        done += len(sites)
        print(f"Cached {done:,}/{total:,} gauges.", flush=True)

    hour38.main()


if __name__ == "__main__":
    main()