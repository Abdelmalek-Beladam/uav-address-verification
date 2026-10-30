"""Collect existing project artifacts in Colab. No training, inference or package installs.
Only the known project model directory and named adjacent training files are read.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import platform
import sys
import zipfile


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def collect(drive_root=Path('/content/drive/MyDrive')):
    model = drive_root / 'yolo_runs/amira_model/best.pt'
    if not model.is_file():
        raise FileNotFoundError(
            'The existing checkpoint was not found at ' + str(model)
            + '. Stop here. Do not retrain or download another model. '
            + 'Send the exact current checkpoint path instead.'
        )
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')
    output_dir = drive_root / 'yolo_runs/submission_artifacts'
    output_dir.mkdir(parents=True, exist_ok=True)
    archive = output_dir / ('existing_project_artifacts_' + stamp + '.zip')
    # Restrict collection to the known checkpoint directory. No personal-notebook scan.
    roots = [model.parent]
    if model.parent.name == 'weights':
        roots.append(model.parent.parent)
    allowed = [
        'args.yaml', 'results.csv', 'results.png',
        'confusion_matrix.png', 'confusion_matrix_normalized.png',
        'PR_curve.png', 'P_curve.png', 'R_curve.png', 'F1_curve.png',
        'BoxPR_curve.png', 'BoxP_curve.png', 'BoxR_curve.png', 'BoxF1_curve.png',
        'data.yaml', 'dataset.yaml', 'training_config.yaml',
    ]
    files = [(model, 'model/best.pt')]
    found_names = set()
    for index, root in enumerate(roots):
        for name in allowed:
            path = root / name
            if path.is_file():
                files.append((path, 'existing_run_' + str(index) + '/' + name))
                found_names.add(name)
    versions = {}
    for package in ['ultralytics', 'torch', 'torchvision', 'paddleocr',
                    'paddlepaddle', 'paddlepaddle-gpu', 'opencv-python',
                    'opencv-python-headless', 'numpy', 'pandas', 'Pillow', 'PyYAML']:
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = 'not installed in the current runtime'
    manifest = {
        'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'collection_scope': 'Existing checkpoint and explicitly named adjacent project training artifacts only',
        'training_or_inference_performed': False,
        'environment_note': 'Versions describe the collection runtime only. They are NOT proof of the original training or OCR environment.',
        'python': sys.version,
        'platform': platform.platform(),
        'package_versions_current_runtime': versions,
        'files': [{'archive_path': name, 'size_bytes': path.stat().st_size,
                   'sha256': sha256(path)} for path, name in files],
        'not_collected': [
            'Original training notebook: download its .ipynb separately.',
            'Current pipeline notebook: download its .ipynb separately.',
            'Dataset split identifiers/provenance if not in adjacent configs.',
            'Exact imagery contributor/licence and team-role confirmations.',
        ],
        'adjacent_training_files_found': sorted(found_names),
    }
    if archive.exists():
        raise FileExistsError('Refusing to overwrite ' + str(archive))
    with zipfile.ZipFile(archive, 'x', zipfile.ZIP_DEFLATED) as bundle:
        for path, name in files:
            bundle.write(path, name)
        bundle.writestr('MANIFEST.json', json.dumps(manifest, indent=2))
        bundle.writestr('READ_ME.txt',
            'This bundle collects existing project files. No model was trained or run.\n'
            'Review args/data YAML files for private paths or links before sharing.\n'
            'The captured package versions describe this runtime, not necessarily training.\n'
            'Please also provide the original training notebook and current pipeline notebook as .ipynb.\n')
    print('Collected existing checkpoint; no training or OCR was run.')
    print('Checkpoint SHA-256:', manifest['files'][0]['sha256'])
    print('Adjacent training files found:', ', '.join(sorted(found_names)) or 'none; not fabricated')
    print('Saved ZIP:', archive)
    return archive


def main():
    from google.colab import drive, files
    root = Path('/content/drive/MyDrive')
    if not root.exists():
        drive.mount('/content/drive')
    archive = collect(root)
    files.download(str(archive))


if __name__ == '__main__':
    main()
