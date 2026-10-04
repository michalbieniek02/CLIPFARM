"""Release package validation and transactional application-file replacement."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import zipfile

REPOSITORY = 'michalbieniek02/CLIPFARM'
ARCHIVE_NAME = 'clipfarm-windows.zip'
MANIFEST_NAME = 'clipfarm-update.json'
MAX_PACKAGE = 250 * 1024 * 1024
HIDDEN = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0


def file_hash(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def allowed_file(name):
    path = PurePosixPath(name)
    if not name or '\\' in name or ':' in name or path.is_absolute() or path.as_posix() != name:
        return False
    if any(part in ('.', '..') or part.startswith('.') for part in path.parts):
        return False
    if len(path.parts) == 1:
        return path.suffix.lower() in ('.py', '.ps1', '.vbs', '.exe', '.cs') or name in (
            'requirements.txt', 'README.md', 'THIRD_PARTY_NOTICES.md', 'version.json')
    return path.parts[0] in ('assets', 'qml')


def safe_path(root, name):
    if not allowed_file(name):
        raise ValueError(f'Niedozwolony plik aktualizacji: {name}')
    root = Path(root).resolve()
    target = (root / name).resolve()
    if not target.is_relative_to(root):
        raise ValueError('Plik aktualizacji wychodzi poza katalog aplikacji.')
    return target


def validate_manifest(data):
    if data.get('schema') != 1 or data.get('repository') != REPOSITORY or data.get('archive') != ARCHIVE_NAME:
        raise ValueError('Nieprawidłowy manifest aktualizacji CLIPFARM.')
    if not re.fullmatch(r'[a-zA-Z0-9._-]{1,80}', data.get('version', '')) or not re.fullmatch(r'[a-f0-9]{40}', data.get('commit', '')):
        raise ValueError('Nieprawidłowy identyfikator wersji.')
    if not isinstance(data.get('size'), int) or not 0 < data['size'] <= MAX_PACKAGE:
        raise ValueError('Nieprawidłowy rozmiar paczki.')
    if not isinstance(data.get('source_date_epoch'), int) or data['source_date_epoch'] < 0:
        raise ValueError('Nieprawidłowa data wersji.')
    if not re.fullmatch(r'[a-f0-9]{64}', data.get('sha256', '')):
        raise ValueError('Brak sumy kontrolnej paczki.')
    files = data.get('files', {})
    if not isinstance(files, dict) or not 1 <= len(files) <= 2000:
        raise ValueError('Nieprawidłowa lista plików.')
    if len({name.casefold() for name in files}) != len(files):
        raise ValueError('Powtórzone nazwy plików.')
    for name, digest in files.items():
        if not allowed_file(name) or not re.fullmatch(r'[a-f0-9]{64}', digest):
            raise ValueError('Nieprawidłowy plik lub suma kontrolna w manifeście.')
    required = {'app.py', 'qt_app.py', 'update_helper.py', 'update_package.py', 'requirements.txt', 'qml/Main.qml', 'version.json'}
    if not required.issubset(files):
        raise ValueError('Paczka nie zawiera kompletnej aplikacji.')
    return data


def verify_payload(payload, manifest):
    validate_manifest(manifest)
    for name, digest in manifest['files'].items():
        path = safe_path(payload, name)
        if not path.is_file() or file_hash(path) != digest:
            raise ValueError(f'Nieprawidłowa suma kontrolna pliku: {name}')


def unpack_update(archive, stage, manifest):
    validate_manifest(manifest)
    archive = Path(archive)
    if archive.stat().st_size != manifest['size'] or file_hash(archive) != manifest['sha256']:
        raise ValueError('Paczka aktualizacji jest niekompletna lub uszkodzona.')
    payload = Path(stage) / 'payload'
    payload.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as source:
        entries = [entry for entry in source.infolist() if not entry.is_dir()]
        if len(entries) != len(manifest['files']) or {e.filename for e in entries} != set(manifest['files']):
            raise ValueError('Zawartość ZIP nie zgadza się z manifestem.')
        if sum(entry.file_size for entry in entries) > MAX_PACKAGE:
            raise ValueError('Rozpakowana paczka jest zbyt duża.')
        for entry in entries:
            if stat.S_ISLNK(entry.external_attr >> 16):
                raise ValueError('Paczka zawiera dowiązanie symboliczne.')
            target = safe_path(payload, entry.filename)
            target.parent.mkdir(parents=True, exist_ok=True)
            with source.open(entry) as src, target.open('wb') as dest:
                shutil.copyfileobj(src, dest)
    verify_payload(payload, manifest)
    return payload


def install_requirements(python, requirements, log):
    subprocess.run([str(python), '-m', 'pip', 'install', '--disable-pip-version-check', '-r', str(requirements)],
                   check=True, timeout=1800, stdout=log, stderr=log, stdin=subprocess.DEVNULL,
                   creationflags=HIDDEN)


def apply_payload(root, stage, manifest, python, log, installer=install_requirements):
    """Back up only application files; never touch projects, exports, models or secrets."""
    root, stage = Path(root).resolve(), Path(stage).resolve()
    payload = stage / 'payload'
    verify_payload(payload, manifest)
    backup = stage / 'backup'
    backup.mkdir(exist_ok=True)
    old_requirements = file_hash(root / 'requirements.txt') if (root / 'requirements.txt').is_file() else None
    changed = []
    dependencies_changed = old_requirements != manifest['files']['requirements.txt']
    try:
        for name in manifest['files']:
            target = safe_path(root, name)
            saved = safe_path(backup, name)
            existed = target.is_file()
            if existed:
                saved.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, saved)
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_name(target.name + '.update-tmp')
            shutil.copy2(safe_path(payload, name), temporary)
            os.replace(temporary, target)
            changed.append((name, existed))
        if dependencies_changed:
            installer(python, root / 'requirements.txt', log)
        # Compile code before committing the update; compilation executes no application code.
        for name in manifest['files']:
            if name.endswith('.py'):
                compile(safe_path(root, name).read_text(encoding='utf-8-sig'), name, 'exec')
    except Exception:
        for name, existed in reversed(changed):
            target = safe_path(root, name)
            if existed:
                shutil.copy2(safe_path(backup, name), target)
            else:
                target.unlink(missing_ok=True)
        if dependencies_changed and old_requirements:
            try:
                installer(python, root / 'requirements.txt', log)
            except Exception as exc:
                print(f'Nie udało się przywrócić bibliotek: {exc}', file=log)
        raise
    (stage / 'installed.json').write_text(json.dumps({'version': manifest['version'], 'commit': manifest['commit']}), encoding='utf-8')
