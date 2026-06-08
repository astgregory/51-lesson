# Импорт необходимых библиотек
import sqlite3  # Библиотека для работы с SQLite базой данных
import json  # Библиотека для работы с JSON форматом
from datetime import datetime  # Библиотека для работы с датой и временем
import threading  # Библиотека для обеспечения потокобезопасности


class ChatCache:
    """
    Класс для кэширования истории чата в бд SQLite.

    Обеспечивает:
    - Потокобезопасное хранение истории сообщений
    - Сохранение метаданных (модель, токены, время)
    - Форматированный вывод истории
    - Очистку истории
    """

    def __init__(self):
        """
        Инициализация системы кэширования.

        Создает:
        - Файл базы данных SQLite
        - Потокобезопасное хранилище соединений
        - Необходимые таблицы в базе данных
        """
        # Имя файла SQLite базы данных
        self.db_name = 'chat_cache.db'

        import os
        full_path = os.path.abspath(self.db_name)
        print(f"DEBUG: ChatCache.__init__() - полный путь к БД: {full_path}")
        print(f"DEBUG: ChatCache.__init__() - текущая директория: {os.getcwd()}")

        # Создание потокобезопасного хранилища соединений
        # Каждый поток будет иметь свое собственное соединение с базой
        self.local = threading.local()

        # Создание необходимых таблиц при инициализации
        self.create_tables()

    # Получение соединения с базой данных
    def get_connection(self):
        return sqlite3.connect(self.db_name)

    # Создание необходимых таблиц в базе данных
    def create_tables(self):
        # Создаем новое соединение с базой
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        # SQL запросы для создания таблиц
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,  -- Уникальный ID сообщения
                model TEXT,                           -- Идентификатор модели
                user_message TEXT,                    -- Текст от пользователя
                ai_response TEXT,                     -- Ответ от AI
                timestamp DATETIME,                   -- Время создания
                tokens_used INTEGER                   -- Использовано токенов
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS analytics_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                model TEXT,
                message_length INTEGER,
                response_time FLOAT,
                tokens_used INTEGER
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS auth_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                api_key TEXT NOT NULL,               -- API ключ OpenRouter
                pin TEXT NOT NULL,                   -- 4-значный PIN код
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.commit()  # Сохранение изменений в базе
        conn.close()  # Закрытие соединения

    # Сохранение нового сообщения в базу данных
    def save_message(self, model, user_message, ai_response, tokens_used):

        conn = self.get_connection()  # Получение соединения для текущего потока
        cursor = conn.cursor()

        # Вставка новой записи в таблицу messages
        cursor.execute('''
            INSERT INTO messages (model, user_message, ai_response, timestamp, tokens_used)
            VALUES (?, ?, ?, ?, ?)
        ''', (model, user_message, ai_response, datetime.now(), tokens_used))
        conn.commit()  # Сохранение изменений

    # Получение последних сообщений из истории чата
    def get_chat_history(self, limit=50):
        conn = self.get_connection()  # Получение соединения для текущего потока
        cursor = conn.cursor()

        # Получение последних сообщений с ограничением по количеству
        cursor.execute('''
            SELECT * FROM messages 
            ORDER BY timestamp DESC 
            LIMIT ?
        ''', (limit,))
        return cursor.fetchall()  # Возврат всех найденных записей

    # Сохранение данных аналитики в базу данных
    def save_analytics(self, timestamp, model, message_length, response_time, tokens_used):

        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO analytics_messages 
            (timestamp, model, message_length, response_time, tokens_used)
            VALUES (?, ?, ?, ?, ?)
        ''', (timestamp, model, message_length, response_time, tokens_used))
        conn.commit()

    # Получение всей истории аналитики
    def get_analytics_history(self):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT timestamp, model, message_length, response_time, tokens_used
            FROM analytics_messages
            ORDER BY timestamp ASC
        ''')
        return cursor.fetchall()

    # Закрывает соединения с базой данных при уничтожении объекта
    def __del__(self):
        # Проверка наличия соединения в текущем потоке
        if hasattr(self.local, 'connection'):
            self.local.connection.close()  # Закрытие соединения

    # Очистка истории сообщений
    def clear_history(self):
        conn = self.get_connection()  # Получение соединения
        cursor = conn.cursor()
        cursor.execute('DELETE FROM messages')  # Удаление всех записей
        conn.commit()  # Сохранение изменений

    # Получение отформатированной истории диалога
    def get_formatted_history(self):

        conn = self.get_connection()  # Получение соединения
        cursor = conn.cursor()

        # Получение всех сообщений, отсортированных по времени
        cursor.execute('''
            SELECT 
                id,
                model,
                user_message,
                ai_response,
                timestamp,
                tokens_used
            FROM messages 
            ORDER BY timestamp ASC
        ''')

        # Формирование списка словарей с данными сообщений
        history = []
        for row in cursor.fetchall():
            history.append({
                "id": row[0],  # ID сообщения
                "model": row[1],  # Использованная модель
                "user_message": row[2],  # Сообщение пользователя
                "ai_response": row[3],  # Ответ AI
                "timestamp": row[4],  # Временная метка
                "tokens_used": row[5]  # Использовано токенов
            })
        return history  # Возврат форматированной истории

    # Сохранение аутентификационных данных (API ключ и PIN)
    def save_auth_data(self, api_key: str, pin: str):
        conn = self.get_connection()
        cursor = conn.cursor()

        # Проверяем, есть ли уже сохраненный API ключ
        cursor.execute('SELECT api_key FROM auth_data LIMIT 1')
        existing_data = cursor.fetchone()

        if existing_data and existing_data[0] == api_key:
            # Если это тот же API ключ, НЕ обновляем PIN
            conn.close()
            return

        # Если это новый API ключ или ключа нет, очищаем старые данные и вставляем новые
        cursor.execute('DELETE FROM auth_data')

        cursor.execute('''
            INSERT INTO auth_data (api_key, pin)
            VALUES (?, ?)
        ''', (api_key, pin))

        conn.commit()
        conn.close()

    # Получение сохраненных аутентификационных данных
    def get_auth_data(self):

        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT api_key, pin FROM auth_data LIMIT 1')
        result = cursor.fetchone()

        if result:
            return result[0], result[1]

        return None, None

    # Проверка наличия сохраненных аутентификационных данных
    def has_auth_data(self):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT COUNT(*) FROM auth_data')
        count = cursor.fetchone()[0]

        return count > 0

    # Очистка всех аутентификационных данных
    def clear_auth_data(self):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('DELETE FROM auth_data')
        conn.commit()