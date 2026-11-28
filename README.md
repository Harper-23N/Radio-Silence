# GaugeDark: Round 57 bundle (17 Nov 2026)

Pilot work produced by Claude (AI) on 16-17 Nov 2026 for the GaugeDark research guide. **Re-run everything yourself** (Week 2 of the guide, after your forms are signed in Week 1) before using any number. Keep this bundle, and your AI prompt log, for ISEF Form 2A.

## data/
| File | What it is |
|---|---|
| stations_7floods_v3.csv | 387 gauges x 7 pilot floods: rise, crest, interval, inserted values, 1-h max rise, dark flags, longest dark gap, last reading, deficit below crest; v1rule_dark = Round 54's rule on the same data |
| live_feed_dark_gauges_classified.csv | 36 archive-dark gauges, classified by what the Iowa State live-feed copy showed (SILENT, FROZEN, UNDER_READ, IMPLAUSIBLE, LIVE_PRESENT, NO_LIVE_DATA) |
| live_feed_only_outages.csv | 7 gauges silent in the live feed but repaired in the archive |
| usgs_to_nwsli_map.json | USGS site -> NWS ID for 359 of the 387 gauges (NOAA HADS list, 16 Nov 2026) |
| guadalupe_4jul2025_hydrographs.json | Hunt, N Fork nr Hunt, Kerrville, Center Point on 4 July 2025 (UTC) |
| pilot_results_round55.json | Every pilot number in the guide |
| watchlist.csv | 116 big-rise gauges to seed DarkWatch |
| gauge_thresholds_usgs.csv | P8: USGS operational maximum (equipment limit) and NWS flood stage for 133 pilot gauges (115 with an operational maximum), from the new API's time-series-metadata. Current values; some may post-date the flood |
| live_detector_pilot.csv | P9: real-time silence, impossible-value and flat-line alarms on the Iowa State live feed for 125 gauges (121 with live data), with confirmation against the later archive crest. first_silent_utc uses a 60-min floor, first_silent_utc_15min_floor a 15-min floor. Hunt's times include Iowa State's later-inserted crest (37.52 ft at 10:10 UTC); without it the alarms are 10:35 and 09:50 UTC |

## code/
| File | What it does |
|---|---|
| gd_gaps.py | Gap rule (inserted-crest aware). `python -I code/test_gd_gaps.py` runs tests on the real Hunt record |
| gd_fetch.py | Downloads from the new USGS Water Data API (set USGS_API_KEY), the Iowa State HADS archive, and the USGS->NWS ID list |
| gd_alarm.py | Silence alarm vs plain missing-data flag, with scoring |
| gd_live_rules.py | P9 live-feed rules (silence, impossible value, flat line). `python -I code/gd_live_rules.py` runs a self-test |
| gd_virtual.py | Blank-out test: hold-last-value, naive transfer, oracle, and a slot for your fitted regression |
| darkwatch.py, darkwatch.yml | Live logger (every 15 min) and a GitHub Actions workflow for it |
| make_figures.py | Rebuilds figs/ from data/ |

## build/
Scripts that generated the PDF guide (content, hour plan, renderer). Not needed for the research.

## Important limits
- The pilots ran through a browser on the user's computer (this workspace cannot reach USGS or Iowa State directly). The Python code was written to match and tested offline on Hunt; run it yourself end to end in Hours 15-20 of the guide.
- Iowa State's archive stores observation time, not arrival time, and contains some later inserts.
- The 7 pilot floods were hand-picked; use them as development data only.
- USGS legacy WaterServices: degraded from Nov 2026, planned outages Jan 2027, shutdown 22 Feb 2027. Use api.waterdata.usgs.gov.
- P8 and P9 are in-sample: the rules and comparisons were designed after seeing these 7 floods.
