# -*- coding: utf-8 -*-
"""Модели для работы с пользователями."""

from typing import Dict, Any, List

class User:
    """Класс для управления данными пользователя в памяти."""
    
    def __init__(self):
        """Инициализация хранилища пользователей."""
        self.user: Dict[int, Dict[int, Dict[str, Any]]] = {}
    
    def add_book(self, user_id: int, book_id: int, status: str) -> bool:
        """
        Добавление книги пользователю.
        
        Args:
            user_id (int): ID пользователя
            book_id (int): ID книги
            status (str): Статус книги
            
        Returns:
            bool: True если успешно добавлено
        """
        try:
            allowed_status = ["planned", "reading", "completed", "dropped"]
            if status not in allowed_status:
                return ValueError(f"Not allowed status")
            if user_id not in self.user:
                self.user[user_id] = {}
            if book_id in self.user[user_id]:
                return False
            self.user[user_id][book_id] = {'status': status, 'rating': None}
            return True
        except Exception as e:
            print(f"Error in add_book: {e}")
            return False
    
    def rate_book(self, user_id: int, book_id: int, rating: int) -> bool:
        """
        Оценка книги пользователем.
        
        Args:
            user_id (int): ID пользователя
            book_id (int): ID книги
            rating (int): Оценка от 1 до 5
            
        Returns:
            bool: True если оценка успешно сохранена
        """
        try:
            if rating < 1 or rating > 5:
                raise ValueError("Rating must be between 1 and 5")
            if user_id not in self.user:
                return False
            if book_id not in self.user[user_id]:
                return False
            self.user[user_id][book_id]['rating'] = rating
            return True
        except Exception as e:
            print(f"Error in rate_book: {e}")
            return False
    
    def get_users_book(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Получение всех книг пользователя.
        
        Args:
            user_id (int): ID пользователя
            
        Returns:
            List[Dict]: Список книг пользователя
        """
        try:
            if user_id not in self.user:
                return []
            books = []
            for book_id, book_data in self.user[user_id].items():
                books.append({'book_id': book_id, 'status': book_data['status'], 'rating': book_data['rating']})
            return books
        except Exception as e:
            print(f"Error in get_users_book: {e}")
            return []
    
    def remove_book(self, user_id: int, book_id: int) -> bool:
        """
        Удаление книги у пользователя.
        
        Args:
            user_id (int): ID пользователя
            book_id (int): ID книги
            
        Returns:
            bool: True если успешно удалено
        """
        try:
            if user_id not in self.user:
                return False
            if book_id not in self.user[user_id]:
                return False
            del self.user[user_id][book_id]
            if len(self.user[user_id]) == 0:
                del self.user[user_id]
            return True
        except Exception as e:
            print(f"Error in remove_book: {e}")
            return False
    
    def get_books_by_status(self, user_id: int, status: str) -> List[Dict[str, Any]]:
        """
        Получение книг пользователя по статусу.
        
        Args:
            user_id (int): ID пользователя
            status (str): Статус книги
            
        Returns:
            List[Dict]: Список книг с указанным статусом
        """
        if user_id not in self.user:
            return []
        books = []
        for book_id, data in self.user[user_id].items():
            if data['status'] == status:
                books.append({'book_id': book_id, 'status': data['status'], 'rating': data['rating']})
        return books
    
    def get_status(self, user_id: int) -> Dict[str, int]:
        """
        Получение статистики по книгам пользователя.
        
        Args:
            user_id (int): ID пользователя
            
        Returns:
            Dict: Статистика по статусам книг
        """
        try:
            stats = {'total': 0, 'planned': 0, 'reading': 0, 'completed': 0, 'dropped': 0}
            if user_id not in self.user:
                return stats
            users_books = self.user[user_id]
            stats['total'] = len(users_books)
            for book_data in users_books.values():
                status = book_data['status']
                if status in stats:
                    stats[status] += 1
            return stats
        except Exception as e:
            print(f"Error in get_status: {e}")
            return {'total': 0, 'planned': 0, 'reading': 0, 'completed': 0, 'dropped': 0}
    
    def get_new_status(self, user_id: int, book_id: int, new_status: str) -> bool:
        """
        Изменение статуса книги.
        
        Args:
            user_id (int): ID пользователя
            book_id (int): ID книги
            new_status (str): Новый статус
            
        Returns:
            bool: True если статус успешно изменен
        """
        try:
            allowed_status = ["planned", "reading", "completed", "dropped"]
            if new_status not in allowed_status:
                return False
            if user_id not in self.user:
                return False
            if book_id not in self.user[user_id]:
                return False
            self.user[user_id][book_id]['status'] = new_status
            return True
        except Exception as e:
            print(f"Error in det_new_status: {e}")
            return False
    
    def get_average_rating(self, user_id: int) -> float:
        """
        Получение средней оценки пользователя.
        
        Args:
            user_id (int): ID пользователя
            
        Returns:
            float: Средняя оценка
        """
        try:
            if user_id not in self.user:
                return 0.0
            total = 0
            cnt = 0
            for book_data in self.user[user_id].values():
                rating = book_data.get('rating')
                if rating is not None:
                    total += rating
                    cnt += 1
            if cnt == 0:
                return 0.0
            return round(total / cnt, 2)
        except Exception as e:
            print(f"Error in get_average_rating: {e}")
            return 0.0
    
    def has_book(self, user_id: int, book_id: int) -> bool:
        """
        Проверка наличия книги у пользователя.
        
        Args:
            user_id (int): ID пользователя
            book_id (int): ID книги
            
        Returns:
            bool: True если книга есть у пользователя
        """
        try:
            if user_id not in self.user:
                return False
            return book_id in self.user[user_id]
        except Exception as e:
            print(f"Error in has_book: {e}")
            return False
    
    def clear_user_books(self, user_id: int) -> bool:
        """
        Очистка всех книг пользователя.
        
        Args:
            user_id (int): ID пользователя
            
        Returns:
            bool: True если успешно очищено
        """
        try:
            if user_id in self.user:
                del self.user[user_id]
                return True
            return False
        except Exception as e:
            print(f"Error in clear_user_books: {e}")
            return False
    
    def get_user_book_count(self, user_id: int) -> int:
        """
        Получение количества книг пользователя.
        
        Args:
            user_id (int): ID пользователя
            
        Returns:
            int: Количество книг
        """
        try:
            if user_id in self.user:
                return len(self.user[user_id])
            return 0
        except Exception as e:
            print(f"Error in get_user_book_count: {e}")
            return 0
    
    def count_rated_books(self, user_id: int) -> int:
        """
        Подсчет оцененных книг пользователя.
        
        Args:
            user_id (int): ID пользователя
            
        Returns:
            int: Количество оцененных книг
        """
        try:
            if user_id not in self.user:
                return 0
            count = 0
            for data in self.user[user_id].values():
                if data['rating'] is not None:
                    count += 1
            return count
        except Exception as e:
            print(f"Error in count_rated_books: {e}")
            return 0
# models.py
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class Book(Base):
    """Модель для книги в картотеке."""
    __tablename__ = 'books'

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    author = Column(String, nullable=False)
    genre = Column(String)
    created_at = Column(DateTime, default=datetime.now)
    # Связь один-к-одному с текстом книги (если он есть)
    content = relationship("BookContent", uselist=False, back_populates="book")
    # Связь один-ко-многим с прогрессом чтения
    reading_progress = relationship("ReadingProgress", back_populates="book")

class BookContent(Base):
    """Модель для хранения текста книги."""
    __tablename__ = 'book_contents'

    id = Column(Integer, primary_key=True)
    book_id = Column(Integer, ForeignKey('books.id'), unique=True)
    text = Column(Text, nullable=False)  # Полный текст книги
    created_at = Column(DateTime, default=datetime.now)

    book = relationship("Book", back_populates="content")

class ReadingProgress(Base):
    """Модель для отслеживания прогресса чтения книги пользователем."""
    __tablename__ = 'reading_progress'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)  # ID пользователя в Telegram
    book_id = Column(Integer, ForeignKey('books.id'))
    last_page = Column(Integer, default=0)     # Последняя прочитанная страница
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    book = relationship("Book", back_populates="reading_progress")
