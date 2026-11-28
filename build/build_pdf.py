import sys, os, re, json, html, datetime as dt, base64
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from plan_v2 import (NEW_HOURS as HOURS, hour_date, START, PER_WEEK, FEB, FORM_LINKS,
                     remap_old_refs, resolve_tokens, MISSES, KEY2NEW, OLD2NEW, DROPPED)
from content import *

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIG = os.path.join(ROOT, "figs")
e = html.escape

def img(name, width="100%"):
    b = base64.b64encode(open(os.path.join(FIG, name), "rb").read()).decode()
    return f'<img src="data:image/png;base64,{b}" style="width:{width}">'

# ---------- schedule ----------
NH = len(HOURS); NW = len(WEEKS)
def hn(x):  # new hour number from an old number or a new key
    return OLD2NEW[x] if isinstance(x, int) else KEY2NEW[x]
def hrs(*xs):
    nums = sorted(hn(x) for x in xs); out = []; a = p = nums[0]
    for n in nums[1:]:
        if n == p + 1: p = n; continue
        out.append(f"{a}-{p}" if p > a else str(a)); a = p = n
    out.append(f"{a}-{p}" if p > a else str(a)); return ", ".join(out)

# ---------- which hours use which completed file ----------
FILES = [
 ("data/stations_7floods_v3.csv", "One row per gauge (387) for the 7 pilot floods: rise, crest, usual interval, inserted values, 1-hour max rise (inserted crests excluded), dark flags (1 h, 3 h), longest dark gap, last reading, deficit below crest, and Round 54's rule for comparison.",
  "Archive only (not live). Automatic rule, not hand-checked except Hunt and Center Point. 7 hand-picked floods. Gauge names omitted; look them up by site number."),
 ("data/live_feed_dark_gauges_classified.csv", "The 36 archive-dark gauges with what the Iowa State live-feed copy showed during each gap: class, coverage, live maximum, longest flat run, crest minus live maximum, and a note.",
  "My labels from automatic rules plus my reading of each record. Iowa State stores observation time, not arrival time, and holds some later inserts. You must re-check all 36 (Hours 11-12)."),
 ("data/live_feed_only_outages.csv", "7 gauges silent in the live feed but repaired in the archive, the case Round 54 worried about.",
  "Could include Iowa State's own ingest gaps; check whether other gauges went silent at the same moment (Hour 42)."),
 ("data/usgs_to_nwsli_map.json", "USGS site number to NWS 5-character ID for 359 of the 387 pilot gauges, from NOAA's HADS list (pulled 16 Nov 2026).",
  "Current list only; a few 2017-era IDs may have changed."),
 ("data/guadalupe_4jul2025_hydrographs.json", "Gage height for Hunt, North Fork near Hunt, Kerrville and Center Point, 00:00-11:00 local time on 4 July 2025.",
  "Hunt thinned to 10-minute steps before 9:30 UTC. Inserted crests are marked in the note."),
 ("data/pilot_results_round55.json", "Every pilot number in this guide in one machine-readable file: census bins, inserted-crest qualifiers, live-feed classes, alarm replay, virtual-gauge blank-outs, the Naples tide check, the Hunt/Center Point facts, and (new) P8 equipment limits, P9 live-feed detector and P10 feasibility checks.",
  "Numbers are from in-sample pilots on development floods; none is a final result."),
 ("data/watchlist.csv", "116 big-rise gauges from the pilot, ready for DarkWatch.",
  "Mostly summer-flood regions; add about 50 West Coast gauges for winter storms (Hour 15)."),
 ("data/gauge_thresholds_usgs.csv", "Pilot P8: each pilot gauge's USGS operational maximum (equipment limit) and NWS flood stage from the new API's time-series-metadata, 133 gauges (115 with an operational maximum).",
  "Current values; some limits may have been set after the flood. Flood stage appears under several label variants. Verify 10 by hand."),
 ("data/live_detector_pilot.csv", "Pilot P9: for 125 gauges (121 with live data), how many silence, impossible-value and flat-line alarms the real-time rules raised in the live feed, with the first alarm time and value, and whether each impossible value is confirmed wrong (above the later archive crest, negative, or an error code).",
  "In-sample: rules designed after seeing these floods. Confirmation uses the archive crest after the fact. Labels come from my P3 classes."),
 ("code/gd_live_rules.py", "The three P9 live-feed rules (silence, impossible value, flat line) in Python, with a self-test on synthetic series. Self-test passes.",
  "Pilot thresholds; the flat-line rule fires on natural crests and needs a neighbour condition. Re-tune on development floods only."),
 ("code/gd_gaps.py + code/test_gd_gaps.py", "The gap rule in Python (inserted-crest aware) with tests on the real Hunt record. Tests pass.",
  "Ported from the browser version; tested on Hunt only. Write tests for more gauges (Hour 93)."),
 ("code/gd_fetch.py", "Downloaders for the new USGS Water Data API (with your key), the Iowa State live feed (with polite pauses) and the USGS-to-NWS ID list.",
  "Written against API behaviour checked on 16-17 Nov 2026; not run end-to-end from this workspace because its network is restricted. Verify on Hour 4."),
 ("code/gd_alarm.py", "Silence alarm vs plain missing-data flag, with the scoring used in the pilot.",
  "Silence only; see code/gd_live_rules.py for pilot frozen and implausible rules. You build the final four rules (Hours 83-86)."),
 ("code/gd_virtual.py", "Blank-out test with hold-last-value, naive transfer, oracle line, and a slot for your fitted regression.",
  "Naive baselines only. The lag in the pilot was chosen on the same event (a leak you will remove)."),
 ("code/darkwatch.py + code/darkwatch.yml", "Live logger polling the USGS 'latest-continuous' collection every 15 minutes, plus a GitHub Actions workflow to run it free in the cloud.",
  "The query was tested live on 17 Nov 2026 (3 Guadalupe gauges); the workflow itself has not been run."),
 ("code/make_figures.py + figs/", "Script and PNGs for the seven pilot figures in this guide.",
  "Pilot figures; your final figures use test floods."),
 ("Undermind workspace 'GaugeDark - stream gauge outages during floods'", "Three deep literature searches (gauge outages in floods; real-time gap filling and virtual gauges; silence detection in sensor networks), 400+ ranked papers with summaries.",
  "Abstract-level screening; I read only a few full texts (Studley 2001, Quintero 2026, Vlah 2024, Luna 2020)."),
]
def hours_using(fname):
    keys = [os.path.basename(p.strip()) for p in re.split(r"\+|,", fname) if p.strip()]
    keys = [k for k in keys if k and k != "figs/"]
    out = []
    for i, h in enumerate(HOURS):
        blob = " ".join([h["uses"], " ".join(h["steps"])])
        if any(k in blob for k in keys) or ("Undermind" in fname and "Undermind" in blob) or (fname.startswith("code/make_figures") and "figs/" in blob):
            out.append(i + 1)
    return out

# ---------- CSS ----------
CSS = """
@page { size: Letter; margin: 0.75in 0.8in 0.8in 0.8in; }
* { box-sizing: border-box; }
body { font-family: 'Inter', sans-serif; color: #1a1a19; font-size: 9.6pt; line-height: 1.45; margin: 0; }
h1 { font-size: 21pt; font-weight: 650; letter-spacing: -0.02em; margin: 0 0 4pt; color: #0b0b0b; }
h2 { font-size: 13pt; font-weight: 650; margin: 16pt 0 6pt; color: #0b0b0b; }
h3 { font-size: 10.5pt; font-weight: 650; margin: 10pt 0 4pt; color: #0b0b0b; }
p { margin: 0 0 6pt; }
h1, h2, h3, .label { break-after: avoid; page-break-after: avoid; }
.grid2, .grid3, .heat, table tr { break-inside: avoid; }
.kicker { font-size: 8pt; letter-spacing: 0.12em; text-transform: uppercase; color: #2a78d6; font-weight: 600; margin-bottom: 4pt; }
.lede { font-size: 11pt; color: #33322f; line-height: 1.5; }
.part { page-break-before: always; }
.muted { color: #52514e; }
.small { font-size: 8.4pt; }
table { border-collapse: collapse; width: 100%; margin: 4pt 0 10pt; }
th { text-align: left; font-weight: 600; font-size: 8.2pt; color: #52514e; border-bottom: 1.2px solid #0b0b0b; padding: 4pt 6pt 4pt 0; }
td { vertical-align: top; border-bottom: 0.6px solid #e4e3df; padding: 5pt 6pt 5pt 0; font-size: 8.8pt; }
.grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12pt; }
.grid3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10pt; }
.card { border: 0.8px solid #e4e3df; border-radius: 6pt; padding: 9pt 11pt; background: #fcfcfb; break-inside: avoid; }
.card h3 { margin-top: 0; }
.stat { font-size: 22pt; font-weight: 650; color: #0b0b0b; letter-spacing: -0.02em; line-height: 1.1; }
.stat-l { font-size: 8.3pt; color: #52514e; margin-top: 3pt; }
.heat { display: grid; grid-template-columns: repeat(8, 1fr) 1.25fr; border-radius: 6pt; overflow: hidden; margin: 6pt 0 4pt; }
.heat div { padding: 7pt 4pt 6pt; text-align: center; }
.heat .lab { font-size: 7.2pt; letter-spacing: 0.04em; text-transform: uppercase; opacity: 0.9; }
.heat .val { font-size: 15pt; font-weight: 650; }
.heat .w { font-size: 7pt; opacity: 0.8; }
.tag { display: inline-block; font-size: 7.4pt; font-weight: 600; padding: 1pt 5pt; border-radius: 3pt; background: #eaf2fc; color: #1d5ea8; margin-right: 3pt; }
.tag.ai { background: #fdeee6; color: #a3431a; }
.tag.you { background: #e5f6ef; color: #12704e; }
.hour { border-top: 1.4px solid #0b0b0b; padding: 7pt 0 9pt; break-inside: avoid; }
.hhead { display: flex; justify-content: space-between; align-items: baseline; }
.hnum { font-size: 8pt; font-weight: 700; color: #2a78d6; letter-spacing: 0.06em; text-transform: uppercase; }
.hdate { font-size: 8pt; color: #52514e; }
.htitle { font-size: 11pt; font-weight: 650; margin: 2pt 0 2pt; color: #0b0b0b; }
.why { font-size: 8.8pt; color: #52514e; font-style: italic; margin-bottom: 4pt; }
.hcols { display: grid; grid-template-columns: 1.55fr 1fr; gap: 14pt; }
ol.steps { margin: 0; padding-left: 14pt; } ol.steps li { margin-bottom: 2.5pt; font-size: 8.9pt; }
ul.check { list-style: none; margin: 0; padding: 0; } ul.check li { font-size: 8.7pt; margin-bottom: 2pt; padding-left: 13pt; position: relative; break-inside: avoid; }
ul.check li:before { content: ''; position: absolute; left: 0; top: 2.5pt; width: 7pt; height: 7pt; border: 1px solid #52514e; border-radius: 1.5pt; }
.done { font-size: 8.6pt; margin-top: 5pt; padding: 4pt 7pt; background: #f3f2ef; border-radius: 4pt; }
.uses { font-size: 8pt; margin-top: 4pt; color: #a3431a; }
.label { font-size: 7.4pt; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; color: #52514e; margin-bottom: 2pt; }
.week { page-break-before: always; border-radius: 8pt; background: #0f2747; color: #f4f6f9; padding: 14pt 16pt; margin-bottom: 8pt; }
.week .kicker { color: #9cc3f2; }
.week h2 { color: #fff; margin: 2pt 0 4pt; font-size: 15pt; }
.week p { color: #dfe6ef; margin: 0 0 3pt; }
.figure { margin: 6pt 0 10pt; break-inside: avoid; }
.caption { font-size: 8.2pt; color: #52514e; margin-top: 3pt; }
.toc td { font-size: 10pt; padding: 6pt 0; }
.verdict { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8pt; margin-top: 6pt; }
.verdict div { border-radius: 5pt; padding: 6pt 8pt; font-size: 8.5pt; }
.v-s { background: #e5f6ef; } .v-c { background: #fdeee6; } .v-u { background: #f3f2ef; }
.callout { border-left: 3px solid #2a78d6; padding: 6pt 10pt; background: #f4f8fd; margin: 8pt 0; font-size: 9.2pt; }
a { color: #1d5ea8; text-decoration: none; word-break: break-all; }
"""

def heat_color(v):
    # single-hue sequential ramp (blue), light -> dark over 6..10
    ramp = ["#dce9f8", "#b9d3f1", "#8fb8e8", "#5d97dc", "#2a78d6", "#1d5ea8", "#134581"]
    t = max(0, min(1, (v - 6.5) / 3.5))
    return ramp[min(len(ramp) - 1, int(round(t * (len(ramp) - 1))))]

def heat_row():
    cells = []
    for name, v, w in RATINGS:
        bg = heat_color(v); fg = "#fff" if v >= 8.5 else "#0b0b0b"
        cells.append(f'<div style="background:{bg};color:{fg}"><div class="lab">{name}</div><div class="val">{v:g}</div><div class="w">weight {w}%</div></div>')
    cells.append(f'<div style="background:#0b0b0b;color:#fff"><div class="lab">Weighted total</div><div class="val">{TOTAL:.2f}</div><div class="w">out of 10</div></div>')
    return '<div class="heat">' + "".join(cells) + "</div>"

# ---------- pages ----------
def cover():
    return """<html><head><meta charset="utf-8"><style>
    @page { size: Letter; margin: 0; } body { margin:0; font-family:'Inter',sans-serif; }
    .c { height: 11in; width: 8.5in; display:flex; flex-direction:column; justify-content:center; align-items:center; position:relative; background:#fbfbfa; }
    .t { font-size: 54pt; font-weight: 300; letter-spacing: 0.02em; color:#0b0b0b; }
    .r { width: 44pt; height: 2px; background:#2a78d6; margin-top: 18pt; }
    .f { position:absolute; bottom: 0.9in; font-size: 8.5pt; letter-spacing: 0.14em; text-transform: uppercase; color:#8a8984; }
    </style></head><body><div class="c"><div class="t">Research</div><div class="r"></div>
    <div class="f">GaugeDark &nbsp;·&nbsp; 17 November 2026 – 31 January 2027</div></div></body></html>"""

def toc():
    rows = [("1", "Executive summary and roadmap", "the project in plain words, ratings, ISEF fit, the line from question to fair"),
            ("2", "What I checked and what changed", "fact-check of Round 54 and the audit, literature verification"),
            ("3", "Work already completed", "10 pilots, every file, its limits, and the hours that use it"),
            ("4", "Hypotheses and what counts as an answer", "support / contradict / unresolved, decided in advance"),
            ("5", "Decision points and fallback paths", "kill tests and what to do if things fail"),
            ("6", "Risks and the 11 weeks at a glance", "what could go wrong and the hour that guards against it"),
            ("7", "Forms and fair requirements", "every ISEF and TCRSF form and task, the hour it happens, and the link"),
            ("8", "The plan, hour by hour", f"{NH} hours, 17 Nov to 31 Jan, then the February dates"),
            ("9", "Sources", "every source behind a claim in this guide")]
    t = "".join(f"<tr><td style='width:28pt;font-weight:650;color:#2a78d6'>{a}</td><td style='font-weight:600'>{b}</td><td class='muted'>{c}</td></tr>" for a, b, c in rows)
    return f"""<div class="kicker">Contents</div><h1>GaugeDark</h1>
    <p class="lede">A step-by-step guide to a public-data research project on river gauges that go silent, or start giving wrong readings, when floods hit hardest.</p>
    <table class="toc">{t}</table>
    <div class="callout"><b>How to read the labels.</b> <span class="tag ai">Done by AI</span> marks work I (Claude) already ran on 16-17 Nov 2026. You must re-run and verify it.
    <span class="tag you">You</span> marks work only you can do. Under ISEF 2026-27 rules the research plan, abstract, poster and citations must be in your own words, and Form 2A asks for a log of every AI prompt. This guide is a plan and a set of pilots, not text to copy.</div>"""

def part1():
    hist = " · ".join(f"{a}: <b>{b}</b>" for a, b in HISTORY)
    return f"""<div class="part"><div class="kicker">Part 1 · Executive summary</div><h1>When the river rises fastest, the warning network goes blind, or starts lying</h1>
<p class="lede">At 4:35 am on 4 July 2025 the river gauge at Hunt, Texas, the one nearest Camp Mystic, sent its last reading: 29.45 ft and climbing about 7 ft every half hour. Then nothing for 35 hours. Twenty miles downstream, the Center Point gauge did something stranger: it kept transmitting, but it reported about 21 ft while the river crested at 39.6 ft. USGS later deleted those readings. Your project asks how often this happens across U.S. floods, what predicts it, and whether software can notice in real time and fill in a best estimate.</p>
<div class="figure">{img("f1_guadalupe.png")}<div class="caption">Figure 1. Three Guadalupe River gauges on 4 July 2025, re-pulled from USGS and the Iowa State live-feed archive on 16-17 Nov 2026. Hollow circles are crest values USGS inserted later from surveys. <span class="tag ai">Done by AI</span> You reproduce this in Hour 5.</div></div>
<div class="grid2">
 <div class="card"><div class="label">Research question · technical</div>
 <p>During U.S. floods, how often do USGS stream gauges stop delivering valid real-time stage data (silent, frozen, under-reading or physically implausible) as the river rises; which gauge and flood characteristics predict it; and can a real-time detector plus a neighbour-based virtual gauge flag those failures and estimate the missing stage better than a plain missing-data flag and persistence on held-out floods?</p></div>
 <div class="card"><div class="label">Research question · plain words</div>
 <p>When a river floods hardest, do the sensors that warn people break or start giving wrong numbers? How often, at which gauges, and can a program spot it within minutes and make a sensible guess of the real water level until the sensor is fixed?</p></div>
</div>
<h2>What you build</h2>
<div class="grid3">
 <div class="card"><h3>1 · A census</h3><p class="small">Every USGS gauge in 15-30 pre-registered floods (2017-2025), compared two ways: the official archive and the live feed forecasters actually received. Output: failure rates by size of rise, with error bars.</p></div>
 <div class="card"><h3>2 · DarkDetect</h3><p class="small">A real-time detector with four rules (silent, frozen, under-reading, implausible) that uses only data available at that moment, tested on floods it never saw, against a plain "no data" flag.</p></div>
 <div class="card"><h3>3 · A virtual gauge</h3><p class="small">An upstream-to-downstream model fitted on past floods that estimates the missing water level with an error range, tested by hiding real rising limbs. Plus DarkWatch, a live logger running this winter.</p></div>
</div>
<div class="grid2" style="margin-top:10pt">
 <div><h3>Who would use it</h3><p class="small">National Weather Service forecasters at River Forecast Centers and local offices, who decide when to warn; county emergency managers watching gauge dashboards; USGS data teams who repair gauges after floods; app makers who show gauge readings to the public; and researchers who study floods from the USGS archive without knowing it was edited.</p>
 <h3>Why now</h3><p class="small">The July 2025 Texas flood killed more than 130 people. A 2026 paper (Baruah et al.) found the failed Hunt gauge stopped the national model from correcting itself, and a second 2026 study (Quintero et al.) shows the model detects about 80% of high-flow events in its first hour with gauge data, against about 10% without it. Texas is funding new warning networks, and USGS is replacing its data system (the old service shuts on 22 Feb 2027). This is the moment to measure the problem.</p></div>
 <div><h3>Method in five steps</h3><ol class="steps small">
 <li>Pre-register a flood list and a dev/test split before looking at results.</li>
 <li>Download archive and live-feed records for every gauge; detect failures with a fixed rule; hand-check 150 random cases with a second rater.</li>
 <li>Model failure vs rise, rise speed, basin size and "above previous record", with errors clustered by flood.</li>
 <li>Build the detector and virtual gauge; tune only on development floods; lock thresholds.</li>
 <li>Evaluate once on test floods and on your live DarkWatch log; report support, contradiction or "unresolved" by rules written in advance (Part 4).</li></ol></div>
</div></div>

<div class="part"><div class="kicker">Part 1 · Executive summary (continued)</div><h2 style="margin-top:0">Ratings on the same rubric used in every earlier round</h2>
{heat_row()}
<p class="small muted">Weighted total = 0.15 Stakes + 0.20 Novelty + 0.15 Build + 0.15 Depth + 0.15 Evidence + 0.10 Feasible + 0.05 Timely + 0.05 Defence. History: {hist}. Uncertainty on the total is about ±0.3. These are judgments on a rubric, not predictions of awards.</p>
<table><tr><th style="width:16%">Score</th><th>Why it sits there</th></tr>
<tr><td>Stakes 9.5</td><td>Flash floods are the deadliest U.S. weather hazard in many years; the Texas case ties gauge failure directly to forecast failure in a peer-reviewed paper.</td></tr>
<tr><td>Novelty 8</td><td>Gauge damage is known (USGS counts 192 gauges damaged in Harvey, Irma and Maria) and estimating data for silent gauges exists (SHEM 2018, a 2017-priority patent). New: failure measured by flood size across many floods; the live-feed "wrong but alive" taxonomy; a held-out detector. Capped below 8.5 because the effect itself is known.</td></tr>
<tr><td>Build 8.5</td><td>Three working artefacts (census pipeline, detector, virtual gauge) plus a live logger and an offline demo.</td></tr>
<tr><td>Depth 8.5</td><td>Clustered logistic models, survival curves, bootstrap by flood, pre-registration, second-rater agreement.</td></tr>
<tr><td>Evidence 8</td><td>Station-level re-run of 387 gauges, live-feed comparison of 36 dark gauges, alarm replay, virtual-gauge pilot, and (new) equipment limits for 133 gauges and a live-feed detector pilot on 121 gauges, all real data. Held back by: in-sample pilots, 7 hand-picked floods, my labels not yet checked by you. More pilots cannot fix that; only your held-out test can, so the score stays at 8.</td></tr>
<tr><td>Feasible 8</td><td>All public, free, no participants; access demonstrated. Risks: USGS API retirement during the project, Iowa State rate limits, and 154 hours finishing on 31 January is tight (the first week of February is buffer).</td></tr>
<tr><td>Timely 9</td><td>2025 disaster, 2026 papers, 2026-27 data-system change. Crowding risk: many Texas students will do flood-warning sensors; you study data failure instead.</td></tr>
<tr><td>Defence 7.5</td><td>The live-feed comparison answers the audit's main objection. A hydrologist mentor would lift this; "USGS already knows" must be answered with your numbers.</td></tr></table>
<h2>How well does it fit an ISEF-winning project?</h2>
<div class="grid2">
<div class="card"><h3>Strengths</h3><ul class="small" style="padding-left:12pt;margin:0">
<li>A true, checkable story with a number on it (silent at 29.45 ft, crest 37.52 ft).</li>
<li>A surprising finding a judge has not heard: the live feed often <i>lied</i> rather than went silent, and 20 of 121 big-rise gauges sent impossible values in real time, 12 of them at gauges whose archive was later cleaned.</li>
<li>Something built and tested on held-out data against a fair baseline; ISEF judging weights execution and creativity heavily.</li>
<li>No participants, no lab, $0 cost.</li></ul></div>
<div class="card"><h3>Weak points to fix</h3><ul class="small" style="padding-left:12pt;margin:0">
<li>Hydrology questions in the interview: get a mentor and read the 12 core sources.</li>
<li>A flat-line (frozen) rule on one gauge cannot tell a stuck sensor from a broad crest (pilot P9); you need the neighbour rule or an honest "open problem".</li>
<li>Flood-warning projects will be common next season (one won a 2026 Texas special award). Lead with the data-failure finding, not a sensor.</li>
<li>NOAA gave no ISEF special award in 2026, so the obvious special award may be gone.</li>
<li>All results must be re-run and written by you, with an AI log on Form 2A.</li></ul></div></div>
<p class="callout"><b>My verdict:</b> a strong regional and state project with a realistic shot at ISEF finalist. A Grand Award needs three things the pilots only hint at: (1) the live-vs-archive taxonomy confirmed by your hand check at census scale, (2) a detector that beats the plain flag on test floods it never saw, and (3) clean answers to hydrology questions. Category: <b>Earth and Environmental Sciences</b> if you lead with the measurement; <b>Systems Software</b> if you lead with the detector. I lean Earth and Environmental, where the judges will value the data finding.</p>
<h2>Three numbers from the pilots</h2>
<div class="grid3">
<div class="card"><div class="stat">24%</div><div class="stat-l">of gauges whose river rose 20 ft or more had a 1-hour+ archive gap on the rise or crest (28 of 116), vs 1% for rises under 5 ft (1 of 103). 7 floods, in-sample.</div></div>
<div class="card"><div class="stat">16 of 33</div><div class="stat-l">archive-dark gauges with live data were not silent in real time: they sent frozen (8), too-low (2) or impossible (6) values.</div></div>
<div class="card"><div class="stat">0.18 → 0.66</div><div class="stat-l">precision of a plain "no data" flag vs a silence alarm that needs a recent rise (19 of 28 dangerous gaps caught, 10 false alarms).</div></div></div>
</div>"""

def part2():
    rows = "".join(f"<tr><td style='width:36%'>{e(a)}</td><td>{e(b)}</td></tr>" for a, b in CORRECTIONS)
    return f"""<div class="part"><div class="kicker">Part 2 · What I checked and what changed</div><h1>Round 54 was right about the story and wrong about several details</h1>
<p class="lede">I re-downloaded every flood from USGS, pulled the live-feed copy for 359 gauges from Iowa State University, checked the key facts against primary sources, and ran three literature deep searches (Undermind) plus targeted web checks. Consensus and Firecrawl ran out of free credits, so literature screening relied on Undermind, Google-indexed sources and direct reads.</p>
<table><tr><th>Claim</th><th>What I found</th></tr>{rows}</table>
<h2>The closest prior work, and the gap</h2>
<table><tr><th style="width:30%">Work</th><th>What it does</th><th style="width:30%">What it does not do</th></tr>
<tr><td>USGS Fact Sheet 2016-3027 (East 2016)</td><td>About 98% of possible values recovered in the 2015 Texas floods; a gauge stopped at 40 ft with 5 ft more shown by high-water marks.</td><td>One event, network-wide; not by size of rise; not live vs archive.</td></tr>
<tr><td>Studley 2001 (USGS, Kansas)</td><td>Causes of missing gage-height record 1987-99 (orifice 46%, sensor 29%...).</td><td>No flood category; no timing relative to rises.</td></tr>
<tr><td>SHEM (Petty & Dhingra 2018); US Patent 11,238,356</td><td>Machine-learning proxy data for gauges that stop transmitting.</td><td>No failure rates; no frozen or wrong-value detection; no crest-specific held-out test.</td></tr>
<tr><td>Vlah et al. 2024; Harvey et al. 2012; Luna et al. 2020</td><td>Gap filling; simple donor regression often beats deep learning.</td><td>Mostly random gaps at ordinary flows; peak skill rarely reported.</td></tr>
<tr><td>Baruah et al. 2026; Quintero et al. 2026; Seo et al. 2021</td><td>Gauge assimilation drives short-range forecast skill; Hunt's failure stopped nudging.</td><td>Do not measure how often gauges fail across floods.</td></tr>
<tr><td>Polz et al. 2023 (microwave links)</td><td>Rain sensors black out in the heaviest rain: outage caused by the extreme itself.</td><td>Different sensor; an analogue, not a river study.</td></tr>
<tr><td>Hughes et al. 2015; Finck & Pedrollo 2021</td><td>Detecting missing reports in sensor networks; forecasting despite lost telemetry.</td><td>Do not condition silence on rising water; do not test U.S. flood gauges.</td></tr></table>
<p class="small muted">Undermind's summary of the first deep search agrees: "The literature does not yet establish how often river gauges fail specifically on flood rises or near peaks." Treat this as a careful search, not proof of absence; Hour 25 repeats it.</p></div>"""

def part3():
    rows = ""
    for f, what, lim in FILES:
        hs = hours_using(f)
        rows += f"<tr><td style='width:23%'><b>{e(f)}</b></td><td>{e(what)}</td><td style='width:26%' class='muted'>{e(lim)}</td><td style='width:12%'>{e(compress(hs)) or '-'}</td></tr>"
    cls = "".join(f"<tr><td style='width:18%'><b>{a}</b></td><td>{e(b)}</td></tr>" for a, b in CLASS_RULES)
    box = "".join(f"<tr><td>{a}</td><td>{b}</td><td>{c}</td></tr>" for a, b, c in BOXES)
    P = [
     ("P1", "Archive census, 7 floods, 387 gauges (station level)", "Dark 1 h+ on rise or crest: 1/103 (rise under 5 ft), 3/58 (5-10), 4/110 (10-20), 28/116 (20+). 32 of the 36 dark gaps contain the crest. Round 54's 36/114 did not reproduce exactly; its rule on today's data gives 32/116.", hrs(7, 8, 45, 61, 66)),
     ("P2", "Inserted crests", "60 gauges have values that look inserted (isolated, off-schedule peaks). In the new USGS API only 2 carry DAYUNKNOWN, 2 FLOOD, 1 REVISED: official flags cannot find them, so the structural rule is needed.", hrs(4, 21, 45)),
     ("P3", "Live feed vs archive (Iowa State HADS copy)", "Of 36 archive-dark gauges: 3 no live record; of the other 33: silent 12, frozen 8, under-read 2, implausible 6, plausible-then-deleted 5. Separately, 7 gauges silent live but repaired in the archive.", hrs(11, 12, 44, 59, 60)),
     ("P4", "Silence alarm replay", "157 gaps, 28 dangerous. Alarm (rise of 0.5 ft in the last hour): 19 hits, 9 misses, 10 false alarms. Plain flag: 28 hits, 129 false alarms. In-sample.", hrs(82, 89)),
     ("P5", "Virtual-gauge blank-out, 6 healthy pairs", "Copying the upstream change beat holding the last value in 6 of 6 pairs (e.g. Kerrville to Comfort RMSE 4.0 vs 25.3 ft) but missed Texas crests by -9.2, -19.9 and +13.9 ft. A fitted model is needed.", hrs(97, 98, 99, 101, 102, 103, 104, 105)),
     ("P6", "Tide-gauge control spot check", "Naples (NOAA 8725110) in Hurricane Ian: last value 9.05 ft at 17:06 UTC 28 Sep 2022, then none through 1 Oct. Confirms Round 54.", hrs(21) + " (context)"),
     ("P7", "Guadalupe case facts", "Hunt: 29.45 ft at 09:35 UTC, crest 37.52 ft inserted (DAYUNKNOWN), silent 35.0 h, 8.07 ft below crest. Center Point: archive stops at 6.16 ft, 81 h gap, crest 39.61 ft inserted; live feed kept sending. Kerrville complete (still provisional).", hrs(4, 5, 91, 102, 107)),
     ("P8 · new", "Equipment limits and flood stage (USGS thresholds, 133 gauges)", "Big-rise gauges whose crest reached their own operational maximum went dark 7 of 13 times (54%, CI 29-77%) vs 20 of 92 (22%, CI 15-31%) below it (unclustered OR 4.2, p = 0.036). But 23 of 27 dark gauges stopped reporting BELOW their limit (Hunt: 29.45 ft vs limit 60 ft), and for 20 of 27 the crest never reached it, and 11 of 14 failed at or above NWS flood stage. Limits explain part of the failures, not most.", hrs("p8v", "mech", 38, 66)),
     ("P9 · new", "Live-feed detector rules (125 gauges, 121 with live data)", "Silence rule: 9 of 12 silent gauges and 5 of 7 live-only outages, 1 alarm on 81 healthy gauges; at Hunt a 60-min floor alarms only after the estimated crest, a 15-min floor 20 min before it. Impossible-value rule: 6 of 6 implausible gauges, and impossible values at 20 of 121 gauges overall (15 in Harvey), 12 at gauges whose archive was later cleaned. 7 gauges truly rose above their published limit, so the limit alone is not a safe ceiling. Flat-line rule: 4 of 8 frozen gauges but 24 of 81 healthy gauges alarmed. In-sample.", hrs("p9v", 82, 83, 84, "srccheck")),
     ("P10 · new", "Feasibility checks", "Hunt has no backup stage sensor (only annual peaks and daily means besides the gage-height series). The STN web service returned 'Access forbidden' to a browser, so the flood list must come from the STN Data Portal or pygeohydro. The new API's bbox filter works for continuous data and site metadata.", hrs(6, 28, 38)),
    ]
    prow = "".join(f"<tr><td>{a}</td><td>{e(b)}</td><td>{e(c)}</td><td>{e(d)}</td></tr>" for a, b, c, d in P)
    return f"""<div class="part"><div class="kicker">Part 3 · Work already completed <span class="tag ai">Done by AI</span></div><h1>Ten pilots, run on real data on 16-17 November 2026</h1>
<p class="lede">Everything here was run by me through your desktop app's browser (USGS, Iowa State, NOAA) and in my workspace. It is pilot evidence that the project works and roughly what to expect. It is not your result. The plan re-runs or verifies every piece in your own hands, mostly in Week 2. P8-P10 were added in this revision because they test the two places the project was weakest: <i>why</i> gauges fail, and whether wrong-but-alive readings can be caught automatically.</p>
<table><tr><th style="width:6%">#</th><th style="width:24%">Pilot</th><th>Result</th><th style="width:13%">Used in hours</th></tr>{prow}</table></div>

<div class="part"><div class="kicker">Part 3 · Pilot figures</div>
<div class="grid2"><div class="figure">{img("f2_dose.png")}<div class="caption">Figure 2. P1, archive outages by size of rise.</div></div>
<div class="figure">{img("f3_live.png")}<div class="caption">Figure 3. P3, what the live feed showed during the 36 archive gaps.</div></div></div>
<div class="grid2"><div class="figure">{img("f4_alarm.png")}<div class="caption">Figure 4. P4, silence alarm vs plain flag on pilot floods (in-sample).</div></div>
<div class="figure">{img("f5_virtual.png")}<div class="caption">Figure 5. P5, naive virtual gauge vs holding the last value.</div></div></div>
<div class="grid2"><div class="figure">{img("f6_limits.png")}<div class="caption">Figure 6. P8, failure rate by whether the crest reached the gauge's own USGS equipment limit (Wilson 95% intervals, unclustered).</div></div>
<div class="figure">{img("f7_detector.png")}<div class="caption">Figure 7. P9, real-time rules on the live feed: share of labelled failures caught vs share of 81 healthy big-rise gauges alarmed (in-sample). The flat-line rule is not usable alone.</div></div></div>
<p class="small muted">What P9 changed in the plan: the impossible-value rule now uses max(equipment limit, prior record) + 2 ft as its ceiling ([[n:mech]] and Hour 84); the frozen rule must include a neighbour check (Hour 83, Hour 86); the silence floor is chosen on development floods in Hour 82, because at Hunt a 60-minute floor fires only after the estimated crest; and a new hour checks whether live-feed silences are really Iowa State outages ([[n:srccheck]]).</p></div>

<div class="part"><div class="kicker">Part 3 · Files delivered with this guide</div><h2 style="margin-top:0">Every file, what it holds, its limits, and the hours that use it</h2>
<table><tr><th>File</th><th>What it contains</th><th>Limitations</th><th>Hours</th></tr>{rows}</table>
<h3>Rules used for the live-feed classes (P3)</h3><table>{cls}</table>
<h3>Pilot flood boxes (west, south, east, north) and dates</h3><table><tr><th>Flood</th><th>Bounding box</th><th>Dates</th></tr>{box}</table>
<p class="small muted">Gap rule (all pilots): drop estimated values; inserted points are isolated or off-schedule peaks before a long gap; a gap is at least 60 min and 3.5 times the usual interval; it is "dark" if the stage rose more than 0.3 ft in the 30 min before it or if the event crest falls inside it. Source code: code/gd_gaps.py.</p>
<div class="callout"><b>What I could not do from here:</b> run your Python code against the live APIs from my workspace (its network is restricted, so the downloads ran in your browser), hand-verify every gauge, learn when NWS actually received each reading (Iowa State stores observation time), reach the STN flood-event service, or check paywalled full texts. These limits are why Week 2 re-runs everything.</div></div>"""

def compress(nums):
    if not nums: return ""
    nums = sorted(nums); out = []; a = p = nums[0]
    for n in nums[1:]:
        if n == p + 1: p = n; continue
        out.append(f"{a}-{p}" if p > a else str(a)); a = p = n
    out.append(f"{a}-{p}" if p > a else str(a)); return ", ".join(out)

def wk(i):  # hour range string of week i (1-based)
    return f"{(i-1)*PER_WEEK+1}-{i*PER_WEEK}"

def roadmap():
    stages = [
     ("1 · Ask", "Week 1", wk(1), "Research plan in your own words; Forms 1, 1A, 1B signed; 12 core papers read.", "A signed plan and an official start date"),
     ("2 · Check", "Week 2", wk(2), "Re-run my pilots, hand-check 30 gauges, verify P8 and P9, start DarkWatch.", "K1: is the effect real enough to continue?"),
     ("3 · Measure", "Weeks 3-5", f"{(2)*PER_WEEK+1}-{hn(63)}", "Pre-register floods, pull the national census, hand-check 150 cases with a second rater, live vs archive.", "H1 and H2: how often do gauges fail, and how?"),
     ("4 · Explain", "Weeks 5-6", f"{hn(65)}-{hn(77)}", "Clustered models of rise, rise speed, record stage, basin size, equipment limits and flood stage.", "H1 and H5: what predicts failure?"),
     ("5 · Build", "Weeks 6-7", f"{hn(81)}-{hn(104)}", "Four real-time rules, neighbour graph, thresholds locked on development floods; fitted virtual gauge.", "A detector and a virtual gauge, frozen before testing"),
     ("6 · Test", "Week 8", wk(8), "One run on held-out floods, flood bootstrap, warning time, your own live log.", "H3 and H4: do they work on floods they never saw?"),
     ("7 · Present", "Weeks 9-11", f"{8*PER_WEEK+1}-{NH}", "Paper, abstract, poster, quad chart, video, Form 2A, mock judging, uploads.", "Everything finished and uploaded on 31 January"),
    ]
    st = "".join(f"<tr><td style='width:13%'><b>{a}</b></td><td style='width:11%'>{b}</td><td style='width:10%'>{c}</td><td>{e(d)}</td><td style='width:27%'><b>{e(o)}</b></td></tr>" for a, b, c, d, o in stages)
    fin = [
     ("Research plan and Forms 1, 1A, 1B signed and dated before data work", hrs("rp1", "rp2", "forms")),
     ("Registered on zFairs with Form 1D, photo and category", hrs("reg")),
     ("Flood list pre-registered on GitHub; national data pulled and backed up", hrs(28, 42)),
     ("Results A (prevalence), B (drivers and mechanism), C (detector and virtual gauge) written", hrs(63, 74, 106)),
     ("Held-out test run once; live feed defended; DarkWatch appendix", hrs(113, "srccheck", 166)),
     ("Paper final, numbers and citations checked, clean reproducibility run", hrs(162, 167, 168)),
     ("Official abstract (250 words) and Form 2A with AI prompt log", hrs(152, 151)),
     ("Quad chart and 2-minute video", hrs("quad", "vrec")),
     ("Poster test-printed, judged in a mock round, then ordered", hrs(145, 149, 165)),
     ("Paperwork PDF uploaded, abstract text entered, fee paid, teacher marked ready", hrs("pdf", "upload")),
    ]
    fr = "".join(f"<li>{e(a)} <span class='muted'>(Hour {b})</span></li>" if "," not in b and "-" not in b else f"<li>{e(a)} <span class='muted'>(Hours {b})</span></li>" for a, b in fin)
    return f"""<div class="part"><div class="kicker">Part 1 · Roadmap</div><h1>The line from question to fair</h1>
<div class="callout" style="font-size:10.5pt"><b>In one sentence:</b> I measure how often U.S. river gauges go silent or give wrong readings during floods, test what predicts it, and build and test a tool that catches those failures live and estimates the missing water level.</div>
<table><tr><th>Stage</th><th>When</th><th>Hours</th><th>What you do</th><th>What it answers</th></tr>{st}</table>
<div class="card"><h3>Finished by Sunday 31 January</h3><ul class="check small" style="columns:2;column-gap:16pt">{fr}</ul></div>
<p class="small" style="margin-top:8pt"><b>How the time is spent.</b> {NH} hours over 11 weeks: 2 hours Tuesday to Friday, 3 hours Saturday and Sunday, Mondays off. Every hour produces something you keep: a file, a number, a decision or a signed form. <b>February is not work time:</b> 1-6 Feb is buffer for the TCRSF deadlines, 6-12 Feb is answering any reviewer request, 26 Feb is judging.</p>
<p class="small muted">Cut from the previous version: 10 stand-alone weekly reviews, 6 catch-up hours, the rainfall model, 3 contingency and 4 duplicate hours. Added: research plan, forms, registration, P8 and P9 checks, the H5 test, a live-feed source check, quad chart, video, uploads and a finish-line check.</p></div>"""

def forms_part():
    L = FORM_LINKS
    def a(name): return f'<a href="{L[name]}">{e(name)}</a>'
    rows = [
     (a("Research plan generator") + " + " + a("Research plan instructions"), "Research plan in your own words, 'no special cases' version. Written before any data work.", hrs("rp1", "rp2")),
     (a("Form 1"), "Adult sponsor checklist; your teacher signs.", hrs("forms")),
     (a("Form 1A"), "Student checklist; research plan attached; actual start date added once signatures are in.", hrs("forms")),
     (a("Form 1B"), "Approval form; you and a parent sign BEFORE data work.", hrs("forms")),
     ("Pre-approval", "School review committee, or email the plan to src@tcrsf.net if your school has none.", hrs("forms")),
     (a("zFairs") + " registration", "Teacher registers first; you register the project, category and photo. Opens 9 Dec.", hrs("reg")),
     (a("TCRSF Form 1D"), "Permission, liability and photo release, signed by you and a parent. Required for every project and for the paper competition.", hrs("reg")),
     (a("Abstract form"), "Official 2027 form, 250 words max; the zFairs text must match it word for word.", hrs(123, 152)),
     (a("Form 2A"), "Student Support Disclosure: all human help and every AI use, with the prompt log attached.", hrs(1, 151)),
     ("Quad chart and video", "Optional at TCRSF but judges preview them 19-25 Feb. 1 page and 2 minutes work for both TCRSF and ISEF.", hrs("quad", "vscript", "vrec")),
     ("Paperwork PDF, upload, fee", "One PDF online by 6 Feb (you: 31 Jan); teacher clicks 'Mark Ready'; $25 fee, check postmarked by 8 Feb.", hrs("pdf", "upload")),
     ("Research-paper competition (optional)", "$20; register by 2 Feb; paper, paper abstract and Form 1D by 4 Feb; every figure credited.", hrs("reg", "upload")),
     ("Display rules", "76 cm deep, 122 cm wide, 240 cm high (149 cm above a table); every image credited; no victim names.", hrs(165)),
     ("Logbook", "Dated entries for every hour; judges may read it.", hrs(1, 153)),
    ]
    not_needed = [
     (a("Form 2C"), "Regulated research institution: only if you work in a university or agency lab. GaugeDark is done at home and school, so no."),
     ("Form 2B", "Qualified Scientist: needed for human participants, vertebrate animals, hazardous biological agents or hazardous chemicals, activities or devices. None apply."),
     ("Form 3", "Risk assessment: hazardous chemicals, activities or devices. None."),
     ("Forms 4-6B", "Human participants, vertebrate animals, biological agents, tissues. None. Public gauge data are not human-participant data."),
     ("Form 7", "Continuation projects only. GaugeDark is new."),
    ]
    r = "".join(f"<tr><td style='width:26%'><b>{n}</b></td><td>{e(w)}</td><td style='width:12%'>{h}</td></tr>" for n, w, h in rows)
    nn = "".join(f"<tr><td style='width:26%'><b>{n}</b></td><td>{e(w)}</td></tr>" for n, w in not_needed)
    return f"""<div class="part"><div class="kicker">Part 7 · Forms and fair requirements</div><h1>Every form and fair task, and the hour it happens</h1>
<p class="lede">Twin Cities Regional Science Fair (TCRSF) 2027 on zFairs, under ISEF 2026-27 rules. Links go to the TCRSF-hosted 2027 forms (checked 16 Nov 2026). Each form also appears as a tag on its hour card in Part 8.</p>
<table><tr><th>Form or task</th><th>What it is</th><th>Hour</th></tr>{r}</table>
<h2>Forms you do not need, and why</h2><table>{nn}</table>
<div class="callout"><b>AI rules.</b> ISEF 2026-27 forbids generative AI writing the research plan, abstract or poster, or creating citations, and Form 2A asks for every prompt. This guide gives you steps and pilot evidence; every sentence a judge reads must be yours. Keep the prompt log from Hour 1.</div></div>"""

def part4():
    out = '<div class="part"><div class="kicker">Part 4 · Hypotheses</div><h1>What would support, contradict, or leave each question unresolved</h1><p class="lede">Written before you collect the test data, so the answer cannot be bent to fit. A null or negative result is reported, not hidden.</p>'
    for t, claim, s, c, u, pilot in HYPOTHESES:
        out += f"""<div class="card" style="margin-bottom:9pt"><h3>{e(t)}</h3><p class="small">{e(claim)}</p>
<div class="verdict"><div class="v-s"><b>Supported if</b><br>{e(s)}</div><div class="v-c"><b>Contradicted if</b><br>{e(c)}</div><div class="v-u"><b>Unresolved if</b><br>{e(u)}</div></div>
<p class="small muted" style="margin-top:5pt">Pilot evidence so far: {e(pilot)}</p></div>"""
    return out + "</div>"

def part5():
    k = "".join(f"<tr><td style='width:32%'><b>{e(a)}</b></td><td>{e(b)}</td></tr>" for a, b in KILLS)
    f = "".join(f"<tr><td style='width:32%'><b>{e(a)}</b></td><td>{e(b)}</td></tr>" for a, b in FALLBACKS)
    return f"""<div class="part"><div class="kicker">Part 5 · Decision points and fallbacks</div><h1>When to continue, change course, or stop</h1>
<h2>Decision points</h2><table>{k}</table>
<h2>Fallback paths</h2><table>{f}</table>
<p class="callout">Rule of thumb: you may change a method only for a reason you write down, only using development floods, and never after looking at a test-flood result. Every change goes in CHANGELOG.md with a date.</p></div>"""

def part6():
    r = "".join(f"<tr><td>{e(a)}</td><td style='width:9%'>{b}</td><td style='width:42%'>{e(c)}</td></tr>" for a, b, c in RISKS)
    w = "".join(f"<tr><td style='width:6%'><b>{i+1}</b></td><td style='width:16%'>{(START+dt.timedelta(days=7*i)).strftime('%d %b')} – {(START+dt.timedelta(days=7*i+(5 if i == NW-1 else 6))).strftime('%d %b')}</td><td style='width:9%'>{wk(i+1)}</td><td><b>{e(a)}</b>. {e(b)}</td><td style='width:20%' class='muted'>{e(c)}</td></tr>" for i, (a, b, c) in enumerate(WEEKS))
    return f"""<div class="part"><div class="kicker">Part 6 · Risks</div><h1>What could go wrong</h1>
<table><tr><th>Risk</th><th>Level</th><th>Guard (hour)</th></tr>{r}</table>
<h2>The 11 weeks at a glance</h2>
<p class="small muted">{PER_WEEK} hours a week: 2 hours Tuesday to Friday, 3 hours Saturday and Sunday, Mondays off. The order matters more than the day; shift around holidays within the same week. Finish line: Sunday 31 January 2027. Writing starts in Week 2 (literature-gap table) and continues every week, so the paper is never a last-minute job.</p>
<table><tr><th>Week</th><th>Dates</th><th>Hours</th><th>Focus</th><th>Decision</th></tr>{w}</table></div>"""

def hour_cards():
    out = f'<div class="part"><div class="kicker">Part 8 · The plan, hour by hour</div><h1>{NH} hours, finished on 31 January</h1><p class="lede">Each hour lists why it matters, the steps, a checklist, what "done" looks like, any form it involves (with link), and any file I already prepared for it. Dates assume 2 hours Tuesday to Friday and 3 hours on Saturday and Sunday.</p></div>'
    for i, h in enumerate(HOURS):
        if i % PER_WEEK == 0:
            w = i // PER_WEEK; a, b, c = WEEKS[w]
            d0 = START + dt.timedelta(days=7 * w); d1 = hour_date(i + PER_WEEK - 1)
            out += f'<div class="week" style="{"page-break-before:auto" if w == 0 else ""}"><div class="kicker">Week {w+1} · {d0.strftime("%a %d %b")} – {d1.strftime("%a %d %b %Y")} · Hours {i+1}-{i+PER_WEEK}</div><h2>{e(a)}</h2><p>{e(b)}</p><p><b>Decision point:</b> {e(c)}</p></div>'
        d = hour_date(i)
        steps = "".join(f"<li>{e(s)}</li>" for s in h["steps"])
        checks = "".join(f"<li>{e(c)}</li>" for c in h["checks"] if c != "-")
        uses = f'<div class="uses"><span class="tag ai">Uses AI-completed work</span> {e(h["uses"])}</div>' if h["uses"] else ""
        forms = ""
        if h.get("forms"):
            forms = '<div class="uses" style="color:#12704e"><span class="tag you">Form</span> ' + " · ".join(f'<a href="{FORM_LINKS[f]}">{e(f)}</a>' for f in h["forms"]) + "</div>"
        done = f'<div class="done"><b>Done looks like:</b> {e(h["done"])}</div>' if h["done"] else ""
        new = ' <span class="tag">New</span>' if h.get("new") else ""
        out += f"""<div class="hour"><div class="hhead"><span class="hnum">Hour {i+1}{new}</span><span class="hdate">Week {i//PER_WEEK+1} · {d.strftime("%a %d %b")}</span></div>
<div class="htitle">{e(h["title"])}</div><div class="why">{e(h["why"])}</div>
<div class="hcols"><div><div class="label">Steps</div><ol class="steps">{steps}</ol></div>
<div><div class="label">Checklist</div><ul class="check">{checks or '<li>Nothing to tick</li>'}</ul>{done}{forms}{uses}</div></div></div>"""
    feb = "".join(f"<tr><td style='width:20%'><b>{e(a)}</b></td><td>{e(b)}</td></tr>" for a, b in FEB)
    out += f"""<div class="week"><div class="kicker">After the plan · 1 February – 3 March 2027</div><h2>February: submit, answer reviewers, present</h2><p>No new research. These are dates to check off, and about 6 hours of judging practice once the online preview opens.</p></div>
<table><tr><th>Date</th><th>What to do</th></tr>{feb}</table>
<p class="small muted">Dates from tcrsf.zfairs.com (checked 16 Nov 2026). Times are Central. If TCRSF changes a date, theirs wins: re-check the TCRSF site on 1 February.</p>"""
    return out

def part8():
    s = "".join(f"<tr><td style='width:4%'>{i+1}</td><td>{e(t)}{'<br><a href=\"'+u+'\">'+e(u)+'</a>' if u else ''}</td></tr>" for i, (t, u) in enumerate(SOURCES))
    return f"""<div class="part"><div class="kicker">Part 9 · Sources</div><h1>Sources behind the claims in this guide</h1>
<p class="small muted">Data sources: USGS Water Data (legacy NWIS instantaneous values, and api.waterdata.usgs.gov continuous / latest-continuous collections), Iowa Environmental Mesonet DCP/HADS archive, NOAA HADS station list, NOAA CO-OPS water levels, all accessed 16-17 Nov 2026. Literature workspace: app.undermind.ai/projects/71b485b8-28c0-4895-b05d-b2aa08f5d0e9. Open each source yourself before citing it (Hour 133).</p>
<table>{s}</table></div>"""

def body():
    old = lambda x, tag: remap_old_refs(x, tag)  # front-matter text is written in the old hour numbering
    front = old(toc() + part1(), "p1") + roadmap() + old(part2() + part3() + part4() + part5() + part6(), "p2-6") + forms_part()
    back = part8()
    back = remap_old_refs(back, "sources")
    html_ = front + hour_cards() + back
    return f"<html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{resolve_tokens(html_)}</body></html>"

if __name__ == "__main__":
    out = os.path.join(ROOT, "build")
    open(os.path.join(out, "cover.html"), "w").write(cover())
    open(os.path.join(out, "body.html"), "w").write(body())
    print("html written; hours:", len(HOURS), "total:", TOTAL, "misses:", MISSES)
