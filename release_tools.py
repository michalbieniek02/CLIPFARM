"""Create a small Windows application update from source; exclude all user data."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import zipfile

from update_package import ARCHIVE_NAME, MANIFEST_NAME, REPOSITORY, allowed_file, file_hash, validate_manifest


def build_release(root, destination, version, commit, source_date_epoch):
    root, destination = Path(root).resolve(), Path(destination).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    paths = [p for p in root.iterdir() if p.is_file() and allowed_file(p.name) and p.name != 'version.json']
    for folder in ('assets', 'qml'):
        paths += [p for p in (root / folder).rglob('*') if p.is_file()]
    files = {}
    metadata = {'schema': 1, 'version': version, 'commit': commit, 'source_date_epoch': source_date_epoch,
                'built_at': datetime.now(timezone.utc).isoformat(), 'repository': REPOSITORY}
    version_file = destination / 'version.json'
    version_file.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
    paths.append(version_file)
    archive = destination / ARCHIVE_NAME
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as bundle:
        for path in sorted(paths):
            if path == version_file:
                name = 'version.json'
            else:
                if not path.resolve().is_relative_to(root) or path.is_symlink():
                    raise ValueError('Plik wydania wychodzi poza projekt.')
                name = path.relative_to(root).as_posix()
            if not allowed_file(name):
                raise ValueError(f'Niedozwolony plik wydania: {name}')
            files[name] = file_hash(path)
            bundle.write(path, name)
    manifest = {**metadata, 'archive': ARCHIVE_NAME, 'size': archive.stat().st_size,
                'sha256': file_hash(archive), 'files': files}
    validate_manifest(manifest)
    (destination / MANIFEST_NAME).write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', required=True)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--output', default='dist')
    args = parser.parse_args()
    epoch = int(subprocess.check_output(['git', 'show', '-s', '--format=%ct', args.commit], text=True).strip())
    result = build_release(Path(__file__).resolve().parent, args.output, args.version, args.commit, epoch)
    print(f'Built {result["version"]}: {len(result["files"])} application files, {result["size"] / 1e6:.1f} MB')
