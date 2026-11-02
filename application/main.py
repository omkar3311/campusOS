import os
import sys

import cv2
from PySide6.QtCore import QLibraryInfo
from PySide6.QtWidgets import QApplication

qt_plugins = os.path.join(
    QLibraryInfo.path(QLibraryInfo.LibraryPath.PluginsPath),
    "platforms"
)
os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = qt_plugins

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from services.auth_service import is_login
from ui.login_window import LoginPage
from ui.dashboard_window import Dashboard

app = QApplication(sys.argv)

login_status, user = is_login()
window = Dashboard(user) if login_status else LoginPage()
window.show()

sys.exit(app.exec())
