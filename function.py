import requests
import json
import datetime
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


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
        data = json.loads(response.content)
        result = ''

        if len(data) == 0:
            return '\nYou have no consoles.', False

        inline_list = []
        for console in data:
            name = console['name']
            console_id = console['id']
            console_url = 'https://www.pythonanywhere.com' + console['console_url']
            result += f'\n[{name}]({console_url})'
            inline_list.append(InlineKeyboardButton(text=name,
                                                    callback_data=f'consoles-{console_id}'))
        return result, inline_list
    else:
        return '\nError', False


def shared_with_you_info(username, token):
    response = requests.get(
        f'https://www.pythonanywhere.com/api/v0/user/{username}/consoles/shared_with_you',
        headers={'Authorization': f'Token {token}'})

    if response.status_code == 200:
        data = json.loads(response.content)

        if len(data) == 0:
            return '\nNo-one has shared any consoles with you :-('

        result = ''
        for console in data:
            name = console['name']
            console_id = console['id']
            console_url = 'https://www.pythonanywhere.com' + console['console_url']
            user = console['user']
            result += f'\n[{name}]({console_url})({user}) - `{console_id}`'

        return result
    else:
        return '\nError'


def consoles_send_input(username, token, console_id, text):
    response = requests.post(
        f'https://www.pythonanywhere.com/api/v0/user/{username}/consoles/{console_id}/send_input/',
        headers={'Authorization': f'Token {token}'},
        data={'input': text}
    )
    if response.status_code == 200:
        return 'Success✅'
    else:
        return 'Error'


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
            description_result = f'({description})' if description != '' else ''
            always_on_id = always_on['id']
            url = 'https://www.pythonanywhere.com' + always_on['logfile']
            state = always_on['state']
            result += f'\n[{command}]({url}){description_result} - {state}'
            inline_list.append(InlineKeyboardButton(text=command,
                                                    callback_data=f'always_on-{always_on_id}'))

        return result, inline_list
    else:
        return '\nError', False


def always_on(always_on_id, username, token):
    response = requests.get(
        f'https://www.pythonanywhere.com/api/v0/user/{username}/always_on/{always_on_id}',
        headers={'Authorization': f'Token {token}'})
    inline_back = InlineKeyboardButton(text='Backward', callback_data='update')

    if response.status_code == 200:
        data = json.loads(response.content)
        id_result = f'id: {always_on_id}\n'
        user = f"user: {data['user']}\n"
        logfile_link = 'https://www.pythonanywhere.com' + data['logfile']
        name = f'<a href="{logfile_link}">{data["command"]}</a>' + f' - {data["state"]}\n'
        description = data['description']
        description_result = f'description: {description}\n' if description != '' else ''
        can = ['enabled, ', 'can_enable, ', 'can_disable, ', 'can_edit, ', 'can_delete, ', 'can_restart, ']
        true_list = ''
        false_list = ''
        for i in can:
            if data[i[:-2]]:
                true_list += i
            else:
                false_list += i
        if true_list != '':
            true_list = 'True: ' + true_list[:-2].replace('can_', 'can ') + '\n'
        if false_list != '':
            false_list = 'False: ' + false_list[:-2].replace('can_', 'can ') + '\n'
        result = name + id_result + user + description_result + true_list + false_list

        inline_update = InlineKeyboardButton(text='Update', callback_data=f'always_on-{always_on_id}')
        inline_list = InlineKeyboardMarkup(inline_keyboard=[[inline_update], [inline_back]])
        return result, inline_list
    else:
        return 'Error', InlineKeyboardMarkup(inline_keyboard=[[inline_back]])


def consoles(console_id, username, token):
    response = requests.get(
        f'https://www.pythonanywhere.com/api/v0/user/{username}/consoles/{console_id}',
        headers={'Authorization': f'Token {token}'})
    inline_back = InlineKeyboardButton(text='Backward', callback_data='update')

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
        info_result = (f'[{name}]({console_url})'
                       f'\nid: {console_id}'
                       f'\nuser: {user}'
                       f'\nexecutable: {executable}'
                       f'{arguments_text}{working_directory_text}\n')

        get_latest_output = requests.get(
            f'https://www.pythonanywhere.com/api/v0/user/{username}/consoles/{console_id}/get_latest_output',
            headers={'Authorization': f'Token {token}'})

        if get_latest_output.status_code == 200:
            output_data = json.loads(get_latest_output.content)
            output = output_data['output']
            count = 2048
            if len(output) >= count:
                output = output[len(output)-count:]
            output_result = '\nLatest output:\n```shell\n' + output + '```'
        else:
            output_result = '\nLatest output:\nError. Most likely the console will need to be restarted\n'



        inline_update = InlineKeyboardButton(text='Update', callback_data=f'consoles-{console_id}')
        inline_send_input = InlineKeyboardButton(text='Send input', callback_data=f'send_input-{console_id}')
        inline_delete = InlineKeyboardButton(text='Delete', callback_data=f'delete-consoles-{console_id}')
        inline_keyboard = InlineKeyboardMarkup(inline_keyboard=[[inline_update], [inline_send_input], [inline_delete], [inline_back]])

        result = info_result + output_result

        return result, inline_keyboard

    else:
        return 'Error',  InlineKeyboardMarkup(inline_keyboard=[[inline_back]])
