# -*- coding: utf-8 -*-
"""Основной модуль Telegram бота с поддержкой файлов."""

import logging
import argparse
import sys
import os
import tempfile
from pathlib import Path

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

from database import DatabaseManager

# Словарь эмодзи
EMOJI = {
    "search": "🔍", "star": "⭐", "plus": "➕",
    "list": "📋", "help": "❓", "home": "🏠", 
    "book": "📚", "trash": "🗑️", "read": "📖",
    "bookmark": "🔖", "prev": "⬅️", "next": "➡️", 
    "info": "ℹ️", "file": "📄", "text": "📝",
    "download": "📥", "upload": "📤"
}

# Состояния диалога
(
    CHOOSING, TYPING_SEARCH, TYPING_BOOK_INFO, 
    CONFIRM_DELETE, TYPING_BOOK_ID, READING,
    TYPING_BOOK_DETAILS, UPLOADING_FILE, PROCESSING_FILE
) = range(9)

class BookBot:
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
        
        # Создаем папку для файлов
        self.books_folder = Path("books_files")
        self.books_folder.mkdir(exist_ok=True)
        
        # Настройка логирования
        logging.basicConfig(
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            level=logging.WARNING
        )
        self.logger = logging.getLogger(__name__)
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /start."""
        try:
            user = update.effective_user
            print(f"[START] от {user.id}")
            
            await update.message.reply_text(
                "📚 Привет! Я BookBot - ваш персональный библиотекарь.\n"
                "Теперь вы можете загружать книги файлами!",
                parse_mode=ParseMode.HTML
            )
            
            keyboard = [
                [KeyboardButton(f"{EMOJI['search']} Поиск"), KeyboardButton(f"{EMOJI['list']} Все книги")],
                [KeyboardButton(f"{EMOJI['plus']} Добавить книгу"), KeyboardButton(f"{EMOJI['read']} Читать")],
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
                await update.message.reply_text("Ошибка. Попробуйте /start снова.")
            except:
                pass
            return CHOOSING
    
    async def help_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /help."""
        try:
            help_text = """<b>BookBot - помощь</b>

<b>Основные команды:</b>
/start - Главное меню
/search - Поиск книг
/add - Добавить книгу
/mybooks - Все книги
/delete - Удалить книгу
/read - Читать книги
/stats - Статистика

<b>Как добавить книгу:</b>
1. Нажмите "➕ Добавить книгу"
2. Выберите тип:
   • <b>1</b> - Книга для учета (без текста)
   • <b>2</b> - Книга с текстом
   • <b>3</b> - Загрузить файл книги

<b>Поддерживаемые форматы файлов:</b>
• 📄 TXT - текстовые файлы
• 📖 EPUB - электронные книги
• 📕 FB2 - FictionBook
• 📘 MOBI - Kindle
• 📙 PDF - PDF документы

<b>Формат добавления вручную:</b>
Название | Автор | Жанр
или
Название | Автор | Жанр | Текст книги

<b>Пример:</b>
<code>Война и мир | Толстой | Роман</code>"""
            
            await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)
            return CHOOSING
        except Exception as e:
            print(f"[HELP ERROR] {e}")
            return CHOOSING
    
    async def add_book(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начать добавление книги."""
        try:
            await update.message.reply_text(
                f"{EMOJI['plus']} <b>Выберите тип добавления:</b>\n\n"
                "1. 📝 Книга для учета (без текста)\n"
                "2. 📖 Книга с текстом (ввести текст)\n"
                "3. 📄 Загрузить файл книги (TXT, EPUB, FB2, PDF)\n\n"
                "<b>Введите 1, 2 или 3:</b>",
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
                    f"{EMOJI['plus']} <b>Введите информацию о книге:</b>\n\n"
                    "<code>Название | Автор | Жанр</code>\n\n"
                    "<i>Пример:</i>\n"
                    "<code>Война и мир | Толстой | Роман</code>",
                    parse_mode=ParseMode.HTML
                )
                context.user_data['add_type'] = 'simple'
                return TYPING_BOOK_DETAILS
            
            elif text == "2":
                await update.message.reply_text(
                    f"{EMOJI['plus']} <b>Введите информацию о книге с текстом:</b>\n\n"
                    "<code>Название | Автор | Жанр | Текст книги</code>\n\n"
                    "<i>Пример:</i>\n"
                    "<code>Гарри Поттер | Роулинг | Фэнтези | Текст первой главы...</code>",
                    parse_mode=ParseMode.HTML
                )
                context.user_data['add_type'] = 'with_content'
                return TYPING_BOOK_DETAILS
            
            elif text == "3":
                await update.message.reply_text(
                    f"{EMOJI['upload']} <b>Загрузите файл книги</b>\n\n"
                    "Поддерживаемые форматы:\n"
                    "• 📄 TXT - текстовые файлы\n"
                    "• 📖 EPUB - электронные книги\n"
                    "• 📕 FB2 - FictionBook\n"
                    "• 📘 MOBI - Kindle\n"
                    "• 📙 PDF - PDF документы\n\n"
                    "После загрузки файла введите информацию о книге:\n"
                    "<code>Название | Автор | Жанр</code>",
                    parse_mode=ParseMode.HTML
                )
                context.user_data['add_type'] = 'file'
                return UPLOADING_FILE
            
            else:
                await update.message.reply_text("❌ Введите 1, 2 или 3")
                return TYPING_BOOK_INFO
                
        except Exception as e:
            print(f"[HANDLE ADD TYPE ERROR] {e}")
            return CHOOSING
    
    async def handle_file_upload(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка загрузки файла."""
        try:
            if update.message.document:
                document = update.message.document
                file_name = document.file_name
                file_size = document.file_size
                
                # Проверяем размер файла (макс 20 MB)
                if file_size > 20 * 1024 * 1024:
                    await update.message.reply_text("❌ Файл слишком большой (макс 20 MB)")
                    return UPLOADING_FILE
                
                # Проверяем расширение файла
                allowed_extensions = ['.txt', '.epub', '.fb2', '.mobi', '.pdf', '.doc', '.docx', '.rtf']
                file_ext = Path(file_name).suffix.lower()
                
                if file_ext not in allowed_extensions:
                    await update.message.reply_text(
                        f"❌ Неподдерживаемый формат файла.\n"
                        f"Допустимые форматы: {', '.join(allowed_extensions)}"
                    )
                    return UPLOADING_FILE
                
                # Сохраняем информацию о файле
                context.user_data['uploaded_file'] = {
                    'file_id': document.file_id,
                    'file_name': file_name,
                    'file_size': file_size,
                    'file_ext': file_ext
                }
                
                await update.message.reply_text(
                    f"✅ Файл получен: <b>{file_name}</b>\n"
                    f"📊 Размер: {file_size / 1024:.1f} KB\n\n"
                    f"Теперь введите информацию о книге:\n"
                    f"<code>Название | Автор | Жанр</code>",
                    parse_mode=ParseMode.HTML
                )
                return PROCESSING_FILE
                
            else:
                await update.message.reply_text("❌ Пожалуйста, загрузите файл книги")
                return UPLOADING_FILE
                
        except Exception as e:
            print(f"[FILE UPLOAD ERROR] {e}")
            await update.message.reply_text("❌ Ошибка при загрузке файла")
            return UPLOADING_FILE
    
    async def process_file_book(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка информации о книге после загрузки файла."""
        try:
            text = update.message.text.strip()
            
            if "|" not in text or text.count("|") < 2:
                await update.message.reply_text(
                    "❌ Неверный формат. Используйте: Название | Автор | Жанр\n\n"
                    "<i>Пример:</i>\n<code>Война и мир | Толстой | Роман</code>",
                    parse_mode=ParseMode.HTML
                )
                return PROCESSING_FILE
            
            parts = [x.strip() for x in text.split("|")]
            title, author, genre = parts[0], parts[1], parts[2]
            
            # Получаем информацию о файле
            file_info = context.user_data.get('uploaded_file')
            if not file_info:
                await update.message.reply_text("❌ Файл не найден. Начните заново.")
                return await self.back_to_menu(update, context)
            
            # Скачиваем файл
            file = await context.bot.get_file(file_info['file_id'])
            
            # Создаем уникальное имя файла
            file_path = self.books_folder / f"{title}_{author}_{file_info['file_name']}"
            
            # Скачиваем файл
            await file.download_to_drive(file_path)
            
            # Читаем содержимое файла (для TXT файлов)
            content = ""
            if file_info['file_ext'] == '.txt':
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read(50000)  # Читаем первые 50000 символов
                except:
                    try:
                        with open(file_path, 'r', encoding='cp1251') as f:
                            content = f.read(50000)
                    except:
                        content = f"[Файл {file_info['file_name']} загружен]"
            else:
                content = f"[Файл {file_info['file_name']} в формате {file_info['file_ext']}]"
            
            # Добавляем книгу в базу
            book_id = self.db.add_book_with_content(title, author, genre, content)
            
            # Сохраняем информацию о файле в базу
            self.db.save_book_file_info(book_id, str(file_path), file_info['file_ext'], file_info['file_size'])
            
            await update.message.reply_text(
                f"✅ Книга из файла добавлена!\n\n"
                f"📖 <b>{title}</b>\n"
                f"✍️ Автор: {author}\n"
                f"🏷️ Жанр: {genre}\n"
                f"📄 Файл: {file_info['file_name']}\n"
                f"📊 Формат: {file_info['file_ext']}\n"
                f"💾 Размер: {file_info['file_size'] / 1024:.1f} KB\n"
                f"🆔 ID: {book_id}",
                parse_mode=ParseMode.HTML
            )
            
            # Очищаем данные
            if 'uploaded_file' in context.user_data:
                del context.user_data['uploaded_file']
            if 'add_type' in context.user_data:
                del context.user_data['add_type']
            
            await self.back_to_menu(update, context)
            return CHOOSING
            
        except Exception as e:
            print(f"[PROCESS FILE ERROR] {e}")
            await update.message.reply_text("❌ Ошибка при обработке файла")
            return PROCESSING_FILE
    
    async def handle_add_book_details(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка деталей книги (для типов 1 и 2)."""
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
                
                book_id = self.db.add_book(title, author, genre)
                await update.message.reply_text(
                    f"✅ Книга добавлена! ID: {book_id}\n"
                    f"📖 Название: {title}\n"
                    f"✍️ Автор: {author}\n"
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
                
                book_id = self.db.add_book_with_content(title, author, genre, content)
                pages = (len(content) // 2000) + 1
                
                await update.message.reply_text(
                    f"✅ Книга с текстом добавлена!\n"
                    f"📖 Название: {title}\n"
                    f"✍️ Автор: {author}\n"
                    f"🏷️ Жанр: {genre}\n"
                    f"📄 Страниц: {pages}\n"
                    f"🆔 ID: {book_id}"
                )
            
            # Очищаем данные и возвращаем в меню
            if 'add_type' in context.user_data:
                del context.user_data['add_type']
            
            await self.back_to_menu(update, context)
            return CHOOSING
            
        except Exception as e:
            print(f"[ADD DETAILS ERROR] {e}")
            await update.message.reply_text("❌ Ошибка добавления")
            return CHOOSING
    
    async def my_books(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать все книги."""
        try:
            books = self.db.get_all_books()
            books_with_content = self.db.get_books_with_content()
            books_with_files = self.db.get_books_with_files()
            
            if not books and not books_with_content and not books_with_files:
                await update.message.reply_text("📭 Библиотека пуста. Добавьте первую книгу!")
                return
            
            response = "<b>📚 Ваша библиотека</b>\n\n"
            
            if books:
                response += f"<b>📝 Книги для учета ({len(books)}):</b>\n"
                for i, book in enumerate(books[:5], 1):
                    response += f"{i}. {book['title']} - {book['author']} (ID: {book['id']})\n"
                if len(books) > 5:
                    response += f"... и еще {len(books) - 5}\n"
                response += "\n"
            
            if books_with_content:
                response += f"<b>📖 Книги с текстом ({len(books_with_content)}):</b>\n"
                for i, book in enumerate(books_with_content[:5], 1):
                    content_len = len(book.get('content', ''))
                    pages = (content_len // 2000) + 1 if content_len > 0 else 0
                    response += f"{i}. {book['title']} - {book['author']} (ID: {book['id']}, {pages} стр.)\n"
                if len(books_with_content) > 5:
                    response += f"... и еще {len(books_with_content) - 5}\n"
                response += "\n"
            
            if books_with_files:
                response += f"<b>📄 Книги из файлов ({len(books_with_files)}):</b>\n"
                for i, book in enumerate(books_with_files[:5], 1):
                    file_ext = book.get('file_ext', '?')
                    file_size = book.get('file_size', 0)
                    size_kb = file_size / 1024 if file_size else 0
                    response += f"{i}. {book['title']} - {book['author']} (ID: {book['id']}, {file_ext}, {size_kb:.1f} KB)\n"
                if len(books_with_files) > 5:
                    response += f"... и еще {len(books_with_files) - 5}\n"
            
            response += f"\nДля чтения используйте {EMOJI['read']} Читать"
            
            await update.message.reply_text(response, parse_mode=ParseMode.HTML)
            
        except Exception as e:
            print(f"[MYBOOKS ERROR] {e}")
            await update.message.reply_text("❌ Ошибка получения списка")
    
    async def download_book_file(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Скачать файл книги."""
        try:
            if len(context.args) < 1:
                await update.message.reply_text("❌ Укажите ID книги: /download <id>")
                return
            
            book_id = int(context.args[0])
            book_info = self.db.get_book_file_info(book_id)
            
            if not book_info or not book_info.get('file_path'):
                await update.message.reply_text(f"❌ У книги ID {book_id} нет файла для скачивания")
                return
            
            file_path = Path(book_info['file_path'])
            if not file_path.exists():
                await update.message.reply_text(f"❌ Файл книги не найден на сервере")
                return
            
            # Отправляем файл пользователю
            with open(file_path, 'rb') as file:
                await update.message.reply_document(
                    document=file,
                    filename=f"{book_info['title']}_{book_info['author']}{book_info['file_ext']}",
                    caption=f"📥 <b>{book_info['title']}</b>\n✍️ {book_info['author']}"
                )
                
        except Exception as e:
            print(f"[DOWNLOAD ERROR] {e}")
            await update.message.reply_text("❌ Ошибка при скачивании файла")
    
    # ... остальные методы остаются такими же (read_book_menu, handle_read_book, и т.д.)
    # Просто добавьте обработчики для скачивания
    
    def setup(self):
        """Настройка обработчиков."""
        self.application = Application.builder().token(self.token).build()
        
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("start", self.start)],
            states={
                CHOOSING: [
                    MessageHandler(filters.Regex(f"^{EMOJI['search']} Поиск$"), self.search_books),
                    MessageHandler(filters.Regex(f"^{EMOJI['list']} Все книги$"), self.my_books),
                    MessageHandler(filters.Regex(f"^{EMOJI['plus']} Добавить книгу$"), self.add_book),
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
                    CommandHandler("download", self.download_book_file),
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
                UPLOADING_FILE: [
                    MessageHandler(filters.Document.ALL, self.handle_file_upload),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_add_type),  # Назад к выбору типа
                ],
                PROCESSING_FILE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.process_file_book),
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
        )
        
        self.application.add_handler(conv_handler)
    
    def run(self):
        """Запуск бота."""
        self.setup()
        
        self.application.run_polling(
            drop_pending_updates=True,
            allowed_updates=['message', 'callback_query', 'document']
        )


def main():
    parser = argparse.ArgumentParser(description="BookBot с поддержкой файлов")
    parser.add_argument('--token', help='Токен бота', required=True)
    
    args = parser.parse_args()
    token = args.token
    
    bot = BookBot(token)
    bot.run()


if __name__ == "__main__":
    main()
