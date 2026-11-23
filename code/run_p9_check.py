"""Hour 26: run the three P9 live-feed rules on the 5 check gauges and print the alarms.

Run from the project folder (the one containing code/ and data/):
    python -I code/run_p9_check.py

Reads data/p9_check/live/<NWS ID>.csv (time_utc, value_ft), downloaded with gd_fetch.iem_hads for
the guide's Part 3 pilot windows (UTC): Texas 2025-07-03T00:00Z to 2025-07-08T06:00Z (HNTT2, KRRT2,
GCTT2); Harvey 2017-08-25T00:00Z to 2017-09-02T06:00Z (CCGT2, BAHT2).
Compare the output with data/live_detector_pilot.csv.

Choices made here (also in the logbook):
- Rows with no stage value are dropped (the live feed includes reports with no stage).
- Hunt: Iowa State's later-inserted survey crest (37.52 ft at 10:10 UTC 4 Jul 2025) is removed,
  because values inserted after the fact are not live readings and forecasters could not see them.
- Operational maximums are the values in live_detector_pilot.csv (today's published limits).
Result on 23 Nov 2026: all five gauges matched the pilot.
"""
import sys, csv, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from datetime import datetime, timezone
import gd_live_rules as L

GAUGES = [('HNTT2', 'Hunt', 60.0), ('KRRT2', 'Kerrville', 60.0), ('GCTT2', 'Center Point', 60.0),
          ('CCGT2', 'Cypress Creek', 200.0), ('BAHT2', 'Buffalo Bayou', 90.0)]   # op_max from live_detector_pilot.csv
LIVE = os.path.join('data', 'p9_check', 'live')


def ms(s): return int(datetime.fromisoformat(s).replace(tzinfo=timezone.utc).timestamp() * 1000)
def utc(t): return datetime.fromtimestamp(t / 1000, timezone.utc).strftime('%Y-%m-%d %H:%M')
def first(a): return utc(a[0]['t']) if a else '-'


if __name__ == '__main__':
    for nid, name, op_max in GAUGES:
        path = os.path.join(LIVE, nid + '.csv')
        if not os.path.exists(path):
            print(nid, 'missing file:', path); continue
        rows = list(csv.DictReader(open(path, encoding='utf-8')))
        recs = sorted((ms(r['time_utc']), float(r['value_ft'])) for r in rows if r['value_ft'])
        note = ''
        if nid == 'HNTT2':   # Iowa State's later-inserted survey crest is not a live reading
            n0 = len(recs)
            recs = [x for x in recs if not (utc(x[0]) == '2025-07-04 10:10' and x[1] == 37.52)]
            note = ' (removed inserted 37.52 ft crest)' if len(recs) < n0 else ' (inserted crest NOT found)'
        s60 = L.silent_alarms(recs, min_gap_min=60)
        s15 = L.silent_alarms(recs, min_gap_min=15)
        imp = L.implausible_alarms(recs, op_max=op_max)
        fro = L.frozen_alarms(recs)
        why = (imp[0]['why'] + ' ' + str(imp[0]['v']) + ' ft') if imp else ''
        fv = (str(fro[0]['v']) + ' ft for ' + str(fro[0]['dur_h']) + ' h') if fro else ''
        print(nid, name + ':', len(recs), 'readings with a value' + note)
        print('  silence     60-min floor:', len(s60), 'first', first(s60), '| 15-min floor:', len(s15), 'first', first(s15))
        print('  impossible  :', len(imp), 'first', first(imp), why)
        print('  flat line   :', len(fro), 'first', first(fro), fv)