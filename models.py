import sqlite3
from contextlib import contextmanager
from database import db, Database
@contextmanager
def get_db_connection():
    """Контекстный менеджер для подключения к БД."""
    conn = sqlite3.connect('telegram_books.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

class Database:
    """Класс для работы с базой данных."""
    
    def __init__(self):
        self.init_database()
    
    def init_database(self):
        """Инициализация таблиц базы данных."""
        with get_db_connection() as conn:
            # Таблица пользователей и их книг
            conn.execute('''
                CREATE TABLE IF NOT EXISTS user_books (
                    user_id INTEGER,
                    book_id INTEGER,
                    status TEXT CHECK(status IN ('planned', 'reading', 'completed', 'dropped')),
                    rating INTEGER CHECK(rating >= 1 AND rating <= 5),
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, book_id)
                )
            ''')
            
            # Таблица книг (если нужно хранить информацию о книгах)
            conn.execute('''
                CREATE TABLE IF NOT EXISTS books (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    author TEXT NOT NULL,
                    genre TEXT,
                    description TEXT
                )
            ''')
            conn.commit()
    
    def add_user_book(self, user_id, book_id, status):
        """Добавляет книгу в коллекцию пользователя."""
        try:
            with get_db_connection() as conn:
                cursor = conn.execute(
                    'INSERT OR REPLACE INTO user_books (user_id, book_id, status) VALUES (?, ?, ?)',
                    (user_id, book_id, status)
                )
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Error adding book: {e}")
            return False
    
    def update_book_status(self, user_id, book_id, status):
        """Обновляет статус книги."""
        try:
            with get_db_connection() as conn:
                cursor = conn.execute(
                    'UPDATE user_books SET status = ? WHERE user_id = ? AND book_id = ?',
                    (status, user_id, book_id)
                )
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Error updating status: {e}")
            return False
    
    def rate_book(self, user_id, book_id, rating):
        """Оценивает книгу."""
        try:
            with get_db_connection() as conn:
                cursor = conn.execute(
                    'UPDATE user_books SET rating = ? WHERE user_id = ? AND book_id = ?',
                    (rating, user_id, book_id)
                )
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Error rating book: {e}")
            return False
    
    def remove_user_book(self, user_id, book_id):
        """Удаляет книгу из коллекции пользователя."""
        try:
            with get_db_connection() as conn:
                cursor = conn.execute(
                    'DELETE FROM user_books WHERE user_id = ? AND book_id = ?',
                    (user_id, book_id)
                )
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Error removing book: {e}")
            return False
    
    def get_user_books(self, user_id, status=None):
        """Получает книги пользователя."""
        try:
            with get_db_connection() as conn:
                if status:
                    cursor = conn.execute(
                        'SELECT book_id, status, rating FROM user_books WHERE user_id = ? AND status = ?',
                        (user_id, status)
                    )
                else:
                    cursor = conn.execute(
                        'SELECT book_id, status, rating FROM user_books WHERE user_id = ?',
                        (user_id,)
                    )
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error getting user books: {e}")
            return []
    
    def get_user_stats(self, user_id):
        """Получает статистику пользователя."""
        try:
            with get_db_connection() as conn:
                cursor = conn.execute('''
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN status = 'planned' THEN 1 ELSE 0 END) as planned,
                        SUM(CASE WHEN status = 'reading' THEN 1 ELSE 0 END) as reading,
                        SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                        SUM(CASE WHEN status = 'dropped' THEN 1 ELSE 0 END) as dropped,
                        AVG(rating) as avg_rating,
                        COUNT(rating) as rated_count
                    FROM user_books 
                    WHERE user_id = ?
                ''', (user_id,))
                
                result = cursor.fetchone()
                if result:
                    return {
                        'total': result['total'] or 0,
                        'planned': result['planned'] or 0,
                        'reading': result['reading'] or 0,
                        'completed': result['completed'] or 0,
                        'dropped': result['dropped'] or 0,
                        'avg_rating': round(result['avg_rating'] or 0, 2),
                        'rated_count': result['rated_count'] or 0
                    }
                return {
                    'total': 0, 'planned': 0, 'reading': 0,
                    'completed': 0, 'dropped': 0, 'avg_rating': 0.0,
                    'rated_count': 0
                }
        except Exception as e:
            print(f"Error getting stats: {e}")
            return {
                'total': 0, 'planned': 0, 'reading': 0,
                'completed': 0, 'dropped': 0, 'avg_rating': 0.0,
                'rated_count': 0
            }
    
    def has_book(self, user_id, book_id):
        """Проверяет, есть ли книга у пользователя."""
        try:
            with get_db_connection() as conn:
                cursor = conn.execute(
                    'SELECT 1 FROM user_books WHERE user_id = ? AND book_id = ?',
                    (user_id, book_id)
                )
                return cursor.fetchone() is not None
        except Exception as e:
            print(f"Error checking book: {e}")
            return False
    
    def search_books(self, query):
        """Ищет книги по названию или автору."""
        try:
            with get_db_connection() as conn:
                search_term = f"%{query}%"
                cursor = conn.execute('''
                    SELECT id, title, author, genre, description 
                    FROM books 
                    WHERE title LIKE ? OR author LIKE ? 
                    LIMIT 20
                ''', (search_term, search_term))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error searching books: {e}")
            return []
    
    def get_book_by_id(self, book_id):
        """Получает книгу по ID."""
        try:
            with get_db_connection() as conn:
                cursor = conn.execute(
                    'SELECT id, title, author, genre, description FROM books WHERE id = ?',
                    (book_id,)
                )
                result = cursor.fetchone()
                return dict(result) if result else None
        except Exception as e:
            print(f"Error getting book: {e}")
            return None

# Создаем глобальный экземпляр базы данных
db = Database()
