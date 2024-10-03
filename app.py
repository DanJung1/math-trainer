from flask import Flask, render_template, request, jsonify
import random

app = Flask(__name__)

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

    def check_answer(self, user_answer, correct_answer):
        is_correct = user_answer == correct_answer
        if is_correct:
            self.correct_answers += 1
        return is_correct

trainer = MentalMathTrainer()

@app.route('/')
def menu():
    return render_template('menu.html')

@app.route('/marathon')
def marathon():
    return render_template('marathon.html')

@app.route('/dynamic')
def dynamic():
    return render_template('dynamic.html')

@app.route('/training')
def training():
    return render_template('training.html')

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

    is_correct = trainer.check_answer(user_answer, correct_answer)

    return jsonify({
        'is_correct': is_correct,
        'correct_answers': trainer.correct_answers,
    })

if __name__ == '__main__':
    app.run(debug=True)