import psycopg2
from psycopg2.extras import RealDictCursor
import psycopg2.pool
from datetime import datetime
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, host, database, user, password, port=5432):
        self.connection_params = {
            'host': host,
            'database': database,
            'user': user,
            'password': password,
            'port': port
        }
        
        self.connection_pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=20,
            **self.connection_params,
            connect_timeout=10,
            keepalives_idle=600,
            keepalives_interval=30,
            keepalives_count=3
        )
        # Удалить дублирующую строку с self.connection_pool
        self.connection = None
        self.connect()
        self.create_tables()

    def get_connection(self):
        """Получение соединения из пула"""
        return self.connection_pool.getconn()
    
    def put_connection(self, connection):
        """Возврат соединения в пул"""
        self.connection_pool.putconn(connection)

    def connect(self):
        """Подключение к базе данных"""
        try:
            logger.info("✅ Успешное подключение к базе данных PostgreSQL")
        except psycopg2.Error as e:
            logger.error(f"❌ Ошибка подключения к базе данных: {e}")
            raise

    def create_tables(self):
        """Создание таблиц в базе данных"""
        create_participants_table = """
        CREATE TABLE IF NOT EXISTS participants (
            id SERIAL PRIMARY KEY,
            telegram_id BIGINT NOT NULL,
            registrator_id BIGINT NOT NULL,
            fio VARCHAR(255) NOT NULL,
            date_fest VARCHAR(50) NOT NULL,
            time_fest VARCHAR(20) NOT NULL,
            gender VARCHAR(20) NOT NULL,
            date_of_birth VARCHAR(20) NOT NULL,
            status VARCHAR(50) NOT NULL,
            region VARCHAR(255) NOT NULL,
            city VARCHAR(255) NOT NULL,
            number VARCHAR(20) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        create_questions_table = """
        CREATE TABLE IF NOT EXISTS questions (
            id SERIAL PRIMARY KEY,
            telegram_id BIGINT NOT NULL,
            username VARCHAR(255),
            full_name VARCHAR(255),
            question_text TEXT NOT NULL,
            answer_text TEXT,
            is_answered BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            answered_at TIMESTAMP
        );
        """
        
        create_mailings_table = """
        CREATE TABLE IF NOT EXISTS mailings (
            id SERIAL PRIMARY KEY,
            admin_id BIGINT NOT NULL,
            message_text TEXT NOT NULL,
            sent_count INTEGER DEFAULT 0,
            failed_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        create_fio_index = """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_participants_fio_unique 
            ON participants(LOWER(TRIM(fio)));
            """
        
        connection = None
        try:
            connection = self.get_connection()
            with connection.cursor() as cursor:
                cursor.execute(create_participants_table)
                cursor.execute(create_questions_table)
                cursor.execute(create_mailings_table)
                cursor.execute(create_fio_index)
                connection.commit()
                logger.info("✅ Таблицы успешно созданы или уже существуют")
        except psycopg2.Error as e:
            if connection:
                connection.rollback()
            return None
        finally:
            if connection:
                self.put_connection(connection)

    def save_participant(self, participant_data, registrator_id):
        """Сохранение участника в базу данных"""
        insert_query = """
        INSERT INTO participants (
            telegram_id, registrator_id, fio, date_fest, time_fest, 
            gender, date_of_birth, status, region, city, number
        ) VALUES (
            %(telegram_id)s, %(registrator_id)s, %(fio)s, %(date_fest)s, %(time_fest)s,
            %(gender)s, %(date_of_birth)s, %(status)s, %(region)s, %(city)s, %(number)s
        )
        ON CONFLICT (LOWER(TRIM(fio))) DO UPDATE SET updated_at = CURRENT_TIMESTAMP 
        RETURNING id, (xmax = 0) AS is_new;
        """
        connection = None
        try:
            connection = self.get_connection()
            with connection.cursor() as cursor:
                # ПРОВЕРКА НА СУЩЕСТВУЮЩЕЕ ФИО:
                check_query = "SELECT id FROM participants WHERE LOWER(TRIM(fio)) = LOWER(TRIM(%s));"
                cursor.execute(check_query, (participant_data['fio'],))
                existing = cursor.fetchone()
                
                if existing:
                    logger.warning(f"⚠️ Участник {participant_data['fio']} уже зарегистрирован")
                    return existing[0]  # Возвращаем ID существующего участника
                
                # Остальной код без изменений...
                data_to_insert = participant_data.copy()
                data_to_insert['registrator_id'] = registrator_id
                
                cursor.execute(insert_query, data_to_insert)
                participant_id = cursor.fetchone()[0]
                connection.commit()
                
                logger.info(f"✅ Участник сохранен с ID: {participant_id}")
                return participant_id
                
        except psycopg2.Error as e:
            if connection:
                connection.rollback()
            return None
        finally:
            if connection:
                self.put_connection(connection)
    def check_participant_exists(self, fio, phone_number=None):
        """Проверка существования участника по ФИО и опционально по телефону"""
        base_query = "SELECT id, fio, number FROM participants WHERE LOWER(TRIM(fio)) = LOWER(TRIM(%s))"
        params = [fio]
        
        if phone_number:
            base_query += " OR number = %s"
            params.append(phone_number)
        
        connection = None
        try:
            connection = self.get_connection()
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(base_query, params)
                result = cursor.fetchone()
                return dict(result) if result else None
                
        except psycopg2.Error as e:
            logger.error(f"❌ Ошибка при проверке участника: {e}")
            return None
        finally:
            if connection:
                self.put_connection(connection)
    def get_participant_by_id(self, participant_id):
        """Получение участника по ID"""
        select_query = "SELECT * FROM participants WHERE id = %s;"
        connection = None
        try:
            connection = self.get_connection()
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(select_query, (participant_id,))
                participant = cursor.fetchone()
                return dict(participant) if participant else None
                
        except psycopg2.Error as e:
            if connection:
                connection.rollback()
            return None
        finally:
            if connection:
                self.put_connection(connection)

    def search_participants(self, search_term):
        """Поиск участников по ФИО или номеру телефона"""
        search_query = """
        SELECT * FROM participants 
        WHERE LOWER(fio) LIKE LOWER(%s) OR number LIKE %s
        ORDER BY created_at DESC;
        """
        connection = None
        try:
            connection = self.get_connection()
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                search_pattern = f"%{search_term}%"
                cursor.execute(search_query, (search_pattern, search_pattern))
                participants = cursor.fetchall()
                return [dict(p) for p in participants]
                
        except psycopg2.Error as e:
            if connection:
                connection.rollback()
            return None
        finally:
            if connection:
                self.put_connection(connection)

    def get_participants_by_registrator(self, registrator_id):
        """Получение участников, зарегистрированных конкретным администратором"""
        select_query = """
        SELECT * FROM participants 
        WHERE registrator_id = %s 
        ORDER BY created_at DESC;
        """
        connection = None
        try:
            connection = self.get_connection()
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(select_query, (registrator_id,))
                participants = cursor.fetchall()
                return [dict(p) for p in participants]
                
        except psycopg2.Error as e:
            if connection:
                connection.rollback()
            return None
        finally:
            if connection:
                self.put_connection(connection)
        
    def update_participant_field(self, participant_id, field_name, new_value):
        """Обновление определенного поля участника"""
        update_query = f"""
        UPDATE participants 
        SET {field_name} = %s, updated_at = CURRENT_TIMESTAMP 
        WHERE id = %s;
        """
        connection = None
        try:
            connection = self.get_connection()
            with connection.cursor() as cursor:
                cursor.execute(update_query, (new_value, participant_id))
                connection.commit()
                
                logger.info(f"✅ Обновлено поле {field_name} для участника {participant_id}")
                return True
                
        except psycopg2.Error as e:
            if connection:
                connection.rollback()
            return None
        finally:
            if connection:
                self.put_connection(connection)
    def get_all_participants(self):
        """Получение всех участников для скачивания данных"""
        select_query = """
        SELECT id, fio, date_fest, time_fest, gender, date_of_birth, 
               status, region, city, number, created_at, telegram_id
        FROM participants 
        ORDER BY created_at DESC;
        """
        connection = None
        try:
            connection = self.get_connection()
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(select_query)
                participants = cursor.fetchall()
                return [dict(p) for p in participants]
                
        except psycopg2.Error as e:
            if connection:
                connection.rollback()
            return None
        finally:
            if connection:
                self.put_connection(connection)
    def save_question(self, telegram_id, username, full_name, question_text):
        """Сохранение вопроса в базу данных"""
        insert_query = """
        INSERT INTO questions (telegram_id, username, full_name, question_text)
        VALUES (%s, %s, %s, %s) RETURNING id;
        """
        connection = None
        try:
            connection = self.get_connection()
            with connection.cursor() as cursor:
                cursor.execute(insert_query, (telegram_id, username, full_name, question_text))
                question_id = cursor.fetchone()[0]
                connection.commit()
                
                logger.info(f"✅ Вопрос сохранен с ID: {question_id}")
                return question_id
                
        except psycopg2.Error as e:
            if connection:
                connection.rollback()
            return None
        finally:
            if connection:
                self.put_connection(connection)
    def get_statistics(self):
        """Получение общей статистики участников"""
        query = """
        SELECT 
            COUNT(*) as total,
            COUNT(CASE WHEN date_fest = '24 октября' OR date_fest = '24-25 октября' THEN 1 END) as oct_24,
            COUNT(CASE WHEN date_fest = '25 октября' OR date_fest = '24-25 октября' THEN 1 END) as oct_25
        FROM participants;
        """
        connection = None
        try:
            connection = self.get_connection()
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query)
                result = cursor.fetchone()
                return dict(result) if result else None
        except psycopg2.Error as e:
            logger.error(f"❌ Ошибка получения статистики: {e}")
            return None
        finally:
            if connection:
                self.put_connection(connection)

    def get_time_statistics(self):
        """Получение статистики по времени для каждого дня"""
        query = """
        SELECT 
            time_fest,
            date_fest
        FROM participants;
        """
        connection = None
        try:
            connection = self.get_connection()
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query)
                results = cursor.fetchall()
                
                # Обрабатываем данные в Python
                time_stats_24 = {}
                time_stats_25 = {}
                
                for row in results:
                    time_fest = row['time_fest']
                    date_fest = row['date_fest']
                    
                    if date_fest == '24 октября':
                        time_stats_24[time_fest] = time_stats_24.get(time_fest, 0) + 1
                    elif date_fest == '25 октября':
                        time_stats_25[time_fest] = time_stats_25.get(time_fest, 0) + 1
                    elif date_fest == '24-25 октября':
                        # Разбиваем время через точку с запятой
                        times = time_fest.split(';')
                        if len(times) == 2:
                            time_stats_24[times[0]] = time_stats_24.get(times[0], 0) + 1
                            time_stats_25[times[1]] = time_stats_25.get(times[1], 0) + 1
                
                return {'oct_24': time_stats_24, 'oct_25': time_stats_25}
                
        except psycopg2.Error as e:
            logger.error(f"❌ Ошибка получения статистики по времени: {e}")
            return None
        finally:
            if connection:
                self.put_connection(connection)

    def get_age_statistics(self):
        """Получение статистики по возрасту"""
        query = """
        SELECT 
            date_of_birth
        FROM participants
        WHERE date_of_birth IS NOT NULL AND date_of_birth != '';
        """
        connection = None
        try:
            connection = self.get_connection()
            with connection.cursor() as cursor:
                cursor.execute(query)
                results = cursor.fetchall()
                
                # Вычисляем возраст в Python
                from datetime import datetime
                age_stats = {}
                
                for row in results:
                    try:
                        birth_date = datetime.strptime(row[0], '%d.%m.%Y')
                        age = datetime.now().year - birth_date.year
                        # Корректируем возраст если день рождения еще не наступил в этом году
                        if datetime.now().month < birth_date.month or \
                        (datetime.now().month == birth_date.month and datetime.now().day < birth_date.day):
                            age -= 1
                        
                        if 1 <= age <= 100:  # Фильтруем некорректные возрасты
                            age_stats[age] = age_stats.get(age, 0) + 1
                    except:
                        continue
                
                # Преобразуем в отсортированный список
                result = [{'age': age, 'count': count} for age, count in sorted(age_stats.items())]
                return result
                
        except psycopg2.Error as e:
            logger.error(f"❌ Ошибка получения статистики по возрасту: {e}")
            return None
        finally:
            if connection:
                self.put_connection(connection)
    def get_unanswered_questions(self):
        """Получение неотвеченных вопросов"""
        select_query = """
        SELECT * FROM questions 
        WHERE is_answered = FALSE 
        ORDER BY created_at ASC;
        """
        connection = None
        try:
            connection = self.get_connection()
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(select_query)
                questions = cursor.fetchall()
                return [dict(q) for q in questions]
                
        except psycopg2.Error as e:
            if connection:
                connection.rollback()
            return None
        finally:
            if connection:
                self.put_connection(connection)

    def answer_question(self, question_id, answer_text):
        """Ответ на вопрос"""
        update_query = """
        UPDATE questions 
        SET answer_text = %s, is_answered = TRUE, answered_at = CURRENT_TIMESTAMP
        WHERE id = %s;
        """
        connection = None
        try:
            connection = self.get_connection()
            with connection.cursor() as cursor:
                cursor.execute(update_query, (answer_text, question_id))
                connection.commit()
                
                logger.info(f"✅ Ответ на вопрос {question_id} сохранен")
                return True
                
        except psycopg2.Error as e:
            if connection:
                connection.rollback()
            return None
        finally:
            if connection:
                self.put_connection(connection)

    def get_question_by_id(self, question_id):
        """Получение вопроса по ID"""
        select_query = "SELECT * FROM questions WHERE id = %s;"
        connection = None
        try:
            connection = self.get_connection()
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(select_query, (question_id,))
                question = cursor.fetchone()
                return dict(question) if question else None
                
        except psycopg2.Error as e:
            if connection:
                connection.rollback()
            return None
        finally:
            if connection:
                self.put_connection(connection)

    def save_mailing(self, admin_id, message_text, sent_count=0, failed_count=0):
        """Сохранение информации о рассылке"""
        insert_query = """
        INSERT INTO mailings (admin_id, message_text, sent_count, failed_count)
        VALUES (%s, %s, %s, %s) RETURNING id;
        """
        connection = None
        try:
            connection = self.get_connection()
            with connection.cursor() as cursor:
                cursor.execute(insert_query, (admin_id, message_text, sent_count, failed_count))
                mailing_id = cursor.fetchone()[0]
                connection.commit()
                
                logger.info(f"✅ Рассылка сохранена с ID: {mailing_id}")
                return mailing_id
                
        except psycopg2.Error as e:
            if connection:
                connection.rollback()
            return None
        finally:
            if connection:
                self.put_connection(connection)

    def get_participants_count(self):
        """Получение количества участников"""
        count_query = "SELECT COUNT(*) FROM participants;"
        connection = None
        try:
            connection = self.get_connection()
            with connection.cursor() as cursor:
                cursor.execute(count_query)
                count = cursor.fetchone()[0]
                return count
                
        except psycopg2.Error as e:
            if connection:
                connection.rollback()
            return None
        finally:
            if connection:
                self.put_connection(connection)

    def get_all_telegram_ids(self):
        """Получение всех telegram_id зарегистрированных пользователей для рассылки"""
        select_query = "SELECT DISTINCT telegram_id FROM participants;"
        connection = None
        try:
            connection = self.get_connection()
            with connection.cursor() as cursor:
                cursor.execute(select_query)
                telegram_ids = [row[0] for row in cursor.fetchall()]
                return telegram_ids
                
        except psycopg2.Error as e:
            if connection:
                connection.rollback()
            return None
        finally:
            if connection:
                self.put_connection(connection)

    def close_connection(self):
        """Закрытие пула соединений с базой данных"""
        if hasattr(self, 'connection_pool') and self.connection_pool:
            self.connection_pool.closeall()
            logger.info("🔒 Пул соединений с базой данных закрыт")

    def __del__(self):
        """Деструктор для автоматического закрытия соединения"""
        self.close_connection()

