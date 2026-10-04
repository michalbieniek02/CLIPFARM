"""Click the real caption editor and verify timing, drafts, focus and busy guards."""
import copy
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QPointF, Qt, QtMsgType, qInstallMessageHandler
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest
import shiboken6
from qt_app import create_application

messages = []
qInstallMessageHandler(lambda kind, context, message: messages.append((kind, message)))
app, engine, backend = create_application(check_updates=False)
window = engine.rootObjects()[0]
def item(name, root=None):
    root = root or window.contentItem()
    if root.objectName() == name:
        return root
    for child in root.childItems():
        found = item(name, child)
        if found:
            return found
def click(target):
    assert target and target.isVisible() and target.isEnabled()
    point = target.mapToScene(QPointF(target.width() / 2, target.height() / 2)).toPoint()
    QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, point)
    QTest.qWait(100)
try:
    backend.segments = [
        {'start': 0, 'end': 2, 'text': 'Pierwsze zdanie', 'words': [
            {'start': .1, 'end': .8, 'text': 'Pierwsze'}, {'start': 1, 'end': 1.8, 'text': 'zdanie'}]},
        {'start': 2, 'end': 4, 'text': 'Drugie zdanie'},
    ]
    backend.stateChanged.emit()
    QTest.qWait(150)
    before = copy.deepcopy(backend.segments[0]['words'])
    click(window.findChild(QQuickItem, 'editCaptionsButton'))
    QTest.qWait(300)
    assert window.property('captionEditOpen')
    assert not window.findChild(QQuickItem, 'settingsModeTabs').isEnabled()
    first, second = item('captionText_0'), item('captionText_1')
    assert first and second
    second.setProperty('text', 'Nie zapisuj jeszcze')
    first.setProperty('text', 'Poprawione zdanie')
    QTest.qWait(50)
    click(item('captionSave_0'))
    assert backend.segments[0]['text'] == 'Poprawione zdanie'
    assert [(w['start'], w['end']) for w in backend.segments[0]['words']] == [(w['start'], w['end']) for w in before]
    assert item('captionText_1').property('text') == 'Nie zapisuj jeszcze', 'Saving one row must preserve another draft'
    first = item('captionText_0')
    first.setProperty('text', 'Trzy nowe slowa')
    QTest.qWait(50)
    click(item('captionSave_0'))
    assert len(backend.segments[0]['words']) == 3
    assert backend.segments[0]['words'][0]['start'] == before[0]['start']
    assert backend.segments[0]['words'][-1]['end'] == before[-1]['end']
    assert 'synchronizacj' in backend.status
    # Empty text cannot replace valid saved captions; editor drafts survive the error panel.
    item('captionText_0').setProperty('text', '')
    QTest.qWait(50)
    click(item('captionSave_0'))
    assert window.property('detailsOpen') and window.property('captionEditOpen')
    assert backend.segments[0]['text'] == 'Trzy nowe slowa'
    click(window.findChild(QQuickItem, 'detailsClose'))
    QTest.qWait(250)
    assert window.property('captionEditOpen') and item('captionText_0').property('text') == ''
    close = item('captionEditorClose')
    close.forceActiveFocus()
    QTest.keyClick(window, Qt.Key_Tab)
    QTest.qWait(100)
    assert item('captionText_0').hasActiveFocus()
    backend._job = object()
    backend.stateChanged.emit()
    app.processEvents()
    assert not item('captionText_0').isEnabled()
    assert not backend.editCaption(0, 'Busy guard')
    backend._job = None
    backend.stateChanged.emit()
    click(close)
    assert not window.property('captionEditOpen')
    warnings = [message for kind, message in messages if kind in (QtMsgType.QtWarningMsg, QtMsgType.QtCriticalMsg, QtMsgType.QtFatalMsg)
                and ('qml' in message.lower() or 'QQml' in message)]
    assert not warnings, '\n'.join(warnings)
    print('PASS: actual caption editor clicks; timing retained/reflowed; drafts/error recovery; focus; busy guard; no QML warnings.')
finally:
    backend._job = None
    backend.updates.stop()
    shiboken6.delete(engine)
