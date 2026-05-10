from . import db
from datetime import datetime
import json

favorites = db.Table('favorites',
    db.Column('user_id', db.Integer, db.ForeignKey('local_user.id'), primary_key=True),
    db.Column('preset_id', db.Integer, db.ForeignKey('preset.id'), primary_key=True)
)

class LocalUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), default="Local User")
    fav_presets = db.relationship('Preset', secondary=favorites, lazy='dynamic', backref=db.backref('favorited_by', lazy='dynamic'))

class Preset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    code = db.Column(db.String(50), unique=True)
    is_hidden = db.Column(db.Boolean, default=False) 
    youtube_url = db.Column(db.String(200), nullable=True)
    folder_path = db.Column(db.String(200))
    notes = db.Column(db.Text, nullable=True)
    config_json = db.Column(db.Text, default='{}') 
    def get_config(self):
        try: return json.loads(self.config_json)
        except: return {}

class StockImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    filename = db.Column(db.String(200))
    tags = db.Column(db.String(200))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {'id': self.id, 'name': self.name, 'filename': self.filename, 'tags': self.tags, 'url': f'/static/stock/{self.filename}'}

class RenderJob(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_uuid = db.Column(db.String(36), unique=True, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('local_user.id'))
    preset_name = db.Column(db.String(100))
    status = db.Column(db.String(20), default='queued')
    filename = db.Column(db.String(200), nullable=True)
    error_msg = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    user = db.relationship('LocalUser', backref='renders')