import sys
import os
import shutil
import webbrowser
import platform
import traceback

# =======================================================
# ФИКС 1: ЗАЩИТА ОТ ВЫЛЕТОВ ПРИ ОТСУТСТВИИ КОНСОЛИ
# Перенаправляем все print() в "пустоту", чтобы программа 
# не крашилась при попытке вывести текст без терминала.
# =======================================================
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QSystemTrayIcon, QMenu, 
                             QAction, QStyle, QFrame)
from PyQt5.QtCore import Qt, QThread, QEvent
from PyQt5.QtGui import QFont, QIcon, QCursor

from app import create_app

# --- Поток для запуска Flask-сервера ---
class FlaskThread(QThread):
    def run(self):
        app = create_app()
        os.makedirs(os.path.join(app.config['BASE_DIR'], 'instance'), exist_ok=True)
        app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)

# --- Главное окно GUI ---
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
        self.setFixedSize(480, 340) 
        
        self.setStyleSheet("""
            QWidget {
                background-color: #09090b; 
                font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, Arial, sans-serif;
            }
        """)

        icon_path = os.path.join(base_dir, 'icon.png')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(40, 35, 40, 35)
        main_layout.setSpacing(20)

        header_layout = QVBoxLayout()
        header_layout.setSpacing(4)
        
        title = QLabel('ALFEONULL STUDIO')
        title.setStyleSheet("color: #ffffff; font-size: 22px; font-weight: 900; letter-spacing: 1.5px;")
        title.setAlignment(Qt.AlignCenter)
        
        subtitle = QLabel('LOCAL RENDER ENGINE')
        subtitle.setStyleSheet("color: #8b5cf6; font-size: 11px; font-weight: 800; letter-spacing: 3px;")
        subtitle.setAlignment(Qt.AlignCenter)
        
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        main_layout.addLayout(header_layout)

        main_layout.addSpacing(10)

        exe_ext = '.exe' if platform.system() == 'Windows' else ''
        
        # FFmpeg
        ffmpeg_local = os.path.join(base_dir, 'ffmpeg', f'ffmpeg{exe_ext}')
        ffmpeg_bin = os.path.join(base_dir, 'ffmpeg', 'bin', f'ffmpeg{exe_ext}')
        
        if os.path.exists(ffmpeg_local) or os.path.exists(ffmpeg_bin):
            ffmpeg_status = "Found & Ready"
            c_ffmpeg = "#22c55e"
            i_ffmpeg = "🟢"
        elif shutil.which("ffmpeg"):
            ffmpeg_status = "System FFmpeg"
            c_ffmpeg = "#eab308"
            i_ffmpeg = "🟡"
        else:
            ffmpeg_status = "Not Found"
            c_ffmpeg = "#ef4444"
            i_ffmpeg = "🔴"

        # Melt
        melt_paths = [
            os.path.join(base_dir, 'melt', f'melt{exe_ext}'),
            os.path.join(base_dir, 'melt', 'bin', f'melt{exe_ext}'),
            r"C:\Program Files\Shotcut\melt.exe", 
            r"C:\Program Files (x86)\Shotcut\melt.exe",
            "/Applications/Shotcut.app/Contents/MacOS/melt",
            "melt"
        ]
        melt_found = any(os.path.exists(p) for p in melt_paths if p != "melt") or shutil.which("melt")
        if melt_found:
            melt_status = "Found & Ready"
            c_melt = "#22c55e"
            i_melt = "🟢"
        else:
            melt_status = "Not Found"
            c_melt = "#ef4444"
            i_melt = "🔴"

        def create_status_card(name, icon, status_text, color):
            card = QFrame()
            card.setStyleSheet("""
                QFrame {
                    background-color: #18181b;
                    border: 1px solid #27272a;
                    border-radius: 12px;
                }
            """)
            card_layout = QHBoxLayout(card)
            card_layout.setContentsMargins(18, 14, 18, 14)

            lbl_name = QLabel(name)
            lbl_name.setStyleSheet("color: #e2e8f0; font-size: 13px; font-weight: 700; border: none; background: transparent;")

            lbl_status = QLabel(f"{icon}  {status_text}")
            lbl_status.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: 800; border: none; background: transparent;")
            lbl_status.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

            card_layout.addWidget(lbl_name)
            card_layout.addWidget(lbl_status)
            return card

        cards_layout = QVBoxLayout()
        cards_layout.setSpacing(12)
        cards_layout.addWidget(create_status_card("FFmpeg Engine", i_ffmpeg, ffmpeg_status, c_ffmpeg))
        cards_layout.addWidget(create_status_card("Melt / Shotcut", i_melt, melt_status, c_melt))
        main_layout.addLayout(cards_layout)

        main_layout.addStretch()

        self.btn_open = QPushButton('LAUNCH IN BROWSER')
        self.btn_open.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_open.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6366f1, stop:1 #8b5cf6);
                color: white; 
                border: none;
                border-radius: 14px; 
                padding: 16px; 
                font-weight: 800; 
                font-size: 13px;
                letter-spacing: 1px;
            }
            QPushButton:hover { 
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f46e5, stop:1 #7c3aed);
            }
            QPushButton:pressed {
                background: #4338ca;
            }
        """)
        self.btn_open.clicked.connect(self.open_browser)
        main_layout.addWidget(self.btn_open)

        self.setLayout(main_layout)

    def initTray(self):
        base_dir = self.get_base_dir()
        self.tray_icon = QSystemTrayIcon(self)
        
        icon_path = os.path.join(base_dir, 'icon.png')
        if os.path.exists(icon_path):
            self.tray_icon.setIcon(QIcon(icon_path))
        else:
            self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))
            
        show_action = QAction("Show Studio Panel", self)
        quit_action = QAction("Exit App", self)
        
        # =======================================================
        # ФИКС 2: ЗАЩИТА СИСТЕМНОГО ТРЕЯ ОТ СБОРЩИКА МУСОРА
        # Добавили "self" в QMenu(self). Теперь меню не удаляется
        # из памяти, и программа больше не будет "молча" вылетать.
        # =======================================================
        self.tray_menu = QMenu(self)
        self.tray_menu.addAction(show_action)
        self.tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(self.tray_menu)
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

def log_crash(e):
    base_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.abspath(os.path.dirname(__file__))
    log_path = os.path.join(base_dir, "crash_log.txt")
    
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(f"CRITICAL ERROR: {str(e)}\n")
        f.write("="*50 + "\n")
        f.write(traceback.format_exc())

if __name__ == '__main__':
    try:
        app = QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(False) 
        gui = StudioGUI()
        gui.show()
        sys.exit(app.exec_())
    except Exception as e:
        log_crash(e)
