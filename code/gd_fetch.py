"""Download helpers for GaugeDark.

IMPORTANT (checked 16 Nov 2026): USGS is retiring the legacy WaterServices API (waterservices.usgs.gov).
Service degradation began November 2026, planned outages start January 2027, and it shuts down on
22 February 2027. Use the new Water Data OGC API (api.waterdata.usgs.gov) for everything. The legacy
function is kept only so you can reproduce the Round 55 pilot while it still works.

Get a free api.data.gov key (https://api.waterdata.usgs.gov/signup/) and put it in the environment:
    export USGS_API_KEY=your_key_here         (macOS/Linux)
    setx USGS_API_KEY your_key_here           (Windows, then reopen the terminal)

Usage examples:
    python -I gd_fetch.py usgs 08165500 2025-07-03T00:00:00Z 2025-07-08T00:00:00Z  > hunt_usgs.csv
    python -I gd_fetch.py iem  HNTT2    2025-07-03T05:00Z    2025-07-08T05:00Z     > hunt_iem.csv
"""
from __future__ import annotations
import csv, http.client, io, json, os, sys, time, urllib.error, urllib.parse, urllib.request

OGC = "https://api.waterdata.usgs.gov/ogcapi/v1/collections/continuous/items"
IEM = "https://mesonet.agron.iastate.edu/cgi-bin/request/hads.py"
HADS_MAP = "https://hads.ncep.noaa.gov/USGS/ALL_USGS-HADS_SITES.txt"
UA = {"User-Agent": "GaugeDark student science-fair project (contact via your school email)"}


RETRY_HTTP = (429, 500, 502, 503, 504)      # rate limit and temporary server errors


def _get(url: str, headers: dict | None = None, tries: int = 5) -> bytes:
    """GET with retries for rate limits, temporary server errors and network drops (wifi, timeouts).

    Waits 10, 20, 30, 40 s between tries, or the server's Retry-After (up to 15 min) on HTTP 429.
    Other HTTP errors (400 bad request, 403, 404) are raised at once: retrying cannot fix them.
    """
    h = dict(UA, **(headers or {}))
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=120) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code not in RETRY_HTTP or k == tries - 1:
                raise
            wait = 10 * (k + 1)
            ra = (e.headers or {}).get("Retry-After", "")
            if e.code == 429 and ra.strip().isdigit():
                wait = min(max(wait, int(ra)), 900)
            print(f"  HTTP {e.code}; retrying in {wait} s", file=sys.stderr, flush=True)
            time.sleep(wait)
        except (urllib.error.URLError, TimeoutError, ConnectionError, http.client.HTTPException) as e:
            if k == tries - 1:
                raise
            wait = 10 * (k + 1)
            print(f"  network error ({e!r}); retrying in {wait} s", file=sys.stderr, flush=True)
            time.sleep(wait)
    raise RuntimeError("unreachable")


def usgs_continuous(site: str, start: str, end: str, param: str = "00065") -> list[tuple[str, float | None, str]]:
    """Gage height (00065) from the new OGC API. Returns (time_utc_iso, value, qualifiers+approval)."""
    key = os.environ.get("USGS_API_KEY")
    headers = {"X-Api-Key": key} if key else {}
    q = {"monitoring_location_id": f"USGS-{site}", "parameter_code": param, "time": f"{start}/{end}", "f": "json", "limit": "10000"}
    url, rows = OGC + "?" + urllib.parse.urlencode(q), []
    while url:
        j = json.loads(_get(url, headers))
        for f in j.get("features", []):
            p = f["properties"]
            v = p.get("value")
            code = (p.get("approval_status") or "") + ("|" + "+".join(p["qualifier"]) if p.get("qualifier") else "")
            rows.append((p["time"], float(v) if v not in (None, "") else None, code))
        url = next((l["href"] for l in j.get("links", []) if l.get("rel") == "next"), None)
    rows.sort()
    return rows


def iem_hads(nwsli: str, sts: str, ets: str) -> list[tuple[str, float | None]]:
    """Live-relay copy of the NWS HADS feed archived by Iowa State (all US stations since 9 Dec 2010)."""
    url = IEM + "?" + urllib.parse.urlencode({"stations": nwsli, "sts": sts, "ets": ets, "what": "txt", "delim": "comma"})
    txt = _get(url).decode()
    if txt.startswith("Error"):
        return []
    rdr = csv.DictReader(io.StringIO(txt))
    out = []
    for r in rdr:
        hg = [k for k in r if k.startswith("HG") and r[k] not in ("", None)]   # stage columns, e.g. HGIRGZZ
        out.append((r["utc_valid"], float(r[hg[0]]) if hg else None))
    time.sleep(2.5)                                                     # IEM rate-limits bursts (HTTP 429)
    return out


def usgs_to_nwsli() -> dict[str, str]:
    m = {}
    for line in _get(HADS_MAP).decode(errors="ignore").splitlines():
        f = line.split("|")
        if len(f) > 2 and f[1].strip().isdigit():
            m[f[1].strip()] = f[0].strip()
    return m


if __name__ == "__main__":
    kind, sid, a, b = sys.argv[1:5]
    out_path = sys.argv[5] if len(sys.argv) > 5 else None
    f = open(out_path, "w", encoding="utf-8", newline="") if out_path else sys.stdout
    w = csv.writer(f)
    if kind == "usgs":
        w.writerow(["time_utc", "value_ft", "code"]); w.writerows(usgs_continuous(sid, a, b))
    else:
        w.writerow(["time_utc", "value_ft"]); w.writerows(iem_hads(sid, a, b))
    if out_path:
        f.close()
        print(f"saved {out_path}")