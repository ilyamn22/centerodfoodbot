import requests
import os
import asyncio
import telebot
import string
from telebot.util import quick_markup
from telebot.async_telebot import AsyncTeleBot
from datetime import datetime, date
import time
from babel.dates import format_date
from io import BytesIO
import pandas

meal_smiles = [
    '🍳', '🍎',
    '🍲', '🐟'
]
meal_names = [
    'breakfast', 'second_breakfast', 
    'lunch', 'dinner'
]
meal_names_ru = [
    'завтрак', 'второй завтрак',
    'обед', 'ужин' 
]
meal_id = dict([
    ('breakfast', 0), 
    ('second_breakfast', 1), 
    ('lunch', 2), 
    ('dinner', 3)
])
category_food = dict([
    ('гор.блюдо', 'dishes'),
    ('гор. блюдо', 'dishes'),
    ('закуска', 'dishes'),
    ('салат', 'dishes'),
    ('1 блюдо', 'dishes'),
    ('2 блюдо', 'dishes'),
    ('гарнир', 'dishes'),
    ('выпечка', 'dishes'),
    ('фрукт', 'dishes'),

    ('гор.напиток', 'drinks'),
    (' гор.напиток', 'drinks'),
    ('напиток', 'drinks'),

    ('сыр', 'other'),
    ('джем', 'other'),
    ('хлеб бел.', 'other'),
    ('хлеб черн.', 'other'),
    ('хлеб', 'other'),
])
category_names = [
    'dishes', 'drinks', 'other'
]
category_names_ru = [
    'блюда', 'напитки', 'прочее'
]

users_data = dict([
    
])
chats_id = [

]
columns_csv = ['username', 'details_page', 'newsletter', 
               'meals', 'categories']

date_loaded = ' '
data_food = '-'
launch_time = ''
version = '1.3'
bot = telebot.async_telebot.AsyncTeleBot("")

async def console_log(data, chat_id):
    log_name = ''
    if (chat_id == ''):
        text = '[' + str(datetime.now().date()) + ', ' + str(datetime.now().time()) + '] ' + str(data)
        log_name = ''
    elif (str(type(users_data[chat_id]['username'])) != "<class 'NoneType'>"):
        text = '[' + str(datetime.now().date()) + ', ' + str(datetime.now().time()) + '] @' + users_data[chat_id]['username'] + ': ' + str(data)
        log_name = '_@' + users_data[chat_id]['username']
    else:
        text = '[' + str(datetime.now().date()) + ', ' + str(datetime.now().time()) + '] ID' + str(chat_id) + ': ' + str(data)
        log_name = '_ID' + str(chat_id)
    with open('logs/' + launch_time + '/' + 'logs' + log_name + '.txt', 'a', encoding='utf-8') as file:
        file.write(text + '\n')



async def user_add_database(chat):
    if (chat.id not in users_data):
        users_data[chat.id] = dict([
            ('username', chat.username),
            ('details_page', 2),
            ('newsletter', 1),
            ('meals', [0, 1, 1, 0]),
            ('categories', [1, 1, 1])
        ])
        
        chats_id.append(chat.id)
        await console_log('Пользователь добавлен в датабазу', chat.id)
        await save_users()

async def load_users():
    users_data.clear()
    chats_id.clear()

    read = pandas.read_csv('users.csv', encoding='utf-8')
    
    for index in range(0, len(read)):
        users_data[int(read.iat[index,0])] = dict([])
        chats_id.append(int(read.iat[index, 0]))
        for j in range(1, 6):
            users_data[int(read.iat[index,0])][read.columns[j]] = read.iat[index,j]
            if j == 2 or j == 3:
                users_data[int(read.iat[index,0])][read.columns[j]] = int(read.iat[index,j])
            elif j == 4 or j == 5:
                users_data[int(read.iat[index,0])][read.columns[j]] = read.iat[index,j][1:len(read.iat[index,j]) - 1].split(sep=',')
                users_data[int(read.iat[index,0])][read.columns[j]] = [int(x) for x in users_data[read.iat[index,0]][read.columns[j]]]
    await console_log('Loaded users.csv', '')
    await console_log('users.csv : ' + str(users_data), '')

async def save_users():
    data = dict([
        ('chat_id', []),
        ('username', []),
        ('details_page', []),
        ('newsletter', []),
        ('meals', []),
        ('categories', []),
    ])
    for index in range(0, len(chats_id)):
        data['chat_id'].append(chats_id[index])
        for j in range(0, len(columns_csv)):
            data[columns_csv[j]].append(users_data[chats_id[index]][columns_csv[j]])
    dataframe = pandas.DataFrame({
        'chat_id': data['chat_id'],
        'username': data['username'],
        'details_page': data['details_page'],
        'newsletter': data['newsletter'],
        'meals': data['meals'],
        'categories': data['categories'],
    })
    dataframe.to_csv('users.csv', index=False)
    await console_log('Saves users.csv', '')
    
async def get_rights_user(user_id, chat_id):
    user = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
    return user.status

async def warn_havent_rights(user_id, chat_id, callback_id):
    chat = await bot.get_chat(chat_id)
    if chat.type != 'private':
        rights = await get_rights_user(user_id, chat_id)
        if rights not in ['creator', 'administrator']:
            text = '⛔ У вас нет прав для выполнения этого действия!'
            await bot.answer_callback_query(callback_query_id=callback_id, text=text, show_alert=True)
            return 1
        else:
            return 0
    else:
        return 0

async def load_data():
    global date_loaded
    with open('date_loaded.txt', 'r', encoding='utf-8') as file:
        date_loaded = file.read()

async def save_data():
    with open('date_loaded.txt', 'w', encoding='utf-8') as file:
        file.write(date_loaded)

async def condition_date():
    global date_loaded, data_food
    while True:
        if date_loaded != date.today().isoformat() or data_food == '-':
            await console_log('Пытаюсь скачать расписание ...', '')

            url = 'https://rlc-rm.gosuslugi.ru/food/' + date.today().isoformat() + '-sm.xlsx'
            exists = await check_file_exists(url)

            if (exists):
                data_food = await data_get()
                old_date = date_loaded
                date_loaded = str(date.today().isoformat())
                if (old_date != date_loaded):
                    await save_data()
                    asyncio.create_task(newsletter_send())
        await asyncio.sleep(180)

    
async def check_file_exists(url):
    try:
        response = requests.head(url, allow_redirects=True, timeout=5)
        return response.status_code in range(200, 300)
    except requests.exceptions.RequestException:
        return False

async def download_file(url):
    try:
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        df =  pandas.read_excel(
            BytesIO(response.content),
            engine='openpyxl'
        )
        await console_log('Файл успешно скачан!', '')
        return df
    except requests.exceptions.RequestException as e:
        await console_log('Ошибка скачивания файла!', '')
        return None
    except Exception as e:
        await console_log('Неизвестная ошибка при скачивании файла!', '')
        return None

async def data_get():
    url = 'https://rlc-rm.gosuslugi.ru/food/' + date.today().isoformat() + '-sm.xlsx'
    exists = await check_file_exists(url)
    if (exists):
        await console_log('Файл существует', '')
        await console_log('Скачивание файла ...', '')
        df = await download_file(url)
        data = []
        
        if df is None:
            await console_log('Не могу скачать файл', '')
            return data
        df = df.fillna('-')
        for i in range(2, df.shape[0]):
            if (str(df.iloc[i, 0]) != '-' or df.iloc[i - 1, 5] != '-'):
                data.append(dict([('dishes', []), ('drinks', []), ('other', [])]))
                
                j = i
                while df.iloc[j, 5] == '-':
                    string = '-'
                    section = '-'

                    if df.iloc[j, 3] == '-' and df.iloc[j, 1] != '-':
                        string = str(df.iloc[j, 1])
                    if df.iloc[j, 3] != '-' and df.iloc[j, 1] != '-':
                        string = str(df.iloc[j, 3])
                    section = str(df.iloc[j, 1])

                    if (string != '-'):
                        if section not in category_food or category_food[section] == 'other':
                            string = section

                        category = '-'
                        if section in category_food:
                            category = category_food[section] 
                        else:
                            category = 'other'

                        string = string.capitalize()
                        data[len(data) - 1][category].append(dict([
                            ['name', string], 
                            ['weight', df.iloc[j, 4]], 
                            ['calories', df.iloc[j, 6]],
                            ['proteins', df.iloc[j, 7]],
                            ['fats', df.iloc[j, 8]],
                            ['carbohydrates', df.iloc[j, 9]]
                        ]))
                    j += 1
        return data



async def print_category(type, data, details, chat_id):
    meal_name = meal_names_ru[type]
    meal_name = meal_name.capitalize()

    answer = '<blockquote><b>' + meal_smiles[type] + ' ' + meal_name + '</b></blockquote>\n'

    for category in range(0, 3):
        if len(data[type][category_names[category]]) > 0 and users_data[chat_id]['categories'][category]:
            category_name = category_names_ru[category]
            category_name = category_name.capitalize()
            answer += '<b>' + category_name + '</b>\n'
            for index in range(0, len(data[type][category_names[category]])):
                answer += '<b>- </b>' + str(data[type][category_names[category]][index]['name'])
                if (details):
                    answer += ' <i>(' + str(data[type][category_names[category]][index]['weight']) + ' г, ' 
                    answer += str(data[type][category_names[category]][index]['weight']) + ' калл)</i>'
                    #answer += ', БЖГ: ' + str(data[type][category_names[category]][index]['proteins']) + ' / '
                    #answer += str(data[type][category_names[category]][index]['fats']) + ' / '
                    #answer += str(data[type][category_names[category]][index]['carbohydrates'])
                answer += '\n'
    await console_log('Расписание для ' + str(meal_names_ru[type]) + ' было загружено', chat_id)
    return answer

async def load_food(category, chat_id, message, details):
    await console_log('Расписание запрошено', chat_id)

    global date_loaded, data_food

    if (message == '-'):
        loading = await bot.send_message(chat_id=chat_id, text='<i>🔃 Загружаю...</i>', parse_mode='html')
    else:
        loading = await bot.edit_message_text(chat_id=chat_id, message_id=message.id, text='<i>🔃 Загружаю...</i>', parse_mode='html')

    exists = True
    if date_loaded != date.today().isoformat() or data_food == '-':
        exists = False
    if exists:
        data = data_food
        
        text = '<b>📆 Расписание столовой ' + format_date(datetime.now(), 'd.M.YYYY', locale='ru_RU') + '</b>\n'
        for index in range(0, len(category)):
            text += await print_category(int(category[index]), data, details, chat_id) + '\n'

        markup = telebot.types.InlineKeyboardMarkup()
        if (details):
            await console_log('Детальное расписание, вкладка: ' + str(category[0] + 1), chat_id)
            
            button_count = telebot.types.InlineKeyboardButton(text=str(category[0] + 1) + ' / 4', callback_data='none')
            
            if (category[0] != 0):
                button_left = telebot.types.InlineKeyboardButton(text='⬅️', callback_data='left')
            else:
                button_left = telebot.types.InlineKeyboardButton(text=' ', callback_data='none')
           
            if (category[0] != 3):
                button_right = telebot.types.InlineKeyboardButton(text='➡️', callback_data='right')
            else:
                button_right = telebot.types.InlineKeyboardButton(text=' ', callback_data='none')
            
            button_back = telebot.types.InlineKeyboardButton(text='Обратно', callback_data='back')

            markup.row(button_count)
            markup.row(button_left, button_back, button_right)
            
            await bot.edit_message_text(chat_id=chat_id, message_id=loading.id, text=text, parse_mode='html', reply_markup=markup)
        else:
            button_details = telebot.types.InlineKeyboardButton(text='Детально', callback_data='details')
            button_back_menu = telebot.types.InlineKeyboardButton(text='Меню', callback_data='menu')
            
            markup.row(button_details, button_back_menu)
           
            await bot.edit_message_text(chat_id=chat_id, message_id=loading.id, text=text, parse_mode='html', reply_markup=markup)
    else:
        button_back_menu = telebot.types.InlineKeyboardButton(text='Меню', callback_data='menu')
        markup = telebot.types.InlineKeyboardMarkup()
        markup.row(button_back_menu)
        await bot.edit_message_text(chat_id=chat_id, message_id=loading.id, text='⛔ Расписания ещё нет!', reply_markup=markup)

@bot.message_handler(commands=['food']) 
async def main(message):
    print(2)
    await user_add_database(message.chat)
    print(3)
    if message.chat.type == 'private':
        await bot.delete_message(chat_id=message.chat.id, message_id=message.id)
    print(4)
    await console_log(str(message.text), message.chat.id)
    print(1)
    food = []
    for index in range(0, 4):
        if (users_data[message.chat.id]['meals'][index]):
            food.append(index)
    await load_food(food, message.chat.id, '-', False)
    print(4)

@bot.callback_query_handler(func=lambda callback: callback.data == 'details')
async def main(callback):
    await user_add_database(callback.message.chat)

    await load_food([users_data[callback.message.chat.id]['details_page']], callback.message.chat.id, callback.message, True)

@bot.callback_query_handler(func=lambda callback: callback.data == 'back' or callback.data == 'food')
async def main(callback):
    await user_add_database(callback.message.chat)

    food = []
    for index in range(0, 4):
        if (users_data[callback.message.chat.id]['meals'][index]):
            food.append(index)
    await load_food(food, callback.message.chat.id, callback.message, False)

@bot.callback_query_handler(func=lambda callback: callback.data == 'left')
async def main(callback):
    await user_add_database(callback.message.chat)

    users_data[callback.message.chat.id]['details_page'] -= 1
    await load_food([users_data[callback.message.chat.id]['details_page']], callback.message.chat.id, callback.message, True)

@bot.callback_query_handler(func=lambda callback: callback.data == 'right')
async def main(callback):
    await user_add_database(callback.message.chat)

    users_data[callback.message.chat.id]['details_page'] += 1
    await load_food([users_data[callback.message.chat.id]['details_page']], callback.message.chat.id, callback.message, True)



@bot.callback_query_handler(func=lambda callback: callback.data[0:4] == 'meal')
async def main(callback):
    await user_add_database(callback.message.chat)

    if not await warn_havent_rights(callback.from_user.id, callback.message.chat.id, callback.id):
        id = int(callback.data[5])
        await meal_toggle(callback.message.chat, int(not users_data[callback.message.chat.id]['meals'][id]), id)

        if users_data[callback.message.chat.id]['meals'][id]:
            await bot.answer_callback_query(callback_query_id=callback.id, text='✅ ' + meal_names_ru[id].capitalize(), show_alert=False)
        else:
            done = False
            for meal_id in range(0, 4):
                if users_data[callback.message.chat.id]['meals'][meal_id]:
                    done = True
            if (done):
                await bot.answer_callback_query(callback_query_id=callback.id, text='⛔ ' + meal_names_ru[id].capitalize(), show_alert=False)
            else:
                await meal_toggle(callback.message.chat, int(not users_data[callback.message.chat.id]['meals'][id]), id)
                await bot.answer_callback_query(callback_query_id=callback.id, text='⚠️ Необходима хотя бы одна категория!', show_alert=True)
        await settings(callback.message)

@bot.callback_query_handler(func=lambda callback: callback.data[0:8] == 'category')
async def main(callback):
    await user_add_database(callback.message.chat)

    if not await warn_havent_rights(callback.from_user.id, callback.message.chat.id, callback.id):
        id = int(callback.data[9])
        await category_toggle(callback.message.chat, int(not users_data[callback.message.chat.id]['categories'][id]), id)
        
        if users_data[callback.message.chat.id]['categories'][id]:
            await bot.answer_callback_query(callback_query_id=callback.id, text='✅ ' + category_names_ru[id].capitalize(), show_alert=False)
        else:
            done = False
            for category_id in range(0, 3):
                if users_data[callback.message.chat.id]['categories'][category_id]:
                    done = True
            if (done):
                await bot.answer_callback_query(callback_query_id=callback.id, text='⛔ ' + category_names_ru[id].capitalize(), show_alert=False)
            else:
                await category_toggle(callback.message.chat, int(not users_data[callback.message.chat.id]['categories'][id]), id)
                await bot.answer_callback_query(callback_query_id=callback.id, text='⚠️ Необходима хотя бы одна категория!', show_alert=True)
        await settings(callback.message)

@bot.callback_query_handler(func=lambda callback: callback.data == 'settings')
async def main(callback):
    await user_add_database(callback.message.chat)

    if not await warn_havent_rights(callback.from_user.id, callback.message.chat.id, callback.id):
        await settings(callback.message)

@bot.message_handler(commands = ['settings'])
async def main(message):
    await user_add_database(message.chat)
    await console_log(str(message.text), message.chat.id)
    if message.chat.type == 'private':
        await bot.delete_message(chat_id=message.chat.id, message_id=message.id)
    else:
        if await get_rights_user(message.from_user.id, message.chat.id) in ['administrator', 'creator']:
            await settings(message)

async def settings(message):
    await console_log('Настройки', message.chat.id)
    
    text = '<b>⚙️ Настройки</b>\nВ этом меню вы можете настроить необходимые для отображения элементы в расписании!'

    buttons_meal = ['','','','']
    for meal_id in range(0, 4):
        text_meal = ''
        if (users_data[message.chat.id]['meals'][meal_id]):
            text_meal = '✅ '
        else:
            text_meal = '⛔ '
        text_meal += meal_names_ru[meal_id].capitalize()

        buttons_meal[meal_id] = telebot.types.InlineKeyboardButton(text=text_meal, callback_data='meal_' + str(meal_id))
    
    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(buttons_meal[0], buttons_meal[1], buttons_meal[2], buttons_meal[3])

    buttons_category = ['', '', '']
    for category_id in range(0, 3):
        text_category = ''
        if (users_data[message.chat.id]['categories'][category_id]):
            text_category = '✅ '
        else:
            text_category = '⛔ '
        text_category += category_names_ru[category_id].capitalize()

        buttons_category[category_id] = telebot.types.InlineKeyboardButton(text=text_category, callback_data='category_' + str(category_id))
    
    markup.row(buttons_category[0], buttons_category[1], buttons_category[2])
    if message.chat.type == 'private':
        markup.row(telebot.types.InlineKeyboardButton(text='Меню', callback_data='menu'))
    
    
    if (message.from_user.id != bot.bot_id):
        await bot.send_message(chat_id=message.chat.id, text=text, parse_mode='html', reply_markup=markup)
    else:
        await bot.edit_message_text(chat_id=message.chat.id, message_id=message.id, text=text, parse_mode='html', reply_markup=markup)

async def meal_toggle(chat, value, id):
    await console_log('Отображение ' + str(meal_names_ru[id]) + ' изменено на ' + str(value), chat.id)

    users_data[chat.id]['meals'][id] = value
    await save_users()
    
async def category_toggle(chat, value, id):
    await console_log('Отображение ' + str(category_names_ru[id]) + ' изменено на ' + str(value), chat.id)

    users_data[chat.id]['categories'][id] = value
    await save_users() 



@bot.callback_query_handler(func=lambda callback: callback.data == 'newsletter')
async def main(callback):
    await user_add_database(callback.message.chat)
    
    if not await warn_havent_rights(callback.from_user.id, callback.message.chat.id, callback.id):
        await newsletter(callback.message)

@bot.message_handler(commands = ['newsletter'])
async def main(message):
    await user_add_database(message.chat)
    await console_log(str(message.text), message.chat.id)
    if message.chat.type == 'private':
        await bot.delete_message(chat_id=message.chat.id, message_id=message.id)
    else:
        if await get_rights_user(message.from_user.id, message.chat.id) in ['administrator', 'creator']:
            await newsletter(message)

@bot.callback_query_handler(func=lambda callback: callback.data == 'newsletter_toggle')
async def main(callback):
    await user_add_database(callback.message.chat)
    if not await warn_havent_rights(callback.from_user.id, callback.message.chat.id, callback.id):
        await newsletter_toggle(callback.message.chat, int(not users_data[callback.message.chat.id]['newsletter']))
        if users_data[callback.message.chat.id]['newsletter']:
            await bot.answer_callback_query(callback_query_id=callback.id, text='✅ Рассылка включена!', show_alert=False)
        else:
            await bot.answer_callback_query(callback_query_id=callback.id, text='⛔ Рассылка выключена!', show_alert=False)
        
        await newsletter(callback.message)

async def newsletter(message):
    await console_log('Рассылка', message.chat.id)
    
    text = ''
    button_newsletter_toggle = telebot.types.InlineKeyboardButton(text='-', callback_data='newsletter_toggle')
    button_back_menu = telebot.types.InlineKeyboardButton(text='Меню', callback_data='menu')
    
    if users_data[message.chat.id]['newsletter']:
        button_newsletter_toggle.text = '✅ Рассылка включена'
        text = '<b>🔔</b>'
    else:
        button_newsletter_toggle.text = '⛔ Рассылка выключена'
        text = '<b>🔕</b>'
    if message.chat.type == 'private':
        text += '<b> Рассылка</b>\nВ этом меню вы можете настроить, будут ли вам приходить уведомления о появлении актуального расписания в столовой!'
    else:
        text += '<b> Рассылка</b>\nВ этом меню вы можете настроить, будут ли в группу приходить уведомления о появлении актуального расписания в столовой!'
    
    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(button_newsletter_toggle)
    if message.chat.type == 'private':
        markup.row(button_back_menu)
    
    if (message.from_user.id != bot.bot_id):
        await bot.send_message(chat_id=message.chat.id, text=text, parse_mode='html', reply_markup=markup)
    else:
        await bot.edit_message_text(chat_id=message.chat.id, message_id=message.id, text=text, parse_mode='html', reply_markup=markup)

async def newsletter_toggle(chat, value):
    await console_log('Рассылка изменена на ' + str(value), chat.id)

    users_data[chat.id]['newsletter'] = value
    await save_users()

async def newsletter_send():
    global data_food
    await console_log('Отправка рассылки подписанным людям', '')
    
    for chat_id in chats_id:
        try:
            if not users_data[chat_id]['newsletter']:
                continue
            text = '<b>🔔 Расписание на ' + str(datetime.now().date()) + ' было получено!</b>\n\n'
            
            has_meals = False
            for index in range(0, 4):
                if users_data[chat_id]['meals'][index]:
                    has_meals = True
                    text += await print_category(index, data_food, False, chat_id)

            await asyncio.wait_for(
                bot.send_message(chat_id=chat_id, text=text, parse_mode='html'),
                timeout=10.0
            )
            await console_log('Рассылка отправлена', chat_id)
            
        except asyncio.TimeoutError:
            await console_log('Таймаут при отправке рассылки', chat_id)
            continue 
            
        except telebot.asyncio_helper.ApiTelegramException as error:
            continue
            
        except Exception as error:
            continue 
        await asyncio.sleep(0.1)
    
    await console_log('Рассылка завершена', '')



async def menu(message):
    await console_log('Меню', message.chat.id)
    
    newsletter = ''
    if (users_data[message.chat.id]['newsletter']):
        newsletter = '🔔'
    else:
        newsletter = '🔕'

    text_food = ''
    if date_loaded != date.today().isoformat() or data_food == '-':
        text_food = '⛔ Расписания нет'
    else:
        text_food = 'Расписание'

    button_newsletter = telebot.types.InlineKeyboardButton(text=newsletter + ' Рассылка', callback_data='newsletter')
    button_food = telebot.types.InlineKeyboardButton(text=text_food, callback_data='food')
    button_settings = telebot.types.InlineKeyboardButton(text='⚙️ Настройки', callback_data='settings')
    
    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(button_food)
    if message.chat.type == 'private':
        markup.row(button_newsletter, button_settings)

    text = 'Этот бот позволяет узнавать об актуальном расписании в столовой на сегодня!'
    if message.chat.type == 'private':
        text = '👋 Привет, <b>@' + message.chat.username + '</b>!\n' + text
    else:
        text = '👋 Привет!\n' + text

    if (message.from_user.id != bot.bot_id):
        await bot.send_message(chat_id=message.chat.id, text=text,  parse_mode = 'html', reply_markup=markup) 
    else:
        await bot.edit_message_text(chat_id=message.chat.id, message_id=message.id, text=text,  parse_mode = 'html', reply_markup=markup) 

@bot.message_handler(commands = ['start', 'menu', 'help'])
async def main(message):
    await user_add_database(message.chat)
    await console_log(str(message.text), message.chat.id)
    
    if message.chat.type == 'private':
        await bot.delete_message(chat_id=message.chat.id, message_id=message.id)

    await menu(message)

@bot.callback_query_handler(func=lambda callback: callback.data == 'menu')
async def main(callback):
    await user_add_database(callback.message.chat)

    await menu(callback.message)



@bot.message_handler(func=lambda message: message.chat.type == 'private')
async def main(message):
    await user_add_database(message.chat)
    await bot.delete_message(chat_id=message.chat.id, message_id=message.id)

async def start():
    global launch_time, version
    launch_time = str(datetime.now().date()) + '_' + str(datetime.now().strftime("%H-%M-%S"))

    os.makedirs("logs/" + launch_time)

    await console_log('@CENTERODFOODBOT ver. ' + str(version) + ', ' + str(datetime.now().date()), '')
    await load_users()
    await load_data()
    asyncio.create_task(condition_date())

    await bot.polling()

if __name__ == "__main__":
    asyncio.run(start())
    



