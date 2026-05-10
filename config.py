import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = 'LOCAL_STUDIO_SECRET_KEY_NO_NEED_TO_CHANGE'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'instance', 'app.db')
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