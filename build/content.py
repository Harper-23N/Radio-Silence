"""Front-matter content for the GaugeDark guide (everything except the hour cards)."""

RATINGS = [("Stakes", 9.5, 15), ("Novelty", 8.0, 20), ("Build", 8.5, 15), ("Depth", 8.5, 15),
           ("Evidence", 8.0, 15), ("Feasible", 8.0, 10), ("Timely", 9.0, 5), ("Defence", 7.5, 5)]
TOTAL = round(sum(v * w for _, v, w in RATINGS) / 100, 2)

HISTORY = [("Round 54 (my earlier report)", "8.86"), ("Independent audit (16 Nov)", "7.93"),
           ("Round 55 first fact-check", "8.15"), ("This guide, after new pilots", f"{TOTAL:.2f}")]

from plan_v2 import WEEKS2 as WEEKS  # (title, summary, decision) per week

HYPOTHESES = [
 ("H1 · Big rises break gauges",
  "Gauges whose river rises 20 ft or more fail (go silent, freeze, under-read or send impossible values) during the rise or crest more often than gauges with rises under 5 ft.",
  "On TEST floods, the flood-clustered odds ratio for (20 ft+ vs under 5 ft) has a 95% CI lower bound above 2.",
  "Odds ratio point estimate below 1.5 with a CI that includes 1.",
  "Anything in between, or fewer than 8 test floods with big rises: report 'unresolved', add floods if time allows, and say what sample would settle it.",
  "Pilot (dev floods, archive only): 28 of 116 (24%, 95% CI 17-33%) vs 1 of 103 (1%, CI 0.2-5%)."),
 ("H2 · Real-time failure is often 'wrong but alive'",
  "Among gauges that are dark in the USGS archive, a substantial share kept transmitting frozen, too-low or impossible values in real time.",
  "At least 25% of archive-dark gauges with live data are FROZEN, UNDER_READ or IMPLAUSIBLE, with the 95% CI lower bound at or above 15%.",
  "Under 10%: archive gaps mostly were live silences after all.",
  "10-25%: report the share with its CI; the taxonomy still stands as a description.",
  "Pilot: 16 of 33 (48%) on dev floods, my labels only; plus 7 live-only outages the archive later repaired."),
 ("H3 · A real-time detector beats a plain 'no data' flag",
  "Rules using only past data flag dangerous gauge failures with useful precision and recall.",
  "On TEST floods: precision at least 0.6 AND recall at least 0.6, AND detector F1 beats the plain missing-data flag in at least 95% of flood-bootstrap resamples.",
  "Detector F1 does not beat the silence-only rule or the plain flag (wins in under 50% of resamples).",
  "Wins in 50-95% of resamples, or precision/recall below 0.6: report as partial; use the error analysis to say why.",
  "Pilot (silence rule only, in-sample, archive gaps): precision 0.66, recall 0.68 vs plain flag precision 0.18."),
 ("H4 · A neighbour-based virtual gauge can estimate the crest",
  "A stage-to-stage model fitted on earlier floods estimates a blanked downstream crest within about 2 ft.",
  "Median crest error at or below 2 ft (bootstrap CI upper bound at or below 3 ft) AND better than hold-last-value and naive transfer in at least 80% of test pairs.",
  "Median crest error above 5 ft, or not better than naive transfer.",
  "Between: report error by river size and rise speed; recommend where it is usable.",
  "Pilot (naive transfer, no fitting): beat hold-last-value in 6 of 6 pairs, but missed Texas crests by -9.2, -19.9 and +13.9 ft."),
 ("H5 · Equipment limits explain only part of it",
  "Gauges fail more often when the river reaches their own published equipment limit (USGS 'operational maximum'), but most failures happen below that limit, so the limits alone cannot warn of a failure.",
  "On TEST floods: failure rate is higher when the crest reaches the limit (flood-clustered odds-ratio CI lower bound above 1) AND at least half of failures happen below the limit.",
  "No difference (odds-ratio CI includes 1 with point estimate below 1.5), OR most failures happen at or above the limit (then the limit IS a usable warning, which is also worth reporting).",
  "Fewer than 10 test gauges reach their limit, or many limits look post-flood: report descriptive shares only.",
  "Pilot (dev floods, unclustered): 7 of 13 (54%) vs 20 of 92 (22%), OR 4.2, p = 0.036; for 20 of 27 dark gauges the crest never reached the limit, and 23 of 27 stopped reporting below it; 11 of 14 failed at or above NWS flood stage."),
]

KILLS = [
 ("K2 · Hour 8 · Can you reproduce my table?", "95% or more agreement on the dark flag: continue. 85-95%: continue, document every difference. Under 85%: stop and debug before anything else (Fallback C if the API is the cause)."),
 ("K1 · Hour 13 · Is the effect real enough?", "Continue if at least 10% of big-rise (20 ft+) pilot gauges show a hand-confirmed failure during rise or crest (archive OR live). Otherwise switch to Fallback A."),
 ("H2 · Hour 59", "Apply the H2 thresholds above. Whatever the verdict, the live-vs-archive table is a result."),
 ("K3 · Hour 75", "Apply the H1 thresholds on test floods only."),
 ("H5 · [[n:mech]]", "Apply the H5 thresholds on test floods. Either outcome is a finding about how USGS limits relate to failure."),
 ("K5 · Hour 104", "Apply the H4 thresholds on test pairs only."),
 ("K4 · Hour 115", "Apply the H3 thresholds on test floods with thresholds locked at Hour 88."),
]

FALLBACKS = [
 ("A · Failures turn out rare", "If K1 fails: re-frame as 'How different is the USGS archive from what forecasters received during floods?' (H2 plus live-only outages). Same data, same code, smaller claim."),
 ("B · Someone publishes the national rate first", "Cite them, compare your numbers, and move your contribution to the live-feed taxonomy (H2) and the detector (H3), which no search found."),
 ("C · The new USGS API cannot serve what you need", "Use the Python 'dataretrieval' package (USGS-maintained), or the Iowa State 'USGS Instantaneous Data Archive' listed on mesonet.agron.iastate.edu/archive. Do bulk pulls before January 2027, when USGS plans outages of the old service."),
 ("D · Iowa State blocks or rate-limits you", "Slow down (5 s between requests), split into nights, or cut the census to 1,000 gauge-events. Also check NOAA NCEI's archive of HADS SHEF data (catalog.data.gov) as a second live-feed source."),
 ("E · DarkWatch catches nothing", "A calm winter is a valid null result. Report gauge-hours logged and zero confirmed outages; rely on the historical live feed."),
 ("F · The detector fails on test floods", "Report it as a negative result with error analysis. Your measurement study (H1, H2) still stands, and the tooling (DarkWatch, classifier) is still the build."),
 ("G · You fall behind by more than 6 hours at the end of Week 6", "Drop, in order: the survival analysis (Hour 70), the event fixed-effects model (Hour 68), half of the virtual-gauge pairs, the uncertainty band (Hour 103). Never drop the hand check, the held-out test, or the 31 January finish: the week of 1-6 February is buffer, not work time."),
 ("H · A single-gauge flat-line rule cannot separate stuck sensors from natural crests", "Expected from pilot P9 (4 of 8 caught, 24 of 81 healthy gauges alarmed). Report the frozen rule only with the neighbour condition, or report frozen detection as an open problem."),
]

RISKS = [
 ("USGS legacy API outages from January 2027; shutdown 22 Feb 2027", "High", "Use api.waterdata.usgs.gov from Hour 4; finish bulk pulls in Week 3; offline demo (Hours 107-108) and the final backup ([[n:final]])."),
 ("Rate limits (Iowa State returned HTTP 429 on 190 of 359 requests in the pilot)", "High", "2.5 s pause, retries with back-off, caching (Hours 33, 40)."),
 ("Archive revisions change numbers between pulls", "Medium", "Record pull dates; keep raw files; report the pull date in the paper."),
 ("Hand labels biased toward my hypothesis", "Medium", "Random sample with a written seed, protocol card, second rater with kappa (Hours 49-58)."),
 ("Over-claiming about deaths", "Medium", "Ethics wording check (Hour 136); never say an outage caused a death."),
 ("ISEF AI rules (no AI-written plan, abstract, poster or citations; Form 2A prompt log)", "Medium", "You write all text; keep the prompt log from Hour 1; citation check (Hour 133)."),
 ("Mentor does not reply", "Low", "Teacher review as backup; your project does not depend on access to anyone."),
 ("GitHub scheduled runs delayed or skipped", "Low", "Log poll times; report actual cadence; the laptop fallback in darkwatch.py."),
 ("Holidays (Thanksgiving 26 Nov, 24-25 Dec, 1 Jan)", "Low", "Order matters, not the day: move those hours to Saturday, Sunday or Monday of the same week."),
 ("Missing a TCRSF deadline or a form error", "Medium", "Forms signed in Week 1 ([[n:forms]]); registered 9 Dec ([[n:reg]]); everything uploaded by 31 Jan ([[n:upload]]), a week before the 6 Feb deadline."),
 ("Published equipment limits set after the flood", "Medium", "Flag possibly post-flood limits ([[n:p8v]]) and run H5 with and without them ([[n:mech]])."),
]

CLASS_RULES = [
 ("SILENT", "Fewer than 20% of the expected live readings exist inside the archive gap."),
 ("FROZEN", "Live readings exist but stay within 0.1 ft of each other for 2 h or more while the surveyed crest is at least 0.5 ft higher."),
 ("UNDER_READ", "Live readings vary but their maximum is more than 2 ft below the crest."),
 ("IMPLAUSIBLE", "Live values that cannot be water: error codes such as 1310.71, negative stages, or tens of feet above the crest."),
 ("LIVE_PRESENT", "Plausible live readings throughout: the archive gap is a later deletion, not a live failure."),
 ("NO_LIVE_DATA", "No NWS ID, or the Iowa State archive has no record for the station."),
]

BOXES = [("Texas Hill Country", "-100.6, 29.6, -97.8, 31.4", "3-7 Jul 2025"), ("Hurricane Helene", "-83.6, 35.0, -81.3, 36.6", "25-30 Sep 2024"),
         ("Eastern Kentucky", "-84.2, 36.9, -82.3, 38.0", "26-31 Jul 2022"), ("Vermont", "-73.4, 43.4, -71.9, 45.0", "9-14 Jul 2023"),
         ("Hurricane Harvey", "-96.5, 28.8, -94.0, 30.6", "25 Aug-1 Sep 2017"), ("Waverly, Tennessee", "-88.3, 35.6, -86.9, 36.5", "20-24 Aug 2021"),
         ("Yellowstone", "-111.5, 44.5, -109.0, 46.0", "11-16 Jun 2022")]

CORRECTIONS = [
 ("Center Point 'sent nothing for 75 minutes while the river rose 33 ft'", "Wrong. The archive's last real reading is 6.16 ft at 6:15 am; the 39.61 ft crest is an inserted survey value; the archive is then empty for 81 hours. The live feed kept sending about 21 ft near the crest."),
 ("Hunt 'nothing for 34 hours'", "35.0 hours (09:35 UTC 4 Jul to 20:35 UTC 5 Jul)."),
 ("'36 of 114 gauges (32%) went dark'", "With the same data and an inserted-crest-aware rule: 28 of 116 (24%). Round 54's own rule on today's data: 32 of 116."),
 ("'USGS runs over 11,000 gauges'", "USGS states more than 13,500 streamgages."),
 ("'Experts already link it to forecast failure'", "Correct, and stronger: Baruah et al. 2026 say Hunt failed on the rising limb, stopping data assimilation. But they name rainfall error as the main cause."),
 ("'No study measures this'", "Partly wrong: USGS measured event data recovery (about 98%) for the 2015 Texas floods, and SHEM (2018) plus a 2017-priority patent already estimate data for gauges that stop. Nobody found measures failure by flood size nationally, or compares live feed with archive."),
 ("Audit: 'archive gaps are not live outages'", "Confirmed, and the live picture is different: of 33 archive-dark gauges with live data, only 12 were silent in real time; 16 sent frozen, too-low or impossible values; 5 looked plausible and were deleted later. Separately, 7 gauges were silent live but repaired in the archive."),
 ("Tide-gauge control: Naples dead 55+ hours in Ian", "Confirmed: last value 9.05 ft at 17:06 UTC 28 Sep 2022, none through 1 Oct."),
]

SOURCES = [
 ("Baruah A. et al. (2026) Rise of the Guadalupe River: a multifaceted post-event analysis of 4 July 2025. Natural Hazards and Earth System Sciences 26:4753-4762.", "https://doi.org/10.5194/nhess-26-4753-2026"),
 ("Quintero F., Krajewski W., Vergara H. (2026) Evaluation of short-range streamflow forecasts at flash-flood prone basins with the National Water Model. Journal of Hydrometeorology.", "https://doi.org/10.1175/jhm-d-26-0026.1"),
 ("Seo B., Krajewski W., Quintero F. (2021) Multi-scale hydrologic evaluation of the National Water Model streamflow data assimilation. JAWRA 57(6):875-884.", "https://doi.org/10.1111/1752-1688.12955"),
 ("Gharamti M. et al. (2021) Ensemble streamflow data assimilation using WRF-Hydro and DART: Hurricane Florence. HESS.", "https://doi.org/10.5194/hess-25-5315-2021"),
 ("East J.W. (2016) U.S. Geological Survey response to flooding in Texas, May-June 2015. USGS Fact Sheet 2016-3027.", "https://pubs.usgs.gov/publication/fs20163027"),
 ("Studley S.E. (2001) Evaluation of missing gage-height record for streams and lakes in Kansas. USGS Fact Sheet 009-01.", "https://doi.org/10.3133/FS00901"),
 ("USGS Office of Surface Water (2006) Memorandum 2006.05: data aging and revision criteria (inserting surveyed peaks into unit values).", "https://water.usgs.gov/admin/memo/SW/sw06.05.html"),
 ("Petty T.R., Dhingra P. (2018) Streamflow Hydrology Estimate using Machine Learning (SHEM). JAWRA 54:55-68.", "https://doi.org/10.1111/1752-1688.12555"),
 ("US Patent 11,238,356 (priority 2017). Method of predicting streamflow data.", "https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/11238356"),
 ("Vlah M.J. et al. (2024) Leveraging gauge networks and strategic discharge measurements to aid the development of continuous streamflow records. HESS 28:545.", "https://doi.org/10.5194/hess-28-545-2024"),
 ("Harvey C., Dixon H., Hannaford J. (2012) An appraisal of data-infilling methods for daily mean river flow records in the UK. Hydrology Research.", "https://doi.org/10.2166/NH.2012.110"),
 ("Luna A.M. et al. (2020) Assessing the best gap-filling technique for river stage data for real-time IoT. Sensors 20:6354.", "https://doi.org/10.3390/s20216354"),
 ("Polz J., Graf M., Chwala C. (2023) Missing rainfall extremes in commercial microwave link data due to complete loss of signal. Earth and Space Science.", "https://doi.org/10.1029/2022EA002456"),
 ("Hughes S., Du Y., Hallstrom J. (2015) Detecting reporting anomalies in streaming sensing systems. SEKE 2015.", "https://doi.org/10.18293/SEKE2015-181"),
 ("Finck J.S., Pedrollo O.C. (2021) Facing losses of telemetric signal in real-time forecasting of water level using ANNs. Water Resources Management.", "https://doi.org/10.1007/s11269-021-02782-x"),
 ("Mbuvha R. et al. (2023) A novel workflow for streamflow prediction in the presence of missing gauge observations. Environmental Data Science.", "https://doi.org/10.1017/eds.2023.11"),
 ("Lopez E. et al. (2020) A cost-effective redundant communication system for a flood early warning system. Journal of Hydroinformatics 22:856.", "https://doi.org/10.2166/hydro.2020.216"),
 ("USGS (2018) Equipment repair and replacement after Harvey, Irma and Maria (192 gauges damaged or destroyed).", "https://www.usgs.gov/supplemental-appropriations-for-disaster-recovery-activities/equipment-repair-and-replacement"),
 ("USGS water alerts, 4-6 July 2025 (Hunt gauge not reporting; back online).", "https://water.usgs.gov/alerts/item_2025-07-06_11:52:27.html"),
 ("Texas Tribune / TPR (2025): NWS meteorologist on the Hunt gauge rising 22 ft in two hours to about 29.5 ft before failing.", "https://www.tpr.org/news/2025-07-06/in-texas-region-prone-to-catastrophic-floods-questions-grow-about-lack-of-warning"),
 ("USGS Water Data APIs and WaterServices decommission notices (2026).", "https://waterdata.usgs.gov/blog/api-waterservices-decom"),
 ("Iowa Environmental Mesonet, DCP/HADS data download (archive of the NWS SHEF relay; all stations since 9 Dec 2010).", "https://mesonet.agron.iastate.edu/request/dcp/fe.phtml"),
 ("NOAA HADS USGS-to-NWS station list.", "https://hads.ncep.noaa.gov/USGS/ALL_USGS-HADS_SITES.txt"),
 ("Society for Science (2026) International Rules 2026-27, final rule modifications (AI use; Form 2A).", "https://sspcdn.blob.core.windows.net/files/Documents/SEP/ISEF/2027/Rules/FINAL-Rule-Modifications-for-2026-27.pdf"),
 ("Independent audit supplied by you: 'ISEF Research Inventory and Evidence Audit', 16 Nov 2026 (GaugeDark 7.93).", ""),
 ("My Round 54 report 'At the line' (15 Nov 2026) and round54_pilots.zip.", ""),
]
