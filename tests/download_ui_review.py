"""Qt download form, option forwarding and automatic source import; no external calls."""
from pathlib import Path
import sys
import time
import threading
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QObject, QtMsgType, qInstallMessageHandler
from PySide6.QtTest import QTest
import shiboken6
from engine import ROOT
from qt_app import create_application

messages = []
qInstallMessageHandler(lambda kind, context, message: messages.append((kind, message)))
app, engine, backend = create_application(check_updates=False)
window = engine.rootObjects()[0]
window.setProperty('sourceTab', 'Pobierz VOD')
def wait(condition):
    deadline = time.monotonic() + 15
    while not condition():
        app.processEvents()
        if time.monotonic() > deadline:
            raise AssertionError(backend.logs)
        time.sleep(.01)
try:
    wait(lambda: window.isExposed())
    quality = window.findChild(QObject, 'vodQuality')
    provider = window.findChild(QObject, 'vodProvider')
    gpu = window.findChild(QObject, 'vodGpu')
    assert quality.property('currentText') == '480p30'
    assert provider.property('currentText') == 'Auto'
    quality.setProperty('currentIndex', 0); app.processEvents()
    assert quality.property('currentText') == 'Oryginał' and not gpu.property('enabled')
    quality.setProperty('currentIndex', 1); provider.setProperty('currentIndex', 3); app.processEvents()
    assert quality.property('currentText') == '720p60' and provider.property('currentText') == 'YouTube'
    release = threading.Event()
    def fake_download(pipeline, *args, **kwargs):
        pipeline.log('VOD: 5.0 / 10.0 s · zapisano 3.2 MB · pozostało około 2 min 15 s')
        assert release.wait(5), 'Test UI did not release the worker'
        return ROOT / 'checks/synthetic.mp4'
    with patch('backend.QFileDialog.getExistingDirectory', return_value=str(ROOT / 'checks')) as folder, \
            patch('vod_download.download_vod', side_effect=fake_download) as download:
        backend.downloadVod('https://youtu.be/test', '00:00:02', '00:00:10', True, 'YouTube', '720p60')
        wait(lambda: backend.progress == .5)
        info = window.findChild(QObject, 'vodProgressInfo')
        assert info.property('visible') and '2 min 15 s' in info.property('text')
        assert backend.busy
        window.resize(1100, 780)
        QTest.qWait(200)
        window.grabWindow().save(str(ROOT / 'checks/download-live-ui.png'))
        release.set()
        wait(lambda: not backend.busy)
        assert not backend.errorMessage, backend.errorMessage
        assert download.call_args.args[3:6] == (2, 10, True)
        assert download.call_args.kwargs == {'quality': '720p60', 'provider': 'YouTube'}
        assert backend.videoPath.endswith('synthetic.mp4')
        assert '720p60' in backend.status
        backend.downloadVod('https://youtu.be/test', '', '', True, 'Kick', '480p30')
        assert backend.errorMessage and folder.call_count == 1
        backend.dismissError()
        window.setProperty('detailsOpen', False)
    window.resize(1100, 780)
    QTest.qWait(200)
    window.grabWindow().save(str(ROOT / 'checks/download-ui.png'))
    warnings = [m for t, m in messages if t in (QtMsgType.QtWarningMsg, QtMsgType.QtCriticalMsg, QtMsgType.QtFatalMsg)
                and ('qml' in m.lower() or 'QQml' in m)]
    assert not warnings, '\n'.join(warnings)
    print('PASS: provider/quality controls, original GPU state, worker parameters, validation and automatic source import.')
finally:
    backend.updates.stop()
    shiboken6.delete(engine)
