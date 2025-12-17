import sqlite3
import json
from typing import List, Dict, Any, Optional

class DatabaseManager:
    def __init__(self, db_path: str = 'telegram_books.db'):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Инициализация базы данных"""
        with sqlite3.connect(self.db_path) as conn:
            # Таблица для книг без текста
            conn.execute('''
                CREATE TABLE IF NOT EXISTS books (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    author TEXT NOT NULL,
                    genre TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица для книг с текстом
            conn.execute('''
                CREATE TABLE IF NOT EXISTS books_with_content (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    author TEXT NOT NULL,
                    genre TEXT,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица прогресса чтения
            conn.execute('''
                CREATE TABLE IF NOT EXISTS reading_progress (
                    user_id INTEGER,
                    book_id INTEGER,
                    page INTEGER DEFAULT 1,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, book_id)
                )
            ''')
            
            conn.commit()
            print("[OK] База данных инициализирована")
    
    def get_connection(self):
        """Получить соединение с базой данных"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def add_book(self, title: str, author: str, genre: str = "") -> int:
        """Добавить книгу без текста"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO books (title, author, genre) VALUES (?, ?, ?)',
                (title, author, genre)
            )
            conn.commit()
            return cursor.lastrowid
    
    def add_book_with_content(self, title: str, author: str, genre: str, content: str) -> int:
        """Добавить книгу с текстом"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO books_with_content (title, author, genre, content) VALUES (?, ?, ?, ?)',
                (title, author, genre, content)
            )
            conn.commit()
            return cursor.lastrowid
    
    def get_all_books(self) -> List[Dict[str, Any]]:
        """Получить все книги без текста"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM books ORDER BY id DESC')
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def get_books_with_content(self) -> List[Dict[str, Any]]:
        """Получить все книги с текстом"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM books_with_content ORDER BY id DESC')
            rows = cursor.fetchall()
            
            books = []
            for row in rows:
                book = dict(row)
                # Добавляем количество страниц (примерно 2000 символов на страницу)
                content_len = len(book.get('content', ''))
                book['pages'] = (content_len // 2000) + 1 if content_len > 0 else 0
                books.append(book)
            
            return books
    
    def search_books(self, query: str) -> List[Dict[str, Any]]:
        """Поиск книг без текста"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            search_term = f'%{query}%'
            cursor.execute(
                'SELECT * FROM books WHERE title LIKE ? OR author LIKE ? OR genre LIKE ?',
                (search_term, search_term, search_term)
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def get_book_content(self, book_id: int, page: int = 1) -> Optional[Dict[str, Any]]:
        """Получить страницу книги с текстом"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Получаем информацию о книге
                cursor.execute(
                    'SELECT * FROM books_with_content WHERE id = ?',
                    (book_id,)
                )
                row = cursor.fetchone()
                
                if not row:
                    print(f"[DB ERROR] Книга с ID {book_id} не найдена")
                    return None
                
                book = dict(row)
                content = book.get('content', '')
                content_len = len(content)
                
                if content_len == 0:
                    print(f"[DB ERROR] Книга с ID {book_id} не содержит текста")
                    return None
                
                # Разбиваем текст на страницы по 2000 символов
                page_size = 2000
                total_pages = (content_len // page_size) + 1
                
                # Корректируем номер страницы
                if page < 1:
                    page = 1
                elif page > total_pages:
                    page = total_pages
                
                # Вычисляем начало и конец текста для текущей страницы
                start_index = (page - 1) * page_size
                end_index = min(start_index + page_size, content_len)
                
                # Получаем текст для текущей страницы
                page_content = content[start_index:end_index]
                
                # Вычисляем прогресс
                progress_position = start_index
                percentage = (progress_position / content_len * 100) if content_len > 0 else 0
                
                result = {
                    'id': book['id'],
                    'title': book['title'],
                    'author': book['author'],
                    'genre': book.get('genre', ''),
                    'content': page_content,
                    'current_page': page,
                    'total_pages': total_pages,
                    'progress': f"{progress_position}/{content_len}",
                    'percentage': round(percentage, 1)
                }
                
                return result
                
        except Exception as e:
            print(f"[DB ERROR] Ошибка при получении контента книги {book_id}: {e}")
            return None
    
    def save_reading_progress(self, user_id: int, book_id: int, page: int):
        """Сохранить прогресс чтения"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO reading_progress (user_id, book_id, page) 
                    VALUES (?, ?, ?)
                ''', (user_id, book_id, page))
                conn.commit()
        except Exception as e:
            print(f"[DB ERROR] Ошибка сохранения прогресса: {e}")
    
    def get_reading_progress(self, user_id: int, book_id: int) -> Optional[int]:
        """Получить сохраненный прогресс чтения"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'SELECT page FROM reading_progress WHERE user_id = ? AND book_id = ?',
                    (user_id, book_id)
                )
                row = cursor.fetchone()
                return row[0] if row else None
        except Exception as e:
            print(f"[DB ERROR] Ошибка получения прогресса: {e}")
            return None
    
    def delete_book(self, book_id: int) -> bool:
        """Удалить книгу (из обеих таблиц)"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Пробуем удалить из обеих таблиц
                deleted_count = 0
                
                cursor.execute('DELETE FROM books WHERE id = ?', (book_id,))
                deleted_count += cursor.rowcount
                
                cursor.execute('DELETE FROM books_with_content WHERE id = ?', (book_id,))
                deleted_count += cursor.rowcount
                
                # Удаляем прогресс чтения для этой книги
                cursor.execute('DELETE FROM reading_progress WHERE book_id = ?', (book_id,))
                
                conn.commit()
                return deleted_count > 0
                
        except Exception as e:
            print(f"[DB ERROR] Ошибка удаления книги {book_id}: {e}")
            return False
