import sqlite3
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)

@contextmanager
def get_db_connection(db_path='telegram_books.db'):
    """Контекстный менеджер для подключения к БД."""
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    except Exception as e:
        logger.error(f"Database error: {e}")
        raise
    finally:
        conn.close()

class Database:
    def __init__(self, db_path='telegram_books.db'):
        self.db_path = db_path
        self.init_tables()
    
    def init_tables(self):
        """Инициализация всех таблиц."""
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Таблица книг
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS books (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    author TEXT NOT NULL,
                    genre TEXT,
                    description TEXT,
                    year INTEGER,
                    pages INTEGER,
                    rating REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица пользовательских коллекций
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_books (
                    user_id INTEGER NOT NULL,
                    book_id INTEGER NOT NULL,
                    status TEXT CHECK(status IN ('planned', 'reading', 'completed', 'dropped')),
                    user_rating INTEGER CHECK(user_rating >= 1 AND user_rating <= 5),
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, book_id),
                    FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
                )
            ''')
            
            # Индексы для ускорения поиска
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_books_title ON books(title)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_books_author ON books(author)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_books_user ON user_books(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_books_status ON user_books(status)')
            
            conn.commit()
            logger.info("Database tables initialized")
    
    # === ОПЕРАЦИИ С КНИГАМИ ===
    
    def add_book(self, title, author, genre=None, description=None, year=None, pages=None, rating=None):
        """Добавляет книгу в каталог."""
        try:
            with get_db_connection(self.db_path) as conn:
                cursor = conn.execute('''
                    INSERT INTO books (title, author, genre, description, year, pages, rating)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (title, author, genre, description, year, pages, rating))
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"Error adding book: {e}")
            return None
    
    def get_book(self, book_id):
        """Получает книгу по ID."""
        try:
            with get_db_connection(self.db_path) as conn:
                cursor = conn.execute('SELECT * FROM books WHERE id = ?', (book_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting book {book_id}: {e}")
            return None
    
    def search_books(self, query, limit=20):
        """Ищет книги по названию или автору."""
        try:
            search_term = f"%{query}%"
            with get_db_connection(self.db_path) as conn:
                # ИСПРАВЛЕННЫЙ ЗАПРОС без UNION
                cursor = conn.execute('''
                    SELECT DISTINCT id, title, author, genre, description, rating
                    FROM books 
                    WHERE title LIKE ? OR author LIKE ?
                    ORDER BY title
                    LIMIT ?
                ''', (search_term, search_term, limit))
                
                results = []
                for row in cursor.fetchall():
                    results.append({
                        'id': row['id'],
                        'title': row['title'],
                        'author': row['author'],
                        'genre': row['genre'],
                        'description': row['description'],
                        'rating': row['rating']
                    })
                return results
        except Exception as e:
            logger.error(f"Error searching books: {e}")
            return []
    
    def get_all_books(self, limit=50):
        """Получает все книги."""
        try:
            with get_db_connection(self.db_path) as conn:
                cursor = conn.execute('''
                    SELECT id, title, author, genre 
                    FROM books 
                    ORDER BY title 
                    LIMIT ?
                ''', (limit,))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting all books: {e}")
            return []
    
    # === ОПЕРАЦИИ С ПОЛЬЗОВАТЕЛЬСКИМИ КОЛЛЕКЦИЯМИ ===
    
    def add_user_book(self, user_id, book_id, status='planned'):
        """Добавляет книгу в коллекцию пользователя."""
        try:
            with get_db_connection(self.db_path) as conn:
                cursor = conn.execute('''
                    INSERT OR REPLACE INTO user_books (user_id, book_id, status, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ''', (user_id, book_id, status))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error adding user book: {e}")
            return False
    
    def update_user_book_status(self, user_id, book_id, status):
        """Обновляет статус книги у пользователя."""
        try:
            with get_db_connection(self.db_path) as conn:
                cursor = conn.execute('''
                    UPDATE user_books 
                    SET status = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ? AND book_id = ?
                ''', (status, user_id, book_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating book status: {e}")
            return False
    
    def rate_user_book(self, user_id, book_id, rating):
        """Оценивает книгу пользователем."""
        try:
            with get_db_connection(self.db_path) as conn:
                cursor = conn.execute('''
                    UPDATE user_books 
                    SET user_rating = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ? AND book_id = ?
                ''', (rating, user_id, book_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error rating book: {e}")
            return False
    
    def remove_user_book(self, user_id, book_id):
        """Удаляет книгу из коллекции пользователя."""
        try:
            with get_db_connection(self.db_path) as conn:
                cursor = conn.execute('''
                    DELETE FROM user_books 
                    WHERE user_id = ? AND book_id = ?
                ''', (user_id, book_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error removing user book: {e}")
            return False
    
    def get_user_books(self, user_id, status=None):
        """Получает книги пользователя."""
        try:
            with get_db_connection(self.db_path) as conn:
                if status:
                    cursor = conn.execute('''
                        SELECT ub.book_id, ub.status, ub.user_rating, 
                               b.title, b.author, b.genre
                        FROM user_books ub
                        JOIN books b ON ub.book_id = b.id
                        WHERE ub.user_id = ? AND ub.status = ?
                        ORDER BY ub.updated_at DESC
                    ''', (user_id, status))
                else:
                    cursor = conn.execute('''
                        SELECT ub.book_id, ub.status, ub.user_rating, 
                               b.title, b.author, b.genre
                        FROM user_books ub
                        JOIN books b ON ub.book_id = b.id
                        WHERE ub.user_id = ?
                        ORDER BY ub.updated_at DESC
                    ''', (user_id,))
                
                results = []
                for row in cursor.fetchall():
                    results.append({
                        'book_id': row['book_id'],
                        'status': row['status'],
                        'user_rating': row['user_rating'],
                        'title': row['title'],
                        'author': row['author'],
                        'genre': row['genre']
                    })
                return results
        except Exception as e:
            logger.error(f"Error getting user books: {e}")
            return []
    
    def get_user_stats(self, user_id):
        """Получает статистику пользователя."""
        try:
            with get_db_connection(self.db_path) as conn:
                cursor = conn.execute('''
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN status = 'planned' THEN 1 ELSE 0 END) as planned,
                        SUM(CASE WHEN status = 'reading' THEN 1 ELSE 0 END) as reading,
                        SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                        SUM(CASE WHEN status = 'dropped' THEN 1 ELSE 0 END) as dropped,
                        AVG(user_rating) as avg_rating,
                        COUNT(user_rating) as rated_count
                    FROM user_books 
                    WHERE user_id = ?
                ''', (user_id,))
                
                row = cursor.fetchone()
                if row:
                    return {
                        'total': row['total'] or 0,
                        'planned': row['planned'] or 0,
                        'reading': row['reading'] or 0,
                        'completed': row['completed'] or 0,
                        'dropped': row['dropped'] or 0,
                        'avg_rating': round(row['avg_rating'] or 0, 2),
                        'rated_count': row['rated_count'] or 0
                    }
                return {
                    'total': 0, 'planned': 0, 'reading': 0,
                    'completed': 0, 'dropped': 0, 'avg_rating': 0.0,
                    'rated_count': 0
                }
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            return {
                'total': 0, 'planned': 0, 'reading': 0,
                'completed': 0, 'dropped': 0, 'avg_rating': 0.0,
                'rated_count': 0
            }
    
    def has_user_book(self, user_id, book_id):
        """Проверяет, есть ли книга у пользователя."""
        try:
            with get_db_connection(self.db_path) as conn:
                cursor = conn.execute('''
                    SELECT 1 FROM user_books 
                    WHERE user_id = ? AND book_id = ?
                ''', (user_id, book_id))
                return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"Error checking user book: {e}")
            return False
    
    def get_popular_books(self, limit=10):
        """Получает популярные книги (по количеству добавлений)."""
        try:
            with get_db_connection(self.db_path) as conn:
                cursor = conn.execute('''
                    SELECT b.id, b.title, b.author, b.genre, b.rating,
                           COUNT(ub.book_id) as user_count
                    FROM books b
                    LEFT JOIN user_books ub ON b.id = ub.book_id
                    GROUP BY b.id
                    ORDER BY user_count DESC, b.rating DESC
                    LIMIT ?
                ''', (limit,))
                
                results = []
                for row in cursor.fetchall():
                    results.append({
                        'id': row['id'],
                        'title': row['title'],
                        'author': row['author'],
                        'genre': row['genre'],
                        'rating': row['rating'],
                        'user_count': row['user_count']
                    })
                return results
        except Exception as e:
            logger.error(f"Error getting popular books: {e}")
            return []
    
    def clear_user_data(self, user_id):
        """Удаляет все данные пользователя."""
        try:
            with get_db_connection(self.db_path) as conn:
                cursor = conn.execute('DELETE FROM user_books WHERE user_id = ?', (user_id,))
                conn.commit()
                return cursor.rowcount
        except Exception as e:
            logger.error(f"Error clearing user data: {e}")
            return 0

# Создаем глобальный экземпляр базы данных
db = Database()
