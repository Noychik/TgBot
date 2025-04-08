import telebot
import os
import json
import threading
import time
from dotenv import load_dotenv
from telebot import types
from datetime import datetime, date, timedelta

# Загрузка переменных окружения
load_dotenv()

# Инициализация бота
bot = telebot.TeleBot(os.getenv('BOT_TOKEN'))

# Пути к файлам
TASKS_FILE = 'tasks.json'
USERS_FILE = 'users.json'

# Словарь для хранения отправленных уведомлений
notifications_sent = {}

# Настройки уведомлений
NOTIFICATION_TIMES = {
    '1 день': timedelta(days=1),
    '12 часов': timedelta(hours=12),
    '6 часов': timedelta(hours=6),
    '2 часа': timedelta(hours=2),
    '30 минут': timedelta(minutes=30)
}

# Загрузка задач из файла
def load_tasks():
    if os.path.exists(TASKS_FILE):
        with open(TASKS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

# Сохранение задач в файл
def save_tasks(tasks):
    with open(TASKS_FILE, 'w', encoding='utf-8') as f:
        json.dump(tasks, f, ensure_ascii=False, indent=4)

# Загрузка пользователей из файла
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

# Сохранение пользователей в файл
def save_users(users):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=4)

# Получение задач пользователя
def get_user_tasks(chat_id):
    tasks = load_tasks()
    return [task for task in tasks if task.get('user_id') == chat_id]

# Проверка валидности даты и времени дедлайна
def is_valid_deadline(deadline_datetime):
    now = datetime.now()
    return deadline_datetime >= now

# Функция для удаления старых выполненных задач
def cleanup_completed_tasks():
    while True:
        tasks = load_tasks()
        now = datetime.now()
        one_week_ago = now - timedelta(days=7)
        
        # Фильтруем задачи, которые не нужно удалять
        tasks_to_keep = []
        for task in tasks:
            # Если задача не выполнена, оставляем её
            if not task.get('completed', False):
                tasks_to_keep.append(task)
            # Если задача выполнена, проверяем дату выполнения
            else:
                completed_at = datetime.strptime(task.get('completed_at', now.strftime('%Y-%m-%d %H:%M:%S')), '%Y-%m-%d %H:%M:%S')
                if completed_at > one_week_ago:
                    tasks_to_keep.append(task)
        
        # Если есть изменения, сохраняем обновленный список
        if len(tasks_to_keep) != len(tasks):
            save_tasks(tasks_to_keep)
        
        # Проверяем раз в день
        time.sleep(86400)  # 24 часа в секундах

# Функция для отправки тестовых уведомлений
def send_test_notifications(time_delta, message, chat_id=None):
    tasks = load_tasks()
    users = load_users()
    
    # Если указан chat_id, отправляем уведомления только этому пользователю
    if chat_id:
        user_tasks = [task for task in tasks if task.get('user_id') == chat_id and task['deadline'] and not task['completed']]
        for task in user_tasks:
            try:
                # Пробуем разные форматы даты
                try:
                    deadline = datetime.strptime(task['deadline'], '%Y-%m-%d %H:%M')
                except ValueError:
                    deadline = datetime.strptime(task['deadline'], '%Y-%m-%d')
                
                notification = f"⚠️ Тестовое уведомление!\n\n" \
                             f"Задача: {task['title']}\n" \
                             f"Дедлайн через: {message}\n" \
                             f"Текущий дедлайн: {task['deadline']}"
                
                try:
                    bot.send_message(chat_id, notification, reply_markup=get_back_to_main_keyboard())
                except Exception as e:
                    print(f"Ошибка отправки уведомления пользователю {chat_id}: {e}")
            except Exception as e:
                print(f"Ошибка обработки задачи {task['id']}: {e}")
    else:
        # Отправляем всем пользователям
        for task in tasks:
            if task['deadline'] and not task['completed']:
                try:
                    # Пробуем разные форматы даты
                    try:
                        deadline = datetime.strptime(task['deadline'], '%Y-%m-%d %H:%M')
                    except ValueError:
                        deadline = datetime.strptime(task['deadline'], '%Y-%m-%d')
                    
                    notification = f"⚠️ Тестовое уведомление!\n\n" \
                                 f"Задача: {task['title']}\n" \
                                 f"Дедлайн через: {message}\n" \
                                 f"Текущий дедлайн: {task['deadline']}"
                    
                    user_id = task.get('user_id')
                    if user_id:
                        try:
                            bot.send_message(user_id, notification, reply_markup=get_back_to_main_keyboard())
                        except Exception as e:
                            print(f"Ошибка отправки уведомления пользователю {user_id}: {e}")
                except Exception as e:
                    print(f"Ошибка обработки задачи {task['id']}: {e}")

# Функция для проверки дедлайнов
def check_deadlines():
    while True:
        try:
            tasks = load_tasks()
            users = load_users()
            current_time = datetime.now()
            
            for task in tasks:
                if task.get('completed', False):
                    continue
                
                # Пропускаем задачи без дедлайна
                if not task.get('deadline'):
                    continue
                    
                try:
                    # Пробуем разные форматы даты
                    try:
                        deadline = datetime.strptime(task['deadline'], '%Y-%m-%d %H:%M')
                    except ValueError:
                        deadline = datetime.strptime(task['deadline'], '%d.%m.%Y %H:%M')
                        
                    time_left = deadline - current_time
                    
                    # Проверяем каждое включенное уведомление
                    for notif_time, delta in NOTIFICATION_TIMES.items():
                        if task.get('notifications', {}).get(notif_time, False):
                            if timedelta(0) <= time_left <= delta:
                                try:
                                    message = f"⚠️ Напоминание о задаче:\n\n"
                                    message += f"Задача: {task['description']}\n"
                                    message += f"Дедлайн: {task['deadline']}\n"
                                    message += f"Осталось времени: {str(time_left).split('.')[0]}"
                                    
                                    bot.send_message(
                                        task['user_id'],
                                        message,
                                        reply_markup=get_back_to_main_keyboard()
                                    )
                                except Exception as e:
                                    print(f"Ошибка при отправке уведомления: {e}")
                except ValueError as e:
                    print(f"Ошибка при обработке дедлайна задачи {task.get('id')}: {e}")
                    continue
                
        except Exception as e:
            print(f"Ошибка при проверке дедлайнов: {e}")
        
        time.sleep(60)  # Проверяем каждую минуту

# Создание клавиатуры
def get_main_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(types.KeyboardButton("Просмотреть список задач"))
    keyboard.add(types.KeyboardButton("Создать новую задачу"))
    keyboard.add(types.KeyboardButton("Отметить задачу как выполненную"))
    return keyboard

# Создание клавиатуры с кнопкой возврата в главное меню
def get_back_to_main_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(types.KeyboardButton("Вернуться в главное меню"))
    return keyboard

# Словарь для хранения состояний пользователей
user_states = {}

# Обработчик команды /start
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    users = load_users()
    
    if str(user_id) not in users:
        users[str(user_id)] = {
            'username': message.from_user.username or 'Unknown',
            'first_name': message.from_user.first_name or 'Unknown',
            'last_name': message.from_user.last_name or 'Unknown'
        }
        save_users(users)
    
    bot.reply_to(
        message,
        "Привет! Я бот для управления задачами. Используйте кнопки ниже для работы со мной.",
        reply_markup=get_main_keyboard()
    )

# Обработчик команды /test
@bot.message_handler(commands=['test'])
def test_notifications(message):
    chat_id = message.chat.id
    send_test_notifications(timedelta(minutes=30), "30 минут", chat_id)
    bot.reply_to(message, "Тестовое уведомление отправлено!", reply_markup=get_back_to_main_keyboard())

# Обработчик текстовых сообщений
@bot.message_handler(func=lambda message: True)
def handle_messages(message):
    chat_id = message.chat.id
    
    if message.text == "Вернуться в главное меню":
        user_states[chat_id] = None
        bot.reply_to(
            message,
            "Главное меню:",
            reply_markup=get_main_keyboard()
        )
        return

    # Если пользователь в процессе создания задачи
    if user_states.get(chat_id) == 'waiting_for_task_name':
        tasks = load_tasks()
        # Получаем информацию о пользователе
        users = load_users()
        user_info = users.get(str(chat_id), {'username': 'Unknown'})
        username = user_info.get('username', 'Unknown')
        
        new_task = {
            'id': len(tasks) + 1,
            'title': message.text,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'deadline': None,
            'completed': False,
            'user_id': chat_id,
            'username': username,
            'notifications': {time: False for time in NOTIFICATION_TIMES.keys()}
        }
        tasks.append(new_task)
        save_tasks(tasks)
        
        # Переходим к вводу даты
        user_states[chat_id] = {
            'state': 'waiting_for_deadline_date',
            'task_index': len(tasks) - 1,
            'notifications': {time: False for time in NOTIFICATION_TIMES.keys()}
        }
        
        bot.reply_to(
            message,
            "Введите дату дедлайна в формате ДД.ММ.ГГГГ или напишите 'нет' если дедлайн не нужен:",
            reply_markup=get_back_to_main_keyboard()
        )
        return

    # Если пользователь вводит дату дедлайна
    if user_states.get(chat_id, {}).get('state') == 'waiting_for_deadline_date':
        tasks = load_tasks()
        task_index = user_states[chat_id].get('task_index')
        
        if task_index is None or task_index >= len(tasks):
            bot.reply_to(message, "Ошибка: задача не найдена", reply_markup=get_back_to_main_keyboard())
            user_states[chat_id] = None
            return
            
        if message.text.lower() == 'нет':
            # Если дедлайн не нужен, переходим к настройке уведомлений
            bot.reply_to(
                message,
                get_notification_message(user_states[chat_id]['notifications']),
                reply_markup=get_notification_keyboard(user_states[chat_id]['notifications'])
            )
            user_states[chat_id]['state'] = 'waiting_for_notifications'
            return
        else:
            try:
                deadline_date = datetime.strptime(message.text, '%d.%m.%Y')
                if not is_valid_deadline(deadline_date):
                    bot.reply_to(
                        message,
                        "Ошибка: Дата дедлайна не может быть в прошлом. Пожалуйста, введите корректную дату в формате ДД.ММ.ГГГГ или напишите 'нет':",
                        reply_markup=get_back_to_main_keyboard()
                    )
                    return
                
                # Сохраняем дату и переходим к вводу времени
                user_states[chat_id]['state'] = 'waiting_for_deadline_time'
                user_states[chat_id]['date'] = deadline_date
                
                bot.reply_to(
                    message,
                    "Теперь введите время дедлайна в формате ЧЧ:ММ:",
                    reply_markup=get_back_to_main_keyboard()
                )
                return
            except ValueError:
                bot.reply_to(
                    message,
                    "Неверный формат даты. Пожалуйста, используйте формат ДД.ММ.ГГГГ или напишите 'нет':",
                    reply_markup=get_back_to_main_keyboard()
                )
                return

    # Если пользователь вводит время дедлайна
    if isinstance(user_states.get(chat_id), dict) and user_states[chat_id].get('state') == 'waiting_for_deadline_time':
        tasks = load_tasks()
        task_index = user_states[chat_id].get('task_index')
        
        if task_index is None or task_index >= len(tasks):
            bot.reply_to(message, "Ошибка: задача не найдена", reply_markup=get_back_to_main_keyboard())
            user_states[chat_id] = None
            return
            
        try:
            deadline_time = datetime.strptime(message.text, '%H:%M').time()
            deadline_date = user_states[chat_id]['date']
            deadline_datetime = datetime.combine(deadline_date.date(), deadline_time)
            
            if not is_valid_deadline(deadline_datetime):
                bot.reply_to(
                    message,
                    "Ошибка: Время дедлайна не может быть в прошлом. Пожалуйста, введите корректное время в формате ЧЧ:ММ:",
                    reply_markup=get_back_to_main_keyboard()
                )
                return
            
            # Сохраняем дедлайн
            tasks[task_index]['deadline'] = deadline_datetime.strftime('%d.%m.%Y %H:%M')
            save_tasks(tasks)
            
            # Переходим к настройке уведомлений
            user_states[chat_id]['state'] = 'waiting_for_notifications'
            bot.reply_to(
                message,
                get_notification_message(user_states[chat_id]['notifications']),
                reply_markup=get_notification_keyboard(user_states[chat_id]['notifications'])
            )
            return
        except ValueError:
            bot.reply_to(
                message,
                "Неверный формат времени. Пожалуйста, используйте формат ЧЧ:ММ:",
                reply_markup=get_back_to_main_keyboard()
            )
            return

    # Если пользователь выбирает задачу для отметки как выполненную
    if user_states.get(chat_id) == 'waiting_for_task_to_complete':
        tasks = load_tasks()
        try:
            task_id = int(message.text)
            # Находим задачу пользователя с указанным ID
            user_tasks = [task for task in tasks if task.get('user_id') == chat_id and task['id'] == task_id]
            
            if not user_tasks:
                bot.reply_to(
                    message,
                    "Ошибка: задача не найдена или не принадлежит вам. Пожалуйста, выберите задачу из списка:",
                    reply_markup=get_back_to_main_keyboard()
                )
                return
                
            task_index = tasks.index(user_tasks[0])
            tasks[task_index]['completed'] = True
            tasks[task_index]['completed_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            save_tasks(tasks)
            
            user_states[chat_id] = None
            bot.reply_to(
                message,
                f"Задача '{tasks[task_index]['title']}' отмечена как выполненная! Она будет автоматически удалена через неделю.",
                reply_markup=get_main_keyboard()
            )
            return
        except ValueError:
            bot.reply_to(
                message,
                "Неверный формат. Пожалуйста, введите номер задачи из списка:",
                reply_markup=get_back_to_main_keyboard()
            )
            return

    if message.text == "Просмотреть список задач":
        user_tasks = get_user_tasks(chat_id)
        if not user_tasks:
            bot.reply_to(message, "У вас нет задач", reply_markup=get_back_to_main_keyboard())
        else:
            response = "Ваши задачи:\n\n"
            for task in user_tasks:
                status = "✅" if task['completed'] else "⏳"
                deadline = f" (дедлайн: {task['deadline']})" if task['deadline'] else ""
                completed_at = f" (выполнено: {task['completed_at']})" if task.get('completed_at') else ""
                response += f"{status} {task['id']}. {task['title']}{deadline}{completed_at} (создано: {task['created_at']})\n"
            bot.reply_to(message, response, reply_markup=get_back_to_main_keyboard())
    
    elif message.text == "Создать новую задачу":
        user_states[chat_id] = 'waiting_for_task_name'
        bot.reply_to(
            message,
            "Введите название новой задачи:",
            reply_markup=get_back_to_main_keyboard()
        )
    
    elif message.text == "Отметить задачу как выполненную":
        user_tasks = get_user_tasks(chat_id)
        if not user_tasks:
            bot.reply_to(message, "У вас нет задач для отметки", reply_markup=get_back_to_main_keyboard())
        else:
            # Фильтруем только невыполненные задачи
            incomplete_tasks = [task for task in user_tasks if not task['completed']]
            if not incomplete_tasks:
                bot.reply_to(message, "У вас нет невыполненных задач", reply_markup=get_back_to_main_keyboard())
            else:
                response = "Выберите задачу для отметки как выполненную (введите номер):\n\n"
                for task in incomplete_tasks:
                    deadline = f" (дедлайн: {task['deadline']})" if task['deadline'] else ""
                    response += f"{task['id']}. {task['title']}{deadline}\n"
                
                user_states[chat_id] = 'waiting_for_task_to_complete'
                bot.reply_to(
                    message,
                    response,
                    reply_markup=get_back_to_main_keyboard()
                )
    
    else:
        bot.reply_to(message, "Пожалуйста, используйте кнопки для навигации", reply_markup=get_back_to_main_keyboard())

@bot.callback_query_handler(func=lambda call: call.data.startswith('notif_'))
def handle_notification_toggle(call):
    chat_id = call.message.chat.id
    time = call.data.replace('notif_', '')
    
    if chat_id not in user_states or not isinstance(user_states[chat_id], dict):
        bot.answer_callback_query(call.id, "Ошибка: настройки не найдены")
        return
        
    # Переключаем состояние уведомления
    user_states[chat_id]['notifications'][time] = not user_states[chat_id]['notifications'][time]
    
    # Обновляем сообщение с новыми настройками
    bot.edit_message_text(
        chat_id=chat_id,
        message_id=call.message.message_id,
        text=get_notification_message(user_states[chat_id]['notifications']),
        reply_markup=get_notification_keyboard(user_states[chat_id]['notifications'])
    )

@bot.callback_query_handler(func=lambda call: call.data == 'save_notifications')
def handle_save_notifications(call):
    chat_id = call.message.chat.id
    
    if chat_id not in user_states or not isinstance(user_states[chat_id], dict):
        bot.answer_callback_query(call.id, "Ошибка: настройки не найдены")
        return
        
    # Сохраняем настройки уведомлений в задаче
    tasks = load_tasks()
    task_index = user_states[chat_id].get('task_index')
    
    if task_index is not None and task_index < len(tasks):
        tasks[task_index]['notifications'] = user_states[chat_id]['notifications']
        save_tasks(tasks)
        
        # Завершаем создание задачи
        user_states[chat_id] = None
        
        # Отправляем сообщение о завершении
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text="Задача успешно создана!"
        )
        bot.send_message(
            chat_id,
            "Вы можете создать новую задачу или просмотреть существующие.",
            reply_markup=get_main_keyboard()
        )
    else:
        bot.answer_callback_query(call.id, "Ошибка: задача не найдена")

def get_notification_message(notifications):
    message = "Настройте уведомления для задачи:\n\n"
    for time, enabled in notifications.items():
        status = "✅" if enabled else "❌"
        message += f"{time}: {status}\n"
    return message

def get_notification_keyboard(notifications):
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    for time, enabled in notifications.items():
        status = "✅" if enabled else "❌"
        keyboard.add(
            types.InlineKeyboardButton(
                f"{time}: {status}",
                callback_data=f"notif_{time}"
            )
        )
    keyboard.add(
        types.InlineKeyboardButton(
            "Сохранить настройки",
            callback_data="save_notifications"
        )
    )
    return keyboard

# Запуск бота
if __name__ == '__main__':
    # Запускаем проверку дедлайнов в отдельном потоке
    deadline_thread = threading.Thread(target=check_deadlines, daemon=True)
    deadline_thread.start()
    
    # Запускаем очистку выполненных задач в отдельном потоке
    cleanup_thread = threading.Thread(target=cleanup_completed_tasks, daemon=True)
    cleanup_thread.start()
    
    print("Бот запущен...")
    bot.polling(none_stop=True) 