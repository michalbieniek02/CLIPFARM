"""Qt bridge; all media/AI processing stays in the existing Python modules."""
import copy
import ctypes
import hashlib
import json
import math
import os
from pathlib import Path
import re
import traceback

from PySide6.QtCore import QAbstractListModel, QModelIndex, QObject, Property, QThread, QTimer, QUrl, Qt, Signal, Slot
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFileDialog

from engine import Cancelled, Pipeline, ROOT, minute_clips, subtitle_text, validate_clips, validate_options
from captions import FONT_SIZE
from font_catalog import FONT_NAMES, resolve_font
from video_layout import SETTING_RANGES, number, frame_layout
from framing import FRAMING_LABELS, FRAMING_HELP
from transcripts import existing_transcript, read_transcript, remember_transcript, validate_segments
from ui_media import thumbnail
from vod_download import PROVIDERS, QUALITIES


def local_path(value):
    url = value if isinstance(value, QUrl) else QUrl(str(value))
    return Path(url.toLocalFile() if url.isLocalFile() else str(value)).resolve()


def thumbnail_url(source, work, seconds=0):
    key = hashlib.sha256(f'{source}:{Path(source).stat().st_mtime_ns}:{seconds}'.encode()).hexdigest()[:20]
    path = Path(work) / 'thumbnails' / f'{key}.png'
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        if not path.exists():
            thumbnail(source, seconds, (400, 225)).save(path)
        return QUrl.fromLocalFile(str(path)).toString()
    except (OSError, ValueError):
        return ''


class ClipModel(QAbstractListModel):
    DataRole = Qt.UserRole + 1

    def __init__(self, parent=None):
        super().__init__(parent)
        self.rows = []

    def roleNames(self):
        return {self.DataRole: b'clipData'}

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.rows)

    def data(self, index, role=Qt.DisplayRole):
        if index.isValid() and role == self.DataRole and 0 <= index.row() < len(self.rows):
            return self.rows[index.row()]

    def replace(self, rows):
        self.beginResetModel()
        self.rows = rows
        self.endResetModel()

    def update(self, index, values):
        self.rows[index] = {**self.rows[index], **values}
        item = self.index(index, 0)
        self.dataChanged.emit(item, item, [self.DataRole])

    def remove(self, index):
        self.beginRemoveRows(QModelIndex(), index, index)
        del self.rows[index]
        self.endRemoveRows()


class Job(QThread):
    log = Signal(str)

    def __init__(self, operation, parent=None):
        super().__init__(parent)
        self.pipeline = Pipeline(self.log.emit)
        self.operation = operation
        self.result = None
        self.error = ''
        self.cancelled = False

    def run(self):
        try:
            self.result = self.operation(self.pipeline)
        except Cancelled:
            self.cancelled = True
        except Exception:
            self.error = traceback.format_exc()


class Backend(QObject):
    stateChanged = Signal()
    clipsChanged = Signal()
    settingsChanged = Signal()
    logsChanged = Signal()
    previewChanged = Signal()
    animationsChanged = Signal()
    errorOccurred = Signal(str)
    previewReady = Signal()
    shutdownReady = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.model = ClipModel(self)
        self.source = None
        self.metadata = {}
        self.segments = []
        self.work = None
        self.destination = ROOT / 'exports'
        self.origin = ''
        self._status = 'Wszystko gotowe. Dodaj swój pierwszy film.'
        self._progress = 0.0
        self._error = ''
        self._logs = ''
        self._downloadInfo = ''
        self._downloadActive = False
        self._preview = ''
        self._thumb = ''
        self._job = None
        self._complete = None
        self._closing = False
        self.updates = None
        self._settings = {'minimum': '20', 'maximum': '30', 'format': 'Pionowy 9:16',
            'framing': 'Cały obraz · czarne pasy', 'burn': True, 'mode': 'AI klipy',
            'light_color': False, 'speed_up': False, 'mirror': False,
            'caption_font': 'Anton', 'caption_size': float(FONT_SIZE),
            'caption_custom': False, 'caption_x': .5, 'caption_y': .84375,
            'fit_zoom': 1.0, 'fit_x': .5, 'fit_y': .5,
            'brief': 'Mocny początek, ciekawa myśl lub zabawny moment. Pełna puenta i naturalne zakończenie.',
            'whisper': 'Zrównoważona'}
        self._animations = self.system_animations()
        self._motion_timer = QTimer(self)
        self._motion_timer.timeout.connect(self.refreshAnimations)
        self._motion_timer.start(3000)

    @staticmethod
    def system_animations():
        if os.environ.get('CLIPFARM_REDUCED_MOTION') == '1':
            return False
        if os.name == 'nt':
            enabled = ctypes.c_int(1)
            # SPI_GETCLIENTAREAANIMATION honours Windows accessibility settings.
            if ctypes.windll.user32.SystemParametersInfoW(0x1042, 0, ctypes.byref(enabled), 0):
                return bool(enabled.value)
        return True

    @Slot()
    def refreshAnimations(self):
        value = self.system_animations()
        if self._animations != value:
            self._animations = value
            self.animationsChanged.emit()

    busy = Property(bool, lambda self: self._job is not None, notify=stateChanged)
    status = Property(str, lambda self: self._status, notify=stateChanged)
    progress = Property(float, lambda self: self._progress, notify=stateChanged)
    downloadInfo = Property(str, lambda self: self._downloadInfo, notify=stateChanged)
    errorMessage = Property(str, lambda self: self._error, notify=stateChanged)
    videoPath = Property(str, lambda self: str(self.source or ''), notify=stateChanged)
    videoName = Property(str, lambda self: self.source.name if self.source else '', notify=stateChanged)
    videoThumbnail = Property(str, lambda self: self._thumb, notify=stateChanged)
    videoInfo = Property(str, lambda self: (f"{int(self.metadata.get('duration', 0)) // 60}:{int(self.metadata.get('duration', 0)) % 60:02d}  ·  {self.metadata.get('width', 0)} × {self.metadata.get('height', 0)}" if self.source else 'MP4, MKV, MOV, AVI, WEBM, M4V'), notify=stateChanged)
    transcriptReady = Property(bool, lambda self: bool(self.segments), notify=stateChanged)
    transcriptStatus = Property(str, lambda self: f'Transkrypcja: gotowa · {len(self.segments)} segmentów' if self.segments else 'Transkrypcja: brak', notify=stateChanged)
    settings = Property('QVariantMap', lambda self: self._settings, notify=settingsChanged)
    clipModel = Property(QObject, lambda self: self.model, constant=True)
    clips = Property('QVariantList', lambda self: self.model.rows, notify=clipsChanged)
    clipCount = Property(int, lambda self: len(self.model.rows), notify=clipsChanged)
    selectedCount = Property(int, lambda self: sum(r.get('selected', True) for r in self.model.rows), notify=clipsChanged)
    logs = Property(str, lambda self: self._logs, notify=logsChanged)
    previewUrl = Property(str, lambda self: self._preview, notify=previewChanged)
    animationsEnabled = Property(bool, lambda self: self._animations, notify=animationsChanged)
    framingLabels = Property('QStringList', lambda self: list(FRAMING_LABELS), constant=True)
    framingHelp = Property(str, lambda self: FRAMING_HELP.get(FRAMING_LABELS.get(self._settings['framing']), '') if self._settings['format'] == 'Pionowy 9:16' else 'Zachowamy oryginalne proporcje całego filmu.', notify=settingsChanged)
    downloadProviders = Property('QStringList', lambda self: list(PROVIDERS), constant=True)
    downloadQualities = Property('QStringList', lambda self: list(QUALITIES), constant=True)
    captionSize = Property(float, lambda self: self._settings['caption_size'], notify=settingsChanged)
    captionFont = Property(str, lambda self: self._settings['caption_font'], notify=settingsChanged)
    fontChoices = Property('QStringList', lambda self: list(FONT_NAMES), constant=True)
    captionRows = Property('QVariantList', lambda self: [
        {'start': row['start'], 'end': row['end'], 'text': row['text']} for row in self.segments], notify=stateChanged)
    previewLayout = Property('QVariantMap', lambda self: frame_layout(
        1672, 941, self._settings['format'] == 'Pionowy 9:16', self._settings['framing'] == 'Cały obraz · czarne pasy',
        self._settings['fit_zoom'], self._settings['fit_x'], self._settings['fit_y'],
        (self._settings['caption_x'], self._settings['caption_y']) if self._settings['caption_custom'] else None,
        self._settings['burn']), notify=settingsChanged)

    @Slot(str, 'QVariant')
    def setSetting(self, name, value):
        if self.busy or name not in self._settings:
            return
        if name in SETTING_RANGES:
            try:
                value = number(value, *SETTING_RANGES[name])
            except (TypeError, ValueError):
                return
        elif name == 'caption_font':
            value = resolve_font(value)
        elif isinstance(self._settings[name], bool):
            value = bool(value)
        elif not isinstance(value, str):
            value = str(value)
        if value == self._settings[name]:
            return
        self._settings = {**self._settings, name: value}
        self.settingsChanged.emit()

    @Slot(int, str, result=bool)
    def editCaption(self, index, text):
        if self.busy or not 0 <= index < len(self.segments):
            return False
        text = text.strip()
        if not text or len(text) > 4000:
            self.reportError('Napis nie może być pusty ani dłuższy niż 4000 znaków.')
            return False
        rows = copy.deepcopy(self.segments)
        row, tokens = rows[index], text.split()
        if text == row['text']:
            return True
        old_words = row.get('words', [])
        adjusted = len(old_words) != len(tokens)
        if not adjusted:
            row['words'] = [{**word, 'text': token} for word, token in zip(old_words, tokens)]
        else:
            left = old_words[0]['start'] if old_words else row['start']
            right = old_words[-1]['end'] if old_words else row['end']
            total, cursor, words = sum(len(token) for token in tokens), left, []
            for position, token in enumerate(tokens):
                finish = right if position == len(tokens) - 1 else cursor + (right - left) * len(token) / total
                words.append({'start': cursor, 'end': min(right, finish), 'text': token})
                cursor = finish
            row['words'] = words
        row['text'] = text
        try:
            if self.source and self.work:
                remember_transcript(self.source, self.work, rows)
        except OSError as exc:
            self.reportError(str(exc))
            return False
        self.segments = rows
        self.closePreview()
        self._status = 'Napis zapisany.' + (' Po dodaniu lub usunięciu słów sprawdź synchronizację w podglądzie.' if adjusted else '')
        self.stateChanged.emit()
        return True

    @Slot(str)
    def reportError(self, text):
        self._error = text
        self.appendLog(text)
        self._status = 'Zadanie nie powiodło się. Otwórz Szczegóły.'
        self.stateChanged.emit()
        self.errorOccurred.emit(text)

    @Slot()
    def dismissError(self):
        self._error = ''
        self.stateChanged.emit()

    @Slot(str)
    def appendLog(self, text):
        self._logs = (self._logs + text + '\n')[-100000:]
        self.logsChanged.emit()
        self._status = text
        if self._downloadActive:
            self._downloadInfo = text
        match = re.search(r'Transkrypcja: ([\d.]+) / ([\d.]+)', text)
        export = re.search(r'Eksport (\d+)/(\d+)', text)
        vod = re.search(r'VOD: ([\d.]+) / ([\d.]+)', text)
        if vod and float(vod[2]) > 0:
            self._progress = min(.99, float(vod[1]) / float(vod[2]))
        elif match and float(match[2]) > 0:
            self._progress = min(.99, float(match[1]) / float(match[2]))
        elif export:
            self._progress = (int(export[1]) - 1) / int(export[2])
        elif 'AI:' in text or 'Synchronizacja' in text or 'Wyodrębnianie' in text:
            self._progress = -1
        self.stateChanged.emit()

    def start(self, operation, complete, status, download=False):
        if self.busy or self.updates and self.updates.installing:
            return False
        self._error = ''
        self._status = status
        self._downloadActive = download
        self._downloadInfo = status if download else ''
        self._progress = -1
        self._complete = complete
        self._job = Job(operation, self)
        self._job.log.connect(self.appendLog, Qt.QueuedConnection)
        self._job.finished.connect(self.finish, Qt.QueuedConnection)
        self.stateChanged.emit()
        self._job.start()
        return True

    @Slot()
    def finish(self):
        job, complete = self._job, self._complete
        download = self._downloadActive
        self._downloadActive = False
        self._job, self._complete = None, None
        self._progress = 0 if job.cancelled or job.error else 1
        if self._closing:
            job.deleteLater()
            self.shutdownReady.emit()
            return
        if job.cancelled:
            self._status = 'Zadanie przerwane. Możesz uruchomić je ponownie.'
            if download:
                self._downloadInfo = 'Pobieranie przerwane. Wznów z tym samym linkiem, jakością, zakresem i folderem.'
        elif job.error:
            self.reportError(job.error)
        else:
            try:
                complete(job.result)
            except Exception:
                self.reportError(traceback.format_exc())
        if download and self._error:
            self._downloadInfo = 'Pobieranie nie powiodło się. Zapisane części zachowano; szczegóły błędu znajdziesz w dzienniku.'
        elif download and not job.cancelled:
            self._downloadInfo = self._status
        job.deleteLater()
        self.stateChanged.emit()

    @Slot()
    def cancelTask(self):
        if self._job:
            self._job.pipeline.cancel.set()
            self._status = 'Przerywanie… poczekaj na zatrzymanie bieżącej operacji.'
            if self._downloadActive:
                self._downloadInfo = self._status
            self.stateChanged.emit()

    @Slot(result=bool)
    def requestClose(self):
        if not self.busy:
            return True
        self._closing = True
        self.cancelTask()
        return False

    @Slot()
    def installUpdate(self):
        if self.busy or not self.updates or self.updates.installing or not self.updates.available:
            return
        recovery = ''
        try:
            if self.source:
                path = ROOT / '.local/updates/recovery-project.json'
                path.parent.mkdir(parents=True, exist_ok=True)
                self.project_data(self.source, self.segments, self.edited_clips(), self._settings, path)
                recovery = str(path)
            self.updates.install(recovery)
        except Exception:
            self.reportError(traceback.format_exc())

    def source_data(self, path, pipeline):
        source = local_path(path)
        if not source.is_file() or source.suffix.lower() not in {'.mp4', '.mkv', '.mov', '.avi', '.webm', '.m4v'}:
            raise ValueError('Wybierz jeden plik filmu: MP4, MKV, MOV, AVI, WEBM lub M4V.')
        metadata = pipeline.probe(source)
        work = ROOT / 'projects' / hashlib.sha256(str(source).encode()).hexdigest()[:16]
        work.mkdir(parents=True, exist_ok=True)
        segments, origin = existing_transcript(source, work, metadata['duration'])
        thumb = thumbnail_url(source, work)
        pipeline.check()
        return source, metadata, work, segments, origin, thumb

    def apply_source(self, data):
        self.source, self.metadata, self.work, self.segments, self.origin, self._thumb = data
        self._preview = ''
        self.previewChanged.emit()

    @Slot(str, str, str, bool, str, str)
    def downloadVod(self, url, begin, finish, gpu, provider, quality):
        if self.busy:
            return
        from vod_download import video_url, format_selector, timestamp, download_vod
        try:
            url, _ = video_url(url, provider)
            format_selector(quality)
            begin, finish = timestamp(begin), timestamp(finish)
            if finish and finish <= begin:
                raise ValueError('Koniec musi być później niż początek.')
        except ValueError as exc:
            self.reportError(str(exc))
            return
        folder = QFileDialog.getExistingDirectory(None, 'Folder pobierania VOD — wybierz ten sam, aby wznowić', str(ROOT))
        if not folder:
            return
        def operation(p):
            path = download_vod(p, url, folder, begin, finish, gpu, quality=quality, provider=provider)
            return self.source_data(path, p)
        def complete(data):
            self.apply_source(data)
            self.model.replace([])
            self.clipsChanged.emit()
            self._status = f'Film pobrany · {quality}. Przejdź do zakładki Film i przygotuj klipy.'
        self.start(operation, complete, 'Przygotowuję pobieranie VOD-a…', download=True)

    @Slot()
    def chooseSource(self):
        if self.busy:
            return
        path, _ = QFileDialog.getOpenFileName(None, 'Wybierz film', '', 'Filmy (*.mp4 *.mkv *.mov *.avi *.webm *.m4v)')
        if path:
            self.importSource(path)

    @Slot(str)
    def importSource(self, path):
        def complete(data):
            self.apply_source(data)
            self.model.replace([])
            self.clipsChanged.emit()
            self._status = 'Film dodany. Znajdź najlepsze fragmenty.'
        self.start(lambda p: self.source_data(path, p), complete, 'Wczytywanie filmu…')

    @Slot('QVariantList')
    def dropFiles(self, urls):
        if self.busy:
            return
        if len(urls) != 1:
            self.reportError('Przeciągnij jeden film naraz.')
            return
        value = urls[0]
        self.importSource(value.toString() if isinstance(value, QUrl) else str(value))

    @Slot()
    def attachTranscript(self):
        if not self.source or self.busy:
            return
        path, _ = QFileDialog.getOpenFileName(None, 'Wczytaj transkrypcję', str(self.source.parent), 'Transkrypcja (*.srt *.vtt *.json)')
        if path:
            self.importTranscript(path)

    @Slot(str)
    def importTranscript(self, path):
        if not self.source or self.busy:
            return
        source, work, duration = self.source, self.work, self.metadata['duration']
        def operation(p):
            rows = read_transcript(local_path(path), duration)
            remember_transcript(source, work, rows)
            return rows
        def complete(rows):
            self.segments, self.origin = rows, Path(path).name
            self._status = 'Transkrypcja wczytana. Możesz szukać klipów.'
        self.start(operation, complete, 'Wczytywanie transkrypcji…')

    @Slot()
    def downloadTranscript(self):
        if not self.segments or self.busy:
            return
        path, _ = QFileDialog.getSaveFileName(None, 'Zapisz transkrypcję', str(self.source.with_suffix('.srt')), 'Napisy SRT (*.srt);;Transkrypcja JSON (*.json)')
        if path:
            self.saveTranscript(path)

    @Slot(str)
    def saveTranscript(self, path):
        if not self.segments or self.busy:
            return
        source, rows, duration = self.source, copy.deepcopy(self.segments), self.metadata['duration']
        def operation(p):
            target = local_path(path)
            text = json.dumps({'version': 1, 'source': str(source), 'segments': rows}, ensure_ascii=False, indent=2) if target.suffix.lower() == '.json' else subtitle_text(rows, 0, duration)
            target.write_text(text, encoding='utf-8')
        self.start(operation, lambda _: self.set_status('Transkrypcja zapisana.'), 'Zapisywanie transkrypcji…')

    def set_status(self, text):
        self._status = text
        self.stateChanged.emit()

    @Slot()
    def transcribeOnly(self):
        if not self.source or self.busy:
            return
        if not self.metadata['audio']:
            self.reportError('Ten film nie zawiera ścieżki audio.')
            return
        source, work, size = self.source, self.work, self.whisper_size()
        def complete(rows):
            self.segments, self.origin = rows, 'Whisper lokalnie'
            self._status = 'Transkrypcja gotowa. Pobierz ją lub znajdź fragmenty.'
        self.start(lambda p: p.transcribe(source, work, size), complete, 'Przygotowanie transkrypcji…')

    def whisper_size(self):
        return {'Szybka': 'tiny', 'Zrównoważona': 'small', 'Dokładna': 'medium', 'Najdokładniejsza': 'large-v3'}[self._settings['whisper']]

    def clip_rows(self, clips, source, work):
        return [{**clip, 'selected': clip.get('selected', True),
                 'thumbnail': thumbnail_url(source, work, clip['start'])} for clip in clips]

    @Slot()
    def analyze(self):
        if not self.source or self.busy:
            return
        s = copy.deepcopy(self._settings)
        try:
            minimum, maximum = float(s['minimum'].replace(',', '.')), float(s['maximum'].replace(',', '.'))
            if not all(math.isfinite(v) for v in (minimum, maximum)) or maximum <= 0:
                raise ValueError('Długość klipu musi być dodatnia.')
            minimum, maximum = sorted((max(15., min(40., minimum)), max(15., min(40., maximum))))
            count = max(1, min(20, math.ceil(self.metadata['duration'] / maximum)))
            film_mode = s['mode'] == 'Film · minuty'
            if not film_mode:
                validate_options(count, minimum, maximum)
            if not self.metadata['audio'] and not self.segments and (not film_mode or s['burn']):
                raise ValueError('Ten film nie ma dźwięku. Wybór AI wymaga transkrypcji mowy.')
        except (ValueError, TypeError) as exc:
            self.reportError(str(exc))
            return
        source, work, duration, rows, size = self.source, self.work, self.metadata['duration'], copy.deepcopy(self.segments), self.whisper_size()
        def operation(p):
            if rows:
                p.log('Używam gotowej transkrypcji — bez ponownego rozpoznawania mowy.')
                segments = rows
            elif film_mode and not s['burn']:
                p.log('Tryb Film · minuty: pomijam transkrypcję, bo napisy są wyłączone.')
                segments = []
            else:
                segments = p.transcribe(source, work, size)
            clips = minute_clips(duration) if film_mode else p.select(segments, duration, count, minimum, maximum, s['brief'], work)
            views = self.clip_rows(clips, source, work)
            self.project_data(source, segments, clips, s, work / 'project.json')
            return segments, views
        def complete(result):
            self.segments, clips = result
            self.origin = self.origin or 'Whisper lokalnie'
            self.model.replace(clips)
            self.clipsChanged.emit()
            self._status = f'Podzielono cały film na {len(clips)} części.' if film_mode else f'Znaleziono {len(clips)} fragmentów. Sprawdź i wyeksportuj wybrane.'
        self.start(operation, complete, 'Wyszukiwanie fragmentów…')

    @Slot(int, bool)
    def selectClip(self, index, selected):
        if not self.busy and 0 <= index < len(self.model.rows):
            self.model.update(index, {'selected': selected})
            self.clipsChanged.emit()

    @Slot(int)
    def removeClip(self, index):
        if not self.busy and 0 <= index < len(self.model.rows):
            self.model.remove(index)
            self.clipsChanged.emit()

    @Slot(int, str, str)
    def editClip(self, index, start, end):
        if self.busy or not 0 <= index < len(self.model.rows):
            return
        try:
            values = {'start': float(start.replace(',', '.')), 'end': float(end.replace(',', '.'))}
            validate_clips([{**self.model.rows[index], **values}], self.metadata['duration'], 1, self.metadata['duration'], strict=True)
            self.model.update(index, values)
            self.clipsChanged.emit()
        except ValueError as exc:
            self.reportError(str(exc))

    def edited_clips(self, selected_only=False):
        clips = [row for row in self.model.rows if not selected_only or row.get('selected', True)]
        return validate_clips(clips, self.metadata['duration'], 1, self.metadata['duration'], strict=True)

    def render(self, clips, folder, preview):
        source, work, rows, s = self.source, self.work, copy.deepcopy(self.segments), copy.deepcopy(self._settings)
        def operation(p):
            files = p.export(source, clips, rows, folder, vertical=s['format'] == 'Pionowy 9:16', burn=s['burn'],
                             framing=FRAMING_LABELS[s['framing']], timing_work=work,
                             light_color=s['light_color'], speed_up=s['speed_up'], mirror=s['mirror'],
                             caption_font=s['caption_font'], caption_size=s['caption_size'],
                             caption_position=(s['caption_x'], s['caption_y']) if s['caption_custom'] else None,
                             fit_zoom=s['fit_zoom'], fit_focus=(s['fit_x'], s['fit_y']))
            return files, p.caption_segments
        def complete(result):
            files, self.segments = result
            if preview:
                self._preview = QUrl.fromLocalFile(files[0]).toString()
                self.previewChanged.emit()
                self.previewReady.emit()
                self._status = 'Podgląd gotowy.'
            else:
                self._status = f'Zapisano {len(files)} klipów w {folder}.'
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))
        self.start(operation, complete, 'Przygotowanie podglądu…' if preview else 'Eksport klipów…')

    @Slot(int)
    def previewClip(self, index):
        if not self.busy and 0 <= index < len(self.model.rows):
            self.render([self.edited_clips()[index]], self.work / 'preview', True)

    @Slot()
    def closePreview(self):
        self._preview = ''
        self.previewChanged.emit()

    @Slot()
    def exportClips(self):
        if self.busy or not self.model.rows:
            return
        folder = QFileDialog.getExistingDirectory(None, 'Gdzie zapisać klipy?', str(self.destination))
        if folder:
            self.exportTo(folder)

    @Slot(str)
    def exportTo(self, folder):
        if self.busy or not self.model.rows:
            return
        clips = self.edited_clips(True)
        if not clips:
            self.reportError('Zaznacz przynajmniej jeden klip.')
            return
        self.destination = local_path(folder)
        self.render(clips, self.destination, False)

    @Slot()
    def openDestination(self):
        self.destination.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.destination)))

    @staticmethod
    def project_data(source, segments, clips, settings, path):
        data = {'version': 2, 'source': str(source), 'segments': segments, 'clips': clips, 'settings': settings}
        Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

    @Slot()
    def saveProject(self):
        if not self.source or self.busy:
            return
        path, _ = QFileDialog.getSaveFileName(None, 'Zapisz projekt', str(self.work / 'clipfarm-project.json'), 'Projekt (*.json)')
        if path:
            self.saveProjectTo(path)

    @Slot(str)
    def saveProjectTo(self, path):
        if not self.source or self.busy:
            return
        source, rows, clips, s = self.source, copy.deepcopy(self.segments), self.edited_clips(), copy.deepcopy(self._settings)
        self.start(lambda p: self.project_data(source, rows, clips, s, local_path(path)),
                   lambda _: self.set_status('Projekt zapisany.'), 'Zapisywanie projektu…')

    @Slot()
    def openProject(self):
        if self.busy:
            return
        path, _ = QFileDialog.getOpenFileName(None, 'Otwórz projekt CLIPFARM', '', 'Projekt (*.json)')
        if path:
            self.openProjectFrom(path)

    @Slot(str)
    def openProjectFrom(self, path):
        defaults = copy.deepcopy(self._settings)
        def operation(p):
            data = json.loads(local_path(path).read_text(encoding='utf-8'))
            source_data = list(self.source_data(data['source'], p))
            source, metadata, work = source_data[:3]
            source_data[3] = validate_segments(data['segments'], metadata['duration']) if data['segments'] else source_data[3]
            if source_data[3]:
                remember_transcript(source, work, source_data[3])
                source_data[4] = 'projekt'
            clips = validate_clips(data['clips'], metadata['duration'], 1, metadata['duration'], strict=True)
            views = self.clip_rows(clips, source, work)
            for key, value in data.get('settings', {}).items():
                if key in SETTING_RANGES:
                    try:
                        defaults[key] = number(value, *SETTING_RANGES[key])
                    except (TypeError, ValueError):
                        pass
                elif key in defaults and isinstance(value, type(defaults[key])):
                    defaults[key] = value
            defaults['caption_font'] = resolve_font(defaults['caption_font'])
            if defaults['format'] not in ('Pionowy 9:16', 'Oryginalny'):
                defaults['format'] = 'Pionowy 9:16'
            if defaults['framing'] not in FRAMING_LABELS:
                defaults['framing'] = 'Cały obraz · czarne pasy'
            if defaults['whisper'] not in ('Szybka', 'Zrównoważona', 'Dokładna', 'Najdokładniejsza'):
                defaults['whisper'] = 'Zrównoważona'
            if defaults['mode'] not in ('AI klipy', 'Film · minuty'):
                defaults['mode'] = 'AI klipy'
            return source_data, views, defaults
        def complete(result):
            data, views, self._settings = result
            self.apply_source(data)
            self.model.replace(views)
            self.clipsChanged.emit()
            self.settingsChanged.emit()
            self._status = 'Wczytano projekt. Możesz poprawić i wyeksportować klipy.'
        self.start(operation, complete, 'Wczytywanie projektu…')
