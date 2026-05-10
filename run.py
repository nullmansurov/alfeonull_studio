import sys
import os
import shutil
import webbrowser
import platform
import traceback

# --- 1. НАСТРОЙКА ПУТЕЙ И ЛОГИРОВАНИЯ ---
if getattr(sys, 'frozen', False):
    # Если запущен скомпилированный .exe
    BASE_DIR = os.path.dirname(sys.executable)
    # Перенаправляем все сообщения сервера в файл flask_logs.txt
    # Это позволит прочитать ошибку "Internal Server Error"
    log_file = os.path.join(BASE_DIR, "flask_logs.txt")
    sys.stdout = open(log_file, "a", encoding="utf-8")
    sys.stderr = open(log_file, "a", encoding="utf-8")
else:
    # Обычный запуск через python run.py
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QSystemTrayIcon, QMenu, 
                             QAction, QStyle, QFrame)
from PyQt5.QtCore import Qt, QThread, QEvent
from PyQt5.QtGui import QIcon, QCursor

# Импортируем создание приложения из твоей папки app
try:
    from app import create_app
except Exception as e:
    # Если даже импорт не удался, пишем в лог
    with open(os.path.join(BASE_DIR, "critical_error.txt"), "w") as f:
        f.write(f"Import Error: {e}\n")
        f.write(traceback.format_exc())
    sys.exit(1)

# --- 2. ПОТОК ДЛЯ FLASK СЕРВЕРА ---
class FlaskThread(QThread):
    def run(self):
        try:
            print("--- Starting Flask Engine ---")
            app = create_app()
            # Запускаем локально. threaded=True важен для работы с GUI
            app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False, threaded=True)
        except Exception as e:
            print(f"CRITICAL FLASK ERROR: {e}")
            traceback.print_exc()

# --- 3. ГЛАВНЫЙ ИНТЕРФЕЙС (GUI) ---
class StudioGUI(QWidget):
    def __init__(self):
        super().__init__()
        # Запуск сервера "под капотом"
        self.flask_thread = FlaskThread()
        self.flask_thread.start()
        
        self.initUI()
        self.initTray()

    def initUI(self):
        self.setWindowTitle('Alfeonull Studio Control')
        self.setFixedSize(480, 360) 
        
        # Современная темная тема
        self.setStyleSheet("""
            QWidget { background-color: #09090b; font-family: 'Segoe UI', sans-serif; }
            QLabel { color: #f8fafc; }
            QFrame#card { 
                background-color: #18181b; 
                border: 1px solid #27272a; 
                border-radius: 12px; 
            }
        """)

        # Проверка иконки
        icon_path = os.path.join(BASE_DIR, 'icon.png')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        layout = QVBoxLayout()
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(15)

        # Логотип/Заголовок
        title = QLabel('ALFEONULL STUDIO')
        title.setStyleSheet("font-size: 24px; font-weight: 900; letter-spacing: 1px;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        status_tag = QLabel('LOCAL SERVICE ACTIVE')
        status_tag.setStyleSheet("color: #8b5cf6; font-size: 10px; font-weight: 800; letter-spacing: 2px;")
        status_tag.setAlignment(Qt.AlignCenter)
        layout.addWidget(status_tag)
        
        layout.addSpacing(10)

        # Проверка наличия FFmpeg и Melt
        def check_engine(name):
            exe = ".exe" if platform.system() == "Windows" else ""
            local = os.path.join(BASE_DIR, name, f"{name}{exe}")
            bin_p = os.path.join(BASE_DIR, name, "bin", f"{name}{exe}")
            if os.path.exists(local) or os.path.exists(bin_p) or shutil.which(name):
                return "READY", "#22c55e"
            return "MISSING", "#ef4444"

        for engine in ["ffmpeg", "melt"]:
            text, color = check_engine(engine)
            card = QFrame(); card.setObjectName("card")
            c_lay = QHBoxLayout(card)
            
            e_name = QLabel(engine.upper())
            e_name.setStyleSheet("font-weight: bold; border: none;")
            
            e_stat = QLabel(text)
            e_stat.setStyleSheet(f"color: {color}; font-weight: 900; border: none;")
            
            c_lay.addWidget(e_name); c_lay.addStretch(); c_lay.addWidget(e_stat)
            layout.addWidget(card)

        layout.addStretch()

        # Кнопка запуска браузера
        self.btn = QPushButton('OPEN STUDIO INTERFACE')
        self.btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn.setStyleSheet("""
            QPushButton {
                background-color: #6366f1; color: white; border: none; 
                border-radius: 10px; padding: 16px; font-weight: bold; font-size: 13px;
            }
            QPushButton:hover { background-color: #4f46e5; }
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
