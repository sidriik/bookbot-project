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

from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    ContextTypes, 
    ConversationHandler,
    filters
)
from telegram.constants import ParseMode

# Импортируем DatabaseManager
from database import DatabaseManager

# Словарь эмодзи
EMOJI = {
    "search": "🔍", "star": "⭐", "fire": "🔥", "trophy": "🏆", "plus": "➕",
    "list": "📋", "help": "❓", "back": "↩️", "home": "🏠", "check": "✅",
    "cross": "❌", "book": "📚", "user": "👤", "pencil": "✏️", "bookshelf": "📖",
    "trash": "🗑️", "info": "ℹ️", "read": "📖", "bookmark": "🔖", 
    "prev": "⬅️", "next": "➡️", "progress": "📊"
}

# Состояния диалога
(
    CHOOSING, TYPING_SEARCH, TYPING_BOOK_INFO, 
    CONFIRM_DELETE, TYPING_BOOK_ID, READING,
    TYPING_BOOK_DETAILS
) = range(7)

class BookBot:
    """Основной класс Telegram бота."""
    
    def __init__(self, token: str):
        self.token = token
        self.application = None
        
        # Подключаем базу
        try:
            self.db = DatabaseManager('telegram_books.db')
            print("[OK] База данных подключена")
        except Exception as e:
            print(f"[ERROR] Ошибка БД: {e}")
            raise
        
        logging.basicConfig(
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            level=logging.WARNING
        )
        self.logger = logging.getLogger(__name__)
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /start."""
        try:
            user = update.effective_user
            print(f"[START] от {user.id} (@{user.username})")
            
            # Сначала простое сообщение
            await update.message.reply_text(
                "📚 Привет! Я BookBot - ваш персональный библиотекарь.",
                parse_mode=ParseMode.HTML
            )
            
            # Затем клавиатура
            keyboard = [
                [KeyboardButton(f"{EMOJI['search']} Поиск"), KeyboardButton(f"{EMOJI['list']} Все книги")],
                [KeyboardButton(f"{EMOJI['plus']} Добавить"), KeyboardButton(f"{EMOJI['read']} Читать")],
                [KeyboardButton(f"{EMOJI['trash']} Удалить"), KeyboardButton(f"{EMOJI['info']} Статистика")],
                [KeyboardButton(f"{EMOJI['help']} Помощь")]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            
            await update.message.reply_text(
                "Выберите действие:",
                reply_markup=reply_markup
            )
            
            return CHOOSING
            
        except Exception as e:
            print(f"[START ERROR] {e}")
            try:
                await update.message.reply_text("Ошибка запуска. Попробуйте /start снова.")
            except:
                pass
            return CHOOSING
    
    async def help_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /help."""
        try:
            help_text = """📚 <b>BookBot - помощь</b>

<b>Основные команды:</b>
/start - Главное меню
/search - Поиск книг
/add - Добавить книгу
/mybooks - Все книги
/delete - Удалить книгу
/read - Читать книги
/stats - Статистика

<b>Формат добавления:</b>
Название | Автор | Жанр
или
Название | Автор | Жанр | Текст книги

<b>Пример:</b>
<code>Война и мир | Толстой | Роман</code>"""
            
            await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)
        except Exception as e:
            print(f"[HELP ERROR] {e}")
    
    # ========== ПОИСК ==========
    
    async def search_books(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            await update.message.reply_text(f"{EMOJI['search']} Введите запрос для поиска:")
            return TYPING_SEARCH
        except Exception as e:
            print(f"[SEARCH ERROR] {e}")
            return CHOOSING
    
    async def handle_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            query = update.message.text.strip()
            if not query:
                await update.message.reply_text("Введите текст для поиска")
                return TYPING_SEARCH
            
            results = self.db.search_books(query)
            
            if not results:
                await update.message.reply_text(f"По запросу '{query}' ничего не найдено.")
                return CHOOSING
            
            response = f"📚 Найдено книг: {len(results)}\n\n"
            for book in results[:5]:
                response += f"<b>{book['title']}</b>\nАвтор: {book['author']}\nЖанр: {book['genre']}\nID: {book['id']}\n\n"
            
            await update.message.reply_text(response, parse_mode=ParseMode.HTML)
            return CHOOSING
            
        except Exception as e:
            print(f"[HANDLE SEARCH ERROR] {e}")
            await update.message.reply_text("Ошибка поиска")
            return CHOOSING
    
    # ========== ДОБАВЛЕНИЕ КНИГ ==========
    
    async def add_book(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начать добавление книги."""
        try:
            await update.message.reply_text(
                f"{EMOJI['plus']} <b>Выберите тип:</b>\n"
                "1. Книга для учета (без текста)\n"
                "2. Книга с текстом\n\n"
                "<b>Введите 1 или 2:</b>",
                parse_mode=ParseMode.HTML
            )
            return TYPING_BOOK_INFO
        except Exception as e:
            print(f"[ADD ERROR] {e}")
            return CHOOSING
    
    async def handle_add_type(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора типа книги."""
        try:
            text = update.message.text.strip()
            
            if text == "1":
                await update.message.reply_text(
                    f"{EMOJI['plus']} <b>Введите в формате:</b>\n"
                    "<code>Название | Автор | Жанр</code>\n\n"
                    "<i>Пример:</i>\n"
                    "<code>Война и мир | Толстой | Роман</code>",
                    parse_mode=ParseMode.HTML
                )
                context.user_data['add_type'] = 'simple'
                return TYPING_BOOK_DETAILS
            elif text == "2":
                await update.message.reply_text(
                    f"{EMOJI['plus']} <b>Введите в формате:</b>\n"
                    "<code>Название | Автор | Жанр | Текст книги</code>\n\n"
                    "<i>Пример:</i>\n"
                    "<code>Гарри Поттер | Роулинг | Фэнтези | Текст книги...</code>",
                    parse_mode=ParseMode.HTML
                )
                context.user_data['add_type'] = 'with_content'
                return TYPING_BOOK_DETAILS
            else:
                await update.message.reply_text("❌ Введите 1 или 2")
                return TYPING_BOOK_INFO
                
        except Exception as e:
            print(f"[HANDLE ADD TYPE ERROR] {e}")
            return CHOOSING
    
    async def handle_add_book_details(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка деталей книги."""
        try:
            text = update.message.text.strip()
            add_type = context.user_data.get('add_type', 'simple')
            
            if add_type == 'simple':
                if "|" not in text or text.count("|") != 2:
                    await update.message.reply_text(
                        "❌ Неверный формат. Используйте: Название | Автор | Жанр\n\n"
                        "<i>Пример:</i>\n<code>Война и мир | Толстой | Роман</code>",
                        parse_mode=ParseMode.HTML
                    )
                    return TYPING_BOOK_DETAILS
                
                parts = [x.strip() for x in text.split("|")]
                title, author, genre = parts[0], parts[1], parts[2]
                
                if len(title) < 2 or len(author) < 2:
                    await update.message.reply_text("❌ Слишком короткое название или автор")
                    return TYPING_BOOK_DETAILS
                
                book_id = self.db.add_book(title, author, genre)
                await update.message.reply_text(
                    f"✅ Книга добавлена! ID: {book_id}\n"
                    f"📖 Название: {title}\n"
                    f"👤 Автор: {author}\n"
                    f"🏷️ Жанр: {genre}"
                )
                
            else:  # with_content
                if "|" not in text or text.count("|") < 3:
                    await update.message.reply_text(
                        "❌ Неверный формат. Используйте: Название | Автор | Жанр | Текст книги\n\n"
                        "<i>Пример:</i>\n<code>Книга | Автор | Жанр | Текст...</code>",
                        parse_mode=ParseMode.HTML
                    )
                    return TYPING_BOOK_DETAILS
                
                parts = [x.strip() for x in text.split("|", 3)]
                if len(parts) < 4:
                    await update.message.reply_text("❌ Неверный формат")
                    return TYPING_BOOK_DETAILS
                
                title, author, genre, content = parts[0], parts[1], parts[2], parts[3]
                
                if len(title) < 2 or len(author) < 2:
                    await update.message.reply_text("❌ Слишком короткое название или автор")
                    return TYPING_BOOK_DETAILS
                
                if len(content) < 10:
                    await update.message.reply_text("❌ Текст слишком короткий (мин. 10 символов)")
                    return TYPING_BOOK_DETAILS
                
                book_id = self.db.add_book_with_content(title, author, genre, content)
                pages = (len(content) // 2000) + 1
                
                await update.message.reply_text(
                    f"✅ Книга с текстом добавлена!\n"
                    f"📖 Название: {title}\n"
                    f"👤 Автор: {author}\n"
                    f"🏷️ Жанр: {genre}\n"
                    f"📄 Страниц: {pages}\n"
                    f"🔢 ID: {book_id}"
                )
            
            # Очищаем данные
            if 'add_type' in context.user_data:
                del context.user_data['add_type']
            
            return CHOOSING
            
        except Exception as e:
            print(f"[ADD DETAILS ERROR] {e}")
            await update.message.reply_text(f"❌ Ошибка добавления: {e}")
            return CHOOSING
    
    # ========== СПИСОК КНИГ ==========
    
    async def my_books(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            books = self.db.get_all_books()
            books_with_content = self.db.get_books_with_content()
            
            if not books and not books_with_content:
                await update.message.reply_text("📚 Библиотека пуста. Добавьте первую книгу!")
                return
            
            response = "📚 <b>Ваша библиотека</b>\n\n"
            
            if books:
                response += f"<b>Книги для учета ({len(books)}):</b>\n"
                for i, book in enumerate(books[:5], 1):
                    response += f"{i}. {book['title']} - {book['author']} (ID: {book['id']})\n"
                if len(books) > 5:
                    response += f"... и еще {len(books) - 5}\n"
                response += "\n"
            
            if books_with_content:
                response += f"<b>Книги для чтения ({len(books_with_content)}):</b>\n"
                for i, book in enumerate(books_with_content[:5], 1):
                    pages = book['pages'] if book['pages'] > 0 else 0
                    response += f"{i}. {book['title']} - {book['author']} (ID: {book['id']}, {pages} стр.)\n"
                if len(books_with_content) > 5:
                    response += f"... и еще {len(books_with_content) - 5}\n"
            
            response += f"\nДля чтения используйте {EMOJI['read']} Читать"
            
            await update.message.reply_text(response, parse_mode=ParseMode.HTML)
            
        except Exception as e:
            print(f"[MYBOOKS ERROR] {e}")
            await update.message.reply_text("❌ Ошибка получения списка")
    
    # ========== ЧТЕНИЕ КНИГ ==========
    
    async def read_book_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            books = self.db.get_books_with_content()
            
            if not books:
                await update.message.reply_text("📖 Нет книг для чтения. Добавьте книгу с текстом!")
                return CHOOSING
            
            response = "📖 <b>Доступные книги:</b>\n\n"
            for book in books[:10]:
                pages = book['pages'] if book['pages'] > 0 else 0
                response += f"<b>ID {book['id']}:</b> {book['title']}\n"
                response += f"   👤 {book['author']} | 📝 {book['genre']} | 📄 {pages} стр.\n\n"
            
            if len(books) > 10:
                response += f"\n<i>Показано 10 из {len(books)} книг</i>"
            
            response += "\n<b>Введите ID книги для чтения:</b>"
            
            await update.message.reply_text(response, parse_mode=ParseMode.HTML)
            return TYPING_BOOK_ID
            
        except Exception as e:
            print(f"[READ MENU ERROR] {e}")
            return CHOOSING
    
    async def handle_read_book(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            book_id = int(update.message.text.strip())
            user_id = update.effective_user.id
            
            book_page = self.db.get_book_content(book_id, 1)
            if not book_page:
                await update.message.reply_text("❌ Книга не найдена или не содержит текста")
                return CHOOSING
            
            saved_page = self.db.get_reading_progress(user_id, book_id)
            current_page = saved_page if saved_page else 1
            
            book_page = self.db.get_book_content(book_id, current_page)
            if not book_page:
                await update.message.reply_text("❌ Ошибка загрузки страницы")
                return CHOOSING
            
            context.user_data['current_book_id'] = book_id
            context.user_data['current_page'] = current_page
            
            keyboard = self._create_reading_keyboard(current_page, book_page['total_pages'])
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            
            response = self._format_book_page(book_page, current_page)
            await update.message.reply_text(response, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
            return READING
            
        except ValueError:
            await update.message.reply_text("❌ Введите числовой ID")
            return TYPING_BOOK_ID
        except Exception as e:
            print(f"[READ ERROR] {e}")
            await update.message.reply_text("❌ Ошибка начала чтения")
            return CHOOSING
    
    async def handle_reading_navigation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            user_id = update.effective_user.id
            command = update.message.text
            
            book_id = context.user_data.get('current_book_id')
            current_page = context.user_data.get('current_page', 1)
            
            if not book_id:
                await update.message.reply_text("❌ Сессия потеряна. Начните заново.")
                return CHOOSING
            
            if command == "⬅️ Назад" and current_page > 1:
                current_page -= 1
            elif command == "➡️ Вперед":
                current_page += 1
            elif command == "🔖 Сохранить":
                self.db.save_reading_progress(user_id, book_id, current_page)
                await update.message.reply_text(f"✅ Прогресс сохранен! Страница {current_page}")
                book_page = self.db.get_book_content(book_id, current_page)
            elif command == "🏠 В меню":
                self.db.save_reading_progress(user_id, book_id, current_page)
                await self.back_to_menu(update, context)
                return CHOOSING
            else:
                await update.message.reply_text("❌ Неизвестная команда")
                book_page = self.db.get_book_content(book_id, current_page)
            
            if 'book_page' not in locals():
                book_page = self.db.get_book_content(book_id, current_page)
            
            if not book_page:
                await update.message.reply_text("❌ Страница не найдена")
                return READING
            
            context.user_data['current_page'] = current_page
            self.db.save_reading_progress(user_id, book_id, current_page)
            
            keyboard = self._create_reading_keyboard(current_page, book_page['total_pages'])
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            
            response = self._format_book_page(book_page, current_page)
            await update.message.reply_text(response, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
            return READING
            
        except Exception as e:
            print(f"[NAV ERROR] {e}")
            return CHOOSING
    
    def _create_reading_keyboard(self, current_page: int, total_pages: int):
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
    
    def _format_book_page(self, book_page, current_page):
        content_preview = book_page['content'][:1500]
        if len(book_page['content']) > 1500:
            content_preview += "..."
            
        return (
            f"📖 <b>{book_page['title']}</b>\n"
            f"👤 {book_page['author']}\n"
            f"📝 Страница {current_page}/{book_page['total_pages']}\n"
            f"📊 {book_page['progress']} ({book_page['percentage']}%)\n\n"
            f"{content_preview}\n\n"
            f"<i>Используйте кнопки для навигации</i>"
        )
    
    # ========== УДАЛЕНИЕ ==========
    
    async def delete_book(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            books = self.db.get_all_books()
            books_with_content = self.db.get_books_with_content()
            
            if not books and not books_with_content:
                await update.message.reply_text("🗑️ Нет книг для удаления")
                return CHOOSING
            
            response = "🗑️ <b>Выберите ID книги для удаления:</b>\n\n"
            
            if books:
                response += "<b>Книги для учета:</b>\n"
                for book in books[:8]:
                    response += f"  ID {book['id']}: {book['title'][:30]}...\n"
            
            if books_with_content:
                response += "\n<b>Книги для чтения:</b>\n"
                for book in books_with_content[:8]:
                    response += f"  ID {book['id']}: {book['title'][:30]}...\n"
            
            response += "\n<b>Введите ID книги:</b>"
            await update.message.reply_text(response, parse_mode=ParseMode.HTML)
            return CONFIRM_DELETE
            
        except Exception as e:
            print(f"[DELETE ERROR] {e}")
            return CHOOSING
    
    async def confirm_delete(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            book_id = int(update.message.text.strip())
            success = self.db.delete_book(book_id)
            
            if success:
                await update.message.reply_text("✅ Книга удалена!")
            else:
                await update.message.reply_text("❌ Книга не найдена")
            
            return CHOOSING
            
        except ValueError:
            await update.message.reply_text("❌ Введите числовой ID")
            return CONFIRM_DELETE
        except Exception as e:
            print(f"[CONFIRM DELETE ERROR] {e}")
            return CHOOSING
    
    # ========== СТАТИСТИКА ==========
    
    async def show_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            books = self.db.get_all_books()
            books_with_content = self.db.get_books_with_content()
            
            total = len(books) + len(books_with_content)
            response = f"📊 <b>Статистика библиотеки</b>\n\n"
            response += f"📚 Всего книг: {total}\n"
            response += f"  📋 Для учета: {len(books)}\n"
            response += f"  📖 Для чтения: {len(books_with_content)}\n"
            
            await update.message.reply_text(response, parse_mode=ParseMode.HTML)
            
        except Exception as e:
            print(f"[STATS ERROR] {e}")
    
    # ========== ВСПОМОГАТЕЛЬНЫЕ ==========
    
    async def back_to_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [
            [KeyboardButton(f"{EMOJI['search']} Поиск"), KeyboardButton(f"{EMOJI['list']} Все книги")],
            [KeyboardButton(f"{EMOJI['plus']} Добавить"), KeyboardButton(f"{EMOJI['read']} Читать")],
            [KeyboardButton(f"{EMOJI['trash']} Удалить"), KeyboardButton(f"{EMOJI['info']} Статистика")],
            [KeyboardButton(f"{EMOJI['help']} Помощь")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text("🏠 <b>Главное меню</b>", parse_mode=ParseMode.HTML, reply_markup=reply_markup)
        return CHOOSING
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("❌ Действие отменено")
        await self.back_to_menu(update, context)
        return CHOOSING
    
    def setup(self):
        """Настройка обработчиков."""
        self.application = (
            Application.builder()
            .token(self.token)
            .connect_timeout(30.0)
            .read_timeout(30.0)
            .write_timeout(30.0)
            .build()
        )
        
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
                    CommandHandler("add", self.add_book),
                    CommandHandler("delete", self.delete_book),
                ],
                TYPING_SEARCH: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_search),
                ],
                TYPING_BOOK_INFO: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_add_type),
                ],
                TYPING_BOOK_DETAILS: [
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
    
    def run(self):
        """Запуск бота."""
        self.setup()
        print("=" * 50)
        print("🤖 BookBot запущен!")
        print("📱 Отправьте /start в Telegram")
        print("⏸️  Ctrl+C для остановки")
        print("=" * 50)
        
        self.application.run_polling(
            poll_interval=1.0,
            timeout=20,
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES
        )


def main():
    parser = argparse.ArgumentParser(description="BookBot")
    parser.add_argument('--token', help='Токен бота')
    
    args = parser.parse_args()
    token = args.token or "8039724055:AAHDEJs6rUxsgN8l2fJphLDAsQfq8FVZTLI"
    
    if not token:
        print("❌ Укажите токен бота")
        sys.exit(1)
    
    bot = BookBot(token)
    bot.run()


if __name__ == "__main__":
    main()
