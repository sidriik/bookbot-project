import asyncio
import logging
import sys
import argparse
from typing import Dict, List, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters, ConversationHandler
)
from telegram.constants import ParseMode
from database import DatabaseManager

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния диалога
(
    MAIN_MENU, 
    ADDING_BOOK, 
    ADDING_BOOK_DETAILS, 
    ADDING_BOOK_CONTENT,
    SEARCHING_BOOKS,
    READING_BOOK,
    DELETING_BOOK,
    VIEWING_STATS,
    VIEWING_ALL_BOOKS
) = range(9)

# Эмодзи
EMOJI = {
    "search": "🔍", "star": "⭐", "fire": "🔥", "trophy": "🏆", "plus": "➕",
    "list": "📋", "help": "❓", "back": "↩️", "home": "🏠", "check": "✅",
    "cross": "❌", "book": "📚", "user": "👤", "pencil": "✏️", "bookshelf": "📖",
    "trash": "🗑️", "info": "ℹ️", "read": "📖", "bookmark": "🔖", 
    "prev": "⬅️", "next": "➡️", "progress": "📊", "stats": "📈"
}

class UniversalBookBot:
    def __init__(self, token: str):
        self.token = token
        self.application = None
        self.db = DatabaseManager('telegram_books.db')
        
    def get_main_keyboard(self) -> ReplyKeyboardMarkup:
        """Основная клавиатура меню"""
        keyboard = [
            [
                KeyboardButton(f"{EMOJI['search']} Поиск"), 
                KeyboardButton(f"{EMOJI['list']} Мои книги")
            ],
            [
                KeyboardButton(f"{EMOJI['plus']} Добавить книгу"), 
                KeyboardButton(f"{EMOJI['read']} Читать")
            ],
            [
                KeyboardButton(f"{EMOJI['trash']} Удалить"), 
                KeyboardButton(f"{EMOJI['stats']} Статистика")
            ],
            [
                KeyboardButton(f"{EMOJI['help']} Помощь")
            ]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    def get_reading_keyboard(self, current_page: int, total_pages: int) -> ReplyKeyboardMarkup:
        """Клавиатура для чтения книги"""
        keyboard = []
        
        nav_buttons = []
        if current_page > 1:
            nav_buttons.append(KeyboardButton("⬅️ Назад"))
        
        nav_buttons.append(KeyboardButton("🔖 Сохранить прогресс"))
        
        if current_page < total_pages:
            nav_buttons.append(KeyboardButton("➡️ Вперед"))
        
        if nav_buttons:
            keyboard.append(nav_buttons)
        
        keyboard.append([KeyboardButton("🏠 В главное меню")])
        
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user = update.effective_user
        user_id = user.id
        
        # Регистрация пользователя (если нужно)
        try:
            # Проверяем/создаем таблицу пользователей
            self.db.execute_query('''
                CREATE TABLE IF NOT EXISTS bot_users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Добавляем пользователя если его нет
            self.db.execute_query(
                'INSERT OR IGNORE INTO bot_users (user_id, username, first_name) VALUES (?, ?, ?)',
                (user_id, user.username, user.first_name)
            )
        except:
            pass  # Игнорируем ошибки пользователей
        
        welcome_text = (
            f"{EMOJI['bookshelf']} <b>Добро пожаловать, {user.first_name}!</b>\n\n"
            f"Я - <b>Universal BookBot</b> - ваш персональный библиотекарь.\n\n"
            "<b>Что я умею:</b>\n"
            f"• {EMOJI['plus']} Добавлять книги для учета и чтения\n"
            f"• {EMOJI['search']} Искать книги по названию, автору, жанру\n"
            f"• {EMOJI['read']} Читать книги с постраничной навигацией\n"
            f"• {EMOJI['bookmark']} Сохранять прогресс чтения\n"
            f"• {EMOJI['list']} Просматривать всю библиотеку\n"
            f"• {EMOJI['stats']} Смотреть статистику\n"
            f"• {EMOJI['trash']} Удалять книги\n\n"
            "Используйте кнопки меню или команды для навигации."
        )
        
        reply_markup = self.get_main_keyboard()
        
        if update.message:
            await update.message.reply_text(welcome_text, 
                                          parse_mode=ParseMode.HTML,
                                          reply_markup=reply_markup)
        elif update.callback_query:
            await update.callback_query.message.reply_text(welcome_text,
                                                         parse_mode=ParseMode.HTML,
                                                         reply_markup=reply_markup)
        
        return MAIN_MENU
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать помощь"""
        help_text = (
            f"{EMOJI['help']} <b>Universal BookBot - помощь</b>\n\n"
            
            "<b>Основные команды:</b>\n"
            "/start - Главное меню\n"
            "/help - Эта справка\n"
            "/add - Добавить книгу\n"
            "/search - Поиск книг\n"
            "/mybooks - Все мои книги\n"
            "/read - Читать книгу\n"
            "/delete - Удалить книгу\n"
            "/stats - Статистика\n\n"
            
            "<b>Добавление книги:</b>\n"
            "1. <b>Без текста</b> (для учета):\n"
            "   <code>Название | Автор | Жанр</code>\n\n"
            "2. <b>С текстом</b> (для чтения):\n"
            "   <code>Название | Автор | Жанр | Текст книги</code>\n\n"
            
            "<b>Примеры:</b>\n"
            "<code>Война и мир | Толстой | Роман</code>\n"
            "<code>Гарри Поттер | Роулинг | Фэнтези | Текст первой главы...</code>\n\n"
            
            f"{EMOJI['bookmark']} <i>При чтении нажимайте 'Сохранить прогресс' для сохранения страницы</i>"
        )
        
        if update.message:
            await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)
        elif update.callback_query:
            await update.callback_query.message.reply_text(help_text, parse_mode=ParseMode.HTML)
        
        return MAIN_MENU
    
    async def show_all_books(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать все книги пользователя"""
        try:
            # Получаем все книги (и простые, и с текстом)
            books = self.db.get_all_books()
            books_with_content = self.db.get_books_with_content()
            
            response = f"{EMOJI['bookshelf']} <b>Ваша библиотека</b>\n\n"
            
            if not books and not books_with_content:
                response = "📚 Ваша библиотека пуста. Добавьте первую книгу!"
                if update.message:
                    await update.message.reply_text(response, parse_mode=ParseMode.HTML)
                return MAIN_MENU
            
            # Книги для учета
            if books:
                response += f"<b>Книги для учета ({len(books)}):</b>\n"
                for i, book in enumerate(books[:10], 1):
                    status = book.get('status', 'не указан')
                    response += f"{i}. <b>{book['title'][:30]}</b>\n"
                    response += f"   Автор: {book['author']} | Жанр: {book['genre']}\n"
                    response += f"   ID: {book['id']} | Статус: {status}\n\n"
                
                if len(books) > 10:
                    response += f"... и ещё {len(books) - 10} книг\n\n"
            
            # Книги для чтения
            if books_with_content:
                response += f"\n<b>Книги для чтения ({len(books_with_content)}):</b>\n"
                for i, book in enumerate(books_with_content[:10], 1):
                    pages = book.get('pages', 0)
                    response += f"{i}. <b>{book['title'][:30]}</b>\n"
                    response += f"   Автор: {book['author']} | Жанр: {book['genre']}\n"
                    response += f"   ID: {book['id']} | Страниц: {pages}\n\n"
                
                if len(books_with_content) > 10:
                    response += f"... и ещё {len(books_with_content) - 10} книг\n\n"
            
            response += f"\n{EMOJI['info']} Для чтения выберите '{EMOJI['read']} Читать' в меню"
            
            if update.message:
                await update.message.reply_text(response, parse_mode=ParseMode.HTML)
            elif update.callback_query:
                await update.callback_query.message.reply_text(response, parse_mode=ParseMode.HTML)
            
        except Exception as e:
            error_msg = f"{EMOJI['cross']} Ошибка при получении списка книг: {str(e)}"
            logger.error(error_msg)
            if update.message:
                await update.message.reply_text(error_msg)
        
        return MAIN_MENU
    
    async def add_book_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начать добавление книги"""
        add_text = (
            f"{EMOJI['plus']} <b>Выберите тип книги:</b>\n\n"
            "1. <b>Книга для учета</b> - только информация о книге\n"
            "2. <b>Книга с текстом</b> - для чтения в боте\n\n"
            "<i>Введите 1 или 2:</i>"
        )
        
        if update.message:
            await update.message.reply_text(add_text, parse_mode=ParseMode.HTML)
        elif update.callback_query:
            await update.callback_query.message.reply_text(add_text, parse_mode=ParseMode.HTML)
        
        return ADDING_BOOK
    
    async def add_book_type(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработать выбор типа книги"""
        text = update.message.text.strip()
        
        if text == "1":
            context.user_data['add_type'] = 'simple'
            instructions = (
                f"{EMOJI['pencil']} <b>Введите информацию о книге:</b>\n\n"
                "<code>Название | Автор | Жанр | Статус</code>\n\n"
                "<b>Статусы:</b> хочу, читаю, прочитал\n"
                "<b>Пример:</b>\n"
                "<code>Преступление и наказание | Достоевский | Классика | прочитал</code>"
            )
            await update.message.reply_text(instructions, parse_mode=ParseMode.HTML)
            return ADDING_BOOK_DETAILS
            
        elif text == "2":
            context.user_data['add_type'] = 'with_content'
            instructions = (
                f"{EMOJI['pencil']} <b>Введите информацию о книге с текстом:</b>\n\n"
                "<code>Название | Автор | Жанр | Текст книги</code>\n\n"
                "<b>Пример:</b>\n"
                "<code>Мастер и Маргарита | Булгаков | Роман | В час жаркого весеннего заката...</code>\n\n"
                "<i>Текст можно вводить большими частями</i>"
            )
            await update.message.reply_text(instructions, parse_mode=ParseMode.HTML)
            return ADDING_BOOK_CONTENT
            
        else:
            await update.message.reply_text("Пожалуйста, введите 1 или 2")
            return ADDING_BOOK
    
    async def add_book_simple(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Добавить простую книгу (без текста)"""
        try:
            text = update.message.text.strip()
            
            # Парсим ввод
            if "|" not in text:
                await update.message.reply_text(
                    "Неверный формат. Используйте: Название | Автор | Жанр | Статус\n\n"
                    "Пример: Преступление и наказание | Достоевский | Классика | прочитал"
                )
                return ADDING_BOOK_DETAILS
            
            parts = [x.strip() for x in text.split("|")]
            if len(parts) < 4:
                await update.message.reply_text(
                    "Не хватает данных. Нужно: Название | Автор | Жанр | Статус"
                )
                return ADDING_BOOK_DETAILS
            
            title, author, genre, status = parts[0], parts[1], parts[2], parts[3].lower()
            
            # Валидация статуса
            valid_statuses = ['хочу', 'читаю', 'прочитал', 'want', 'reading', 'read']
            if status not in valid_statuses:
                await update.message.reply_text(
                    f"Неверный статус. Допустимо: {', '.join(valid_statuses[:3])}"
                )
                return ADDING_BOOK_DETAILS
            
            # Добавляем книгу
            book_id = self.db.add_book(title, author, genre)
            
            # Сохраняем статус в отдельной таблице
            try:
                self.db.execute_query('''
                    CREATE TABLE IF NOT EXISTS book_status (
                        book_id INTEGER PRIMARY KEY,
                        status TEXT,
                        user_id INTEGER,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                self.db.execute_query(
                    'INSERT OR REPLACE INTO book_status (book_id, status, user_id) VALUES (?, ?, ?)',
                    (book_id, status, update.effective_user.id)
                )
            except:
                pass  # Игнорируем ошибки статуса
            
            response = (
                f"{EMOJI['check']} <b>Книга добавлена!</b>\n\n"
                f"<b>📖 Название:</b> {title}\n"
                f"<b>✍️ Автор:</b> {author}\n"
                f"<b>🏷️ Жанр:</b> {genre}\n"
                f"<b>📊 Статус:</b> {status}\n"
                f"<b>🆔 ID:</b> {book_id}"
            )
            
            await update.message.reply_text(response, parse_mode=ParseMode.HTML)
            
        except Exception as e:
            logger.error(f"Error adding simple book: {e}")
            await update.message.reply_text(f"{EMOJI['cross']} Ошибка при добавлении книги")
        
        return MAIN_MENU
    
    async def add_book_with_content(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Добавить книгу с текстом"""
        try:
            text = update.message.text.strip()
            
            if "|" not in text or text.count("|") < 3:
                await update.message.reply_text(
                    "Неверный формат. Используйте: Название | Автор | Жанр | Текст книги\n\n"
                    "Пример: Гарри Поттер | Роулинг | Фэнтези | Текст книги..."
                )
                return ADDING_BOOK_CONTENT
            
            parts = [x.strip() for x in text.split("|", 3)]
            title, author, genre, content = parts[0], parts[1], parts[2], parts[3]
            
            if len(content) < 10:
                await update.message.reply_text("Текст слишком короткий (минимум 10 символов)")
                return ADDING_BOOK_CONTENT
            
            # Добавляем книгу с текстом
            book_id = self.db.add_book_with_content(title, author, genre, content)
            pages = (len(content) // 2000) + 1
            
            response = (
                f"{EMOJI['check']} <b>Книга с текстом добавлена!</b>\n\n"
                f"<b>📖 Название:</b> {title}\n"
                f"<b>✍️ Автор:</b> {author}\n"
                f"<b>🏷️ Жанр:</b> {genre}\n"
                f"<b>📄 Страниц:</b> {pages}\n"
                f"<b>🆔 ID:</b> {book_id}\n\n"
                f"{EMOJI['read']} Теперь вы можете читать эту книгу в боте!"
            )
            
            await update.message.reply_text(response, parse_mode=ParseMode.HTML)
            
        except Exception as e:
            logger.error(f"Error adding book with content: {e}")
            await update.message.reply_text(f"{EMOJI['cross']} Ошибка при добавлении книги")
        
        return MAIN_MENU
    
    async def search_books_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начать поиск книг"""
        search_text = (
            f"{EMOJI['search']} <b>Поиск книг</b>\n\n"
            "Введите запрос для поиска:\n"
            "• Название книги\n"
            "• Автор\n"
            "• Жанр\n"
            "• Любое ключевое слово\n\n"
            "<i>Ищет по всем книгам в библиотеке</i>"
        )
        
        if update.message:
            await update.message.reply_text(search_text, parse_mode=ParseMode.HTML)
        elif update.callback_query:
            await update.callback_query.message.reply_text(search_text, parse_mode=ParseMode.HTML)
        
        return SEARCHING_BOOKS
    
    async def search_books_execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Выполнить поиск книг"""
        try:
            query = update.message.text.strip()
            
            if not query:
                await update.message.reply_text("Введите текст для поиска")
                return SEARCHING_BOOKS
            
            # Ищем в обеих таблицах
            books = self.db.search_books(query)
            books_with_content = []
            
            # Дополнительный поиск в книгах с контентом
            try:
                books_with_content = self.db.execute_query(
                    '''SELECT id, title, author, genre FROM books_with_content 
                       WHERE title LIKE ? OR author LIKE ? OR genre LIKE ?''',
                    (f'%{query}%', f'%{query}%', f'%{query}%')
                )
            except:
                pass
            
            all_books = []
            if books:
                all_books.extend([dict(book) for book in books])
            if books_with_content:
                all_books.extend([{
                    'id': b[0],
                    'title': b[1],
                    'author': b[2],
                    'genre': b[3],
                    'type': 'with_content'
                } for b in books_with_content])
            
            if not all_books:
                response = f"{EMOJI['cross']} По запросу '{query}' ничего не найдено."
                await update.message.reply_text(response)
                return MAIN_MENU
            
            response = f"{EMOJI['search']} <b>Результаты поиска:</b> '{query}'\n\n"
            
            for i, book in enumerate(all_books[:10], 1):
                book_type = "📄" if book.get('type') == 'with_content' else "📖"
                response += f"{i}. {book_type} <b>{book['title'][:40]}</b>\n"
                response += f"   ✍️ {book['author']} | 🏷️ {book['genre']}\n"
                response += f"   🆔 ID: {book['id']}\n\n"
            
            if len(all_books) > 10:
                response += f"... и ещё {len(all_books) - 10} книг"
            
            await update.message.reply_text(response, parse_mode=ParseMode.HTML)
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            await update.message.reply_text(f"{EMOJI['cross']} Ошибка при поиске")
        
        return MAIN_MENU
    
    async def read_book_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начать чтение книги - показать список книг с текстом"""
        try:
            books = self.db.get_books_with_content()
            
            if not books:
                response = f"{EMOJI['cross']} Нет книг для чтения. Сначала добавьте книгу с текстом."
                if update.message:
                    await update.message.reply_text(response)
                return MAIN_MENU
            
            response = f"{EMOJI['read']} <b>Выберите книгу для чтения:</b>\n\n"
            
            for book in books[:15]:
                pages = book.get('pages', 0)
                response += f"<b>{book['title'][:30]}</b>\n"
                response += f"Автор: {book['author']} | Жанр: {book['genre']}\n"
                response += f"Страниц: {pages} | ID: {book['id']}\n\n"
            
            if len(books) > 15:
                response += f"\nПоказано 15 из {len(books)} книг"
            
            response += "\n<b>Введите ID книги для чтения:</b>"
            
            if update.message:
                await update.message.reply_text(response, parse_mode=ParseMode.HTML)
            elif update.callback_query:
                await update.callback_query.message.reply_text(response, parse_mode=ParseMode.HTML)
            
            return READING_BOOK
            
        except Exception as e:
            logger.error(f"Read start error: {e}")
            error_msg = f"{EMOJI['cross']} Ошибка при загрузке списка книг"
            if update.message:
                await update.message.reply_text(error_msg)
            
            return MAIN_MENU
    
    async def read_book_page(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Чтение конкретной страницы книги"""
        try:
            user_input = update.message.text.strip()
            user_id = update.effective_user.id
            
            # Если это ID книги (первый вход)
            if 'current_book_id' not in context.user_data:
                try:
                    book_id = int(user_input)
                    context.user_data['current_book_id'] = book_id
                    current_page = 1
                except ValueError:
                    await update.message.reply_text("Введите числовой ID книги")
                    return READING_BOOK
            else:
                # Обработка команд навигации
                book_id = context.user_data['current_book_id']
                current_page = context.user_data.get('current_page', 1)
                
                if user_input == "⬅️ Назад":
                    if current_page > 1:
                        current_page -= 1
                elif user_input == "➡️ Вперед":
                    current_page += 1
                elif user_input == "🔖 Сохранить прогресс":
                    # Сохраняем прогресс
                    self.db.save_reading_progress(user_id, book_id, current_page)
                    await update.message.reply_text(f"{EMOJI['bookmark']} Прогресс сохранен! Страница {current_page}")
                elif user_input == "🏠 В главное меню":
                    # Сохраняем прогресс перед выходом
                    self.db.save_reading_progress(user_id, book_id, current_page)
                    await self.back_to_menu(update, context)
                    return MAIN_MENU
            
            # Получаем страницу книги
            book_page = self.db.get_book_content(book_id, current_page)
            
            if not book_page:
                await update.message.reply_text(f"{EMOJI['cross']} Книга не найдена или не содержит текста")
                return MAIN_MENU
            
            # Сохраняем текущую страницу
            context.user_data['current_page'] = current_page
            
            # Получаем сохраненный прогресс
            saved_page = self.db.get_reading_progress(user_id, book_id)
            if saved_page:
                progress_text = f"Сохраненная страница: {saved_page}"
            else:
                progress_text = "Прогресс не сохранен"
            
            # Создаем ответ
            response = (
                f"{EMOJI['book']} <b>{book_page['title']}</b>\n"
                f"✍️ Автор: {book_page['author']}\n"
                f"🏷️ Жанр: {book_page['genre']}\n"
                f"📄 Страница: <b>{current_page}/{book_page['total_pages']}</b>\n"
                f"{EMOJI['progress']} Прогресс: {book_page['percentage']}%\n"
                f"{EMOJI['bookmark']} {progress_text}\n\n"
                f"{book_page['content'][:1500]}"
            )
            
            if len(book_page['content']) > 1500:
                response += "\n\n<i>(текст сокращен, продолжите чтение)</i>"
            
            # Клавиатура для навигации
            reply_markup = self.get_reading_keyboard(current_page, book_page['total_pages'])
            
            await update.message.reply_text(response, 
                                          parse_mode=ParseMode.HTML,
                                          reply_markup=reply_markup)
            
            return READING_BOOK
            
        except Exception as e:
            logger.error(f"Read page error: {e}")
            await update.message.reply_text(f"{EMOJI['cross']} Ошибка при чтении книги")
            return MAIN_MENU
    
    async def delete_book_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начать удаление книги"""
        try:
            # Получаем все книги
            books = self.db.get_all_books()
            books_with_content = self.db.get_books_with_content()
            
            if not books and not books_with_content:
                await update.message.reply_text(f"{EMOJI['cross']} Нет книг для удаления")
                return MAIN_MENU
            
            response = f"{EMOJI['trash']} <b>Выберите книгу для удаления:</b>\n\n"
            
            all_books = []
            if books:
                for book in books[:5]:
                    book['type'] = 'simple'
                    all_books.append(book)
            
            if books_with_content:
                for book in books_with_content[:5]:
                    book['type'] = 'with_content'
                    all_books.append(book)
            
            for i, book in enumerate(all_books, 1):
                book_type = "📄" if book['type'] == 'with_content' else "📖"
                response += f"{i}. {book_type} <b>{book['title'][:30]}</b>\n"
                response += f"   ID: {book['id']} | Автор: {book['author']}\n\n"
            
            response += "\n<b>Введите ID книги для удаления:</b>"
            
            await update.message.reply_text(response, parse_mode=ParseMode.HTML)
            return DELETING_BOOK
            
        except Exception as e:
            logger.error(f"Delete start error: {e}")
            await update.message.reply_text(f"{EMOJI['cross']} Ошибка при загрузке списка книг")
            return MAIN_MENU
    
    async def delete_book_confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Подтвердить удаление книги"""
        try:
            book_id = int(update.message.text.strip())
            
            # Пробуем удалить из обеих таблиц
            success = self.db.delete_book(book_id)
            
            if success:
                response = f"{EMOJI['check']} Книга с ID {book_id} успешно удалена!"
            else:
                response = f"{EMOJI['cross']} Книга с ID {book_id} не найдена"
            
            await update.message.reply_text(response)
            
        except ValueError:
            await update.message.reply_text("Пожалуйста, введите числовой ID книги")
            return DELETING_BOOK
        except Exception as e:
            logger.error(f"Delete error: {e}")
            await update.message.reply_text(f"{EMOJI['cross']} Ошибка при удалении книги")
        
        return MAIN_MENU
    
    async def show_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать статистику"""
        try:
            books = self.db.get_all_books()
            books_with_content = self.db.get_books_with_content()
            
            total_books = len(books) + len(books_with_content)
            
            # Статистика по статусам
            status_stats = {'хочу': 0, 'читаю': 0, 'прочитал': 0}
            try:
                status_data = self.db.execute_query(
                    'SELECT status, COUNT(*) FROM book_status GROUP BY status'
                )
                for status, count in status_data:
                    if status in status_stats:
                        status_stats[status] = count
            except:
                pass
            
            # Подсчитываем общее количество страниц в книгах с контентом
            total_pages = 0
            for book in books_with_content:
                total_pages += book.get('pages', 0)
            
            response = (
                f"{EMOJI['stats']} <b>Статистика библиотеки</b>\n\n"
                f"📊 <b>Общая статистика:</b>\n"
                f"• Всего книг: <b>{total_books}</b>\n"
                f"• Книг для учета: {len(books)}\n"
                f"• Книг для чтения: {len(books_with_content)}\n"
                f"• Всего страниц текста: {total_pages}\n\n"
                
                f"📈 <b>Статистика по статусам:</b>\n"
                f"• {EMOJI['star']} Хочу прочитать: {status_stats['хочу']}\n"
                f"• {EMOJI['progress']} Читаю сейчас: {status_stats['читаю']}\n"
                f"• {EMOJI['check']} Прочитано: {status_stats['прочитал']}\n\n"
                
                f"{EMOJI['info']} <i>Статистика обновляется при добавлении/удалении книг</i>"
            )
            
            if update.message:
                await update.message.reply_text(response, parse_mode=ParseMode.HTML)
            elif update.callback_query:
                await update.callback_query.message.reply_text(response, parse_mode=ParseMode.HTML)
            
        except Exception as e:
            logger.error(f"Stats error: {e}")
            error_msg = f"{EMOJI['cross']} Ошибка при получении статистики"
            if update.message:
                await update.message.reply_text(error_msg)
        
        return MAIN_MENU
    
    async def back_to_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Вернуться в главное меню"""
        try:
            # Очищаем данные контекста
            if 'current_book_id' in context.user_data:
                del context.user_data['current_book_id']
            if 'current_page' in context.user_data:
                del context.user_data['current_page']
            
            reply_markup = self.get_main_keyboard()
            menu_text = f"{EMOJI['home']} <b>Главное меню</b>\n\nВыберите действие:"
            
            if update.message:
                await update.message.reply_text(menu_text, 
                                              parse_mode=ParseMode.HTML,
                                              reply_markup=reply_markup)
            elif update.callback_query:
                await update.callback_query.message.reply_text(menu_text,
                                                             parse_mode=ParseMode.HTML,
                                                             reply_markup=reply_markup)
            
        except Exception as e:
            logger.error(f"Back to menu error: {e}")
        
        return MAIN_MENU
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отменить текущее действие"""
        await self.back_to_menu(update, context)
        return ConversationHandler.END
    
    def setup_handlers(self):
        """Настройка всех обработчиков"""
        conv_handler = ConversationHandler(
            entry_points=[
                CommandHandler("start", self.start),
                CommandHandler("help", self.help_command),
                MessageHandler(filters.Regex(f"^{EMOJI['home']}") | filters.Regex("^🏠"), self.back_to_menu)
            ],
            states={
                MAIN_MENU: [
                    CommandHandler("start", self.start),
                    CommandHandler("help", self.help_command),
                    CommandHandler("add", self.add_book_start),
                    CommandHandler("search", self.search_books_start),
                    CommandHandler("mybooks", self.show_all_books),
                    CommandHandler("read", self.read_book_start),
                    CommandHandler("delete", self.delete_book_start),
                    CommandHandler("stats", self.show_stats),
                    
                    MessageHandler(filters.Regex(f"^{EMOJI['plus']} Добавить книгу$"), self.add_book_start),
                    MessageHandler(filters.Regex(f"^{EMOJI['search']} Поиск$"), self.search_books_start),
                    MessageHandler(filters.Regex(f"^{EMOJI['list']} Мои книги$"), self.show_all_books),
                    MessageHandler(filters.Regex(f"^{EMOJI['read']} Читать$"), self.read_book_start),
                    MessageHandler(filters.Regex(f"^{EMOJI['trash']} Удалить$"), self.delete_book_start),
                    MessageHandler(filters.Regex(f"^{EMOJI['stats']} Статистика$"), self.show_stats),
                    MessageHandler(filters.Regex(f"^{EMOJI['help']} Помощь$"), self.help_command),
                    
                    MessageHandler(filters.Regex("^/?"), self.back_to_menu),  # Любая команда
                ],
                
                ADDING_BOOK: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.add_book_type),
                    CommandHandler("cancel", self.cancel),
                ],
                
                ADDING_BOOK_DETAILS: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.add_book_simple),
                    CommandHandler("cancel", self.cancel),
                ],
                
                ADDING_BOOK_CONTENT: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.add_book_with_content),
                    CommandHandler("cancel", self.cancel),
                ],
                
                SEARCHING_BOOKS: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.search_books_execute),
                    CommandHandler("cancel", self.cancel),
                ],
                
                READING_BOOK: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.read_book_page),
                    CommandHandler("cancel", self.cancel),
                ],
                
                DELETING_BOOK: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.delete_book_confirm),
                    CommandHandler("cancel", self.cancel),
                ],
                
                VIEWING_STATS: [
                    CommandHandler("cancel", self.cancel),
                ],
                
                VIEWING_ALL_BOOKS: [
                    CommandHandler("cancel", self.cancel),
                ],
            },
            fallbacks=[
                CommandHandler("cancel", self.cancel),
                CommandHandler("start", self.start),
                MessageHandler(filters.Regex(f"^{EMOJI['home']}") | filters.Regex("^🏠"), self.back_to_menu)
            ],
            per_message=False,
        )
        
        self.application.add_handler(conv_handler)
        
        # Обработчик ошибок
        self.application.add_error_handler(self.error_handler)
    
    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        """Глобальный обработчик ошибок"""
        logger.error(f"Exception while handling an update: {context.error}")
        
        try:
            if update and hasattr(update, 'effective_chat'):
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"{EMOJI['cross']} Произошла ошибка. Пожалуйста, попробуйте снова или используйте /start"
                )
        except:
            pass
    
    def run(self):
        """Запуск бота"""
        try:
            # Создаем Application
            self.application = (
                Application.builder()
                .token(self.token)
                .connect_timeout(30.0)
                .read_timeout(30.0)
                .write_timeout(30.0)
                .build()
            )
            
            # Настраиваем обработчики
            self.setup_handlers()

            
            # Запускаем бота
            self.application.run_polling(
                poll_interval=1.0,
                timeout=20,
                drop_pending_updates=True,
                allowed_updates=Update.ALL_TYPES
            )
            
        except Exception as e:
            logger.error(f"Failed to start bot: {e}")
            sys.exit(1)

def main():
    """Основная функция запуска"""
    parser = argparse.ArgumentParser(description='Universal BookBot - все функции в одном боте')
    parser.add_argument('--token', type=str, help='Токен Telegram бота')
    parser.add_argument('--test', action='store_true', help='Тестовый режим')
    
    args = parser.parse_args()
    
    # Получаем токен
    token = args.token
    
    if not token:
        print(" Токен бота не указан!")
        print("Использование: python telegram_bot.py --token 'ВАШ_ТОКЕН'")
        print("Или создайте config.py с BOT_TOKEN")
        sys.exit(1)
    
    # Запускаем бота
    bot = UniversalBookBot(token)
    bot.run()

if __name__ == "__main__":
    main()
