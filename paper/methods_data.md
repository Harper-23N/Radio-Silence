| Dataset | Source URL | Date pulled | Rows | Known issues |
|---|---|---|---:|---|
| Flood event inventory (`events.csv`) | [USGS Short-Term Network](https://api.waterdata.usgs.gov/stnservices/events/), [NOAA Storm Events](https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/) | 2026-11-26 (file date) | 24 event rows | Includes 7 development and 17 test events. Two test events came from NOAA Storm Events. |
| USGS gage-height observations (17 test-event folders under `data/raw`) | [USGS Continuous Data](https://api.waterdata.usgs.gov/ogcapi/v1/collections/continuous/items), [Monitoring Locations](https://api.waterdata.usgs.gov/ogcapi/v1/collections/monitoring-locations/items) | 2026-11-26 to 2026-11-27 (UTC pull log) | 14,605,523 observation rows in 7,517 CSVs | Raw files include non-stream sites and records with missing stage values. Of the 7,517 census log rows, 3 were marked `no_values`. |
| USGS station metadata (`site_meta.csv`) | [Monitoring Locations](https://api.waterdata.usgs.gov/ogcapi/v1/collections/monitoring-locations/items), [Time Series Metadata](https://api.waterdata.usgs.gov/ogcapi/v1/collections/time-series-metadata/items), [Peaks](https://api.waterdata.usgs.gov/ogcapi/v1/collections/peaks/items) | 2026-11-27 (file date) | 6,783 gauge-event rows covering 4,062 distinct gauges | Flood stage was blank in 4,374 gauge-event rows. HTTP 429 rate limits delayed the metadata pull. |
| USGS-to-NWS station crosswalk (`census_nwsli.csv`) | [NOAA HADS USGS station list](https://hads.ncep.noaa.gov/USGS/ALL_USGS-HADS_SITES.txt) | 2026-11-27 (file date) | 4,062 gauge rows | 3,438 mapped (84.6%), 613 unmapped, and 11 ambiguous. |
| Archived live-feed stage observations (`data/live`) | [Iowa Environmental Mesonet HADS archive](https://mesonet.agron.iastate.edu/cgi-bin/request/hads.py) | 2026-11-27 (file dates) | 9,805,325 observation rows in 5,569 CSVs | The Hour 42 check could use live series for 5,302 of 6,783 eligible gauge-event records. |
| Network-wide outage audit (`outage_minutes.csv`, `outage_summary.csv`) | Derived from the USGS census, NOAA HADS crosswalk, and IEM live-feed archive above | 2026-11-27 (output file date) | 357,120 event-minute rows and 17 event summary rows | The 80% rule flagged 0 outage periods and 0 excluded minutes. Unknown coverage left 25 event-minutes unresolved across two events. |

Row counts exclude CSV headers. File dates are the saved files’ modification dates.

Below are 5 gauges that were randomly selected from the 4,062 eligible test-event gauges using seed 43, all gauge-event records fell in the 2021 Ida window. Saved CSVs were compared with the same USGS continuous gage-height series (parameter 00065) using the original pull window August 26 at 00:00 through September 5 at 00:00 UTC, 2021					
					
USGS gauge	CSV max (ft)	USGS max (ft)	Difference (ft)	First maximum (UTC)	Readings in each source
02024000	4.81	4.81	0	Sep 2, 9:45	2,805
04101225	1.92	1.92	0	Aug 27, 8:45	961
03129197	7.53	7.53	0	Aug 26, 0:00	961
01650800	6.04	6.04	0	Sep 1, 8:40	2,881
021623950	3.06	3.06	0	Sep 1, 8:00	960