import sys
import os
import shutil
import webbrowser
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QSystemTrayIcon, QMenu, QAction, QStyle
from PyQt5.QtCore import Qt, QThread, QEvent
from PyQt5.QtGui import QFont, QIcon

from app import create_app

class FlaskThread(QThread):
    def run(self):
        app = create_app()
        # Дополнительно создаем папку instance, чтобы БД не падала
        os.makedirs(os.path.join(app.config['BASE_DIR'], 'instance'), exist_ok=True)
        app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)

class StudioGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.flask_thread = FlaskThread()
        self.flask_thread.start()
        
        self.initUI()
        self.initTray()

    def get_base_dir(self):
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        return os.path.abspath(os.path.dirname(__file__))

    def initUI(self):
        base_dir = self.get_base_dir()
        
        self.setWindowTitle('Alfeonull Local Studio')
        self.setFixedSize(450, 260)
        self.setStyleSheet("background-color: #09090b; color: #f8fafc;")

        # Устанавливаем твою иконку для окна
        icon_path = os.path.join(base_dir, 'icon.png')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)

        title = QLabel('Alfeonull Studio Control')
        title.setFont(QFont('Arial', 18, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        import platform
        exe_ext = '.exe' if platform.system() == 'Windows' else ''
        
        ffmpeg_local = os.path.join(base_dir, 'ffmpeg', f'ffmpeg{exe_ext}')
        ffmpeg_bin = os.path.join(base_dir, 'ffmpeg', 'bin', f'ffmpeg{exe_ext}')
        
        if os.path.exists(ffmpeg_local) or os.path.exists(ffmpeg_bin):
            ffmpeg_status = "✅ Local FFmpeg: Found & Ready"
            c_ffmpeg = "#22c55e"
        elif shutil.which("ffmpeg"):
            ffmpeg_status = "⚠️ System FFmpeg: Found (Local preferred)"
            c_ffmpeg = "#eab308"
        else:
            ffmpeg_status = "❌ Local FFmpeg: Not Found in /ffmpeg"
            c_ffmpeg = "#ef4444"

        melt_paths = [r"C:\Program Files\Shotcut\melt.exe", r"C:\Program Files (x86)\Shotcut\melt.exe", "melt"]
        melt_found = any(os.path.exists(p) for p in melt_paths if p != "melt") or shutil.which("melt")
        if melt_found:
            melt_status = "✅ Shotcut (MELT): Found & Ready"
            c_melt = "#22c55e"
        else:
            melt_status = "❌ Shotcut (MELT): Not Found"
            c_melt = "#ef4444"

        lbl_ffmpeg = QLabel(ffmpeg_status)
        lbl_ffmpeg.setStyleSheet(f"color: {c_ffmpeg}; font-weight: bold; font-size: 13px;")
        layout.addWidget(lbl_ffmpeg)

        lbl_melt = QLabel(melt_status)
        lbl_melt.setStyleSheet(f"color: {c_melt}; font-weight: bold; font-size: 13px;")
        layout.addWidget(lbl_melt)

        layout.addStretch()

        self.btn_open = QPushButton('Launch Studio in Browser')
        self.btn_open.setCursor(Qt.PointingHandCursor)
        self.btn_open.setStyleSheet("""
            QPushButton {
                background-color: #6366f1; color: white; border: none;
                border-radius: 8px; padding: 12px; font-weight: bold; font-size: 14px;
            }
            QPushButton:hover { background-color: #4f46e5; }
        """)
        self.btn_open.clicked.connect(self.open_browser)
        layout.addWidget(self.btn_open)

        self.setLayout(layout)

    def initTray(self):
        base_dir = self.get_base_dir()
        self.tray_icon = QSystemTrayIcon(self)
        
        # Устанавливаем твою иконку в системный трей (возле часов)
        icon_path = os.path.join(base_dir, 'icon.png')
        if os.path.exists(icon_path):
            self.tray_icon.setIcon(QIcon(icon_path))
        else:
            self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))
            
        show_action = QAction("Show Studio Panel", self)
        quit_action = QAction("Exit App", self)
        
        show_action.triggered.connect(self.showNormal)
        quit_action.triggered.connect(QApplication.instance().quit)
        
        tray_menu = QMenu()
        tray_menu.addAction(show_action)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        
        self.tray_icon.activated.connect(self.on_tray_click)

    def on_tray_click(self, reason):
        if reason == QSystemTrayIcon.DoubleClick or reason == QSystemTrayIcon.Trigger:
            self.showNormal()
            self.activateWindow()

    def changeEvent(self, event):
        if event.type() == QEvent.WindowStateChange:
            if self.isMinimized():
                self.hide()
                self.tray_icon.showMessage(
                    "Alfeonull Studio",
                    "Studio is running in the background.",
                    QSystemTrayIcon.Information,
                    2000
                )
                event.ignore()
        super().changeEvent(event)

    def closeEvent(self, event):
        QApplication.instance().quit()

    def open_browser(self):
        webbrowser.open('http://127.0.0.1:5000')

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False) 
    gui = StudioGUI()
    gui.show()
    sys.exit(app.exec_())
