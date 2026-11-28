from hours_w1_4 import H, HOURS

# ---------------- WEEK 5: statistics (Hours 65-80) ----------------
H("Learn logistic regression on a toy example",
  "You will model 'did this gauge fail? yes/no' from its features. Logistic regression is the standard tool.",
  ["Watch or read one short intro (for example the statsmodels Logit docs example).",
   "In a notebook, make fake data: 200 gauges, failure more likely when rise is large. Fit statsmodels.formula.api.logit('fail ~ rise', data).",
   "Read the coefficient as an odds ratio: exp(coef). Write in your words what 'odds ratio 1.08 per foot' means."],
  ["Toy model fitted", "Odds ratio explained in words"],
  "A notebook proving you understand the method before using it.")

H("Build the feature table",
  "The model can only use what you give it.",
  ["One row per gauge-event: fail (any live or archive failure during rise/crest), rise_ft, max_rise_1h_ft, log10 drainage area, reporting interval, stage above prior record (yes/no), region, event, dev/test.",
   "Check for missing values; decide (and log) how to handle them.",
   "Save data/features.csv."],
  ["features.csv saved", "Missing-value decisions logged"],
  "A clean modelling table.",
  "data/stations_7floods_v3.csv (column max_rise_1h_ft)")

H("Fit the main model with event-clustered errors",
  "Gauges in the same flood are not independent; ordinary p-values would be too optimistic.",
  ["Fit logit('fail ~ np.log1p(rise_ft) + max_rise_1h_ft + log_area + above_record', data=dev+test).",
   "Use cluster-robust standard errors by event: .fit(cov_type='cluster', cov_kwds={'groups': event_codes}).",
   "Report odds ratios with 95% CIs. Note: the pilot's Fisher test (28/116 vs 1/103, p of about 8e-8) ignored clustering; your clustered result is the one to report."],
  ["Model fitted", "Odds ratios with clustered CIs"],
  "Table 2 of your paper: what predicts failure.")

H("Alternative model: event fixed effects",
  "If results change a lot with a different but reasonable model, you must say so.",
  ["Fit the same model with C(event) added (fixed effects).",
   "Compare the rise coefficient with the clustered model. Write whether the conclusion holds."],
  ["Second model fitted", "Comparison sentence"],
  "A robustness check for the paper.")

H("Robustness to your own choices",
  "Your thresholds (1 h, 0.3 ft, 20 ft) are choices. Show they do not drive the result.",
  ["Re-run with: 3-hour gaps instead of 1 hour; rise measured as share of prior record instead of feet; excluding inserted-crest-only cases.",
   "Make a small table: setting | odds ratio for rise | CI."],
  ["3 variants run", "Table made"],
  "A sensitivity table.")

H("Time-to-failure (survival) analysis",
  "Asks a sharper question: as water rises past a level, how fast does the risk of failure grow?",
  ["pip install lifelines. For each big-rise gauge, measure 'time' as feet risen until failure (or until crest, if no failure = censored).",
   "Plot a Kaplan-Meier curve of 'still working' vs feet risen, split by above/below the prior record.",
   "Save figure."],
  ["KM curve plotted"],
  "A curve showing how gauges drop out as the river climbs.")

H("Interpret the record-stage effect",
  "Tests Hypothesis H1b: gauges fail more once the river goes above anything they have seen.",
  ["Compare the two KM curves with a log-rank test (lifelines.statistics.logrank_test).",
   "Write what the result means physically (shelters built above old records get flooded, e.g. the 2015 Blanco River gauges in USGS FS 2016-3027).",
   "If there is no difference, say so plainly; it is still a finding."],
  ["Test run", "Interpretation written"],
  "One paragraph for Results B.")

H("Leave-one-event-out check",
  "Harvey has 59 of the 116 pilot big-rise gauges. One flood must not decide your answer.",
  ["Re-fit the main model dropping one event at a time. Record the rise odds ratio each time.",
   "Plot the 15-30 estimates as dots. If one event flips the conclusion, name it in the paper."],
  ["LOEO done", "Plot saved"],
  "Evidence the result is not one flood's story.")

H("Make Figures 2 and 3",
  "Clear figures win poster judging.",
  ["Figure 2: odds ratios with CIs (a forest plot).",
   "Figure 3: KM survival curves.",
   "Check colours with a colour-blind simulator (e.g. Coblis website)."],
  ["2 figures saved"],
  "Publication-ready figures.")

H("Draft Results part B (drivers)",
  "Turns numbers into findings.",
  ["Write 250-300 words: what predicts failure, how big the effect is, how robust it is.",
   "Use phrases like 'associated with', not 'causes'."],
  ["Results B drafted"],
  "paper/results_B_v0.docx.")

H("Decision K3: does prevalence hold on test floods?",
  "This is where the main hypothesis H1 is supported, contradicted or left unresolved, using the rule in Part 5.",
  ["Compute the failure rate for big vs small rises on TEST floods only, with clustered CIs.",
   "Apply the K3 criteria. Write the verdict and the numbers on a dated logbook page.",
   "If contradicted or unresolved, follow the matching branch in Part 5. Do not change the hypothesis after the fact."],
  ["K3 verdict written"],
  "An honest verdict on H1.")

H("Mentor check-in, part 1",
  "An expert catches mistakes you cannot see.",
  ["Send your mentor (or teacher) Table 1, Table 2 and Figures 1-3 with a 5-line summary.",
   "Ask: 'What would a hydrologist object to?'"],
  ["Sent"],
  "Feedback requested.")

H("Act on feedback",
  "Use the reply, or your own review if none came.",
  ["List every comment. For each, write: accept and fix / disagree because ...",
   "Make the fixes that take under 30 minutes now; schedule the rest."],
  ["Comments triaged"],
  "A response list in your logbook.")

H("DarkWatch check and data backup",
  "Protect the only data you can never re-download.",
  ["Download the DarkWatch log and save it to a second place.",
   "Update darkwatch_events.csv with new candidate outages."],
  ["Backup done", "Events updated"],
  "Two copies of your live log.")

H("Catch-up hour (default: extend the hand check)",
  "Every week has one hour reserved for slippage.",
  ["If behind, finish the most overdue task.",
   "If on time, hand-label 25 more random gauges from test floods to tighten the precision CI."],
  ["Either catch-up done or 25 extra labels"],
  "No overdue tasks.")

H("Week 5 review",
  "Lock the statistical results before building the detector.",
  ["Summarise H1 verdict. Freeze Table 1, Table 2 and Figures 1-3 (copy to paper/frozen/).",
   "Plan Week 6."],
  ["Frozen copies saved"],
  "A stable set of prevalence results.")

# ---------------- WEEK 6: detector (Hours 81-96) ----------------
H("Write the detector specification",
  "Engineering starts with a spec: what goes in, what comes out, what counts as success.",
  ["Inputs: only data available at time t (the gauge's own past readings, neighbours' past readings).",
   "Outputs every 15 minutes: OK, or ALARM with a reason: SILENT, FROZEN, UNDER_READ, IMPLAUSIBLE.",
   "Success metrics (from Part 5): episode precision, recall, false alarms per 100 gauge-days, lead time. Write the spec in detector_spec.md."],
  ["Spec written"],
  "A one-page spec judges can read.")

H("Silence rule",
  "Port the pilot rule into the detector.",
  ["In code/gd_detect.py, write silent_alarm(series, now): fires when no reading for more than 2 times the usual interval AND the stage rose at least X ft in the hour before going quiet.",
   "Start with X = 0.5 ft (the pilot's best balance: 19 of 28 caught, 10 false alarms, in-sample).",
   "Unit-test it on Hunt: it must fire at 09:45 UTC (4:45 am CDT)."],
  ["silent_alarm written", "Hunt test passes"],
  "The first detector rule, tested.",
  "code/gd_alarm.py, code/test_gd_gaps.py (Hunt data)")

H("Frozen rule",
  "Cypress Creek repeated about 128.04 ft for 19.7 hours while the river rose to 129.97 ft. A silence alarm never sees that.",
  ["Write frozen_alarm: fires when the last N readings (start N = 8) vary by less than 0.05 ft AND (the gauge was rising before, OR an upstream neighbour is rising).",
   "Test on the FROZEN gauges in your verified table; it should catch most of them.",
   "Test on 20 calm, healthy gauges at low flow; it must NOT fire (low flow is naturally flat; that is why the 'rising' condition matters)."],
  ["frozen_alarm written", "Tested on frozen + calm gauges"],
  "A rule for stuck sensors.",
  "data/live_feed_dark_gauges_classified.csv")

H("Implausible rule",
  "Values like 1310.71 or -631.96 are error codes or broken sensors, not water.",
  ["Write implausible_alarm: fires when a value is below (record minimum - 5 ft), above (record maximum + 15 ft), or jumps more than 10 ft in one reading interval.",
   "Test on the IMPLAUSIBLE gauges. Check it does not fire on Kerrville's real 11 ft jump in 15 minutes (10:45-11:00 UTC, 14.60 to 26.06 ft); adjust the jump limit using dev floods only."],
  ["Rule written", "Kerrville false alarm avoided"],
  "A rule for impossible readings.",
  "data/guadalupe_4jul2025_hydrographs.json (Kerrville)")

H("Find each gauge's neighbours (NLDI)",
  "To spot a gauge that under-reads, you compare it with gauges up and downstream.",
  ["Use the USGS Network-Linked Data Index: api.water.usgs.gov/nldi/linked-data/nwissite/USGS-<site>/navigation/UM/nwissite?distance=100 (checked working 17 Nov 2026; it lists Hunt upstream of Kerrville) (upstream) and DM (downstream).",
   "Save data/neighbours.csv: site, neighbour, direction, river distance.",
   "Check by hand for Guadalupe: Hunt > Kerrville (abv Bear Ck, then at Kerrville) > Center Point > Comfort."],
  ["neighbours.csv built", "Guadalupe order verified"],
  "A river-network map in table form.")

H("Under-read rule",
  "Center Point read about 21 ft near a 39.61 ft crest while Kerrville upstream had just crested at 34.29 ft.",
  ["Write under_read_alarm: fires when the upstream neighbour rose more than R ft in the last T hours (T = travel time) but this gauge rose less than a fraction F of that.",
   "Start with R = 10 ft, F = 0.3. Tune on dev floods only.",
   "Test on Center Point 4 July 2025: when would it fire?"],
  ["Rule written", "Center Point test result logged"],
  "A rule for gauges that keep talking but say too little.")

H("Assemble the detector and the replay harness",
  "Replay = feed past data in 15-minute steps as if it were live, and record every alarm.",
  ["Write replay.py: for each gauge-event, step through time, call all four rules with only past data, log alarms with reasons.",
   "Run on 2 dev floods. Check the log by eye."],
  ["replay.py works", "Alarm logs look sensible"],
  "A machine that tells you what the detector would have done in a past flood.")

H("Tune thresholds on development floods, then lock",
  "Tuning on dev floods and locking the values before touching test floods is what makes your accuracy believable.",
  ["Try 3-4 values for each threshold on dev floods. Choose by best F1 score (balance of precision and recall), and prefer simpler values when ties occur.",
   "Write the final values in thresholds.json and commit. Write 'LOCKED' and the date in the logbook."],
  ["Thresholds chosen", "thresholds.json committed"],
  "Locked settings. Do not edit them again.")

H("Build the baselines",
  "Your detector only matters if it beats what already exists.",
  ["Baseline 1: plain missing-data flag (any gap of 1 hour or more). Pilot: caught 28 of 28 but with 129 false alarms.",
   "Baseline 2: simple range check (value outside the gauge's historical min-max).",
   "Baseline 3: silence rule alone.",
   "Run all on dev floods with replay.py."],
  ["3 baselines run"],
  "The comparison you will show on your poster.",
  "code/gd_alarm.py")

H("Define and compute the metrics",
  "Precise definitions stop arguments in the interview.",
  ["Failure episode = a hand- or rule-labelled failure from Week 4. A hit = an alarm during the episode's first 2 hours.",
   "Compute precision, recall, false alarms per 100 gauge-days of calm data, and median lead time (alarm time minus the time the crest reached the next downstream gauge).",
   "Write metrics.py and test it on a tiny made-up example where you know the answer."],
  ["metrics.py written and tested"],
  "Unambiguous scoring code.")

H("Replay the Guadalupe on 4 July 2025",
  "This is your demo: what would the detector have said, and when?",
  ["Run replay.py for Hunt, Center Point, Kerrville and Comfort.",
   "Write a timeline: Hunt silent alarm about 4:45 am CDT; Kerrville starts rising 5:15 am, crests 6:30 am; Center Point archive ends 6:15 am; when does your under-read alarm fire?",
   "Be careful: do not claim the alarm would have saved lives. Say what information it would have added, and when."],
  ["Timeline written"],
  "The 4 July timeline for your poster.",
  "data/guadalupe_4jul2025_hydrographs.json")

H("Write the detector methods",
  "Methods are easiest to write right after building.",
  ["Write 300 words: each rule, its inputs, thresholds (locked values), baselines, metrics.",
   "Include a small flowchart."],
  ["Methods C drafted"],
  "paper/methods_detector_v0.docx.")

H("Clean code and add tests",
  "Clean code is part of 'Build' quality, and judges may look.",
  ["Add a unit test for each rule using real examples (Hunt, Cypress Creek, Center Point, one IMPLAUSIBLE gauge).",
   "Run all tests. Add docstrings. Commit."],
  ["4 rule tests pass"],
  "A tested detector.")

H("Stress test on calm data",
  "A detector that cries wolf every night will be switched off. Measure false alarms where nothing is happening.",
  ["Pull 30 days of ordinary (non-flood) data for 50 random census gauges from the new API.",
   "Run replay.py with the locked thresholds. Count alarms per 100 gauge-days, by rule.",
   "If one rule fires a lot on calm data, record it. Do NOT re-tune (thresholds are locked); report it as a known weakness."],
  ["Calm-data run done", "False alarms per 100 gauge-days by rule"],
  "A false-alarm rate on ordinary days, for Table 3.")

H("Catch-up hour (default: extra frozen-rule tests)",
  "Reserved slippage hour.",
  ["Finish anything overdue.",
   "If nothing is overdue, test the frozen rule on 20 more calm gauges in winter (DarkWatch log) to check false alarms."],
  ["Catch-up done"],
  "No overdue tasks.")

H("Week 6 review",
  "Confirm the detector is locked before evaluation.",
  ["Check thresholds.json has not changed since locking (git log).",
   "Plan Week 7."],
  ["Lock verified"],
  "A locked detector ready for honest testing.")

# ---------------- WEEK 7: virtual gauge (Hours 97-112) ----------------
H("Choose virtual-gauge pairs",
  "A virtual gauge estimates a silent gauge from a neighbour upstream.",
  ["From neighbours.csv choose pairs where the upstream gauge is within about 12 hours of river travel.",
   "Keep pairs with at least 3 past floods available for training (before each test event).",
   "List them in pairs.csv."],
  ["pairs.csv made"],
  "A list of pairs to test.")

H("Pull training floods for each pair",
  "A fitted relation needs past floods.",
  ["For each pair, find the 5 highest annual peaks before the test event (peak file) and pull 3 days around each from the new API.",
   "Save under data/train/<pair>/."],
  ["Training data pulled"],
  "Historic flood data for every pair.")

H("Fit the stage-to-stage regression",
  "This replaces my naive 'copy the upstream change' with a learned relation, which is what the 2-ft target needs.",
  ["For each pair, find the travel-time lag by cross-correlating 15-minute changes on TRAINING floods only.",
   "Fit downstream = a + b x upstream(t - lag) on training floods (also try a quadratic term). Use the regress option in gd_virtual.blank_out().",
   "Save coefficients in vg_models.json."],
  ["Models fitted", "Lag from training data only"],
  "One small model per pair.",
  "code/gd_virtual.py")

H("Optional: add rainfall",
  "Rain upstream can explain rises the upstream gauge does not see (like the ungauged South Fork above Hunt).",
  ["Only if on schedule: get basin-average radar rainfall (for example the IEM MRMS archive) for 2-3 pairs.",
   "Add rain in the last 3 hours as a second predictor. Compare error with and without it.",
   "If behind schedule, skip and list it as future work."],
  ["Done or consciously skipped"],
  "A decision, either way.")

H("Blank-out tests on test floods",
  "This is the honest test of the virtual gauge: hide a real rising limb, estimate it, compare with the truth.",
  ["For each pair and test flood, hide the downstream gauge from rise start to crest.",
   "Estimate with: hold-last-value, naive transfer, fitted regression, and the oracle line (for reference only).",
   "Record RMSE and crest error for each. The pilot's naive transfer missed Texas crests by 9-20 ft; your fitted model must do better."],
  ["All blank-outs run", "Results table saved"],
  "The virtual-gauge results table.",
  "code/gd_virtual.py, pilot_results_round55.json (P5)")

H("Test on a real failure: Center Point",
  "A blanked healthy gauge is a simulation; Center Point is a real failure with a surveyed crest (39.61 ft).",
  ["Use the Kerrville to Center Point pair, fitted on earlier floods.",
   "Estimate Center Point's crest on 4 July 2025 and compare with 39.61 ft and with what the live feed said (about 21 ft).",
   "Report the error honestly, even if large."],
  ["Estimate made", "Compared with survey and live feed"],
  "One real-world validation number.",
  "data/guadalupe_4jul2025_hydrographs.json")

H("Add uncertainty to the virtual gauge",
  "A best guess without a range is dangerous in a flood.",
  ["From training residuals, compute a 90% prediction interval for each estimate.",
   "On blank-out tests, check coverage: how often does the truth fall inside the interval? Target about 90%.",
   "If coverage is poor at crests, say so."],
  ["Intervals computed", "Coverage measured"],
  "Estimates with honest error bars.")

H("Decision K5: does the virtual gauge work?",
  "Supported, contradicted, or unresolved under the K5 rule in Part 5.",
  ["Compute the median crest error of the fitted model on test floods with a bootstrap CI.",
   "Apply K5. Write the verdict.",
   "If it fails, keep it in the paper as a negative result: 'neighbour-based estimates were not accurate enough at crests.'"],
  ["K5 verdict written"],
  "An honest verdict on H4.")

H("Virtual-gauge figure",
  "Shows the comparison at a glance.",
  ["Grouped bars: crest error by method across test pairs (like figs/f5_virtual.png, but with your fitted model and test floods).",
   "Add one example hydrograph: truth, estimate, interval."],
  ["Figure saved"],
  "Figure 5 of your paper.",
  "code/make_figures.py")

H("Draft Results part C (virtual gauge)",
  "Write while fresh.",
  ["250 words: methods compared, errors, real-failure check, verdict."],
  ["Drafted"],
  "paper/results_C_v0.docx.")

H("Build the demo, part 1",
  "A working replay on a laptop makes the interview memorable.",
  ["Make a simple Streamlit app (pip install streamlit) or a static HTML page: pick a past flood, press play, watch readings arrive every 15 minutes with alarms appearing.",
   "Start with the Guadalupe 4 July 2025 data you already have."],
  ["App skeleton runs"],
  "A demo that plays one flood.")

H("Build the demo, part 2",
  "Finish the demo so it works offline.",
  ["Show the virtual-gauge estimate as a dashed line when a gauge goes silent or is flagged.",
   "Make it run with no internet (judging halls often have bad Wi-Fi, and the old USGS service is being retired)."],
  ["Demo works offline"],
  "A demo you can run anywhere.")

H("Summarise DarkWatch (December to mid-January)",
  "Your own live log is evidence nobody else has.",
  ["Count gauge-hours logged, candidate outages, and which candidates were confirmed by later USGS data (repaired? deleted? real?).",
   "Run the detector on the DarkWatch log. Did it alarm on any real event?",
   "Write 150 words and a small table."],
  ["Summary written"],
  "A live-evidence paragraph for the paper.",
  "code/darkwatch.py")

H("Mentor check-in, part 2",
  "Second expert look before writing up.",
  ["Send detector results, virtual-gauge results and the demo link or video."],
  ["Sent"],
  "Feedback requested.")

H("Catch-up hour (default: more blank-out pairs)",
  "Reserved slippage hour.",
  ["Finish overdue work, or add 3 more pairs to the blank-out test."],
  ["Done"],
  "No overdue tasks.")

H("Week 7 review",
  "All three parts of the project now have results.",
  ["List the verdicts for H1-H4 on one page.",
   "Plan Week 8."],
  ["Verdict page written"],
  "One page with four verdicts.")

# ---------------- WEEK 8: held-out evaluation (Hours 113-128) ----------------
H("Run the locked detector on test floods",
  "This is the result that matters for H3. No tuning allowed.",
  ["Run replay.py with thresholds.json on all test floods and all baselines.",
   "Save results/test_alarms.csv.",
   "Commit the output before looking at summary numbers, so you cannot quietly re-run."],
  ["Run done", "Output committed"],
  "Locked test results.")

H("Compute test metrics with bootstrap intervals",
  "Resampling floods (not gauges) gives honest uncertainty.",
  ["Bootstrap by event (1,000 resamples): precision, recall, false alarms per 100 gauge-days, lead time.",
   "Make Table 3: detector vs 3 baselines with 95% intervals."],
  ["Table 3 made"],
  "Your main engineering result.")

H("Is the detector really better?",
  "Differences can be noise.",
  ["Paired bootstrap: in each resample compute (detector F1 - baseline F1). Report the share of resamples where the detector wins.",
   "Apply the K4 rule from Part 5. Write the verdict for H3."],
  ["Comparison done", "K4 verdict written"],
  "A verdict on H3.")

H("Error analysis",
  "Reading failures teaches more than averages do.",
  ["Plot 10 missed failures and 10 false alarms.",
   "Group them by cause (for example: gauge failed before rising; slow rivers; tidal gauges; ice).",
   "Write what a version 2 would change."],
  ["20 cases reviewed", "Causes grouped"],
  "An error-analysis paragraph.")

H("Live evaluation on DarkWatch",
  "Real-time data is the strictest test.",
  ["Run the locked detector on the DarkWatch log.",
   "For each alarm, check later USGS data: was it a real problem?",
   "Report counts even if small (for example '3 alarms, 2 confirmed')."],
  ["Live evaluation done"],
  "A small but real-time result.",
  "code/darkwatch.py")

H("Robustness of the detector",
  "Show results do not depend on one choice.",
  ["Re-run with each threshold 25% higher and lower. Leave-one-event-out recall.",
   "Small table."],
  ["Robustness table"],
  "Evidence of stability.")

H("Final figures",
  "Finish all figures to the same style.",
  ["Figure 4: detector vs baselines (like figs/f4_alarm.png, but test floods).",
   "Figure 6: Guadalupe timeline with alarms.",
   "Same fonts, colours and units across all figures."],
  ["All figures final"],
  "A consistent figure set.",
  "code/make_figures.py")

H("Write the Discussion",
  "Explains what the results mean and do not mean.",
  ["For each hypothesis: verdict, what it means for forecasters, how it compares with prior work (SHEM, USGS FS 2016-3027, Polz 2023).",
   "400-500 words, your own words."],
  ["Discussion drafted"],
  "paper/discussion_v0.docx.")

H("Write the Limitations",
  "Owning limits makes you more credible, not less.",
  ["Include: Iowa State archive stores observation time, not receipt time; flood selection rule; small number of floods; labels by one student plus a second rater; no proof that any outage changed a warning or cost a life.",
   "150-250 words."],
  ["Limitations drafted"],
  "An honest limitations section.")

H("Write the Conclusion and future work",
  "Ends the paper with a clear take-home message.",
  ["3-4 sentences of conclusion. Future work: receipt-time logs from NWS, radar rain, working with a USGS centre."],
  ["Drafted"],
  "paper/conclusion_v0.docx.")

H("Write the abstract",
  "Many judges read only this. ISEF requires it in your own words.",
  ["250 words max: problem, method, 3 key numbers, conclusion.",
   "Count words. No AI writing."],
  ["Abstract written, under 250 words"],
  "paper/abstract_v1.docx.")

H("Assemble full draft v1",
  "Putting sections together reveals gaps and repetition.",
  ["Combine intro, methods, results A-C, discussion, limitations, conclusion, references.",
   "Read it once from start to end and mark weak places."],
  ["Draft v1 assembled"],
  "A complete first draft.")

H("Reproducibility run from scratch",
  "If you cannot reproduce your own results on a clean folder, neither can anyone else.",
  ["Clone your repo into a new folder. Follow your README exactly. Re-create all tables and figures.",
   "Fix every step that fails. Record Python and package versions (pip freeze > requirements.txt)."],
  ["Clean run succeeded", "requirements.txt saved"],
  "A repo anyone can re-run.")

H("Send draft v1 for review",
  "Fresh eyes find what you cannot.",
  ["Send to your mentor and teacher with 3 specific questions (for example: 'Is the under-read rule explained clearly?')."],
  ["Sent"],
  "Review requested.")

H("Catch-up hour (default: second-rater on live classes)",
  "Reserved slippage hour.",
  ["Finish overdue work, or have your second rater label 15 live-feed classes for an agreement score."],
  ["Done"],
  "No overdue tasks.")

H("Week 8 review",
  "All results are final from now on.",
  ["Freeze results/ and figures/. Only writing and presenting from here.",
   "Plan Week 9."],
  ["Results frozen"],
  "A frozen results folder.")

# ---------------- WEEK 9: revision (Hours 129-144) ----------------
H("Revise from feedback, part 1",
  "Use comments to improve the argument.",
  ["List every comment. Fix the 5 most important first (usually clarity of the question and of the methods)."],
  ["Top 5 fixed"],
  "Draft v1.1.")
H("Revise from feedback, part 2", "Continue revision.", ["Fix the remaining comments, or write why you disagree."], ["All comments handled"], "Draft v1.2.")
H("Revise from feedback, part 3", "Tighten the writing.", ["Cut 10% of words. Replace vague phrases with numbers.", "Make sure each paragraph starts with its main point."], ["Draft shortened"], "Draft v1.3.")

H("Number check",
  "One wrong number can sink an interview.",
  ["Make a list of every number in the paper. Next to each, write the file and code that produced it. Re-run and compare.",
   "Fix any mismatch."],
  ["Every number traced"],
  "A number-trace table (keep it in the logbook).")

H("Citation check",
  "ISEF forbids AI-created citations; every reference must be real and say what you claim.",
  ["Open every reference. Check the author, year, title, and that it supports the sentence where you cite it.",
   "Remove any you have not personally opened."],
  ["All references checked"],
  "A clean bibliography.")

H("Polish figures for colour-blindness and print",
  "Judges view posters from a distance and some are colour-blind.",
  ["Check every figure in a colour-blind simulator. Make sure labels are readable at poster size (at least 24 pt equivalent)."],
  ["All figures checked"],
  "Accessible figures.")

H("Write the 'Hunt and Center Point' story box",
  "A clear, true story helps judges remember your project.",
  ["Write 120 words in your own words: Hunt went silent at 29.45 ft at 4:35 am; Center Point kept sending wrong numbers; the crest was surveyed later.",
   "Check every fact against your own downloads."],
  ["Story written and checked"],
  "A poster story box.")

H("Ethics and wording check",
  "Avoid overclaiming about a tragedy.",
  ["Search the draft for words like 'caused', 'would have saved', 'failed to warn'. Replace with accurate wording.",
   "Add a sentence acknowledging the people affected, without using names."],
  ["Wording checked"],
  "Respectful, accurate language.")

H("Poster layout",
  "Layout comes before content filling.",
  ["Sketch on paper: title, question, story box, 3 findings (prevalence, live-feed failures, detector), virtual gauge, limitations, QR code to repo.",
   "Follow your fair's size rules."],
  ["Sketch done"],
  "A poster plan.")
H("Poster first draft", "Turn the sketch into a file.", ["Build in PowerPoint, Google Slides or Canva at full size.", "Place figures and short text (bullet points, large font)."], ["Draft file"], "Poster v1.")
H("Poster content pass", "Every word on a poster should earn its place.", ["Cut text by half. Make the 3 key numbers huge.", "Check the poster passes the '10-foot test' (readable from 10 feet away)."], ["Text cut", "Numbers large"], "Poster v2.")

H("Demo polish",
  "A demo that crashes is worse than no demo.",
  ["Run the demo 5 times start to finish. Fix glitches. Record a 60-second screen video as a backup."],
  ["Demo stable", "Backup video saved"],
  "A reliable demo and a video backup.")

H("Peer read-through",
  "A classmate can tell you what is confusing.",
  ["Ask a classmate to read the abstract and look at the poster for 2 minutes, then explain your project back to you.",
   "Note what they got wrong; that is what to fix."],
  ["Read-through done"],
  "A list of confusing parts.")
H("Fix confusing parts", "Make it understandable to non-experts.", ["Fix each confusing part found in the read-through."], ["Fixed"], "Clearer poster and abstract.")
H("Catch-up hour (default: re-run the number check)", "Reserved slippage hour.", ["Finish overdue work, or repeat the number check on the poster."], ["Done"], "No overdue tasks.")
H("Week 9 review", "Paper and poster drafts both exist.", ["Rate each section 1-5 for clarity. Plan Week 10 around the weakest."], ["Ratings done"], "A focused plan for Week 10.")

# ---------------- WEEK 10: interview preparation (Hours 145-160) ----------------
H("Print a test poster",
  "Colours and font sizes look different on paper.",
  ["Print at reduced size (for example tabloid) and check readability and colours."],
  ["Test print checked"],
  "Confidence the poster prints well.")

H("Write the interview question bank",
  "Interviews carry about a quarter of ISEF judging points; practise the hard questions.",
  ["Write 30 questions, including: 'Doesn't USGS already know gauges fail?', 'Isn't a gap just maintenance?', 'How do you know the live feed is what forecasters saw?', 'Why not use deep learning?', 'What did you do yourself and what did AI do?'",
   "Write your own short answer to each."],
  ["30 Q&As written"],
  "A question bank in your words.")

H("Practise the 2-minute pitch",
  "Judges often ask 'tell me about your project' first.",
  ["Write and time a 2-minute version: story, question, 3 findings, what you built.",
   "Practise 5 times out loud."],
  ["Pitch under 2:10"],
  "A smooth 2-minute pitch.")
H("Practise the 5-minute walkthrough", "Some judges want the detail.", ["Walk through the poster in 5 minutes, pointing at each figure.", "Record yourself once and watch it."], ["Recorded once"], "A 5-minute walkthrough.")

H("Mock judging, round 1",
  "Real pressure reveals weak spots.",
  ["Ask a teacher to judge you for 10 minutes using ISEF-style criteria.",
   "Write down every question you struggled with."],
  ["Mock done", "Struggles listed"],
  "A list of weak answers.")
H("Fix weak answers", "Turn weak spots into strengths.", ["For each struggle, find the data or source that answers it and rewrite the answer."], ["All weak answers rewritten"], "Stronger answers.")

H("Form 2A: support and AI disclosure",
  "Required for every project in 2026-27.",
  ["Fill Form 2A. Answer 'yes' to generative AI use. Attach the AI prompt log (this conversation and any others).",
   "List clearly: the AI assistant ran pilot analyses and drafted this plan; you re-ran every analysis, hand-checked the data, built the final code and wrote all text yourself.",
   "List human help: mentor, second rater, sponsor."],
  ["2A complete", "Prompt log attached"],
  "A complete, honest disclosure.")

H("Official abstract form",
  "Fairs use a specific abstract form.",
  ["Copy your abstract onto your fair's form. Check the word limit and required fields."],
  ["Form filled"],
  "Abstract form ready.")

H("Logbook completeness check",
  "Judges may read your logbook.",
  ["Make sure every hour has a dated entry, decisions are explained, and kill tests are recorded.",
   "Add a table of contents at the front."],
  ["Logbook complete"],
  "A logbook that tells the whole story.")

H("Paper version 2",
  "Final full draft before polishing.",
  ["Make all changes from mock judging into the paper.",
   "Re-check figures and numbers again."],
  ["Paper v2 saved"],
  "Near-final paper.")

H("Practise data questions",
  "Judges test whether you really know your data.",
  ["Have someone pick 5 random rows from your census table and ask you to explain each.",
   "Practise explaining one false alarm and one miss."],
  ["5 rows explained"],
  "Confidence with your own data.")

H("Offline backup kit",
  "The old USGS service shuts down on 22 February 2027 and Wi-Fi fails at fairs.",
  ["Put on a USB drive: paper PDF, poster file, demo (offline), backup video, data and code.",
   "Test that the demo runs from the USB on another computer."],
  ["USB kit tested"],
  "A backup that works without internet.")

H("Mock judging, round 2",
  "Second round checks the fixes worked.",
  ["Ask a different adult to judge you. Ask them to be tough."],
  ["Mock 2 done"],
  "Fewer weak spots.")
H("Act on mock round 2", "Close remaining gaps.", ["Fix remaining weak answers and any poster confusion."], ["Done"], "Ready for the fair.")
H("Catch-up hour (default: extra pitch practice)", "Reserved slippage hour.", ["Finish overdue work, or practise the pitch 3 more times."], ["Done"], "No overdue tasks.")
H("Week 10 review", "Final week plan.", ["List everything left. Order by importance."], ["List done"], "A short final to-do list.")

# ---------------- WEEK 11: final (Hours 161-176) ----------------
H("Final paper revision, part 1", "Polish the paper.", ["Read aloud, fix awkward sentences in intro and methods."], ["Done"], "Paper v2.1.")
H("Final paper revision, part 2", "Polish the paper.", ["Read aloud, fix results and discussion."], ["Done"], "Paper v2.2.")
H("Final paper revision, part 3", "Format the paper.", ["Apply your fair's format: headings, page numbers, figure captions, references."], ["Formatted"], "Paper v2.3.")
H("Final paper revision, part 4", "Final proof.", ["Spell-check, check every figure is referenced in the text, export PDF."], ["PDF exported"], "Final paper PDF.")
H("Order the final poster", "Printing can take days.", ["Export at full resolution. Order printing with a delivery date at least 3 days before the fair."], ["Order placed"], "Poster on the way.")

H("Stop DarkWatch and write the appendix",
  "End the live log cleanly and report it.",
  ["Disable the workflow on 31 January. Back up the final log twice.",
   "Write a 1-page appendix: dates, gauges, candidate and confirmed outages, detector alarms."],
  ["Logger stopped", "Appendix written"],
  "A completed live-logging study.",
  "code/darkwatch.yml")

H("Final reproducibility run", "Make sure the final repo reproduces the final paper.", ["Clean clone, run everything, compare outputs with the paper."], ["Matches"], "A reproducible final repo.")
H("Final number check", "Last guard against errors.", ["Re-check the 10 most important numbers on poster, abstract and paper; all three must agree."], ["All agree"], "Consistent numbers everywhere.")
H("Practise, part 1", "Polish delivery.", ["Run the full judging routine (pitch, demo, Q&A) twice."], ["Done"], "Smooth delivery.")
H("Practise, part 2", "Polish delivery.", ["Practise with the printed poster if it has arrived."], ["Done"], "Confident with the real poster.")
H("Submit materials", "Meet the deadline with a day to spare.", ["Submit paper, abstract and forms to your fair's system. Save the confirmation."], ["Submitted", "Confirmation saved"], "Everything submitted.")
H("Contingency hour 1", "Reserved for surprises.", ["Use for anything that went wrong. If nothing did, rest; tired presenters do worse."], ["-"], "Calm before the fair.")
H("Contingency hour 2", "Reserved for surprises.", ["Same as above."], ["-"], "")
H("Contingency hour 3", "Reserved for surprises.", ["Same as above."], ["-"], "")
H("Contingency hour 4", "Reserved for surprises.", ["Same as above."], ["-"], "")
H("Contingency hour 5", "Reserved for surprises.", ["Same as above."], ["-"], "")
