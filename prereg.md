# Pre-registration: flood selection
Date: 11/26/2026   Author: Harper Fang

## Rule
A. USGS STN events: years 2017-2025, area lower 48 U.S. states, minimum high-water marks: 50
B. Deadly floods: source NOAA Storm events database; area lower 48 U.S. states; one flood = one Storm events episode; Deaths = direct deaths from its Flood and Flash Flood records, added together; Threshold = 10 or more deaths, years 2017-2025

## Box and window
STN floods (Part A, and Part B floods that also have an STN event):
   Box = rectangle around all high-water marks, plus 0.25° on every side
   Window = STN event start date to event end date, +1 day before and after. If an STN event has no start or end date, or its dates span more than 14 days, the NOAA Storm events episode dates for the same flood will be used.
Part B floods without STN marks:
   Box = rectangle around start/end coordinates of episode's Flood and Flash Flood records (county centre if none exists), plus 0.25°  
   Window = earliest start to latest end in the episode, +1 day before and after

## Gauges included
Parameter: River gauges only (stage, code 00065); 
Excluded site types: reservoirs, lakes, estuaries, springs; big rise ≥ 20 ft

## Special cases
Overlapping/duplicate events: A storm with multiple STN events or in both A and B will be merged into one flood. Events are merged if they are the same named storm, or if their boxes and windows overlap. A merged flood's box and window will be the combined rectangle along with the earliest-to-latest window of the overlapping events.   
Coastal/tidal gauges: Include only USGS site type ST (stream). All other USGS labels like ST-TS (tidal stream), ES (estuary), LK (lake/reservoir), SP (spring), are excluded.

## Development vs test
Development Floods: Hurricane Harvey, Texas (25 Aug - 2 Sep 2017); Waverly Flash Flood, Tennessee (20 - 25 Aug 2021); Eastern Kentucky Floods, Kentucky (26 Jul - 1 Aug 2022); Vermont Floods, Vermont (9 - 15 Jul 2023); Hurricane Helene, Southeast (25 Sep - 1 Oct 2024); Texas Hill Country (Guadalupe), Texas (3 - 8 Jul 2025); Yellowstone flood, Montana/Wyoming (11 - 17 Jun 2022).
Test: every other flood the rule selects. If the rule happens to select a development flood, it will stay development and not be used for testing.

## Changes
Any change is dated in CHANGELOG.md with a reason, and never made after seeing a test-flood result.

## Why these thresholds
Years (2017-2025): Covers all of the development floods from the earliest one Harvey (2017) and ending with the latest full year as of this date (11/26/2026). Covered from both the live-feed archive from Iowa state and the new USGS API.
Lower 48 U.S. states: same gauge network and data systems throughout, excluding Alaska, Hawaii, and U.S. territories as gauges and flood types can differ there.
≥ 50 high-water marks: Selects only large, well documented floods. This threshold provides enough marks to draw a reliable box. Fewer marks could also indicate a small or poorly surveyed/documented event.
Window: high-water marks are flagged/surveyed after a flood (USGS Vermont July 2023 data release metadata), this means that mark dates can fall after the peak. By using event dates, we are bracketing the flood itself.
≥ 10 deaths: Deadliest floods, warnings for these floods matter the most, greatest consequences/impact.
0.25° widening: About 25 km on each side, catches gauges just outside the area that was surveyed without being too large that unrelated rivers are included.
+1 day on each side: includes river before and after the rise and fall, this way the census will be able to measure the full event.