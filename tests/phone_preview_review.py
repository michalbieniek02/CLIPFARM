"""Native Windows interaction and rendered pixels for the full-phone canvas.

Run locally with runtime\\Scripts\\python.exe. This is intentionally separate
from CI's offscreen render checks: the rounded GPU mask is reviewed in a real
window, at both supported workspace sizes.
"""
from pathlib import Path
import copy
import json
import os
import sys
import tempfile
import time

os.environ['QT_QPA_PLATFORM'] = 'windows'
os.environ.pop('QT_QUICK_BACKEND', None)
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
from PySide6.QtCore import QPoint, QPointF, Qt, QtMsgType, qInstallMessageHandler
from PySide6.QtGui import QImage, QWheelEvent
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest
import shiboken6

from engine import Pipeline
from qt_app import create_application

messages = []
qInstallMessageHandler(lambda kind, context, message: messages.append((kind, message)))
app, engine, backend = create_application(check_updates=False)
window = engine.rootObjects()[0]
review = ROOT / '.impeccable/review'
review.mkdir(parents=True, exist_ok=True)
captures = []


def item(name):
    found = window.findChild(QQuickItem, name)
    assert found, name
    return found


def settle():
    QTest.qWait(350)


def scene(target, x=.5, y=.5):
    return target.mapToScene(QPointF(target.width() * x, target.height() * y))


def click(name, fraction=.5):
    target = item(name)
    point = scene(target, fraction)
    if point.x() < 296:
        scroll = item('settingsScroll').property('contentItem')
        if point.y() > window.height() - 40:
            scroll.setProperty('contentY', scroll.property('contentY') + point.y() - window.height() + 80)
        elif point.y() < 110:
            scroll.setProperty('contentY', max(0, scroll.property('contentY') + point.y() - 130))
        app.processEvents()
        point = scene(target, fraction)
    assert target.isVisible() and target.isEnabled(), name
    QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, point.toPoint())
    settle()


def select(name, options, value):
    click(name)
    QTest.keyClick(window, Qt.Key_Home)
    for _ in range(options.index(value)):
        QTest.keyClick(window, Qt.Key_Down)
    QTest.keyClick(window, Qt.Key_Return)
    settle()


def capture(name):
    settle()
    path = review / ('phone-' + name + '.png')
    assert window.grabWindow().save(str(path))
    captures.append(path)


def rgb():
    image = window.grabWindow().convertToFormat(QImage.Format_RGBA8888)
    return np.frombuffer(image.bits(), dtype=np.uint8).reshape(image.height(), image.bytesPerLine())[:, :image.width() * 4].reshape(image.height(), image.width(), 4)[:, :, :3].copy()


def visible_pixel(image, target, x, y):
    point = scene(target, x, y)
    px, py = round(point.x()), round(point.y())
    return np.median(image[py - 1:py + 2, px - 1:px + 2], axis=(0, 1))


def assert_cover():
    frame, picture = item('settingsPreviewFrame'), item('settingsPreviewPicture')
    assert picture.x() <= .01 and picture.y() <= .01
    assert picture.x() + picture.width() >= frame.width() - .01
    assert picture.y() + picture.height() >= frame.height() - .01
    # Independent source aspect test: filling must crop, never stretch.
    assert abs(picture.width() / picture.height() - 1672 / 941) < .005


def assert_phone_pixels():
    screen, frame = item('settingsPreviewScreen'), item('settingsPreviewFrame')
    assert abs(screen.width() / screen.height() - 9 / 19.5) < .0001
    assert abs(frame.width() - screen.width()) < .01
    assert abs(frame.height() - screen.height()) < .01
    assert abs(frame.x()) < .01 and abs(frame.y()) < .01
    assert_cover()
    image = rgb()
    # Probe each edge away from the island, home indicator and rounded corners.
    # A black letterbox has RGB zero; the actual sample source has color here.
    for x, y in ((.02, .3), (.02, .7), (.98, .3), (.98, .7), (.35, .025), (.65, .025), (.35, .975), (.65, .975)):
        actual = visible_pixel(image, screen, x, y)
        assert actual.max() > 12, ('Black phone edge', x, y, actual)
    # Rounded screen corners are transparent through to the workbench, rather
    # than letting the full-screen image bleed beyond the hardware frame.
    for x, y in ((.01, .004), (.99, .004), (.01, .996), (.99, .996)):
        actual = visible_pixel(image, screen, x, y)
        # At the smaller window, subpixel rounding can put a corner probe on
        # the gray antialiased hardware rim. Both that rim and Theme.surface
        # have increasing R/G/B, unlike the warm tan source at every corner.
        assert actual[0] <= actual[1] <= actual[2] and actual[2] - actual[0] >= 1 and actual.max() <= 175, ('Unmasked corner', x, y, actual)


def done(seconds=30):
    deadline = time.monotonic() + seconds
    while backend.busy:
        QTest.qWait(10)
        assert time.monotonic() < deadline, 'Project operation timeout'
    settle()
    assert not backend.errorMessage, backend.errorMessage


try:
    settle()
    if item('previewPlaybackButton').isEnabled():
        click('previewPlaybackButton')
    frame, screen = item('settingsPreviewFrame'), item('settingsPreviewScreen')
    assert backend.settings['format'] == 'Pionowy 9:16'
    assert abs(frame.width() / frame.height() - 9 / 16) < .0001
    assert frame.height() < screen.height() and frame.y() > 0
    assert backend.previewLayout['canvas_width'] == 1080 and backend.previewLayout['canvas_height'] == 1920
    capture('standard-desktop')

    click('previewFillScreenButton')
    assert backend.settings['format'] == 'Telefon 9:19,5'
    assert backend.settings['framing'] == 'Wypełnij · środek'
    assert backend.previewLayout['canvas_width'] == 1080 and backend.previewLayout['canvas_height'] == 2340
    assert not item('previewFillScreenButton').isEnabled()
    backend.setSetting('burn', False)
    settle()
    assert_phone_pixels()
    backend.setSetting('burn', True)
    capture('filled-desktop')

    # Native mouse pan, wheel zoom and keyboard nudges share export geometry.
    drag = item('settingsPreviewImageDrag')
    start = scene(drag, .5, .3)
    previous = backend.settings['fit_x']
    QTest.mousePress(window, Qt.LeftButton, Qt.NoModifier, start.toPoint())
    QTest.mouseMove(window, (start + QPointF(-24, 10)).toPoint(), 50)
    QTest.mouseRelease(window, Qt.LeftButton, Qt.NoModifier, (start + QPointF(-24, 10)).toPoint())
    settle()
    assert backend.settings['fit_x'] > previous
    assert_cover()
    previous = backend.settings['fit_x']
    QTest.keyClick(window, Qt.Key_Left)
    settle()
    assert backend.settings['fit_x'] > previous
    point = scene(drag, .5, .3)
    event = QWheelEvent(point, QPointF(window.mapToGlobal(point.toPoint())), QPoint(0, 0), QPoint(0, 120), Qt.NoButton, Qt.NoModifier, Qt.NoScrollPhase, False)
    app.sendEvent(window, event)
    settle()
    assert backend.settings['fit_zoom'] > 1
    assert_cover()
    for x, y in ((0, 0), (1, 1), (0, 1), (1, 0)):
        backend.setSetting('fit_x', x)
        backend.setSetting('fit_y', y)
        settle()
        assert_cover()
    # Start at a saturated edge and move back toward the image: the first
    # small drag must move immediately instead of crossing a focus dead zone.
    backend.setSetting('fit_x', 1)
    backend.setSetting('fit_y', .5)
    settle()
    picture = item('settingsPreviewPicture')
    old_x = picture.x()
    start = scene(drag, .5, .3)
    QTest.mousePress(window, Qt.LeftButton, Qt.NoModifier, start.toPoint())
    QTest.mouseMove(window, (start + QPointF(8, 0)).toPoint(), 50)
    QTest.mouseRelease(window, Qt.LeftButton, Qt.NoModifier, (start + QPointF(8, 0)).toPoint())
    settle()
    assert picture.x() > old_x + 1, ('Clamped focus drag dead zone', old_x, picture.x())
    capture('panned-desktop')

    # Captions move in full output-canvas coordinates, including keyboard.
    caption = item('settingsPreviewCaptionDrag')
    start = scene(caption)
    QTest.mousePress(window, Qt.LeftButton, Qt.NoModifier, start.toPoint())
    QTest.mouseMove(window, (start + QPointF(0, -36)).toPoint(), 50)
    QTest.mouseRelease(window, Qt.LeftButton, Qt.NoModifier, (start + QPointF(0, -36)).toPoint())
    settle()
    assert backend.settings['caption_custom'] and backend.settings['caption_y'] < .84375
    previous = backend.settings['caption_y']
    QTest.keyClick(window, Qt.Key_Up)
    settle()
    assert backend.settings['caption_y'] < previous
    assert abs(backend.previewLayout['caption_y'] - backend.settings['caption_y'] * 2340) < .01
    click('previewResetButton')
    assert backend.settings['fit_zoom'] == 1 and backend.settings['fit_x'] == .5 and backend.settings['fit_y'] == .5
    assert not backend.settings['caption_custom']

    window.resize(1100, 780)
    settle()
    backend.setSetting('burn', False)
    assert_phone_pixels()
    backend.setSetting('burn', True)
    capture('filled-minimum')
    summary = item('previewTranscriptionInfo')
    preview = item('settingsPreview')
    assert summary.mapToItem(preview, QPointF(0, summary.height())).y() < preview.height() - 12
    click('settingsFormatChoice')
    capture('format-menu-minimum')
    QTest.keyClick(window, Qt.Key_Escape)
    select('settingsFormatChoice', backend.formatChoices, 'Pionowy 9:16')
    assert backend.settings['format'] == 'Pionowy 9:16'
    assert abs(frame.width() / frame.height() - 9 / 16) < .0001
    capture('standard-minimum')
    select('settingsFormatChoice', backend.formatChoices, 'Oryginalny')
    assert backend.settings['format'] == 'Oryginalny'
    assert abs(frame.width() / frame.height() - backend.previewLayout['canvas_width'] / backend.previewLayout['canvas_height']) < .0001
    assert abs(frame.width() / frame.height() - 1672 / 941) < .005
    assert not item('settingsFramingChoice').isEnabled()
    capture('original-minimum')
    select('settingsFormatChoice', backend.formatChoices, 'Telefon 9:19,5')
    assert backend.settings['format'] == 'Telefon 9:19,5'
    select('settingsFramingChoice', backend.framingLabels, 'Cały obraz · czarne pasy')
    assert item('settingsPreviewPicture').height() < frame.height() / 2
    assert item('settingsPreviewImageDrag').property('enabled')
    select('settingsFramingChoice', backend.framingLabels, 'Podążaj za twarzą')
    assert backend.settings['framing'] == 'Podążaj za twarzą', (backend.settings['framing'], item('settingsFramingChoice').property('currentIndex'), item('settingsFramingChoice').property('highlightedIndex'))
    assert not item('settingsPreviewImageDrag').property('enabled')
    assert not item('fitZoomSlider').isVisible()
    click('previewFillScreenButton')
    assert_cover()
    click('sourceTabs', .75)
    capture('vod-minimum')
    click('sourceTabs', .25)

    # Busy UI prevents changes and the bridge itself rejects the same action.
    before = copy.deepcopy(backend.settings)
    backend._job = object()
    backend.stateChanged.emit()
    settle()
    assert not item('previewResetButton').isEnabled()
    assert not item('settingsFormatChoice').isEnabled()
    assert not item('settingsPreviewImageDrag').property('enabled')
    backend.fillPhoneScreen()
    backend.setSetting('format', 'Oryginalny')
    assert backend.settings == before
    backend._job = None
    backend.stateChanged.emit()
    settle()

    # A new project with real local media persists the new format and crop.
    (ROOT / 'checks').mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='phone-preview-', dir=ROOT / 'checks') as folder:
        folder = Path(folder)
        source = folder / 'source.mp4'
        p = Pipeline()
        p.run([p.ffmpeg(), '-y', '-f', 'lavfi', '-i', 'color=c=blue:s=640x360:r=2:d=2', '-c:v', 'libx264', '-preset', 'ultrafast', str(source)])
        backend.importSource(str(source))
        done()
        backend.setSetting('fit_zoom', 1.5)
        backend.setSetting('fit_x', .6)
        backend.setSetting('fit_y', .4)
        backend.setSetting('caption_custom', True)
        backend.setSetting('caption_x', .4)
        backend.setSetting('caption_y', .3)
        saved = copy.deepcopy(backend.settings)
        project = folder / 'project.json'
        backend.saveProjectTo(str(project))
        done()
        assert json.loads(project.read_text(encoding='utf-8'))['settings']['format'] == 'Telefon 9:19,5'
        backend.setSetting('format', 'Oryginalny')
        backend.setSetting('fit_zoom', 1)
        backend.openProjectFrom(str(project))
        done()
        assert backend.settings == saved
        assert backend.previewLayout['canvas_height'] == 2340
        assert_cover()
        backend.render([{'start': 0, 'end': 1, 'title': 'Phone bridge', 'reason': 'QA', 'score': 8}], folder / 'render', preview=True)
        done(45)
        rendered = list((folder / 'render').glob('*.mp4'))
        assert len(rendered) == 1
        metadata = p.probe(rendered[0])
        assert (metadata['width'], metadata['height']) == (1080, 2340), metadata
        assert backend.previewUrl.endswith(rendered[0].name)
        QTest.keyClick(window, Qt.Key_Escape)
        settle()

    os.environ['CLIPFARM_REDUCED_MOTION'] = '1'
    backend.refreshAnimations()
    settle()
    timer = window.findChild(object, 'previewCaptionTimer')
    assert not timer.property('running')
    assert not item('previewPlaybackButton').isEnabled()
    warnings = [message for kind, message in messages if kind in (QtMsgType.QtWarningMsg, QtMsgType.QtCriticalMsg, QtMsgType.QtFatalMsg)
                and ('qml' in message.lower() or 'QQml' in message)]
    assert not warnings, '\n'.join(warnings)
    print('PASS: full native phone edges and rounded mask; cover aspect and pan/zoom/keyboard/clamp; caption placement; formats/fit/face; both window sizes; VOD; project roundtrip; actual backend render 1080x2340; busy/reduced motion; no QML warnings.')
    for path in captures:
        print(path)
finally:
    backend._job = None
    backend.updates.stop()
    shiboken6.delete(engine)
