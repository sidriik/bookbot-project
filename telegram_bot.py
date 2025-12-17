# -*- coding: utf-8 -*-
"""Основной модуль Telegram бота с поддержкой файлов."""

import logging
import argparse
import sys
import os
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
/download <id> - Скачать файл книги

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
    
    # ========== ПОИСК ==========
    
    async def search_books(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начать поиск книг."""
        try:
            await update.message.reply_text(f"{EMOJI['search']} Введите запрос для поиска:")
            return TYPING_SEARCH
        except Exception as e:
            print(f"[SEARCH ERROR] {e}")
            return CHOOSING
    
    async def handle_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка поиска книг."""
        try:
            query = update.message.text.strip()
            if not query:
                await update.message.reply_text("Введите текст для поиска")
                return TYPING_SEARCH
            
            results = self.db.search_books(query)
            
            if not results:
                await update.message.reply_text(f"По запросу '{query}' ничего не найдено.")
                return CHOOSING
            
            response = f"🔍 Найдено книг: {len(results)}\n\n"
            for book in results[:5]:
                response += f"<b>{book['title']}</b>\n"
                response += f"Автор: {book['author']}\n"
                response += f"Жанр: {book.get('genre', 'не указан')}\n"
                response += f"ID: {book['id']}\n\n"
            
            await update.message.reply_text(response, parse_mode=ParseMode.HTML)
            return CHOOSING
            
        except Exception as e:
            print(f"[HANDLE SEARCH ERROR] {e}")
            await update.message.reply_text("Ошибка поиска")
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
            self.db.save_book_file_info(book_id, str(file_path), file_info['file_ext'], file_info['file_size'], file_info['file_name'])
            
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
            
            response += f"\nДля чтения используйте {EMOJI['read']} Читать\n"
            response += f"Для скачивания: /download ID_книги"
            
            await update.message.reply_text(response, parse_mode=ParseMode.HTML)
            
        except Exception as e:
            print(f"[MYBOOKS ERROR] {e}")
            await update.message.reply_text("❌ Ошибка получения списка")
    
    # ========== ЧТЕНИЕ КНИГ ==========
    
    async def read_book_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Меню выбора книги для чтения."""
        try:
            books_with_content = self.db.get_books_with_content()
            books_with_files = self.db.get_books_with_files()
            
            # Объединяем книги с текстом и из файлов
            all_books = books_with_content + books_with_files
            
            if not all_books:
                await update.message.reply_text("📭 Нет книг для чтения. Добавьте книгу с текстом или файлом!")
                return CHOOSING
            
            response = "<b>📖 Доступные книги для чтения:</b>\n\n"
            for book in all_books[:10]:
                content_len = len(book.get('content', ''))
                pages = (content_len // 2000) + 1 if content_len > 0 else 0
                file_ext = book.get('file_ext', '')
                
                response += f"ID {book['id']}: {book['title']}\n"
                response += f"   Автор: {book['author']} | Жанр: {book.get('genre', '')}"
                if file_ext:
                    response += f" | Файл: {file_ext}"
                response += f" | Страниц: {pages}\n\n"
            
            if len(all_books) > 10:
                response += f"\n📄 Показано 10 из {len(all_books)} книг"
            
            response += "\n<b>Введите ID книги для чтения:</b>"
            
            await update.message.reply_text(response, parse_mode=ParseMode.HTML)
            return TYPING_BOOK_ID
            
        except Exception as e:
            print(f"[READ MENU ERROR] {e}")
            await update.message.reply_text("❌ Ошибка загрузки списка книг")
            return CHOOSING
    
    async def handle_read_book(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка начала чтения книги."""
        try:
            user_input = update.message.text.strip()
            
            try:
                book_id = int(user_input)
            except ValueError:
                await update.message.reply_text("❌ Введите числовой ID книги")
                return TYPING_BOOK_ID
            
            # Получаем страницу книги
            book_page = self.db.get_book_content(book_id, 1)
            
            if not book_page:
                await update.message.reply_text(
                    f"❌ Книга с ID {book_id} не найдена или не содержит текста.\n"
                    f"Проверьте ID и попробуйте снова."
                )
                return CHOOSING
            
            # Сохраняем данные в контексте
            context.user_data['current_book_id'] = book_id
            context.user_data['current_page'] = 1
            
            await self.show_book_page(update, context, book_page)
            return READING
            
        except Exception as e:
            print(f"[READ ERROR] {e}")
            await update.message.reply_text("❌ Ошибка начала чтения")
            return CHOOSING
    
    async def show_book_page(self, update: Update, context: ContextTypes.DEFAULT_TYPE, book_page: dict):
        """Показать страницу книги."""
        current_page = context.user_data.get('current_page', 1)
        book_id = context.user_data.get('current_book_id')
        
        # Создаем клавиатуру для навигации
        keyboard = []
        
        nav_buttons = []
        if current_page > 1:
            nav_buttons.append(KeyboardButton("⬅️ Назад"))
        
        nav_buttons.append(KeyboardButton("🔖 Сохранить"))
        
        if current_page < book_page['total_pages']:
            nav_buttons.append(KeyboardButton("➡️ Вперед"))
        
        if nav_buttons:
            keyboard.append(nav_buttons)
        
        keyboard.append([KeyboardButton("🏠 В меню")])
        
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        # Форматируем страницу
        response = f"<b>{book_page['title']}</b>\n"
        response += f"✍️ Автор: {book_page['author']}\n"
        response += f"🏷️ Жанр: {book_page['genre']}\n"
        response += f"📄 Страница {current_page}/{book_page['total_pages']}\n"
        
        # Если есть файл, показываем информацию
        if book_page.get('has_file'):
            file_ext = book_page.get('file_ext', '')
            file_size = book_page.get('file_size', 0)
            size_mb = file_size / (1024 * 1024) if file_size else 0
            response += f"📁 Файл: {file_ext} ({size_mb:.1f} MB)\n"
        
        response += "\n"
        
        # Добавляем текст (ограничиваем длину)
        text_content = book_page['content']
        if len(text_content) > 1500:
            text_content = text_content[:1500] + "..."
        
        # Безопасное отображение
        text_content = text_content.replace('<', '&lt;').replace('>', '&gt;')
        
        response += f"<pre>{text_content}</pre>\n\n"
        response += "Используйте кнопки для навигации"
        
        await update.message.reply_text(response, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
    
    async def handle_reading_navigation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка навигации при чтении."""
        try:
            user_id = update.effective_user.id
            command = update.message.text
            
            book_id = context.user_data.get('current_book_id')
            current_page = context.user_data.get('current_page', 1)
            
            if not book_id:
                await update.message.reply_text("❌ Сессия потеряна. Начните заново.")
                return await self.back_to_menu(update, context)
            
            # Обработка команды "В меню"
            if command == "🏠 В меню":
                context.user_data.clear()
                await self.back_to_menu(update, context)
                return CHOOSING
            
            # Обработка других команд
            new_page = current_page
            
            if command == "⬅️ Назад" and current_page > 1:
                new_page = current_page - 1
            elif command == "➡️ Вперед":
                new_page = current_page + 1
            elif command == "🔖 Сохранить":
                self.db.save_reading_progress(user_id, book_id, current_page)
                await update.message.reply_text(f"✅ Прогресс сохранен! Страница {current_page}")
            
            # Если страница изменилась
            if new_page != current_page:
                book_page = self.db.get_book_content(book_id, new_page)
                
                if not book_page:
                    await update.message.reply_text("❌ Страница не найдена")
                    return READING
                
                current_page = new_page
                context.user_data['current_page'] = current_page
            
            # Получаем страницу для отображения
            book_page = self.db.get_book_content(book_id, current_page)
            await self.show_book_page(update, context, book_page)
            return READING
            
        except Exception as e:
            print(f"[NAV ERROR] {e}")
            await update.message.reply_text("❌ Ошибка навигации")
            return CHOOSING
    
    # ========== УДАЛЕНИЕ ==========
    
    async def delete_book(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начать удаление книги."""
        try:
            books = self.db.get_all_books()
            books_with_content = self.db.get_books_with_content()
            books_with_files = self.db.get_books_with_files()
            
            all_books = books + books_with_content + books_with_files
            
            if not all_books:
                await update.message.reply_text("📭 Нет книг для удаления")
                return CHOOSING
            
            response = "<b>🗑️ Выберите ID книги для удаления:</b>\n\n"
            
            # Группируем книги по типам
            for i, book in enumerate(all_books[:10], 1):
                book_type = "📝" if book.get('content') is None else "📖"
                if book.get('file_ext'):
                    book_type = "📄"
                
                response += f"{i}. {book_type} ID {book['id']}: {book['title'][:30]}...\n"
            
            response += "\n<b>Введите ID книги:</b>"
            await update.message.reply_text(response, parse_mode=ParseMode.HTML)
            return CONFIRM_DELETE
            
        except Exception as e:
            print(f"[DELETE ERROR] {e}")
            await update.message.reply_text("❌ Ошибка загрузки списка книг")
            return CHOOSING
    
    async def confirm_delete(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Подтверждение удаления книги."""
        try:
            book_id = int(update.message.text.strip())
            success = self.db.delete_book(book_id)
            
            if success:
                await update.message.reply_text("✅ Книга удалена!")
            else:
                await update.message.reply_text("❌ Книга не найдена")
            
            await self.back_to_menu(update, context)
            return CHOOSING
            
        except ValueError:
            await update.message.reply_text("❌ Введите числовой ID")
            return CONFIRM_DELETE
        except Exception as e:
            print(f"[CONFIRM DELETE ERROR] {e}")
            await update.message.reply_text("❌ Ошибка при удалении")
            return CHOOSING
    
    # ========== СТАТИСТИКА ==========
    
    async def show_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать статистику библиотеки."""
        try:
            books = self.db.get_all_books()
            books_with_content = self.db.get_books_with_content()
            books_with_files = self.db.get_books_with_files()
            
            total_books = len(books) + len(books_with_content) + len(books_with_files)
            
            # Подсчитываем общий размер файлов
            total_size = 0
            for book in books_with_files:
                total_size += book.get('file_size', 0)
            total_size_mb = total_size / (1024 * 1024)
            
            response = f"<b>📊 Статистика библиотеки</b>\n\n"
            response += f"📚 Всего книг: {total_books}\n"
            response += f"  📝 Для учета: {len(books)}\n"
            response += f"  📖 С текстом: {len(books_with_content)}\n"
            response += f"  📄 Из файлов: {len(books_with_files)}\n"
            
            if total_size > 0:
                response += f"\n💾 Общий размер файлов: {total_size_mb:.1f} MB"
            
            await update.message.reply_text(response, parse_mode=ParseMode.HTML)
            
        except Exception as e:
            print(f"[STATS ERROR] {e}")
            await update.message.reply_text("❌ Ошибка загрузки статистики")
    
    # ========== СКАЧИВАНИЕ ФАЙЛА ==========
    
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
                    filename=f"{book_info['title']}_{book_info['author']}{book_info.get('file_ext', '')}",
                    caption=f"📥 <b>{book_info['title']}</b>\n✍️ {book_info['author']}",
                    parse_mode=ParseMode.HTML
                )
                
        except ValueError:
            await update.message.reply_text("❌ Введите числовой ID книги")
        except Exception as e:
            print(f"[DOWNLOAD ERROR] {e}")
            await update.message.reply_text("❌ Ошибка при скачивании файла")
    
    # ========== ВСПОМОГАТЕЛЬНЫЕ ==========
    
    async def back_to_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Вернуться в главное меню."""
        try:
            keyboard = [
                [KeyboardButton(f"{EMOJI['search']} Поиск"), KeyboardButton(f"{EMOJI['list']} Все книги")],
                [KeyboardButton(f"{EMOJI['plus']} Добавить книгу"), KeyboardButton(f"{EMOJI['read']} Читать")],
                [KeyboardButton(f"{EMOJI['trash']} Удалить"), KeyboardButton(f"{EMOJI['info']} Статистика")],
                [KeyboardButton(f"{EMOJI['help']} Помощь")]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            
            await update.message.reply_text(
                "🏠 Главное меню\n\nВыберите действие:",
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup
            )
            return CHOOSING
        except Exception as e:
            print(f"[BACK TO MENU ERROR] {e}")
            return CHOOSING
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отменить действие."""
        await update.message.reply_text("❌ Действие отменено")
        await self.back_to_menu(update, context)
        return CHOOSING
    
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
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_add_type),
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
