import requests
import datetime

from aiogram import Bot, Dispatcher, types, F
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state, State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.session.aiohttp import AiohttpSession

from sql import sql_launch, sql_change, sql_username_and_token
from function import cpu, consoles_info, always_on_info, consoles, shared_with_you_info, consoles_send_input, always_on
from config import bot_token, start_message

# session = AiohttpSession(proxy="http://proxy.server:3128")
bot = Bot(bot_token)  # bot = Bot(bot_token, session=session)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)


class FSMFillForm(StatesGroup):
    fill_change = State()
    fill_send_input = State()

fsm_dict = dict()


def print_fuc(message, name, username):
    print(f'{message} by {name}({username}) at {datetime.datetime.now().strftime("%H:%M:%S")}')


@dp.message(CommandStart())  # start command processing
async def command_start_handler(message: Message) -> None:
    name = message.from_user.full_name  # name recognition
    print_fuc('/start', name, message.from_user.username)
    await message.answer(f'Hello, {name}. \n{start_message}', parse_mode='Markdown')  # send a message


@dp.message(Command('setting'))  # setting command processing
async def command_setting(message: Message) -> None:
    user_id = message.from_user.id  # recognise the id
    print_fuc('/setting', message.from_user.full_name, message.from_user.username)
    # from the database (by id) find out token and username (pythonanywhere, not telegram)
    username, token = sql_username_and_token(user_id)
    await bot.send_message(user_id, text=
                          'This is your settings. You need to provide your username and API token to retrieve the data.' 
                          f'\nid: {user_id}' 
                          f'\nusername: {username}'
                          f'\ntoken: `{token}`\n\n'
                          f'To change username and token, send the /change command. If you want to delete the data, '
                          f'send the /deletedata command', parse_mode='Markdown')


@dp.message(Command('change'))
async def command_change(message: Message, state: FSMContext) -> None:
    print_fuc('/change', message.from_user.full_name, message.from_user.username)
    await message.answer('Send your username and token. Please use this format:\nusername - token')
    await state.set_state(FSMFillForm.fill_change)


@dp.message(Command('deletedata'))
async def command_delete_data(message: Message) -> None:
    print_fuc('/deletedata', message.from_user.full_name, message.from_user.username)
    user_id = message.from_user.id
    sql_change(user_id, None, None)
    await message.answer('The data has been deleted')


@dp.message(Command('cancel'), StateFilter(default_state))
async def command_cancel_default_state(message: Message):
    print_fuc('/cancel(nothing to cancel)', message.from_user.full_name, message.from_user.username)
    await message.answer('There\'s nothing to cancel. You\'re outside the state machine')


@dp.message(Command('cancel'), ~StateFilter(default_state))
async def command_cancel(message: Message, state: FSMContext):
    print_fuc('/cancel(got out)', message.from_user.full_name, message.from_user.username)
    await message.answer('You got out of the state machine')
    await state.clear()


@dp.message(Command('consoles'))
async def command_consoles(message: Message) -> None:
    pass


def main_info(username, token):

    cpu_result = cpu(username, token)

    inline_update = [InlineKeyboardButton(text='Update', callback_data='update')]

    if cpu_result != 'error':

        consoles_result, inline_consoles = consoles_info(username, token)
        always_on_result, inline_always_on = always_on_info(username, token)
        shared_with_you_result = shared_with_you_info(username, token)

        inline_keyboard = [inline_update]
        if inline_consoles:
            inline_keyboard.append(inline_consoles)
        if inline_always_on:
            inline_keyboard.append(inline_always_on)

        text = (f'*CPU Usage:* {cpu_result}\n\n'
                f'*Always-on tasks:*{always_on_result}\n\n'
                f'*Your consoles:*{consoles_result}\n\n'
                f'*Consoles shared with you:*{shared_with_you_result}\n\n'
                f'Updated at {datetime.datetime.now(datetime.timezone.utc).strftime("%H:%M:%S %d.%m.%Y")}')
        inline_keyboard = InlineKeyboardMarkup(inline_keyboard=inline_keyboard)
        return text, inline_keyboard

    else:
        return 'error', InlineKeyboardMarkup(inline_keyboard=[inline_update])


@dp.callback_query(F.data)
async def callback_data(callback: types.CallbackQuery, state: FSMContext):
    data = callback.data
    print_fuc(f'callback {data}', callback.from_user.full_name, callback.from_user.username)
    user_id = callback.from_user.id
    message_id = callback.message.message_id
    username, token = sql_username_and_token(user_id)
    data = data.split('-')
    call = data[0]
    callback_answer_text = ''
    show_alert = False

    if call == 'update':
        text, inline_keyboard = main_info(username, token)
        await bot.edit_message_text(chat_id=user_id, message_id=message_id, text=text, parse_mode='Markdown',
                                    disable_web_page_preview=True, reply_markup=inline_keyboard)

    elif call == 'consoles':
        console_id = data[1]
        result, inline_keyboard = consoles(console_id, username, token)
        await bot.edit_message_text(chat_id=user_id, message_id=message_id, text=result + f'\nUpdated at '
                                                                                          f'{datetime.datetime.now(datetime.timezone.utc).strftime("%H:%M:%S %d.%m.%Y")}',
                                    parse_mode='Markdown', disable_web_page_preview=True, reply_markup=inline_keyboard)

    elif call == 'always_on':
        always_on_id = data[1]
        result, inline_keyboard = always_on(always_on_id, username, token)
        await bot.edit_message_text(chat_id=user_id, message_id=message_id, text=result,
                                    parse_mode='HTML', disable_web_page_preview=True, reply_markup=inline_keyboard)

    elif call == 'delete':
        what_we_remove, object_id = data[1], data[2]
        response = requests.delete(f'https://www.pythonanywhere.com/api/v0/user/{username}/{what_we_remove}/{object_id}',
                                headers={'Authorization': f'Token {token}'})

        if response.status_code == 204:
            if what_we_remove == 'consoles':
                what_we_remove = 'console'
            else:
                what_we_remove = 'always-on task'
            text, inline_keyboard = main_info(username, token)
            await bot.edit_message_text(chat_id=user_id, message_id=message_id, text=text, parse_mode='Markdown',
                                        disable_web_page_preview=True, reply_markup=inline_keyboard)
            callback_answer_text = f'The {what_we_remove} has been successfully delete✅'
        else:
            callback_answer_text = 'Error'
            show_alert = True

    elif call == 'send_input':
        await bot.send_message(chat_id=user_id, text='"type" into the console. Add a "\\n" for return.')
        await state.set_state(FSMFillForm.fill_send_input)
        global fsm_dict
        fsm_dict[str(user_id)] = data[1]

    await callback.answer(callback_answer_text, show_alert=show_alert)


@dp.message(StateFilter(FSMFillForm.fill_change))
async def process_name_sent(message: Message, state: FSMContext):
    print_fuc('message(change)', message.from_user.full_name, message.from_user.username)
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


@dp.message(StateFilter(FSMFillForm.fill_send_input))
async def send_input(message: Message, state: FSMContext):
    text = message.text
    global fsm_dict
    user_id = str(message.from_user.id)
    console_id = fsm_dict[user_id]
    username, token = sql_username_and_token(message.from_user.id)
    await message.answer(text=consoles_send_input(username, token, console_id, text))
    fsm_dict.pop(user_id)
    await state.clear()


@dp.message(StateFilter(default_state))
async def main_handler(message: types.Message) -> None:
    print_fuc('message', message.from_user.full_name, message.from_user.username)
    user_id = message.from_user.id

    username, token = sql_username_and_token(user_id)

    text, inline_keyboard = main_info(username, token)
    await bot.send_message(user_id, text=text, parse_mode='Markdown',
                           disable_web_page_preview=True, reply_markup=inline_keyboard)


if __name__ == '__main__':
    sql_launch()
    print(f'The bot launches at {datetime.datetime.now().strftime("%H:%M:%S %d.%m.%Y")}')
    dp.run_polling(bot)
    
