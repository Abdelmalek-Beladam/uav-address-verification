from pathlib import Path
import json,sys
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'src'))
from plateverif.ocr_safety import numeric_reading
def enrich(site):
 for file in (Path(site)/'data').glob('rue_*.json'):
  d=json.loads(file.read_text());byid={p['plate_id']:p for p in d['plates']}
  for p in d['plates']:
   for o in p['observations']:o['ocr_needs_review']=bool(o['raw_ocr'] and not numeric_reading(o['raw_ocr']) and any(c.isalpha() for c in o['raw_ocr']))
   p['candidate_address']=p['expected_address'] or p['official_address_of_reading'];p['candidate_distance_m']=p['match_distance_m'] if p['address_id'] else p['official_distance_m']
   p['recognition_state']='Recorded number' if p['reading'] else ('Ambiguous OCR' if any(o['ocr_needs_review'] for o in p['observations']) else 'No reliable reading')
   p['recognition_note']='Grouped OCR, not a human-validated transcription.'
   if any(o['ocr_needs_review'] for o in p['observations']):p['recognition_note']='Ambiguous raw letters were not silently truncated or converted. I means capital I, not digit 1.'
   p['registry_state']='Number agrees' if p['status']=='CORRECT' else ('Candidate requires review' if p['candidate_address'] else 'No candidate identified')
   p['location_state']='Rule-based association' if p['address_id'] else 'Position unresolved'
   notes=[]
   if p['located_by']=='assumed distance':notes.append('Plate depth is assumed, not measured. Camera GPS alone does not locate a facade plate.')
   elif p['located_by']=='single sight line':notes.append('Single-view position uses the register as a constraint, not an independent range measurement.')
   else:notes.append('Multi-view sight-line fit residual is not absolute GPS accuracy.')
   if not p['address_id'] and p['reading']:
    limit=d['summary']['config']['matching']['max_match_distance_m']
    if p['official_distance_m'] and float(p['official_distance_m'])>limit:notes.append(f'Number candidate lies outside the primary {limit:g} m tolerance. Fallbacks require strong multi-view evidence and reject nearby multiple streets.')
    if int(p['n_photos'])<2:notes.append('One photo cannot satisfy multi-view fallback requirements.')
    notes.append('A matching register number alone does not prove correct physical placement.')
   p['decision_notes']=notes
  for a in d['addresses']:
   linked=[byid[k] for k in a['plates'].split(';') if k in byid];a['supporting_photo_count']=len({o['sequence_number'] for p in linked for o in p['observations']})
  file.write_text(json.dumps(d,ensure_ascii=False))
