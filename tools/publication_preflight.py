"""Fail closed on missing sequence-specific credits. Does not confer legal approval."""
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
def check(root):
    manifest=json.loads((root/'website/data/imagery-credits.json').read_text())
    errors=[]
    for route in manifest['routes']:
        missing=[k for k in ('producer','license','credit','metadata_url') if not route.get(k)]
        if route.get('verification_status')!='source_metadata_verified' or missing:
            errors.append(route['dataset_id']+': source attribution/licence evidence unresolved')
    for path in root.rglob('*'):
        if not path.is_file(): continue
        rel=path.relative_to(root)
        if '.git' in rel.parts: continue
        if any(x in rel.parts for x in ['.venv','venv','node_modules','private-handoff']) or path.name.startswith('.env') or path.suffix.lower() in {'.pt','.onnx','.zip'}:
            errors.append(str(rel)+': private or binary payload in publication tree')
    return errors
if __name__=='__main__':
    failures=check(ROOT)
    for item in failures: print('BLOCKED:',item)
    print('Publication preflight:', 'BLOCKED' if failures else 'machine checks passed; maintainers must still approve rights/privacy/licensing')
    sys.exit(bool(failures))
