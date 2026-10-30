import unittest,importlib.util,tempfile,json,hashlib,zipfile
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1]
def load(name):
 spec=importlib.util.spec_from_file_location(name,ROOT/'tools'/(name+'.py'))
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
class HandoffContractTests(unittest.TestCase):
 def test_all_protected_hashes(self):
  errors,total=load('check_handoff').check(ROOT);self.assertFalse(errors);self.assertGreater(total,1000)
 def test_tampered_file_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'evidence.txt').write_text('changed');(root/'release_integrity.json').write_text(json.dumps({'files':{'evidence.txt':hashlib.sha256(b'original').hexdigest()}}))
   errors,_=load('check_handoff').check(root);self.assertEqual(len(errors),1)
 def test_roles_separate_from_tools(self):
  roles=(ROOT/'submission/TEAM_ROLES.md').read_text()
  for term in ['ChatGPT','Claude','Gemini','Notion AI','AI-assisted']:self.assertNotIn(term,roles)
  self.assertIn('ChatGPT',(ROOT/'submission/TOOLS_AND_PRIOR_WORK.md').read_text())
 def test_current_future_scope(self):
  page=(ROOT/'website/index.html').read_text();self.assertIn('UAV acquisition is planned',page);self.assertIn('Flight control, aerial capture and onboard processing are not implemented',page);self.assertIn('Playback shows saved results, not fresh inference',page);self.assertNotIn('MAV',page)
 def test_windows_pythonpath_separator(self):
  m=load('run_street')
  with patch.dict(m.os.environ,{'PYTHONPATH':'previous'}),patch.object(m.os,'pathsep',';'),patch.object(m.subprocess,'run',return_value=SimpleNamespace(stdout='',stderr='',returncode=0)) as run:
   m.verify(Path('/tmp/metadata'),Path('/tmp/addresses'),Path('/tmp/output'),Path('/tmp/config'))
   self.assertEqual(run.call_args.kwargs['env']['PYTHONPATH'],str(m.REPO/'src')+';previous')
 def test_unsafe_archive_rejected_before_extraction(self):
  m=load('run_street')
  for member in ['../escape.txt','C:/escape.txt','/absolute.txt']:
   with self.subTest(member=member),tempfile.TemporaryDirectory() as d:
    root=Path(d);zpath=root/'street.zip'
    with zipfile.ZipFile(zpath,'w') as z:z.writestr('metadata.csv','sequence_number\n1\n');z.writestr(member,'unsafe')
    with self.assertRaises(SystemExit):m.extract(zpath,root/'work')
    self.assertFalse((root/'escape.txt').exists());self.assertFalse((root/'work/metadata.csv').exists())
 def test_safe_archive_extracts(self):
  m=load('run_street')
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);zpath=root/'street.zip'
   with zipfile.ZipFile(zpath,'w') as z:z.writestr('survey/metadata.csv','sequence_number\n1\n')
   self.assertEqual(m.extract(zpath,root/'work'),root/'work/survey')
