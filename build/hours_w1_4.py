# Hours 1-64. Each entry: (title, why, steps, checklist, done, uses)
# "uses" names files from the Round 55 bundle (see Part 3 of the guide).
HOURS = []
def H(title, why, steps, checks, done, uses=""):
    HOURS.append(dict(title=title, why=why, steps=steps, checks=checks, done=done, uses=uses))

# ---------------- WEEK 1: reproduce, kill test, paperwork ----------------
H("Read the plan and open your logbook",
  "Everything later depends on you understanding what has already been done and what has not.",
  ["Read Parts 1-3 of this guide (summary, ratings, completed work). Mark anything you do not understand with a '?' in the margin.",
   "Start a paper or digital logbook with numbered, dated pages. Page 1: the research question in your own words, today's date, and the line 'Pilot work in /data was produced by an AI assistant on 16-17 Nov 2026 and must be re-run by me.'",
   "Start an AI prompt log (a document where you paste every prompt you give an AI tool and its answer, with dates). ISEF Form 2A now asks for this.",
   "Write three questions you would ask a hydrologist. Keep them for Hour 14."],
  ["Logbook exists, page 1 dated and signed", "AI prompt log file created and this conversation saved into it", "3 questions written"],
  "A logbook with one honest page, and a prompt log that already contains this conversation.",
  "pilot_results_round55.json (skim the numbers)")

H("Paperwork: Forms 1, 1A, 1B, 2A and the research plan outline",
  "ISEF requires Forms 1B to be signed BEFORE your actual start date; data analysis of public data needs no extra review, but you still need the core forms.",
  ["Download the 2026-27 forms from societyforscience.org (Forms 1, 1A, 1B, 2A). Check your regional fair's site for any stricter local rules.",
   "Meet or email your adult sponsor (usually a science teacher). Show them Part 1 of this guide. Ask them to complete Form 1.",
   "Fill Form 1A. Under data: 'publicly available USGS, NOAA and Iowa State University data; no human participants, no hazardous materials.' Set the actual start date to the day AFTER 1B is signed.",
   "Write the research plan outline headings: Rationale, Research question and hypotheses, Procedures, Risk and safety, Data analysis, Bibliography. Do not let any AI write this text; the 2026-27 rules forbid it."],
  ["Forms downloaded", "Sponsor contacted", "1A drafted", "Research plan headings in your own document"],
  "A folder called 'forms' with drafts, and a date for the 1B signature.")

H("Install your tools and run the tests",
  "You need a working Python setup before you can reproduce anything.",
  ["Install Python 3.12 (python.org), VS Code, and git. Create a free GitHub account if you do not have one.",
   "Create a PUBLIC repository called gaugedark. Copy the bundle folders (code, data, figs) into it. Commit with the message 'Round 55 AI pilot bundle, unmodified'.",
   "In a terminal: pip install pandas matplotlib scipy statsmodels pytest. Then run: python -I code/test_gd_gaps.py. You should see 'all tests passed'.",
   "Open code/gd_gaps.py and read the docstring at the top. In your logbook, rewrite the six rules in your own words, one line each."],
  ["Python works", "Repo created and first commit pushed", "Tests pass", "Six rules rewritten in your words"],
  "A GitHub repo with a green first commit and a logbook page explaining the gap rule.",
  "code/gd_gaps.py, code/test_gd_gaps.py")

H("Get your USGS key and reproduce the Hunt gauge yourself",
  "The single most important fact in the project (the Hunt gauge stopped at 29.45 ft) must come from your own download, not from me.",
  ["Sign up for a free key at api.waterdata.usgs.gov/signup. Set it: on Mac/Linux 'export USGS_API_KEY=...'; on Windows 'setx USGS_API_KEY ...' then reopen the terminal.",
   "Run: python -I code/gd_fetch.py usgs 08165500 2025-07-04T00:00:00Z 2025-07-06T00:00:00Z > data/mine_hunt.csv",
   "Open the CSV. Find the 09:35 row (29.45 ft) and the 10:10 row (37.52 ft). Check that the 10:10 row carries the qualifier DAYUNKNOWN. That flag means USGS inserted the crest later.",
   "Screenshot the USGS web page waterdata.usgs.gov/monitoring-location/USGS-08165500 for 4 July 2025 and paste it in your logbook."],
  ["Key works", "mine_hunt.csv saved", "29.45 / 37.52 / DAYUNKNOWN confirmed", "Screenshot in logbook"],
  "Your own file showing Hunt's last live reading and the inserted crest.",
  "code/gd_fetch.py, data/guadalupe_4jul2025_hydrographs.json")

H("Reproduce the Center Point surprise and Figure 1",
  "Center Point is your best story: the archive goes silent, but the live feed kept sending wrong numbers. You must see it with your own eyes.",
  ["Pull Center Point from the archive: python -I code/gd_fetch.py usgs 08166250 2025-07-04T00:00:00Z 2025-07-08T00:00:00Z > data/mine_cp_usgs.csv",
   "Pull the live-feed copy from Iowa State: python -I code/gd_fetch.py iem GCTT2 2025-07-04T05:00Z 2025-07-08T05:00Z > data/mine_cp_iem.csv",
   "Put both in a spreadsheet side by side for 11:00-16:00 UTC. You should see the archive stop at 6.16 ft (11:15) while the live feed reads 14.25, 18.75, 20.74, 21.28 ft.",
   "Run python -I code/make_figures.py and compare figs/f1_guadalupe.png with your spreadsheet."],
  ["Both files saved", "Side-by-side table made", "Figure regenerated", "Logbook note: what does 'USGS later deleted it' mean?"],
  "A table proving that the gauge kept talking but said the wrong thing.",
  "code/gd_fetch.py, code/make_figures.py, data/guadalupe_4jul2025_hydrographs.json")

H("Write the bounding-box downloader for the new API",
  "The old USGS service (waterservices.usgs.gov) has planned outages from January 2027 and shuts on 22 February 2027, so your pipeline must use the new API from the start.",
  ["Read the API docs page for the 'monitoring-locations' and 'continuous' collections at api.waterdata.usgs.gov/ogcapi/v1/. Find how to filter by bbox and by parameter_code=00065 (gage height).",
   "Write code/bbox_pull.py: given a bbox and dates, (1) list stream sites in the box that have 00065, (2) call usgs_continuous() for each, (3) save one CSV per gauge into data/raw/<event>/.",
   "Test it on the Texas box -100.6,29.6,-97.8,31.4 for 3-7 July 2025. Count gauges. My pilot found 89.",
   "If the bbox filter does not exist on 'continuous', use the monitoring-locations list and loop. Write in your logbook which approach worked."],
  ["bbox_pull.py written", "Texas box pulled", "Gauge count recorded (expect about 89)"],
  "A folder of raw CSVs for Texas that you downloaded yourself.",
  "code/gd_fetch.py")

H("Pull the other six pilot floods",
  "Re-running all seven floods lets you check my 387-gauge table line by line.",
  ["Run bbox_pull.py for Helene, Harvey, Kentucky, Vermont, Waverly and Yellowstone using the boxes and dates in Part 3 of this guide.",
   "Run them one at a time and leave the computer on if needed. If you get HTTP 429 (too many requests), wait and retry; the script already backs off.",
   "Count gauges per event and compare with my counts: Helene 84, Harvey 93, Kentucky 34, Vermont 45, Waverly 14, Yellowstone 28.",
   "Commit the code (not the raw data if it is over 50 MB; add data/raw to .gitignore and keep a backup on a USB drive)."],
  ["6 events pulled", "Counts compared", "Differences written down"],
  "Seven folders of raw data and a small table: my count vs. your count.",
  "data/stations_7floods_v3.csv")

H("Re-run the gap rule and compare with my table",
  "If you cannot reproduce 28 of 116, nothing else in the project stands.",
  ["Write code/run_census.py: for each raw CSV call gd_gaps.analyze(); write one row per gauge with the same columns as data/stations_7floods_v3.csv.",
   "Merge your output with mine on the site column. Count disagreements in dark1h.",
   "Target: at least 95% agreement. If lower, open 3 disagreeing gauges and find out why (approved data revised? different window? new qualifiers?).",
   "Record the final numbers for big rises (20 ft or more) and small rises (under 5 ft)."],
  ["run_census.py works", "Agreement percentage computed", "Reasons for disagreements noted"],
  "Your own version of 'X of Y big-rise gauges went dark', with a written explanation of any gap from my 28/116.",
  "code/gd_gaps.py, data/stations_7floods_v3.csv")

H("Kill test, part 1: hand-check 15 gauges",
  "Automatic rules make mistakes. You need to know how often before you trust a percentage.",
  ["Write code/plot_gauge.py: plots one gauge's archive series (blue) and live-feed series (orange dashed) for an event, with the event crest marked.",
   "Pick 15 gauges: 10 from the 28 dark big-rise gauges and 5 big-rise gauges the rule called healthy.",
   "For each plot decide: real outage during rise/crest? inserted crest? maintenance gap? Write the label in a spreadsheet (hand_labels.csv) with a one-line reason.",
   "Keep the labelling rules on one card and do not change them halfway."],
  ["plot_gauge.py works", "15 labels with reasons"],
  "A spreadsheet of 15 hand labels.",
  "data/stations_7floods_v3.csv, data/live_feed_dark_gauges_classified.csv")

H("Kill test, part 2: hand-check 15 more gauges",
  "30 checks give you a usable error estimate for the automatic rule.",
  ["Label 15 more: 10 more dark big-rise gauges and 5 more 'healthy' ones.",
   "Compute: of the gauges the rule called dark, what share you agree are real outages (precision); of the healthy ones, how many were really dark (misses).",
   "Put both numbers with their counts in the logbook."],
  ["30 labels total", "Precision and miss counts computed"],
  "Two numbers, for example 'rule correct on 19 of 20 dark calls; missed 1 of 10'.")

H("Check my live-feed labels, part 1",
  "My biggest new claim is that many 'dark' gauges were actually sending wrong numbers. You must check every one of the 36.",
  ["Open data/live_feed_dark_gauges_classified.csv. For the first 18 rows, plot archive vs live with plot_gauge.py.",
   "Decide for each: SILENT, FROZEN (same value for hours), UNDER_READ (rising far less than the river), IMPLAUSIBLE (impossible numbers such as 1310.71 or negative), LIVE_PRESENT, or NO_LIVE_DATA.",
   "Where you disagree with my label, write your label and why in a new column 'my_class'."],
  ["18 rows checked", "Disagreements explained"],
  "Half the live-feed table verified by you.",
  "data/live_feed_dark_gauges_classified.csv, code/gd_fetch.py")

H("Check my live-feed labels, part 2",
  "Finishing the check gives you a clean, human-verified benchmark of 36 real failures.",
  ["Do the remaining 18 rows the same way.",
   "Recount the classes with your labels. My counts were SILENT 12, FROZEN 8, UNDER_READ 2, IMPLAUSIBLE 6, LIVE_PRESENT 5, NO_LIVE_DATA 3.",
   "Also check the 7 gauges in data/live_feed_only_outages.csv (silent live, repaired in the archive)."],
  ["36 + 7 rows checked", "Class counts recomputed"],
  "A verified table you can cite as 'hand-checked by the student'.",
  "data/live_feed_only_outages.csv")

H("Go / no-go decision (kill test K1)",
  "Decide with numbers, before investing 160 more hours.",
  ["Apply the K1 rule from Part 5: CONTINUE if at least 10% of big-rise gauges had a hand-confirmed failure (silent, frozen, under-read or implausible) during the rise or crest. My pilot suggests about 24%.",
   "If it fails, switch to Fallback A in Part 5 (data-quality taxonomy only) and rewrite the question.",
   "Write a one-page decision memo in the logbook: numbers, decision, what would change your mind."],
  ["K1 computed", "Decision written and dated"],
  "A signed and dated go/no-go page.",
  "pilot_results_round55.json")

H("Contact experts",
  "A hydrologist mentor makes the interview defensible, and USGS staff can tell you how inserted crests and deleted values are recorded.",
  ["Email the USGS Texas Water Science Center (find the contact on usgs.gov) and your local NWS office or River Forecast Center. Keep it to 5 sentences in your own words.",
   "Ask: (1) Is there a record of when real-time values were received? (2) How are deleted real-time values documented? (3) Could I share my findings with you later?",
   "Email one hydrology or civil-engineering professor at a nearby university asking for a 20-minute call as an informal mentor.",
   "Log every email in the logbook (date, to whom, what you asked)."],
  ["3 emails sent", "Logged"],
  "Three sent emails. Replies are a bonus, not a requirement.")

H("Start DarkWatch, the live logger",
  "Winter storms (Dec-Jan) are your only chance to record real-time outages yourself. Every day you delay is data you lose.",
  ["Copy code/darkwatch.yml to .github/workflows/darkwatch.yml in your repo. Add your key as a repository secret named USGS_API_KEY.",
   "Use data/watchlist.csv (116 big-rise gauges from the pilot). Add about 50 gauges from California, Oregon and Washington, where winter atmospheric rivers cause floods. Find them on waterdata.usgs.gov.",
   "Trigger the workflow by hand (Actions > darkwatch > Run workflow). Check that data/darkwatch_log.csv appears with one row per gauge.",
   "Write in the logbook: start date/time, number of gauges, and that GitHub may delay scheduled runs by several minutes."],
  ["Workflow runs", "Log has rows", "Watchlist expanded"],
  "A log file that grows every 15 minutes on its own.",
  "code/darkwatch.py, code/darkwatch.yml, data/watchlist.csv")

H("Week 1 review",
  "Weekly reviews stop small problems turning into lost weeks.",
  ["Write half a page: what you reproduced, what disagreed, what you decided.",
   "Update the research question if the kill test changed it.",
   "Check DarkWatch has run at least 50 times without errors (open data/darkwatch_log.csv.errors).",
   "Plan Week 2 by copying the next 16 hour titles into your calendar."],
  ["Review written", "DarkWatch healthy", "Week 2 scheduled"],
  "Half a page that a judge could read to see your week 1 progress.")

# ---------------- WEEK 2: literature + pre-registration ----------------
H("Set up a reference manager",
  "You will cite about 25 sources. ISEF forbids AI-generated citations, so every reference must be one you found and opened yourself.",
  ["Install Zotero (free) and the browser connector.",
   "Create a collection 'GaugeDark'. Add the 12 core sources listed in Part 8 by opening each DOI link and saving it.",
   "For each, add a one-line note: why it matters to you."],
  ["Zotero installed", "12 sources saved with notes"],
  "A reference library you can export to any citation style.",
  "Undermind workspace (search list), Part 8 source list")

H("Read Baruah et al. 2026 (the Texas flood paper)",
  "This is the paper that says a failed Hunt gauge stopped the national model from correcting itself. You will be asked about it.",
  ["Open nhess.copernicus.org/articles/26/4753/2026/. Read the abstract, Section 2 and Section 4.",
   "Write in your words: (a) what nudging is, (b) what happened when Hunt failed, (c) what the authors say was the MAIN cause of the under-prediction (rainfall error).",
   "Note the gauge-ID typo in the paper (08615500 instead of 08165500). Small details like this impress judges if you mention them carefully."],
  ["Paper read", "3 notes written"],
  "One paragraph you could say out loud in 30 seconds.")

H("Read Quintero et al. 2026 (forecast skill with and without gauges)",
  "It gives your stakes in numbers: with assimilated gauges the model detects about 80% of high-flow events in the first forecast hour; without them, about 10%.",
  ["Find it via doi.org/10.1175/jhm-d-26-0026.1. Read abstract, methods summary and results figures.",
   "Write one careful sentence: their comparison is 'with vs without assimilation', NOT a study of gauge outages. Your project links the two.",
   "Save the numbers (0.8 vs 0.1 median probability of detection at hour 1) in your notes."],
  ["Read", "Careful sentence written"],
  "A stakes sentence that is accurate and not exaggerated.")

H("Learn how gauges feed forecasts (Seo 2021, Gharamti 2021)",
  "You need a simple, correct mental picture of the data path from gauge to warning.",
  ["Skim Seo et al. 2021 (doi.org/10.1111/1752-1688.12955) and the introduction of Gharamti et al. 2021 (doi.org/10.5194/hess-25-5315-2021).",
   "Draw the data path in your logbook: sensor > data logger > GOES satellite radio > NOAA HADS > NWS / National Water Model; and separately > USGS database > later review and edits.",
   "Mark on the drawing where each of your failure types happens (silent, frozen, under-read, implausible, deleted later)."],
  ["Diagram drawn", "Failure types placed on it"],
  "A hand-drawn diagram you will later redraw for your poster.")

H("Read the USGS sources on missing record and inserted peaks",
  "These are your closest 'prior measurements' and they show the effect is known but not measured nationally.",
  ["Read USGS Fact Sheet 2016-3027 (Texas floods 2015): note the network reliability figure (about 98% of values recovered) and the gauge that stopped at 40 ft.",
   "Read Studley 2001 (USGS FS-009-01, Kansas missing gage-height record): causes of missing record, with no flood breakdown.",
   "Read USGS Office of Surface Water memo 2006.05: it tells offices to insert surveyed peaks into the unit values. This explains your 'inserted crests'.",
   "Write 3 bullet points: what USGS already measures, and what it does not."],
  ["3 sources read", "3 bullets written"],
  "A clear statement of the gap you fill.")

H("Read SHEM and the virtual-gauge patent",
  "Someone already estimates data for gauges that stop. You must know exactly how your work differs.",
  ["Read the abstract of Petty & Dhingra 2018, SHEM (doi.org/10.1111/1752-1688.12555), and the claims of US Patent 11,238,356.",
   "Make a 2-column table: what SHEM/patent does vs what you do (they estimate discharge from clustered gauges; you (1) measure how often and how gauges fail by flood size, (2) detect frozen/wrong values, (3) test on held-out floods at the crest).",
   "Be generous in the interview: 'my virtual gauge is a baseline in the SHEM tradition; my contribution is the measurement and the detector.'"],
  ["Read", "Comparison table done"],
  "A table that pre-empts the 'this already exists' question.")

H("Read the gap-filling evidence (Vlah 2024, Harvey 2012, Luna 2020)",
  "These tell you which baseline to beat. Simple donor-gauge regression often beats deep learning.",
  ["Vlah et al. 2024 (doi.org/10.5194/hess-28-545-2024): regression beat LSTMs in 21 of 23 comparisons; peak skill not reported.",
   "Harvey et al. 2012 (doi.org/10.2166/NH.2012.110): compares infilling methods on UK records.",
   "Luna et al. 2020 (doi.org/10.3390/s20216354): spline vs neural nets for river stage; no flood-specific results.",
   "Write: 'Prior gap-filling papers mostly test random gaps in ordinary flow; few test the crest of floods.'"],
  ["3 read", "Gap sentence written"],
  "A justification for testing at flood crests.")

H("Read the analogue: rain sensors that black out in heavy rain",
  "Polz et al. 2023 show microwave-link rain sensors lose signal exactly in the heaviest rain. This is the same failure mode in a different sensor, and a strong citation.",
  ["Read Polz et al. 2023 (doi.org/10.1029/2022EA002456) and the abstract of Graf et al. 2023.",
   "Read Hughes et al. 2015 on detecting reporting anomalies (doi.org/10.18293/SEKE2015-181).",
   "Write 2 sentences connecting them to your 'silence is a signal' idea."],
  ["Read", "2 sentences"],
  "One analogue paragraph for your introduction.")

H("Search for anything newer than November 2026",
  "Novelty claims go stale. Check again before writing.",
  ["Search Google Scholar, Semantic Scholar and arXiv for: 'stream gauge outage flood', 'streamgage failure rising limb', 'missing real-time stage data flood warning', 'gage malfunction flood peak'. Restrict to 2025-2027.",
   "Record each search string, date and number of relevant hits in a table.",
   "Set a Google Scholar alert for 'streamgage' AND 'outage'.",
   "If you find a paper measuring the same thing nationally, stop and write it down; then read Fallback B in Part 5."],
  ["Search table done", "Alert set"],
  "A dated search log. Judges like seeing how you checked novelty.")

H("Write the literature-gap table",
  "This table becomes the backbone of your introduction.",
  ["Make columns: Topic | Who did it | What they found | What they did NOT do.",
   "Rows: gauge damage counts (USGS), event data recovery (USGS FS 2016-3027), missing-record causes (Studley), assimilation value (Seo, Quintero), virtual gauges (SHEM, Vlah), sensor blackout (Polz), Texas 2025 (Baruah).",
   "Last row: 'This project'. Fill it last."],
  ["Table complete with 8 rows"],
  "A one-page table you can paste into the paper.")

H("Draft introduction, version 0",
  "Writing early exposes gaps in your understanding while there is still time to fix them.",
  ["Write 300-400 words in your own words: the Hunt story (2 sentences), why gauges matter for warnings, what is known, what is missing, your question.",
   "No AI writing. You may ask a teacher to read it.",
   "Save as paper/intro_v0.docx with today's date."],
  ["Draft saved"],
  "A rough introduction. It will change, and that is fine.")

H("Pre-register the flood-selection rule",
  "Choosing floods after seeing results is the easiest way to fool yourself. Fix the rule first.",
  ["Write the rule BEFORE looking at any outage data. Suggested: every USGS Short-Term Network (STN) flood event from 2017 to 2025 in the lower 48 with at least 50 surveyed high-water marks, plus any flood with 10 or more deaths in the NOAA Storm Events database.",
   "Write how you will draw the box around each flood (for example: the bounding box of its high-water marks plus 0.25 degrees) and the date window (first to last HWM date, plus 1 day each side).",
   "Commit the rule as prereg.md to GitHub. The commit time proves it came first."],
  ["prereg.md committed"],
  "A dated, public rule that decides your floods for you.")

H("Build the flood list",
  "Applying your rule gives a fair sample instead of famous floods only.",
  ["Open stn.wim.usgs.gov (Flood Event Viewer). List events and their HWM counts. Apply your rule.",
   "Make data/events.csv with columns: event, start, end, west, south, east, north, n_hwm, source.",
   "Expect roughly 15-30 events. If you get more than 40, keep the rule and just note that you may sample later."],
  ["events.csv made", "Number of events recorded"],
  "A list of floods you did not hand-pick.")

H("Split into development and test floods",
  "Tune your methods only on development floods. Report results only on test floods.",
  ["Mark the 7 pilot floods as 'dev'. Everything else from events.csv is 'test'.",
   "If a pilot flood is not on your list, still keep it as 'dev' (note it).",
   "Commit events.csv. From now on, never change a threshold after looking at a test-flood result."],
  ["Split committed"],
  "A dev/test split that makes your later accuracy numbers honest.")

H("DarkWatch maintenance",
  "A logger that silently broke is worse than none.",
  ["Open the Actions tab. Count successful runs in the last week. Note any failures.",
   "Open darkwatch_log.csv in a spreadsheet. Check that times are advancing and gauges are present.",
   "If any gauge shows minutes_since_obs over 180, look it up on waterdata.usgs.gov and write what you see."],
  ["Run count logged", "Any silent gauges noted"],
  "A short health note in your logbook.",
  "code/darkwatch.py")

H("Week 2 review and research plan final",
  "Your research plan should now be complete, in your words, and signed off.",
  ["Finish the research plan: question, 4 hypotheses (Part 4), procedures (download, detect, hand-check, model, evaluate), risk and safety (none physical; data ethics), data analysis (logistic regression, precision/recall, blank-out tests), bibliography.",
   "Ask your sponsor to sign Form 1B if not done.",
   "Plan Week 3."],
  ["Plan complete", "1B signed"],
  "A finished research plan in your own words.")

# ---------------- WEEK 3: national pipeline ----------------
H("Write the census downloader",
  "Scaling from 7 floods to your full list is the main data job of the project.",
  ["Extend bbox_pull.py into census_pull.py that loops over events.csv and saves data/raw/<event>/<site>.csv.",
   "Add caching: skip files that already exist, so a crash does not mean starting over.",
   "Add a log file listing every site and whether the pull succeeded."],
  ["census_pull.py written", "Caching works (run twice; second run is instant)"],
  "A downloader you can restart safely.",
  "code/gd_fetch.py")

H("Test the census on 3 events",
  "Catch bugs on a small run before the big one.",
  ["Run census_pull.py on 3 test events.",
   "Check pagination: does any gauge return exactly 10,000 rows? If so, you are missing pages; fix the 'next link' loop.",
   "Time it, and estimate the total time for all events."],
  ["3 events pulled", "Pagination checked", "Time estimate written"],
  "Confidence the downloader works and an estimate of how long the full run takes.")

H("Full census pull, batch 1",
  "Get as much data as possible before USGS's planned January outages.",
  ["Run census_pull.py on the first third of events. Let it run; meanwhile read the log for errors.",
   "Back up data/raw to a USB drive or cloud folder."],
  ["Batch 1 done", "Backup made"],
  "One third of all raw data on disk, backed up.")

H("Full census pull, batch 2",
  "Same as batch 1, for the second third of the events.",
  ["Run the second third. Fix any site that failed in batch 1 by re-running (the cache skips finished ones).",
   "Back up again."],
  ["Batch 2 done", "Batch 1 failures retried"],
  "Two thirds downloaded.")

H("Full census pull, batch 3",
  "Finishing the census unblocks all of the analysis.",
  ["Run the final third. Re-run failures.",
   "Write the final counts: events, gauges, gauge-event pairs, failed pulls."],
  ["All events pulled", "Counts written"],
  "A complete raw dataset with a short data report.")

H("Pull gauge metadata",
  "Drainage area, reporting interval and past record peaks may explain which gauges fail.",
  ["From the new API 'monitoring-locations' collection, get drainage area, state, HUC and coordinates for each census site.",
   "Get each gauge's annual peak record (the peaks service; check current docs because the old /nwis/peak page is being retired) and compute the highest stage BEFORE each event.",
   "Save data/site_meta.csv."],
  ["site_meta.csv made", "Prior-record stage computed for most gauges"],
  "A table of gauge features for the model.")

H("Map USGS gauges to NWS IDs",
  "You need NWS IDs to look up the live feed.",
  ["Download hads.ncep.noaa.gov/USGS/ALL_USGS-HADS_SITES.txt (or use usgs_to_nwsli() in gd_fetch.py).",
   "Join it to your census gauges. Report the share mapped (the pilot mapped 359 of 387, 93%).",
   "List unmapped gauges; they will have 'no live data'."],
  ["Mapping done", "Share mapped recorded"],
  "data/census_nwsli.csv.",
  "data/usgs_to_nwsli_map.json, code/gd_fetch.py")

H("Pull the live feed, batch 1",
  "The live feed is what forecasters actually saw. It is the heart of your new finding.",
  ["Loop iem_hads() over half of the mapped gauges. Keep the 2.5-second pause; Iowa State rate-limits with HTTP 429 (the pilot hit this on 190 of 359 requests and had to retry slowly).",
   "Save data/live/<event>/<nwsli>.csv."],
  ["Batch 1 done", "429 errors retried"],
  "Half the live-feed files.",
  "code/gd_fetch.py")

H("Pull the live feed, batch 2",
  "This completes the live record for the census.",
  ["Run the rest. Retry failures.",
   "Count stations with 'Error, no results' (no live record)."],
  ["All done", "No-record count noted"],
  "The full live-feed dataset.")

H("Pull the live feed, gap check",
  "You need to know whether Iowa State's own archive has gaps (their server, not the gauge).",
  ["For each event, count how many gauges have no live data at the same time. If 80% or more of gauges in an event are silent at the same moment, it is probably an archive outage, not gauge failures.",
   "Write code that flags such 'network-wide' gaps and excludes them.",
   "Note the number excluded."],
  ["Network-wide gap check written", "Exclusions counted"],
  "Protection against blaming gauges for an archive problem.")

H("Data audit and provenance table",
  "Judges ask 'where exactly did this number come from?'. A provenance table answers it.",
  ["Make a table: dataset | source URL | date pulled | rows | known issues.",
   "Spot-check 5 random gauges by opening them on waterdata.usgs.gov and comparing the maximum stage.",
   "Write it into paper/methods_data.md."],
  ["Table written", "5 spot checks done"],
  "A methods section about data that is already half written.")

H("Port the live-feed classifier to Python",
  "My live classification ran in a browser. You need a tested Python version.",
  ["Write code/gd_live.py with classify(archive_gap, live_series, crest) returning SILENT / FROZEN / UNDER_READ / IMPLAUSIBLE / LIVE_PRESENT, using the rules in Part 3.",
   "Test it on your hand-verified 36 gauges. Target: it reproduces your hand labels on at least 32 of 36.",
   "Where it fails, decide whether the rule or the label is wrong, and log the decision."],
  ["gd_live.py written", "Agreement on 36 measured"],
  "A classifier checked against your own labels.",
  "data/live_feed_dark_gauges_classified.csv")

H("Run the archive gap rule on the census",
  "This produces your main prevalence table.",
  ["Run run_census.py over all census events.",
   "Save data/census_archive.csv.",
   "Do not look at test-flood percentages yet beyond checking that the file has the right number of rows."],
  ["census_archive.csv saved", "Row count correct"],
  "The archive census table.",
  "code/gd_gaps.py")

H("Run the live classifier on the census",
  "This tells you how the live feed behaved for every archive-dark gauge, and finds live-only outages.",
  ["Run gd_live.py for every archive-dark gauge, and run the gap rule on the live series of every gauge.",
   "Save data/census_live.csv."],
  ["census_live.csv saved"],
  "The live census table.")

H("First merged look (development floods only)",
  "A careful first look on dev floods catches bugs without peeking at the test floods.",
  ["Merge the archive and live tables. For dev floods only, recompute the pilot numbers.",
   "If they differ a lot from the pilot, find out why before going further."],
  ["Dev numbers match pilot or differences explained"],
  "Assurance the pipeline is right.")

H("Week 3 review and methods draft",
  "Writing methods while they are fresh saves days later.",
  ["Write 300 words of Methods: data sources, flood selection, gap rule, live classification.",
   "Check DarkWatch health.",
   "Plan Week 4."],
  ["Methods draft saved", "DarkWatch OK"],
  "paper/methods_v0.docx.")

# ---------------- WEEK 4: hand-check + prevalence ----------------
H("Design the hand-check sample",
  "A random, stratified hand check turns 'my rule says' into 'I verified'.",
  ["Randomly sample 100 archive-dark gauge-events (stratified by event) and 50 'healthy' big-rise gauge-events, using a fixed random seed you write down.",
   "Write a one-page labelling protocol: definitions and examples of each label.",
   "Make an empty sheet hand_check_150.csv."],
  ["Sample drawn with seed", "Protocol written"],
  "A fair sample and the rules for labelling it.")

H("Hand-check, gauges 1-25",
  "Each label needs a plot and a reason.",
  ["Plot each with plot_gauge.py (archive + live).",
   "Label: real failure (which class), inserted crest only, maintenance, ice, data removed for other reasons, or no failure.",
   "Write a one-line reason. About 2 minutes per gauge."],
  ["25 labelled"],
  "25 rows filled.")
H("Hand-check, gauges 26-50", "Continue the random sample.", ["Same procedure as the last hour.", "Take a 2-minute break every 10 gauges to stay consistent."], ["50 labelled"], "50 rows filled.")
H("Hand-check, gauges 51-75", "Continue the random sample.", ["Same procedure.", "Re-read the protocol card before you start."], ["75 labelled"], "75 rows filled.")
H("Hand-check, gauges 76-100", "Finish the dark sample.", ["Same procedure."], ["100 labelled"], "All flagged gauges in the sample checked.")
H("Hand-check, healthy gauges 1-25", "Healthy gauges tell you how many outages the rule misses.", ["Plot and label as before.", "Look carefully at the crest: is there a gap or an inserted value the rule missed?"], ["25 healthy labelled"], "Half the miss sample checked.")
H("Hand-check, healthy gauges 26-50", "Finish the miss sample.", ["Same procedure."], ["50 healthy labelled"], "Hand check complete: 150 labels.")

H("Compute the rule's error rates",
  "Every percentage you report must carry its error.",
  ["Precision = confirmed failures / gauges flagged. Miss rate = failures found among 'healthy' / 50.",
   "Compute 95% Wilson confidence intervals (statsmodels proportion_confint, method='wilson').",
   "Write: 'The automatic rule was correct for X of 100 flagged gauge-events (95% CI a-b%).'"],
  ["Precision and miss rate with CIs"],
  "Two error statistics for your methods section.")

H("Fix the rule only if the error is systematic",
  "Changing rules after seeing data is allowed only with a written reason and only using dev floods.",
  ["Look for a pattern in the errors (for example, ice at northern gauges, or 30-minute gauges).",
   "If found, change the rule, record the change in CHANGELOG.md with the date, and re-run.",
   "If not, leave the rule alone and report the error rate."],
  ["Decision logged"],
  "A rule you can defend.")

H("Second-rater agreement",
  "If another person labels the same gauges the same way, your labels are trustworthy.",
  ["Ask a classmate or teacher to label 20 random gauges from your sample using only your protocol card. (They are helping, not being studied; note their help on Form 2A.)",
   "Compute percent agreement and Cohen's kappa (sklearn.metrics.cohen_kappa_score).",
   "Kappa above 0.6 is usually called substantial agreement."],
  ["20 second labels", "Kappa computed"],
  "An agreement number for your methods.")

H("Live vs archive, at census scale",
  "This tests Hypothesis H2: real-time failure is often 'wrong but alive', not silence.",
  ["From census_live.csv, count the classes among archive-dark gauges, by event.",
   "Compute the share 'wrong but alive' (FROZEN + UNDER_READ + IMPLAUSIBLE) among those with live data. Pilot: 16 of 33 (48%).",
   "Compute live-only outages (live silent, archive repaired). Pilot: 7 gauges."],
  ["Class table by event", "H2 share with CI"],
  "The headline table of your project.",
  "data/live_feed_only_outages.csv")

H("Archive vs reality metrics",
  "Quantifies how much the archive misleads anyone who studies floods from it.",
  ["Compute two numbers: (a) share of archive gaps where the live feed actually had data; (b) share of live outages that the archive later repaired.",
   "Give both with CIs. Write one sentence on what this means for researchers who use the archive."],
  ["Both numbers computed"],
  "A finding that is useful to scientists, not just forecasters.")

H("Prevalence figure and table",
  "Your first results figure.",
  ["Make the dose-response bar chart for all floods (dev and test separately), like figs/f2_dose.png.",
   "Make Table 1: by rise bin, gauges, dark (archive), failed (live classes), with CIs."],
  ["Figure saved", "Table 1 saved"],
  "Figure 1 and Table 1 of your paper.",
  "code/make_figures.py, figs/f2_dose.png")

H("DarkWatch midpoint review",
  "Check whether winter storms have produced real outages in your live log.",
  ["Scan darkwatch_log.csv for gauges with minutes_since_obs above 3 times their usual interval.",
   "For each, check if the river was rising (look at earlier rows) and whether an NWS flood warning was active (IEM VTEC browser: mesonet.agron.iastate.edu/vtec/).",
   "Record each candidate outage in darkwatch_events.csv."],
  ["Log scanned", "Candidates recorded"],
  "A list of live outages you caught yourself, even if it is short or empty.",
  "code/darkwatch.py")

H("Draft Results part A (prevalence)",
  "Write while the numbers are fresh.",
  ["Write 250-350 words: how many gauges, how many failed, how failure grows with rise, what the live feed showed.",
   "Every number must come from a file; write the file name in a comment next to it."],
  ["Results A drafted"],
  "paper/results_A_v0.docx.")

H("Week 4 review",
  "Check that you are on schedule for statistics next week.",
  ["Half-page summary. Update the risk list (Part 6) if anything new went wrong.",
   "Plan Week 5."],
  ["Review written"],
  "A clear plan for the modelling week.")
