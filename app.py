from flask import Flask, render_template, request, jsonify
import random
import time
from datetime import datetime, date
import sqlite3
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'multiplication-trainer-secret-key')

# Получаем порт из переменной окружения Render
port = int(os.environ.get('PORT', 5000))


# Инициализация базы данных
def init_db():
    conn = sqlite3.connect('multiplication.db')
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            number INTEGER NOT NULL,
            correct_answers INTEGER DEFAULT 0,
            total_answers INTEGER DEFAULT 0,
            UNIQUE(date, number)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS answer_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            number INTEGER NOT NULL,
            multiplier INTEGER NOT NULL,
            user_answer INTEGER NOT NULL,
            correct_answer INTEGER NOT NULL,
            is_correct BOOLEAN NOT NULL,
            response_time REAL
        )
    ''')

    conn.commit()
    conn.close()


init_db()


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


def record_answer(number, multiplier, user_answer, correct_answer, response_time=None):
    conn = sqlite3.connect('multiplication.db')
    cursor = conn.cursor()

    is_correct = user_answer == correct_answer
    today = date.today().isoformat()

    # Записываем в историю
    cursor.execute('''
        INSERT INTO answer_history 
        (timestamp, number, multiplier, user_answer, correct_answer, is_correct, response_time)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (datetime.now().isoformat(), number, multiplier, user_answer, correct_answer, is_correct, response_time))

    # Обновляем ежедневную статистику
    cursor.execute('''
        INSERT OR REPLACE INTO daily_stats (date, number, correct_answers, total_answers)
        VALUES (?, ?, 
            COALESCE((SELECT correct_answers FROM daily_stats WHERE date = ? AND number = ?), 0) + ?,
            COALESCE((SELECT total_answers FROM daily_stats WHERE date = ? AND number = ?), 0) + 1
        )
    ''', (today, number, today, number, 1 if is_correct else 0, today, number))

    conn.commit()
    conn.close()

    return is_correct


@app.route('/')
def index():
    return render_template('index.html', today=date.today().isoformat())


@app.route('/stats')
def stats():
    return render_template('stats.html')


@app.route('/select_number', methods=['POST'])
def select_number():
    try:
        number = int(request.json['number'])
        question_data = game.generate_question(number)
        return jsonify(question_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/check_answer', methods=['POST'])
def check_answer():
    try:
        user_answer = int(request.json['answer'])
        response_time = time.time() - game.start_time

        # Записываем ответ в базу
        is_correct = record_answer(
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
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/daily_stats')
def api_daily_stats():
    date_str = request.args.get('date', date.today().isoformat())

    conn = sqlite3.connect('multiplication.db')
    cursor = conn.cursor()

    cursor.execute('''
        SELECT number, correct_answers, total_answers,
               ROUND(correct_answers * 100.0 / total_answers, 1) as accuracy
        FROM daily_stats 
        WHERE date = ?
        ORDER BY number
    ''', (date_str,))

    stats = cursor.fetchall()
    conn.close()

    result = [{
        'number': row[0],
        'correct': row[1] or 0,
        'total': row[2] or 0,
        'accuracy': row[3] or 0
    } for row in stats]

    # Добавляем недостающие числа
    for number in range(2, 10):
        if not any(stat['number'] == number for stat in result):
            result.append({
                'number': number,
                'correct': 0,
                'total': 0,
                'accuracy': 0
            })

    result.sort(key=lambda x: x['number'])
    return jsonify(result)


@app.route('/api/weekly_progress')
def api_weekly_progress():
    conn = sqlite3.connect('multiplication.db')
    cursor = conn.cursor()

    cursor.execute('''
        SELECT date, 
               SUM(correct_answers) as total_correct,
               SUM(total_answers) as total_answers,
               ROUND(SUM(correct_answers) * 100.0 / SUM(total_answers), 1) as accuracy
        FROM daily_stats 
        WHERE date >= date('now', '-6 days')
        GROUP BY date
        ORDER BY date
    ''')

    weekly_data = cursor.fetchall()
    conn.close()

    return jsonify([{
        'date': row[0],
        'correct': row[1] or 0,
        'total': row[2] or 0,
        'accuracy': row[3] or 0
    } for row in weekly_data])


@app.route('/api/overall_stats')
def api_overall_stats():
    conn = sqlite3.connect('multiplication.db')
    cursor = conn.cursor()

    cursor.execute('''
        SELECT 
            COUNT(*) as total_questions,
            SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) as correct_answers,
            COUNT(DISTINCT date(timestamp)) as days_played
        FROM answer_history
    ''')

    overall = cursor.fetchone()
    conn.close()

    total_questions = overall[0] or 0
    correct_answers = overall[1] or 0
    days_played = overall[2] or 0

    return jsonify({
        'total_questions': total_questions,
        'correct_answers': correct_answers,
        'accuracy': round(correct_answers * 100.0 / total_questions, 1) if total_questions > 0 else 0,
        'days_played': days_played
    })


@app.route('/api/achievements')
def api_achievements():
    # Упрощенная версия без достижений
    return jsonify([])


if __name__ == '__main__':
    # Важно: слушаем на 0.0.0.0 для Render
    app.run(debug=False, host='0.0.0.0', port=port)