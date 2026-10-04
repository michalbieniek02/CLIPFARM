"""Qt integration checks. AI/Whisper calls are controlled; FFmpeg and video playback are real.

Run: runtime/Scripts/python.exe tests/qt_review.py
Requires checks/synthetic.mp4 and checks/e2e/narrated.mp4 from the local media checks.
"""
import json
import os
from pathlib import Path
import sys
import time
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QUrl, QTimer, QtMsgType, qInstallMessageHandler, QMimeData, QPoint, QPointF, Qt
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest
import shiboken6
from backend import Backend
from engine import Cancelled, Pipeline, ROOT
from qt_app import create_application

messages = []
qInstallMessageHandler(lambda kind, context, message: messages.append((kind, message)))
app, engine, b = create_application(check_updates=False)
window = engine.rootObjects()[0]
out = ROOT / 'checks/qt'
out.mkdir(parents=True, exist_ok=True)


def wait_until(condition, seconds=40):
    limit = time.monotonic() + seconds
    while not condition():
        app.processEvents()
        if time.monotonic() > limit:
            raise AssertionError('Timeout: ' + b.status + '\n' + b.logs)
        time.sleep(.01)
    app.processEvents()


def done():
    wait_until(lambda: not b.busy, 120)
    assert not b.errorMessage, b.errorMessage


try:
    wait_until(lambda: window.isExposed())
    # A genuine GUI timer keeps ticking during a long worker operation.
    ticks = []
    timer = QTimer(); timer.timeout.connect(lambda: ticks.append(1)); timer.start(10)
    b.start(lambda p: time.sleep(.15), lambda _: None, 'Test wątku')
    assert b.busy
    done(); assert len(ticks) >= 5
    timer.stop()

    video = ROOT / 'checks/e2e/narrated.mp4'
    mime = QMimeData(); mime.setUrls([QUrl.fromLocalFile(str(video))])
    enter = QDragEnterEvent(QPoint(850, 700), Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier)
    app.sendEvent(window, enter)
    drop = QDropEvent(QPointF(850, 700), Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier)
    app.sendEvent(window, drop)
    assert drop.isAccepted(), 'QML DropArea did not accept the file outside the video card'
    done()
    assert b.source == video and b.videoThumbnail
    b.importTranscript(str(ROOT / 'checks/e2e/transcript.json')); done()
    original = json.loads(json.dumps(b.segments))
    b.saveTranscript(str(out / 'transcript.json')); done()
    b.saveTranscript(str(out / 'transcript.srt')); done()
    assert json.loads((out / 'transcript.json').read_text(encoding='utf-8'))['segments'] == original
    assert '-->' in (out / 'transcript.srt').read_text(encoding='utf-8')
    selected = [{'start': 0, 'end': 24.32, 'score': 8, 'title': 'Historia pierwszego nagrania',
                 'reason': 'Początek, zmiana podejścia i rezultat.', 'hook_sentence': original[0]['text']}]
    with patch.object(Pipeline, 'transcribe', side_effect=AssertionError('Transkrypcja nie powinna się powtarzać')), patch.object(Pipeline, 'select', return_value=selected) as select:
        b.analyze(); done(); assert select.call_count == 1
    assert b.clipCount == b.selectedCount == 1
    b.editClip(0, '0', '22'); assert b.clips[0]['end'] == 22
    b.selectClip(0, False); assert b.selectedCount == 0
    b.selectClip(0, True)
    b.setSetting('light_color', True); b.setSetting('speed_up', True); b.setSetting('mirror', True)
    b.saveProjectTo(str(out / 'project.json')); done()
    b.removeClip(0); assert b.clipCount == 0
    b.openProjectFrom(str(out / 'project.json')); done()
    assert b.clipCount == 1 and b.settings['light_color'] and b.settings['speed_up'] and b.settings['mirror']
    b.setSetting('burn', False)
    # Real FFmpeg export + actual embedded QtMultimedia decoding.
    b.previewClip(0); done(); assert b.previewUrl
    player = window.findChild(QMediaPlayer, 'previewPlayer')
    wait_until(lambda: player.videoSink().videoFrame().isValid())
    assert player.duration() > 0
    review = ROOT / '.impeccable/review'; review.mkdir(parents=True, exist_ok=True)
    QTest.qWait(300)
    window.grabWindow().save(str(review / 'desktop-preview.png'))
    for key in [Qt.Key_Tab] * 8 + [Qt.Key_Backtab] * 8:
        QTest.keyClick(window, key); app.processEvents()
        assert window.activeFocusItem().objectName() in {'previewClose', 'previewSeek', 'previewPlay', 'previewVolume'}
    QTest.keyClick(window, Qt.Key_Escape); app.processEvents()
    assert not window.property('overlayActive')
    b.closePreview(); player.stop()
    with patch('backend.QDesktopServices.openUrl', return_value=True):
        b.exportTo(str(out / 'exports')); done()
    assert list((out / 'exports').glob('*.mp4'))
    assert list((out / 'exports').glob('*.srt'))
    manifest = json.loads((out / 'exports/clips.json').read_text(encoding='utf-8'))
    assert manifest['speed_up'] and manifest['mirror']

    # Invalid input preserves the active project and exposes the full traceback.
    saved_source, saved_clips = b.source, b.clipCount
    field = window.findChild(QQuickItem, 'minimumField'); field.forceActiveFocus(); app.processEvents()
    b.importSource(str(out / 'missing.mp4')); wait_until(lambda: not b.busy)
    assert b.errorMessage and 'Traceback' in b.logs and b.source == saved_source and b.clipCount == saved_clips
    QTest.qWait(300)
    window.grabWindow().save(str(review / 'desktop-details.png'))
    for key in [Qt.Key_Tab] * 8 + [Qt.Key_Backtab] * 8:
        QTest.keyClick(window, key); app.processEvents()
        assert window.activeFocusItem().objectName() in {'detailsClose', 'detailsLog'}
    QTest.keyClick(window, Qt.Key_Escape); app.processEvents()
    assert not window.property('overlayActive')
    assert window.activeFocusItem() == field, 'Focus must return to the previous control'
    b.dismissError()

    def cancellable(p):
        while not p.cancel.is_set():
            time.sleep(.01)
        p.check()
    b.start(cancellable, lambda _: None, 'Test przerwania')
    b.cancelTask(); done(); assert 'przerwane' in b.status

    b.importSource(str(ROOT / 'checks/synthetic.mp4')); done()
    b.setSetting('mode', 'Film · minuty'); b.setSetting('burn', False)
    with patch.object(Pipeline, 'transcribe', side_effect=AssertionError('Minuty bez napisów nie wymagają Whispera')), patch.object(Pipeline, 'select', side_effect=AssertionError('Minuty nie wymagają AI')):
        b.analyze(); done()
    assert b.clipCount == 1 and b.clips[0]['start'] == 0 and b.clips[0]['end'] > 7
    os.environ['CLIPFARM_REDUCED_MOTION'] = '1'; b.refreshAnimations(); assert not b.animationsEnabled
    del os.environ['CLIPFARM_REDUCED_MOTION']; b.refreshAnimations()
    wait_until(lambda: True)
    warnings = [m for t, m in messages if t in (QtMsgType.QtWarningMsg, QtMsgType.QtCriticalMsg, QtMsgType.QtFatalMsg) and ('qml' in m.lower() or 'QQml' in m)]
    assert not warnings, '\n'.join(warnings)
    print('PASS: QML without warnings; responsive worker, import/drop, transcript reuse/download, AI/minute bridge, edit/select/remove, project round-trip, real FFmpeg preview/export, QtMultimedia frames, errors, cancellation, reduced motion.')
finally:
    b.updates.stop()
    if b.busy:
        b.cancelTask(); wait_until(lambda: not b.busy, 120)
    shiboken6.delete(engine)
