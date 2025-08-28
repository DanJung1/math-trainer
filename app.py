from flask import Flask, render_template, request, jsonify, session
import random
import os
from datetime import datetime, timedelta
from models import db, User, Progress, Analytics, LearningPath, LeaderboardScore
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'  # Change this in production
# Use in-memory database for Vercel (serverless) or file-based for local development
if os.environ.get('VERCEL'):
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///math_trainer.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

class QuestionGenerator:
    def __init__(self):
        self.used_questions = set()

    def generate_question(self, mode='dynamic'):
        while True:
            operation = random.choice(['+', '-', '*', '/'])

            if operation == '+':
                a, b = random.randint(10, 99), random.randint(10, 99)
            elif operation == '-':
                a = random.randint(10, 99)
                b = random.randint(1, a)
            elif operation == '*':
                a, b = random.randint(2, 12), random.randint(2, 12)
            else:
                b = random.randint(2, 12)
                a = b * random.randint(1, 12)

            question_str = f'{a} {operation} {b}'
            if question_str not in self.used_questions:
                self.used_questions.add(question_str)
                return question_str, eval(question_str)

            if len(self.used_questions) > 100:
                self.used_questions.clear()

class AdaptiveQuestionGenerator:
    def __init__(self):
        self.history = {'+': [], '-': [], '*': [], '/': []}

    def generate_question(self):
        # Determine the operation the user struggles with the most
        operation = min(self.history, key=lambda op: sum(self.history[op][-10:]))

        if operation == '+':
            a, b = random.randint(10, 99), random.randint(10, 99)
        elif operation == '-':
            a = random.randint(10, 99)
            b = random.randint(1, a)
        elif operation == '*':
            a, b = random.randint(2, 12), random.randint(2, 12)
        else:  # division
            b = random.randint(2, 12)
            a = b * random.randint(1, 12)

        return f'{a} {operation} {b}', eval(f'{a} {operation} {b}')

    def update_history(self, operation, correct):
        self.history[operation].append(correct)

class MentalMathTrainer:
    def __init__(self):
        self.correct_answers = 0
        self.generator = QuestionGenerator()
        self.session_start_time = datetime.now()
        self.response_times = []

    def check_answer(self, user_answer, correct_answer, operation, response_time):
        is_correct = user_answer == correct_answer
        if is_correct:
            self.correct_answers += 1
        
        # Update progress in database only if user is logged in
        if 'user_id' in session:
            progress = Progress.query.filter_by(
                user_id=session['user_id'],
                operation=operation
            ).first()
            
            if not progress:
                progress = Progress(
                    user_id=session['user_id'],
                    operation=operation,
                    difficulty_level=1,
                    total_attempts=0,
                    correct_answers=0
                )
                db.session.add(progress)
            
            if progress.total_attempts is None:
                progress.total_attempts = 0
            if progress.correct_answers is None:
                progress.correct_answers = 0
            
            progress.total_attempts += 1
            if is_correct:
                progress.correct_answers += 1
            progress.last_attempt = datetime.utcnow()
            
            # Update analytics
            today = datetime.utcnow().date()
            analytics = Analytics.query.filter_by(
                user_id=session['user_id'],
                session_date=today
            ).first()
            
            if not analytics:
                analytics = Analytics(
                    user_id=session['user_id'],
                    session_date=today,
                    questions_attempted=0,
                    correct_answers=0,
                    average_response_time=0.0,
                    session_duration=0
                )
                db.session.add(analytics)
            
            if analytics.questions_attempted is None:
                analytics.questions_attempted = 0
            if analytics.correct_answers is None:
                analytics.correct_answers = 0
            if analytics.average_response_time is None:
                analytics.average_response_time = 0.0
            if analytics.session_duration is None:
                analytics.session_duration = 0
            
            analytics.questions_attempted += 1
            if is_correct:
                analytics.correct_answers += 1
            
            self.response_times.append(response_time)
            analytics.average_response_time = sum(self.response_times) / len(self.response_times)
            analytics.session_duration = (datetime.now() - self.session_start_time).seconds
            
            db.session.commit()
        
        return is_correct

trainer = MentalMathTrainer()

@app.route('/')
def menu():
    return render_template('menu.html')

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'})

@app.route('/dynamic')
def dynamic():
    return render_template('dynamic.html')

@app.route('/training')
def training():
    operation = request.args.get('operation', '+')
    return render_template('training.html', operation=operation)

@app.route('/marathon')
def marathon():
    return render_template('marathon.html')

@app.route('/analytics')
def analytics():
    if 'user_id' not in session:
        return render_template('analytics.html', progress=[], analytics=[])
    
    user = User.query.get(session['user_id'])
    progress_data = Progress.query.filter_by(user_id=user.id).all()
    analytics_data = Analytics.query.filter_by(user_id=user.id).order_by(Analytics.session_date.desc()).limit(7).all()
    
    # Convert analytics_data to a list of dicts for JSON serialization
    analytics_dicts = [
        {
            'session_date': a.session_date.strftime('%Y-%m-%d'),
            'questions_attempted': a.questions_attempted,
            'correct_answers': a.correct_answers,
            'average_response_time': a.average_response_time,
            'session_duration': a.session_duration,
            'accuracy': a.accuracy
        }
        for a in analytics_data
    ]
    
    return render_template('analytics.html', 
                         progress=progress_data,
                         analytics=analytics_dicts)

@app.route('/learning-path')
def learning_path():
    if 'user_id' not in session:
        return render_template('learning_path.html', paths=[])
    
    user = User.query.get(session['user_id'])
    learning_paths = LearningPath.query.filter_by(user_id=user.id).all()
    
    # Generate new learning paths if none exist
    if not learning_paths:
        for operation in ['+', '-', '*', '/']:
            path = LearningPath(
                user_id=user.id,
                operation=operation
            )
            db.session.add(path)
        db.session.commit()
        learning_paths = LearningPath.query.filter_by(user_id=user.id).all()
    
    return render_template('learning_path.html', paths=learning_paths)

@app.route('/get_question', methods=['GET'])
def get_question():
    mode = request.args.get('mode', 'dynamic')
    question, answer = trainer.generator.generate_question(mode)
    return jsonify({'question': question, 'answer': answer})

@app.route('/check_answer', methods=['POST'])
def check_answer():
    data = request.json
    user_answer = int(data['user_answer'])
    correct_answer = int(data['correct_answer'])
    operation = data.get('operation', '+')
    response_time = float(data.get('response_time', 0))

    is_correct = trainer.check_answer(user_answer, correct_answer, operation, response_time)

    return jsonify({
        'is_correct': is_correct,
        'correct_answers': trainer.correct_answers,
    })

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    
    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Username already exists'}), 400
    
    user = User(username=username)
    db.session.add(user)
    db.session.commit()
    
    session['user_id'] = user.id
    return jsonify({'message': 'Registration successful'})

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    session['user_id'] = user.id
    return jsonify({'message': 'Login successful'})

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    return jsonify({'message': 'Logout successful'})

@app.route('/check-auth-status')
def check_auth_status():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user:
            return jsonify({'logged_in': True, 'username': user.username, 'user_id': user.id})
    return jsonify({'logged_in': False})

@app.route('/leaderboard')
def leaderboard():
    return render_template('leaderboard.html')

@app.route('/api/leaderboard/<mode>')
def get_leaderboard(mode):
    if mode not in ['standard', 'marathon']:
        return jsonify({'error': 'Invalid mode'}), 400
    
    # Get top scores for the mode
    scores = LeaderboardScore.query.filter_by(mode=mode)\
        .order_by(LeaderboardScore.score.desc())\
        .limit(50)\
        .all()
    
    entries = []
    for i, score in enumerate(scores, 1):
        entries.append({
            'rank': i,
            'user_id': score.user_id,
            'username': score.user.username,
            'score': score.score
        })
    
    return jsonify({'entries': entries})

@app.route('/api/submit-score', methods=['POST'])
def submit_score():
    if 'user_id' not in session:
        return jsonify({'error': 'User not logged in'}), 401
    
    data = request.json
    mode = data.get('mode')
    score = data.get('score')
    
    if mode not in ['standard', 'marathon'] or not isinstance(score, int):
        return jsonify({'error': 'Invalid data'}), 400
    
    # Save the score
    leaderboard_score = LeaderboardScore(
        user_id=session['user_id'],
        mode=mode,
        score=score
    )
    db.session.add(leaderboard_score)
    db.session.commit()
    
    return jsonify({'message': 'Score submitted successfully'})

# Create database tables (only if not in production/vercel)
import os
if not os.environ.get('VERCEL'):
    with app.app_context():
        db.create_all()

if __name__ == '__main__':
    app.run(debug=True)