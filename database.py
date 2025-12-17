# database.py
"""Менеджер базы данных для BookBot с поддержкой чтения книг."""

import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

class DatabaseManager:
    """Управление базой данных SQLite для книжного бота."""
    
    def __init__(self, db_name: str = 'telegram_books.db'):
        """
        Инициализация менеджера базы данных.
        
        Args:
            db_name (str): Имя файла базы данных
        """
        self.db_name = db_name
        self.init_database()
    
    def init_database(self):
        """Инициализация структуры базы данных."""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # Таблица книг (основная)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                genre TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(title, author)  -- Предотвращение дубликатов
            )
        ''')
        
        # Таблица содержания книг (для чтения)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS book_contents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id INTEGER NOT NULL UNIQUE,
                content TEXT NOT NULL,
                content_length INTEGER,
                pages INTEGER DEFAULT 1,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
            )
        ''')
        
        # Таблица прогресса чтения пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reading_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                book_id INTEGER NOT NULL,
                current_page INTEGER DEFAULT 1,
                last_read TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, book_id),
                FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
            )
        ''')
        
        # Индексы для ускорения поиска
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_books_title ON books(title)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_books_author ON books(author)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_books_genre ON books(genre)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_progress_user ON reading_progress(user_id)')
        
        conn.commit()
        conn.close()
        
        print(f"✅ База данных '{self.db_name}' инициализирована")
    
    # ========== МЕТОДЫ ДЛЯ ОБЫЧНЫХ КНИГ ==========
    
    def add_book(self, title: str, author: str, genre: str = 'Не указан') -> int:
        """
        Добавить обычную книгу (без текста).
        
        Args:
            title (str): Название книги
            author (str): Автор книги
            genre (str): Жанр книги
            
        Returns:
            int: ID добавленной книги
            
        Raises:
            sqlite3.IntegrityError: Если книга уже существует
        """
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                'INSERT INTO books (title, author, genre) VALUES (?, ?, ?)',
                (title, author, genre)
            )
            book_id = cursor.lastrowid
            conn.commit()
            return book_id
        except sqlite3.IntegrityError:
            # Книга уже существует, находим её ID
            cursor.execute(
                'SELECT id FROM books WHERE title = ? AND author = ?',
                (title, author)
            )
            result = cursor.fetchone()
            if result:
                raise Exception(f"Книга '{title}' уже существует (ID: {result[0]})")
            else:
                raise Exception("Неизвестная ошибка при добавлении книги")
        finally:
            conn.close()
    
    def get_all_books(self) -> List[Dict[str, Any]]:
        """
        Получить все книги из базы.
        
        Returns:
            List[Dict]: Список книг
        """
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT b.id, b.title, b.author, b.genre, b.created_at,
                   CASE WHEN bc.id IS NOT NULL THEN 1 ELSE 0 END as has_content
            FROM books b
            LEFT JOIN book_contents bc ON b.id = bc.book_id
            ORDER BY b.id DESC
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
                'created_at': row[4],
                'has_content': bool(row[5])
            })
        
        return books
    
    def get_book(self, book_id: int) -> Optional[Dict[str, Any]]:
        """
        Получить книгу по ID.
        
        Args:
            book_id (int): ID книги
            
        Returns:
            Dict: Информация о книге или None
        """
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT b.id, b.title, b.author, b.genre, b.created_at,
                   bc.content_length, bc.pages
            FROM books b
            LEFT JOIN book_contents bc ON b.id = bc.book_id
            WHERE b.id = ?
        ''', (book_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'id': row[0],
                'title': row[1],
                'author': row[2],
                'genre': row[3],
                'created_at': row[4],
                'has_content': row[5] is not None,
                'content_length': row[5] if row[5] else 0,
                'pages': row[6] if row[6] else 0
            }
        return None
    
    def search_books(self, query: str) -> List[Dict[str, Any]]:
        """
        Поиск книг по названию, автору или жанру.
        
        Args:
            query (str): Поисковый запрос
            
        Returns:
            List[Dict]: Найденные книги
        """
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        search_term = f'%{query}%'
        cursor.execute('''
            SELECT b.id, b.title, b.author, b.genre, b.created_at,
                   CASE WHEN bc.id IS NOT NULL THEN 1 ELSE 0 END as has_content
            FROM books b
            LEFT JOIN book_contents bc ON b.id = bc.book_id
            WHERE b.title LIKE ? OR b.author LIKE ? OR b.genre LIKE ?
            ORDER BY b.title
        ''', (search_term, search_term, search_term))
        
        rows = cursor.fetchall()
        conn.close()
        
        books = []
        for row in rows:
            books.append({
                'id': row[0],
                'title': row[1],
                'author': row[2],
                'genre': row[3],
                'created_at': row[4],
                'has_content': bool(row[5])
            })
        
        return books
    
    def delete_book(self, book_id: int) -> bool:
        """
        Удалить книгу.
        
        Args:
            book_id (int): ID книги
            
        Returns:
            bool: True если книга удалена, False если не найдена
        """
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM books WHERE id = ?', (book_id,))
        deleted = cursor.rowcount > 0
        
        conn.commit()
        conn.close()
        
        return deleted
    
    def book_exists(self, title: str, author: str) -> bool:
        """
        Проверить, существует ли книга.
        
        Args:
            title (str): Название книги
            author (str): Автор книги
            
        Returns:
            bool: True если книга существует
        """
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT id FROM books WHERE title = ? AND author = ?',
            (title, author)
        )
        
        exists = cursor.fetchone() is not None
        conn.close()
        
        return exists
    
    # ========== МЕТОДЫ ДЛЯ КНИГ С ТЕКСТОМ ==========
    
    def add_book_with_content(self, title: str, author: str, genre: str, content: str) -> int:
        """
        Добавить книгу с текстом.
        
        Args:
            title (str): Название книги
            author (str): Автор книги
            genre (str): Жанр книги
            content (str): Текст книги
            
        Returns:
            int: ID добавленной книги
        """
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            # Сначала проверяем, нет ли уже такой книги
            if self.book_exists(title, author):
                raise Exception(f"Книга '{title}' уже существует")
            
            # Добавляем книгу
            cursor.execute(
                'INSERT INTO books (title, author, genre) VALUES (?, ?, ?)',
                (title, author, genre)
            )
            book_id = cursor.lastrowid
            
            # Рассчитываем количество страниц (примерно 1500 символов на страницу)
            content_length = len(content)
            pages = max(1, (content_length + 1499) // 1500)  # Округление вверх
            
            # Добавляем текст книги
            cursor.execute(
                '''INSERT INTO book_contents 
                   (book_id, content, content_length, pages) 
                   VALUES (?, ?, ?, ?)''',
                (book_id, content, content_length, pages)
            )
            
            conn.commit()
            return book_id
            
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def get_books_with_content(self) -> List[Dict[str, Any]]:
        """
        Получить все книги, у которых есть текст.
        
        Returns:
            List[Dict]: Книги с текстом
        """
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT b.id, b.title, b.author, b.genre, 
                   bc.content_length, bc.pages, bc.added_at
            FROM books b
            INNER JOIN book_contents bc ON b.id = bc.book_id
            ORDER BY b.title
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
                'content_length': row[4],
                'pages': row[5],
                'added_at': row[6]
            })
        
        return books
    
    def get_book_content(self, book_id: int) -> Optional[str]:
        """
        Получить текст книги.
        
        Args:
            book_id (int): ID книги
            
        Returns:
            str: Текст книги или None
        """
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT content FROM book_contents WHERE book_id = ?',
            (book_id,)
        )
        
        row = cursor.fetchone()
        conn.close()
        
        return row[0] if row else None
    
    def get_book_page(self, book_id: int, page: int = 1, page_size: int = 1500) -> Optional[Dict[str, Any]]:
        """
        Получить конкретную страницу книги.
        
        Args:
            book_id (int): ID книги
            page (int): Номер страницы (начиная с 1)
            page_size (int): Размер страницы в символах
            
        Returns:
            Dict: Информация о странице
        """
        content = self.get_book_content(book_id)
        if not content:
            return None
        
        book_info = self.get_book(book_id)
        if not book_info:
            return None
        
        content_length = len(content)
        total_pages = max(1, (content_length + page_size - 1) // page_size)
        
        # Корректируем номер страницы
        if page < 1:
            page = 1
        elif page > total_pages:
            page = total_pages
        
        # Вычисляем диапазон символов для страницы
        start_idx = (page - 1) * page_size
        end_idx = min(start_idx + page_size, content_length)
        
        page_content = content[start_idx:end_idx]
        
        return {
            'book_id': book_id,
            'title': book_info['title'],
            'author': book_info['author'],
            'page': page,
            'total_pages': total_pages,
            'content': page_content,
            'start_char': start_idx + 1,
            'end_char': end_idx,
            'total_chars': content_length,
            'progress': f"{start_idx+1}-{end_idx} из {content_length}",
            'percentage': int((end_idx / content_length) * 100)
        }
    
    def add_content_to_existing_book(self, book_id: int, content: str) -> bool:
        """
        Добавить текст к существующей книге.
        
        Args:
            book_id (int): ID книги
            content (str): Текст книги
            
        Returns:
            bool: True если успешно
        """
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            # Проверяем, существует ли книга
            cursor.execute('SELECT id FROM books WHERE id = ?', (book_id,))
            if not cursor.fetchone():
                return False
            
            # Проверяем, нет ли уже текста
            cursor.execute('SELECT id FROM book_contents WHERE book_id = ?', (book_id,))
            if cursor.fetchone():
                # Обновляем существующий текст
                content_length = len(content)
                pages = max(1, (content_length + 1499) // 1500)
                
                cursor.execute(
                    '''UPDATE book_contents 
                       SET content = ?, content_length = ?, pages = ? 
                       WHERE book_id = ?''',
                    (content, content_length, pages, book_id)
                )
            else:
                # Добавляем новый текст
                content_length = len(content)
                pages = max(1, (content_length + 1499) // 1500)
                
                cursor.execute(
                    '''INSERT INTO book_contents 
                       (book_id, content, content_length, pages) 
                       VALUES (?, ?, ?, ?)''',
                    (book_id, content, content_length, pages)
                )
            
            conn.commit()
            return True
            
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    # ========== МЕТОДЫ ДЛЯ ПРОГРЕССА ЧТЕНИЯ ==========
    
    def save_reading_progress(self, user_id: int, book_id: int, current_page: int = 1) -> bool:
        """
        Сохранить прогресс чтения пользователя.
        
        Args:
            user_id (int): ID пользователя Telegram
            book_id (int): ID книги
            current_page (int): Текущая страница
            
        Returns:
            bool: True если успешно
        """
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO reading_progress 
                (user_id, book_id, current_page, last_read) 
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ''', (user_id, book_id, current_page))
            
            conn.commit()
            return True
            
        except Exception as e:
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def get_reading_progress(self, user_id: int, book_id: int) -> int:
        """
        Получить сохраненный прогресс чтения.
        
        Args:
            user_id (int): ID пользователя Telegram
            book_id (int): ID книги
            
        Returns:
            int: Номер последней прочитанной страницы (0 если нет прогресса)
        """
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT current_page FROM reading_progress WHERE user_id = ? AND book_id = ?',
            (user_id, book_id)
        )
        
        row = cursor.fetchone()
        conn.close()
        
        return row[0] if row else 0
    
    def get_user_reading_history(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Получить историю чтения пользователя.
        
        Args:
            user_id (int): ID пользователя Telegram
            
        Returns:
            List[Dict]: История чтения
        """
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT rp.book_id, rp.current_page, rp.last_read,
                   b.title, b.author, bc.pages
            FROM reading_progress rp
            JOIN books b ON rp.book_id = b.id
            LEFT JOIN book_contents bc ON b.id = bc.book_id
            WHERE rp.user_id = ?
            ORDER BY rp.last_read DESC
        ''', (user_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        history = []
        for row in rows:
            history.append({
                'book_id': row[0],
                'current_page': row[1],
                'last_read': row[2],
                'title': row[3],
                'author': row[4],
                'total_pages': row[5] if row[5] else 0,
                'progress_percentage': int((row[1] / (row[5] if row[5] else 1)) * 100) if row[5] else 0
            })
        
        return history
    
    # ========== СЛУЖЕБНЫЕ МЕТОДЫ ==========
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Получить статистику библиотеки.
        
        Returns:
            Dict: Статистические данные
        """
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        stats = {}
        
        # Общее количество книг
        cursor.execute('SELECT COUNT(*) FROM books')
        stats['total_books'] = cursor.fetchone()[0]
        
        # Книги с текстом
        cursor.execute('SELECT COUNT(*) FROM book_contents')
        stats['books_with_content'] = cursor.fetchone()[0]
        
        # Книги без текста
        stats['books_without_content'] = stats['total_books'] - stats['books_with_content']
        
        # Уникальные авторы
        cursor.execute('SELECT COUNT(DISTINCT author) FROM books')
        stats['unique_authors'] = cursor.fetchone()[0]
        
        # Уникальные жанры
        cursor.execute('SELECT COUNT(DISTINCT genre) FROM books WHERE genre IS NOT NULL')
        stats['unique_genres'] = cursor.fetchone()[0]
        
        # Топ жанров
        cursor.execute('''
            SELECT genre, COUNT(*) as count 
            FROM books 
            WHERE genre IS NOT NULL 
            GROUP BY genre 
            ORDER BY count DESC 
            LIMIT 5
        ''')
        stats['top_genres'] = [{'genre': row[0], 'count': row[1]} for row in cursor.fetchall()]
        
        # Топ авторов
        cursor.execute('''
            SELECT author, COUNT(*) as count 
            FROM books 
            GROUP BY author 
            ORDER BY count DESC 
            LIMIT 5
        ''')
        stats['top_authors'] = [{'author': row[0], 'count': row[1]} for row in cursor.fetchall()]
        
        # Общий объем текста
        cursor.execute('SELECT SUM(content_length) FROM book_contents')
        total_chars = cursor.fetchone()[0] or 0
        stats['total_characters'] = total_chars
        stats['total_pages'] = max(1, total_chars // 1500)  # Примерный расчет страниц
        
        conn.close()
        
        return stats
    
    def backup_database(self, backup_path: str = None) -> str:
        """
        Создать резервную копию базы данных.
        
        Args:
            backup_path (str): Путь для сохранения резервной копии
            
        Returns:
            str: Путь к созданной резервной копии
        """
        if backup_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = f'{self.db_name}.backup_{timestamp}'
        
        conn = sqlite3.connect(self.db_name)
        backup_conn = sqlite3.connect(backup_path)
        
        conn.backup(backup_conn)
        
        backup_conn.close()
        conn.close()
        
        return backup_path
    
    def clear_database(self) -> bool:
        """
        Очистить всю базу данных (только для тестов!).
        
        Returns:
            bool: True если успешно
        """
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            # Удаляем данные в правильном порядке (с учетом внешних ключей)
            cursor.execute('DELETE FROM reading_progress')
            cursor.execute('DELETE FROM book_contents')
            cursor.execute('DELETE FROM books')
            
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            return False
        finally:
            conn.close()


# ========== ТЕСТОВЫЕ ФУНКЦИИ ==========

def test_database():
    """Тестирование функциональности базы данных."""
    print("🧪 Тестирование DatabaseManager...")
    
    # Создаем временную базу для тестов
    test_db = DatabaseManager('test_books.db')
    
    try:
        # Тест 1: Добавление обычной книги
        print("1. Добавление обычной книги...")
        book_id = test_db.add_book("Тестовая книга", "Тестовый автор", "Тест")
        print(f"   ✅ Книга добавлена, ID: {book_id}")
        
        # Тест 2: Добавление книги с текстом
        print("2. Добавление книги с текстом...")
        content = "Это тестовый текст книги. " * 100  # Создаем длинный текст
        book_id2 = test_db.add_book_with_content(
            "Книга с текстом", 
            "Автор книги", 
            "Роман", 
            content
        )
        print(f"   ✅ Книга с текстом добавлена, ID: {book_id2}")
        
        # Тест 3: Получение всех книг
        print("3. Получение всех книг...")
        books = test_db.get_all_books()
        print(f"   ✅ Найдено книг: {len(books)}")
        
        # Тест 4: Получение книг с текстом
        print("4. Получение книг с текстом...")
        books_with_content = test_db.get_books_with_content()
        print(f"   ✅ Книг с текстом: {len(books_with_content)}")
        
        # Тест 5: Получение текста книги
        print("5. Получение текста книги...")
        book_content = test_db.get_book_content(book_id2)
        print(f"   ✅ Текст получен, длина: {len(book_content)} символов")
        
        # Тест 6: Получение страницы книги
        print("6. Получение страницы книги...")
        page = test_db.get_book_page(book_id2, 1)
        print(f"   ✅ Страница получена: {page['page']}/{page['total_pages']}")
        
        # Тест 7: Сохранение прогресса
        print("7. Сохранение прогресса чтения...")
        test_db.save_reading_progress(12345, book_id2, 5)
        progress = test_db.get_reading_progress(12345, book_id2)
        print(f"   ✅ Прогресс сохранен: страница {progress}")
        
        # Тест 8: Поиск книг
        print("8. Поиск книг...")
        search_results = test_db.search_books("тест")
        print(f"   ✅ Найдено по запросу 'тест': {len(search_results)}")
        
        # Тест 9: Статистика
        print("9. Получение статистики...")
        stats = test_db.get_statistics()
        print(f"   ✅ Статистика: {stats['total_books']} книг, "
              f"{stats['books_with_content']} с текстом")
        
        print("\n✅ Все тесты пройдены успешно!")
        
    except Exception as e:
        print(f"❌ Ошибка тестирования: {e}")
    
    finally:
        # Удаляем тестовую базу
        try:
            os.remove('test_books.db')
            print("🗑️ Тестовая база удалена")
        except:
            pass


if __name__ == "__main__":
    # Если файл запущен напрямую, выполняем тесты
    test_database()
