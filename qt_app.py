"""PySide6/QML application entry point; invoked by the existing Windows launcher."""
import os
from pathlib import Path
import sys

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QFont, QFontDatabase, QIcon
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtWidgets import QApplication

from backend import Backend
from app_updates import Updates

ROOT = Path(__file__).resolve().parent


def create_application(check_updates=True):
    QQuickStyle.setStyle('Basic')
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName('CLIPFARM')
    app.setOrganizationName('CLIPFARM')
    app.setWindowIcon(QIcon(str(ROOT / 'assets/clipfarm.ico')))
    families = QFontDatabase.families()
    app.setFont(QFont('Inter' if 'Inter' in families else 'Segoe UI', 10))
    backend = Backend()
    updates = Updates(ROOT, backend, auto_check=check_updates)
    backend.updates = updates
    # Keep the context object alive until the QML engine is destroyed.
    app._clipfarm_backend = backend
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty('backend', backend)
    engine.rootContext().setContextProperty('updates', updates)
    engine.load(QUrl.fromLocalFile(str(ROOT / 'qml/Main.qml')))
    if not engine.rootObjects():
        raise RuntimeError('Nie udało się wczytać interfejsu QML.')
    backend.shutdownReady.connect(app.quit)
    updates.restartRequested.connect(app.quit)
    updates.failed.connect(backend.reportError)
    if updates.startup_error:
        QTimer.singleShot(0, lambda: backend.reportError(updates.startup_error))
    app.aboutToQuit.connect(updates.stop)
    return app, engine, backend


def main():
    if sys.version_info < (3, 11):
        raise RuntimeError('CLIPFARM wymaga Python 3.11 lub nowszego.')
    if os.name == 'nt':
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('Clipfarm.Desktop')
    app, engine, backend = create_application()
    if '--restore-project' in sys.argv:
        index = sys.argv.index('--restore-project') + 1
        if index < len(sys.argv) and Path(sys.argv[index]).is_file():
            QTimer.singleShot(0, lambda: backend.openProjectFrom(sys.argv[index]))
    try:
        return app.exec()
    finally:
        backend.updates.stop()
        import shiboken6
        shiboken6.delete(engine)


if __name__ == '__main__':
    sys.exit(main())
