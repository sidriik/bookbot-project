import sqlite3
import os
from pathlib import Path
from typing import List, Dict, Any, Optional

class DatabaseManager:
    def __init__(self, db_path: str = 'telegram_books.db'):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Инициализация базы данных с поддержкой файлов"""
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
            
            # Таблица для информации о файлах книг
            conn.execute('''
                CREATE TABLE IF NOT EXISTS book_files (
                    book_id INTEGER PRIMARY KEY,
                    file_path TEXT NOT NULL,
                    file_ext TEXT NOT NULL,
                    file_size INTEGER,
                    original_filename TEXT,
                    FOREIGN KEY (book_id) REFERENCES books_with_content(id)
                )
            ''')
            
            # Таблица прогресса чтения
            conn.execute('''
                CREATE TABLE IF NOT EXISTS reading_progress (
                    user_id INTEGER,
                    book_id INTEGER,
                    page INTEGER DEFAULT 1,
                    PRIMARY KEY (user_id, book_id)
                )
            ''')
            
            conn.commit()
            print("[OK] База данных с поддержкой файлов инициализирована")
    
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
    
    def save_book_file_info(self, book_id: int, file_path: str, file_ext: str, file_size: int, original_filename: str = ""):
        """Сохранить информацию о файле книги"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT OR REPLACE INTO book_files (book_id, file_path, file_ext, file_size, original_filename) VALUES (?, ?, ?, ?, ?)',
                (book_id, file_path, file_ext, file_size, original_filename)
            )
            conn.commit()
    
    def get_book_file_info(self, book_id: int) -> Optional[Dict[str, Any]]:
        """Получить информацию о файле книги"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''SELECT bwc.*, bf.file_path, bf.file_ext, bf.file_size, bf.original_filename 
                   FROM books_with_content bwc
                   LEFT JOIN book_files bf ON bwc.id = bf.book_id
                   WHERE bwc.id = ?''',
                (book_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
    
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
            return [dict(row) for row in rows]
    
    def get_books_with_files(self) -> List[Dict[str, Any]]:
        """Получить все книги с файлами"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''SELECT bwc.*, bf.file_ext, bf.file_size 
                   FROM books_with_content bwc
                   JOIN book_files bf ON bwc.id = bf.book_id
                   ORDER BY bwc.id DESC'''
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def search_books(self, query: str) -> List[Dict[str, Any]]:
        """Поиск книг"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            search_term = f'%{query}%'
            cursor.execute(
                '''SELECT * FROM books 
                   WHERE title LIKE ? OR author LIKE ? OR genre LIKE ?
                   UNION
                   SELECT * FROM books_with_content 
                   WHERE title LIKE ? OR author LIKE ? OR genre LIKE ?
                   ORDER BY id DESC''',
                (search_term, search_term, search_term, search_term, search_term, search_term)
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def get_book_content(self, book_id: int, page: int = 1) -> Optional[Dict[str, Any]]:
        """Получить страницу книги с текстом"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Получаем книгу
                cursor.execute(
                    'SELECT * FROM books_with_content WHERE id = ?',
                    (book_id,)
                )
                row = cursor.fetchone()
                
                if not row:
                    return None
                
                book = dict(row)
                content = book.get('content', '')
                
                if not content:
                    return None
                
                # Разбиваем на страницы по 2000 символов
                page_size = 2000
                content_length = len(content)
                total_pages = (content_length // page_size) + 1
                
                # Корректируем номер страницы
                if page < 1:
                    page = 1
                elif page > total_pages:
                    page = total_pages
                
                # Получаем текст для страницы
                start_idx = (page - 1) * page_size
                end_idx = min(start_idx + page_size, content_length)
                page_content = content[start_idx:end_idx]
                
                # Получаем информацию о файле
                cursor.execute(
                    'SELECT * FROM book_files WHERE book_id = ?',
                    (book_id,)
                )
                file_row = cursor.fetchone()
                file_info = dict(file_row) if file_row else {}
                
                result = {
                    'id': book['id'],
                    'title': book['title'],
                    'author': book['author'],
                    'genre': book.get('genre', ''),
                    'content': page_content,
                    'current_page': page,
                    'total_pages': total_pages,
                    'has_file': file_info.get('file_path') is not None,
                    'file_ext': file_info.get('file_ext', ''),
                    'file_size': file_info.get('file_size', 0)
                }
                
                return result
                
        except Exception as e:
            print(f"[DB ERROR] Ошибка при получении книги {book_id}: {e}")
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
        except:
            pass
    
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
        except:
            return None
    
    def delete_book(self, book_id: int) -> bool:
        """Удалить книгу (из всех таблиц)"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                deleted = False
                
                # Удаляем из books
                cursor.execute('DELETE FROM books WHERE id = ?', (book_id,))
                if cursor.rowcount > 0:
                    deleted = True
                
                # Удаляем из books_with_content
                cursor.execute('DELETE FROM books_with_content WHERE id = ?', (book_id,))
                if cursor.rowcount > 0:
                    deleted = True
                
                # Удаляем файл книги (если есть)
                cursor.execute('SELECT file_path FROM book_files WHERE book_id = ?', (book_id,))
                file_row = cursor.fetchone()
                if file_row:
                    file_path = file_row[0]
                    try:
                        if os.path.exists(file_path):
                            os.remove(file_path)
                    except:
                        pass
                
                # Удаляем информацию о файле
                cursor.execute('DELETE FROM book_files WHERE book_id = ?', (book_id,))
                
                # Удаляем прогресс чтения
                cursor.execute('DELETE FROM reading_progress WHERE book_id = ?', (book_id,))
                
                conn.commit()
                return deleted
                
        except Exception as e:
            print(f"[DB ERROR] Ошибка удаления книги {book_id}: {e}")
            return False
