#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Основной модуль Telegram бота."""

import logging
import argparse
import os
import sys

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

# Импортируем DatabaseManager напрямую из текущей папки
from database import DatabaseManager

EMOJI = {
    "search": "🔍", "star": "⭐️", "fire": "🔥", "trophy": "🏆", "plus": "➕",
    "list": "📋", "help": "❓", "back": "↩️", "home": "🏠", "check": "✅",
    "cross": "❌", "book": "📚", "user": "👤", "pencil": "✏️", "bookshelf": "📖",
    "trash": "🗑️", "info": "ℹ️"
}

CHOOSING, TYPING_SEARCH, TYPING_BOOK_INFO, CONFIRM_DELETE = range(4)

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
            print("✅ База данных успешно подключена")
        except Exception as e:
            print(f"❌ Ошибка подключения к БД: {e}")
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
{EMOJI['plus']} Добавлять новые книги
{EMOJI['list']} Показывать все ваши книги
{EMOJI['trash']} Удалять книги
{EMOJI['trophy']} Показывать статистику

<b>Выберите действие:</b>"""
        
        keyboard = [
            [KeyboardButton(f"{EMOJI['search']} Поиск"), KeyboardButton(f"{EMOJI['list']} Все книги")],
            [KeyboardButton(f"{EMOJI['plus']} Добавить"), KeyboardButton(f"{EMOJI['trash']} Удалить")],
            [KeyboardButton(f"{EMOJI['info']} Статистика"), KeyboardButton(f"{EMOJI['help']} Помощь")]
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
/stats - Статистика

<b>Формат добавления книги:</b>
<code>Название | Автор | Жанр</code>

<b>Пример:</b>
<code>Властелин колец | Толкин | Фэнтези</code>
<code>1984 | Оруэлл | Антиутопия</code>
<code>Война и мир | Толстой | Роман</code>

<b>Для поиска</b> просто введите название, автора или жанр."""
        
        await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)
    
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
            # Ищем книги в базе
            results = self.db.search_books(query)
            
            if not results:
                await update.message.reply_text(
                    f"{EMOJI['search']} <b>По запросу '{query}' ничего не найдено.</b>",
                    parse_mode=ParseMode.HTML
                )
                return CHOOSING
            
            response = f"{EMOJI['search']} <b>Найдено книг: {len(results)}</b>\n\n"
            
            for book in results:
                response += f"<b>{book['title']}</b>\n"
                response += f"{EMOJI['user']} {book['author']}\n"
                response += f"{EMOJI['pencil']} {book['genre']}\n"
                response += f"ID: {book['id']}\n\n"
            
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
            f"{EMOJI['plus']} <b>Введите книгу в формате:</b>\n"
            "<code>Название | Автор | Жанр</code>\n\n"
            "<i>Примеры:</i>\n"
            "<code>Властелин колец | Толкин | Фэнтези</code>\n"
            "<code>1984 | Оруэлл | Антиутопия</code>",
            parse_mode=ParseMode.HTML
        )
        return TYPING_BOOK_INFO
    
    async def handle_add_book(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка добавления книги."""
        text = update.message.text.strip()
        
        if "|" not in text:
            await update.message.reply_text(
                f"{EMOJI['cross']} <b>Неверный формат.</b>\n"
                "Используйте: <code>Название | Автор | Жанр</code>",
                parse_mode=ParseMode.HTML
            )
            return TYPING_BOOK_INFO
        
        try:
            title, author, genre = [x.strip() for x in text.split("|")]
            
            if len(title) < 2 or len(author) < 2:
                await update.message.reply_text(
                    f"{EMOJI['cross']} <b>Слишком короткое название или имя автора.</b>",
                    parse_mode=ParseMode.HTML
                )
                return TYPING_BOOK_INFO
            
            # Проверяем, нет ли уже такой книги
            existing = self.db.search_books(title)
            for book in existing:
                if book['title'].lower() == title.lower() and book['author'].lower() == author.lower():
                    await update.message.reply_text(
                        f"{EMOJI['info']} <b>Эта книга уже есть в библиотеке:</b>\n"
                        f"ID: {book['id']}\n"
                        f"{EMOJI['bookshelf']} {book['title']}",
                        parse_mode=ParseMode.HTML
                    )
                    return CHOOSING
            
            # Добавляем книгу в базу
            book_id = self.db.add_book(title, author, genre)
            
            await update.message.reply_text(
                f"{EMOJI['check']} <b>Книга успешно добавлена!</b>\n\n"
                f"<b>ID:</b> {book_id}\n"
                f"<b>Название:</b> {title}\n"
                f"<b>Автор:</b> {author}\n"
                f"<b>Жанр:</b> {genre}",
                parse_mode=ParseMode.HTML
            )
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
            
            if not books:
                await update.message.reply_text(
                    f"{EMOJI['list']} <b>Ваша библиотека пуста.</b>\n"
                    f"Используйте {EMOJI['plus']} <b>Добавить</b> для первой книги.",
                    parse_mode=ParseMode.HTML
                )
                return
            
            # Если книг много, разбиваем на несколько сообщений
            if len(books) > 10:
                await update.message.reply_text(
                    f"{EMOJI['list']} <b>В вашей библиотеке {len(books)} книг.</b>\n"
                    f"Показаны первые 10. Используйте поиск для фильтрации.",
                    parse_mode=ParseMode.HTML
                )
                books = books[:10]
            
            response = f"{EMOJI['list']} <b>Ваша библиотека</b> ({len(books)} книг)\n\n"
            
            for i, book in enumerate(books, 1):
                response += f"<b>{i}. {book['title']}</b>\n"
                response += f"   {EMOJI['user']} {book['author']}\n"
                response += f"   {EMOJI['pencil']} {book['genre']}\n"
                response += f"   ID: {book['id']}\n\n"
            
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
            
            if not books:
                await update.message.reply_text(
                    f"{EMOJI['list']} <b>Нет книг для удаления.</b>",
                    parse_mode=ParseMode.HTML
                )
                return CHOOSING
            
            response = f"{EMOJI['trash']} <b>Выберите ID книги для удаления:</b>\n\n"
            
            for book in books[:15]:  # Показываем только первые 15
                response += f"<b>ID {book['id']}:</b> {book['title']}\n"
            
            if len(books) > 15:
                response += f"\n<i>Показано 15 из {len(books)} книг</i>"
            
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
       
    async def confirm_delete(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Подтверждение удаления книги."""
        try:
            book_id = int(update.message.text.strip())
            
            # Проверяем, существует ли книга
            book = self.db.get_book(book_id)
            if not book:
                await update.message.reply_text(
                    f"{EMOJI['cross']} <b>Книга с ID {book_id} не найдена.</b>",
                    parse_mode=ParseMode.HTML
                )
                return CHOOSING
            
            # Удаляем книгу
            success = self.db.delete_book(book_id)
            
            if success:
                await update.message.reply_text(
                    f"{EMOJI['check']} <b>Книга успешно удалена!</b>\n\n"
                    f"<b>Название:</b> {book['title']}\n"
                    f"<b>Автор:</b> {book['author']}",
                    parse_mode=ParseMode.HTML
                )
            else:
                await update.message.reply_text(
                    f"{EMOJI['cross']} <b>Не удалось удалить книгу.</b>",
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
            
            # Самые популярные жанры
            genres = {}
            authors = {}
            
            for book in books:
                genre = book['genre']
                author = book['author']
                
                genres[genre] = genres.get(genre, 0) + 1
                authors[author] = authors.get(author, 0) + 1
            
            # Сортируем
            top_genres = sorted(genres.items(), key=lambda x: x[1], reverse=True)[:3]
            top_authors = sorted(authors.items(), key=lambda x: x[1], reverse=True)[:3]
            
            response = f"{EMOJI['trophy']} <b>Статистика библиотеки</b>\n\n"
            response += f"<b>Всего книг:</b> {total_books}\n\n"
            
            response += f"<b>Топ жанров:</b>\n"
            for genre, count in top_genres:
                response += f"  {EMOJI['pencil']} {genre}: {count} книг\n"
            
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
        """Вернуться в меню."""
        keyboard = [
            [KeyboardButton(f"{EMOJI['search']} Поиск"), KeyboardButton(f"{EMOJI['list']} Все книги")],
            [KeyboardButton(f"{EMOJI['plus']} Добавить"), KeyboardButton(f"{EMOJI['trash']} Удалить")],
            [KeyboardButton(f"{EMOJI['info']} Статистика"), KeyboardButton(f"{EMOJI['help']} Помощь")]
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
        
        # Основной обработчик
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("start", self.start)],
            states={
                CHOOSING: [
                    MessageHandler(filters.Regex(f"^{EMOJI['search']} Поиск$"), self.search_books),
                    MessageHandler(filters.Regex(f"^{EMOJI['list']} Все книги$"), self.my_books),
                    MessageHandler(filters.Regex(f"^{EMOJI['plus']} Добавить$"), self.add_book),
                    MessageHandler(filters.Regex(f"^{EMOJI['trash']} Удалить$"), self.delete_book),
                    MessageHandler(filters.Regex(f"^{EMOJI['info']} Статистика$"), self.show_stats),
                    MessageHandler(filters.Regex(f"^{EMOJI['help']} Помощь$"), self.help_cmd),
                    CommandHandler("help", self.help_cmd),
                    CommandHandler("mybooks", self.my_books),
                    CommandHandler("stats", self.show_stats),
                ],
                TYPING_SEARCH: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_search),
                ],
                TYPING_BOOK_INFO: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_add_book),
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
    
    def run(self):
        """Запуск бота."""
        self.setup()
        print("=" * 50)
        print("🤖 BookBot запущен!")
        print("📱 Перейдите в Telegram и используйте /start")
        print("=" * 50)
        self.application.run_polling()


def main():
    """Главная функция."""
    parser = argparse.ArgumentParser(description="Telegram BookBot")
    parser.add_argument('--token', help='Токен бота')
    
    args = parser.parse_args()
    
    token = args.token or os.getenv('TELEGRAM_TOKEN')
    
    if not token:
        print("❌ Ошибка: Укажите токен бота")
        print("   python telegram_bot.py --token 'ВАШ_ТОКЕН'")
        print("   или set TELEGRAM_TOKEN='ВАШ_ТОКЕН'")
        sys.exit(1)
    
    bot = BookBot(token)
    bot.run()
def run(self):
    """Запуск бота."""
    self.setup()
    print("=" * 50)
    print("🤖 BookBot запущен!")
    print(f"📱 Имя бота: @{(await self.application.bot.get_me()).username}")
    print("📱 Перейдите в Telegram и используйте /start")
    print("=" * 50)
    
    # Обработка ошибок
    try:
        await self.application.run_polling()
    except Exception as e:
        self.logger.error(f"Ошибка запуска бота: {e}")
        print(f"❌ Критическая ошибка: {e}")

if __name__ == "__main__":
    main()
