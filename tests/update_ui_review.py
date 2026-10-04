"""Click the native update icon; verify byte UI, saved state and recurring checks."""
import json
from pathlib import Path
import sys
import tempfile
import time
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QPointF, Qt, QtMsgType, qInstallMessageHandler
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest
import shiboken6
from app_updates import CHECK_INTERVAL_MS
from engine import ROOT
from qt_app import create_application

messages = []
qInstallMessageHandler(lambda kind, context, message: messages.append((kind, message)))
app, engine, backend = create_application(check_updates=False)
updates = backend.updates
window = engine.rootObjects()[0]
review = ROOT / '.impeccable/review'
review.mkdir(parents=True, exist_ok=True)

def wait(condition):
    deadline = time.monotonic() + 15
    while not condition():
        app.processEvents()
        assert time.monotonic() < deadline, backend.status
        time.sleep(.01)

try:
    wait(lambda: window.isExposed())
    backend.importSource(str(ROOT / 'checks/synthetic.mp4'))
    wait(lambda: not backend.busy)
    assert not backend.errorMessage
    backend.setSetting('light_color', True)
    updates._candidate = {'manifest': {'version': 'build-ui-test'}}
    updates._status = 'Dostępna aktualizacja build-ui-test.'
    updates.changed.emit()
    button = window.findChild(QQuickItem, 'installUpdateButton')
    app.processEvents()
    assert button.isVisible() and button.isEnabled()
    window.resize(1100, 780)
    QTest.qWait(200)
    window.grabWindow().save(str(review / 'update-available-minimum.png'))
    with tempfile.TemporaryDirectory(dir=ROOT / 'checks') as temporary, patch('backend.ROOT', Path(temporary)), patch.object(updates, 'install') as install:
        position = button.mapToScene(QPointF(button.width() / 2, button.height() / 2)).toPoint()
        QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, position)
        app.processEvents()
        assert install.call_count == 1, 'The actual update icon must trigger installation'
        saved = Path(install.call_args.args[0])
        state = json.loads(saved.read_text(encoding='utf-8'))
        assert state['source'] == str(backend.source) and state['settings']['light_color']

    updates._installing = True
    updates._on_progress({'received': 250000, 'total': 1000000, 'rate': 250000, 'eta': 3})
    QTest.qWait(300)
    bar = window.findChild(QQuickItem, 'updateProgressBar')
    fill = bar.childItems()[0]
    quarter = fill.width()
    updates._on_progress({'received': 500000, 'total': 1000000, 'rate': 250000, 'eta': 2})
    app.processEvents()
    assert abs(fill.width() - quarter) < 2, 'The bar should animate instead of jumping instantly'
    QTest.qWait(100)
    assert quarter < fill.width() < bar.width() * .5 + 1
    assert not button.isVisible()
    info = window.findChild(QQuickItem, 'updateDownloadInfo')
    assert '0.5 / 1.0 MB' in info.property('text')
    for width, height, name in ((1100, 780, 'minimum'), (1360, 900, 'desktop')):
        window.resize(width, height)
        QTest.qWait(300)
        window.grabWindow().save(str(review / f'update-download-{name}.png'))
    updates._installing = False
    updates.changed.emit()
    vod_tab = window.findChild(QQuickItem, 'sourceTabs')
    position = vod_tab.mapToScene(QPointF(vod_tab.width() * .75, vod_tab.height() / 2)).toPoint()
    QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, position)
    wait(lambda: window.property('sourceTab') == 'Pobierz VOD')
    assert not backend.errorMessage, backend.errorMessage
    def downloading(pipeline):
        pipeline.log('VOD: 1200.0 / 24180.0 s · 480p30 · 25.0× · zapisano 201.4 MB · pozostało około 15 min 19 s')
        while not pipeline.cancel.is_set():
            time.sleep(.01)
        pipeline.check()
    backend.start(downloading, lambda _: None, 'Odczytuję VOD…', download=True)
    wait(lambda: backend.progress > 0)
    for width, height, name in ((1100, 780, 'minimum'), (1360, 900, 'desktop')):
        window.resize(width, height)
        QTest.qWait(600)
        assert not window.findChild(QQuickItem, 'detailsPanel').isVisible()
        assert not window.findChild(QQuickItem, 'previewPanel').isVisible()
        assert backend.busy
        window.grabWindow().save(str(review / f'vod-progress-{name}.png'))
    backend.cancelTask()
    wait(lambda: not backend.busy)

    assert updates.timer.interval() == CHECK_INTERVAL_MS == 300000
    with patch('app_updates.check_for_update', return_value=(None, '')) as check:
        updates.timer.setInterval(30)
        updates.timer.start()
        wait(lambda: check.call_count >= 2)
        updates.timer.stop()
    warnings = [m for kind, m in messages if kind in (QtMsgType.QtWarningMsg, QtMsgType.QtCriticalMsg, QtMsgType.QtFatalMsg)
                and ('qml' in m.lower() or 'QQml' in m)]
    assert not warnings, '\n'.join(warnings)
    print('PASS: actual update-icon click, saved source/settings, smooth byte progress, minimum/default layouts and recurring background checks.')
finally:
    if backend.busy:
        backend.cancelTask()
        wait(lambda: not backend.busy)
    updates.stop()
    shiboken6.delete(engine)
