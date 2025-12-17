class User:
    """
    Manages user's book collection with reading status and rating tracking.

    Attributes:
        user (dict): Dictionary storing user data: {user_id: {book_id: {'status': str, 'rating': int|None}}}
    """

    def __init__(self):
        """
        Initializes a new User with an empty dictionary.
        """
        self.user = {}

    def add_book(self, user_id, book_id, status):
        """
        Adds a book to a user's collection.

        Args:
            user_id (int): The unique identifier of the user.
            book_id (int): The unique identifier of the book
            status (str): The reading status of the book: "planned", "reading", "completed", "dropped".

        Returns:
            bool: True if the book was successfully added, False if the book already exists.

        Raises:
            ValueError: If invalid status.
        """
        try:
            allowed_status = ["planned", "reading", "completed", "dropped"]
            if status not in allowed_status:
                raise ValueError
            if user_id not in self.user:
                self.user[user_id] = {}
            if book_id in self.user[user_id]:
                return False
            self.user[user_id][book_id] = {
                'status': status, 'rating': None}
            return True
        except Exception as e:
            print(f"Error in add_book: {e}")
            return False

    def rate_book(self, user_id, book_id, rating):
        """
        Rates a book in the user's collection.

        Args:
            user_id (int): The unique identifier of the user.
            book_id (int): The unique identifier of the book.
            rating (int): The rating value (1-5).

        Returns:
            bool: True if the rating was successfully added, False if user or book not found.

        Raises:
            ValueError: If the rating is not between 1 and 5.
        """
        try:
            if rating < 1 or rating > 5:
                raise ValueError
            if user_id not in self.user:
                return False
            if book_id not in self.user[user_id]:
                return False
            self.user[user_id][book_id]['rating'] = rating
            return True
        except Exception as e:
            print(f"Error in rate_book: {e}")
            return False

    def get_users_book(self, user_id):
        """
        Gets all books from a user's collection.

        Args:
            user_id (int): The unique identifier of the user.

        Returns:
            list: List of dictionaries with book info: [{'book_id': int, 'status': str, 'rating': int|None}, ...]
                  Returns empty list if user has no books.
        """
        try:
            if user_id not in self.user:
                return []
            books = []
            for book_id, book_data in self.user[user_id].items():
                books.append({
                    'book_id': book_id,
                    'status': book_data['status'],
                    'rating': book_data['rating']
                })
            return books
        except Exception as e:
            print(f"Error in get_users_book: {e}")
            return []

    def remove_book(self, user_id, book_id):
        """
        Removes a book from the user's collection.

        Args:
            user_id (int): The unique identifier of the user.
            book_id (int): The unique identifier of the book to remove.

        Returns:
            bool: True if the book was successfully removed, False if user or book not found.
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

    def get_books_by_status(self, user_id, status):
        """
        Gets books by specific status.

        Args:
            user_id (int): The unique identifier of the user.
            status (str): The reading status to filter by.

        Returns:
            list: List of books with specified status: [{'book_id': int,'status': str, 'rating': int|None}, ...]
                  Returns empty list if no books match the status.
        """
        try:
            if user_id not in self.user:
                return []
            books = []
            for book_id, data in self.user[user_id].items():
                if data['status'] == status:
                    books.append({
                        'book_id': book_id,
                        'status': data['status'],
                        'rating': data['rating']
                    })
            return books
        except Exception as e:
            print(f"Error in get_books_by_status: {e}")
            return []

    def get_status(self, user_id):
        """
        Gets reading statistics.

        Args:
            user_id (int): The unique identifier of the user.

        Returns:
            dict: Statistics: {'total': int, 'planned': int, 'reading': int, 'completed': int, 'dropped': int}
                  All values are 0 if user has no books.
        """
        try:
            stats = {'total': 0, 'planned': 0, 'reading': 0,
                     'completed': 0, 'dropped': 0}
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
            return {'total': 0, 'planned': 0, 'reading': 0,
                    'completed': 0, 'dropped': 0}

    def get_new_status(self, user_id, book_id, new_status):
        """
        Updates book's reading status.

        Args:
            user_id (int): The unique identifier of the user.
            book_id (int): The unique identifier of the book.
            new_status (str): The new reading status: "planned", "reading", "completed", "dropped".

        Returns:
            bool: True if status was successfully updated, False if invalid status, user, or book not found.

        Raises:
            ValueError: If invalid status.
        """
        try:
            allowed_status = ["planned", "reading", "completed", "dropped"]
            if new_status not in allowed_status:
                raise ValueError
            if user_id not in self.user:
                return False
            if book_id not in self.user[user_id]:
                return False
            self.user[user_id][book_id]['status'] = new_status
            return True
        except Exception as e:
            print(f"Error in det_new_status: {e}")
            return False

    def get_average_rating(self, user_id):
        """
        Calculates average rating of rated books.

        Args:
            user_id (int): The unique identifier of the user.

        Returns:
            float: Average rating (2 decimal places).
                   Returns 0.0 if user has no books or no rated books.
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

    def has_book(self, user_id, book_id):
        """
        Checks if user has specific book.

        Args:
            user_id (int): The unique identifier of the user.
            book_id (int): The unique identifier of the book to check.

        Returns:
            bool: True if the book exists in the user's collection, False otherwise.
        """
        try:
            if user_id not in self.user:
                return False
            return book_id in self.user[user_id]
        except Exception as e:
            print(f"Error in has_book: {e}")
            return False

    def clear_user_books(self, user_id):
        """
        Removes all books from a user's collection.

        Args:
            user_id (int): The unique identifier of the user.

        Returns:
            bool: True if the user's books were cleared, False if user not found.
        """
        try:
            if user_id in self.user:
                del self.user[user_id]
                return True
            return False
        except Exception as e:
            print(f"Error in clear_user_books: {e}")
            return False

    def get_user_book_count(self, user_id):
        """
        Gets the total number of books in a user's collection.

        Args:
            user_id (int): The unique identifier of the user.

        Returns:
            int: The number of books in the user's collection. Returns 0 if user has no books.
        """
        try:
            if user_id not in self.user:
                return 0
            return len(self.user[user_id])
        except Exception as e:
            print(f"Error in get_user_book_count: {e}")
            return 0

    def count_rated_books(self, user_id):
        """
        Counts rated books.

        Args:
            user_id (int): The unique identifier of the user.

        Returns:
            int: The number of rated books. Returns 0 if user has no books or no ratings.
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
