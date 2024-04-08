import requests
import datetime

from aiogram import Bot, Dispatcher, types, F
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state, State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.session.aiohttp import AiohttpSession


from sql import sql_launch, sql_change, sql_token_and_username
from function import cpu, consoles_info, always_on_info
from config import bot_token, start_message

# session = AiohttpSession(proxy="http://proxy.server:3128")
bot = Bot(bot_token)  # bot = Bot(bot_token, session=session)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)


class FSMFillForm(StatesGroup):
    fill_change = State()


def print_fuc(message, name):
    print(f'{message} by {name} at {datetime.datetime.now().strftime("%H:%M:%S")}')


@dp.message(CommandStart())  # start command processing
async def command_start_handler(message: Message) -> None:
    name = f'{message.from_user.full_name}({message.from_user.username})'
    await message.answer(f'Hello, {message.from_user.full_name}. \n{start_message}', parse_mode='Markdown')  # send a message
    print_fuc('/start', name)  # output the information that there was a request to the console


@dp.message(Command('setting'))
async def command_setting(message: Message) -> None:
    user_id = message.from_user.id
    name = f'{message.from_user.full_name}({message.from_user.username})'
    username, token = sql_token_and_username(user_id)
    await bot.send_message(user_id, text=
                         'This is your settings. You need to provide your username and API token to retrieve the data.' 
                         f'\nid: {user_id}' 
                         f'\nusername: {username}'
                         f'\ntoken: `{token}`\n\n'
                         f'To change username and token, send the /change command. If you want to delete the data, '
                         f'send the /deletedata command', parse_mode='Markdown')
    print_fuc('/setting', name)


@dp.message(Command('change'))
async def command_change(message: Message, state: FSMContext) -> None:
    name = f'{message.from_user.full_name}({message.from_user.username})'
    await message.answer('Send your username and token. Please use this format:\nusername - token')
    await state.set_state(FSMFillForm.fill_change)
    print_fuc('/change', name)


@dp.message(Command('deletedata'))
async def command_delete_data(message: Message) -> None:
    name = f'{message.from_user.full_name}({message.from_user.username})'
    user_id = message.from_user.id
    sql_change(user_id, None, None)
    await message.answer('The data has been deleted')
    print_fuc('/deletedata', name)


@dp.message(Command('cancel'), StateFilter(default_state))
async def command_cancel_default_state(message: Message):
    name = f'{message.from_user.full_name}({message.from_user.username})'
    await message.answer('There\'s nothing to cancel. You\'re outside the state machine')
    print_fuc('/cancel(nothing to cancel)', name)


@dp.message(Command('cancel'), ~StateFilter(default_state))
async def command_cancel(message: Message, state: FSMContext):
    name = f'{message.from_user.full_name}({message.from_user.username})'
    await message.answer('You got out of the state machine')
    await state.clear()
    print_fuc('/cancel(got out)', name)

@dp.message(Command('consoles'))
async def command_consoles(message: Message) -> None:
    pass


@dp.callback_query(F.data)
async def callback_data(callback: types.CallbackQuery):
    data = callback.data
    name = f'{callback.from_user.full_name}({callback.from_user.username})'
    user_id = callback.from_user.id

    if data[:6] == 'update':
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
    print_fuc(f'callback {data}', name)


@dp.message(StateFilter(FSMFillForm.fill_change))
async def process_name_sent(message: Message, state: FSMContext):
    name = f'{message.from_user.full_name}({message.from_user.username})'
    username, token = message.text.split(' - ')
    user_id = message.from_user.id
    response = requests.get(
        f'https://www.pythonanywhere.com/api/v0/user/{username}/consoles/',
        headers={'Authorization': f'Token {token}'})

    if response.status_code == 200:
        sql_change(user_id, username, token)
        await bot.send_message(user_id, 'Data saved')
    else:
        await bot.send_message(user_id, 'Incorrect input')
    await state.clear()
    print_fuc('message(change)', name)


@dp.message(StateFilter(default_state))
async def main_handler(message: types.Message) -> None:
    name = f'{message.from_user.full_name}({message.from_user.username})'
    user_id = message.from_user.id

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

    print_fuc('message', name)



if __name__ == '__main__':
    sql_launch()
    print(f'The bot launches at {datetime.datetime.now().strftime("%H:%M:%S %d.%m.%Y")}')
    dp.run_polling(bot)
