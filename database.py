import sqlite3
import logging
from typing import List, Dict, Any, Optional

class DatabaseManager:
    """Класс для работы с базой данных SQLite."""
    
    def __init__(self, db_path: str = 'telegram_books.db'):
        """
        Инициализация подключения к базе данных.
        
        Args:
            db_path (str): Путь к файлу базы данных
        """
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        
        # Инициализируем базу данных
        self.init_db()
        
        # Настройка логирования
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def init_db(self):
        """Инициализация базы данных."""
        # Таблица обычных книг
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                genre TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица книг с текстом
        self.cursor.execute('''
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
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS reading_progress (
                user_id INTEGER,
                book_id INTEGER,
                page INTEGER DEFAULT 1,
                last_read TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, book_id),
                FOREIGN KEY (book_id) REFERENCES books_with_content(id)
            )
        ''')
        
        self.conn.commit()
        print(" Таблицы базы данных созданы/проверены")
    
    def add_book(self, title: str, author: str, genre: str = None) -> int:
        """
        Добавление книги в картотеку (без текста).
        
        Args:
            title (str): Название книги
            author (str): Автор книги
            genre (str, optional): Жанр книги
            
        Returns:
            int: ID добавленной книги
        """
        try:
            self.cursor.execute(
                "INSERT INTO books (title, author, genre) VALUES (?, ?, ?)",
                (title, author, genre)
            )
            self.conn.commit()
            return self.cursor.lastrowid
        except Exception as e:
            self.logger.error(f"Ошибка при добавлении книги: {e}")
            raise
    
    def add_book_with_content(self, title: str, author: str, genre: str, content: str) -> int:
        """
        Добавление книги с текстом.
        
        Args:
            title (str): Название книги
            author (str): Автор книги
            genre (str): Жанр книги
            content (str): Текст книги
            
        Returns:
            int: ID добавленной книги
        """
        try:
            self.cursor.execute(
                "INSERT INTO books_with_content (title, author, genre, content) VALUES (?, ?, ?, ?)",
                (title, author, genre, content)
            )
            self.conn.commit()
            return self.cursor.lastrowid
        except Exception as e:
            self.logger.error(f"Ошибка при добавлении книги с текстом: {e}")
            raise
    
    def search_books(self, query: str) -> List[Dict[str, Any]]:
        """
        Поиск книг по названию, автору или жанру.
        
        Args:
            query (str): Поисковый запрос
            
        Returns:
            List[Dict]: Список найденных книг
        """
        try:
            search_pattern = f"%{query}%"
            
            # Ищем в обычных книгах
            self.cursor.execute('''
                SELECT id, title, author, genre, 'simple' as type 
                FROM books 
                WHERE title LIKE ? OR author LIKE ? OR genre LIKE ?
            ''', (search_pattern, search_pattern, search_pattern))
            
            books = []
            for row in self.cursor.fetchall():
                books.append({
                    'id': row[0],
                    'title': row[1],
                    'author': row[2],
                    'genre': row[3],
                    'type': row[4]
                })
            
            # Ищем в книгах с текстом
            self.cursor.execute('''
                SELECT id, title, author, genre, 'with_content' as type 
                FROM books_with_content 
                WHERE title LIKE ? OR author LIKE ? OR genre LIKE ?
            ''', (search_pattern, search_pattern, search_pattern))
            
            for row in self.cursor.fetchall():
                books.append({
                    'id': row[0],
                    'title': row[1],
                    'author': row[2],
                    'genre': row[3],
                    'type': row[4]
                })
            
            return books
        except Exception as e:
            self.logger.error(f"Ошибка при поиске книг: {e}")
            return []
    
    def get_all_books(self) -> List[Dict[str, Any]]:
        """
        Получение всех книг из картотеки.
        
        Returns:
            List[Dict]: Список всех книг
        """
        try:
            self.cursor.execute("SELECT id, title, author, genre FROM books ORDER BY id DESC")
            books = []
            for row in self.cursor.fetchall():
                books.append({
                    'id': row[0],
                    'title': row[1],
                    'author': row[2],
                    'genre': row[3]
                })
            return books
        except Exception as e:
            self.logger.error(f"Ошибка при получении всех книг: {e}")
            return []
    
    def get_books_with_content(self) -> List[Dict[str, Any]]:
        """
        Получение всех книг с текстом.
        
        Returns:
            List[Dict]: Список книг с текстом
        """
        try:
            self.cursor.execute("SELECT id, title, author, genre, LENGTH(content) as content_length FROM books_with_content ORDER BY id DESC")
            books = []
            for row in self.cursor.fetchall():
                pages = row[4] // 2000 + 1 if row[4] > 0 else 0
                books.append({
                    'id': row[0],
                    'title': row[1],
                    'author': row[2],
                    'genre': row[3],
                    'content_length': row[4],
                    'pages': pages
                })
            return books
        except Exception as e:
            self.logger.error(f"Ошибка при получении книг с текстом: {e}")
            return []
    
    def delete_book(self, book_id: int) -> bool:
        """
        Удаление книги по ID.
        
        Args:
            book_id (int): ID книги
            
        Returns:
            bool: True если удалено успешно
        """
        try:
            # Пробуем удалить из обычных книг
            self.cursor.execute("DELETE FROM books WHERE id = ?", (book_id,))
            
            # Если ничего не удалилось, пробуем из книг с текстом
            if self.cursor.rowcount == 0:
                self.cursor.execute("DELETE FROM books_with_content WHERE id = ?", (book_id,))
            
            self.conn.commit()
            return self.cursor.rowcount > 0
        except Exception as e:
            self.logger.error(f"Ошибка при удалении книги: {e}")
            return False
    
    def get_book_content(self, book_id: int, page: int = 1, page_size: int = 2000) -> Optional[Dict[str, Any]]:
        """
        Получение страницы текста книги.
        
        Args:
            book_id (int): ID книги
            page (int): Номер страницы (начинается с 1)
            page_size (int): Размер страницы в символах
            
        Returns:
            Optional[Dict]: Информация о странице или None
        """
        try:
            # Получаем общую информацию о книге
            self.cursor.execute(
                "SELECT id, title, author, genre, content FROM books_with_content WHERE id = ?",
                (book_id,)
            )
            row = self.cursor.fetchone()
            
            if not row:
                return None
            
            book_id, title, author, genre, full_content = row
            
            # Рассчитываем позиции для пагинации
            start_pos = (page - 1) * page_size
            end_pos = start_pos + page_size
            
            # Извлекаем часть текста
            content_part = full_content[start_pos:end_pos]
            
            # Рассчитываем общее количество страниц
            total_pages = (len(full_content) + page_size - 1) // page_size
            
            # Рассчитываем процент прочитанного
            progress_percent = min(100, int((page * page_size) / len(full_content) * 100)) if full_content else 0
            
            return {
                'id': book_id,
                'title': title,
                'author': author,
                'genre': genre,
                'content': content_part,
                'page': page,
                'total_pages': total_pages,
                'progress': f"{page}/{total_pages}",
                'percentage': progress_percent
            }
        except Exception as e:
            self.logger.error(f"Ошибка при получении текста книги: {e}")
            return None
    
    def save_reading_progress(self, user_id: int, book_id: int, page: int) -> bool:
        """
        Сохранение прогресса чтения книги.
        
        Args:
            user_id (int): ID пользователя
            book_id (int): ID книги
            page (int): Текущая страница
            
        Returns:
            bool: True если успешно сохранено
        """
        try:
            self.cursor.execute('''
                INSERT OR REPLACE INTO reading_progress (user_id, book_id, page, last_read)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ''', (user_id, book_id, page))
            self.conn.commit()
            return True
        except Exception as e:
            self.logger.error(f"Ошибка при сохранении прогресса: {e}")
            return False
    
    def get_reading_progress(self, user_id: int, book_id: int) -> Optional[int]:
        """
        Получение сохраненного прогресса чтения.
        
        Args:
            user_id (int): ID пользователя
            book_id (int): ID книги
            
        Returns:
            Optional[int]: Номер страницы или None
        """
        try:
            self.cursor.execute(
                "SELECT page FROM reading_progress WHERE user_id = ? AND book_id = ?",
                (user_id, book_id)
            )
            row = self.cursor.fetchone()
            return row[0] if row else None
        except Exception as e:
            self.logger.error(f"Ошибка при получении прогресса: {e}")
            return None
    
    def get_user_progress(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Получение всего прогресса пользователя.
        
        Args:
            user_id (int): ID пользователя
            
        Returns:
            List[Dict]: Список книг с прогрессом
        """
        try:
            self.cursor.execute('''
                SELECT rp.book_id, rp.page, b.title, b.author
                FROM reading_progress rp
                LEFT JOIN books_with_content b ON rp.book_id = b.id
                WHERE rp.user_id = ?
                ORDER BY rp.last_read DESC
            ''', (user_id,))
            
            progress = []
            for row in self.cursor.fetchall():
                progress.append({
                    'book_id': row[0],
                    'page': row[1],
                    'title': row[2] or "Неизвестная книга",
                    'author': row[3] or "Неизвестный автор"
                })
            return progress
        except Exception as e:
            self.logger.error(f"Ошибка при получении прогресса пользователя: {e}")
            return []
    
    def close(self):
        """Закрытие соединения с базой данных."""
        self.conn.close()
