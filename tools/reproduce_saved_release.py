"""Reproduce the saved demo from preserved detector rows on CPU, without model inference.
Creates a NEW output directory. Never changes the source project or original results.
Example: python tools/reproduce_saved_release.py --out C:\\AddressObservatory-reproduction
"""
import argparse
from collections import defaultdict
import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'src'))
from plateverif.ocr_safety import numeric_reading


def read_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def safe_rows(det, manifest):
    crops = defaultdict(list)
    for crop in manifest:
        crops[Path(crop['image']).name].append(crop)
    for group in crops.values():
        group.sort(key=lambda crop: int(crop['box']))
    counts = defaultdict(int)
    changes = []
    for row in det:
        image = Path(row['image']).name
        ordinal = counts[image]
        counts[image] += 1
        if ordinal >= len(crops[image]) or int(crops[image][ordinal]['box']) != ordinal:
            raise ValueError('Cannot establish original crop order for ' + image)
        raw = crops[image][ordinal]['ocr_raw_text']
        if str(row['text']).strip() not in ('', '?', 'nan') and not numeric_reading(raw):
            changes.append({'image': row['image'], 'box': ordinal,
                            'raw_ocr': raw, 'before': row['text'], 'after': '?'})
            row['text'] = '?'
            row['ocr_conf'] = '0.0'
    if any(counts[image] != len(group) for image, group in crops.items()):
        raise ValueError('Detection/crop manifest counts differ')
    return det, changes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    out = Path(args.out).resolve()
    if out.exists():
        raise SystemExit('Choose a new output folder. Existing output is never overwritten.')
    if out == REPO or REPO in out.parents or out in REPO.parents:
        raise SystemExit('Output must be outside the source repository.')
    catalog = json.loads((REPO / 'website/data/catalog.json').read_text())
    out.mkdir(parents=True)
    target = out / 'website'
    shutil.copytree(REPO / 'website', target)
    env = os.environ.copy()
    env['PYTHONPATH'] = str(REPO / 'src')
    report = {
        'inference_or_training_run': False,
        'note': 'Reverification from saved detector/OCR artifacts, not a fresh model run.',
        'addresses_sha256': sha256(REPO / 'data/adresse_paris.csv'),
        'config_sha256': sha256(REPO / 'config/numbers_only.toml'),
        'surveys': [],
    }
    all_equal = True
    for entry in catalog:
        sid = entry['id']
        if not all(c.isalnum() or c in '_-' for c in sid):
            raise SystemExit('Unsafe survey identifier')
        original = REPO / 'archive/baseline_v1' / sid / 'detections.csv'
        if not original.is_file():
            original = REPO / 'website/surveys' / sid / 'detections.csv'
        folder = target / 'surveys' / sid
        det, changes = safe_rows(read_csv(original), read_csv(folder / 'web/plate_crops.csv'))
        with (folder / 'detections.csv').open('w', encoding='utf-8-sig', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(det[0]))
            writer.writeheader()
            writer.writerows(det)
        generated = folder / 'reproduction_results'
        subprocess.run([
            sys.executable, '-m', 'plateverif', 'verify',
            '--metadata', str(folder / 'web/data/metadata.csv'),
            '--addresses', str(REPO / 'data/adresse_paris.csv'),
            '--detections', str(folder / 'detections.csv'),
            '--config', str(REPO / 'config/numbers_only.toml'),
            '--out', str(generated),
        ], env=env, check=True)
        comparisons = {}
        for name in ['addresses.csv', 'plates.csv', 'detections.csv', 'photos.csv', 'expected_views.csv']:
            comparisons[name] = read_csv(generated / name) == read_csv(REPO / 'website/surveys' / sid / 'results' / name)
        equal = all(comparisons.values())
        all_equal = all_equal and equal
        report['surveys'].append({
            'id': sid, 'original_detections_sha256': sha256(original),
            'safety_abstentions': changes, 'csv_rows_equal_to_shipped_release': comparisons,
            'all_compared_csv_rows_equal': equal,
        })
        # This deletion is confined to the NEW copied output, never the source project.
        shutil.rmtree(folder / 'results')
        generated.rename(folder / 'results')
        for path in (folder / 'results').iterdir():
            if path.is_file():
                shutil.copy2(path, folder / 'web/data' / path.name)
    subprocess.run([sys.executable, str(REPO / 'tools/build_dashboard_data.py'),
                    '--site', str(target)], check=True)
    report['all_compared_csv_rows_equal'] = all_equal
    report['timestamp_note'] = 'Summary/report generation timestamps may differ and are not compared as result rows.'
    (out / 'reproduction_report.json').write_text(json.dumps(report, indent=2))
    print('Reproduction report:', out / 'reproduction_report.json')
    print('All compared CSV rows equal:', all_equal)
    if not all_equal:
        raise SystemExit('Reproduction differs. Inspect the report; do not silently accept new results.')


if __name__ == '__main__':
    main()
