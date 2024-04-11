import sqlite3


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


def sql_username_and_token(user_id):
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
    else:
        cursor.execute(f"UPDATE user SET (username, token) = ('{username}', '{token}') WHERE id = {user_id}")

    connection.commit()
    connection.close()
