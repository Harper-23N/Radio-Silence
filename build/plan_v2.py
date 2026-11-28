"""Round 57 plan: 154 hours, 11 weeks (17 Nov 2026 - Sun 31 Jan 2027), 14 h/week.
Everything is finished by 31 January, so 2-6 February is only uploading finished files.
Forms come before data collection. Old (Round 56) hours are reused where they still serve the project;
references are written as [[o:N]] (old hour N) or [[n:key]] (new hour) and resolved after assembly.
"""
import re, copy, datetime as dt
import hours_w5_11  # noqa
from hours_w1_4 import HOURS as OLD
import enrich
enrich.apply()

START = dt.date(2026, 11, 17)  # Tuesday
SLOTS = [0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 4, 5, 5, 5]  # Tue-Fri 2 h, Sat 3 h, Sun 3 h; Mondays off
PER_WEEK = len(SLOTS)

TC = "https://tcrsf.zfairs.com/File/Client/"
FORM_LINKS = {
 "Form 1": TC + "60cef971-8231-4b14-96ab-6a46df0c645d", "Form 1A": TC + "aab49de3-a895-43b2-a145-acdeda639836",
 "Form 1B": TC + "127ccfb3-2f79-4880-b876-45e6f8c84afc", "Form 2A": TC + "d3356f7d-14af-41b1-b9c8-f82552f7860f",
 "Form 2C": TC + "ee477f39-a3f8-4e16-a0a1-9a97fa768cc7", "TCRSF Form 1D": TC + "21be37eb-7101-441b-b4c0-24063f7afa29",
 "Abstract form": TC + "ee54c058-7c61-49ea-92b8-a33be721c445", "Research plan generator": TC + "82283e58-68d0-437b-be06-04c89252c737",
 "Research plan instructions": TC + "cd35a328-45ba-47b7-bef8-694bb823e1a8", "zFairs": "https://tcrsf.zfairs.com",
}


def N(key, title, why, steps, checks, done, uses="", forms=()):
    return dict(key=key, title=title, why=why, steps=steps, checks=checks, done=done, uses=uses, forms=list(forms), new=True)


def O(n, **over):
    h = copy.deepcopy(OLD[n - 1]); h["old"] = n; h["forms"] = []
    for k, v in over.items():
        if k == "add_steps": h["steps"] = h["steps"] + v
        elif k == "pre_steps": h["steps"] = v + h["steps"]
        else: h[k] = v
    return h


WEEKLY_CHECK = "End-of-week check (10 min): DarkWatch ran without errors this week, every hour has a dated logbook entry, AI prompts are in the log."

W = []  # (title, summary, decision, hours)

# ---------------- WEEK 1 ----------------
W.append(("Plan, forms and reading",
 "Write the research plan in your own words, get Forms 1, 1A and 1B signed, and do the background reading. No data collection until Form 1B is signed: that day is your official start date.",
 "Start date set at [[n:forms]]", [
 O(1, steps=["Read Parts 1-5 of this guide and the roadmap page. Mark anything you do not understand with a '?' and ask about it.",
             "Start a logbook with numbered, dated pages. Page 1: the research question in your own words, today's date, and the line 'Pilot work in /data was produced by an AI assistant on 16-17 Nov 2026 and must be re-run by me.'",
             "Start an AI prompt log (every prompt you give an AI tool and its answer, with dates). Form 2A requires it. Save this conversation into it.",
             "Put the TCRSF dates in your calendar now: 9 Dec (registration opens), 6 Feb (paperwork), 15 Feb (freeze), 26 Feb (judging)."],
   checks=["Logbook page 1 dated", "AI prompt log started", "TCRSF dates in calendar"]),
 N("rp1", "Write the research plan, part 1 (why and what)",
   "ISEF and TCRSF require a research plan written before any data collection, in your own words. No AI may write it.",
   ["Download TCRSF's 2027 research-plan generator ('no special cases' version: GaugeDark has no humans, animals, tissues, microbes or hazardous materials) and the 2027 instructions.",
    "Rationale (150-250 words): the Hunt gauge story, why gauges matter for warnings, what is not yet known. Use future tense ('I will measure...').",
    "Research question and the five hypotheses (H1-H5 in Part 4), each in one sentence of your own, plus expected outcomes.",
    "Save as research_plan_v1.docx."],
   ["Generator downloaded", "Rationale written", "Question, hypotheses, expected outcomes written"],
   "Half of a research plan, in your own words.", forms=["Research plan generator", "Research plan instructions"]),
 N("rp2", "Write the research plan, part 2 (how)",
   "The procedures section is what the reviewers (SRC) check; it must show you understand every step.",
   ["Materials: computer, Python 3.12, free USGS Water Data API key, GitHub account; public data from USGS, NOAA and Iowa State University.",
    "Procedures, numbered: reproduce the pilots; pre-register a flood list; download archive and live-feed records; detect failures with a fixed rule; hand-check 150 random cases with a second rater; model failure vs rise, basin size, flood stage and equipment limits; build and lock a detector and a virtual gauge on development floods; test once on held-out floods and on the live logger.",
    "Risk and safety: no physical risk. Data ethics: no victim names; never claim an outage caused a death.",
    "Data analysis: Wilson intervals, logistic regression clustered by flood, precision and recall with flood-level bootstrap, blank-out crest errors. Bibliography: the 12 core sources (Part 9). Export as PDF."],
   ["Procedures written", "Risk and analysis written", "Bibliography added", "PDF exported"],
   "A complete research plan PDF ready for signatures.", forms=["Research plan generator"]),
 N("forms", "Forms 1, 1A and 1B, and pre-approval",
   "Forms must be dated before you start; ISEF says wrong dates are the most common form error. This hour is the gate for all data work.",
   ["Meet your adult sponsor (science teacher) with the plan PDF. They complete and sign Form 1.",
    "Fill Form 1A: work site home and school; data from publicly available sources; attach the research plan. Leave 'actual start date' for later.",
    "You and a parent or guardian sign Form 1B. No data download before this date.",
    "If your school has no review committee, email the plan PDF (name, school, grade) to src@tcrsf.net and log it. When signatures (and any reply) are in, write the official start date on logbook page 1 and on Form 1A. If approval is still pending at the start of Week 2, do [[o:26]] and [[o:27]] (writing, no data) first."],
   ["Form 1 signed", "Form 1A filled, plan attached", "Form 1B signed", "Pre-approval requested", "Start date recorded"],
   "Signed forms scanned into a 'forms' folder; a clear 'go' date for data work.", forms=["Form 1", "Form 1A", "Form 1B"]),
 O(3, title="Install your tools and run the tests",
   why="Installing software and running the included tests is not data collection, so it can happen while signatures are pending."),
 O(18, pre_steps=["First (10 min): install Zotero (free) and add every paper you read from now on; you will need the list for the bibliography and the citation check."]),
 O(19), O(20), O(21), O(22), O(23), O(24), O(25),
 O(14, add_steps=[WEEKLY_CHECK.replace("DarkWatch ran without errors this week, ", "")]),
]))

# ---------------- WEEK 2 ----------------
W.append(("Reproduce the pilots and decide go/no-go",
 "Re-run my pilots yourself, verify my labels and the two newest pilots, start the live logger for winter storms, and make the K1 decision.",
 "K2 at [[o:8]], K1 at [[o:13]]", [
 O(4), O(5), O(15),
 O(6, steps=["The new API's 'continuous' collection accepts a bbox filter (checked 17 Nov 2026: a box around Hunt returned Hunt, North Fork, Kerrville and Guadalupe above Bear Creek).",
             "Write code/bbox_pull.py: call the continuous items endpoint with bbox, parameter_code=00065, time=start/end, limit=10000, following 'next' links; group by monitoring_location_id; save one CSV per gauge in data/raw/<event>/.",
             "Test on the Texas box -100.6,29.6,-97.8,31.4 for 3-7 July 2025. My pilot found 89 gauges with data.",
             "Note in the logbook how many pages and seconds the pull took."]),
 O(7), O(8), O(9), O(10), O(11), O(12),
 N("p8v", "Verify pilot P8: equipment limits and flood stage",
   "P8 suggests gauges whose crest topped their own USGS 'operational limit (maximum)' went dark more often, yet most failures happened below that limit. Reproduce it before you rely on it.",
   ["For 10 gauges in data/gauge_thresholds_usgs.csv, open api.waterdata.usgs.gov/ogcapi/v1/collections/time-series-metadata/items?monitoring_location_id=USGS-<site>&parameter_code=00065&f=json and confirm 'Operational limit (maximum)' and 'NWS Flood Stage'.",
    "Look for any date on each threshold. If a limit may have been set after the flood (for example after the gauge was rebuilt), mark it 'possibly post-flood'.",
    "Recompute on the pilot table: dark rate when the crest reached the limit vs not (pilot: 7 of 13 vs 20 of 92), and how many dark gauges stopped reporting below their limit (pilot: 23 of 27; for 20 of 27 even the crest never reached it)."],
   ["10 limits verified", "Possibly post-flood limits flagged", "Rates recomputed"],
   "Your own check of the equipment-limit result, including its biggest weakness.", uses="data/gauge_thresholds_usgs.csv, data/stations_7floods_v3.csv"),
 N("p9v", "Verify pilot P9: the live-feed detector rules",
   "P9 is the first evidence that wrong-but-alive readings can be caught automatically, and that a flat-line rule alone cannot do it. Re-run it on 5 gauges.",
   ["Read code/gd_live_rules.py and write each rule (silent, impossible value, flat line) as one sentence in your logbook. Run its self-test.",
    "Download live files with gd_fetch.iem_hads for Hunt (HNTT2), Cypress Creek (CCGT2), Buffalo Bayou (BAHT2), Kerrville (KRRT2) and Center Point (GCTT2) for the pilot windows.",
    "Run the three rules and compare with data/live_detector_pilot.csv. Kerrville should show one impossible value (94.5 ft) even though its archive is clean: explain in one sentence why that matters."],
   ["Rules rewritten", "5 gauges re-run", "Differences explained"],
   "Confidence that the detector pilot is real.", uses="code/gd_live_rules.py, data/live_detector_pilot.csv, code/gd_fetch.py"),
 O(13), O(26, add_steps=[WEEKLY_CHECK]),
]))

# ---------------- WEEK 3 ----------------
W.append(("Pre-registration and the national data pull",
 "Fix the flood list in public before seeing any results, then download every pre-registered flood (archive, live feed, gauge metadata) while the old USGS service is still up.",
 "Rule committed at [[o:28]]; bulk pulls finished by [[o:42]]", [
 O(27),
 O(28, steps=["Write the rule BEFORE looking at any outage data. Suggested: every USGS Short-Term Network (STN) flood event 2017-2025 in the lower 48 with at least 50 surveyed high-water marks, plus any U.S. flood with 10 or more deaths in the NOAA Storm Events database.",
              "Get the event list from the STN Flood Event Data Portal (stn.wim.usgs.gov/STNDataPortal) or the Python package pygeohydro (STNFloodEventData). The raw STNServices URL returned 'Access forbidden' from a browser on 17 Nov 2026, so use one of these two routes.",
              "Write how each flood's box (high-water marks plus 0.25 degrees) and window (first to last mark, plus 1 day each side) are drawn.",
              "Commit the rule as prereg.md to GitHub. The commit time proves it came first."]),
 O(29), O(30),
 O(33), O(34), O(35), O(36), O(37),
 O(38, steps=["From 'monitoring-locations' (bbox works), get drainage area, state, HUC and coordinates for each census site.",
              "From 'time-series-metadata', get each gauge's operational maximum and minimum (equipment limits) and NWS flood stage. 115 of 133 pilot gauges had an operational maximum; flood stage appears under several labels (see data/gauge_thresholds_usgs.csv).",
              "From the 'Max At Event Time' series (annual peaks, back to 1932 at Hunt), compute each gauge's highest stage BEFORE each flood (prior record).",
              "Save data/site_meta.csv."], uses="data/gauge_thresholds_usgs.csv"),
 O(39), O(40), O(41), O(42, add_steps=[WEEKLY_CHECK, "Back up data/raw to two places: the old USGS service has planned outages from January."]),
]))

# ---------------- WEEK 4 ----------------
W.append(("Register for TCRSF, run the census, start the hand check",
 "Registration opens Wednesday 9 December. Register, sign Form 1D, decide on the paper competition, then run the classifiers on the full census and start the random hand check.",
 "Registered at [[n:reg]]", [
 O(43), O(44),
 N("reg", "Register for TCRSF on zFairs (opens 9 December)",
   "Registering early lets you upload paperwork early and catch problems long before 6 February.",
   ["Ask your teacher to register on tcrsf.zfairs.com as a Teacher first (TCRSF requires this).",
    "Create your Participant account (new profile every year) and register the PROJECT; only projects advance to state and ISEF. Working title, for example 'GaugeDark: When Flood Gauges Go Silent or Go Wrong'.",
    "Choose the category now and keep it: Earth and Environmental Sciences if you lead with the measurement, Systems Software if you lead with the detector. It cannot change after 10 February.",
    "Print TCRSF Form 1D (permission and liability release); you and a parent sign it. Upload a head-and-shoulders photo. Decide on the optional research-paper competition ($20, paper due 4 Feb, same research, judge comments by email): if yes, register that entry too."],
   ["Teacher registered", "Project registered", "Category chosen", "Form 1D signed", "Photo uploaded", "Paper competition decided"],
   "A registered project with Form 1D signed.", forms=["zFairs", "TCRSF Form 1D"]),
 O(45), O(46), O(47),
 O(48, title="Methods draft, version 0", steps=["Write 300 words of Methods: data sources (with pull dates), flood selection, gap rule, live-feed classes.", "Add the equipment-limit and flood-stage variables from [[o:38]].", "Save paper/methods_v0.docx."], checks=["Methods draft saved"]),
 O(49), O(50), O(51), O(52),
 O(53, steps=["Re-read the protocol card before you start.", "Label gauges 76-100 exactly as in the previous three hours.", "Mark any gauge you are unsure about with '?' so the second rater can look at it.", "Keep a running count of each label."]),
 O(54),
 O(55, add_steps=[WEEKLY_CHECK, "Upload the signed Forms 1, 1A, 1B, research plan and Form 1D to zFairs now (re-uploadable later)."]),
]))

# ---------------- WEEK 5 ----------------
W.append(("Error rates, live vs archive, first results, models",
 "Measure the rule's error, get second-rater agreement, build the live-vs-archive table (H2), draft Results A, and fit the main model.",
 "H2 verdict at [[o:59]]", [
 O(56), O(57), O(58), O(59), O(60), O(61), O(63), O(65),
 O(66, add_steps=["Add three columns: crest at or above the operational maximum (yes/no), last reading at or above NWS flood stage (yes/no), and prior-record stage (from [[o:38]])."]),
 O(67), O(68), O(69), O(70), O(71, title="Interpret the record-stage effect", add_steps=[WEEKLY_CHECK]),
]))

# ---------------- WEEK 6 ----------------
W.append(("Mechanism, drivers write-up, detector rules",
 "Test the equipment-limit mechanism (H5), finish Results B and the H1 verdict on test floods, then build the detector rules. Holiday week: move the 24-25 Dec hours to Saturday, Sunday or Monday 28 Dec; keep the order.",
 "K3 at [[o:75]]", [
 O(72),
 N("mech", "Mechanism test: equipment limits and flood stage (H5)",
   "If gauges fail because water reaches their equipment, USGS's own limits should predict failure. The pilot says limits predict some failures, but most happen below the limit.",
   ["On development floods, compare failure rates for gauges whose crest reached the operational maximum vs not, with flood-clustered intervals. Pilot: 7 of 13 (54%) vs 20 of 92 (22%), unclustered odds ratio 4.2, p = 0.036.",
    "Report the share of failures whose last reading was BELOW the gauge's own limit (pilot: 23 of 27; for 20 of 27 the crest never reached it) and the share while the river was at or above NWS flood stage (pilot: 11 of 14 with a published flood stage).",
    "Repeat without the 'possibly post-flood' limits from [[n:p8v]] (sensitivity check).",
    "Apply the H5 rule in Part 4 on test floods and write the verdict."],
   ["Clustered rates", "Below-limit and above-flood-stage shares", "Sensitivity check", "H5 verdict"],
   "A mechanism paragraph for Results B.", uses="data/gauge_thresholds_usgs.csv, figs/f6_limits.png"),
 O(73), O(74, add_steps=["Freeze Tables 1-2 and Figures 1-3: copy them to paper/frozen/."]), O(75), O(76), O(77),
 O(81),
 O(82, uses="code/gd_alarm.py, code/gd_live_rules.py, code/test_gd_gaps.py (Hunt data)",
       add_steps=["Choose the silence floor now, on development floods only: run silent_alarms with min_gap_min = 15, 30 and 60. Pilot P9: at Hunt the 60-min floor fires at 5:35 am CDT, after the estimated crest; the 15-min floor fires at 4:50 am, 20 min before it, with no extra alarms on 81 healthy gauges. Record false alarms per 100 calm gauge-days for each and pick one."]),
 O(83, add_steps=["Start from code/gd_live_rules.frozen_alarms. Pilot P9: it caught 4 of 8 FROZEN gauges but also fired at 24 of 81 healthy gauges, because broad natural crests are flat too. Add a neighbour condition in [[o:86]]: a flat reading only counts if the upstream gauge is still rising."],
       uses="code/gd_live_rules.py, data/live_detector_pilot.csv"),
 O(84, steps=["Start from code/gd_live_rules.implausible_alarms: negative values, values above the gauge's operational maximum (+1 ft), and one-step jumps over 15 ft that come straight back.",
              "Pilot P9 lesson: 7 gauges really rose above their published operational maximum, so use ceiling = max(operational maximum, prior record from [[o:38]]) + 2 ft.",
              "Unit test with three series: one with 1310.71, one negative, one real 11 ft flash rise (Kerrville, 10:45-11:00 UTC 4 July 2025, 14.60 to 26.06 ft). Only the first two may alarm.",
              "Run on development floods; count alarms that are confirmed wrong (above the later archive crest, negative, or error codes) vs real water."],
       uses="code/gd_live_rules.py, data/live_detector_pilot.csv, data/gauge_thresholds_usgs.csv"),
 O(85), O(86), O(87, add_steps=[WEEKLY_CHECK]),
]))

# ---------------- WEEK 7 ----------------
W.append(("Lock the detector, replay Texas, build the virtual gauge",
 "Tune and lock thresholds on development floods, score against baselines, replay the Guadalupe flood, then fit and test the virtual gauge. 1 January: move those 2 hours to the weekend.",
 "Thresholds locked at [[o:88]]; K5 at [[o:104]]", [
 O(88), O(89),
 O(90, steps=["Failure episode = a hand- or rule-labelled failure from Weeks 4-5. A hit = an alarm during the episode's first 2 hours.",
              "Compute precision, recall, false alarms per 100 gauge-days of calm data, and two times: delay (alarm minus failure start) and lead (USGS crest time minus alarm).",
              "Write metrics.py and test it on a tiny made-up example where you know the answer."]),
 O(94),
 O(91, steps=["Run replay.py for Hunt, Center Point, Kerrville and Comfort with your locked thresholds.",
              "Write a timeline in local time (CDT): Hunt last reading 4:35 am; your silence alarm time; Kerrville rising from about 5:15 am; Center Point archive ends 6:15 am while its live feed kept sending about 20 ft; when does your under-read alarm fire?",
              "Be careful: do not claim the alarm would have saved lives. Say what information it would have added, and when."]),
 O(92), O(93),
 O(97), O(98), O(99), O(101), O(102), O(103), O(104, add_steps=[WEEKLY_CHECK]),
]))

# ---------------- WEEK 8 ----------------
W.append(("Held-out test",
 "Run the locked detector once on test floods, bootstrap by flood (including warning time), check that live-feed silences are not Iowa State outages, evaluate on your own live log, and finish the figures.",
 "K4 at [[o:115]]", [
 O(105), O(106), O(113), O(114), O(115), O(116),
 N("srccheck", "Is the live feed itself trustworthy?",
   "Your live-feed findings (H2, the detector) rest on Iowa State's copy of the NWS feed. A judge may ask whether a 'silent' gauge was really Iowa State missing data. This hour answers that.",
   ["For every live-feed silence in your census, count how many OTHER gauges in the same flood also went silent within the same 15 minutes. Many at once suggests an Iowa State or satellite outage, not a gauge failure.",
    "Flag those cases and re-compute your H2 share and detector recall without them.",
    "Look for a second copy of the live feed for 10 gauges (for example NOAA NCEI's HADS archive on catalog.data.gov). If you find one, compare; if not, write that in Limitations.",
    "Add one sentence and one number to Methods (for example 'x of y silences coincided with network-wide gaps and were excluded')."],
   ["Simultaneous-silence check done", "H2 and recall re-computed", "Second-source attempt recorded"],
   "A defended live-feed result.", uses="data/live_feed_only_outages.csv, data/live_detector_pilot.csv"),
 O(109, title="Summarise DarkWatch (mid-November to early January)"),
 O(117), O(118), O(107), O(108), O(110), O(119, add_steps=[WEEKLY_CHECK]),
]))

# ---------------- WEEK 9 ----------------
W.append(("Discussion, abstract and full draft",
 "Write Discussion, Limitations and Conclusion, the abstract (needed for paperwork), draft v1, a clean reproducibility run, and the poster draft.",
 "Draft v1 sent at [[o:126]]", [
 O(120), O(121), O(122),
 O(123, why="Judges read the abstract first; TCRSF needs it in your paperwork and as text in your entry; no AI may write it.",
   add_steps=["Use the official 2027 abstract form (max 250 words). Keep a plain-text copy for zFairs; the two must match word for word."], forms=["Abstract form"]),
 O(124), O(125), O(126),
 O(127, title="Second rater on the live-feed classes",
   why="The live-feed taxonomy (H2) is your most surprising finding, so its labels need an agreement score like the archive labels.",
   steps=["Give your second rater 20 random live-feed cases with the class rules (Part 3) and no labels.",
          "Compute Cohen's kappa against your labels.",
          "Add the kappa to Methods; discuss any class with poor agreement in Limitations."],
   checks=["20 cases rated", "Kappa computed and added to Methods"], done="An agreement score for the live-feed classes."),
 O(134), O(135), O(136), O(137), O(138), O(139, add_steps=[WEEKLY_CHECK]),
]))

# ---------------- WEEK 10 ----------------
W.append(("Revise, check, build the online exhibit",
 "Revise from feedback, check every number and citation, make the quad chart and the 2-minute video that judges preview online, and complete Form 2A and the official abstract.",
 "Online exhibit ready at [[n:vrec]]", [
 O(129), O(130), O(131), O(132), O(133), O(140), O(141), O(142),
 N("quad", "Make the quad chart",
   "Judges preview projects online (19-25 Feb); a quad chart tells your story at a glance. TCRSF allows up to 6 pages in one PDF; ISEF wants 1 page.",
   ["Make one page: four boxes. Problem (Hunt: 29.45 ft, then silent for 35 h), Method (census plus live feed, development and test floods), Results (three headline numbers with intervals), Build (detector and virtual gauge with test-flood scores).",
    "Credit every image and chart individually (USGS, NOAA, Iowa Environmental Mesonet, or 'figure by the student').",
    "Export quad_chart.pdf. Optionally add up to 5 supporting pages for TCRSF."],
   ["One-page quad chart", "Every element credited", "PDF exported"], "quad_chart.pdf ready to upload."),
 N("vscript", "Write the 2-minute video script",
   "TCRSF allows up to 12 minutes but ISEF only 2; a 2-minute video works for both and forces clarity.",
   ["About 260 words in your own words: 20 s story, 20 s question, 50 s findings, 20 s what you built, 10 s why it matters.",
    "Mark where the Guadalupe demo replay appears on screen.",
    "Read it aloud with a timer; cut until it fits in 2:00."],
   ["Script written", "Timed under 2:00"], "video_script.txt."),
 N("vrec", "Record and edit the video",
   "A clear video helps judges who preview your project before the fair.",
   ["Record yourself speaking plus a screen capture of the demo (phone or free screen recorder).",
    "Add captions for the key numbers. Keep it under 2:00.",
    "Upload as an unlisted video or in the format TCRSF accepts; save the link."],
   ["Video recorded", "Under 2:00", "Link saved"], "A 2-minute video link."),
 O(151, forms=["Form 2A"]), O(152, forms=["Abstract form"]), O(153, add_steps=[WEEKLY_CHECK]),
]))

# ---------------- WEEK 11 ----------------
W.append(("Mock judging, final paper, poster, submit",
 "Use mock judging to fix the poster before ordering it, finish the paper, stop DarkWatch, check numbers, and upload everything to zFairs. On Sunday 31 January the project is done.",
 "Submission-ready at [[n:final]]", [
 O(145), O(146), O(147), O(149), O(150),
 O(161, steps=["Read the introduction and methods aloud slowly; fix every sentence you stumble over.",
               "Check the research question is identical in the paper, abstract, poster and video.",
               "Apply any changes from mock judging that affect the text."]),
 O(162, steps=["Read results and discussion aloud.", "Check every claim is followed by its number and interval.", "Check you wrote 'associated with', never 'caused'."]),
 O(166, steps=["Disable the DarkWatch workflow on 29 January. Back up the final log twice.",
               "Run the locked detector one last time on the full log.",
               "Write a 1-page appendix: dates, gauges, gauge-hours, candidate and confirmed outages, detector alarms. Change the abstract only if the appendix changes a headline number.",
               "Thank everyone who helped in the acknowledgements."]),
 O(167, steps=["Clone the repo into a fresh folder and run every script in README order.", "Compare every table and figure with the final paper.", "Fix the README if any step was missing."]),
 O(168, steps=["Check the 10 most important numbers across abstract, quad chart, video, poster, paper and demo: all must agree.", "Check dates and units on every figure.", "Re-export any file you changed."]),
 O(165, steps=["Check the display limits: 76 cm (30 in) deep, 122 cm (48 in) wide, 240 cm (94 in) from the floor, or at most 149 cm (4 ft 10 in) above the table.",
               "Export at full resolution and order with delivery well before 26 Feb.",
               "Proofread the printer's preview before paying."]),
 N("pdf", "Assemble the paperwork PDF",
   "TCRSF wants all review paperwork as one PDF online by 6 February; doing it now leaves a week of margin.",
   ["Combine in order: Form 1, Form 1A, research plan, Form 1B, Form 2A with AI prompt log, official abstract, TCRSF Form 1D. Add Form 2C only if any work happened in a university or agency lab (it should not).",
    "Check every signature and date: Form 1B is dated before the actual start date on Form 1A.",
    "Ask your teacher to look it over."],
   ["One PDF assembled", "Dates checked", "Teacher asked to review"], "paperwork_GaugeDark.pdf.",
   forms=["Form 1", "Form 1A", "Form 1B", "Form 2A", "Abstract form", "TCRSF Form 1D"]),
 N("upload", "Upload to zFairs and pay the fee",
   "Uploading a week early leaves room for review corrections (6-12 Feb).",
   ["Upload paperwork_GaugeDark.pdf; paste the abstract text into the project entry (it must match the form); upload quad_chart.pdf and the video link.",
    "Ask your teacher to click 'Mark Ready' for review.",
    "Pay the $25 project fee (+$20 if you entered the paper competition); a check must be postmarked by 8 Feb. Request electricity ($10) only if the laptop cannot run on battery all day.",
    "If you entered the paper competition, upload the paper, its abstract and Form 1D now (due 4 Feb, 10 pm)."],
   ["Paperwork uploaded", "Abstract text entered", "Exhibit uploaded", "Teacher marked ready", "Fee paid"],
   "A complete zFairs entry a week before the deadline.", forms=["zFairs"]),
 N("final", "31 January: submission-ready check",
   "This is the finish line. February is only checking, fixing anything the reviewers ask for, and presenting.",
   ["Tick every row of the 'Finished by 31 January' list on the roadmap page.",
    "Make a 'GaugeDark_final' folder: paper, abstract, quad chart, video, paperwork PDF, code, data, logbook scan. Copy it to a USB stick and the cloud.",
    "Copy the February dates (Part 8) into your calendar with alarms.",
    "Write a closing logbook entry with today's date."],
   ["Every deliverable final", "Two backups", "February alarms set"], "A finished project, ready for 2 February."),
]))

# ---------------- February (not research hours) ----------------
FEB = [
 ("Mon 1 Feb", "Rest day. Nothing is due."),
 ("Tue 2 Feb, 10 pm", "Only if you entered the paper competition: entry registration closes. (Already done at [[n:reg]].)"),
 ("Thu 4 Feb, 10 pm", "Paper-competition uploads freeze. (Already uploaded at [[n:upload]].)"),
 ("Fri 5 Feb, 10 pm", "Project registration closes: open zFairs and confirm the title, category and teacher link."),
 ("Sat 6 Feb, 10 pm", "All review paperwork online and marked ready. Confirm it shows as received."),
 ("6-12 Feb", "Review window: check email daily; fix and re-upload any correction the same day."),
 ("Mon 8 Feb", "Last postmark for a mailed fee check."),
 ("Wed 10 Feb", "Project data extracted: category and project number fixed."),
 ("Mon 15 Feb, 10 pm", "Everything frozen: paperwork approved, video, quad chart, photo, fee received."),
 ("19-25 Feb", "Judges preview your entry online. About 6 hours of practice: the 5-minute walkthrough with the demo, 20 data questions from your question bank, and a second mock judging with a different adult, then fix weak answers."),
 ("By 24 Feb", "Pack: poster, printed abstract, logbook, 1-2 paper copies, laptop with the offline demo, charger and a USB backup of the 'GaugeDark_final' folder, lunch and water (no food sold on site)."),
 ("Fri 26 Feb", "Judging at the Lee & Rose Warner Coliseum, Minnesota State Fairgrounds. Check the day-of schedule on zFairs for set-up time."),
 ("Sun 28 Feb", "Awards ceremony, 12:00-2:30 pm."),
 ("Mon 1 Mar", "If selected for ISEF: certification meeting, 6-8 pm."),
 ("Wed 3 Mar", "If selected for state: RSVP. State fair 1 April 2027; ISEF 8-14 May 2027, Los Angeles."),
]

# ---------------- assemble ----------------
NEW_HOURS, WEEKS2 = [], []
for title, summary, decision, hours in W:
    assert len(hours) == PER_WEEK, (title, len(hours))
    WEEKS2.append((title, summary, decision))
    NEW_HOURS.extend(hours)

OLD2NEW = {h["old"]: i + 1 for i, h in enumerate(NEW_HOURS) if "old" in h}
KEY2NEW = {h["key"]: i + 1 for i, h in enumerate(NEW_HOURS) if "key" in h}
USED = set(OLD2NEW)
DROPPED = sorted(set(range(1, 177)) - USED)
MOVED_TO_FEB = [148, 155, 156, 157, 158]
MISSES = []


def hour_date(i):
    w, k = divmod(i, PER_WEEK)
    return START + dt.timedelta(days=7 * w + SLOTS[k])


def _compress(nums):
    nums = sorted(nums); out = []; s = p = nums[0]
    for x in nums[1:]:
        if x == p + 1: p = x; continue
        out.append(f"{s}-{p}" if p > s else str(s)); s = p = x
    out.append(f"{s}-{p}" if p > s else str(s))
    return ", ".join(out)


def remap_old_refs(s, ctx=""):
    """Rewrite 'Hour 12', 'Hours 11-12', 'Hours 33, 40' written in OLD numbering into new numbering."""
    def repl(m):
        word, body = m.group(1), m.group(2)
        nums = []
        for part in re.split(r",\s*|\s+and\s+", body):
            if "-" in part:
                a, b = map(int, part.split("-"))
                got = [OLD2NEW[x] for x in range(a, b + 1) if x in OLD2NEW]
                if not got: MISSES.append((ctx, part)); return m.group(0)
                nums += got
            else:
                x = int(part)
                if x not in OLD2NEW: MISSES.append((ctx, part)); return m.group(0)
                nums.append(OLD2NEW[x])
        c = _compress(nums)
        w = "Hours" if ("," in c or "-" in c) else "Hour"
        return f"{w} {c}"
    return re.sub(r"\b(Hours?)\s+(\d+(?:-\d+)?(?:(?:,\s*|\s+and\s+)\d+(?:-\d+)?)*)", repl, s)


def resolve_tokens(s):
    def one(m):
        kind, v = m.group(1), m.group(2)
        if kind == "o":
            n = int(v)
            if n in OLD2NEW: return f"Hour {OLD2NEW[n]}"
            if n in MOVED_TO_FEB: return OLD[n - 1]["title"]
            MISSES.append(("token", v)); return f"Hour ?{v}"
        return f"Hour {KEY2NEW[v]}"
    s = re.sub(r"\[\[(o|n):([\w]+)\]\]", one, s)
    # collapse 'Hour 151-Hour 152' produced by '[[o:a]]-[[o:b]]'
    s = re.sub(r"Hour (\d+)-Hour (\d+)", r"Hours \1-\2", s)
    return s


for idx, h in enumerate(NEW_HOURS):
    for k in ("title", "why", "done", "uses"):
        if not h.get("new"): h[k] = remap_old_refs(h[k], f"h{idx+1}.{k}")
        h[k] = resolve_tokens(h[k])
    for k in ("steps", "checks"):
        h[k] = [resolve_tokens(remap_old_refs(x, f"h{idx+1}.{k}") if not h.get("new") else x) for x in h[k]]
# WEEKS2 and FEB keep their [[...]] tokens; build_pdf resolves them after the old-number remap.

if __name__ == "__main__":
    print("hours", len(NEW_HOURS), "weeks", len(WEEKS2), "last date", hour_date(len(NEW_HOURS) - 1))
    print("dropped", DROPPED)
    print("misses", MISSES)
