import telebot
from telebot import types
from config import TOKEN, MAIN_ADMIN, ADMINS, DATABASE_CONFIG, MESSAGES
import handler
import registr
from database import DatabaseManager
import sys
import time

bot = telebot.TeleBot(TOKEN)
db = None

@bot.message_handler(commands=['start'])
def start_handler(message):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    if user_id in ADMINS:
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("📋 Зарегистрироваться на фестиваль", callback_data="btn_new_part"))
        keyboard.add(types.InlineKeyboardButton("🔍 Поиск участников", callback_data="btn_search_part"))
        keyboard.add(types.InlineKeyboardButton("👤 Личный кабинет", callback_data="personal_cabinet"))
        keyboard.add(types.InlineKeyboardButton("📈 Статистика", callback_data="statistics"))
        keyboard.add(types.InlineKeyboardButton("📊 Скачать данные", callback_data="download_data"))
        keyboard.add(types.InlineKeyboardButton("💬 Ответить на вопрос", callback_data="answer_quest"))
        keyboard.add(types.InlineKeyboardButton("📊 Скачать базу вопросов", callback_data="download_data_ask"))
        keyboard.add(types.InlineKeyboardButton("💬 Написать личное сообщение", callback_data="send_message"))
        keyboard.add(types.InlineKeyboardButton("📢 Рассылка", callback_data="mailing"))
        keyboard.add(types.InlineKeyboardButton("🚗 Как добраться", callback_data="how_get"))
        keyboard.add(types.InlineKeyboardButton("✨ Программа", callback_data="program"))
        bot.send_message(
            message.chat.id, 
            f"Привет, {message.from_user.first_name}! {MESSAGES['welcome_admin']}", 
            reply_markup=keyboard
        )
    else:
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("📋 Зарегистрироваться на фестиваль", callback_data="btn_new_part"))
        keyboard.add(types.InlineKeyboardButton("👤 Личный кабинет", callback_data="personal_cabinet"))
        keyboard.add(types.InlineKeyboardButton("❓ Задать вопрос", callback_data="ask_quest"))
        keyboard.add(types.InlineKeyboardButton("🚗 Как добраться", callback_data="how_get"))
        keyboard.add(types.InlineKeyboardButton("🌐 Официальный сайт", callback_data="web_cite"))
        keyboard.add(types.InlineKeyboardButton("✨ Программа", callback_data="program"))
        bot.send_message(
            message.chat.id, 
            f"Привет, {message.from_user.first_name}! {MESSAGES['welcome_user']}", 
            reply_markup=keyboard
        )
@bot.callback_query_handler(func=lambda call: call.data == "callback_start")
def start_handler_callback(call):
    """Обработчик команды /start"""
    bot.clear_step_handler_by_chat_id(call.message.chat.id)
    user_id = call.from_user.id
    if user_id in ADMINS:
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("📋 Зарегистрироваться на фестиваль", callback_data="btn_new_part"))
        keyboard.add(types.InlineKeyboardButton("🔍 Поиск участников", callback_data="btn_search_part"))
        keyboard.add(types.InlineKeyboardButton("👤 Личный кабинет", callback_data="personal_cabinet"))
        keyboard.add(types.InlineKeyboardButton("📈 Статистика", callback_data="statistics"))
        keyboard.add(types.InlineKeyboardButton("📊 Скачать данные", callback_data="download_data"))
        keyboard.add(types.InlineKeyboardButton("💬 Ответить на вопрос", callback_data="answer_quest"))
        keyboard.add(types.InlineKeyboardButton("📊 Скачать базу вопросов", callback_data="download_data_ask"))
        keyboard.add(types.InlineKeyboardButton("💬 Написать личное сообщение", callback_data="send_message"))
        keyboard.add(types.InlineKeyboardButton("📢 Рассылка", callback_data="mailing"))
        keyboard.add(types.InlineKeyboardButton("🚗 Как добраться", callback_data="how_get"))
        keyboard.add(types.InlineKeyboardButton("✨ Программа", callback_data="program"))

        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text = MESSAGES['welcome_admin2'], 
            reply_markup=keyboard
        )
    else:
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("📋 Зарегистрироваться на фестиваль", callback_data="btn_new_part"))
        keyboard.add(types.InlineKeyboardButton("👤 Личный кабинет", callback_data="personal_cabinet"))
        keyboard.add(types.InlineKeyboardButton("❓ Задать вопрос", callback_data="ask_quest"))
        keyboard.add(types.InlineKeyboardButton("🚗 Как добраться", callback_data="how_get"))
        keyboard.add(types.InlineKeyboardButton("🌐 Официальный сайт", callback_data="web_cite"))
        keyboard.add(types.InlineKeyboardButton("✨ Программа", callback_data="program"))
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text = MESSAGES['welcome_user2'], 
            reply_markup=keyboard
        )
@bot.callback_query_handler(func=lambda call: call.data == "callback_start2")
def start_handler_callback2(call):
    """Обработчик команды /start"""
    bot.clear_step_handler_by_chat_id(call.message.chat.id)
    from handler import clear_chat_history_optimized
    clear_chat_history_optimized(call.message, 2)
    user_id = call.from_user.id
    if user_id in ADMINS:
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("📋 Зарегистрироваться на фестиваль", callback_data="btn_new_part"))
        keyboard.add(types.InlineKeyboardButton("🔍 Поиск участников", callback_data="btn_search_part"))
        keyboard.add(types.InlineKeyboardButton("👤 Личный кабинет", callback_data="personal_cabinet"))
        keyboard.add(types.InlineKeyboardButton("📈 Статистика", callback_data="statistics"))
        keyboard.add(types.InlineKeyboardButton("📊 Скачать данные", callback_data="download_data"))
        keyboard.add(types.InlineKeyboardButton("💬 Ответить на вопрос", callback_data="answer_quest"))
        keyboard.add(types.InlineKeyboardButton("📊 Скачать базу вопросов", callback_data="download_data_ask"))
        keyboard.add(types.InlineKeyboardButton("💬 Написать личное сообщение", callback_data="send_message"))
        keyboard.add(types.InlineKeyboardButton("📢 Рассылка", callback_data="mailing"))
        keyboard.add(types.InlineKeyboardButton("🚗 Как добраться", callback_data="how_get"))
        keyboard.add(types.InlineKeyboardButton("✨ Программа", callback_data="program"))

        bot.send_message(
            chat_id=call.message.chat.id,
            text = MESSAGES['welcome_admin2'], 
            reply_markup=keyboard
        )
    else:
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("📋 Зарегистрироваться на фестиваль", callback_data="btn_new_part"))
        keyboard.add(types.InlineKeyboardButton("👤 Личный кабинет", callback_data="personal_cabinet"))
        keyboard.add(types.InlineKeyboardButton("❓ Задать вопрос", callback_data="ask_quest"))
        keyboard.add(types.InlineKeyboardButton("🚗 Как добраться", callback_data="how_get"))
        keyboard.add(types.InlineKeyboardButton("🌐 Официальный сайт", callback_data="web_cite"))
        keyboard.add(types.InlineKeyboardButton("✨ Программа", callback_data="program"))
        bot.send_message(
            chat_id=call.message.chat.id,
            text = MESSAGES['welcome_admin2'], 
            reply_markup=keyboard
        )
def init_database():
    """Инициализация базы данных"""
    global db
    try:
        # Создаем копию конфига и убираем параметры, не поддерживаемые пулом
        db_config = {
            'host': DATABASE_CONFIG['host'],
            'database': DATABASE_CONFIG['database'], 
            'user': DATABASE_CONFIG['user'],
            'password': DATABASE_CONFIG['password'],
            'port': DATABASE_CONFIG['port']
        }
        
        db = DatabaseManager(**db_config)
        print("✅ База данных успешно инициализирована")
        return True
    except Exception as e:
        print(f"❌ Ошибка инициализации базы данных: {e}")
        return False
    
def main():
    """Основная функция запуска бота"""
    global db
    
    print("🤖 Инициализация бота...")
    
    # Инициализация базы данных
    print("💾 Подключение к базе данных...")
    if not init_database():
        print("❌ Не удалось подключиться к базе данных. Завершение работы.")
        sys.exit(1)

    # Инициализация модуля регистрации
    print("📋 Инициализация модуля регистрации...")
    registr.init_bot(bot, db)
    
    # Инициализация обработчиков с передачей объекта базы данных
    print("⚙️ Инициализация обработчиков...")
    handler.init_main_menu(bot, registr, db)
    handler.register_main_menu_handlers(bot)
    
    print("✅ Бот успешно инициализирован")
    print(f"👥 Администраторы: {ADMINS}")
    print(f"🗄️ База данных: {DATABASE_CONFIG['database']} на {DATABASE_CONFIG['host']}")
    print("🚀 Запуск бота...")
    while True:
        # Запуск бота
        try:
            bot.infinity_polling(
                timeout=60, 
                long_polling_timeout=60,
                skip_pending=True,
                none_stop=True
            )
        except KeyboardInterrupt:
            print("\n🛑 Получен сигнал остановки")
        except Exception as e:
            print(f"❌ Ошибка polling: {e}")
            time.sleep(5)  # Ждем 5 секунд перед перезапуском
            continue
        finally:
            # Закрываем соединение с базой данных
            if db:
                db.close_connection()
            print("👋 Завершение работы бота")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен пользователем")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("👋 Завершение работы бота")