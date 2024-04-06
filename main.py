import requests
import sqlite3
import json

import datetime

from colorama import init, Fore, Style
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram.client.session.aiohttp import AiohttpSession

init()

# session = AiohttpSession(proxy="http://proxy.server:3128")
bot_token = 'bot_token'
bot = Bot(bot_token)  # bot = Bot(bot_token, session=session)
dp = Dispatcher()


def name_fuc(username, name):
    return username if username is not None else name


def sql_launch():
    connection = sqlite3.connect('pythonanywhere.db')
    cursor = connection.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user (
        id INT,
        username TEXT,
        token TEXT
        )
        ''')
    connection.commit()
    connection.close()


def sql_token_and_username(user_id):
    connection = sqlite3.connect('pythonanywhere.db')
    cursor = connection.cursor()

    cursor.execute(f"SELECT * FROM user WHERE id = {user_id}")
    row = cursor.fetchone()
    connection.close()

    if row is None or row[2] == 'None':
        return ['None', 'None']
    else:
        return row[1], row[2]


def sql_change(user_id, username, token):
    connection = sqlite3.connect('pythonanywhere.db')
    cursor = connection.cursor()

    cursor.execute(f"SELECT * FROM user WHERE id = {user_id}")
    row = cursor.fetchone()

    if row is None:
        cursor.execute(f"INSERT INTO user(id, username, token) VALUES ({user_id}, '{username}', '{token}')")
    elif token == 'None':
        cursor.execute(f"UPDATE user SET (username, token) = ('None', 'None') WHERE id = {user_id}")
    else:
        cursor.execute(f"UPDATE user SET (username, token) = ('{username}', '{token}') WHERE id = {user_id}")

    connection.commit()
    connection.close()


@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    name = name_fuc(message.from_user.username, message.from_user.full_name)
    await message.answer(f'Hello, {name}')


@dp.message(Command('setting'))
async def command_setting(message: Message) -> None:
    user_id = message.from_user.id
    username, token = sql_token_and_username(user_id)
    await message.answer('This is your settings. You need to provide your username and API token to retrieve the data.' 
                         f'\nid: {user_id}' 
                         f'\nusername: {username}'
                         f'\ntoken: {token}\n\n'
                         'To change username and token, send the /change command. If you want to delete the data, '
                         'send the /delete_data command')


fsm_by_lazy = dict()


@dp.message(Command('change'))
async def command_change(message: Message) -> None:
    await message.answer('Enter username')
    global fsm_by_lazy
    fsm_by_lazy[str(message.from_user.id)] = [None, None]


@dp.message(Command('delete_data'))
async def command_delete_data(message: Message) -> None:
    user_id = message.from_user.id
    sql_change(user_id, None, None)
    await message.answer('The data has been deleted')


@dp.message(Command('consoles'))
async def command_consoles(message: Message) -> None:
    pass


@dp.message()
async def main_handler(message: types.Message) -> None:

    global fsm_by_lazy
    user_id = message.from_user.id

    if str(user_id) in fsm_by_lazy.keys():
        ut_list = fsm_by_lazy[str(user_id)]
        if ut_list[0] is None:
            fsm_by_lazy[str(user_id)] = [message.text, None]
            await message.answer('Enter token')
        else:
            sql_change(user_id, ut_list[0], message.text)
            username, token = sql_token_and_username(user_id)

            response = requests.get(f'https://www.pythonanywhere.com/api/v0/user/{username}/cpu/',
                                    headers={'Authorization': f'Token {token}'})
            if response.status_code != 200:
                await message.answer('Invalid token or username. Make sure you have entered everything correctly. '
                                     'Try again: /change')
                sql_change(user_id, None, None)
            else:
                await message.answer('Success. Data saved')
            fsm_by_lazy.pop(str(user_id))
        return

    await main_start(user_id)


async def main_start(user_id):

    username, token = sql_token_and_username(user_id)
    response = requests.get(f'https://www.pythonanywhere.com/api/v0/user/{username}/cpu/',
                            headers={'Authorization': f'Token {token}'})
    if response.status_code == 200:
        parsed_data = json.loads(response.content)

        cpu_limit = parsed_data['daily_cpu_limit_seconds']
        cpu_usage = parsed_data['daily_cpu_total_usage_seconds']
        reset_time = parsed_data['next_reset_time']

        cpu_percent = (cpu_usage / cpu_limit) * 100

        reset_datetime = datetime.datetime.fromisoformat(reset_time.replace('T', ' ')).replace(tzinfo=datetime.timezone.utc)
        now = datetime.datetime.now(datetime.timezone.utc)
        time_until_reset = reset_datetime - now

        hours = int(time_until_reset.total_seconds() // 3600)
        minutes = int((time_until_reset.total_seconds() % 3600) // 60)

        if hours != 0:
            time = f'{hours} hours, {minutes} minutes'
        else:
            time = f'{minutes} minutes'
        result = f"{cpu_percent:.0f}% used – {cpu_usage:.2f}s of {cpu_limit}s. Resets in {time}"
        await bot.send_message(user_id, f'CPU Usage: {result}')

    else:
        error = str(response.content)
        error = error[error.find(":") + 2:error.rfind('"') - 1]
        await bot.send_message(user_id, f'Error {response.status_code}: {error}')

if __name__ == '__main__':
    sql_launch()
    print(f'The bot {Fore.RED}launches{Style.RESET_ALL} at {datetime.datetime.now().strftime("%H:%M:%S %d.%m.%Y")}')
    dp.run_polling(bot)
