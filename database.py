import sqlite3
from datetime import datetime, date
import json


class Database:
    def __init__(self):
        self.init_database()

    def init_database(self):
        conn = sqlite3.connect('multiplication.db')
        cursor = conn.cursor()

        # Таблица для ежедневной статистики
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

        # Таблица для детальной истории ответов
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

        # Таблица для достижений
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS achievements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                achievement_type TEXT NOT NULL,
                description TEXT NOT NULL
            )
        ''')

        conn.commit()
        conn.close()

    def record_answer(self, number, multiplier, user_answer, correct_answer, response_time=None):
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

        # Проверяем достижения
        self._check_achievements(cursor, today, number, is_correct)

        conn.commit()
        conn.close()

        return is_correct

    def _check_achievements(self, cursor, today, number, is_correct):
        """Проверяет и добавляет достижения"""

        # Достижение за первую правильную ответ
        cursor.execute('''
            SELECT COUNT(*) FROM answer_history 
            WHERE date(timestamp) = ? AND is_correct = 1
        ''', (today,))
        total_correct_today = cursor.fetchone()[0]

        if total_correct_today == 1:
            cursor.execute('''
                INSERT OR IGNORE INTO achievements (date, achievement_type, description)
                VALUES (?, 'first_correct', 'Первая правильная ответ сегодня!')
            ''', (today,))

        # Достижение за 10 правильных ответов подряд
        if is_correct:
            cursor.execute('''
                SELECT is_correct FROM answer_history 
                WHERE date(timestamp) = ? 
                ORDER BY timestamp DESC LIMIT 10
            ''', (today,))
            last_10 = cursor.fetchall()
            if len(last_10) >= 10 and all(result[0] for result in last_10):
                cursor.execute('''
                    INSERT OR IGNORE INTO achievements (date, achievement_type, description)
                    VALUES (?, 'streak_10', '10 правильных ответов подряд!')
                ''', (today,))

        # Достижение за изучение всех чисел
        cursor.execute('''
            SELECT COUNT(DISTINCT number) FROM daily_stats 
            WHERE date = ? AND correct_answers >= 5
        ''', (today,))
        numbers_learned = cursor.fetchone()[0]

        if numbers_learned >= 8:  # Все числа от 2 до 9
            cursor.execute('''
                INSERT OR IGNORE INTO achievements (date, achievement_type, description)
                VALUES (?, 'all_numbers', 'Изучил все числа сегодня!')
            ''', (today,))

    def get_daily_stats(self, date_str=None):
        if date_str is None:
            date_str = date.today().isoformat()

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

        return [{
            'number': row[0],
            'correct': row[1],
            'total': row[2],
            'accuracy': row[3] if row[2] > 0 else 0
        } for row in stats]

    def get_weekly_progress(self):
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

        return [{
            'date': row[0],
            'correct': row[1],
            'total': row[2],
            'accuracy': row[3] if row[2] > 0 else 0
        } for row in weekly_data]

    def get_achievements(self, date_str=None):
        if date_str is None:
            date_str = date.today().isoformat()

        conn = sqlite3.connect('multiplication.db')
        cursor = conn.cursor()

        cursor.execute('''
            SELECT achievement_type, description, date 
            FROM achievements 
            WHERE date = ?
            ORDER BY id DESC
        ''', (date_str,))

        achievements = cursor.fetchall()
        conn.close()

        return [{
            'type': row[0],
            'description': row[1],
            'date': row[2]
        } for row in achievements]

    def get_overall_stats(self):
        conn = sqlite3.connect('multiplication.db')
        cursor = conn.cursor()

        cursor.execute('''
            SELECT 
                COUNT(*) as total_questions,
                SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) as correct_answers,
                AVG(CASE WHEN is_correct THEN response_time ELSE NULL END) as avg_time_correct,
                COUNT(DISTINCT date(timestamp)) as days_played
            FROM answer_history
        ''')

        overall = cursor.fetchone()
        conn.close()

        return {
            'total_questions': overall[0],
            'correct_answers': overall[1],
            'accuracy': round(overall[1] * 100.0 / overall[0], 1) if overall[0] > 0 else 0,
            'avg_time_correct': round(overall[2], 1) if overall[2] else 0,
            'days_played': overall[3]
        }


db = Database()