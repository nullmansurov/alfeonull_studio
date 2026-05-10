from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import Config
import os

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    for path in [app.config['UPLOAD_FOLDER'], app.config['STOCK_FOLDER'], 
                 app.config['TEMPLATES_DATA_DIR'], app.config['RENDER_TMP_DIR'], 
                 app.config['CACHE_DIR'], os.path.join(app.instance_path)]:
        os.makedirs(path, exist_ok=True)

    db.init_app(app)

    @app.template_filter('youtube_embed')
    def youtube_embed_filter(url):
        if not url: return ""
        try:
            if "watch?v=" in url: return f"https://www.youtube.com/embed/{url.split('watch?v=')[1].split('&')[0]}"
            if "youtu.be/" in url: return f"https://www.youtube.com/embed/{url.split('youtu.be/')[1].split('?')[0]}"
        except: return url
        return url
        
    @app.template_filter('youtube_thumb')
    def youtube_thumb_filter(url):
        if not url: return ""
        try:
            vid_id = ""
            if "watch?v=" in url: vid_id = url.split("watch?v=")[1].split("&")[0]
            elif "youtu.be/" in url: vid_id = url.split("youtu.be/")[1].split("?")[0]
            if vid_id: return f"https://img.youtube.com/vi/{vid_id}/mqdefault.jpg"
        except: pass
        return ""

    from .routes_main import main_bp
    app.register_blueprint(main_bp)
    
    from flask import render_template
    @app.errorhandler(404)
    def page_not_found(e): return render_template('404.html'), 404

    with app.app_context():
        from . import models
        db.create_all()
        if not models.LocalUser.query.first():
            local_user = models.LocalUser(name='Local Studio User')
            db.session.add(local_user)
            db.session.commit()

    from .services.render_engine import RenderWorker
    worker = RenderWorker(app)
    worker.start()

    return app
