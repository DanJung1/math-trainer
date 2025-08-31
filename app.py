from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import random
import os
import uuid
from datetime import datetime, timedelta
from models import db, User, Progress, Analytics, LearningPath, LeaderboardScore, Duel, DuelScore
import json
from google.oauth2 import id_token
from google.auth.transport import requests
from google_auth_oauthlib.flow import Flow
from pip._vendor import cachecontrol
import google.auth.transport.requests
import pathlib
import requests as http_requests
from config import config
from flask_socketio import SocketIO, emit, join_room, leave_room

# Determine configuration based on environment
config_name = os.environ.get('FLASK_CONFIG') or 'default'
app = Flask(__name__)
app.config.from_object(config[config_name])

# Apply configuration
config[config_name].init_app(app)

# Initialize SocketIO for WebSocket support
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Google OAuth Configuration
GOOGLE_CLIENT_ID = app.config['GOOGLE_CLIENT_ID']
GOOGLE_CLIENT_SECRET = app.config['GOOGLE_CLIENT_SECRET']
client_secrets_file = os.path.join(pathlib.Path(__file__).parent, "client_secret.json")

# Add response headers for better performance
@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

db.init_app(app)

class QuestionGenerator:
    def __init__(self):
        self.used_questions = set()

    def generate_question(self, mode='dynamic', operations=None, min_range=1, max_range=100):
        if operations is None:
            operations = ['+', '-', '*', '/']
        
        while True:
            operation = random.choice(operations)

            if operation == '+':
                # Addition: both numbers from 2 to 100
                a, b = random.randint(2, 100), random.randint(2, 100)
            elif operation == '-':
                # Subtraction: addition in reverse (2 to 100)
                a = random.randint(2, 100)
                b = random.randint(2, a)  # Ensure b <= a for positive result
            elif operation == '*':
                # Multiplication: first number 2-12, second number 2-100
                a = random.randint(2, 12)
                b = random.randint(2, 100)
            else:  # division
                # Division: multiplication in reverse
                # First choose b (divisor) from 2-12
                b = random.randint(2, 12)
                # Then choose a multiplier from 2-100 to get a
                multiplier = random.randint(2, 100)
                a = b * multiplier

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
        
        # Only update database if user is logged in and not on Vercel (to reduce latency)
        if 'user_id' in session and not os.environ.get('VERCEL'):
            try:
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
            except Exception as e:
                # Silently fail on database errors to prevent UI lag
                print(f"Database error: {e}")
        
        return is_correct

trainer = MentalMathTrainer()

# Duel Management System
class DuelManager:
    def __init__(self):
        self.active_duels = {}  # {room_id: duel_data}
        self.player_rooms = {}  # {user_id: room_id}
    
    def create_duel(self, player1_id, time_limit=30, max_rounds=10):
        """Create a new duel and return room_id"""
        room_id = str(uuid.uuid4())[:8]
        
        # Create duel in database
        duel = Duel(
            room_id=room_id,
            player1_id=player1_id,
            status='waiting',
            time_limit=time_limit,
            max_rounds=max_rounds
        )
        db.session.add(duel)
        
        # Create score records
        score1 = DuelScore(duel_id=duel.id, user_id=player1_id)
        db.session.add(score1)
        
        db.session.commit()
        
        # Store in memory for quick access
        self.active_duels[room_id] = {
            'duel_id': duel.id,
            'player1_id': player1_id,
            'player2_id': None,
            'status': 'waiting',
            'current_question': None,
            'current_answer': None,
            'round_number': 1,
            'max_rounds': max_rounds,
            'time_limit': time_limit,
            'scores': {player1_id: 0},
            'question_start_time': None
        }
        
        self.player_rooms[player1_id] = room_id
        return room_id
    
    def join_duel(self, room_id, player2_id):
        """Join an existing duel"""
        if room_id not in self.active_duels:
            return False, "Duel not found"
        
        duel_data = self.active_duels[room_id]
        if duel_data['status'] != 'waiting':
            return False, "Duel already started"
        
        if duel_data['player2_id'] is not None:
            return False, "Duel is full"
        
        # Update database
        duel = Duel.query.filter_by(room_id=room_id).first()
        if duel:
            duel.player2_id = player2_id
            duel.status = 'active'
            
            # Create score record for player 2
            score2 = DuelScore(duel_id=duel.id, user_id=player2_id)
            db.session.add(score2)
            
            db.session.commit()
        
        # Update memory
        duel_data['player2_id'] = player2_id
        duel_data['status'] = 'active'
        duel_data['scores'][player2_id] = 0
        self.player_rooms[player2_id] = room_id
        
        return True, "Joined duel successfully"
    
    def start_round(self, room_id):
        """Start a new round with a new question"""
        if room_id not in self.active_duels:
            return None
        
        duel_data = self.active_duels[room_id]
        if duel_data['status'] != 'active':
            return None
        
        # Generate new question
        question, answer = trainer.generator.generate_question()
        
        # Update database
        duel = Duel.query.filter_by(room_id=room_id).first()
        if duel:
            duel.current_question = question
            duel.current_answer = answer
            duel.question_start_time = datetime.utcnow()
            db.session.commit()
        
        # Update memory
        duel_data['current_question'] = question
        duel_data['current_answer'] = answer
        duel_data['question_start_time'] = datetime.utcnow()
        
        return {
            'question': question,
            'answer': answer,
            'round': duel_data['round_number'],
            'time_limit': duel_data['time_limit']
        }
    
    def submit_answer(self, room_id, user_id, answer, response_time):
        """Submit an answer and return result"""
        if room_id not in self.active_duels:
            return None
        
        duel_data = self.active_duels[room_id]
        if duel_data['status'] != 'active':
            return None
        
        if user_id not in duel_data['scores']:
            return None
        
        # Check if answer is correct
        is_correct = answer == duel_data['current_answer']
        
        # Calculate points based on speed and correctness
        points = 0
        if is_correct:
            time_taken = response_time
            if time_taken < 5:
                points = 100
            elif time_taken < 10:
                points = 75
            elif time_taken < 15:
                points = 50
            else:
                points = 25
            
            duel_data['scores'][user_id] += points
        
        # Update database
        duel_score = DuelScore.query.filter_by(
            duel_id=duel_data['duel_id'],
            user_id=user_id
        ).first()
        
        if duel_score:
            duel_score.total_answers += 1
            if is_correct:
                duel_score.correct_answers += 1
                duel_score.score += points
            
            # Update average response time
            if duel_score.average_response_time == 0:
                duel_score.average_response_time = response_time
            else:
                duel_score.average_response_time = (
                    (duel_score.average_response_time + response_time) / 2
                )
            
            db.session.commit()
        
        return {
            'correct': is_correct,
            'points': points,
            'total_score': duel_data['scores'][user_id],
            'response_time': response_time
        }
    
    def end_round(self, room_id):
        """End current round and prepare for next"""
        if room_id not in self.active_duels:
            return None
        
        duel_data = self.active_duels[room_id]
        duel_data['round_number'] += 1
        
        # Check if duel is complete
        if duel_data['round_number'] > duel_data['max_rounds']:
            return self.end_duel(room_id)
        
        return {
            'round': duel_data['round_number'],
            'scores': duel_data['scores']
        }
    
    def end_duel(self, room_id):
        """End the duel and return final results"""
        if room_id not in self.active_duels:
            return None
        
        duel_data = self.active_duels[room_id]
        
        # Update database
        duel = Duel.query.filter_by(room_id=room_id).first()
        if duel:
            duel.status = 'completed'
            duel.completed_at = datetime.utcnow()
            db.session.commit()
        
        # Determine winner
        scores = duel_data['scores']
        winner_id = max(scores, key=scores.get) if scores else None
        
        # Clean up memory
        for user_id in [duel_data['player1_id'], duel_data['player2_id']]:
            if user_id in self.player_rooms:
                del self.player_rooms[user_id]
        
        result = {
            'status': 'completed',
            'winner': winner_id,
            'final_scores': scores,
            'total_rounds': duel_data['round_number'] - 1
        }
        
        del self.active_duels[room_id]
        return result

# Global duel manager instance
duel_manager = DuelManager()

@app.route('/')
def menu():
    return render_template('menu.html')

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'})

@app.route('/setup-db')
def setup_database():
    """Initialize database tables for production deployment"""
    try:
        with app.app_context():
            db.create_all()
            return jsonify({
                'status': 'success',
                'message': 'Database initialized successfully',
                'tables': ['User', 'Progress', 'Analytics', 'LearningPath', 'LeaderboardScore', 'Duel', 'DuelScore']
            })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Database initialization failed: {str(e)}'
        }), 500

# Duel Routes
@app.route('/duel')
def duel():
    if 'user_id' not in session:
        return redirect(url_for('menu'))
    return render_template('duel.html')

@app.route('/api/duel/create', methods=['POST'])
def create_duel():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    data = request.json
    time_limit = data.get('time_limit', 30)
    max_rounds = data.get('max_rounds', 10)
    
    room_id = duel_manager.create_duel(session['user_id'], time_limit, max_rounds)
    
    return jsonify({
        'room_id': room_id,
        'message': 'Duel created successfully'
    })

@app.route('/api/duel/join/<room_id>', methods=['POST'])
def join_duel(room_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    success, message = duel_manager.join_duel(room_id, session['user_id'])
    
    if success:
        return jsonify({'message': message})
    else:
        return jsonify({'error': message}), 400

@app.route('/api/duel/<room_id>/status')
def get_duel_status(room_id):
    if room_id not in duel_manager.active_duels:
        return jsonify({'error': 'Duel not found'}), 404
    
    duel_data = duel_manager.active_duels[room_id]
    return jsonify({
        'status': duel_data['status'],
        'player1_id': duel_data['player1_id'],
        'player2_id': duel_data['player2_id'],
        'scores': duel_data['scores'],
        'round': duel_data['round_number'],
        'max_rounds': duel_data['max_rounds']
    })

# WebSocket Event Handlers
@socketio.on('connect')
def handle_connect():
    print(f'Client connected: {request.sid}')
    emit('connected', {'message': 'Connected to server'})

@socketio.on('disconnect')
def handle_disconnect():
    print(f'Client disconnected: {request.sid}')
    # Clean up if user was in a duel
    # This would need more sophisticated user tracking

@socketio.on('join_duel_room')
def handle_join_duel_room(data):
    room_id = data['room_id']
    user_id = data['user_id']
    
    join_room(room_id)
    print(f'User {user_id} joined duel room {room_id}')
    
    # Notify other players in the room
    emit('player_joined', {
        'user_id': user_id,
        'message': 'Player joined the duel'
    }, room=room_id, include_self=False)

@socketio.on('start_duel')
def handle_start_duel(data):
    room_id = data['room_id']
    
    # Start the first round
    round_data = duel_manager.start_round(room_id)
    if round_data:
        emit('round_started', round_data, room=room_id)
        print(f'Round started in duel {room_id}: {round_data["question"]}')

@socketio.on('submit_answer')
def handle_submit_answer(data):
    room_id = data['room_id']
    user_id = data['user_id']
    answer = data['answer']
    response_time = data['response_time']
    
    # Process the answer
    result = duel_manager.submit_answer(room_id, user_id, answer, response_time)
    
    if result:
        # Send result to the submitting player
        emit('answer_result', result)
        
        # Notify other players about the answer submission
        emit('opponent_answered', {
            'user_id': user_id,
            'correct': result['correct'],
            'points': result['points']
        }, room=room_id, include_self=False)
        
        # Check if both players have answered
        duel_data = duel_manager.active_duels.get(room_id)
        if duel_data and duel_data['status'] == 'active':
            # End round after a short delay to show results
            socketio.sleep(2)
            round_result = duel_manager.end_round(room_id)
            if round_result:
                if round_result.get('status') == 'completed':
                    emit('duel_ended', round_result, room=room_id)
                else:
                    # Start next round
                    next_round = duel_manager.start_round(room_id)
                    if next_round:
                        emit('round_started', next_round, room=room_id)

@socketio.on('leave_duel')
def handle_leave_duel(data):
    room_id = data['room_id']
    user_id = data['user_id']
    
    leave_room(room_id)
    emit('player_left', {
        'user_id': user_id,
        'message': 'Player left the duel'
    }, room=room_id)

@app.errorhandler(403)
def forbidden(error):
    return redirect(url_for('menu'))

@app.route('/dynamic')
def dynamic():
    return render_template('dynamic.html')

@app.route('/training-config')
def training_config():
    return render_template('training_config.html')

@app.route('/training')
def training():
    return render_template('training.html')

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
    
    if mode == 'training':
        # Get training configuration from request parameters
        operations = request.args.get('operations', '').split(',') if request.args.get('operations') else None
        min_range = int(request.args.get('min_range', 1))
        max_range = int(request.args.get('max_range', 100))
        
        # Filter out empty strings and convert to list
        if operations:
            operations = [op for op in operations if op]
        
        question, answer = trainer.generator.generate_question(
            mode, 
            operations=operations, 
            min_range=min_range, 
            max_range=max_range
        )
    else:
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
    print(f"Check auth status - session: {session}")
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user:
            print(f"User found: {user.username}")
            # Check if user has a temporary username (needs to set a real one)
            needs_username = user.username.startswith('User') and user.username[4:].isdigit()
            return jsonify({
                'logged_in': True, 
                'username': user.username, 
                'user_id': user.id,
                'email': user.email,
                'profile_picture': user.profile_picture,
                'needs_username': needs_username
            })
        else:
            print(f"User not found for ID: {session['user_id']}")
    else:
        print("No user_id in session")
    return jsonify({'logged_in': False})

@app.route('/api/update-username', methods=['POST'])
def update_username():
    if 'user_id' not in session:
        return jsonify({'error': 'User not logged in'}), 401
    
    data = request.json
    new_username = data.get('username', '').strip()
    
    if not new_username:
        return jsonify({'error': 'Username cannot be empty'}), 400
    
    if len(new_username) > 20:
        return jsonify({'error': 'Username too long (max 20 characters)'}), 400
    
    # Check if username is already taken
    existing_user = User.query.filter_by(username=new_username).first()
    if existing_user and existing_user.id != session['user_id']:
        return jsonify({'error': 'Username already taken'}), 400
    
    # Update the user's username
    user = User.query.get(session['user_id'])
    if user:
        user.username = new_username
        db.session.commit()
        return jsonify({'success': True, 'username': new_username})
    else:
        return jsonify({'error': 'User not found'}), 404

@app.route('/leaderboard')
def leaderboard():
    return render_template('leaderboard.html')

@app.route('/api/leaderboard/<mode>')
def get_leaderboard(mode):
    if mode not in ['standard', 'marathon']:
        return jsonify({'error': 'Invalid mode'}), 400
    
    try:
        # Get top scores for the mode with pagination support
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        
        # Limit per_page to prevent abuse
        per_page = min(per_page, 100)
        
        scores = LeaderboardScore.query.filter_by(mode=mode)\
            .order_by(LeaderboardScore.score.desc(), LeaderboardScore.created_at.asc())\
            .paginate(page=page, per_page=per_page, error_out=False)
        
        entries = []
        for i, score in enumerate(scores.items, (page - 1) * per_page + 1):
            entries.append({
                'rank': i,
                'user_id': score.user_id,
                'username': score.user.username,
                'score': score.score,
                'created_at': score.created_at.isoformat() if score.created_at else None
            })
        
        # Get current user ID if logged in
        current_user_id = session.get('user_id') if 'user_id' in session else None
        
        return jsonify({
            'entries': entries,
            'current_user_id': current_user_id,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': scores.total,
                'pages': scores.pages,
                'has_next': scores.has_next,
                'has_prev': scores.has_prev
            }
        })
    except Exception as e:
        print(f"Leaderboard error: {e}")
        return jsonify({'error': 'Failed to load leaderboard'}), 500

@app.route('/api/submit-score', methods=['POST'])
def submit_score():
    if 'user_id' not in session:
        return jsonify({'error': 'User not logged in'}), 401
    
    try:
        data = request.json
        mode = data.get('mode')
        score = data.get('score')
        
        if mode not in ['standard', 'marathon'] or not isinstance(score, int):
            return jsonify({'error': 'Invalid data'}), 400
        
        # Validate score range (prevent abuse)
        if score < 0 or score > 10000:  # Reasonable upper limit
            return jsonify({'error': 'Invalid score value'}), 400
        
        # Check if user already has a score for this mode
        existing_score = LeaderboardScore.query.filter_by(
            user_id=session['user_id'], 
            mode=mode
        ).first()
        
        if existing_score:
            # Update existing score if new score is higher
            if score > existing_score.score:
                existing_score.score = score
                existing_score.created_at = datetime.utcnow()  # Update timestamp
                db.session.commit()
                return jsonify({
                    'message': 'Score updated successfully',
                    'previous_score': existing_score.score,
                    'new_score': score
                })
            else:
                return jsonify({
                    'message': 'Score not updated (lower than existing)',
                    'current_score': existing_score.score,
                    'attempted_score': score
                })
        else:
            # Create new score
            leaderboard_score = LeaderboardScore(
                user_id=session['user_id'],
                mode=mode,
                score=score
            )
            db.session.add(leaderboard_score)
            db.session.commit()
            return jsonify({
                'message': 'Score submitted successfully',
                'score': score
            })
    except Exception as e:
        db.session.rollback()
        print(f"Score submission error: {e}")
        return jsonify({'error': 'Failed to submit score'}), 500

# Google OAuth Routes
@app.route('/google-login')
def google_login():
    flow = Flow.from_client_secrets_file(
        client_secrets_file=client_secrets_file,
        scopes=["https://www.googleapis.com/auth/userinfo.profile", "https://www.googleapis.com/auth/userinfo.email", "openid"],
        redirect_uri="http://localhost:5001/callback"
    )
    
    authorization_url, state = flow.authorization_url()
    session["state"] = state
    
    return redirect(authorization_url)

@app.route('/callback')
def callback():
    try:
        print("OAuth callback started")
        flow = Flow.from_client_secrets_file(
            client_secrets_file=client_secrets_file,
            scopes=["https://www.googleapis.com/auth/userinfo.profile", "https://www.googleapis.com/auth/userinfo.email", "openid"],
            state=session.get("state")
        )
        
        # Set the redirect URI explicitly for the token exchange
        flow.redirect_uri = "http://localhost:5001/callback"
        
        flow.fetch_token(authorization_response=request.url)
        print("Token fetched successfully")
        
        if not session.get("state") == request.args.get("state"):
            print("State mismatch")
            return redirect(url_for("menu"))
    
        credentials = flow.credentials
        request_session = http_requests.session()
        cached_session = cachecontrol.CacheControl(request_session)
        token_request = google.auth.transport.requests.Request(session=cached_session)
        
        id_info = id_token.verify_oauth2_token(
            id_token=credentials._id_token,
            request=token_request,
            audience=GOOGLE_CLIENT_ID
        )
        print(f"ID token verified for email: {id_info.get('email')}")
        
        # Get user info from Google
        google_id = id_info.get("sub")
        email = id_info.get("email")
        name = id_info.get("name")
        picture = id_info.get("picture")
        
        # Check if user exists
        user = User.query.filter_by(google_id=google_id).first()
        
        if not user:
            # Create new user with temporary username
            user = User(
                username=f"User{random.randint(1000, 9999)}",  # Temporary username
                email=email,
                google_id=google_id,
                profile_picture=picture
            )
            db.session.add(user)
            db.session.commit()
            print(f"Created new user with temporary username: {user.username}")
        else:
            print(f"Found existing user: {user.username}")
        
        session['user_id'] = user.id
        print(f"Set session user_id: {user.id}")
        return redirect(url_for("menu"))
    except Exception as e:
        print(f"OAuth callback error: {e}")
        import traceback
        traceback.print_exc()
        return redirect(url_for("menu"))

# Create database tables (only if not in production/vercel)
import os
if not os.environ.get('VERCEL') and not os.environ.get('RENDER'):
    with app.app_context():
        db.create_all()

if __name__ == '__main__':
    socketio.run(app, debug=True, host='localhost', port=5001)