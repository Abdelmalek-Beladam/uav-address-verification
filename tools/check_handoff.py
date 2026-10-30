"""Verify protected release files without loading model weights or importing ML packages."""
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1]
def check(root):
 manifest=json.loads((root/'release_integrity.json').read_text())
 failures=[]
 for rel,expected in manifest['files'].items():
  p=(root/rel).resolve()
  if not p.is_relative_to(root.resolve()) or not p.is_file():failures.append(rel+': missing or unsafe');continue
  h=hashlib.sha256()
  with p.open('rb') as f:
   for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
  if h.hexdigest()!=expected:failures.append(rel+': checksum differs')
 return failures,len(manifest['files'])
if __name__=='__main__':
 failures,total=check(ROOT)
 print('Protected files checked:',total)
 print('Artifact integrity:', 'PASS' if not failures else 'FAIL')
 for failure in failures:print(failure)
 print('This checks saved-file identity, not model accuracy or fresh inference compatibility.')
 sys.exit(bool(failures))
