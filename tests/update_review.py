"""Real release ZIP, byte streaming, integrity, data preservation and rollback."""
from io import BytesIO
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
from urllib.error import HTTPError
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app_updates import asset_url, check_for_update, download_update
from release_tools import build_release
from update_package import ARCHIVE_NAME, MANIFEST_NAME, REPOSITORY, allowed_file, apply_payload, file_hash, unpack_update, validate_manifest

ROOT = Path(__file__).resolve().parents[1]
(ROOT / 'checks').mkdir(exist_ok=True)

for name in ('../projects/a', 'C:/Windows/a.py', '.git/config', '.env', 'runtime/a.py', 'projects/a.py', 'qml/../../a.py', 'qml\\a.py'):
    assert not allowed_file(name), name
try:
    asset_url({'name': ARCHIVE_NAME, 'browser_download_url': 'https://example.com/' + ARCHIVE_NAME})
except ValueError:
    pass
else:
    raise AssertionError('Only this GitHub repository may supply releases')

class Response(BytesIO):
    headers = {'ETag': 'release-test'}

class SlowResponse(Response):
    def read(self, size=-1):
        time.sleep(.015)
        return super().read(size)

with tempfile.TemporaryDirectory(dir=ROOT / 'checks') as temp:
    work = Path(temp)
    manifest = build_release(ROOT, work / 'dist', 'build-test', '1' * 40, 1)
    archive = work / 'dist' / ARCHIVE_NAME
    assert not any(name.startswith(('.local', 'models', 'projects', 'exports', 'runtime')) for name in manifest['files'])
    candidate = {'manifest': manifest, 'url': f'https://github.com/{REPOSITORY}/releases/download/build-test/{ARCHIVE_NAME}'}
    updates = []
    with patch('app_updates.urlopen', return_value=SlowResponse(archive.read_bytes())):
        stage = download_update(candidate, work / 'stage', updates.append, threading.Event())
    assert len(updates) >= 3 and updates[0]['received'] == 0
    assert updates[-1]['received'] == manifest['size']
    assert any(0 < p['received'] < p['total'] for p in updates)
    assert sorted(p['received'] for p in updates) == [p['received'] for p in updates]

    install = work / 'app'
    install.mkdir()
    (install / 'app.py').write_text('# previous version', encoding='utf-8')
    (install / 'requirements.txt').write_bytes((ROOT / 'requirements.txt').read_bytes())
    protected = ['projects/a.json', 'exports/a.mp4', 'models/a.bin', '.env', '.local/secret.txt']
    for name in protected:
        path = install / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'user data, never replace')
    with (work / 'install.log').open('w') as log:
        apply_payload(install, stage, manifest, sys.executable, log,
                      installer=lambda *args: (_ for _ in ()).throw(AssertionError('Unchanged dependencies must not be installed')))
    assert file_hash(install / 'app.py') == manifest['files']['app.py']
    assert json.loads((install / 'version.json').read_text())['commit'] == '1' * 40
    assert all((install / name).read_bytes() == b'user data, never replace' for name in protected)

    rollback = work / 'rollback'
    rollback.mkdir()
    (rollback / 'app.py').write_text('# keep this previous app', encoding='utf-8')
    (rollback / 'requirements.txt').write_text('# previous requirements', encoding='utf-8')
    (rollback / 'projects').mkdir()
    (rollback / 'projects/a.json').write_text('keep the project')
    attempts = []
    def broken_install(python, requirements, log):
        attempts.append(requirements.read_text())
        if len(attempts) == 1:
            raise RuntimeError('Simulated interrupted dependency installation')
    with (work / 'rollback.log').open('w') as log:
        try:
            apply_payload(rollback, stage, manifest, sys.executable, log, installer=broken_install)
        except RuntimeError:
            pass
        else:
            raise AssertionError('Dependency failure must roll back application files')
    assert (rollback / 'app.py').read_text() == '# keep this previous app'
    assert (rollback / 'requirements.txt').read_text() == '# previous requirements'
    assert (rollback / 'projects/a.json').read_text() == 'keep the project'
    assert not (rollback / 'version.json').exists() and len(attempts) == 2

    corrupted = work / 'corrupt.zip'
    corrupted.write_bytes(archive.read_bytes()[:-20])
    try:
        unpack_update(corrupted, work / 'bad-stage', manifest)
    except ValueError:
        pass
    else:
        raise AssertionError('Truncated release must never be installed')
    bad_manifest = {**manifest, 'files': {**manifest['files'], '../projects/a': '0' * 64}}
    try:
        validate_manifest(bad_manifest)
    except ValueError:
        pass
    else:
        raise AssertionError('Path traversal in a release must be rejected')

    release = {'tag_name': 'build-test', 'assets': [
        {'name': name, 'size': manifest['size'] if name == ARCHIVE_NAME else 1,
         'browser_download_url': f'https://github.com/{REPOSITORY}/releases/download/build-test/{name}'}
        for name in (ARCHIVE_NAME, MANIFEST_NAME)]}
    def responses():
        return [Response(json.dumps(release).encode()), Response(json.dumps(manifest).encode())]
    with patch('app_updates.urlopen', side_effect=responses()), patch('app_updates.installed_version', return_value={'commit': '0' * 40, 'source_date_epoch': 0}):
        found, etag = check_for_update(install)
        assert found['manifest']['commit'] == manifest['commit'] and etag == 'release-test'
    for local in ({'commit': manifest['commit'], 'source_date_epoch': 1}, {'commit': '2' * 40, 'source_date_epoch': 2}):
        with patch('app_updates.urlopen', side_effect=responses()), patch('app_updates.installed_version', return_value=local):
            assert check_for_update(install)[0] is None, 'Same or older releases must not be offered'
    with patch('app_updates.urlopen', side_effect=HTTPError('https://api.github.com', 304, 'unchanged', {}, None)):
        assert check_for_update(install, etag, found) == (found, etag)
print('PASS: verified ZIP, live byte progress, cached release checks, no downgrade, protected user data, corrupt/traversal rejection and dependency rollback.')
