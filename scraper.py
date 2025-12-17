import requests
from bs4 import BeautifulSoup
import sqlite3
import time

def init_scraper_db():
    """Инициализация базы данных для парсера."""
    conn = sqlite3.connect('telegram_books.db')
    cursor = conn.cursor()
    
    # Создаем таблицу книг, если ее нет
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            genre TEXT,
            description TEXT,
            source_url TEXT,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def scrape_litres_sample():
    """
    Пример парсера для сайта litres.ru (учебный пример).
    В реальном проекте нужно адаптировать под конкретный сайт.
    """
    try:
        # Пример URL (нужно заменить на реальный)
        url = "https://www.litres.ru/genre/knigi-"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Здесь должна быть логика парсинга конкретного сайта
        # Это пример - нужно адаптировать под реальную структуру сайта
        
        books = []
        
        # Пример извлечения данных (заглушка)
        sample_books = [
            {"title": "Преступление и наказание", "author": "Фёдор Достоевский", "genre": "Классика"},
            {"title": "Мастер и Маргарита", "author": "Михаил Булгаков", "genre": "Классика"},
            {"title": "1984", "author": "Джордж Оруэлл", "genre": "Антиутопия"},
        ]
        
        conn = sqlite3.connect('telegram_books.db')
        cursor = conn.cursor()
        
        for book in sample_books:
            try:
                cursor.execute('''
                    INSERT OR IGNORE INTO books (title, author, genre)
                    VALUES (?, ?, ?)
                ''', (book['title'], book['author'], book['genre']))
            except Exception as e:
                print(f"Error inserting book {book['title']}: {e}")
        
        conn.commit()
        conn.close()
        print(f"Добавлено {len(sample_books)} примеров книг")
        
    except Exception as e:
        print(f"Ошибка при парсинге: {e}")

if __name__ == '__main__':
    init_scraper_db()
    scrape_litres_sample()
