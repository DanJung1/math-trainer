from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    google_id = db.Column(db.String(100), unique=True, nullable=True)
    profile_picture = db.Column(db.String(200), nullable=True)
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

    # Index for faster queries
    __table_args__ = (
        db.Index('idx_progress_user_operation', 'user_id', 'operation'),
    )

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

    # Index for faster queries
    __table_args__ = (
        db.Index('idx_analytics_user_date', 'user_id', 'session_date'),
    )

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

    # Index for faster queries
    __table_args__ = (
        db.Index('idx_learning_path_user_operation', 'user_id', 'operation'),
    )

class LeaderboardScore(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    mode = db.Column(db.String(20), nullable=False)  # 'standard' or 'marathon'
    score = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    user = db.relationship('User', backref='leaderboard_scores')
    
    # Indexes for better performance
    __table_args__ = (
        db.Index('idx_leaderboard_mode_score', 'mode', 'score'),  # For leaderboard queries
        db.Index('idx_leaderboard_user_mode', 'user_id', 'mode'),  # For user score lookups
        db.Index('idx_leaderboard_created_at', 'created_at'),  # For time-based queries
    )

class Duel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.String(50), unique=True, nullable=False)
    player1_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    player2_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    status = db.Column(db.String(20), default='waiting')  # waiting, active, completed
    current_question = db.Column(db.String(100), nullable=True)
    current_answer = db.Column(db.Integer, nullable=True)
    question_start_time = db.Column(db.DateTime, nullable=True)
    round_number = db.Column(db.Integer, default=1)
    max_rounds = db.Column(db.Integer, default=10)
    time_limit = db.Column(db.Integer, default=30)  # seconds per question
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    player1 = db.relationship('User', foreign_keys=[player1_id], backref='duels_as_player1')
    player2 = db.relationship('User', foreign_keys=[player2_id], backref='duels_as_player2')
    
    # Indexes for better performance
    __table_args__ = (
        db.Index('idx_duel_room_id', 'room_id'),
        db.Index('idx_duel_status', 'status'),
        db.Index('idx_duel_players', 'player1_id', 'player2_id'),
    )

class DuelScore(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    duel_id = db.Column(db.Integer, db.ForeignKey('duel.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    score = db.Column(db.Integer, default=0)
    correct_answers = db.Column(db.Integer, default=0)
    total_answers = db.Column(db.Integer, default=0)
    average_response_time = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    duel = db.relationship('Duel', backref='scores')
    user = db.relationship('User', backref='duel_scores')
    
    # Indexes for better performance
    __table_args__ = (
        db.Index('idx_duel_score_duel_user', 'duel_id', 'user_id'),
        db.Index('idx_duel_score_user', 'user_id'),
    ) 