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
    if point.x() < 296 and point.y() > window.height() - 40:
        scroll.setProperty('contentY', scroll.property('contentY') + point.y() - window.height() + 80)
        app.processEvents()
        point = target.mapToScene(QPointF(target.width() * fraction, target.height() / 2))
    elif point.x() < 296 and point.y() < 110:
        scroll.setProperty('contentY', max(0, scroll.property('contentY') + point.y() - 130))
        app.processEvents()
        point = target.mapToScene(QPointF(target.width() * fraction, target.height() / 2))
    assert target.isVisible() and target.isEnabled(), name
    QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, point.toPoint())
    settle()
def capture(name):
    if os.environ.get('CLIPFARM_SKIP_REVIEW_CAPTURES') == '1':
        return
    settle()
    assert window.grabWindow().save(str(review / name))
try:
    settle()
    click('previewPlaybackButton')
    frame = item('settingsPreviewFrame')
    picture = item('settingsPreviewPicture')
    phone = item('settingsPreviewPhone')
    assert phone.height() > frame.height() and phone.width() > frame.width()
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
    summary_bottom = summary.mapToItem(preview, QPointF(0, summary.height())).y()
    assert summary_bottom < preview.height() - 12, (summary_bottom, preview.height())
    capture('settings-preview-minimum.png')
    # Font names are shown in their own real registered family, and affect the caption.
    assert len(backend.fontChoices) == 20
    click('captionFontChoice')
    capture('settings-preview-font-list.png')
    QTest.keyClick(window, Qt.Key_End)
    QTest.keyClick(window, Qt.Key_Return)
    settle()
    assert backend.settings['caption_font'] == backend.fontChoices[-1]
    assert item('captionFontChoice').property('font').family() == backend.fontChoices[-1]
    captions = item('settingsPreviewCaptions')
    caption_texts = [child for child in captions.childItems() if child.property('text') in ('TAK', 'WYGLĄDA', 'TWÓJ', 'KLIP')]
    assert len(caption_texts) == 4
    assert all(child.property('font').family() == backend.fontChoices[-1] for child in caption_texts)
    click('captionSizeField')
    QTest.keyClick(window, Qt.Key_A, Qt.ControlModifier)
    for key in '110':
        QTest.keyClick(window, Qt.Key(ord(key)))
    QTest.keyClick(window, Qt.Key_Tab)
    settle()
    assert backend.captionSize == 110
    # Drag the complete caption line on the actual phone canvas, then nudge via keyboard.
    drag = item('settingsPreviewCaptionDrag')
    start = drag.mapToScene(QPointF(drag.width() / 2, drag.height() / 2))
    QTest.mousePress(window, Qt.LeftButton, Qt.NoModifier, start.toPoint())
    QTest.mouseMove(window, (start + QPointF(8, -40)).toPoint(), 50)
    QTest.mouseRelease(window, Qt.LeftButton, Qt.NoModifier, (start + QPointF(8, -40)).toPoint())
    settle()
    assert backend.settings['caption_custom'] and backend.settings['caption_y'] < .84
    assert captions.x() >= -1 and captions.x() + captions.width() <= frame.width() + 1
    previous = backend.settings['caption_y']
    QTest.keyClick(window, Qt.Key_Up)
    settle()
    assert backend.settings['caption_y'] < previous
    click('captionYField')
    QTest.keyClick(window, Qt.Key_A, Qt.ControlModifier)
    for key in '65':
        QTest.keyClick(window, Qt.Key(ord(key)))
    QTest.keyClick(window, Qt.Key_Tab)
    settle()
    assert abs(backend.settings['caption_y'] - .65) < .001
    backend.setSetting('caption_x', 0)
    backend.setSetting('caption_y', 1)
    settle()
    assert captions.x() >= 0 and captions.y() + captions.height() <= frame.height() + .01
    backend.setSetting('caption_x', .5)
    backend.setSetting('caption_y', .65)
    capture('settings-preview-caption-edit.png')
    # Zoom preserves source aspect; a drag selects the normalized source focus.
    zoom = item('fitZoomSlider')
    click('fitZoomSlider', .5)
    assert backend.settings['fit_zoom'] > 1
    assert abs(picture.width() / picture.height() - 1672 / 941) < .01
    image_drag = item('settingsPreviewImageDrag')
    start = image_drag.mapToScene(QPointF(image_drag.width() / 2, image_drag.height() * .18))
    previous = backend.settings['fit_x']
    QTest.mousePress(window, Qt.LeftButton, Qt.NoModifier, start.toPoint())
    QTest.mouseMove(window, (start + QPointF(-20, 15)).toPoint(), 50)
    QTest.mouseRelease(window, Qt.LeftButton, Qt.NoModifier, (start + QPointF(-20, 15)).toPoint())
    settle()
    assert backend.settings['fit_x'] > previous
    assert 0 <= backend.settings['fit_y'] <= 1
    capture('settings-preview-zoom-pan.png')
    click('previewResetButton')
    assert not backend.settings['caption_custom']
    assert backend.settings['fit_zoom'] == 1 and backend.settings['fit_x'] == .5 and backend.settings['fit_y'] == .5
    assert item('captionYField').property('text') == str(round(backend.previewLayout['caption_y'] / backend.previewLayout['canvas_height'] * 100))
    backend.setSetting('caption_font', 'Anton')
    backend.setSetting('caption_size', 84)
    click('settingsFormatChoice')
    QTest.keyClick(window, Qt.Key_End)
    QTest.keyClick(window, Qt.Key_Return)
    settle()
    assert backend.settings['format'] == 'Oryginalny'
    assert abs(frame.width() / frame.height() - 16 / 9) < .01
    assert abs(captions.property('fittedSize') - backend.captionSize * frame.width() / 1080) < 1
    capture('settings-preview-original-minimum.png')
    click('settingsFormatChoice')
    QTest.keyClick(window, Qt.Key_Home)
    QTest.keyClick(window, Qt.Key_Return)
    settle()
    # Use the real combo popup through keyboard selection.
    choice = item('settingsFramingChoice')
    click('settingsFramingChoice')
    QTest.keyClick(window, Qt.Key_End)
    QTest.keyClick(window, Qt.Key_Return)
    settle()
    assert backend.settings['framing'] == backend.framingLabels[-1], backend.settings
    assert picture.height() >= frame.height() - 1
    click('mirrorSwitch', .1)
    assert backend.settings['mirror'] and window.findChild(object, 'previewMirrorTransform').property('xScale') == -1
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
    click('editCaptionsButton')
    assert window.property('captionEditOpen')
    capture('caption-editor-desktop.png')
    window.resize(1100, 780)
    capture('caption-editor-minimum.png')
    click('captionEditorClose')
    assert not window.property('captionEditOpen')
    os.environ['CLIPFARM_REDUCED_MOTION'] = '1'
    backend.refreshAnimations()
    settle()
    assert not timer.property('running')
    assert not item('previewPlaybackButton').isEnabled()
    warnings = [message for kind, message in messages if kind in (QtMsgType.QtWarningMsg, QtMsgType.QtCriticalMsg, QtMsgType.QtFatalMsg)
                and ('qml' in message.lower() or 'QQml' in message)]
    assert not warnings, '\n'.join(warnings)
    print('PASS: real font selection and size editing; caption mouse/keyboard/numeric positioning; fit zoom/source-focus drag/reset; phone aspect ratios; mirror/colors; project/reduced motion; no QML warnings.')
finally:
    backend.updates.stop()
    shiboken6.delete(engine)
