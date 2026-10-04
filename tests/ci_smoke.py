"""QML loads on the Windows CI runner without a GPU or a GitHub network request."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QtMsgType, qInstallMessageHandler
from PySide6.QtTest import QTest
import shiboken6
from qt_app import create_application

messages = []
qInstallMessageHandler(lambda kind, context, message: messages.append((kind, message)))
app, engine, backend = create_application(check_updates=False)
try:
    assert engine.rootObjects()
    QTest.qWait(100)
    warnings = [message for kind, message in messages if kind in (QtMsgType.QtWarningMsg, QtMsgType.QtCriticalMsg, QtMsgType.QtFatalMsg)
                and ('qml' in message.lower() or 'QQml' in message)]
    assert not warnings, '\n'.join(warnings)
    assert backend.updates.timer.interval() == 300000
    print('PASS: native QML starts, update context exists, five-minute interval, no QML warnings.')
finally:
    backend.updates.stop()
    shiboken6.delete(engine)
