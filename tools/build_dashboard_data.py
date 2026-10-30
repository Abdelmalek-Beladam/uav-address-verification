"""Convert existing processed surveys to dashboard JSON. No inference performed."""
from pathlib import Path
from collections import defaultdict
import csv,json,argparse
LABELS={'rue_bonaparte':('Rue Bonaparte','Development / demonstration'), 'rue_de_four':('Rue du Four','Training area — not an independent test')}
def rows(p):
 with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def build(site):
 site=Path(site);(site/'data').mkdir(exist_ok=True);catalog=[]
 for folder in sorted((site/'surveys').iterdir()):
  if not (folder/'results/summary.json').is_file():continue
  sid=folder.name
  if not all(c.isalnum() or c in '_-' for c in sid):raise ValueError('Invalid survey ID')
  summary=json.loads((folder/'results/summary.json').read_text());plates=rows(folder/'results/plates.csv');addresses=rows(folder/'results/addresses.csv');photos=rows(folder/'results/photos.csv')
  crops=defaultdict(list)
  for c in rows(folder/'web/plate_crops.csv'):crops[Path(c['image']).name].append(c)
  for g in crops.values():g.sort(key=lambda c:int(c['box']))
  counts=defaultdict(int);byplate=defaultdict(list)
  for d in rows(folder/'results/detections.csv'):
   im=Path(d['image']).name;i=counts[im];counts[im]+=1;c=crops[im][i] if i<len(crops[im]) else {};assert c and int(c['box'])==i, 'Uncertain crop join'
   crop=f"surveys/{sid}/web/"+c.get('plate_crop','');view=f"surveys/{sid}/web/views/{im}"
   byplate[d['plate_id']].append({**d,'raw_ocr':c.get('ocr_raw_text',''),'crop':crop if (site/crop).is_file() else None,'view_url':view if (site/view).is_file() else None})
  for p in plates:
   p['observations']=byplate[p['plate_id']];p['first_photo']=min([int(x) for x in p['photos'].split(';') if x],default=0)
  for p in photos:
   p['views']={side:f"surveys/{sid}/web/views/{int(p['sequence_number']):06}_{side}.jpg" for side in ('left','right') if (folder/'web/views'/f"{int(p['sequence_number']):06}_{side}.jpg").is_file()}
  name,role=LABELS.get(sid,(sid,'Dataset role unconfirmed'))
  d={'id':sid,'name':name,'role':role,'source_mode':'recorded','summary':summary,'plates':plates,'addresses':addresses,'photos':photos,'report_url':f'surveys/{sid}/results/report.html'}
  (site/'data'/f'{sid}.json').write_text(json.dumps(d,ensure_ascii=False),encoding='utf-8');catalog.append({k:d[k] for k in ('id','name','role','summary','report_url','source_mode')})
 (site/'data/catalog.json').write_text(json.dumps(catalog,ensure_ascii=False),encoding='utf-8');from dashboard_evidence import enrich;enrich(site);return catalog
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--site',default='website');a=p.parse_args();print('Built',len(build(a.site)),'recorded surveys')
