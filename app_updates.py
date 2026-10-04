"""Nonblocking five-minute release checks and byte-level update downloads."""
from collections import deque
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import time
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from PySide6.QtCore import QObject, Property, QTimer, Qt, Signal, Slot
from update_package import ARCHIVE_NAME, HIDDEN, MANIFEST_NAME, REPOSITORY, unpack_update, validate_manifest

CHECK_INTERVAL_MS = 5 * 60 * 1000


def request(url, **headers):
    return Request(url, headers={'User-Agent': 'CLIPFARM-updater', 'Accept': 'application/vnd.github+json', **headers})


def asset_url(asset):
    url = asset.get('browser_download_url', '')
    parsed = urlparse(url)
    if parsed.scheme != 'https' or parsed.hostname != 'github.com' or parsed.username or parsed.password:
        raise ValueError('Aktualizacja nie pochodzi z GitHuba.')
    if not parsed.path.startswith(f'/{REPOSITORY}/releases/download/') or parsed.path.rsplit('/', 1)[-1] != asset['name']:
        raise ValueError('Aktualizacja nie pochodzi z repozytorium CLIPFARM.')
    return url


def installed_version(root):
    root = Path(root)
    try:
        return json.loads((root / 'version.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        try:
            value = subprocess.check_output(['git', 'show', '-s', '--format=%H %ct', 'HEAD'], cwd=root,
                                            text=True, stderr=subprocess.DEVNULL, timeout=5, creationflags=HIDDEN).split()
            return {'commit': value[0], 'source_date_epoch': int(value[1])}
        except (OSError, ValueError, subprocess.SubprocessError):
            return {'commit': '', 'source_date_epoch': 0}


def check_for_update(root, etag='', previous=None):
    try:
        headers = {'If-None-Match': etag} if etag else {}
        with urlopen(request(f'https://api.github.com/repos/{REPOSITORY}/releases/latest', **headers), timeout=15) as response:
            release = json.loads(response.read(2 * 1024 * 1024))
            etag = response.headers.get('ETag', '')
    except HTTPError as exc:
        if exc.code == 304:
            return previous, etag
        if exc.code == 404:
            return None, ''
        raise
    if release.get('draft') or release.get('prerelease'):
        return None, etag
    assets = {asset['name']: asset for asset in release.get('assets', [])}
    if MANIFEST_NAME not in assets or ARCHIVE_NAME not in assets:
        return None, etag
    with urlopen(request(asset_url(assets[MANIFEST_NAME])), timeout=15) as response:
        manifest = validate_manifest(json.loads(response.read(2 * 1024 * 1024)))
    if release['tag_name'] != manifest['version'] or assets[ARCHIVE_NAME]['size'] != manifest['size']:
        raise ValueError('Wydanie i paczka mają różne identyfikatory lub rozmiary.')
    local = installed_version(root)
    if manifest['commit'] == local.get('commit') or manifest.get('source_date_epoch', 0) < local.get('source_date_epoch', 0):
        return None, etag
    return {'manifest': manifest, 'url': asset_url(assets[ARCHIVE_NAME])}, etag


def download_update(candidate, stage, progress, cancel):
    manifest = validate_manifest(candidate['manifest'])
    stage = Path(stage)
    stage.mkdir(parents=True, exist_ok=True)
    partial = stage / (ARCHIVE_NAME + '.part')
    total, received = manifest['size'], 0
    samples, last_log = deque(), -math.inf
    progress({'received': 0, 'total': total, 'rate': 0, 'eta': None})
    with urlopen(request(candidate['url']), timeout=30) as response, partial.open('wb') as dest:
        while True:
            if cancel.is_set():
                raise InterruptedError('Pobieranie aktualizacji przerwane.')
            chunk = response.read(64 * 1024)
            if not chunk:
                break
            dest.write(chunk)
            received += len(chunk)
            if received > total:
                raise ValueError('Paczka przekroczyła zapowiedziany rozmiar.')
            now = time.monotonic()
            samples.append((now, received))
            while len(samples) > 2 and samples[1][0] < now - 10:
                samples.popleft()
            elapsed = now - samples[0][0]
            rate = (received - samples[0][1]) / elapsed if elapsed >= .3 else 0
            if now - last_log >= .05 or received == total:
                last_log = now
                progress({'received': received, 'total': total, 'rate': rate,
                          'eta': (total - received) / rate if rate else None})
    if cancel.is_set():
        raise InterruptedError('Pobieranie aktualizacji przerwane.')
    if received != total:
        raise ValueError('Nie pobrano całej paczki aktualizacji. Spróbuj ponownie.')
    archive = stage / ARCHIVE_NAME
    partial.replace(archive)
    (stage / MANIFEST_NAME).write_text(json.dumps(manifest), encoding='utf-8')
    unpack_update(archive, stage, manifest)
    return stage


class Updates(QObject):
    changed = Signal()
    restartRequested = Signal()
    failed = Signal(str)
    _checked = Signal(object)
    _progressed = Signal(object)
    _downloaded = Signal(object)

    def __init__(self, root, parent=None, auto_check=True):
        super().__init__(parent)
        self.root = Path(root)
        self._candidate = None
        self._checking = self._installing = False
        self._progress = 0.0
        self._status = ''
        self.startup_error = ''
        self._etag = ''
        self._closed, self._cancel = threading.Event(), threading.Event()
        self._recovery, self._stage = '', None
        self._checked.connect(self._on_checked, Qt.QueuedConnection)
        self._progressed.connect(self._on_progress, Qt.QueuedConnection)
        self._downloaded.connect(self._on_downloaded, Qt.QueuedConnection)
        self.timer = QTimer(self)
        self.timer.setInterval(CHECK_INTERVAL_MS)
        self.timer.timeout.connect(self.check)
        if auto_check:
            self.timer.start()
            QTimer.singleShot(1000, self.check)
        failure = self.root / '.local/update-error.json'
        if failure.is_file():
            try:
                error = json.loads(failure.read_text(encoding='utf-8'))
                self.startup_error = f'Aktualizacja nie powiodła się: {error["error"]}. Log: {error["log"]}'
                self._status = self.startup_error
                failure.unlink()
            except (OSError, ValueError, KeyError):
                pass

    available = Property(bool, lambda self: self._candidate is not None, notify=changed)
    checking = Property(bool, lambda self: self._checking, notify=changed)
    installing = Property(bool, lambda self: self._installing, notify=changed)
    progress = Property(float, lambda self: self._progress, notify=changed)
    status = Property(str, lambda self: self._status, notify=changed)
    version = Property(str, lambda self: self._candidate['manifest']['version'] if self._candidate else '', notify=changed)

    def emit_if_open(self, signal, value):
        if not self._closed.is_set():
            try:
                signal.emit(value)
            except RuntimeError:
                pass

    @Slot()
    def check(self):
        if self._closed.is_set() or self._checking or self._installing:
            return
        self._checking = True
        self.changed.emit()
        def work():
            try:
                result = check_for_update(self.root, self._etag, self._candidate)
            except Exception as exc:
                result = exc
            self.emit_if_open(self._checked, result)
        threading.Thread(target=work, name='clipfarm-update-check', daemon=True).start()

    @Slot(object)
    def _on_checked(self, result):
        self._checking = False
        if isinstance(result, Exception):
            self._status = 'Nie udało się sprawdzić aktualizacji. Ponowię za 5 minut.'
        else:
            self._candidate, self._etag = result
            self._status = f'Dostępna aktualizacja {self.version}.' if self._candidate else 'Masz aktualną wersję.'
        self.changed.emit()

    def install(self, recovery=''):
        if self._closed.is_set() or self._installing or not self._candidate:
            return
        self._recovery = recovery
        self._installing, self._progress = True, 0
        self._status = 'Łączę się z GitHubem…'
        self._cancel.clear()
        self.changed.emit()
        candidate = self._candidate
        stage = self.root / '.local/updates' / candidate['manifest']['version']
        def work():
            try:
                result = download_update(candidate, stage, lambda data: self.emit_if_open(self._progressed, data), self._cancel)
            except Exception as exc:
                result = exc
            self.emit_if_open(self._downloaded, result)
        threading.Thread(target=work, name='clipfarm-update-download', daemon=True).start()

    @Slot(object)
    def _on_progress(self, data):
        self._progress = data['received'] / data['total']
        pace = f' · {data["rate"] / 1e6:.1f} MB/s' if data['rate'] else ''
        eta = f' · około {max(1, math.ceil(data["eta"]))} s' if data['eta'] else ''
        self._status = f'Pobieram {data["received"] / 1e6:.1f} / {data["total"] / 1e6:.1f} MB{pace}{eta}'
        if self._progress == 1:
            self._status = 'Pobrano paczkę. Sprawdzam pliki…'
        self.changed.emit()

    @Slot(object)
    def _on_downloaded(self, result):
        if isinstance(result, Exception):
            self._installing = False
            self._status = f'Aktualizacja nie została zainstalowana: {result}. Kliknij ikonę, aby ponowić.'
            self.failed.emit(self._status)
        else:
            self._stage, self._progress = result, 1
            self._status = 'Paczka sprawdzona. Instaluję i uruchamiam ponownie…'
            QTimer.singleShot(350, self._launch_installer)
        self.changed.emit()

    def _launch_installer(self):
        if self._closed.is_set() or self._cancel.is_set():
            return
        try:
            installer = self._stage / 'installer'
            installer.mkdir(exist_ok=True)
            for name in ('update_helper.py', 'update_package.py'):
                shutil.copy2(self.root / name, installer / name)
            args = [sys.executable, str(installer / 'update_helper.py'), '--root', str(self.root),
                    '--stage', str(self._stage), '--pid', str(os.getpid()), '--recovery', self._recovery]
            with (self._stage / 'helper.log').open('a', encoding='utf-8') as log:
                subprocess.Popen(args, cwd=self.root, stdin=subprocess.DEVNULL, stdout=log, stderr=log, creationflags=HIDDEN)
        except Exception as exc:
            self._installing = False
            self._status = f'Nie udało się uruchomić instalacji: {exc}. Ponów aktualizację.'
            self.failed.emit(self._status)
            self.changed.emit()
        else:
            self.restartRequested.emit()

    def stop(self):
        self._closed.set()
        self._cancel.set()
        self.timer.stop()
