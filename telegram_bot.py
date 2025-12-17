# -*- coding: utf-8 -*-
"""Основной модуль Telegram бота."""

import logging
import argparse
import os
import sys
import warnings
from typing import List, Dict, Any

# Подавляем предупреждения
warnings.filterwarnings("ignore", message=".*per_message=False.*")

# Добавляем текущую директорию в путь Python
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    ContextTypes, 
    ConversationHandler,
    filters,
    CallbackQueryHandler
)
from telegram.constants import ParseMode

# Импортируем DatabaseManager напрямую из текущей папки
from database import DatabaseManager

# Обновленный словарь эмодзи
EMOJI = {
    "search": "🔍", "star": "⭐️", "fire": "🔥", "trophy": "🏆", "plus": "➕",
    "list": "📋", "help": "❓", "back": "↩️", "home": "🏠", "check": "✅",
    "cross": "❌", "book": "📚", "user": "👤", "pencil": "✏️", "bookshelf": "📖",
    "trash": "🗑️", "info": "ℹ️", "read": "📖", "bookmark": "🔖", 
    "prev": "⬅️", "next": "➡️", "progress": "📊"
}

# Состояния диалога
CHOOSING, TYPING_SEARCH, TYPING_BOOK_INFO, CONFIRM_DELETE, TYPING_BOOK_ID, READING = range(6)

class BookBot:
    """Основной класс Telegram бота."""
    
    def __init__(self, token: str):
        """
        Инициализация бота.
        
        Args:
            token (str): Токен Telegram бота
        """
        self.token = token
        self.application = None
        
        # Тест подключения к базе
        try:
            self.db = DatabaseManager('telegram_books.db')
            print("[OK] База данных успешно подключена")
        except Exception as e:
            print(f"[ERROR] Ошибка подключения к БД: {e}")
            raise
        
        logging.basicConfig(
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            level=logging.INFO
        )
        self.logger = logging.getLogger(__name__)
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /start."""
        welcome_text = f"""
{EMOJI['book']} <b>Привет!</b>

Я <b>BookBot</b> - ваш персональный библиотекарь.

<b>Что умею:</b>
{EMOJI['search']} Искать книги в вашей библиотеке
{EMOJI['plus']} Добавлять новые книги (с текстом!)
{EMOJI['list']} Показывать все ваши книги
{EMOJI['read']} <b>Читать книги</b> - новая функция!
{EMOJI['trash']} Удалять книги
{EMOJI['trophy']} Показывать статистику

<b>Выберите действие:</b>"""
        
        keyboard = [
            [KeyboardButton(f"{EMOJI['search']} Поиск"), KeyboardButton(f"{EMOJI['list']} Все книги")],
            [KeyboardButton(f"{EMOJI['plus']} Добавить"), KeyboardButton(f"{EMOJI['read']} Читать")],
            [KeyboardButton(f"{EMOJI['trash']} Удалить"), KeyboardButton(f"{EMOJI['info']} Статистика")],
            [KeyboardButton(f"{EMOJI['help']} Помощь")]
        ]
        
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            welcome_text, 
            parse_mode=ParseMode.HTML, 
            reply_markup=reply_markup
        )
        return CHOOSING
    
    async def help_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /help."""
        help_text = f"""
{EMOJI['help']} <b>Помощь по командам</b>

<b>Основные команды:</b>
/start - Главное меню
/search - Поиск книг
/add - Добавить книгу
/mybooks - Все мои книги
/delete - Удалить книгу
/read - Читать книги
/stats - Статистика

<b>Формат добавления книги:</b>
<code>Название | Автор | Жанр</code>

<b>Формат добавления книги с текстом:</b>
<code>Название | Автор | Жанр | Текст книги</code>

<b>Примеры:</b>
<code>Властелин колец | Толкин | Фэнтези</code>
<code>1984 | Оруэлл | Антиутопия</code>
<code>Тест | Автор | Жанр | Это текст книги...</code>

<b>Для поиска</b> просто введите название, автора или жанр."""
        
        await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)
    
    # ========== МЕТОДЫ ДЛЯ УЧЕТА КНИГ ==========
    
    async def search_books(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начать поиск книг."""
        await update.message.reply_text(
            f"{EMOJI['search']} <b>Введите название, автора или жанр для поиска:</b>",
            parse_mode=ParseMode.HTML
        )
        return TYPING_SEARCH
    
    async def handle_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка поискового запроса."""
        query = update.message.text.strip()
        
        if not query:
            await update.message.reply_text(
                f"{EMOJI['cross']} <b>Введите текст для поиска</b>",
                parse_mode=ParseMode.HTML
            )
            return TYPING_SEARCH
        
        try:
            results = self.db.search_books(query)
            
            if not results:
                await update.message.reply_text(
                    f"{EMOJI['search']} <b>По запросу '{query}' ничего не найдено.</b>",
                    parse_mode=ParseMode.HTML
                )
                return CHOOSING
            
            response = f"{EMOJI['search']} <b>Найдено книг: {len(results)}</b>\n\n"
            
            for book in results[:10]:
                response += f"<b>{book['title']}</b>\n"
                response += f"{EMOJI['user']} {book['author']}\n"
                response += f"{EMOJI['pencil']} {book['genre']}\n"
                response += f"ID: {book['id']}\n\n"
            
            if len(results) > 10:
                response += f"<i>Показано 10 из {len(results)} результатов</i>"
            
            await update.message.reply_text(response, parse_mode=ParseMode.HTML)
            return CHOOSING
            
        except Exception as e:
            self.logger.error(f"Ошибка поиска: {e}")
            await update.message.reply_text(
                f"{EMOJI['cross']} <b>Ошибка при поиске:</b>\n{str(e)}",
                parse_mode=ParseMode.HTML
            )
            return CHOOSING
    
    async def add_book(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Добавить книгу."""
        await update.message.reply_text(
            f"{EMOJI['plus']} <b>Выберите тип добавления:</b>\n"
            "1. Книга для учета (без текста)\n"
            "2. Книга с текстом (для чтения)\n\n"
            "<b>Введите 1 или 2:</b>",
            parse_mode=ParseMode.HTML
        )
        return TYPING_BOOK_INFO
    
    async def handle_add_book(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка добавления книги."""
        text = update.message.text.strip()
        
        if text == "1":
            await update.message.reply_text(
                f"{EMOJI['plus']} <b>Введите книгу для учета (без текста):</b>\n"
                "<code>Название | Автор | Жанр</code>\n\n"
                "<i>Пример:</i>\n"
                "<code>Властелин колец | Толкин | Фэнтези</code>",
                parse_mode=ParseMode.HTML
            )
            context.user_data['add_type'] = 'simple'
            return TYPING_BOOK_INFO
        elif text == "2":
            await update.message.reply_text(
                f"{EMOJI['plus']} <b>Введите книгу с текстом:</b>\n"
                "<code>Название | Автор | Жанр | Текст книги</code>\n\n"
                "<i>Пример:</i>\n"
                "<code>Тестовая книга | Автор | Жанр | Это текст книги для тестирования...</code>",
                parse_mode=ParseMode.HTML
            )
            context.user_data['add_type'] = 'with_content'
            return TYPING_BOOK_INFO
        else:
            await update.message.reply_text(
                f"{EMOJI['cross']} <b>Введите 1 или 2.</b>",
                parse_mode=ParseMode.HTML
            )
            return TYPING_BOOK_INFO
    
    async def handle_add_book_details(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка деталей добавления книги."""
        text = update.message.text.strip()
        add_type = context.user_data.get('add_type', 'simple')
        
        try:
            if add_type == 'simple':
                if "|" not in text or text.count("|") != 2:
                    await update.message.reply_text(
                        f"{EMOJI['cross']} <b>Неверный формат.</b>\n"
                        "Используйте: <code>Название | Автор | Жанр</code>",
                        parse_mode=ParseMode.HTML
                    )
                    return TYPING_BOOK_INFO
                
                parts = [x.strip() for x in text.split("|")]
                title, author, genre = parts[0], parts[1], parts[2]
                
                if len(title) < 2 or len(author) < 2:
                    await update.message.reply_text(
                        f"{EMOJI['cross']} <b>Слишком короткое название или имя автора.</b>",
                        parse_mode=ParseMode.HTML
                    )
                    return TYPING_BOOK_INFO
                
                book_id = self.db.add_book(title, author, genre)
                
                await update.message.reply_text(
                    f"{EMOJI['check']} <b>Книга для учета успешно добавлена!</b>\n\n"
                    f"<b>ID:</b> {book_id}\n"
                    f"<b>Название:</b> {title}\n"
                    f"<b>Автор:</b> {author}\n"
                    f"<b>Жанр:</b> {genre}",
                    parse_mode=ParseMode.HTML
                )
                
            else:
                if "|" not in text or text.count("|") < 3:
                    await update.message.reply_text(
                        f"{EMOJI['cross']} <b>Неверный формат.</b>\n"
                        "Используйте: <code>Название | Автор | Жанр | Текст книги</code>",
                        parse_mode=ParseMode.HTML
                    )
                    return TYPING_BOOK_INFO
                
                parts = [x.strip() for x in text.split("|", 3)]
                title, author, genre, content = parts[0], parts[1], parts[2], parts[3]
                
                if len(title) < 2 or len(author) < 2:
                    await update.message.reply_text(
                        f"{EMOJI['cross']} <b>Слишком короткое название или имя автора.</b>",
                        parse_mode=ParseMode.HTML
                    )
                    return TYPING_BOOK_INFO
                
                if len(content) < 10:
                    await update.message.reply_text(
                        f"{EMOJI['cross']} <b>Текст книги слишком короткий.</b>\nМинимум 10 символов.",
                        parse_mode=ParseMode.HTML
                    )
                    return TYPING_BOOK_INFO
                
                book_id = self.db.add_book_with_content(title, author, genre, content)
                pages = (len(content) // 2000) + 1
                
                await update.message.reply_text(
                    f"{EMOJI['check']} <b>Книга с текстом успешно добавлена!</b>\n\n"
                    f"<b>ID:</b> {book_id}\n"
                    f"<b>Название:</b> {title}\n"
                    f"<b>Автор:</b> {author}\n"
                    f"<b>Жанр:</b> {genre}\n"
                    f"<b>Текст:</b> {len(content)} символов\n"
                    f"<b>Страниц:</b> {pages}\n\n"
                    f"Теперь можете читать её через {EMOJI['read']} <b>Читать</b>",
                    parse_mode=ParseMode.HTML
                )
            
            if 'add_type' in context.user_data:
                del context.user_data['add_type']
            
            return CHOOSING
            
        except Exception as e:
            self.logger.error(f"Ошибка добавления: {e}")
            await update.message.reply_text(
                f"{EMOJI['cross']} <b>Ошибка при добавлении:</b>\n{str(e)}",
                parse_mode=ParseMode.HTML
            )
            return CHOOSING
    
    async def my_books(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать все книги."""
        try:
            books = self.db.get_all_books()
            books_with_content = self.db.get_books_with_content()
            
            if not books and not books_with_content:
                await update.message.reply_text(
                    f"{EMOJI['list']} <b>Ваша библиотека пуста.</b>\n"
                    f"Используйте {EMOJI['plus']} <b>Добавить</b> для первой книги.",
                    parse_mode=ParseMode.HTML
                )
                return
            
            response = f"{EMOJI['list']} <b>Ваша библиотека</b>\n\n"
            
            if books:
                response += f"<b>📚 Книги для учета ({len(books)}):</b>\n"
                for i, book in enumerate(books[:5], 1):
                    response += f"{i}. {book['title']} - {book['author']} (ID: {book['id']})\n"
                
                if len(books) > 5:
                    response += f"... и еще {len(books) - 5}\n"
                response += "\n"
            
            if books_with_content:
                response += f"<b>📖 Книги для чтения ({len(books_with_content)}):</b>\n"
                for i, book in enumerate(books_with_content[:5], 1):
                    pages_info = f"{book['pages']} стр." if book['pages'] > 0 else "нет текста"
                    response += f"{i}. {book['title']} - {book['author']} (ID: {book['id']}, {pages_info})\n"
                
                if len(books_with_content) > 5:
                    response += f"... и еще {len(books_with_content) - 5}\n"
            
            response += f"\n<i>Для чтения используйте {EMOJI['read']} Читать</i>"
            
            await update.message.reply_text(response, parse_mode=ParseMode.HTML)
            
        except Exception as e:
            self.logger.error(f"Ошибка получения списка: {e}")
            await update.message.reply_text(
                f"{EMOJI['cross']} <b>Ошибка при получении списка книг:</b>\n{str(e)}",
                parse_mode=ParseMode.HTML
            )
    
    async def delete_book(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начать удаление книги."""
        try:
            books = self.db.get_all_books()
            books_with_content = self.db.get_books_with_content()
            
            if not books and not books_with_content:
                await update.message.reply_text(
                    f"{EMOJI['list']} <b>Нет книг для удаления.</b>",
                    parse_mode=ParseMode.HTML
                )
                return CHOOSING
            
            response = f"{EMOJI['trash']} <b>Выберите ID книги для удаления:</b>\n\n"
            
            all_books = []
            if books:
                response += "<b>Книги для учета:</b>\n"
                for book in books[:8]:
                    response += f"  ID {book['id']}: {book['title'][:30]}...\n"
                    all_books.append(('simple', book['id'], book['title']))
            
            if books_with_content:
                response += "\n<b>Книги для чтения:</b>\n"
                for book in books_with_content[:8]:
                    response += f"  ID {book['id']}: {book['title'][:30]}...\n"
                    all_books.append(('content', book['id'], book['title']))
            
            response += f"\n<b>Введите ID книги для удаления:</b>"
            
            await update.message.reply_text(response, parse_mode=ParseMode.HTML)
            return CONFIRM_DELETE
            
        except Exception as e:
            self.logger.error(f"Ошибка при подготовке удаления: {e}")
            await update.message.reply_text(
                f"{EMOJI['cross']} <b>Ошибка:</b>\n{str(e)}",
                parse_mode=ParseMode.HTML
            )
            return CHOOSING
    
    async def confirm_delete(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Подтверждение удаления книги."""
        try:
            book_id = int(update.message.text.strip())
            
            success = self.db.delete_book(book_id)
            
            if success:
                await update.message.reply_text(
                    f"{EMOJI['check']} <b>Книга успешно удалена!</b>",
                    parse_mode=ParseMode.HTML
                )
            else:
                await update.message.reply_text(
                    f"{EMOJI['cross']} <b>Книга с ID {book_id} не найдена.</b>",
                    parse_mode=ParseMode.HTML
                )
            
            return CHOOSING
            
        except ValueError:
            await update.message.reply_text(
                f"{EMOJI['cross']} <b>Введите числовой ID книги.</b>",
                parse_mode=ParseMode.HTML
            )
            return CONFIRM_DELETE
        except Exception as e:
            self.logger.error(f"Ошибка удаления: {e}")
            await update.message.reply_text(
                f"{EMOJI['cross']} <b>Ошибка при удалении:</b>\n{str(e)}",
                parse_mode=ParseMode.HTML
            )
            return CHOOSING
    
    async def show_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать статистику."""
        try:
            books = self.db.get_all_books()
            books_with_content = self.db.get_books_with_content()
            
            if not books and not books_with_content:
                await update.message.reply_text(
                    f"{EMOJI['info']} <b>В библиотеке пока нет книг.</b>",
                    parse_mode=ParseMode.HTML
                )
                return
            
            response = f"{EMOJI['trophy']} <b>Статистика библиотеки</b>\n\n"
            
            total_books = len(books) + len(books_with_content)
            response += f"<b>Всего книг:</b> {total_books}\n"
            response += f"  📚 Для учета: {len(books)}\n"
            response += f"  📖 Для чтения: {len(books_with_content)}\n\n"
            
            all_genres = {}
            for book in books:
                genre = book['genre']
                all_genres[genre] = all_genres.get(genre, 0) + 1
            
            for book in books_with_content:
                genre = book['genre']
                all_genres[genre] = all_genres.get(genre, 0) + 1
            
            if all_genres:
                top_genres = sorted(all_genres.items(), key=lambda x: x[1], reverse=True)[:3]
                response += "<b>Топ жанров:</b>\n"
                for genre, count in top_genres:
                    response += f"  {EMOJI['pencil']} {genre}: {count} книг\n"
            
            await update.message.reply_text(response, parse_mode=ParseMode.HTML)
            
        except Exception as e:
            self.logger.error(f"Ошибка статистики: {e}")
            await update.message.reply_text(
                f"{EMOJI['cross']} <b>Ошибка при получении статистики:</b>\n{str(e)}",
                parse_mode=ParseMode.HTML
            )
    
    # ========== МЕТОДЫ ДЛЯ ЧТЕНИЯ КНИГ ==========
    
    async def read_book_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Меню чтения книг."""
        try:
            books = self.db.get_books_with_content()
            
            if not books:
                await update.message.reply_text(
                    f"{EMOJI['read']} <b>Нет книг для чтения.</b>\n"
                    f"Сначала добавьте книги с текстом через {EMOJI['plus']} Добавить",
                    parse_mode=ParseMode.HTML
                )
                return CHOOSING
            
            response = f"{EMOJI['read']} <b>Доступные для чтения книги:</b>\n\n"
            
            for book in books[:10]:
                pages_info = f"{book['pages']} стр." if book['pages'] > 0 else "нет текста"
                response += f"<b>ID {book['id']}:</b> {book['title']}\n"
                response += f"   {EMOJI['user']} {book['author']} | {EMOJI['pencil']} {book['genre']} | {EMOJI['book']} {pages_info}\n\n"
            
            if len(books) > 10:
                response += f"\n<i>Показано 10 из {len(books)} книг</i>"
            
            response += f"\n<b>Введите ID книги для чтения:</b>"
            
            await update.message.reply_text(response, parse_mode=ParseMode.HTML)
            return TYPING_BOOK_ID
            
        except Exception as e:
            self.logger.error(f"Ошибка в меню чтения: {e}")
            await update.message.reply_text(
                f"{EMOJI['cross']} <b>Ошибка:</b>\n{str(e)}",
                parse_mode=ParseMode.HTML
            )
            return CHOOSING
    
    async def handle_read_book(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка начала чтения книги."""
        try:
            book_id = int(update.message.text.strip())
            user_id = update.effective_user.id
            
            # Проверяем книгу
            book_info = self.db.get_book_content(book_id, 1)
            
            if not book_info:
                await update.message.reply_text(
                    f"{EMOJI['cross']} <b>Книга с ID {book_id} не найдена или не содержит текста.</b>",
                    parse_mode=ParseMode.HTML
                )
                return CHOOSING
            
            # Получаем сохраненный прогресс
            saved_page = self.db.get_reading_progress(user_id, book_id)
            current_page = saved_page if saved_page else 1
            
            # Получаем страницу
            book_page = self.db.get_book_content(book_id, current_page)
            
            if not book_page:
                await update.message.reply_text(
                    f"{EMOJI['cross']} <b>Не удалось загрузить страницу {current_page}.</b>",
                    parse_mode=ParseMode.HTML
                )
                return CHOOSING
            
            # Сохраняем данные
            context.user_data['current_book_id'] = book_id
            context.user_data['current_page'] = current_page
            
            # Создаем клавиатуру
            keyboard = self._create_reading_keyboard(current_page, book_page['total_pages'])
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            
            # Формируем ответ
            response = self._format_book_page(book_page, current_page)
            
            await update.message.reply_text(response, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
            return READING
            
        except ValueError:
            await update.message.reply_text(
                f"{EMOJI['cross']} <b>Введите числовой ID книги.</b>",
                parse_mode=ParseMode.HTML
            )
            return TYPING_BOOK_ID
        except Exception as e:
            self.logger.error(f"Ошибка начала чтения: {e}")
            await update.message.reply_text(
                f"{EMOJI['cross']} <b>Ошибка при начале чтения:</b>\n{str(e)}",
                parse_mode=ParseMode.HTML
            )
            return CHOOSING
    
    async def handle_reading_navigation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка навигации при чтении."""
        user_id = update.effective_user.id
        command = update.message.text
        
        book_id = context.user_data.get('current_book_id')
        current_page = context.user_data.get('current_page', 1)
        
        if not book_id:
            await update.message.reply_text(
                f"{EMOJI['cross']} <b>Сессия чтения потеряна.</b>\nНачните заново.",
                parse_mode=ParseMode.HTML
            )
            return CHOOSING
        
        # Обработка команд
        if command == "⬅️ Назад":
            if current_page > 1:
                current_page -= 1
        elif command == "➡️ Вперед":
            current_page += 1
        elif command == "🔖 Сохранить":
            self.db.save_reading_progress(user_id, book_id, current_page)
            await update.message.reply_text(
                f"{EMOJI['bookmark']} <b>Прогресс сохранен!</b>\nСтраница {current_page}",
                parse_mode=ParseMode.HTML
            )
            book_page = self.db.get_book_content(book_id, current_page)
        elif command == "🏠 В меню":
            self.db.save_reading_progress(user_id, book_id, current_page)
            await self.back_to_menu(update, context)
            return CHOOSING
        else:
            await update.message.reply_text(
                f"{EMOJI['cross']} <b>Неизвестная команда.</b>",
                parse_mode=ParseMode.HTML
            )
            book_page = self.db.get_book_content(book_id, current_page)
        
        if 'book_page' not in locals():
            book_page = self.db.get_book_content(book_id, current_page)
        
        if not book_page:
            await update.message.reply_text(
                f"{EMOJI['cross']} <b>Страница {current_page} не найдена.</b>",
                parse_mode=ParseMode.HTML
            )
            return READING
        
        context.user_data['current_page'] = current_page
        self.db.save_reading_progress(user_id, book_id, current_page)
        
        keyboard = self._create_reading_keyboard(current_page, book_page['total_pages'])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        response = self._format_book_page(book_page, current_page)
        
        await update.message.reply_text(response, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
        return READING
    
    def _create_reading_keyboard(self, current_page: int, total_pages: int) -> List[List[KeyboardButton]]:
        """Создание клавиатуры для навигации при чтении."""
        keyboard = []
        
        nav_buttons = []
        if current_page > 1:
            nav_buttons.append(KeyboardButton("⬅️ Назад"))
        
        nav_buttons.append(KeyboardButton("🔖 Сохранить"))
        
        if current_page < total_pages:
            nav_buttons.append(KeyboardButton("➡️ Вперед"))
        
        if nav_buttons:
            keyboard.append(nav_buttons)
        
        keyboard.append([KeyboardButton("🏠 В меню")])
        
        return keyboard
    
    def _format_book_page(self, book_page: Dict[str, Any], current_page: int) -> str:
        """Форматирование страницы книги для отображения."""
        response = f"{EMOJI['book']} <b>{book_page['title']}</b>\n"
        response += f"{EMOJI['user']} {book_page['author']}\n"
        response += f"{EMOJI['pencil']} {book_page['genre']}\n"
        response += f"{EMOJI['progress']} Страница {current_page}/{book_page['total_pages']}\n"
        response += f"{EMOJI['info']} {book_page['progress']} ({book_page['percentage']}%)\n\n"
        
        content = book_page['content'].replace('\n', '\n    ')
        response += f"<pre>{content}</pre>\n\n"
        response += f"<i>Используйте кнопки для навигации</i>"
        
        return response
    
    async def back_to_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Вернуться в меню."""
        keyboard = [
            [KeyboardButton(f"{EMOJI['search']} Поиск"), KeyboardButton(f"{EMOJI['list']} Все книги")],
            [KeyboardButton(f"{EMOJI['plus']} Добавить"), KeyboardButton(f"{EMOJI['read']} Читать")],
            [KeyboardButton(f"{EMOJI['trash']} Удалить"), KeyboardButton(f"{EMOJI['info']} Статистика")],
            [KeyboardButton(f"{EMOJI['help']} Помощь")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            f"{EMOJI['home']} <b>Главное меню</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )
        return CHOOSING
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отмена."""
        await update.message.reply_text(
            f"{EMOJI['cross']} <b>Действие отменено</b>",
            parse_mode=ParseMode.HTML
        )
        await self.back_to_menu(update, context)
    
    def setup(self):
        """Настройка обработчиков."""
        self.application = Application.builder().token(self.token).build()
        
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("start", self.start)],
            states={
                CHOOSING: [
                    MessageHandler(filters.Regex(f"^{EMOJI['search']} Поиск$"), self.search_books),
                    MessageHandler(filters.Regex(f"^{EMOJI['list']} Все книги$"), self.my_books),
                    MessageHandler(filters.Regex(f"^{EMOJI['plus']} Добавить$"), self.add_book),
                    MessageHandler(filters.Regex(f"^{EMOJI['read']} Читать$"), self.read_book_menu),
                    MessageHandler(filters.Regex(f"^{EMOJI['trash']} Удалить$"), self.delete_book),
                    MessageHandler(filters.Regex(f"^{EMOJI['info']} Статистика$"), self.show_stats),
                    MessageHandler(filters.Regex(f"^{EMOJI['help']} Помощь$"), self.help_cmd),
                    CommandHandler("help", self.help_cmd),
                    CommandHandler("mybooks", self.my_books),
                    CommandHandler("stats", self.show_stats),
                    CommandHandler("read", self.read_book_menu),
                ],
                TYPING_SEARCH: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_search),
                ],
                TYPING_BOOK_INFO: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_add_book_details),
                ],
                TYPING_BOOK_ID: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_read_book),
                ],
                READING: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_reading_navigation),
                ],
                CONFIRM_DELETE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.confirm_delete),
                ],
            },
            fallbacks=[CommandHandler("cancel", self.cancel)],
            per_message=False,
        )
        
        self.application.add_handler(conv_handler)
        
        self.application.add_handler(CommandHandler("search", self.search_books))
        self.application.add_handler(CommandHandler("add", self.add_book))
        self.application.add_handler(CommandHandler("delete", self.delete_book))
    
    def run(self):
        """Запуск бота."""
        self.setup()
        print(">>> BookBot запущен! Нажмите Ctrl+C для остановки.")
        print("==================================================")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)


def main():
    """Главная функция."""
    parser = argparse.ArgumentParser(description="Telegram BookBot")
    parser.add_argument('--token', help='Токен бота')
    
    args = parser.parse_args()
    
    token = args.token or os.getenv('TELEGRAM_TOKEN')
    
    if not token:
        print("ERROR: Укажите токен бота")
        print("   python telegram_bot.py --token 'ВАШ_ТОКЕН'")
        print("   или set TELEGRAM_TOKEN='ВАШ_ТОКЕН'")
        sys.exit(1)
    
    bot = BookBot(token)
    bot.run()


if __name__ == "__main__":
    main()
