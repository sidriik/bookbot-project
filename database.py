# -*- coding: utf-8 -*-
"""Модуль для работы с базой данных SQLite для проекта BookBot."""

import sqlite3
import os
import sys
from typing import List, Optional, Dict, Any

# Исправление кодировки вывода для Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

class DatabaseManager:
    """Менеджер базы данных для хранения книг."""
    
    def __init__(self, db_path: str = "books.db"):
        """
        Инициализация менеджера базы данных.
        
        Args:
            db_path (str): Путь к файлу базы данных
        """
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Инициализация таблиц в базе данных."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Таблица книг (основная - для учета)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                genre TEXT NOT NULL
            )
        ''')
        
        # Таблица книг с текстом (для чтения)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS books_with_content (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                genre TEXT NOT NULL,
                content TEXT NOT NULL,
                page_size INTEGER DEFAULT 2000,
                added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE,
                username TEXT
            )
        ''')
        
        # Таблица списков прочтения
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reading_lists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                book_id INTEGER NOT NULL,
                status TEXT DEFAULT 'reading',
                rating INTEGER CHECK(rating >= 1 AND rating <= 5),
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (book_id) REFERENCES books(id),
                UNIQUE(user_id, book_id)
            )
        ''')
        
        # Таблица для отслеживания прогресса чтения
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reading_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                book_id INTEGER NOT NULL,
                current_page INTEGER DEFAULT 1,
                last_read TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (book_id) REFERENCES books_with_content(id),
                UNIQUE(user_id, book_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    # ========== ОСНОВНЫЕ МЕТОДЫ ДЛЯ УЧЕТА КНИГ ==========
    
    def add_book(self, title: str, author: str, genre: str) -> int:
        """
        Добавление новой книги в базу данных (без текста).
        
        Args:
            title (str): Название книги
            author (str): Автор книги
            genre (str): Жанр книги
            
        Returns:
            int: ID добавленной книги
            
        Raises:
            ValueError: Если книга уже существует
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Проверяем, существует ли книга
        cursor.execute(
            "SELECT id FROM books WHERE title = ? AND author = ?",
            (title, author)
        )
        if cursor.fetchone():
            conn.close()
            raise ValueError(f"Книга '{title}' уже существует")
        
        # Добавляем книгу
        cursor.execute(
            "INSERT INTO books (title, author, genre) VALUES (?, ?, ?)",
            (title, author, genre)
        )
        conn.commit()
        book_id = cursor.lastrowid
        conn.close()
        return book_id
    
    def get_book(self, book_id: int) -> Optional[Dict[str, Any]]:
        """
        Получение информации о книге по ID.
        
        Args:
            book_id (int): ID книги
            
        Returns:
            Optional[Dict]: Информация о книге или None если не найдена
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM books WHERE id = ?", (book_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'id': row[0],
                'title': row[1],
                'author': row[2],
                'genre': row[3]
            }
        return None
    
    def search_books(self, query: str, search_type: str = None) -> List[Dict[str, Any]]:
        """
        Поиск книг по различным критериям.
        
        Args:
            query (str): Поисковый запрос
            search_type (str, optional): Тип поиска ('title', 'author', 'genre')
                                         Если None, ищет по всем полям
            
        Returns:
            List[Dict]: Список найденных книг
            
        Raises:
            ValueError: Если указан неверный тип поиска
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if search_type:
            # Если указан тип поиска
            valid_types = ['title', 'author', 'genre']
            if search_type not in valid_types:
                conn.close()
                raise ValueError(f"Тип поиска должен быть одним из: {valid_types}")
            
            # Для жанра ищем точное совпадение, для остальных - подстроку
            if search_type == 'genre':
                cursor.execute(
                    f"SELECT * FROM books WHERE {search_type} = ? ORDER BY title",
                    (query,)
                )
            else:
                cursor.execute(
                    f"SELECT * FROM books WHERE {search_type} LIKE ? ORDER BY title",
                    (f'%{query}%',)
                )
        else:
            # Поиск по всем полям (для telegram_bot.py)
            cursor.execute('''
                SELECT * FROM books 
                WHERE title LIKE ? OR author LIKE ? OR genre LIKE ?
                ORDER BY title
            ''', (f'%{query}%', f'%{query}%', f'%{query}%'))
        
        rows = cursor.fetchall()
        conn.close()
        
        results = []
        for row in rows:
            results.append({
                'id': row[0],
                'title': row[1],
                'author': row[2],
                'genre': row[3]
            })
        return results
    
    def get_all_books(self) -> List[Dict[str, Any]]:
        """
        Получение всех книг из базы данных.
        
        Returns:
            List[Dict]: Все книги
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM books ORDER BY title")
        rows = cursor.fetchall()
        conn.close()
        
        books = []
        for row in rows:
            books.append({
                'id': row[0],
                'title': row[1],
                'author': row[2],
                'genre': row[3]
            })
        return books
    
    def delete_book(self, book_id: int) -> bool:
        """
        Удаление книги из базы данных.
        
        Args:
            book_id (int): ID книги
            
        Returns:
            bool: True если успешно удалено
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Сначала удаляем связанные записи в reading_lists
        cursor.execute("DELETE FROM reading_lists WHERE book_id = ?", (book_id,))
        cursor.execute("DELETE FROM books WHERE id = ?", (book_id,))
        
        conn.commit()
        deleted = cursor.rowcount > 0
        conn.close()
        
        return deleted
    
    # ========== МЕТОДЫ ДЛЯ РАБОТЫ С ПОЛЬЗОВАТЕЛЯМИ ==========
    
    def add_user(self, telegram_id: int, username: str = None) -> int:
        """
        Добавление нового пользователя.
        
        Args:
            telegram_id (int): ID пользователя в Telegram
            username (str, optional): Имя пользователя
            
        Returns:
            int: ID пользователя в базе данных
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Проверяем, существует ли пользователь
        cursor.execute(
            "SELECT id FROM users WHERE telegram_id = ?",
            (telegram_id,)
        )
        existing = cursor.fetchone()
        
        if existing:
            conn.close()
            return existing[0]
        
        # Добавляем нового пользователя
        cursor.execute(
            "INSERT INTO users (telegram_id, username) VALUES (?, ?)",
            (telegram_id, username)
        )
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        return user_id
    
    def add_to_reading_list(self, user_id: int, book_id: int) -> bool:
        """
        Добавление книги в список прочтения пользователя.
        
        Args:
            user_id (int): ID пользователя
            book_id (int): ID книги
            
        Returns:
            bool: True если успешно добавлено
            
        Raises:
            ValueError: Если книга уже в списке пользователя
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Проверяем, есть ли уже книга в списке
        cursor.execute(
            "SELECT id FROM reading_lists WHERE user_id = ? AND book_id = ?",
            (user_id, book_id)
        )
        if cursor.fetchone():
            conn.close()
            raise ValueError("Книга уже в списке прочтения")
        
        # Добавляем в список
        cursor.execute(
            "INSERT INTO reading_lists (user_id, book_id) VALUES (?, ?)",
            (user_id, book_id)
        )
        conn.commit()
        conn.close()
        return True
    
    def rate_book(self, user_id: int, book_id: int, rating: int) -> bool:
        """
        Оценка книги пользователем.
        
        Args:
            user_id (int): ID пользователя
            book_id (int): ID книги
            rating (int): Оценка от 1 до 5
            
        Returns:
            bool: True если оценка успешно сохранена
            
        Raises:
            ValueError: Если оценка не в диапазоне 1-5 или книга не в списке пользователя
        """
        if rating < 1 or rating > 5:
            raise ValueError("Оценка должна быть от 1 до 5")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Проверяем, есть ли книга в списке пользователя
        cursor.execute(
            "SELECT id FROM reading_lists WHERE user_id = ? AND book_id = ?",
            (user_id, book_id)
        )
        if not cursor.fetchone():
            conn.close()
            raise ValueError("Книга должна быть в списке прочтения для оценки")
        
        # Обновляем оценку
        cursor.execute(
            "UPDATE reading_lists SET rating = ? WHERE user_id = ? AND book_id = ?",
            (rating, user_id, book_id)
        )
        conn.commit()
        updated = cursor.rowcount > 0
        conn.close()
        return updated
    
    # ========== МЕТОДЫ ДЛЯ ЧТЕНИЯ КНИГ ==========
    
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
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO books_with_content (title, author, genre, content) VALUES (?, ?, ?, ?)",
            (title, author, genre, content)
        )
        
        conn.commit()
        book_id = cursor.lastrowid
        conn.close()
        return book_id
    
    def get_book_content(self, book_id: int, page: int = 1) -> Optional[Dict[str, Any]]:
        """
        Получение страницы книги.
        
        Args:
            book_id (int): ID книги
            page (int): Номер страницы (начинается с 1)
            
        Returns:
            Dict: Информация о странице книги или None если книга не найдена
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM books_with_content WHERE id = ?", (book_id,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return None
        
        # Извлекаем данные
        book_id, title, author, genre, content, page_size, added_date = row
        
        # Устанавливаем размер страницы по умолчанию
        if not page_size:
            page_size = 2000
        
        # Вычисляем границы страницы
        content_length = len(content)
        start_index = (page - 1) * page_size
        end_index = min(start_index + page_size, content_length)
        
        # Получаем текст страницы
        page_content = content[start_index:end_index]
        
        # Вычисляем общее количество страниц
        total_pages = content_length // page_size
        if content_length % page_size > 0:
            total_pages += 1
        
        # Если запрошена несуществующая страница
        if page > total_pages or page < 1:
            conn.close()
            return None
        
        conn.close()
        
        return {
            'id': book_id,
            'title': title,
            'author': author,
            'genre': genre,
            'content': page_content,
            'page': page,
            'total_pages': total_pages,
            'page_size': page_size,
            'progress': f"{min(end_index, content_length)}/{content_length}",
            'percentage': round((end_index / content_length) * 100, 1) if content_length > 0 else 0
        }
    
    def save_reading_progress(self, user_id: int, book_id: int, page: int) -> bool:
        """
        Сохранение прогресса чтения пользователя.
        
        Args:
            user_id (int): ID пользователя
            book_id (int): ID книги
            page (int): Текущая страница
            
        Returns:
            bool: True если успешно сохранено
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Вставляем или обновляем прогресс
            cursor.execute('''
                INSERT INTO reading_progress (user_id, book_id, current_page)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id, book_id) 
                DO UPDATE SET current_page = ?, last_read = CURRENT_TIMESTAMP
            ''', (user_id, book_id, page, page))
            
            conn.commit()
            success = cursor.rowcount > 0
            conn.close()
            return success
        except Exception as e:
            conn.close()
            raise e
    
    def get_reading_progress(self, user_id: int, book_id: int) -> Optional[int]:
        """
        Получение прогресса чтения пользователя.
        
        Args:
            user_id (int): ID пользователя
            book_id (int): ID книги
            
        Returns:
            int: Номер последней прочитанной страницы или None
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT current_page FROM reading_progress WHERE user_id = ? AND book_id = ?",
            (user_id, book_id)
        )
        
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else None
    
    def get_books_with_content(self) -> List[Dict[str, Any]]:
        """
        Получение всех книг с текстом.
        
        Returns:
            List[Dict]: Список книг с текстом
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, title, author, genre, 
                   LENGTH(content) as text_length,
                   added_date 
            FROM books_with_content 
            ORDER BY title
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        books = []
        for row in rows:
            books.append({
                'id': row[0],
                'title': row[1],
                'author': row[2],
                'genre': row[3],
                'text_length': row[4],
                'pages': (row[4] // 2000) + 1 if row[4] > 0 else 1,
                'added_date': row[5]
            })
        
        return books
    
    def search_books_with_content(self, query: str) -> List[Dict[str, Any]]:
        """
        Поиск книг с текстом.
        
        Args:
            query (str): Поисковый запрос
            
        Returns:
            List[Dict]: Список найденных книг
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, title, author, genre 
            FROM books_with_content 
            WHERE title LIKE ? OR author LIKE ? OR genre LIKE ?
            ORDER BY title
        ''', (f'%{query}%', f'%{query}%', f'%{query}%'))
        
        rows = cursor.fetchall()
        conn.close()
        
        results = []
        for row in rows:
            results.append({
                'id': row[0],
                'title': row[1],
                'author': row[2],
                'genre': row[3]
            })
        return results
    
    # ========== ТЕСТЫ ==========
    
    @staticmethod
    def simple_test():
        """Простой тест без эмодзи."""
        test_db = "simple_test.db"
        if os.path.exists(test_db):
            os.remove(test_db)
        
        print("=" * 50)
        print("ПРОСТОЙ ТЕСТ БАЗЫ ДАННЫХ")
        print("=" * 50)
        
        db = DatabaseManager(test_db)
        
        # Тест 1: Кириллица
        print("\n1. Тест кириллицы:")
        book_id = db.add_book("Война и мир", "Лев Толстой", "Роман")
        print(f"   Книга добавлена, ID: {book_id}")
        
        book = db.get_book(book_id)
        if book and book['title']:
            print(f"   Получен заголовок: длина={len(book['title'])} символов")
            # Проверяем первые символы
            if book['title']:
                chars = [ord(c) for c in book['title'][:5]]
                print(f"   Коды первых 5 символов: {chars}")
                if any(c > 127 for c in chars):
                    print("   РЕЗУЛЬТАТ: Кириллица сохранена корректно!")
                else:
                    print("   РЕЗУЛЬТАТ: Возможно проблемы с кириллицей")
        
        # Тест 2: Поиск
        print("\n2. Тест поиска:")
        results = db.search_books('Толстой', 'author')
        print(f"   Найдено книг по автору 'Толстой': {len(results)}")
        
        # Тест 3: Латинские символы
        print("\n3. Тест латинских символов:")
        book_id2 = db.add_book("1984", "George Orwell", "Dystopia")
        book2 = db.get_book(book_id2)
        print(f"   Английская книга: '{book2['title']}'")
        
        # Тест 4: Поиск без указания типа
        print("\n4. Тест общего поиска:")
        results2 = db.search_books('1984')
        print(f"   Найдено книг по запросу '1984': {len(results2)}")
        
        # Тест 5: Книги с текстом
        print("\n5. Тест книг с текстом:")
        content_id = db.add_book_with_content(
            "Тестовая книга", 
            "Тестовый автор", 
            "Тест", 
            "Это тестовый текст книги для проверки функционала чтения."
        )
        print(f"   Книга с текстом добавлена, ID: {content_id}")
        
        # Получаем текст
        book_content = db.get_book_content(content_id, 1)
        if book_content:
            print(f"   Получена страница: {len(book_content['content'])} символов")
            print(f"   Прогресс: {book_content['progress']}")
        
        print("\n" + "=" * 50)
        print("ТЕСТ ЗАВЕРШЕН")
        print("=" * 50)
        
        # Удаляем тестовый файл
        if os.path.exists(test_db):
            os.remove(test_db)


if __name__ == "__main__":
    DatabaseManager.simple_test()
