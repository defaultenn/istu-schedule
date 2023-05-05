from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder, 
    CommandHandler, 
    filters,
    MessageHandler,
    CallbackContext, CallbackQueryHandler
)
from telegram._update import Update
from telegram.ext._extbot import ExtBot
import csv, os, io, datetime
from typing import List
from datetime import datetime
import math

# pip install python-telegram-bot --upgrade - перед запуском
bot_token = 'токен сюда'

weekdays_verbose = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота']
# начальная неделя над чертой
start_week = datetime(2023, 5, 1, 0, 0, 0, 0)

def get_university_names():
    return list(map(lambda x: x.split('.')[0],os.listdir('data')))

def get_groups(university_name: str) -> List[str]:
    with io.open(f'data/{university_name}.csv', 'r', newline='', encoding='utf8') as csvfile:
        spamreader = csv.reader(csvfile, delimiter=';')
        data = [row for row in spamreader]
        groups = [value[0].strip() for value in data[::9]]
        csvfile.close()
    return groups

def get_sublists(original_list, number_of_sub_list_wanted) -> List:
    sublists = list()
    for sub_list_count in range(number_of_sub_list_wanted): 
        sublists.append(original_list[sub_list_count::number_of_sub_list_wanted])
    return sublists

def get_keyboard(buttons: List[str] = None, type: str = None, extra: List[str] = []):
    keyboard_buttons = []
    if(buttons and type):
        keyboard_buttons = list(
            map(
                lambda button_str: InlineKeyboardButton(
                    text=button_str, 
                    callback_data=f'{type}:{button_str}:{":".join(extra)}' if extra else f'{type}:{button_str}'
                ), buttons
            )
        )
    if(len(extra) > 0):
        if(type == 'period'):
            callback_data = f'university:{extra[-2]}'
        elif(type == 'group'):
            callback_data = f'start'
        elif(type == None):
            callback_data = f'group:{":".join(reversed(extra))}'
        extra.remove(extra[-1])
        if(len(extra) > 0):
            callback_data += f':{":".join(extra)}'
    else:
        callback_data = 'start'

    if(not type == 'university'):
        keyboard_buttons.append(
            InlineKeyboardButton(
                text='Назад', 
                callback_data=callback_data
            )
        )
    return get_sublists(keyboard_buttons, 2)

async def handle_start(update: Update, context: CallbackContext):
    names = get_university_names()
    keyboard = get_keyboard(names, 'university')
    bot: ExtBot = context.bot
    await bot.send_message(
        chat_id=update.effective_chat.id,
        text='Выберите институт:',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

def get_week_description():
    return 'Неделя под чертой' if isOver() else 'Неделя над чертой'

async def start(update: Update, context: CallbackContext):
    await handle_start(update, context)

def isOver():
    delta = datetime.now() - start_week
    return round(math.modf(delta.days / 7)[1] % 2)

def get_couple_with_week(parsable: str):
    return parsable.split('/')[int(isOver())]

def get_schedule(university: str, group: str, period: str):
    with io.open(f'data/{university}.csv', 'r', newline='', encoding='utf8') as csvfile:
        spamreader = csv.reader(csvfile, delimiter=';')
        data = [row for row in spamreader]
        groups = [value[0].strip() for value in data[::9]]
        group_index = groups.index(group)
        data = data[group_index * 9 + 1:(group_index + 1) * 9]
        csvfile.close()

    weekday = datetime.now().weekday() % 7
    
    if(period == 'Сегодня'):
        if(weekday == 6):
            return 'Отдыхай!'
        return [
            weekdays_verbose[weekday],
            *[f'{index + 1}. {get_couple_with_week(row[weekday + 1])}' for index, row in enumerate(data)],
            get_week_description()
        ]
    elif(period == 'Завтра'):
        if((weekday + 1) == 6):
            return f'Отдыхай! {weekday}'
        return [
            weekdays_verbose[weekday + 1],
            *[f'{index + 1}. {get_couple_with_week(row[weekday + 1])}' for index, row in enumerate(data)],
            get_week_description()
        ]
    elif(period == 'На неделю'):
        result = []
        for day in range(6):
            result = [
                *result,
                *[
                    weekdays_verbose[day], 
                    *[f'{index + 1}. {get_couple_with_week(row[day])}' for index, row in enumerate(data)],
                    '\n'
                ]
            ]
        result.append(get_week_description())
        return result
    else:
        return []



async def handle(update: Update, context: CallbackContext):
    query = update.callback_query
    query_data = query.data
    type = query_data.split(":")[0]

    try:
        data = query_data.split(":")[1]
        await query.answer()
        await query.edit_message_text(text=f'Выбран: {data}')
    except:
        await query.delete_message()
        return await handle_start(update, context)

    
    async def handle_university_type():
        # university:институт3
        groups = get_groups(data)
        if(len(groups) == 0):
            keyboard = get_keyboard()
            return await context.bot.send_message(
                chat_id=update.effective_chat.id, 
                text="У университета нет групп.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        keyboard = get_keyboard(
            groups, 
            'group',
            [data]
        )
        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text="Выберите группу:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    async def handle_group_type():
        # group:20-191-1:институт3
        university = query_data.split(':')[2]
        keyboard = get_keyboard([
                'Сегодня',
                'Завтра',
                'На неделю'
            ], 
            'period',
            [university, data]
        )
        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text="Выберите период:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    async def handle_period_type():
        # period:Сегодня:институт3:20-191-1
        university = query_data.split(':')[2]
        group = query_data.split(':')[3]
        schedule = get_schedule(university, group, data)
        if(isinstance(schedule, list)):
            schedule = '\n'.join(schedule)
        keyboard = get_keyboard(extra=[university, group])
        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text=schedule,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    if(type == 'university'):
        await handle_university_type()
    elif(type == 'group'):
        await handle_group_type()
    elif(type == 'period'):
        await handle_period_type()
        
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text="Я не понимаю команду, что Вы от меня хотите."
        )

app = ApplicationBuilder().token(bot_token).build()
app.add_handler(CommandHandler('start', start))
app.add_handler(CallbackQueryHandler(handle))
app.run_polling()