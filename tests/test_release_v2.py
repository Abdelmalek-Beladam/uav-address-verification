import unittest,json
from pathlib import Path
from plateverif.ocr_safety import numeric_reading
class ReleaseTests(unittest.TestCase):
 def test_safe_digits(self):
  for raw,out in [('17','17'),('11','11'),('001','1'),('12 bis','12'),('17 A','17')]:self.assertEqual(numeric_reading(raw),out)
 def test_ambiguous_abstention(self):
  for raw in ['2I','I7','II','1o6','T3','0','000','2200','1 7','12/14','shop 17']:self.assertEqual(numeric_reading(raw),'')
 def test_coverage_separated(self):
  for f in (Path(__file__).resolve().parents[1]/'website/data').glob('rue_*.json'):
   for a in json.loads(f.read_text())['addresses']:self.assertIn('supporting_photo_count',a)
 def test_uncertain_explanations(self):
  for f in (Path(__file__).resolve().parents[1]/'website/data').glob('rue_*.json'):
   for p in json.loads(f.read_text())['plates']:
    if p['status']=='UNCERTAIN':self.assertNotIn('There is no official address at this spot',p['explanation'])
