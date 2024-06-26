import requests
from sqlalchemy.orm import Session

from backend.models import SessionLocal, Client, SupportTicket

TOKEN_Neuron = 'API_TOKEN'
API_URL = f'https://api.telegram.org/bot{TOKEN_Neuron}/'


def send_response_to_user(text, appeal_id):
    method = 'sendMessage'
    params = {'chat_id': get_chat_id(appeal_id), 'text': text}
    response = requests.post(API_URL + method, params=params)
    result = response.json()

    if result['ok']:
        print('Successfully replied')
    else:
        print(result)
        print('Error with replying')
    return response.json()


def send_promocode(appeal_id, promocode):
    message = f'Извините за неудобства, ваш промокод на бесплатную поездку: {promocode}\n'

    method = 'sendMessage'
    params = {'chat_id': get_chat_id(appeal_id), 'text': message}
    response = requests.post(API_URL + method, params=params)
    result = response.json()

    if result['ok']:
        print('Successfully replied')
    else:
        print(result)
        print('Error with replying')
    return response.json()


def get_chat_id(ticket_id):
    print(ticket_id)
    db = SessionLocal()
    ticket = db.query(SupportTicket).filter(SupportTicket.ticket_id == ticket_id).first()

    client = db.query(Client).filter(Client.client_id == ticket.user_id).first()
    return client.email
