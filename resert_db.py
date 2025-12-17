import os
import sys
import sqlite3

def reset_database():
    """Полный сброс базы данных."""
    db_path = 'telegram_books.db'
    
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"[DELETED] Old database: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Создаем таблицы
    cursor.execute('''
        CREATE TABLE books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            genre TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE books_with_content (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            genre TEXT,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE reading_progress (
            user_id INTEGER,
            book_id INTEGER,
            page INTEGER DEFAULT 1,
            last_read TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, book_id),
            FOREIGN KEY (book_id) REFERENCES books_with_content(id)
        )
    ''')
    
    # Добавляем тестовые данные
    cursor.execute("INSERT INTO books (title, author, genre) VALUES (?, ?, ?)", 
                   ("Vlastelin kolets", "Tolkin", "Fantasy"))
    cursor.execute("INSERT INTO books (title, author, genre) VALUES (?, ?, ?)", 
                   ("1984", "Orwell", "Antitopia"))
    
    cursor.execute("INSERT INTO books_with_content (title, author, genre, content) VALUES (?, ?, ?, ?)", 
                   ("Test Book", "Test Author", "Test", "This is a test book for reading check. " * 50))
    
    conn.commit()
    conn.close()
    
    print("[SUCCESS] Database created with test data")
    print("  Simple books: 2")
    print("  Books with content: 1")

if __name__ == "__main__":
    # Устанавливаем правильную кодировку для Windows
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    reset_database()
