import requests
import sqlite3
import json

import datetime

from colorama import init, Fore, Style
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.client.session.aiohttp import AiohttpSession

from sql import sql_launch, sql_change, sql_token_and_username
init()

# session = AiohttpSession(proxy="http://proxy.server:3128")
bot_token = 'bot_token'
bot = Bot(bot_token)  # bot = Bot(bot_token, session=session)
dp = Dispatcher()
fsm_by_lazy = []


def name_fuc(username, name):
    return username if username is not None else name


def cpu(username, token):

    response = requests.get(f'https://www.pythonanywhere.com/api/v0/user/{username}/cpu/',
                                headers={'Authorization': f'Token {token}'})
    if response.status_code == 200:
        parsed_data = json.loads(response.content)

        cpu_limit = parsed_data['daily_cpu_limit_seconds']
        cpu_usage = parsed_data['daily_cpu_total_usage_seconds']
        reset_time = parsed_data['next_reset_time']

        cpu_percent = (cpu_usage / cpu_limit) * 100

        reset_datetime = datetime.datetime.fromisoformat(reset_time.replace('T', ' ')).replace(
                tzinfo=datetime.timezone.utc)
        now = datetime.datetime.now(datetime.timezone.utc)
        time_until_reset = reset_datetime - now

        hours = int(time_until_reset.total_seconds() // 3600)
        minutes = int((time_until_reset.total_seconds() % 3600) // 60)

        if hours != 0:
            time = f'{hours} hours, {minutes} minutes'
        else:
            time = f'{minutes} minutes'

        return f"{cpu_percent:.0f}% used – {cpu_usage:.2f}s of {cpu_limit}s. Resets in {time}"

    else:
        return 'error'


def consoles_info(username, token):
    response = requests.get(
        f'https://www.pythonanywhere.com/api/v0/user/{username}/consoles/',
        headers={'Authorization': f'Token {token}'})

    if response.status_code == 200:
        parsed_data = json.loads(response.content)
        result = ''

        if len(parsed_data) == 0:
            return 'You have no consoles.', False

        inline_list = []
        for console in parsed_data:
            name = console['name']
            console_id = console['id']
            console_url = 'https://www.pythonanywhere.com' + console['console_url']
            result += f'\n[{name}]({console_url}) - `{console_id}`'
            inline_list.append(InlineKeyboardButton(text=name,
                                                    callback_data=f'consoles-{console_id}'))

        return result, inline_list
    else:
        return 'error', False


def always_on_info(username, token):
    response = requests.get(
        f'https://www.pythonanywhere.com/api/v0/user/{username}/always_on/',
        headers={'Authorization': f'Token {token}'})

    if response.status_code == 200:
        parsed_data = json.loads(response.content)
        result = ''

        if len(parsed_data) == 0:
            return '\nYou have no tasks yet.', False

        inline_list = []
        for always_on in parsed_data:
            command = always_on['command']
            description = always_on['description']
            always_on_id = always_on['id']
            url = 'https://www.pythonanywhere.com' + always_on['url']
            result += f'\n[{command}]({url})({description}) - `{always_on_id}`'
            inline_list.append(InlineKeyboardButton(text=command,
                                                    callback_data=f'always_on-{always_on_id}'))

        return result, inline_list
    else:
        return '\nerror', False



@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    name = name_fuc(message.from_user.username, message.from_user.full_name)
    await message.answer(f'Hello, {name}')
    print(f'start by {message.from_user.username}')


@dp.message(Command('setting'))
async def command_setting(message: Message) -> None:
    user_id = message.from_user.id
    username, token = sql_token_and_username(user_id)
    await bot.send_message(user_id, text='This is your settings. You need to provide your username and API token to retrieve the data.' 
                         f'\nid: {user_id}' 
                         f'\nusername: {username}'
                         f'\ntoken: `{token}`\n\n'
                         f'To change username and token, send the /change command. If you want to delete the data, send the /deletedata command', parse_mode='Markdown')
    print(f'setting by {message.from_user.username}')


@dp.message(Command('change'))
async def command_change(message: Message) -> None:
    await message.answer('Send your username and token. Please use this format:\nusername - token')
    global fsm_by_lazy
    fsm_by_lazy.append(message.from_user.id)
    print(f'change by {message.from_user.username}')


@dp.message(Command('deletedata'))
async def command_delete_data(message: Message) -> None:
    user_id = message.from_user.id
    sql_change(user_id, None, None)
    await message.answer('The data has been deleted')
    print(f'deletedata by {message.from_user.username}')


@dp.message(Command('consoles'))
async def command_consoles(message: Message) -> None:
    pass


@dp.callback_query(F.data)
async def callback_data(callback: types.CallbackQuery):
    data = callback.data
    user_id = callback.from_user.id

    if data[:6] == 'update':
        from random import randint
        username, token = sql_token_and_username(user_id)

        cpu_result = cpu(username, token)
        if cpu_result != 'error':
            consoles_result, inline_consoles = consoles_info(username, token)
            always_on_result, inline_always_on = always_on_info(username, token)
            inline_update = [InlineKeyboardButton(text='Update', callback_data='update')]
            inline_keyboard = [inline_update]
            if inline_consoles:
                inline_keyboard.append(inline_consoles)
            if inline_always_on:
                inline_keyboard.append(inline_always_on)
            message_id = callback.message.message_id
            await bot.edit_message_text(chat_id=user_id, message_id=message_id, text=f'*CPU Usage:* {cpu_result}\n\n'
                                        f'*Your consoles:*{consoles_result}\n\n'
                                        f'*Always-on tasks:*{always_on_result}\n\n'
                                        f'Updated at {datetime.datetime.now(datetime.timezone.utc).strftime("%H:%M:%S %d.%m.%Y")}',
                                        parse_mode='Markdown', disable_web_page_preview=True,
                                        reply_markup=InlineKeyboardMarkup(inline_keyboard=inline_keyboard))
        else:
            await bot.edit_message_text(text=f'error')

    if data[:8] == 'consoles':
        data = data[9:]

    await callback.answer()


@dp.message()
async def main_handler(message: types.Message) -> None:
    print(f'message by {message.from_user.username}')
    global fsm_by_lazy
    user_id = message.from_user.id
    if user_id in fsm_by_lazy:
        username, token = message.text.split(' - ')
        response = requests.get(
            f'https://www.pythonanywhere.com/api/v0/user/{username}/consoles/',
            headers={'Authorization': f'Token {token}'})

        if response.status_code == 200:
            sql_change(user_id, username, token)
            await bot.send_message(user_id, 'Data saved')
        else:
            await bot.send_message(user_id, 'Incorrect input')
        fsm_by_lazy.remove(user_id)
        return

    username, token = sql_token_and_username(user_id)

    cpu_result = cpu(username, token)

    if cpu_result != 'error':
        consoles_result, inline_consoles = consoles_info(username, token)
        always_on_result, inline_always_on = always_on_info(username, token)
        inline_update = [InlineKeyboardButton(text='Update', callback_data='update')]
        inline_keyboard = [inline_update]
        if inline_consoles:
            inline_keyboard.append(inline_consoles)
        if inline_always_on:
            inline_keyboard.append(inline_always_on)
        await bot.send_message(user_id, f'*CPU Usage:* {cpu_result}\n\n'
                                        f'*Your consoles:*{consoles_result}\n\n'
                                        f'*Always-on tasks:*{always_on_result}',
                               parse_mode='Markdown', disable_web_page_preview=True,
                               reply_markup=InlineKeyboardMarkup(inline_keyboard=inline_keyboard))
    else:
        await bot.send_message(user_id, 'Error')




if __name__ == '__main__':
    sql_launch()
    print(f'The bot {Fore.RED}launches{Style.RESET_ALL} at {datetime.datetime.now().strftime("%H:%M:%S %d.%m.%Y")}')
    dp.run_polling(bot)
    
