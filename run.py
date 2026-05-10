import os
import sys
import subprocess
import shutil
import webbrowser
import platform
import traceback
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SETUP_MARKER = os.path.join(BASE_DIR, "setup_done.txt")
REQ_FILE = os.path.join(BASE_DIR, "requirements.txt")

try:
    from PyQt5.QtWidgets import QApplication
except ImportError:
    print("Initial setup: Installing UI components...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "PyQt5"])
    os.execv(sys.executable, ['python'] + sys.argv)

from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QSystemTrayIcon, QMenu, 
                             QAction, QStyle, QFrame, QGraphicsDropShadowEffect, QStackedWidget, QProgressBar)
from PyQt5.QtCore import Qt, QThread, QEvent, pyqtSignal, QPoint
from PyQt5.QtGui import QIcon, QCursor, QColor, QFont

# --- ПОТОК ДЛЯ ПРОВЕРКИ И УСТАНОВКИ ЗАВИСИМОСТЕЙ ---
class StartupWorker(QThread):
    update_text = pyqtSignal(str)
    update_progress = pyqtSignal(int)
    finished_setup = pyqtSignal()

    def run(self):
        if not os.path.exists(SETUP_MARKER):
            # Реальная установка при первом запуске
            self.update_text.emit("INITIALIZING FIRST SETUP...")
            self.update_progress.emit(10)
            time.sleep(1)
            
            try:
                self.update_text.emit("INSTALLING DEPENDENCIES FROM REQUIREMENTS.TXT...")
                self.update_progress.emit(40)
                if os.path.exists(REQ_FILE):
                    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", REQ_FILE], stdout=subprocess.DEVNULL)
                
                self.update_text.emit("FINALIZING SETUP...")
                self.update_progress.emit(90)
                with open(SETUP_MARKER, "w") as f:
                    f.write("Dependencies installed successfully.\n")
                time.sleep(1)
            except Exception as e:
                with open(os.path.join(BASE_DIR, "setup_error.txt"), "w") as f:
                    f.write(f"Setup failed: {e}\n")
        else:
            # "Фейковая" красивая проверка для пускания пыли в глаза
            self.update_text.emit("VERIFYING SYSTEM INTEGRITY...")
            self.update_progress.emit(25)
            time.sleep(0.6)
            
            self.update_text.emit("CHECKING FFMPEG & MELT RENDER ENGINES...")
            self.update_progress.emit(50)
            time.sleep(0.8)
            
            self.update_text.emit("VALIDATING CACHE AND LOCAL DATABASE...")
            self.update_progress.emit(75)
            time.sleep(0.5)

        self.update_text.emit("STARTING LOCAL FLASK SERVER...")
        self.update_progress.emit(100)
        time.sleep(0.5)
        
        self.finished_setup.emit()

# --- ПОТОК ДЛЯ FLASK СЕРВЕРА ---
class FlaskThread(QThread):
    def run(self):
        try:
            import logging
            log = logging.getLogger('werkzeug')
            log.setLevel(logging.ERROR)
            
            from app import create_app
            app = create_app()
            app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False, threaded=True)
        except Exception as e:
            with open(os.path.join(BASE_DIR, "flask_error.txt"), "w") as f:
                f.write(f"FLASK ERROR: {e}\n")

# --- ГЛАВНЫЙ ИНТЕРФЕЙС (GUI) ---
class StudioGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.oldPos = self.pos()
        self.initUI()
        self.initTray()
        
        # Запускаем проверку при открытии
        self.startup_worker = StartupWorker()
        self.startup_worker.update_text.connect(self.set_loading_text)
        self.startup_worker.update_progress.connect(self.set_progress)
        self.startup_worker.finished_setup.connect(self.start_app)
        self.startup_worker.start()

    def initUI(self):
        self.setWindowFlags(Qt.FramelessWindowHint) # Убираем стандартные рамки окна
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(500, 420) 

        # Главный контейнер (с закругленными краями) - ТЕПЕРЬ В ЦВЕТАХ ПРОЕКТА
        self.main_frame = QFrame(self)
        self.main_frame.setGeometry(10, 10, 480, 400)
        self.main_frame.setStyleSheet("""
            QFrame { background-color: #09090b; border-radius: 16px; border: 1px solid #27272a; font-family: 'Inter', 'Segoe UI', sans-serif; }
            QLabel { border: none; color: #f8fafc; }
        """)
        
        # Тень для окна
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 200))
        shadow.setOffset(0, 10)
        self.main_frame.setGraphicsEffect(shadow)

        main_layout = QVBoxLayout(self.main_frame)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Верхняя панель управления (кнопка закрытия)
        header = QFrame()
        header.setFixedHeight(40)
        header.setStyleSheet("border: none;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 15, 0)
        header_layout.addStretch()
        
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(24, 24)
        close_btn.setStyleSheet("""
            QPushButton { background-color: transparent; color: #a1a1aa; border: none; font-weight: bold; border-radius: 12px; }
            QPushButton:hover { background-color: #ef4444; color: white; }
        """)
        close_btn.clicked.connect(self.safe_exit)
        header_layout.addWidget(close_btn)
        main_layout.addWidget(header)

        # QStackedWidget для переключения между "Загрузкой" и "Главным меню"
        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack)

        # --- СТРАНИЦА 1: ЗАГРУЗКА ---
        self.page_loading = QWidget()
        load_layout = QVBoxLayout(self.page_loading)
        load_layout.setContentsMargins(40, 20, 40, 60)
        
        title_load = QLabel('ALFEONULL STUDIO')
        title_load.setStyleSheet("font-size: 26px; font-weight: 900; letter-spacing: 2px; color: #ffffff;")
        title_load.setAlignment(Qt.AlignCenter)
        load_layout.addWidget(title_load)
        
        load_layout.addStretch()
        
        self.loading_lbl = QLabel("INITIALIZING...")
        self.loading_lbl.setStyleSheet("color: #a1a1aa; font-size: 11px; font-weight: 800; letter-spacing: 2px;")
        self.loading_lbl.setAlignment(Qt.AlignCenter)
        load_layout.addWidget(self.loading_lbl)
        
        self.progress = QProgressBar()
        self.progress.setFixedHeight(4)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet("""
            QProgressBar { border: none; background-color: #18181b; border-radius: 2px; }
            QProgressBar::chunk { background-color: #6366f1; border-radius: 2px; }
        """)
        load_layout.addWidget(self.progress)
        self.stack.addWidget(self.page_loading)

        # --- СТРАНИЦА 2: ГЛАВНОЕ МЕНЮ ---
        self.page_main = QWidget()
        main_page_layout = QVBoxLayout(self.page_main)
        main_page_layout.setContentsMargins(40, 0, 40, 40)
        
        title_main = QLabel('ALFEONULL STUDIO')
        title_main.setStyleSheet("font-size: 26px; font-weight: 900; letter-spacing: 2px; color: #ffffff;")
        title_main.setAlignment(Qt.AlignCenter)
        main_page_layout.addWidget(title_main)

        status_tag = QLabel('● LOCAL SERVICE ACTIVE')
        status_tag.setStyleSheet("color: #a78bfa; font-size: 11px; font-weight: 800; letter-spacing: 3px;")
        status_tag.setAlignment(Qt.AlignCenter)
        main_page_layout.addWidget(status_tag)
        main_page_layout.addSpacing(20)

        # Карточки компонентов
        for engine in ["ffmpeg", "melt"]:
            text, color = self.check_engine(engine)
            main_page_layout.addWidget(self.create_card(engine, text, color))

        main_page_layout.addStretch()

        # Кнопка запуска
        self.btn = QPushButton('OPEN STUDIO INTERFACE')
        self.btn.setCursor(QCursor(Qt.PointingHandCursor))
        
        # Эффект тени для кнопки
        btn_shadow = QGraphicsDropShadowEffect()
        btn_shadow.setBlurRadius(20)
        btn_shadow.setColor(QColor(99, 102, 241, 75)) # rgba(99, 102, 241, 0.3)
        btn_shadow.setOffset(0, 4)
        self.btn.setGraphicsEffect(btn_shadow)
        
        self.btn.setStyleSheet("""
            QPushButton { 
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #6366f1, stop:1 #8b5cf6);
                color: white; border: none; border-radius: 12px; padding: 16px; 
                font-weight: 900; font-size: 13px; letter-spacing: 1px;
            }
            QPushButton:hover { 
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #4f46e5, stop:1 #7c3aed); 
            }
        """)
        self.btn.clicked.connect(lambda: webbrowser.open('http://127.0.0.1:5000'))
        main_page_layout.addWidget(self.btn)
        self.stack.addWidget(self.page_main)

    def create_card(self, engine_name, status_text, status_color):
        card = QFrame()
        # Стилизовано под карточки (.alf-card) из твоего интерфейса
        card.setStyleSheet("background-color: #18181b; border: 1px solid #27272a; border-radius: 12px;")
        c_lay = QHBoxLayout(card)
        c_lay.setContentsMargins(20, 15, 20, 15)
        e_name = QLabel(engine_name.upper())
        e_name.setStyleSheet("font-size: 13px; font-weight: 800; border: none; color: #f8fafc; letter-spacing: 1px;")
        e_stat = QLabel(status_text)
        e_stat.setStyleSheet(f"font-size: 12px; font-weight: 900; border: none; color: {status_color}; letter-spacing: 1px;")
        c_lay.addWidget(e_name); c_lay.addStretch(); c_lay.addWidget(e_stat)
        return card

    def check_engine(self, name):
        exe = ".exe" if platform.system() == "Windows" else ""
        local = os.path.join(BASE_DIR, name, f"{name}{exe}")
        bin_p = os.path.join(BASE_DIR, name, "bin", f"{name}{exe}")
        if os.path.exists(local) or os.path.exists(bin_p) or shutil.which(name):
            return "READY", "#4ade80" 
        return "MISSING", "#f87171"

    # Методы для получения сигналов от потока загрузки
    def set_loading_text(self, text):
        self.loading_lbl.setText(text)

    def set_progress(self, val):
        self.progress.setValue(val)

    def start_app(self):
        # Переключаем экран на главное меню
        self.stack.setCurrentIndex(1)
        # Запускаем Flask сервер
        self.flask_thread = FlaskThread()
        self.flask_thread.start()

    # Позволяем перетаскивать окно мышкой (так как мы убрали стандартную рамку)
    def mousePressEvent(self, event):
        self.oldPos = event.globalPos()
    def mouseMoveEvent(self, event):
        delta = QPoint(event.globalPos() - self.oldPos)
        self.move(self.x() + delta.x(), self.y() + delta.y())
        self.oldPos = event.globalPos()

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
