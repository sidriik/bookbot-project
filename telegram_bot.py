# -*- coding: utf-8 -*-
"""Telegram бот для управления библиотекой книг с функцией чтения."""

import logging
import argparse
import os
import sys
from typing import List, Dict, Any

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

# Импортируем DatabaseManager
from database import DatabaseManager

# Обновленный словарь эмодзи
EMOJI = {
    "search": "🔍", "star": "⭐️", "fire": "🔥", "trophy": "🏆", "plus": "➕",
    "list": "📋", "help": "❓", "back": "↩️", "home": "🏠", "check": "✅",
    "cross": "❌", "book": "📚", "user": "👤", "pencil": "✏️", "bookshelf": "📖",
    "trash": "🗑️", "info": "ℹ️", "read": "📖", "bookmark": "🔖", 
    "prev": "⬅️", "next": "➡️", "progress": "📊"
}

# Состояния для ConversationHandler
(
    CHOOSING,
    TYPING_SEARCH,
    TYPING_BOOK_INFO,
    CONFIRM_DELETE,
    # Новые состояния для чтения:
    READING_BOOK_SELECTION,   # Выбор книги для чтения
    READING_PAGE_NAVIGATION,  # Навигация по страницам
) = range(6)

class BookBot:
    """Основной класс Telegram бота с функцией чтения книг."""
    
    def __init__(self, token: str):
        """
        Инициализация бота.
        
        Args:
            token (str): Токен Telegram бота
        """
        self.token = token
        self.application = None
        
        # Подключение к базе данных
        try:
            self.db = DatabaseManager('telegram_books.db')
            print(" База данных успешно подключена")
        except Exception as e:
            print(f"❌ Ошибка подключения к БД: {e}")
            raise
        
        # Настройка логирования
        logging.basicConfig(
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            level=logging.INFO
        )
        self.logger = logging.getLogger(__name__)
    
    # ========== МЕТОДЫ ДЛЯ ГЛАВНОГО МЕНЮ ==========
    
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
{EMOJI['info']} Показывать статистику

<b>Выберите действие:</b>"""
        
        # Обновленная клавиатура с кнопкой "Читать"
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
<code>1984 | Оруэлл | Антиутопия | Это был яркий холодный день...</code>

<b>Для поиска</b> просто введите название, автора или жанр.
<b>Для чтения</b> используйте кнопку {EMOJI['read']} Читать"""
        
        await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)
        return CHOOSING
    
    # ========== МЕТОДЫ ДЛЯ ДОБАВЛЕНИЯ КНИГ ==========
    
    async def add_book(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начать добавление книги."""
        await update.message.reply_text(
            f"{EMOJI['plus']} <b>Выберите тип добавления:</b>\n"
            "1. Книга для учета (без текста)\n"
            "2. Книга с текстом (для чтения)\n\n"
            "<b>Введите 1 или 2:</b>",
            parse_mode=ParseMode.HTML
        )
        return TYPING_BOOK_INFO
    
    async def handle_add_choice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора типа добавления."""
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
                "<code>Отрывок из книги | Автор | Жанр | Это текст книги для чтения...</code>",
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
    
    async def handle_book_details(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка деталей книги."""
        text = update.message.text.strip()
        add_type = context.user_data.get('add_type', 'simple')
        
        try:
            if add_type == 'simple':
                # Книга для учета
                if "|" not in text or text.count("|") != 2:
                    await update.message.reply_text(
                        f"{EMOJI['cross']} <b>Неверный формат.</b>\n"
                        "Используйте: <code>Название | Автор | Жанр</code>",
                        parse_mode=ParseMode.HTML
                    )
                    return TYPING_BOOK_INFO
                
                parts = [x.strip() for x in text.split("|")]
                title, author, genre = parts[0], parts[1], parts[2]
                
                # Проверка дубликатов
                existing = self.db.search_books(title)
                for book in existing:
                    if book['title'].lower() == title.lower() and book['author'].lower() == author.lower():
                        await update.message.reply_text(
                            f"{EMOJI['info']} <b>Книга уже существует:</b>\n"
                            f"ID: {book['id']}\n"
                            f"Название: {book['title']}",
                            parse_mode=ParseMode.HTML
                        )
                        return CHOOSING
                
                # Добавление книги
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
                # Книга с текстом
                if "|" not in text or text.count("|") < 3:
                    await update.message.reply_text(
                        f"{EMOJI['cross']} <b>Неверный формат.</b>\n"
                        "Используйте: <code>Название | Автор | Жанр | Текст книги</code>",
                        parse_mode=ParseMode.HTML
                    )
                    return TYPING_BOOK_INFO
                
                parts = [x.strip() for x in text.split("|", 3)]
                title, author, genre, content = parts[0], parts[1], parts[2], parts[3]
                
                if len(content) < 10:
                    await update.message.reply_text(
                        f"{EMOJI['cross']} <b>Текст книги слишком короткий.</b>\n"
                        "Минимум 10 символов.",
                        parse_mode=ParseMode.HTML
                    )
                    return TYPING_BOOK_INFO
                
                # Добавление книги с текстом
                book_id = self.db.add_book_with_content(title, author, genre, content)
                pages = (len(content) // 1500) + 1  # Примерно 1500 символов на страницу
                
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
            
            # Очистка данных
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
    
    # ========== МЕТОДЫ ДЛЯ ПОИСКА И СПИСКА ==========
    
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
            # Поиск книг в базе
            results = self.db.search_books(query)
            
            if not results:
                await update.message.reply_text(
                    f"{EMOJI['search']} <b>По запросу '{query}' ничего не найдено.</b>",
                    parse_mode=ParseMode.HTML
                )
                return CHOOSING
            
            response = f"{EMOJI['search']} <b>Найдено книг: {len(results)}</b>\n\n"
            
            for book in results[:10]:  # Ограничиваем 10 результатами
                book_type = "📖" if hasattr(book, 'content') or 'content' in book else "📚"
                response += f"{book_type} <b>{book['title']}</b>\n"
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
    
    async def my_books(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать все книги."""
        try:
            # Получаем все книги
            books = self.db.get_all_books()
            
            if not books:
                await update.message.reply_text(
                    f"{EMOJI['list']} <b>Ваша библиотека пуста.</b>\n"
                    f"Используйте {EMOJI['plus']} <b>Добавить</b> для первой книги.",
                    parse_mode=ParseMode.HTML
                )
                return
            
            # Получаем книги с текстом (если такой метод существует)
            books_with_content = []
            try:
                books_with_content = self.db.get_books_with_content()
            except AttributeError:
                pass  # Метод не реализован
            
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
                    # Проверяем структуру объекта
                    if isinstance(book, dict):
                        title = book.get('title', 'Без названия')
                        author = book.get('author', 'Неизвестен')
                        book_id = book.get('id', '?')
                    else:
                        title = getattr(book, 'title', 'Без названия')
                        author = getattr(book, 'author', 'Неизвестен')
                        book_id = getattr(book, 'id', '?')
                    
                    response += f"{i}. {title} - {author} (ID: {book_id})\n"
                
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
    
    # ========== МЕТОДЫ ДЛЯ ЧТЕНИЯ КНИГ ==========
    
    async def read_book_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /read или кнопки 'Читать'."""
        try:
            # Пробуем получить книги с текстом
            books_with_content = self.db.get_books_with_content()
        except AttributeError:
            # Метод не реализован в базе
            await update.message.reply_text(
                f"{EMOJI['cross']} <b>Функция чтения пока недоступна.</b>\n"
                f"База данных не поддерживает хранение текста книг.",
                parse_mode=ParseMode.HTML
            )
            return CHOOSING
        
        if not books_with_content:
            await update.message.reply_text(
                f"{EMOJI['read']} <b>В библиотеке пока нет книг с текстом для чтения.</b>\n"
                f"Добавьте книги с текстом через {EMOJI['plus']} Добавить",
                parse_mode=ParseMode.HTML
            )
            return CHOOSING
        
        # Формируем список книг для выбора
        keyboard = []
        for book in books_with_content[:15]:  # Ограничиваем 15 книгами
            # Обрабатываем разные форматы книги
            if isinstance(book, dict):
                title = book.get('title', 'Без названия')
                author = book.get('author', 'Неизвестен')
                book_id = book.get('id', 0)
            else:
                title = getattr(book, 'title', 'Без названия')
                author = getattr(book, 'author', 'Неизвестен')
                book_id = getattr(book, 'id', 0)
            
            # Создаем кнопку для каждой книги
            button_text = f"{title[:30]}... - {author[:15]}..." if len(title) > 30 else f"{title} - {author}"
            keyboard.append([InlineKeyboardButton(
                button_text,
                callback_data=f"read_{book_id}"
            )])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"{EMOJI['read']} <b>Выберите книгу для чтения:</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )
        return READING_BOOK_SELECTION
    
    async def handle_book_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора книги для чтения (callback)."""
        query = update.callback_query
        await query.answer()
        
        # Извлекаем ID книги из callback_data
        if query.data.startswith("read_"):
            book_id = int(query.data.split("_")[1])
            context.user_data['current_book_id'] = book_id
            context.user_data['current_page'] = 0  # Начинаем с первой страницы
            
            # Переходим к показу страницы
            await self.show_book_page(update, context, book_id, 0)
            return READING_PAGE_NAVIGATION
    
    async def show_book_page(self, update: Update, context: ContextTypes.DEFAULT_TYPE, book_id: int = None, page_num: int = 0):
        """Показывает конкретную страницу книги и кнопки навигации."""
        if book_id is None:
            book_id = context.user_data.get('current_book_id')
        
        if book_id is None:
            await update.callback_query.message.reply_text(
                f"{EMOJI['cross']} <b>Ошибка: книга не выбрана.</b>",
                parse_mode=ParseMode.HTML
            )
            return CHOOSING
        
        user_id = update.effective_user.id if update.effective_user else 0
        
        try:
            # Получаем текст книги
            text = self.db.get_book_content(book_id)
        except AttributeError:
            # Метод не реализован
            await update.callback_query.message.reply_text(
                f"{EMOJI['cross']} <b>Не удалось загрузить текст книги.</b>\n"
                f"Функция чтения не настроена в базе данных.",
                parse_mode=ParseMode.HTML
            )
            return CHOOSING
        
        if not text:
            await update.callback_query.message.reply_text(
                f"{EMOJI['cross']} <b>Текст книги не найден.</b>",
                parse_mode=ParseMode.HTML
            )
            return CHOOSING
        
        # Получаем сохранённый прогресс или начинаем с начала
        try:
            last_page = self.db.get_reading_progress(user_id, book_id)
        except AttributeError:
            last_page = 0
        
        current_page = page_num if page_num > 0 else last_page
        
        # Логика разбивки текста на страницы
        page_size = 1500  # Символов на страницу
        pages = [text[i:i+page_size] for i in range(0, len(text), page_size)]
        total_pages = len(pages)
        
        if current_page >= total_pages:
            current_page = total_pages - 1
        
        if current_page < 0:
            current_page = 0
        
        # Сохраняем текущую страницу как прогресс
        try:
            self.db.save_reading_progress(user_id, book_id, current_page)
        except AttributeError:
            pass  # Метод не реализован
        
        # Обновляем данные в контексте
        context.user_data['current_book_id'] = book_id
        context.user_data['current_page'] = current_page
        context.user_data['total_pages'] = total_pages
        
        # Создаем клавиатуру для навигации
        nav_buttons = []
        
        # Кнопка "Назад"
        if current_page > 0:
            nav_buttons.append(InlineKeyboardButton(
                "⬅️ Назад", 
                callback_data=f"nav_{book_id}_{current_page-1}"
            ))
        
        # Индикатор страницы
        nav_buttons.append(InlineKeyboardButton(
            f"{current_page+1}/{total_pages}", 
            callback_data="page_info"
        ))
        
        # Кнопка "Вперед"
        if current_page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton(
                "Вперёд ➡️", 
                callback_data=f"nav_{book_id}_{current_page+1}"
            ))
        
        # Дополнительные кнопки
        extra_buttons = []
        extra_buttons.append(InlineKeyboardButton(
            "🔖 Закладка", 
            callback_data=f"bookmark_{book_id}_{current_page}"
        ))
        extra_buttons.append(InlineKeyboardButton(
            "🏠 В меню", 
            callback_data="back_to_menu"
        ))
        
        keyboard = [nav_buttons, extra_buttons]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Получаем информацию о книге для заголовка
        try:
            book_info = self.db.get_book(book_id)
            book_title = book_info.get('title', 'Книга') if isinstance(book_info, dict) else getattr(book_info, 'title', 'Книга')
        except:
            book_title = "Книга"
        
        # Отправляем страницу
        if update.callback_query:
            await update.callback_query.message.reply_text(
                f"{EMOJI['book']} <b>{book_title}</b>\n"
                f"{EMOJI['progress']} <b>Страница {current_page+1} из {total_pages}</b>\n\n"
                f"{pages[current_page]}",
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                f"{EMOJI['book']} <b>{book_title}</b>\n"
                f"{EMOJI['progress']} <b>Страница {current_page+1} из {total_pages}</b>\n\n"
                f"{pages[current_page]}",
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup
            )
        
        return READING_PAGE_NAVIGATION
    
    async def handle_page_navigation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка навигации по страницам (callback)."""
        query = update.callback_query
        await query.answer()
        
        if query.data.startswith("nav_"):
            # Навигация: nav_{book_id}_{page_num}
            parts = query.data.split("_")
            book_id = int(parts[1])
            page_num = int(parts[2])
            
            await self.show_book_page(update, context, book_id, page_num)
            return READING_PAGE_NAVIGATION
        
        elif query.data.startswith("bookmark_"):
            # Закладка: bookmark_{book_id}_{page_num}
            parts = query.data.split("_")
            book_id = int(parts[1])
            page_num = int(parts[2])
            
            await query.edit_message_text(
                f"{EMOJI['bookmark']} <b>Закладка установлена на странице {page_num+1}!</b>",
                parse_mode=ParseMode.HTML
            )
            return READING_PAGE_NAVIGATION
        
        elif query.data == "back_to_menu":
            # Возврат в меню
            await self.back_to_menu(update, context)
            return CHOOSING
    
    # ========== ДОПОЛНИТЕЛЬНЫЕ МЕТОДЫ ==========
    
    async def delete_book(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начать удаление книги."""
        try:
            books = self.db.get_all_books()
            
            if not books:
                await update.message.reply_text(
                    f"{EMOJI['list']} <b>Нет книг для удаления.</b>",
                    parse_mode=ParseMode.HTML
                )
                return CHOOSING
            
            response = f"{EMOJI['trash']} <b>Выберите ID книги для удаления:</b>\n\n"
            
            for book in books[:10]:
                response += f"<b>ID {book['id']}:</b> {book['title'][:30]}...\n"
            
            if len(books) > 10:
                response += f"\n<i>Показано 10 из {len(books)} книг</i>"
            
            response += f"\n\n<b>Введите ID книги для удаления:</b>"
            
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
            
            # Пробуем удалить книгу
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
            
            if not books:
                await update.message.reply_text(
                    f"{EMOJI['info']} <b>В библиотеке пока нет книг.</b>",
                    parse_mode=ParseMode.HTML
                )
                return
            
            # Собираем статистику
            total_books = len(books)
            
            # Статистика по жанрам
            genres = {}
            authors = {}
            
            for book in books:
                genre = book.get('genre', 'Не указан')
                author = book.get('author', 'Неизвестен')
                
                genres[genre] = genres.get(genre, 0) + 1
                authors[author] = authors.get(author, 0) + 1
            
            # Топ жанров и авторов
            top_genres = sorted(genres.items(), key=lambda x: x[1], reverse=True)[:3]
            top_authors = sorted(authors.items(), key=lambda x: x[1], reverse=True)[:3]
            
            response = f"{EMOJI['trophy']} <b>Статистика библиотеки</b>\n\n"
            response += f"<b>Всего книг:</b> {total_books}\n\n"
            
            if top_genres:
                response += f"<b>Топ жанров:</b>\n"
                for genre, count in top_genres:
                    response += f"  {EMOJI['pencil']} {genre}: {count} книг\n"
            
            if top_authors:
                response += f"\n<b>Топ авторов:</b>\n"
                for author, count in top_authors:
                    response += f"  {EMOJI['user']} {author}: {count} книг\n"
            
            await update.message.reply_text(response, parse_mode=ParseMode.HTML)
            
        except Exception as e:
            self.logger.error(f"Ошибка статистики: {e}")
            await update.message.reply_text(
                f"{EMOJI['cross']} <b>Ошибка при получении статистики:</b>\n{str(e)}",
                parse_mode=ParseMode.HTML
            )
    
    async def back_to_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Вернуться в главное меню."""
        keyboard = [
            [KeyboardButton(f"{EMOJI['search']} Поиск"), KeyboardButton(f"{EMOJI['list']} Все книги")],
            [KeyboardButton(f"{EMOJI['plus']} Добавить"), KeyboardButton(f"{EMOJI['read']} Читать")],
            [KeyboardButton(f"{EMOJI['trash']} Удалить"), KeyboardButton(f"{EMOJI['info']} Статистика")],
            [KeyboardButton(f"{EMOJI['help']} Помощь")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.callback_query.message.reply_text(
            f"{EMOJI['home']} <b>Главное меню</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )
        return CHOOSING
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отмена текущего действия."""
        await update.message.reply_text(
            f"{EMOJI['cross']} <b>Действие отменено</b>",
            parse_mode=ParseMode.HTML
        )
        # Возвращаем в главное меню
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
    
    # ========== НАСТРОЙКА ОБРАБОТЧИКОВ ==========
    
    def setup(self):
        """Настройка обработчиков бота."""
        self.application = Application.builder().token(self.token).build()
        
        # Основной ConversationHandler
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("start", self.start)],
            states={
                CHOOSING: [
                    MessageHandler(filters.Regex(f"^{EMOJI['search']} Поиск$"), self.search_books),
                    MessageHandler(filters.Regex(f"^{EMOJI['list']} Все книги$"), self.my_books),
                    MessageHandler(filters.Regex(f"^{EMOJI['plus']} Добавить$"), self.add_book),
                    MessageHandler(filters.Regex(f"^{EMOJI['read']} Читать$"), self.read_book_command),
                    MessageHandler(filters.Regex(f"^{EMOJI['trash']} Удалить$"), self.delete_book),
                    MessageHandler(filters.Regex(f"^{EMOJI['info']} Статистика$"), self.show_stats),
                    MessageHandler(filters.Regex(f"^{EMOJI['help']} Помощь$"), self.help_cmd),
                    CommandHandler("help", self.help_cmd),
                    CommandHandler("mybooks", self.my_books),
                    CommandHandler("stats", self.show_stats),
                    CommandHandler("read", self.read_book_command),
                ],
                TYPING_SEARCH: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_search),
                ],
                TYPING_BOOK_INFO: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_add_choice),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_book_details),
                ],
                READING_BOOK_SELECTION: [
                    CallbackQueryHandler(self.handle_book_selection, pattern="^read_"),
                ],
                READING_PAGE_NAVIGATION: [
                    CallbackQueryHandler(self.handle_page_navigation, pattern="^(nav_|bookmark_|back_to_menu|page_info)"),
                ],
                CONFIRM_DELETE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.confirm_delete),
                ],
            },
            fallbacks=[CommandHandler("cancel", self.cancel)],
        )
        
        self.application.add_handler(conv_handler)
        
        # Отдельные команды для удобства
        self.application.add_handler(CommandHandler("search", self.search_books))
        self.application.add_handler(CommandHandler("add", self.add_book))
        self.application.add_handler(CommandHandler("delete", self.delete_book))
        self.application.add_handler(CommandHandler("read", self.read_book_command))
    
    def run(self):
        """Запуск бота."""
        self.setup()
        print("=" * 60)
        print("🤖 BookBot запущен с функцией чтения книг!")
        print("📱 Перейдите в Telegram и используйте /start")
        print("=" * 60)
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)


def main():
    """Главная функция запуска бота."""
    parser = argparse.ArgumentParser(description="Telegram BookBot с функцией чтения")
    parser.add_argument('--token', help='Токен Telegram бота')
    
    args = parser.parse_args()
    
    token = args.token or os.getenv('TELEGRAM_TOKEN')
    
    if not token:
        print("❌ ОШИБКА: Не указан токен бота")
        print("\n📝 Использование:")
        print("   python telegram_bot.py --token 'ВАШ_ТОКЕН'")
        print("\n🔧 Или установите переменную окружения:")
        print("   set TELEGRAM_TOKEN=ВАШ_ТОКЕН")
        print("   python telegram_bot.py")
        print("\n🔑 Токен можно получить у @BotFather в Telegram")
        sys.exit(1)
    
    # Запускаем бота
    bot = BookBot(token)
    bot.run()


if __name__ == "__main__":
    main()
