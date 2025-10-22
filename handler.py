import telebot
from telebot import types
from telebot.apihelper import ApiException
import time
import io
import pandas as pd
from datetime import datetime
import queue
import threading
from time import sleep
from config import WEBSITE_URL
from psycopg2.extras import RealDictCursor
registr = None
bot = None
db = None 
user_temp_data = {}
admin_temp_data = {}
message_queue = queue.Queue()
last_message_time = {}
def init_main_menu(bot_instance, registr_module, db_instance):
    """Инициализация модуля главного меню с зависимостями"""
    global bot, registr, db
    bot = bot_instance
    registr = registr_module
    db = db_instance

def clear_chat_history_optimized(message, count):
    """Быстрое удаление последних N сообщений"""
    chat_id = message.chat.id
    current_message_id = message.message_id
    deleted_count = 0
    
    for message_id in range(current_message_id, max(1, current_message_id - count), -1):
        try:
            bot.delete_message(chat_id=chat_id, message_id=message_id)
            deleted_count += 1
        except ApiException as e:
            if "message to delete not found" in str(e).lower():
                continue
            elif "message can't be deleted" in str(e).lower():
                continue
            elif "too many requests" in str(e).lower():
                time.sleep(0.3)
                continue
        except Exception:
            continue
def register_main_menu_handlers(bot_instance):
    """Регистрация всех обработчиков"""
    global bot
    bot = bot_instance

    # ========== ПОИСК УЧАСТНИКОВ ==========
    @bot.callback_query_handler(func=lambda call: call.data == "btn_search_part")
    def callback_search_participants(call):
        bot.clear_step_handler_by_chat_id(call.message.chat.id)
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data="callback_start"))
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="🔍 Введите ФИО участника или номер телефона для поиска:",
            reply_markup=keyboard
        )
        
        bot.register_next_step_handler(call.message, search_participant_handler)

    def search_participant_handler(message):
        bot.delete_message(message.chat.id, message.message_id)
        clear_chat_history_optimized(message, 2)
        search_term = message.text.strip()
        
        participants = db.search_participants(search_term)
        
        keyboard = types.InlineKeyboardMarkup()
        
        if participants:
            text = f"🔍 Найдено участников: {len(participants)}\n\n"
            text += "Выберите участника для просмотра:"
            
            for participant in participants:
                keyboard.add(types.InlineKeyboardButton(
                    f"{participant['fio']}", 
                    callback_data=f"search_participant_{participant['id']}"
                ))
        else:
            text = "❌ Участники не найдены"
        
        keyboard.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data="callback_start"))
        
        safe_send_message(message.chat.id, text, reply_markup=keyboard)
    @bot.callback_query_handler(func=lambda call: call.data == "statistics")
    def callback_statistics(call):
        """Обработчик кнопки статистики"""
        stats = db.get_statistics()
        
        if not stats:
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data="callback_start"))
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="❌ Ошибка получения статистики",
                reply_markup=keyboard
            )
            return
        
        text = f"📈 Статистика фестиваля:\n\n"
        text += f"👥 Общее количество участников: {stats['total']}\n"
        text += f"📅 24 октября: {stats['oct_24']} человек\n"
        text += f"📅 25 октября: {stats['oct_25']} человек\n"
        
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("⏰ Детализация по времени", callback_data="stats_time"))
        keyboard.add(types.InlineKeyboardButton("🎂 Детализация по возрасту", callback_data="stats_age"))
        keyboard.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data="callback_start"))
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text,
            reply_markup=keyboard
        )
    @bot.callback_query_handler(func=lambda call: call.data == "download_data_ask")
    def callback_download_questions(call):
        try:
            # Получаем ВСЕ вопросы (не только неотвеченные)
            connection = db.get_connection()
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("SELECT * FROM questions ORDER BY created_at DESC;")
                questions = cursor.fetchall()
            db.put_connection(connection)
            
            if not questions:
                keyboard = types.InlineKeyboardMarkup()
                keyboard.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data="callback_start"))
                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text="📊 База вопросов пуста",
                    reply_markup=keyboard
                )
                return
            
            # Создаем DataFrame
            df = pd.DataFrame([dict(q) for q in questions])
            
            # Переименовываем колонки на русский
            column_mapping = {
                'id': 'ID',
                'telegram_id': 'ID Телеграмма',
                'username': 'Username',
                'full_name': 'ФИО',
                'question_text': 'Вопрос',
                'answer_text': 'Ответ',
                'is_answered': 'Отвечен',
                'created_at': 'Дата создания',
                'answered_at': 'Дата ответа'
            }
            df = df.rename(columns=column_mapping)
            
            # Создаем Excel файл в памяти
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Вопросы', index=False)
            
            output.seek(0)
            
            # Отправляем файл
            current_date = datetime.now().strftime("%Y-%m-%d_%H-%M")
            filename = f"questions_{current_date}.xlsx"
            clear_chat_history_optimized(call.message, 1)
            bot.send_document(
                call.message.chat.id,
                document=output,
                visible_file_name=filename,
                caption=f"📊 База вопросов\n💬 Всего вопросов: {len(questions)}"
            )
            
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data="callback_start"))
            safe_send_message(
                call.message.chat.id,
                "✅ Файл успешно создан и отправлен!",
                reply_markup=keyboard
            )
            
        except Exception as e:
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data="callback_start"))
            safe_send_message(
                call.message.chat.id,
                f"❌ Ошибка при создании файла: {str(e)}",
                reply_markup=keyboard
            )
    @bot.callback_query_handler(func=lambda call: call.data == "stats_time")
    def callback_statistics_time(call):
        """Обработчик детализации по времени"""
        time_stats = db.get_time_statistics()
        
        if not time_stats:
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(types.InlineKeyboardButton("⬅️ Назад к статистике", callback_data="statistics"))
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="❌ Ошибка получения статистики по времени",
                reply_markup=keyboard
            )
            return
        
        text = "⏰ Детализация по времени:\n\n"
        
        # 24 октября
        text += "📅 24 октября:\n"
        standard_times = ["12:00", "13:00", "14:00", "15:00", "16:00", "17:00", "18:00"]
        for time in standard_times:
            count = time_stats['oct_24'].get(time, 0)
            if count > 0:
                text += f"  {time} - {count} чел.\n"
        
        # Добавляем нестандартные времена для 24 октября
        for time, count in sorted(time_stats['oct_24'].items()):
            if time not in standard_times and count > 0:
                text += f"  {time} - {count} чел.\n"
        
        text += "\n"
        
        # 25 октября
        text += "📅 25 октября:\n"
        for time in standard_times:
            count = time_stats['oct_25'].get(time, 0)
            if count > 0:
                text += f"  {time} - {count} чел.\n"
        
        # Добавляем нестандартные времена для 25 октября
        for time, count in sorted(time_stats['oct_25'].items()):
            if time not in standard_times and count > 0:
                text += f"  {time} - {count} чел.\n"
        
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("⬅️ Назад к статистике", callback_data="statistics"))
        keyboard.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data="callback_start"))
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text,
            reply_markup=keyboard
        )

    @bot.callback_query_handler(func=lambda call: call.data == "stats_age")
    def callback_statistics_age(call):
        """Обработчик детализации по возрасту"""
        age_stats = db.get_age_statistics()
        
        if not age_stats:
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(types.InlineKeyboardButton("⬅️ Назад к статистике", callback_data="statistics"))
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="❌ Ошибка получения статистики по возрасту",
                reply_markup=keyboard
            )
            return
        
        text = "🎂 Детализация по возрасту:\n\n"
        
        for item in age_stats:
            age = item['age']
            count = item['count']
            # Правильное склонение слова "человек"
            if count % 10 == 1 and count % 100 != 11:
                word = "человек"
            elif count % 10 in [2, 3, 4] and count % 100 not in [12, 13, 14]:
                word = "человека"
            else:
                word = "человек"
            
            text += f"{age} лет: {count} {word}\n"
        
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("⬅️ Назад к статистике", callback_data="statistics"))
        keyboard.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data="callback_start"))
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text,
            reply_markup=keyboard
        )
    # ========== ЛИЧНЫЙ КАБИНЕТ ==========
    @bot.callback_query_handler(func=lambda call: call.data == "personal_cabinet")
    def callback_personal_cabinet(call):
        user_id = call.from_user.id
        participants = db.get_participants_by_registrator(user_id)
        
        keyboard = types.InlineKeyboardMarkup()
        
        if participants:
            text = f"👤 Ваши зарегистрированные участники ({len(participants)}):\n\n"
            text += "Выберите участника для просмотра:"
            
            for participant in participants:
                keyboard.add(types.InlineKeyboardButton(
                    f"{participant['fio']}", 
                    callback_data=f"participant_{participant['id']}"
                ))
        else:
            text = "📝 У вас нет зарегистрированных участников"
        keyboard.add(types.InlineKeyboardButton("📋 Зарегистрироваться на фестиваль", callback_data="btn_new_part"))
        keyboard.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data="callback_start"))
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text,
            reply_markup=keyboard
        )
    @bot.callback_query_handler(func=lambda call: call.data.startswith("search_participant_"))
    def callback_search_participant_info(call):
        participant_id = int(call.data.split("_")[2])
        participant = db.get_participant_by_id(participant_id)
        
        if not participant:
            bot.answer_callback_query(call.id, "❌ Участник не найден")
            return
        
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("✏️ Редактировать данные", callback_data=f"search_edit_{participant_id}"))
        keyboard.add(types.InlineKeyboardButton("⬅️ Назад к поиску", callback_data="btn_search_part"))
        
        text = f"📋 Информация об участнике:\n\n"
        text += f"👤 ФИО: {participant['fio']}\n"
        text += f"📅 Дата фестиваля: {participant['date_fest']}\n"
        text += f"🕐 Время: {participant['time_fest']}\n"
        text += f"👥 Пол: {participant['gender']}\n"
        text += f"🎂 Дата рождения: {participant['date_of_birth']}\n"
        text += f"🏷 Статус: {participant['status']}\n"
        text += f"🌍 Регион: {participant['region']}\n"
        text += f"🏠 Город: {participant['city']}\n"
        text += f"📞 Телефон: {participant['number']}\n"
        text += f"📋 ID участника: {participant['id']}\n"
        text += f"📅 Дата регистрации: {participant['created_at'].strftime('%d.%m.%Y %H:%M')}"
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text,
            reply_markup=keyboard
        )

    @bot.callback_query_handler(func=lambda call: call.data.startswith("search_edit_"))
    def callback_search_edit_participant(call):
        participant_id = int(call.data.split("_")[2])
        participant = db.get_participant_by_id(participant_id)
        
        if not participant:
            bot.answer_callback_query(call.id, "❌ Участник не найден")
            return
        
        # Сохраняем ID участника для редактирования
        admin_temp_data[call.from_user.id] = {'editing_participant_id': participant_id, 'from_search': True}
        
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("ФИО", callback_data="edit_field_fio"))
        keyboard.add(types.InlineKeyboardButton("Дата фестиваля", callback_data="edit_field_date_fest"))
        keyboard.add(types.InlineKeyboardButton("Время", callback_data="edit_field_time_fest"))
        keyboard.add(types.InlineKeyboardButton("Пол", callback_data="edit_field_gender"))
        keyboard.add(types.InlineKeyboardButton("Дата рождения", callback_data="edit_field_date_of_birth"))
        keyboard.add(types.InlineKeyboardButton("Статус", callback_data="edit_field_status"))
        keyboard.add(types.InlineKeyboardButton("Регион", callback_data="edit_field_region"))
        keyboard.add(types.InlineKeyboardButton("Город", callback_data="edit_field_city"))
        keyboard.add(types.InlineKeyboardButton("Телефон", callback_data="edit_field_number"))
        keyboard.add(types.InlineKeyboardButton("⬅️ Назад", callback_data=f"search_participant_{participant_id}"))
        
        text = f"📋 Информация об участнике:\n\n"
        text += f"👤 ФИО: {participant['fio']}\n"
        text += f"📅 Дата фестиваля: {participant['date_fest']}\n"
        text += f"🕐 Время: {participant['time_fest']}\n"
        text += f"👥 Пол: {participant['gender']}\n"
        text += f"🎂 Дата рождения: {participant['date_of_birth']}\n"
        text += f"🏷 Статус: {participant['status']}\n"
        text += f"🌍 Регион: {participant['region']}\n"
        text += f"🏠 Город: {participant['city']}\n"
        text += f"📞 Телефон: {participant['number']}\n\n"
        text += "✏️ Выберите поле для редактирования:"
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text,
            reply_markup=keyboard
        )
    @bot.callback_query_handler(func=lambda call: call.data.startswith("participant_"))
    def callback_participant_info(call):
        participant_id = int(call.data.split("_")[1])
        participant = db.get_participant_by_id(participant_id)
        
        if not participant:
            bot.answer_callback_query(call.id, "❌ Участник не найден")
            return
        
        # Проверяем, что пользователь является регистратором этого участника
        if participant['registrator_id'] != call.from_user.id:
            bot.answer_callback_query(call.id, "❌ Нет доступа к данному участнику")
            return
        
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("✏️ Редактировать данные", callback_data=f"edit_{participant_id}"))
        keyboard.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="personal_cabinet"))
        
        text = f"📋 Информация об участнике:\n\n"
        text += f"👤 ФИО: {participant['fio']}\n"
        text += f"📅 Дата фестиваля: {participant['date_fest']}\n"
        text += f"🕐 Время: {participant['time_fest']}\n"
        text += f"👥 Пол: {participant['gender']}\n"
        text += f"🎂 Дата рождения: {participant['date_of_birth']}\n"
        text += f"🏷 Статус: {participant['status']}\n"
        text += f"🌍 Регион: {participant['region']}\n"
        text += f"🏠 Город: {participant['city']}\n"
        text += f"📞 Телефон: {participant['number']}\n"
        text += f"📋 ID участника: {participant['id']}\n"
        text += f"📅 Дата регистрации: {participant['created_at'].strftime('%d.%m.%Y %H:%M')}"
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text,
            reply_markup=keyboard
        )

    @bot.callback_query_handler(func=lambda call: call.data.startswith("edit_") and not call.data.startswith("edit_field_"))
    def callback_edit_participant(call):
        participant_id = int(call.data.split("_")[1])
        participant = db.get_participant_by_id(participant_id)
        
        if not participant or participant['registrator_id'] != call.from_user.id:
            bot.answer_callback_query(call.id, "❌ Участник не найден")
            return
        
        # Сохраняем ID участника для редактирования
        admin_temp_data[call.from_user.id] = {'editing_participant_id': participant_id}
        
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("ФИО", callback_data="edit_field_fio"))
        keyboard.add(types.InlineKeyboardButton("Дата фестиваля", callback_data="edit_field_date_fest"))
        keyboard.add(types.InlineKeyboardButton("Время", callback_data="edit_field_time_fest"))
        keyboard.add(types.InlineKeyboardButton("Пол", callback_data="edit_field_gender"))
        keyboard.add(types.InlineKeyboardButton("Дата рождения", callback_data="edit_field_date_of_birth"))
        keyboard.add(types.InlineKeyboardButton("Статус", callback_data="edit_field_status"))
        keyboard.add(types.InlineKeyboardButton("Регион", callback_data="edit_field_region"))
        keyboard.add(types.InlineKeyboardButton("Город", callback_data="edit_field_city"))
        keyboard.add(types.InlineKeyboardButton("Телефон", callback_data="edit_field_number"))
        keyboard.add(types.InlineKeyboardButton("⬅️ Назад", callback_data=f"participant_{participant_id}"))
        
        text = f"📋 Информация об участнике:\n\n"
        text += f"👤 ФИО: {participant['fio']}\n"
        text += f"📅 Дата фестиваля: {participant['date_fest']}\n"
        text += f"🕐 Время: {participant['time_fest']}\n"
        text += f"👥 Пол: {participant['gender']}\n"
        text += f"🎂 Дата рождения: {participant['date_of_birth']}\n"
        text += f"🏷 Статус: {participant['status']}\n"
        text += f"🌍 Регион: {participant['region']}\n"
        text += f"🏠 Город: {participant['city']}\n"
        text += f"📞 Телефон: {participant['number']}\n\n"
        text += "✏️ Выберите поле для редактирования:"
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text,
            reply_markup=keyboard
        )
    @bot.callback_query_handler(func=lambda call: call.data.startswith("edit_field_"))
    def callback_edit_field(call):
        field = call.data.split("edit_field_")[1]
        admin_id = call.from_user.id
        
        if admin_id not in admin_temp_data:
            bot.answer_callback_query(call.id, "❌ Данные редактирования не найдены")
            return
        
        participant_id = admin_temp_data[admin_id]['editing_participant_id']
        admin_temp_data[admin_id]['editing_field'] = field
        
        keyboard = types.InlineKeyboardMarkup()
        if admin_id in admin_temp_data and admin_temp_data[admin_id].get('from_search'):
            keyboard.add(types.InlineKeyboardButton("⬅️ Назад к участнику", callback_data=f"search_participant_{participant_id}"))
        else:
            keyboard.add(types.InlineKeyboardButton("⬅️ Назад к участнику", callback_data=f"participant_{participant_id}"))
        
        field_names = {
            'fio': 'ФИО',
            'date_fest': 'дату фестиваля',
            'time_fest': 'время',
            'gender': 'пол',
            'date_of_birth': 'дату рождения',
            'status': 'статус',
            'region': 'регион',
            'city': 'город',
            'number': 'номер телефона'
        }
        
        if field == 'gender':
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(types.InlineKeyboardButton("Мужской", callback_data="update_gender_Мужской"))
            keyboard.add(types.InlineKeyboardButton("Женский", callback_data="update_gender_Женский"))
            if admin_id in admin_temp_data and admin_temp_data[admin_id].get('from_search'):
                keyboard.add(types.InlineKeyboardButton("⬅️ Назад к участнику", callback_data=f"search_participant_{participant_id}"))
            else:
                keyboard.add(types.InlineKeyboardButton("⬅️ Назад к участнику", callback_data=f"participant_{participant_id}"))
            text = f"Выберите новый пол:"
        elif field == 'status':
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(types.InlineKeyboardButton("Родитель", callback_data="update_status_Родитель"))
            keyboard.add(types.InlineKeyboardButton("Ребенок", callback_data="update_status_Ребенок"))
            keyboard.add(types.InlineKeyboardButton("Педагог", callback_data="update_status_Педагог"))
            keyboard.add(types.InlineKeyboardButton("Студент", callback_data="update_status_Студент"))
            keyboard.add(types.InlineKeyboardButton("Взрослый", callback_data="update_status_Взрослый"))
            if admin_id in admin_temp_data and admin_temp_data[admin_id].get('from_search'):
                keyboard.add(types.InlineKeyboardButton("⬅️ Назад к участнику", callback_data=f"search_participant_{participant_id}"))
            else:
                keyboard.add(types.InlineKeyboardButton("⬅️ Назад к участнику", callback_data=f"participant_{participant_id}"))
            text = f"Выберите новый статус:"
        elif field == 'date_fest':
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(types.InlineKeyboardButton("24 октября", callback_data="update_date_fest_24 октября"))
            keyboard.add(types.InlineKeyboardButton("25 октября", callback_data="update_date_fest_25 октября"))
            keyboard.add(types.InlineKeyboardButton("24-25 октября", callback_data="update_date_fest_24-25 октября"))
            if admin_id in admin_temp_data and admin_temp_data[admin_id].get('from_search'):
                keyboard.add(types.InlineKeyboardButton("⬅️ Назад к участнику", callback_data=f"search_participant_{participant_id}"))
            else:
                keyboard.add(types.InlineKeyboardButton("⬅️ Назад к участнику", callback_data=f"participant_{participant_id}"))
            text = f"Выберите новую дату фестиваля:"
        elif field == 'time_fest':
            # Получаем информацию об участнике для проверки date_fest
            participant = db.get_participant_by_id(participant_id)
            
            if participant['date_fest'] == '24-25 октября':
                # Для двухдневного посещения показываем кнопки для первого дня
                keyboard = types.InlineKeyboardMarkup()
                keyboard.add(types.InlineKeyboardButton("13:00", callback_data="update_time1_13:00"))
                keyboard.add(types.InlineKeyboardButton("14:00", callback_data="update_time1_14:00"))
                keyboard.add(types.InlineKeyboardButton("15:00", callback_data="update_time1_15:00"))
                keyboard.add(types.InlineKeyboardButton("16:00", callback_data="update_time1_16:00"))
                keyboard.add(types.InlineKeyboardButton("17:00", callback_data="update_time1_17:00"))
                keyboard.add(types.InlineKeyboardButton("18:00", callback_data="update_time1_18:00"))
                # Кнопка назад остается как есть
                text = f"Выберите время посещения для 24 октября:"
            else:
                # Для однодневного посещения - текстовый ввод как сейчас
                text = f"Введите новое значение для поля '{field_names[field]}':"
                bot.register_next_step_handler(call.message, edit_field_handler, admin_id, field)
        else:
            text = f"Введите новое значение для поля '{field_names[field]}':"
            bot.register_next_step_handler(call.message, edit_field_handler, admin_id, field)
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text,
            reply_markup=keyboard
        )

    # Обработчики для кнопочных полей
    @bot.callback_query_handler(func=lambda call: call.data.startswith("update_gender_"))
    def callback_update_gender(call):
        new_value = call.data.split("update_gender_")[1]
        update_field_value(call, 'gender', new_value)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("update_status_"))
    def callback_update_status(call):
        new_value = call.data.split("update_status_")[1]
        update_field_value(call, 'status', new_value)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("update_date_fest_"))
    def callback_update_date_fest(call):
        new_value = call.data.split("update_date_fest_")[1]
        update_field_value(call, 'date_fest', new_value)

    def update_field_value(call, field, new_value):
        admin_id = call.from_user.id
        if admin_id not in admin_temp_data:
            return
        
        participant_id = admin_temp_data[admin_id]['editing_participant_id']
        
        if db.update_participant_field(participant_id, field, new_value):
            
            success_text = "✅ Данные успешно обновлены!"
        else:
            success_text = "❌ Ошибка при обновлении данных"
        
        keyboard = types.InlineKeyboardMarkup()
        if admin_id in admin_temp_data and admin_temp_data[admin_id].get('from_search'):
            keyboard.add(types.InlineKeyboardButton("⬅️ Назад к участнику", callback_data=f"search_participant_{participant_id}"))
        else:
            keyboard.add(types.InlineKeyboardButton("⬅️ Назад к участнику", callback_data=f"participant_{participant_id}"))
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=success_text,
            reply_markup=keyboard
        )
        
        # Очищаем временные данные
        if admin_id in admin_temp_data:
            del admin_temp_data[admin_id]
    # ========== СКАЧАТЬ ДАННЫЕ ==========
    @bot.callback_query_handler(func=lambda call: call.data == "download_data")
    def callback_download_data(call):
        try:
            participants = db.get_all_participants()
            
            if not participants:
                keyboard = types.InlineKeyboardMarkup()
                keyboard.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data="callback_start"))
                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text="📊 База данных пуста",
                    reply_markup=keyboard
                )
                return
            
            # Создаем DataFrame
            df = pd.DataFrame(participants)
            
            # Переименовываем колонки на русский
            column_mapping = {
                'id': 'ID',
                'fio': 'ФИО',
                'date_fest': 'Дата фестиваля',
                'time_fest': 'Время',
                'gender': 'Пол',
                'date_of_birth': 'Дата рождения',
                'status': 'Статус',
                'region': 'Регион',
                'city': 'Город',
                'number': 'Телефон',
                'created_at': 'Дата регистрации',
                'telegram_id': 'ID Телеграмма'
            }
            df = df.rename(columns=column_mapping)
            
            # Создаем Excel файл в памяти
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Участники', index=False)
            
            output.seek(0)
            
            # Отправляем файл
            current_date = datetime.now().strftime("%Y-%m-%d_%H-%M")
            filename = f"festival_participants_{current_date}.xlsx"
            clear_chat_history_optimized(call.message, 1)
            bot.send_document(
                call.message.chat.id,
                document=output,
                visible_file_name=filename,
                caption=f"📊 База данных участников фестиваля\n👥 Всего участников: {len(participants)}"
            )
            
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data="callback_start"))
            safe_send_message(
                call.message.chat.id,
                "✅ Файл успешно создан и отправлен!",
                reply_markup=keyboard
            )
            
        except Exception as e:
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data="callback_start"))
            safe_send_message(
                call.message.chat.id,
                f"❌ Ошибка при создании файла: {str(e)}",
                reply_markup=keyboard
            )

    # ========== ЗАДАТЬ ВОПРОС ==========
    @bot.callback_query_handler(func=lambda call: call.data == "ask_quest")
    def callback_ask_question(call):
        bot.clear_step_handler_by_chat_id(call.message.chat.id)
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data="callback_start"))
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="❓ Введите ваш вопрос:",
            reply_markup=keyboard
        )
        
        bot.register_next_step_handler(call.message, ask_question_handler)

    def ask_question_handler(message):
        bot.delete_message(message.chat.id, message.message_id)
        
        user_id = message.from_user.id
        username = message.from_user.username
        full_name = f"{message.from_user.first_name or ''} {message.from_user.last_name or ''}".strip()
        question_text = message.text.strip()
        
        question_id = db.save_question(user_id, username, full_name, question_text)
        
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data="callback_start"))
        
        if question_id:
            text1 = f"✅ Ваш вопрос отправлен!\n📋 Номер вопроса: {question_id}\n\n💬 Ответ придет в этот чат."
        else:
            text1 = "❌ Ошибка при отправке вопроса. Попробуйте позже."
        clear_chat_history_optimized(message, 2)
        safe_send_message(
            chat_id=1385548872,
            text = 'Добавлен вопрос в разделе "Ответить на вопрос"', 
            reply_markup=keyboard)
        safe_send_message(
            chat_id=message.chat.id,
            text = text1, 
            reply_markup=keyboard)

    # ========== ОТВЕТИТЬ НА ВОПРОС ==========
    @bot.callback_query_handler(func=lambda call: call.data == "answer_quest")
    def callback_answer_questions(call):
        questions = db.get_unanswered_questions()
        
        keyboard = types.InlineKeyboardMarkup()
        
        if questions:
            keyboard.add(types.InlineKeyboardButton("📝 Посмотреть вопросы", callback_data="view_questions"))
        
        keyboard.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data="callback_start"))
        
        text = f"💬 Неотвеченных вопросов: {len(questions)}"
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text,
            reply_markup=keyboard
        )

    @bot.callback_query_handler(func=lambda call: call.data == "view_questions")
    def callback_view_questions(call):
        questions = db.get_unanswered_questions()
        
        if not questions:
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data="callback_start"))
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="✅ Все вопросы отвечены!",
                reply_markup=keyboard
            )
            return
        
        # Показываем первые 5 вопросов
        text = "📝 Неотвеченные вопросы:\n\n"
        keyboard = types.InlineKeyboardMarkup()
        
        for i, question in enumerate(questions[:5], 1):
            text += f"{i}. От: {question['full_name']} (@{question['username'] or 'без username'})\n"
            text += f"❓ {question['question_text'][:100]}...\n"
            text += f"📅 {question['created_at'].strftime('%d.%m.%Y %H:%M')}\n\n"
            
            keyboard.add(types.InlineKeyboardButton(
                f"Ответить на вопрос {i}", 
                callback_data=f"answer_{question['id']}"
            ))
        
        if len(questions) > 5:
            text += f"... и еще {len(questions) - 5} вопросов"
        
        keyboard.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data="callback_start"))
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text,
            reply_markup=keyboard
        )

    @bot.callback_query_handler(func=lambda call: call.data.startswith("answer_"))
    def callback_answer_specific_question(call):
        question_id = int(call.data.split("_")[1])
        question = db.get_question_by_id(question_id)
        
        if not question:
            bot.answer_callback_query(call.id, "❌ Вопрос не найден")
            return
        
        admin_temp_data[call.from_user.id] = {'question_id': question_id}
        
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("📝 Посмотреть вопросы", callback_data="view_questions"))
        keyboard.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data="callback_start"))
        
        text = f"❓ Вопрос #{question['id']}\n"
        text += f"От: {question['full_name']} (@{question['username'] or 'без username'})\n"
        text += f"📅 {question['created_at'].strftime('%d.%m.%Y %H:%M')}\n\n"
        text += f"💬 Вопрос: {question['question_text']}\n\n"
        text += "✏️ Введите ваш ответ:"
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text,
            reply_markup=keyboard
        )
        
        bot.register_next_step_handler(call.message, answer_question_handler, call.from_user.id)

    def answer_question_handler(message, admin_id):
        bot.delete_message(message.chat.id, message.message_id)
        
        if admin_id not in admin_temp_data:
            return
        
        question_id = admin_temp_data[admin_id]['question_id']
        answer_text = message.text.strip()
        
        question = db.get_question_by_id(question_id)
        if not question:
            safe_send_message(message.chat.id, "❌ Вопрос не найден")
            return
        
        # Сохраняем ответ в базе данных
        if db.answer_question(question_id, answer_text):
            # Отправляем ответ пользователю
            try:
                safe_send_message(
                    question['telegram_id'],
                    f"✅ Ответ на ваш вопрос #{question_id}:\n\n"
                    f"❓ Ваш вопрос: {question['question_text']}\n\n"
                    f"💬 Ответ: {answer_text}"
                )
                success_text = "✅ Ответ отправлен пользователю!"
            except:
                success_text = "✅ Ответ сохранен, но не удалось отправить пользователю"
        else:
            success_text = "❌ Ошибка при сохранении ответа"
        time.sleep(1)
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("📝 Посмотреть вопросы", callback_data="view_questions"))
        keyboard.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data="callback_start"))
        
        safe_send_message(message.chat.id, success_text, reply_markup=keyboard)
        
        # Очищаем временные данные
        if admin_id in admin_temp_data:
            del admin_temp_data[admin_id]

    # ========== РАССЫЛКА ==========
    @bot.callback_query_handler(func=lambda call: call.data == "mailing")
    def callback_mailing(call):
        bot.clear_step_handler_by_chat_id(call.message.chat.id)
        
        participants_count = db.get_participants_count()
        
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data="callback_start"))
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"📢 Рассылка сообщений\n\n👥 Участников в базе: {participants_count}\n\n✏️ Отправьте текст, фото или документ для рассылки:",
            reply_markup=keyboard
        )
        
        bot.register_next_step_handler(call.message, mailing_content_handler, call.from_user.id)
    @bot.callback_query_handler(func=lambda call: call.data == "send_message")
    def callback_send_personal_message(call):
        bot.clear_step_handler_by_chat_id(call.message.chat.id)
        
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data="callback_start"))
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="📋 Введите Telegram ID пользователя:",
            reply_markup=keyboard
        )
        
        bot.register_next_step_handler(call.message, personal_message_id_handler, call.from_user.id)

    def personal_message_id_handler(message, admin_id):
        bot.delete_message(message.chat.id, message.message_id)
        
        try:
            target_id = int(message.text.strip())
            
            # Сохраняем ID получателя
            admin_temp_data[admin_id] = {'target_telegram_id': target_id}
            
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data="callback_start"))
            
            clear_chat_history_optimized(message, 2)
            safe_send_message(
                message.chat.id,
                f"✅ ID получателя: {target_id}\n\n✏️ Теперь введите текст сообщения:",
                reply_markup=keyboard
            )
            
            bot.register_next_step_handler(message, personal_message_text_handler, admin_id)
            
        except ValueError:
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data="callback_start"))
            
            clear_chat_history_optimized(message, 2)
            safe_send_message(
                message.chat.id,
                "❌ Неправильный формат ID! Введите числовой ID:",
                reply_markup=keyboard
            )
            bot.register_next_step_handler(message, personal_message_id_handler, admin_id)

    def personal_message_text_handler(message, admin_id):
        bot.delete_message(message.chat.id, message.message_id)
        
        if admin_id not in admin_temp_data:
            return
        
        target_id = admin_temp_data[admin_id]['target_telegram_id']
        message_text = message.text.strip()
        
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data="callback_start"))
        
        try:
            safe_send_message(
                target_id,
                f"📬 Личное сообщение от администратора:\n\n{message_text}"
            )
            
            clear_chat_history_optimized(message, 2)
            safe_send_message(
                message.chat.id,
                f"✅ Сообщение успешно отправлено пользователю {target_id}!",
                reply_markup=keyboard
            )
            
        except Exception as e:
            clear_chat_history_optimized(message, 2)
            safe_send_message(
                message.chat.id,
                f"❌ Ошибка при отправке сообщения: {str(e)}",
                reply_markup=keyboard
            )
        
        # Очищаем временные данные
        if admin_id in admin_temp_data:
            del admin_temp_data[admin_id]
    def mailing_content_handler(message, admin_id):
        bot.delete_message(message.chat.id, message.message_id)
        
        telegram_ids = db.get_all_telegram_ids()
        
        if not telegram_ids:
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data="callback_start"))
            safe_send_message(
                message.chat.id,
                "❌ Нет зарегистрированных пользователей для рассылки",
                reply_markup=keyboard
            )
            return
        
        # Определяем тип контента
        content_type = message.content_type
        content_data = {}
        
        if content_type == 'text':
            content_data = {
                'type': 'text',
                'text': message.text,
                'preview': f"📝 Текст: {message.text[:100]}{'...' if len(message.text) > 100 else ''}"
            }
        elif content_type == 'photo':
            photo = message.photo[-1]  # Берем фото наибольшего размера
            content_data = {
                'type': 'photo',
                'file_id': photo.file_id,
                'caption': message.caption or '',
                'preview': f"📸 Фото{' с подписью: ' + message.caption[:50] + '...' if message.caption else ''}"
            }
        elif content_type == 'document':
            document = message.document
            content_data = {
                'type': 'document',
                'file_id': document.file_id,
                'caption': message.caption or '',
                'filename': document.file_name,
                'preview': f"📄 Документ: {document.file_name}{' с подписью: ' + message.caption[:50] + '...' if message.caption else ''}"
            }
        else:
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data="callback_start"))
            safe_send_message(
                message.chat.id,
                "❌ Поддерживаются только текстовые сообщения, фото и документы",
                reply_markup=keyboard
            )
            return
        
        # Показываем предварительный просмотр
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("✅ Отправить", callback_data="confirm_mailing"))
        keyboard.add(types.InlineKeyboardButton("❌ Отмена", callback_data="callback_start"))
        
        # Сохраняем данные для рассылки
        admin_temp_data[admin_id] = {
            'content_data': content_data,
            'telegram_ids': telegram_ids
        }
        
        preview_text = f"📢 Предварительный просмотр рассылки:\n\n"
        preview_text += f"{content_data['preview']}\n\n"
        preview_text += f"👥 Будет отправлено {len(telegram_ids)} пользователям\n\n"
        preview_text += "Подтвердите отправку:"
        clear_chat_history_optimized(message, 3)
        safe_send_message(message.chat.id, preview_text, reply_markup=keyboard)
    @bot.callback_query_handler(func=lambda call: call.data.startswith("update_time1_"))
    def callback_update_time1(call):
        """Первое время для 24-25 октября (24 октября)"""
        time1 = call.data.split("update_time1_")[1]
        admin_id = call.from_user.id
        
        # Сохраняем первое время во временные данные
        admin_temp_data[admin_id]['time1'] = time1
        
        # Показываем кнопки для второго дня
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("15:00", callback_data="update_time2_15:00"))
        keyboard.add(types.InlineKeyboardButton("16:00", callback_data="update_time2_16:00"))
        keyboard.add(types.InlineKeyboardButton("17:00", callback_data="update_time2_17:00"))
        keyboard.add(types.InlineKeyboardButton("18:00", callback_data="update_time2_18:00"))
        participant_id = admin_temp_data[admin_id]['editing_participant_id']
        if admin_id in admin_temp_data and admin_temp_data[admin_id].get('from_search'):
            keyboard.add(types.InlineKeyboardButton("⬅️ Назад к участнику", callback_data=f"search_participant_{participant_id}"))
        else:
            keyboard.add(types.InlineKeyboardButton("⬅️ Назад к участнику", callback_data=f"participant_{participant_id}"))
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"Выбрано время для 24 октября: {time1}\n\nТеперь выберите время для 25 октября.\n\nВременные слоты 12:00, 13:00, 14:00 закрыты, в связи с максимальным количеством участников в данное время.",
            reply_markup=keyboard
        )

    @bot.callback_query_handler(func=lambda call: call.data.startswith("update_time2_"))
    def callback_update_time2(call):
        """Второе время для 24-25 октября (25 октября)"""
        time2 = call.data.split("update_time2_")[1]
        admin_id = call.from_user.id
        
        if admin_id not in admin_temp_data or 'time1' not in admin_temp_data[admin_id]:
            bot.answer_callback_query(call.id, "❌ Ошибка: первое время не найдено")
            return
        
        time1 = admin_temp_data[admin_id]['time1']
        new_value = f"{time1};{time2}"
        
        # Обновляем поле в БД
        update_field_value(call, 'time_fest', new_value)
    @bot.callback_query_handler(func=lambda call: call.data == "confirm_mailing")
    def callback_confirm_mailing(call):
        admin_id = call.from_user.id
        
        if admin_id not in admin_temp_data:
            bot.answer_callback_query(call.id, "❌ Данные рассылки не найдены")
            return
        
        mailing_data = admin_temp_data[admin_id]
        content_data = mailing_data['content_data']
        telegram_ids = mailing_data['telegram_ids']
        
        # Отправляем уведомление о начале рассылки
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"📤 Начинается рассылка...\n👥 Пользователей: {len(telegram_ids)}"
        )
        
        sent_count = 0
        failed_count = 0
        
        # Отправляем сообщения в зависимости от типа контента
        for i, telegram_id in enumerate(telegram_ids):
            try:
                if content_data['type'] == 'text':
                    safe_send_message(telegram_id, content_data['text'])
                elif content_data['type'] == 'photo':
                    bot.send_photo(telegram_id, content_data['file_id'], 
                                caption=content_data['caption'])
                elif content_data['type'] == 'document':
                    bot.send_document(telegram_id, content_data['file_id'], 
                                    caption=content_data['caption'])
                
                sent_count += 1
                
                # ДОБАВИТЬ АДАПТИВНУЮ ЗАДЕРЖКУ:
                if i % 20 == 0 and i > 0:  # Каждые 20 сообщений
                    sleep(1)  # Пауза 1 секунда
                else:
                    sleep(0.1)  # Базовая задержка
                    
            except Exception as e:
                if "Too Many Requests" in str(e):
                    sleep(10)  # Ждем 10 секунд при превышении лимита
                    continue
                failed_count += 1
        
        # Сохраняем статистику рассылки (для текстового контента сохраняем preview)
        message_for_db = content_data.get('text', content_data['preview'])
        db.save_mailing(admin_id, message_for_db, sent_count, failed_count)
        
        # Отправляем отчет
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data="callback_start"))
        
        report_text = f"📊 Отчет о рассылке:\n\n"
        report_text += f"✅ Успешно отправлено: {sent_count}\n"
        report_text += f"❌ Не удалось отправить: {failed_count}\n"
        report_text += f"📈 Успешность: {(sent_count / len(telegram_ids) * 100):.1f}%"
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=report_text,
            reply_markup=keyboard
        )
        
        # Очищаем временные данные
        if admin_id in admin_temp_data:
            del admin_temp_data[admin_id]

    # ========== КАК ДОБРАТЬСЯ ==========
    @bot.callback_query_handler(func=lambda call: call.data == "how_get")
    def callback_how_get(call):
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data="callback_start"))
        
        # Здесь указываем информацию о том, как добраться до места проведения
        location_text = """🚗 Как добраться до места проведения фестиваля:

📍 Адрес: Шевченко 47б

🚌 Общественный транспорт:
• Автобус №33 до остановки "ГРЭС-2"
до остановки Енисейская - далее пешком 700м
до остановки Шевченко - далее пешком 700м

🚗 На автомобиле:
• Парковка доступна рядом с местом проведения
• GPS координаты: 56.469852, 84.990921

🚶‍♂️ Пешком от остановки: 5-10 минут

⏰ Рекомендуем приехать за 15 минут до начала"""
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=location_text,
            reply_markup=keyboard
        )

    # ========== ОФИЦИАЛЬНЫЙ САЙТ ==========
    @bot.callback_query_handler(func=lambda call: call.data == "web_cite")
    def callback_web_site(call):
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("🌐 Перейти на сайт", url=WEBSITE_URL))
        keyboard.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data="callback_start"))
        
        site_text = """🌐 Официальный сайт мероприятия:

На сайте вы можете найти:
• 📋 Подробную программу мероприятия
• 👥 Информацию о спикерах
• 📸 Фотографии с прошлых мероприятий
• 📞 Контактную информацию
• 📰 Новости и анонсы

Нажмите кнопку ниже, чтобы перейти на сайт."""
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=site_text,
            reply_markup=keyboard
        )

# ========== ФУНКЦИЯ ДЛЯ СОХРАНЕНИЯ УЧАСТНИКА ==========
def save_participant_to_db(participant_data, registrator_id):
    """
    Функция для сохранения участника в базу данных
    Вызывается из модуля registr.py после завершения регистрации
    """
    if db is None:
        print("❌ База данных не инициализирована")
        return None
    
    # Добавляем telegram_id в данные участника (если его еще нет)
    if 'telegram_id' not in participant_data:
        participant_data['telegram_id'] = registrator_id
    
    participant_id = db.save_participant(participant_data, registrator_id)
    return participant_id

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========
def format_participant_info(participant):
    """Форматирование информации об участнике для отображения"""
    text = f"👤 {participant['fio']}\n"
    text += f"📅 {participant['date_fest']} в {participant['time_fest']}\n"
    text += f"🎂 Дата рождения: {participant['date_of_birth']}\n"
    text += f"👥 Пол: {participant['gender']}\n"
    text += f"🏷 Статус: {participant['status']}\n"
    text += f"🌍 Регион: {participant['region']}\n"
    text += f"🏠 Город: {participant['city']}\n"
    text += f"📞 Телефон: {participant['number']}\n"
    text += f"📋 ID: {participant['id']}\n"
    text += f"📅 Зарегистрирован: {participant['created_at'].strftime('%d.%m.%Y %H:%M')}"
    return text

def get_statistics():
    """Получение статистики для администраторов"""
    if db is None:
        return "❌ База данных недоступна"
    
    total_participants = db.get_participants_count()
    unanswered_questions = len(db.get_unanswered_questions())
    
    stats = f"📊 Статистика фестиваля:\n\n"
    stats += f"👥 Всего участников: {total_participants}\n"
    stats += f"❓ Неотвеченных вопросов: {unanswered_questions}\n"
    stats += f"📅 Последнее обновление: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
    
    return stats
def edit_field_handler(message, admin_id, field):
    #bot.delete_message(message.chat.id, message.message_id)
    
    if admin_id not in admin_temp_data:
        return
    
    participant_id = admin_temp_data[admin_id]['editing_participant_id']
    new_value = message.text.strip()
    
    # Валидация данных (такая же как в регистрации)
    validation_error = None
    
    if field == 'fio':
        words = new_value.split()
        if len(words) < 2:
            clear_chat_history_optimized(message, 2)
            validation_error = "Неправильный формат ввода!\nВведите ФИО в формате Иванов Иван Иванович"
        else:
            for word in words:
                if not word[0].isupper():
                    clear_chat_history_optimized(message, 2)
                    validation_error = "Каждое слово должно начинаться с заглавной буквы!\nВведите ФИО в формате Иванов Иван Иванович"
                    break
    
    elif field == 'time_fest':
            participant_id = admin_temp_data[admin_id]['editing_participant_id']
            participant = db.get_participant_by_id(participant_id)
            if participant['date_fest'] == '24-25 октября':
                return
            if len(new_value) != 5 or new_value.count(':') != 1:
                clear_chat_history_optimized(message, 2)
                validation_error = 'Неправильный формат времени!\nВведите время в формате "ЧЧ:ММ"'
            else:
                try:
                    from datetime import datetime
                    time_obj = datetime.strptime(new_value, "%H:%M").time()
                    start_time = datetime.strptime("12:00", "%H:%M").time()
                    end_time = datetime.strptime("19:00", "%H:%M").time()
                    if not (start_time <= time_obj <= end_time):
                        clear_chat_history_optimized(message, 2)
                        validation_error = 'Время должно быть в диапазоне от 12:00 до 19:00!'
                except ValueError:
                    clear_chat_history_optimized(message, 2)
                    validation_error = 'Неправильный формат времени!\nВведите время в формате "ЧЧ:ММ"'
    
    elif field == 'date_of_birth':
        try:
            from datetime import datetime
            birth_date = datetime.strptime(new_value, "%d.%m.%Y")
            current_date = datetime.now()
            if birth_date.year <= 1900:
                clear_chat_history_optimized(message, 2)
                validation_error = 'Год рождения должен быть больше 1900!'
            elif birth_date > current_date:
                clear_chat_history_optimized(message, 2)
                validation_error = 'Дата рождения не может быть больше текущей даты!'
        except ValueError:
            clear_chat_history_optimized(message, 2)
            validation_error = 'Неправильный формат даты!\nВведите дату в формате "ДД.ММ.ГГГГ"'
    
    elif field == 'number':
        if len(new_value) != 12 or not new_value.startswith('+79') or not new_value[3:].isdigit():
            clear_chat_history_optimized(message, 2)
            validation_error = 'Неправильный формат номера!\nВведите номер в формате "+79XXXXXXXXX"'
    
    if validation_error:
        clear_chat_history_optimized(message, 2)
        keyboard = types.InlineKeyboardMarkup()
        if admin_id in admin_temp_data and admin_temp_data[admin_id].get('from_search'):
            keyboard.add(types.InlineKeyboardButton("⬅️ Назад к участнику", callback_data=f"search_participant_{participant_id}"))
        else:
            keyboard.add(types.InlineKeyboardButton("⬅️ Назад к участнику", callback_data=f"participant_{participant_id}"))
        message1 = safe_send_message(message.chat.id, validation_error, reply_markup=keyboard)
        bot.register_next_step_handler(message, edit_field_handler, admin_id, field)
        return
    
    # Обновляем данные
    if db.update_participant_field(participant_id, field, new_value):
        success_text = "✅ Данные успешно обновлены!"
    else:
        success_text = "❌ Ошибка при обновлении данных"
    
    keyboard = types.InlineKeyboardMarkup()
    if admin_id in admin_temp_data and admin_temp_data[admin_id].get('from_search'):
        keyboard.add(types.InlineKeyboardButton("⬅️ Назад к участнику", callback_data=f"search_participant_{participant_id}"))
    else:
        keyboard.add(types.InlineKeyboardButton("⬅️ Назад к участнику", callback_data=f"participant_{participant_id}"))
    clear_chat_history_optimized(message, 2)
    safe_send_message(message.chat.id, success_text, reply_markup=keyboard)
    
    # Очищаем временные данные
    if admin_id in admin_temp_data:
        del admin_temp_data[admin_id]

def safe_send_message(chat_id, text, reply_markup=None, **kwargs):
    """Безопасная отправка с rate limiting"""
    import time
    
    current_time = time.time()
    if chat_id in last_message_time:
        time_diff = current_time - last_message_time[chat_id]
        if time_diff < 1.0:  # Меньше секунды
            sleep(1.0 - time_diff)
    
    try:
        result = bot.send_message(chat_id, text, reply_markup=reply_markup, **kwargs)  # ИСПРАВИТЬ НА bot.send_message
        last_message_time[chat_id] = time.time()
        return result
    except Exception as e:
        if "Too Many Requests" in str(e):
            sleep(5)  # Ждем 5 секунд при превышении лимита
            return bot.send_message(chat_id, text, reply_markup=reply_markup, **kwargs)  # ИСПРАВИТЬ НА bot.send_message
        raise e