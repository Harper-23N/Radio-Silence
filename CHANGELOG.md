## 2026-11-21
- Fixed a bug with the estimated value filter (rule 1) in code/gd_gaps.py. The problem was that it was dropping everything with an 'e' and the marking for old USGS was A e for Approved|Estimated but new Approved and Approved|Estimated meaning that it would get rid of all of them.
    The fix is that it drops a reading only if there's a whole 'ESTIMATED' (New API) or 'e' (Old codes).
- The lable was confirmed by finding 5 ice-affected gauges that have 'Approved|ESTIMATED' readings.
- Before: Hunt had 0 gaps, after Hunt 1 Dark gap, 35.0 h, 8.07 ft deficit
- Centerpoint: 81.0 h, 33.45 ft. Old tests still pass
- Made files code/test_new_api.py and code/check_codes.py

"Converted mine_*.csv from UTF-16 to UTF-8 and removed blank rows (to_utf8.py). gd_fetch.py can now save straight to a file in UTF-8.

- Hour 20: Non-river gauges were excluded from the comparison laeding to a 386/387 agreement rate (99.7%)

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