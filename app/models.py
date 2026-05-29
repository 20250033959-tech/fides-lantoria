from app import db, login_manager
from flask_login import UserMixin
from datetime import datetime

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    id       = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80),  unique=True, nullable=False)
    email    = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role     = db.Column(db.String(20),  nullable=False, default='user')
    notes    = db.relationship('Note', backref='author', lazy=True)

    def __repr__(self):
        return f'<User {self.username} ({self.role})>'

class Note(db.Model):
    id             = db.Column(db.Integer, primary_key=True)
    title          = db.Column(db.String(120), nullable=False, default='Untitled')
    content        = db.Column(db.Text, nullable=False)
    image_filename = db.Column(db.String(300), nullable=True)
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)
    user_id        = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f'<Note {self.id} - {self.title}>'