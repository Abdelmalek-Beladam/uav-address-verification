import csv,json,unittest
from pathlib import Path
SITE=Path(__file__).resolve().parents[1]/'website'
class DashboardDataTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.catalog=json.loads((SITE/'data/catalog.json').read_text(encoding='utf-8'));cls.ds=[json.loads((SITE/'data'/f"{c['id']}.json").read_text(encoding='utf-8')) for c in cls.catalog]
 def test_counts(self):
  expected={'rue_bonaparte':(190,107,97),'rue_de_four':(553,192,149)}
  for d in self.ds:self.assertEqual(len(d['photos']),expected[d['id']][0]);self.assertEqual(len(d['plates']),d['summary']['plates']['total']);self.assertEqual(len(d['addresses']),d['summary']['addresses']['reported'])
 def test_recorded(self):
  for d in self.ds:self.assertEqual(d['source_mode'],'recorded')
 def test_assets(self):
  for d in self.ds:
   self.assertTrue((SITE/d['report_url']).is_file())
   for p in d['plates']:
    for o in p['observations']:
     for k in ['crop','view_url']:
      if o[k]:self.assertTrue((SITE/o[k]).is_file(),o[k])
   for p in d['photos']:
    for u in p['views'].values():self.assertTrue((SITE/u).is_file(),u)
 def test_statuses_unchanged(self):
  for d in self.ds:
   with (SITE/'surveys'/d['id']/'results/plates.csv').open(newline='',encoding='utf-8-sig') as f:r=list(csv.DictReader(f))
   self.assertEqual([(x['plate_id'],x['reading'],x['status']) for x in r],[(x['plate_id'],x['reading'],x['status']) for x in d['plates']])
 def test_observation_ids(self):
  for d in self.ds:
   for p in d['plates']:
    for o in p['observations']:self.assertEqual(o['plate_id'],p['plate_id'])
 def test_raw_ocr(self):
  for d in self.ds:
   with (SITE/'surveys'/d['id']/'web/plate_crops.csv').open(newline='',encoding='utf-8-sig') as f:raw={r['plate_crop']:r['ocr_raw_text'] for r in csv.DictReader(f)}
   for p in d['plates']:
    for o in p['observations']:
     if o['crop']:self.assertEqual(o['raw_ocr'],raw[o['crop'].split('/web/',1)[1]])
 def test_playback_bound(self):
  for d in self.ds:
   for p in d['plates']:self.assertEqual(p['first_photo'],min([int(x) for x in p['photos'].split(';') if x],default=0))
if __name__=='__main__':unittest.main()
