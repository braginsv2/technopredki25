from telebot import types
from handler import clear_chat_history_optimized
from datetime import datetime
import time

user_temp_data = {}
bot = None
db = None

def init_bot(bot_instance, db_instance=None):
    global bot, db
    bot = bot_instance
    db = db_instance

    @bot.callback_query_handler(func=lambda call: call.data == "btn_new_part")
    def callback_mew_part(call):
        from config import MESSAGES, REGULATION_URL
        bot.clear_step_handler_by_chat_id(call.message.chat.id)
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("Даю согласие", callback_data="soglasen"))
        keyboard.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data="callback_start"))
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=MESSAGES['consent_text']+f"\n'С положением можно ознакомиться на официальном сайте или по ссылке {REGULATION_URL}", 
            reply_markup=keyboard)
    
    @bot.callback_query_handler(func=lambda call: call.data == "soglasen")
    def callback_mew_part(call):
        bot.clear_step_handler_by_chat_id(call.message.chat.id)
        clear_chat_history_optimized(call.message, 1)

        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data="callback_start"))

        message1 = bot.send_message(
            call.message.chat.id,
            'Введите ФИО участника фестиваля в формате Иванов Иван Иванович',
            reply_markup=keyboard)
        
        user_message_id = message1.message_id
        bot.register_next_step_handler(call.message, FIO, user_message_id)

    @bot.callback_query_handler(func=lambda call: call.data in ["24_oct", "25_oct", "24-25_oct"])
    def callback_date_fest(call):
        bot.clear_step_handler_by_chat_id(call.message.chat.id)
        user_id = call.from_user.id 
        data = user_temp_data[user_id]

        keyboard = types.InlineKeyboardMarkup()

        if call.data == "24_oct":
            data.update({'date_fest': '24 октября'})
            user_temp_data[user_id] = data
            keyboard.add(types.InlineKeyboardButton("12:00", callback_data="12:00"),types.InlineKeyboardButton("13:00", callback_data="13:00"), types.InlineKeyboardButton("14:00", callback_data="14:00"))
            keyboard.add(types.InlineKeyboardButton("15:00", callback_data="15:00"),types.InlineKeyboardButton("16:00", callback_data="16:00"), types.InlineKeyboardButton("17:00", callback_data="17:00"))
            keyboard.add(types.InlineKeyboardButton("18:00", callback_data="18:00"),types.InlineKeyboardButton("⬅️ Назад", callback_data="date_fest_back"))
            bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="Выберите время посещения фестиваля.",
            reply_markup=keyboard)
        elif call.data == "25_oct":
            data.update({'date_fest': '25 октября'})
            user_temp_data[user_id] = data
            keyboard.add(types.InlineKeyboardButton("12:00", callback_data="12:00"),types.InlineKeyboardButton("13:00", callback_data="13:00"), types.InlineKeyboardButton("14:00", callback_data="14:00"))
            keyboard.add(types.InlineKeyboardButton("15:00", callback_data="15:00"),types.InlineKeyboardButton("16:00", callback_data="16:00"), types.InlineKeyboardButton("17:00", callback_data="17:00"))
            keyboard.add(types.InlineKeyboardButton("18:00", callback_data="18:00"),types.InlineKeyboardButton("⬅️ Назад", callback_data="date_fest_back"))
            bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="Выберите время посещения фестиваля.",
            reply_markup=keyboard)
        elif call.data == "24-25_oct":
            data.update({'date_fest': '24-25 октября'})
            user_temp_data[user_id] = data
            keyboard.add(types.InlineKeyboardButton("12:00", callback_data="12:0024"),types.InlineKeyboardButton("13:00", callback_data="13:0024"), types.InlineKeyboardButton("14:00", callback_data="14:0024"))
            keyboard.add(types.InlineKeyboardButton("15:00", callback_data="15:0024"),types.InlineKeyboardButton("16:00", callback_data="16:0024"), types.InlineKeyboardButton("17:00", callback_data="17:0024"))
            keyboard.add(types.InlineKeyboardButton("18:00", callback_data="18:0024"),types.InlineKeyboardButton("⬅️ Назад", callback_data="date_fest_back"))
            bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="Выберите время посещения фестиваля 24 октября.",
            reply_markup=keyboard)
 

    @bot.callback_query_handler(func=lambda call: call.data in ["date_fest_back"])
    def callback_date_fest_back(call):
        bot.clear_step_handler_by_chat_id(call.message.chat.id)
        user_id = call.from_user.id 
        print(user_id)
        data = user_temp_data[user_id]
        data.update({'time_fest': ''})
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("24 октября", callback_data="24_oct"))
        keyboard.add(types.InlineKeyboardButton("25 октября", callback_data="25_oct"))
        keyboard.add(types.InlineKeyboardButton("24-25 октября", callback_data="24-25_oct"))
        keyboard.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="soglasen"))
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="Выберите день, когда вы хотели бы посетить мероприятие.",
            reply_markup=keyboard)
    @bot.callback_query_handler(func=lambda call: call.data in ["12:00", "13:00", "14:00", "15:00", "16:00", "17:00", "18:00", 'back_gender'])
    def callback_time_fest(call):
        user_id = call.from_user.id 
        bot.clear_step_handler_by_chat_id(call.message.chat.id)
        print(user_id)
        data = user_temp_data[user_id]
        if call.data == 'back_gender':
            pass
        elif len(list(data.get('time_fest', ''))) == 5:
            data.update({'time_fest': data['time_fest']+";"+call.data})
        else:
            data.update({'time_fest': call.data})

        user_temp_data[user_id] = data

        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("Мужской", callback_data="male"))
        keyboard.add(types.InlineKeyboardButton("Женский", callback_data="female"))
        keyboard.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="time_back"))
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="Выберите пол.",
            reply_markup=keyboard)
    @bot.callback_query_handler(func=lambda call: call.data in ["12:0024", "13:0024", "14:0024", "15:0024", "16:0024", "17:0024", "18:0024"])
    def callback_time_fest2(call):
        bot.clear_step_handler_by_chat_id(call.message.chat.id)
        user_id = call.from_user.id 
        data = user_temp_data[user_id]

        keyboard = types.InlineKeyboardMarkup()
        data.update({'time_fest': call.data[:5]})
        user_temp_data[user_id] = data
        keyboard.add(types.InlineKeyboardButton("12:00", callback_data="12:00"),types.InlineKeyboardButton("13:00", callback_data="13:00"), types.InlineKeyboardButton("14:00", callback_data="14:00"))
        keyboard.add(types.InlineKeyboardButton("15:00", callback_data="15:00"),types.InlineKeyboardButton("16:00", callback_data="16:00"), types.InlineKeyboardButton("17:00", callback_data="17:00"))
        keyboard.add(types.InlineKeyboardButton("18:00", callback_data="18:00"),types.InlineKeyboardButton("⬅️ Назад", callback_data="date_fest_back"))
        bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="Выберите время посещения фестиваля 25 октября.",
        reply_markup=keyboard)

    @bot.callback_query_handler(func=lambda call: call.data in ["male", "female"])
    def callback_male(call):
        user_id = call.from_user.id
        bot.clear_step_handler_by_chat_id(call.message.chat.id) 
        print(user_id)
        data = user_temp_data[user_id]
        if call.data == "male":
            data.update({'gender': "Мужской"})
        elif call.data == "female":
            data.update({'gender': "Женский"})

        user_temp_data[user_id] = data

        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("⬅️ Назад", callback_data='back_gender'))

        message1 = bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text='Введите дату рождения в формате "ДД.ММ.ГГГГ".',
            reply_markup=keyboard)
        user_message_id = message1.message_id
        bot.register_next_step_handler(call.message, date_of_birth, data, user_message_id)

    @bot.callback_query_handler(func=lambda call: call.data in ["time_back"])
    def callback_time_fest_back(call):
        user_id = call.from_user.id
        bot.clear_step_handler_by_chat_id(call.message.chat.id) 
        data = user_temp_data[user_id]

        keyboard = types.InlineKeyboardMarkup()

        if data['date_fest'] == "24 октября":
            keyboard.add(types.InlineKeyboardButton("12:00", callback_data="12:00"),types.InlineKeyboardButton("13:00", callback_data="13:00"), types.InlineKeyboardButton("14:00", callback_data="14:00"))
            keyboard.add(types.InlineKeyboardButton("15:00", callback_data="15:00"),types.InlineKeyboardButton("16:00", callback_data="16:00"), types.InlineKeyboardButton("17:00", callback_data="17:00"))
            keyboard.add(types.InlineKeyboardButton("18:00", callback_data="18:00"),types.InlineKeyboardButton("⬅️ Назад", callback_data="date_fest_back"))
            bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="Выберите время посещения фестиваля.",
            reply_markup=keyboard)
        elif data['date_fest'] == "25 октября":
            keyboard.add(types.InlineKeyboardButton("12:00", callback_data="12:00"),types.InlineKeyboardButton("13:00", callback_data="13:00"), types.InlineKeyboardButton("14:00", callback_data="14:00"))
            keyboard.add(types.InlineKeyboardButton("15:00", callback_data="15:00"),types.InlineKeyboardButton("16:00", callback_data="16:00"), types.InlineKeyboardButton("17:00", callback_data="17:00"))
            keyboard.add(types.InlineKeyboardButton("18:00", callback_data="18:00"),types.InlineKeyboardButton("⬅️ Назад", callback_data="date_fest_back"))
            bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="Выберите время посещения фестиваля.",
            reply_markup=keyboard)
        elif data['date_fest'] == "24-25 октября":

            keyboard.add(types.InlineKeyboardButton("12:00", callback_data="12:0024"),types.InlineKeyboardButton("13:00", callback_data="13:0024"), types.InlineKeyboardButton("14:00", callback_data="14:0024"))
            keyboard.add(types.InlineKeyboardButton("15:00", callback_data="15:0024"),types.InlineKeyboardButton("16:00", callback_data="16:0024"), types.InlineKeyboardButton("17:00", callback_data="17:0024"))
            keyboard.add(types.InlineKeyboardButton("18:00", callback_data="18:0024"),types.InlineKeyboardButton("⬅️ Назад", callback_data="date_fest_back"))
            bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="Выберите время посещения фестиваля 24 октября.",
            reply_markup=keyboard)
    @bot.callback_query_handler(func=lambda call: call.data in ["status_parent", "status_baby", "status_teacher", "status_student", "status_big"])
    def callback_status(call):
        user_id = call.from_user.id
        bot.clear_step_handler_by_chat_id(call.message.chat.id) 
        data = user_temp_data[user_id]

        if call.data == "status_parent":
            data.update({'status': 'Родитель'})
        elif call.data == "status_baby":
            data.update({'status': 'Ребенок'})
        elif call.data == "status_teacher":
            data.update({'status': 'Учитель'})
        elif call.data == "status_student":
            data.update({'status': 'Студент'})
        elif call.data == "status_big":
            data.update({'status': 'Взрослый'})

        user_temp_data[user_id] = data          
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="status_back"))
        message1 = bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text='Введите свой регион, например, "Томская область".',
            reply_markup=keyboard)
        user_message_id = message1.message_id
        bot.register_next_step_handler(call.message, region, data, user_message_id)
    @bot.callback_query_handler(func=lambda call: call.data in ["status_back"])
    def callback_status_back(call): 
        user_id = call.from_user.id
        bot.clear_step_handler_by_chat_id(call.message.chat.id)
        data = user_temp_data[user_id]
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("Родитель", callback_data="status_parent"))
        keyboard.add(types.InlineKeyboardButton("Ребенок", callback_data="status_baby"))
        keyboard.add(types.InlineKeyboardButton("Педагог", callback_data="status_teacher"))
        keyboard.add(types.InlineKeyboardButton("Студент", callback_data="status_student"))
        keyboard.add(types.InlineKeyboardButton("Взрослый", callback_data="status_big"))
        if data['gender'] == "Мужской":
            keyboard.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="male"))
        elif data['gender'] == "Женский":
            keyboard.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="female"))
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="Выберите статус.", 
            reply_markup=keyboard )  
def FIO(message, user_message_id):
    bot.delete_message(message.chat.id, user_message_id)
    bot.delete_message(message.chat.id, message.message_id)

    if len(message.text.split())<2:
            message = bot.send_message(message.chat.id, text="Неправильный формат ввода!\nВведите ФИО клиента в формате Иванов Иван Иванович".format(message.from_user))
            user_message_id = message.message_id
            bot.register_next_step_handler(message, FIO, user_message_id)
    else:
        words = message.text.split()
        for word in words:
            if not word[0].isupper():  # Проверяем, что первая буква заглавная
                message = bot.send_message(message.chat.id, text="Каждое слово должно начинаться с заглавной буквы!\nВведите ФИО клиента в формате Иванов Иван Иванович")
                user_message_id = message.message_id
                bot.register_next_step_handler(message, FIO, user_message_id)
                return
        data = {"fio": message.text}
        user_id = message.from_user.id
        print(user_id)
        user_temp_data[user_id] = data

        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("24 октября", callback_data="24_oct"))
        keyboard.add(types.InlineKeyboardButton("25 октября", callback_data="25_oct"))
        keyboard.add(types.InlineKeyboardButton("24-25 октября", callback_data="24-25_oct"))
        keyboard.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="soglasen"))
        bot.send_message(
            message.chat.id,
            'Выберите день, когда вы хотели бы посетить мероприятие.',
            reply_markup=keyboard)


def date_of_birth(message, data, user_message_id):
    user_id = message.from_user.id
    bot.delete_message(message.chat.id, user_message_id)
    bot.delete_message(message.chat.id, message.message_id)
    try:
        birth_date = datetime.strptime(message.text, "%d.%m.%Y")
        current_date = datetime.now()

        # Проверяем, что год больше 1900
        if birth_date.year <= 1900:
            message1 = bot.send_message(
                message.chat.id, 
                'Год рождения должен быть больше 1900!\n'
                'Введите дату рождения в формате "ДД.ММ.ГГГГ".'
            )
            user_message_id = message1.message_id
            bot.register_next_step_handler(message, date_of_birth, data, user_message_id)
            return
        
        # Проверяем, что дата не больше текущей
        if birth_date > current_date:
            message1 = bot.send_message(
                message.chat.id, 
                'Дата рождения не может быть больше текущей даты!\n'
                'Введите дату рождения в формате "ДД.ММ.ГГГГ".'
            )
            user_message_id = message1.message_id
            bot.register_next_step_handler(message, date_of_birth, data, user_message_id)
            return
        
        data.update({"date_of_birth": message.text})

        user_temp_data[user_id] = data
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("Родитель", callback_data="status_parent"))
        keyboard.add(types.InlineKeyboardButton("Ребенок", callback_data="status_baby"))
        keyboard.add(types.InlineKeyboardButton("Педагог", callback_data="status_teacher"))
        keyboard.add(types.InlineKeyboardButton("Студент", callback_data="status_student"))
        keyboard.add(types.InlineKeyboardButton("Взрослый", callback_data="status_big"))
        if data['gender'] == "Мужской":
            keyboard.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="male"))
        elif data['gender'] == "Женский":
            keyboard.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="female"))
        bot.send_message(message.chat.id, text="Выберите статус.", reply_markup=keyboard )

    except ValueError:
        message1 = bot.send_message(message.chat.id, text='Неправильный формат ввода!\nВведите дату рождения в формате "ДД.ММ.ГГГГ".')
        user_message_id = message1.message_id
        bot.register_next_step_handler(message, date_of_birth, data, user_message_id)

def region(message, data, user_message_id):
    user_id = message.from_user.id
    bot.delete_message(message.chat.id, user_message_id)
    bot.delete_message(message.chat.id, message.message_id)
    data.update({'region': message.text})
    user_temp_data[user_id] = data
    keyboard = types.InlineKeyboardMarkup()
    if data['status'] == "Родитель":
        keyboard.add(types.InlineKeyboardButton("⬅️ Назад", callback_data='status_parent'))
    elif data['status'] == "Ребенок":
        keyboard.add(types.InlineKeyboardButton("⬅️ Назад", callback_data='status_baby'))
    elif data['status'] == "Педагог":
        keyboard.add(types.InlineKeyboardButton("⬅️ Назад", callback_data='status_teacher'))
    elif data['status'] == "Студент":
        keyboard.add(types.InlineKeyboardButton("⬅️ Назад", callback_data='status_student'))
    else:
        keyboard.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="status_big"))

    message1 = bot.send_message(message.chat.id, text='Введите свой населенный пункт, например, "г.Томск".', reply_markup=keyboard)
    user_message_id = message1.message_id
    bot.register_next_step_handler(message, city, data, user_message_id)

def city(message, data, user_message_id):
    user_id = message.from_user.id
    bot.delete_message(message.chat.id, user_message_id)
    bot.delete_message(message.chat.id, message.message_id)
    data.update({'city': message.text})
    user_temp_data[user_id] = data

    keyboard = types.InlineKeyboardMarkup()
    if data['status'] == "Родитель":
        keyboard.add(types.InlineKeyboardButton("⬅️ Назад", callback_data='status_parent'))
    elif data['status'] == "Ребенок":
        keyboard.add(types.InlineKeyboardButton("⬅️ Назад", callback_data='status_baby'))
    elif data['status'] == "Педагог":
        keyboard.add(types.InlineKeyboardButton("⬅️ Назад", callback_data='status_teacher'))
    elif data['status'] == "Студент":
        keyboard.add(types.InlineKeyboardButton("⬅️ Назад", callback_data='status_student'))
    else:
        keyboard.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="status_big"))

    message1 = bot.send_message(message.chat.id, text='Введите номер телефона в формате "+79XXXXXXXXX".', reply_markup=keyboard)
    user_message_id = message1.message_id
    bot.register_next_step_handler(message, number, data, user_message_id)

def number(message, data, user_message_id):
    user_id = message.from_user.id
    registrator_id = message.from_user.id 
    bot.delete_message(message.chat.id, user_message_id)
    bot.delete_message(message.chat.id, message.message_id)
    if len(message.text) != 12 or not message.text.startswith('+79') or not message.text[3:].isdigit():
        user_message_id = message.message_id
        message = bot.send_message(message.chat.id, text='Неправильный формат ввода!\nВведите номер телефона в формате "+79XXXXXXXXX".')
        user_message_id = message.message_id
        bot.register_next_step_handler(message, number, data, user_message_id)
    else:
        data.update({"number": message.text, "telegram_id": user_id})
        print(data)
        if user_id in user_temp_data:
            if user_temp_data[user_id].get('processing'):
                bot.send_message(message.chat.id, "⏳ Регистрация уже обрабатывается, подождите...")
                return
        
        # Помечаем, что идет обработка
        data.update({"number": message.text, "telegram_id": user_id, "processing": True})
        user_temp_data[user_id] = data
        
        if db:
            participant_id = db.save_participant(data, registrator_id)
            if participant_id:
                # ПРОВЕРЯЕМ, НОВЫЙ ЛИ УЧАСТНИК ИЛИ УЖЕ СУЩЕСТВОВАЛ:
                existing_participant = db.get_participant_by_id(participant_id)
                if existing_participant and existing_participant['fio'].lower().strip() == data['fio'].lower().strip():
                    # Если нашли точное совпадение по ФИО
                    current_time = datetime.now()
                    registration_time = existing_participant['created_at']
                    
                    # Если регистрация была давно (больше минуты назад)
                    if (current_time - registration_time).total_seconds() > 60:
                        success_text = f'⚠️ Участник с ФИО "{data["fio"]}" уже был зарегистрирован ранее.\n📋 Номер участника: {participant_id}'
                    else:
                        success_text = f'✅ Вы успешно зарегистрировались на фестиваль!\n📋 Ваш номер участника: {participant_id}'
                else:
                    success_text = f'✅ Поздравляю, вы успешно зарегистрировались на фестиваль!\n📋 Ваш номер участника: {participant_id}'
                
                print(f"✅ Участник {data['fio']} сохранен в БД с ID: {participant_id}")
            else:
                success_text = '❌ Ошибка регистрации. Обратитесь к администратору.'
                print(f"❌ Ошибка сохранения участника {data['fio']} в БД")
        else:
            success_text = '❌ База данных недоступна. Обратитесь к администратору.'
            print("❌ База данных не инициализирована")
        
        # Очищаем временные данные пользователя
        if user_id in user_temp_data:
            del user_temp_data[user_id]
        
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data="callback_start"))
        bot.send_message(message.chat.id, text=success_text, reply_markup=keyboard)

