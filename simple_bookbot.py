#!/usr/bin/env python3
"""Упрощенная версия BookBot."""

import logging
import asyncio
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode
import telegram

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

TOKEN = "8039724055:AAHDEJs6rUxsgN8l2fJphLDAsQfq8FVZTLI"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /start."""
    try:
        user = update.effective_user
        print(f"✅ /start от {user.id} (@{user.username})")
        
        welcome_text = """
📚 <b>Привет! Я BookBot</b>

Я помогу вам управлять вашей библиотекой книг.

<b>Доступные команды:</b>
/help - Помощь
/mybooks - Мои книги
/search - Поиск книг
/add - Добавить книгу
/read - Читать книги
/stats - Статистика
"""
        
        keyboard = [
            [KeyboardButton("📚 Мои книги"), KeyboardButton("🔍 Поиск")],
            [KeyboardButton("➕ Добавить"), KeyboardButton("📖 Читать")],
            [KeyboardButton("📊 Статистика"), KeyboardButton("❓ Помощь")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            welcome_text,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )
        
    except Exception as e:
        print(f"❌ Ошибка в start: {e}")
        await update.message.reply_text("Произошла ошибка. Попробуйте еще раз.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /help."""
    help_text = """
❓ <b>Помощь по командам</b>

<b>Основные команды:</b>
/start - Главное меню
/help - Эта справка
/mybooks - Показать все книги
/search - Поиск книг
/add - Добавить книгу
/read - Читать книги
/stats - Статистика библиотеки

<b>Простой тест:</b>
Отправьте любое сообщение, и я его повторю.
"""
    await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Эхо-ответ для тестирования."""
    await update.message.reply_text(f"Вы сказали: {update.message.text}")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок."""
    print(f" Ошибка: {context.error}")
    
    try:
        if update and hasattr(update, 'effective_chat'):
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="⚠️ Произошла ошибка. Попробуйте еще раз."
            )
    except:
        pass

def main():
    """Запуск бота."""
    print(" Запуск упрощенного BookBot...")
    
    # Создаем приложение с увеличенными таймаутами
    application = (
        Application.builder()
        .token(TOKEN)
        .connect_timeout(60.0)
        .read_timeout(60.0)
        .write_timeout(60.0)
        .pool_timeout(60.0)
        .build()
    )
    
    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("mybooks", help_command))  # временно
    application.add_handler(CommandHandler("search", help_command))   # временно
    application.add_handler(CommandHandler("add", help_command))      # временно
    application.add_handler(CommandHandler("read", help_command))     # временно
    application.add_handler(CommandHandler("stats", help_command))    # временно
    
    # Эхо-обработчик для тестирования
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    
    # Добавляем обработчик ошибок
    application.add_error_handler(error_handler)
    
    print(" Бот запущен. Нажмите Ctrl+C для остановки.")
    print(" Теперь отправьте /start в Telegram")
    
    # Запускаем бота
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        poll_interval=1.0,
        timeout=30
    )

if __name__ == "__main__":
    main()
