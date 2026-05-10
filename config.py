import os
import sys

# Магия для PyInstaller: определяем, скомпилировано ли приложение
if getattr(sys, 'frozen', False):
    # Если это скомпилированный .exe, берем папку, где лежит сам .exe
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # Иначе берем папку, где лежит скрипт (обычный запуск)
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# ИСПРАВЛЕНИЕ: Меняем обратные слеши на прямые для SQLite
db_path = os.path.join(BASE_DIR, 'instance', 'app.db').replace('\\', '/')

class Config:
    SECRET_KEY = 'LOCAL_STUDIO_SECRET_KEY_NO_NEED_TO_CHANGE'
    
    # Жестко привязываем базу данных
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + db_path
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    BASE_DIR = BASE_DIR
    STATIC_FOLDER = os.path.join(BASE_DIR, 'app', 'static')
    UPLOAD_FOLDER = os.path.join(STATIC_FOLDER, 'uploads')
    STOCK_FOLDER = os.path.join(STATIC_FOLDER, 'stock')
    TEMPLATES_DATA_DIR = os.path.join(BASE_DIR, 'app', 'presets_data')
    RENDER_TMP_DIR = os.path.join(STATIC_FOLDER, 'renders')
    CACHE_DIR = os.path.join(BASE_DIR, 'app', 'cache')
    
    PRESETS_PER_PAGE = 20
    HISTORY_PER_PAGE = 15
    STOCK_PER_PAGE = 24
