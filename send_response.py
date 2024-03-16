import requests

TOKEN_Neuron = '6476293936:AAFHclxqvsL3pLEXnhD6O3FqNokpKqzlwek'
API_URL = f'https://api.telegram.org/bot{TOKEN_Neuron}/'


def send_response_to_user(text, appeal_id, promocode=None):
    message = text + f'\nИзвините за неудобства, ваш промокод на бесплатную поездку: {promocode}\n' if promocode else text

    message = f'Ответ по вашему обращению номер {appeal_id} \n' + message

    chat_id = get_chat_id(appeal_id)

    method = 'sendMessage'
    params = {'chat_id': chat_id, 'text': message}
    response = requests.post(API_URL + method, params=params)
    result = response.json()

    if result['ok']:
        print('Successfully replied')
    else:
        print(result)
        print('Error with replying')
    return response.json()


def get_chat_id(response_id):
    import sqlite3

    conn = sqlite3.connect('instance/database.db')
    cursor = conn.cursor()

    cursor.execute('SELECT user_id FROM appeals WHERE appeal_id = ?', (response_id,))
    user_id = cursor.fetchone()

    conn.commit()
    conn.close()
    return user_id[0]
