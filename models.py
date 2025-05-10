from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    progress = db.relationship('Progress', backref='user', lazy=True)
    analytics = db.relationship('Analytics', backref='user', lazy=True)

class Progress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    operation = db.Column(db.String(1), nullable=False)  # +, -, *, /
    difficulty_level = db.Column(db.Integer, nullable=False)
    correct_answers = db.Column(db.Integer, default=0)
    total_attempts = db.Column(db.Integer, default=0)
    last_attempt = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def accuracy(self):
        return (self.correct_answers / self.total_attempts * 100) if self.total_attempts > 0 else 0

class Analytics(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    session_date = db.Column(db.Date, nullable=False)
    questions_attempted = db.Column(db.Integer, default=0)
    correct_answers = db.Column(db.Integer, default=0)
    average_response_time = db.Column(db.Float, default=0.0)
    session_duration = db.Column(db.Integer, default=0)  # in seconds

    @property
    def accuracy(self):
        return (self.correct_answers / self.questions_attempted * 100) if self.questions_attempted > 0 else 0

class LearningPath(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    operation = db.Column(db.String(1), nullable=False)
    current_level = db.Column(db.Integer, default=1)
    target_level = db.Column(db.Integer, default=5)
    completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True) 