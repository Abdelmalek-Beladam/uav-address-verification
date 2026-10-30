"""Recheck saved pipeline ZIPs on CPU without running YOLO or OCR again."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile
import pandas as pd

repo=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--saved',required=True)
p.add_argument('--out',required=True)
a=p.parse_args()
out=Path(a.out)
if out.exists():
    raise SystemExit('Choose a new output folder; existing folders are preserved.')
out.mkdir(parents=True)
saved=out/'original_saved_run'
with zipfile.ZipFile(a.saved) as z:
    for info in z.infolist():
        dest=(saved/info.filename).resolve()
        if not dest.is_relative_to(saved.resolve()):
            raise SystemExit('Unsafe archive member')
    z.extractall(saved)
roots=[p.parent for p in saved.rglob('detections.csv') if (p.parent/'web'/'data'/'metadata.csv').exists()]
if len(roots)!=1:
    raise SystemExit('Could not uniquely locate the saved run inside the archive')
root=roots[0]
new=out/'updated_run'
shutil.copytree(root,new)
env=os.environ.copy();env['PYTHONPATH']=str(repo/'src')
subprocess.run([sys.executable,'-m','plateverif','verify','--metadata',str(root/'web/data/metadata.csv'),'--addresses',str(repo/'data/adresse_paris.csv'),'--detections',str(root/'detections.csv'),'--config',str(repo/'config/numbers_only.toml'),'--out',str(new/'results')],env=env,check=True)
for f in (new/'results').iterdir():
    if f.is_file():shutil.copy2(f,new/'web/data'/f.name)
for name,key in [('addresses','address_id'),('plates','plate_id')]:
    old=pd.read_csv(root/f'results/{name}.csv')
    latest=pd.read_csv(new/f'results/{name}.csv')
    comparison=old[[key,'status']].merge(latest[[key,'status']],on=key,suffixes=('_before','_after'))
    comparison.to_csv(new/f'{name}_comparison.csv',index=False)
    print('\n'+name.upper(),latest.status.value_counts().to_dict())
    print('Changed statuses:',int((comparison.status_before!=comparison.status_after).sum()))
archive=shutil.make_archive(str(out/'updated_results'),'zip',new)
print('\nSAVED:',archive)
