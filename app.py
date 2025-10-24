from flask import Flask, render_template, request, jsonify, session
import random
import time
from datetime import datetime, date, timedelta
from database import db

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Замените на случайный ключ в продакшене


class MultiplicationGame:
    def __init__(self):
        self.current_number = None
        self.current_multiplier = None
        self.correct_answer = None
        self.start_time = None

    def generate_question(self, number):
        """Генерирует вопрос и варианты ответов"""
        self.current_number = number
        self.current_multiplier = random.randint(2, 9)
        self.correct_answer = self.current_number * self.current_multiplier
        self.start_time = time.time()

        # Создаем варианты ответов
        answers = [self.correct_answer]

        # Добавляем 2 неправильных ответа (больше правильного)
        while len(answers) < 3:
            wrong_answer = self.correct_answer + random.randint(1, 5)
            if wrong_answer not in answers:
                answers.append(wrong_answer)

        # Добавляем 3 неправильных ответа (меньше правильного)
        while len(answers) < 6:
            wrong_answer = max(1, self.correct_answer - random.randint(1, 5))
            if wrong_answer not in answers:
                answers.append(wrong_answer)

        # Перемешиваем ответы
        random.shuffle(answers)

        return {
            'question': f"{self.current_number} × {self.current_multiplier} = ?",
            'answers': answers,
            'correct_answer': self.correct_answer
        }


game = MultiplicationGame()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/stats')
def stats():
    return render_template('stats.html')


@app.route('/select_number', methods=['POST'])
def select_number():
    number = int(request.json['number'])
    question_data = game.generate_question(number)
    return jsonify(question_data)


@app.route('/check_answer', methods=['POST'])
def check_answer():
    user_answer = int(request.json['answer'])
    response_time = time.time() - game.start_time

    # Записываем ответ в базу
    is_correct = db.record_answer(
        game.current_number,
        game.current_multiplier,
        user_answer,
        game.correct_answer,
        response_time
    )

    # Генерируем новый вопрос с тем же числом
    new_question = game.generate_question(game.current_number)

    return jsonify({
        'correct': is_correct,
        'correct_answer': game.correct_answer,
        'new_question': new_question,
        'response_time': round(response_time, 1)
    })


@app.route('/api/daily_stats')
def api_daily_stats():
    date_str = request.args.get('date', date.today().isoformat())
    stats = db.get_daily_stats(date_str)
    return jsonify(stats)


@app.route('/api/weekly_progress')
def api_weekly_progress():
    progress = db.get_weekly_progress()
    return jsonify(progress)


@app.route('/api/achievements')
def api_achievements():
    date_str = request.args.get('date', date.today().isoformat())
    achievements = db.get_achievements(date_str)
    return jsonify(achievements)


@app.route('/api/overall_stats')
def api_overall_stats():
    stats = db.get_overall_stats()
    return jsonify(stats)


@app.route('/api/streak')
def api_streak():
    conn = sqlite3.connect('multiplication.db')
    cursor = conn.cursor()

    # Вычисляем текущую серию дней
    cursor.execute('''
        WITH dates AS (
            SELECT DISTINCT date(timestamp) as day 
            FROM answer_history 
            ORDER BY day DESC
        ),
        streaks AS (
            SELECT day, 
                   date(day, '-' || (ROW_NUMBER() OVER (ORDER BY day DESC) - 1) || ' days') as calc_date
            FROM dates
        )
        SELECT COUNT(*) 
        FROM streaks 
        WHERE calc_date = date('now', '-' || (ROW_NUMBER() OVER (ORDER BY day DESC) - 1) || ' days')
        LIMIT 1
    ''')

    streak = cursor.fetchone()[0]
    conn.close()

    return jsonify({'streak': streak})


if __name__ == '__main__':
    app.run(debug=True)