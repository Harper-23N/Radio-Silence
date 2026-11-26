## 2026-11-21
- Fixed a bug with the estimated value filter (rule 1) in code/gd_gaps.py. The problem was that it was dropping everything with an 'e' and the marking for old USGS was A e for Approved|Estimated but new Approved and Approved|Estimated meaning that it would get rid of all of them because 'Approved' contains an 'e'.
    The fix is that it drops a reading only if there's a whole 'ESTIMATED' (New API) or 'e' (Old codes).
- The label was confirmed by finding 5 ice-affected gauges that have 'Approved|ESTIMATED' readings.
- Before: Hunt had 0 gaps, after Hunt 1 Dark gap, 35.0 h, 8.07 ft deficit
- Centerpoint: 81.0 h, 33.45 ft. Old tests still pass
- Made files code/test_new_api.py and code/check_codes.py

Converted mine_*.csv from UTF-16 to UTF-8 and removed blank rows (to_utf8.py). gd_fetch.py can now save straight to a file in UTF-8.

- Hour 20: dark1h agreement with the pilot 386/387 (99.7%). The only disagreement is Kerrville 08166200 (rise readings missing from today's archive; live feed shows the gauge worked). The 7 non-river sites were not compared (no pilot rows).

Separate gage-height time series in bbox_pull.py
- Problem: some USGS sites have two gage-height time series (e.g. primary and secondary sensor).
  The new API returns both under one site number, and bbox_pull.py mixed them into one file.
  Found at 6 gauges: harvey 08079120; texas 08101310, 08101330, 08101340, 08170950, 08194840.
  Signs: median interval 0 min, double the readings, impossible rises (08170950: 18.28 ft vs pilot 2.46 ft).
- Fix: readings are now grouped by time_series_id. One series per site goes in <site>.csv; the
  others go in data/raw/<event>/extra_series/ (ignored by run_census.py).
- How the series is chosen: (1) hand choice in data/series_choices.csv; (2) the only series USGS
  flags primary; (3) the only series described as "Primary Sensor"; (4) otherwise most readings,
  flagged CHECK BY HAND. USGS flagged both series primary at all 6 sites, so 5 were chosen by the
  "Primary Sensor" description, and 08079120 (Landward/Seaward) by hand: Seaward, matches pilot.
- Re-pulled Texas and Harvey with the same bbox and dates. Gauge counts unchanged.
- Effect: dark1h agreement unchanged (386/387). Small rises 1/101 -> 1/102. 08194840 now uses the
  Primary Sensor (rise 7.96 ft); the pilot used the Secondary (rise 1.41 ft).

- The bbox query returns every site reporting gage height, not only rivers. 7 non-river sites found:
  springs 08168000, 08170990; lakes/reservoirs 08072000, 02162285, 021623961, 13039000;
  estuary 08067118. Not compared with the pilot. To be excluded from the river census
  (filter to be added before the full census, Hour 33).

## 2026-11-23 — gd_live_rules.py: two fixes to the spike check (Hour 26)

What was wrong
1. Spike alarms were timed too early. A spike is a jump of more than 15 ft that comes
   straight back, so it can only be confirmed when the NEXT reading arrives. The alarm was
   stamped at the spike reading itself, about one reading (usually 15 min) earlier than it
   could really have fired. That broke the file's rule that every alarm uses only readings
   available at the moment it fires.
2. The spike check skipped the second-to-last reading. The condition `i + 2 < len(recs)`
   was one stricter than needed; only the last reading has no next reading to check.

What changed
1. Spike alarms are now timed at the next reading: `t = recs[i + 1][0]` for spikes.
   Negative, above-maximum and far-above-normal alarms still use the bad reading's own
   time, because one reading is enough to see them.
2. `i + 2 < len(recs)` changed to `i + 1 < len(recs)`.

Tests
- Added a self-test with a spike in the second-to-last reading: it must be caught and
  timed at the next reading. This test fails on the old code and passes on the new.
- Added a check that a one-reading problem (1310.71 ft) is still timed at itself.
- Comment fixes: silence gap in the self-test is ~7.75 h (not 7.5 h); removed a leftover
  `* 0` that added nothing.
- `python -I code/gd_live_rules.py` → "gd_live_rules self-test passed".

Effect
- Thresholds unchanged. Only spike alarms move, by one reading.
- P9 check on 5 gauges (code/run_p9_check.py) still matches the pilot exactly; none of
  the five alarms is a spike.

  ## 2026-11-26

  Mark counts use marks with a measured elevation (elev_ft) located in the lower 48 (state_name not Alaska, Hawaii or a territory)

  Excluded: studies, exercises, tsunamis and coastal-only storm-surge events.

  Counts use surveyed lower-48 marks whose environment is not Coastal (Riverine, Urban, Rural or blank), because the project studies inland flooding and Coastal marks record storm surge.

  A STN event's NOAA window = the earliest start to the latest end of all Flood and Flash Flood records that (a) lie inside the event's lower-48 box and (b) begin between the STN start date and the STN end date (or 30 days after the start if there is no end date), plus 1 day each side. If no records match, the event is dropped.

  Events whose NOAA window spans more than one month (more than 31 days) are treated as a season of floods and excluded. Set cutoff after seeing window dates but before viewing any outage data.
  Central US Spring 2019 (91 days) excluded; all other kept events are 29 days or less

  292 (2018 Sep SC DOT Bridge) merged into 283 (Florence): overlapping box and dates; marks flagged Dec 2018–Feb 2019 at bridges on the Pee Dee and Waccamaw rivers, likely Florence flood marks

  ## 2026-11-26 — Part B (deadly floods) applied

- Source: NOAA Storm Events details files 2017–2025 (downloaded 2026-11-26,
  files dated c20261119).
- Rule as pre-registered: one flood = one NOAA episode; direct deaths summed
  over its Flood/Flash Flood records; keep episodes with 10 or more.
- Result: 12 episodes qualified.
  - 10 match floods already on the list (same storm, overlapping area and dates)
    and were merged into them. The STN box and window are kept, as prereg.md says:
      Harvey (dev): 119753, 119746
      Waverly (dev): 162118
      Ida (test): 163555, 162538, 163518
      Kentucky (dev): 172563
      Helene (dev): 196694, 195887
      Texas July 2025 (dev): 204934
  - 2 have no STN event and were added as new test floods, using the NOAA box
    (record coordinates + 0.25°) and window (first to last record date, ±1 day):
      NOAA-119185: Arizona, 14–16 Jul 2017, 10 direct deaths
      NOAA-204035: Texas, 10–13 Jun 2025, 13 direct deaths
- Waverly (dev) has no STN high-water marks, so it had no box. Its box is taken
  from NOAA episode 162118: west -88.1682, south 35.2834, east -86.8226, north 36.7008.
- Decided before looking at any outage data for these floods.
Final list: 17 test floods (15 STN + 2 NOAA Part B) and 7 development floods; see data/events_decisions.csv.

Rules above were set while building the list on 2026-11-26; no gauge outage data for any test flood had been viewed.

## 2026-11-26 — census_pull.py (Hour 33) and a retry fix in gd_fetch.py

What I did
- Wrote a first draft of code/census_pull.py: loops over data/events.csv, runs the same
  bbox pull as bbox_pull.py for each flood, skips finished events (_pull_summary.json),
  skips dev floods unless --include-dev, and logs every site to data/raw/_census_log.csv.

AI-assisted review and fixes (Claude, Anthropic; 26 Nov 2026)
- I asked Claude to review my draft. It found problems and wrote the fixes below;
  the code changes in this entry are AI-written, not mine.
- Bugs found (reproduced with a fake downloader, no USGS calls):
  1. --force with a new box left the old box's gauge CSVs in the folder, so the census
     would have analysed gauges outside the box. Fix: the old folder is renamed to
     <event>__replaced_<time> before saving (nothing is deleted).
  2. A pull that returned 0 gauges (e.g. a wrong box) was marked finished and never
     retried. Fix: logged as no_gauges and not marked finished.
  3. A half-written _pull_summary.json crashed every later run. Fix: summary is written
     in one step; an unreadable summary is skipped until --force.
- Added: events.csv is checked before pulling (box order, lower-48 range, dates,
  dev/test value, duplicate names); script stops if USGS_API_KEY is not set; bbox_pull's
  "full page but no next link" warning is saved in the summary (replaces the rows % LIMIT check).
- Non-river filter (promised for Hour 33 in the 21 Nov entry; prereg.md: stream sites only):
  every site is still downloaded, but marked ST or not_ST using the monitoring-locations
  collection (bbox + site_type_code=ST). The census analysis must keep only ST rows.
- gd_fetch.py _get(): now also retries network drops, timeouts and HTTP 500/502/504,
  and respects Retry-After on 429. Other HTTP errors still fail at once. Also affects bbox_pull.py.

My tests (26 Nov 2026)
- Caching: ran census_pull.py twice on 2024_november_sc_flood. First run: 39 gauges
  (all with data), 15,936 rows, 2 pages, 4.3 s. Second run: skipped, 0 s. Caching works.
- Paging: page 1 held exactly 10,000 rows and the script followed the next link to
  page 2 (5,936 rows); no paging warning.
- Stream filter: monitoring-locations query for the Texas box with site_type_code=ST
  returned 352 sites, all ST; includes 08165500 (Hunt), 08166200 (Kerrville) and
  08167000 (Comfort); excludes springs 08168000 (Hueco Springs) and 08170990 (Jacobs Well).
  In the census test, 38 of 39 sites were marked ST; 02196999 was marked not_ST
  (site type on waterdata.usgs.gov: RV reservoir), correctly excluded by the filter.
- census_pull.py written; caching works.