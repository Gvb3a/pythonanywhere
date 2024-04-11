import requests
import json
import datetime
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from sql import sql_username_and_token


def cpu(username, token):

    response = requests.get(f'https://www.pythonanywhere.com/api/v0/user/{username}/cpu/',
                                headers={'Authorization': f'Token {token}'})
    if response.status_code == 200:
        parsed_data = json.loads(response.content)

        cpu_limit = parsed_data['daily_cpu_limit_seconds']
        cpu_usage = parsed_data['daily_cpu_total_usage_seconds']
        reset_time = parsed_data['next_reset_time']

        cpu_percent = (cpu_usage / cpu_limit) * 100

        reset_datetime = datetime.datetime.fromisoformat(reset_time.replace('T', ' ')).replace(tzinfo=datetime.timezone.utc)
        time_until_reset = reset_datetime - datetime.datetime.now(datetime.timezone.utc)

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


def consoles(console_id, username, token):
    response = requests.get(
        f'https://www.pythonanywhere.com/api/v0/user/{username}/consoles/{console_id}',
        headers={'Authorization': f'Token {token}'})

    if response.status_code == 200:
        data = json.loads(response.content)
        user = data['user']
        name = data['name']
        executable = data['executable']
        arguments = data['arguments']
        working_directory = data['working_directory']
        arguments_text = f'\narguments: {arguments}' if arguments != '' else ''
        working_directory_text = f'\nworking directory: {working_directory}' if str(working_directory) != 'None' else ''
        console_url = 'https://www.pythonanywhere.com/' + data['console_url']
        info_result = (f'[{name}]({console_url}) - `{console_id}`'
                       f'\nuser: {user}'
                       f'\nexecutable: {executable}'
                       f'{arguments_text}{working_directory_text}\n')

        get_latest_output = requests.get(
            f'https://www.pythonanywhere.com/api/v0/user/{username}/consoles/{console_id}/get_latest_output',
            headers={'Authorization': f'Token {token}'})
        output_data = json.loads(get_latest_output.content)
        output = output_data['output']
        count = 4096 - len(info_result)
        while len(output) >= count:
            output = output[len(output_data)-count:]

        output_result = '\nLatest output:\n```shell\n' + output + '```'

        inline_update = InlineKeyboardButton(text='Update', callback_data=f'consoles-{console_id}')
        inline_delete = InlineKeyboardButton(text='Delete', callback_data=f'delete-consoles-{console_id}')
        inline_back = InlineKeyboardButton(text='Backward', callback_data='update')
        inline_keyboard = InlineKeyboardMarkup(inline_keyboard=[[inline_update], [inline_delete], [inline_back]])

        result = info_result + output_result

        return result, inline_keyboard

    else:
        return 'Error',  InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Backward', callback_data='update')]])
