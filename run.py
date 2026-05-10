import os
import sys
import subprocess
import shutil
import webbrowser
import platform
import traceback

# --- 1. АВТОМАТИЧЕСКАЯ УСТАНОВКА ЗАВИСИМОСТЕЙ ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SETUP_MARKER = os.path.join(BASE_DIR, "setup_done.txt")
REQ_FILE = os.path.join(BASE_DIR, "requirements.txt")

if not os.path.exists(SETUP_MARKER):
    # Если это первый запуск, устанавливаем зависимости в фоне
    try:
        if os.path.exists(REQ_FILE):
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", REQ_FILE])
        
        # Создаем файл-метку, чтобы больше не устанавливать
        with open(SETUP_MARKER, "w") as f:
            f.write("Dependencies installed successfully.\n")
            
    except Exception as e:
        # Если что-то пошло не так, пишем лог
        with open(os.path.join(BASE_DIR, "setup_error.txt"), "w") as f:
            f.write(f"Setup failed: {e}\n")
        sys.exit(1)

# --- Теперь безопасно импортируем сторонние библиотеки ---
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QSystemTrayIcon, QMenu, 
                             QAction, QStyle, QFrame, QGraphicsDropShadowEffect)
from PyQt5.QtCore import Qt, QThread, QEvent
from PyQt5.QtGui import QIcon, QCursor, QColor

from app import create_app

# --- 2. ПОТОК ДЛЯ FLASK СЕРВЕРА ---
class FlaskThread(QThread):
    def run(self):
        try:
            # Отключаем вывод Flask в консоль (так как её больше нет)
            import logging
            log = logging.getLogger('werkzeug')
            log.setLevel(logging.ERROR)
            
            app = create_app()
            app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False, threaded=True)
        except Exception as e:
            with open(os.path.join(BASE_DIR, "flask_error.txt"), "w") as f:
                f.write(f"FLASK ERROR: {e}\n")

# --- 3. ГЛАВНЫЙ ИНТЕРФЕЙС (GUI) ---
class StudioGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.flask_thread = FlaskThread()
        self.flask_thread.start()
        
        self.initUI()
        self.initTray()

    def initUI(self):
        self.setWindowTitle('Alfeonull Studio')
        self.setFixedSize(500, 420) 
        
        self.setStyleSheet("""
            QWidget { background-color: #0f172a; font-family: 'Segoe UI', sans-serif; }
            QLabel { color: #f8fafc; }
            QFrame#card { background-color: #1e293b; border: 1px solid #334155; border-radius: 14px; }
        """)

        icon_path = os.path.join(BASE_DIR, 'icon.png')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        layout = QVBoxLayout()
        layout.setContentsMargins(45, 40, 45, 40)
        layout.setSpacing(18)

        title = QLabel('ALFEONULL STUDIO')
        title.setStyleSheet("font-size: 26px; font-weight: 900; letter-spacing: 2px; color: #ffffff;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        status_tag = QLabel('● LOCAL SERVICE ACTIVE')
        status_tag.setStyleSheet("color: #a78bfa; font-size: 11px; font-weight: 800; letter-spacing: 3px;")
        status_tag.setAlignment(Qt.AlignCenter)
        layout.addWidget(status_tag)
        layout.addSpacing(15)

        def create_card(engine_name, status_text, status_color):
            card = QFrame(); card.setObjectName("card")
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(15); shadow.setColor(QColor(0, 0, 0, 80)); shadow.setOffset(0, 4)
            card.setGraphicsEffect(shadow)
            c_lay = QHBoxLayout(card)
            c_lay.setContentsMargins(20, 15, 20, 15)
            e_name = QLabel(engine_name.upper())
            e_name.setStyleSheet("font-size: 13px; font-weight: 800; border: none; color: #cbd5e1;")
            e_stat = QLabel(status_text)
            e_stat.setStyleSheet(f"font-size: 12px; font-weight: 900; border: none; color: {status_color};")
            c_lay.addWidget(e_name); c_lay.addStretch(); c_lay.addWidget(e_stat)
            return card

        def check_engine(name):
            exe = ".exe" if platform.system() == "Windows" else ""
            local = os.path.join(BASE_DIR, name, f"{name}{exe}")
            bin_p = os.path.join(BASE_DIR, name, "bin", f"{name}{exe}")
            if os.path.exists(local) or os.path.exists(bin_p) or shutil.which(name):
                return "READY", "#4ade80" 
            return "MISSING", "#f87171" 

        for engine in ["ffmpeg", "melt"]:
            text, color = check_engine(engine)
            layout.addWidget(create_card(engine, text, color))

        layout.addStretch()

        self.btn = QPushButton('OPEN STUDIO INTERFACE')
        self.btn.setCursor(QCursor(Qt.PointingHandCursor))
        btn_shadow = QGraphicsDropShadowEffect()
        btn_shadow.setBlurRadius(20); btn_shadow.setColor(QColor(99, 102, 241, 100)); btn_shadow.setOffset(0, 5)
        self.btn.setGraphicsEffect(btn_shadow)
        self.btn.setStyleSheet("""
            QPushButton { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6366f1, stop:1 #8b5cf6);
                color: white; border: none; border-radius: 12px; padding: 18px; font-weight: 900; font-size: 13px; }
            QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f46e5, stop:1 #7c3aed); }
        """)
        self.btn.clicked.connect(lambda: webbrowser.open('http://127.0.0.1:5000'))
        layout.addWidget(self.btn)

        self.setLayout(layout)

    def initTray(self):
        self.tray = QSystemTrayIcon(self)
        icon_path = os.path.join(BASE_DIR, 'icon.png')
        if os.path.exists(icon_path):
            self.tray.setIcon(QIcon(icon_path))
        else:
            self.tray.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))
        menu = QMenu()
        show_action = menu.addAction("Show Panel")
        show_action.triggered.connect(self.showNormal)
        exit_action = menu.addAction("Exit Entire App")
        exit_action.triggered.connect(self.safe_exit)
        self.tray.setContextMenu(menu)
        self.tray.show()
        self.tray.activated.connect(self.on_tray_click)

    def on_tray_click(self, reason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self.showNormal()

    def changeEvent(self, event):
        if event.type() == QEvent.WindowStateChange and self.isMinimized():
            self.hide()
        super().changeEvent(event)

    def closeEvent(self, event):
        self.safe_exit()

    def safe_exit(self):
        self.tray.hide()
        QApplication.instance().quit()

if __name__ == '__main__':
    try:
        q_app = QApplication(sys.argv)
        q_app.setQuitOnLastWindowClosed(False)
        gui = StudioGUI()
        gui.show()
        sys.exit(q_app.exec_())
    except Exception as e:
        with open(os.path.join(BASE_DIR, "startup_crash.txt"), "w") as f:
            f.write(traceback.format_exc())
