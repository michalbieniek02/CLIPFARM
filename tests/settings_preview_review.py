"""Click the sidebar and verify its native live preview, both layouts and reduced motion."""
from pathlib import Path
import os
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QPointF, Qt, QtMsgType, qInstallMessageHandler
from PySide6.QtQuick import QQuickItem
from PySide6.QtGui import QImage
from PySide6.QtTest import QTest
import shiboken6
from engine import ROOT
from qt_app import create_application

messages = []
qInstallMessageHandler(lambda kind, context, message: messages.append((kind, message)))
app, engine, backend = create_application(check_updates=False)
window = engine.rootObjects()[0]
review = ROOT / '.impeccable/review'
review.mkdir(parents=True, exist_ok=True)
def item(name):
    found = window.findChild(QQuickItem, name)
    assert found, name
    return found
def settle():
    QTest.qWait(350)
def click(name, fraction=.5):
    target = item(name)
    point = target.mapToScene(QPointF(target.width() * fraction, target.height() / 2))
    scroll = item('settingsScroll').property('contentItem')
    if name.endswith('Switch') and point.y() > window.height() - 40:
        scroll.setProperty('contentY', scroll.property('contentY') + point.y() - window.height() + 80)
        app.processEvents()
        point = target.mapToScene(QPointF(target.width() * fraction, target.height() / 2))
    assert target.isVisible() and target.isEnabled(), name
    QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, point.toPoint())
    settle()
def capture(name):
    settle()
    assert window.grabWindow().save(str(review / name))
try:
    settle()
    click('previewPlaybackButton')
    frame = item('settingsPreviewFrame')
    picture = item('settingsPreviewPicture')
    assert abs(frame.width() / frame.height() - 9 / 16) < .005
    assert item('settingsPreviewCaptions').isVisible()
    assert picture.height() < frame.height() / 2
    # Check the rendered result, including Qt's source-texture optimizations.
    import numpy as np
    def pixels():
        point = frame.mapToScene(QPointF(0, 0))
        image = window.grabWindow().copy(round(point.x()), round(point.y()), round(frame.width()), round(frame.height()))
        image = image.convertToFormat(QImage.Format_RGBA8888)
        return np.frombuffer(image.bits(), dtype=np.uint8).reshape(image.height(), image.bytesPerLine())[:, :image.width() * 4].reshape(image.height(), image.width(), 4)[:, :, :3].copy()
    backend.setSetting('burn', False)
    settle()
    normal = pixels()
    backend.setSetting('mirror', True)
    settle()
    mirrored = pixels()
    difference = np.abs(normal[:, ::-1].astype(float) - mirrored.astype(float)).mean()
    same = np.abs(normal.astype(float) - mirrored.astype(float)).mean()
    assert difference < 8 and difference < same, (difference, same)
    backend.setSetting('mirror', False)
    backend.setSetting('light_color', True)
    settle()
    assert np.abs(normal.astype(float) - pixels().astype(float)).mean() > .2, 'Color correction must affect the rendered image'
    backend.setSetting('light_color', False)
    backend.setSetting('burn', True)
    capture('settings-preview-desktop.png')
    window.resize(1100, 780)
    settle()
    assert abs(frame.width() / frame.height() - 9 / 16) < .005
    assert item('settingsPreview').height() > 500
    summary = item('previewTranscriptionInfo')
    preview = item('settingsPreview')
    assert summary.y() + summary.height() < preview.height() - 10, (summary.y(), summary.height(), preview.height())
    capture('settings-preview-minimum.png')
    click('settingsFormatTabs', .75)
    assert backend.settings['format'] == 'Oryginalny'
    assert abs(frame.width() / frame.height() - 16 / 9) < .01
    capture('settings-preview-original-minimum.png')
    click('settingsFormatTabs', .25)
    # Use the real combo popup through keyboard selection.
    choice = item('settingsFramingChoice')
    click('settingsFramingChoice')
    QTest.keyClick(window, Qt.Key_End)
    QTest.keyClick(window, Qt.Key_Return)
    settle()
    assert backend.settings['framing'] == backend.framingLabels[-1], backend.settings
    assert picture.height() >= frame.height() - 1
    before = picture.x()
    click('mirrorSwitch', .1)
    assert backend.settings['mirror'] and window.findChild(object, 'previewMirrorTransform').property('xScale') == -1
    assert abs(picture.x() - before) > 5
    click('colorSwitch', .1)
    assert backend.settings['light_color'] and item('settingsPreviewEffect').property('contrast') > 0
    click('tempoSwitch', .1)
    assert backend.settings['speed_up'] and item('previewTempoLabel').property('text') == '1,1×'
    timer = window.findChild(object, 'previewCaptionTimer')
    assert timer.property('interval') < 420
    capture('settings-preview-effects-minimum.png')
    click('burnSwitch', .1)
    assert not item('settingsPreviewCaptions').isVisible()
    click('burnSwitch', .1)
    click('settingsModeTabs', .75)
    assert '54,5' in item('previewLengthLabel').property('text')
    click('sourceTabs', .75)
    capture('settings-preview-vod-minimum.png')
    # Original media workflow still fits the narrower workspace.
    click('sourceTabs', .25)
    backend.openProjectFrom(str(ROOT / 'checks/qt/project.json'))
    deadline = time.monotonic() + 15
    while backend.busy:
        app.processEvents()
        assert time.monotonic() < deadline
        time.sleep(.01)
    assert not backend.errorMessage, backend.errorMessage
    window.resize(1360, 900)
    capture('settings-preview-project-desktop.png')
    os.environ['CLIPFARM_REDUCED_MOTION'] = '1'
    backend.refreshAnimations()
    settle()
    assert not timer.property('running')
    assert not item('previewPlaybackButton').isEnabled()
    warnings = [message for kind, message in messages if kind in (QtMsgType.QtWarningMsg, QtMsgType.QtCriticalMsg, QtMsgType.QtFatalMsg)
                and ('qml' in message.lower() or 'QQml' in message)]
    assert not warnings, '\n'.join(warnings)
    print('PASS: actual sidebar clicks change format, crop, mirror, colors, captions, tempo and length; media project fits; reduced motion; no QML warnings.')
finally:
    backend.updates.stop()
    shiboken6.delete(engine)
