import logging
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.dispatcher.middlewares import BaseMiddleware
import aiohttp
import asyncio

API_TOKEN = 'API_TOKEN'

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

phone_keyboard = ReplyKeyboardMarkup(resize_keyboard=True).add(
    KeyboardButton('Поделиться номером', request_contact=True))

type_buttons = [
    InlineKeyboardButton('Рекомендация', callback_data='recommendation'),
    InlineKeyboardButton('Замечание', callback_data='remark')
]
type_keyboard = InlineKeyboardMarkup().row(*type_buttons)
restart_keyboard = InlineKeyboardMarkup().add(
    InlineKeyboardButton('Начать новое обращение', callback_data='start_new'))

user_states = {}
user_timeouts = {}
user_tickets = {}


class TimeoutMiddleware(BaseMiddleware):
    def __init__(self, timeout=600):
        self.timeout = timeout
        super().__init__()

    async def on_process_message(self, message: types.Message, data: dict):
        user_id = message.from_user.id
        if user_id in user_timeouts:
            user_timeouts[user_id].cancel()
        user_timeouts[user_id] = asyncio.create_task(self.reset_state_after_timeout(user_id))

    async def reset_state_after_timeout(self, user_id):
        await asyncio.sleep(self.timeout)
        if user_id in user_states and user_id in user_tickets:
            async with aiohttp.ClientSession() as session:
                async with session.post(f'http://localhost:8000/appeals/{user_tickets[user_id]}/update_status', data={
                    'status': 'closed',
                }) as response:
                    pass
            user_states[user_id] = None
            user_tickets[user_id] = None
            await bot.send_message(user_id,
                                   "Ваше обращение было завершено из-за неактивности. Нажмите /new для начала нового обращения.")


@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    await message.answer("Привет! Чтобы начать, пожалуйста, поделись своим номером телефона.",
                         reply_markup=phone_keyboard)


@dp.message_handler(commands=['new'])
async def start_new_request(message: types.Message):
    user_id = message.from_user.id
    user_states[user_id] = None
    user_tickets[user_id] = None
    await message.answer("Выберите тип обращения:", reply_markup=type_keyboard)


@dp.message_handler(content_types=['contact'])
async def contact_handler(message: types.Message):
    user_id = message.from_user.id
    phone_number = message.contact.phone_number
    await register_user(user_id, phone_number=phone_number)
    await message.reply("Выберите тип обращения:", reply_markup=type_keyboard)


@dp.callback_query_handler(lambda c: c.data in ['recommendation', 'remark'])
async def type_callback_handler(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    appeal_type = 'Рекомендация' if callback_query.data == 'recommendation' else 'Замечание'
    user_states[user_id] = {'type': appeal_type}
    await bot.send_message(user_id, "Пожалуйста, напишите ваше обращение.")
    await callback_query.answer()


@dp.callback_query_handler(lambda c: c.data in ['start_new'])
async def start_new_callback_handler(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    user_states[user_id] = None
    user_tickets[user_id] = None
    await bot.send_message(user_id, "Выберите тип обращения:", reply_markup=type_keyboard)


@dp.message_handler(content_types=['text'])
async def message_handler(message: types.Message):
    user_id = message.from_user.id
    user_state = user_states.get(user_id)
    user_ticket = user_tickets.get(user_id)

    if user_state and 'type' in user_state:
        if user_ticket:
            await add_to_existing_appeal(message=message.text, ticket_id=user_ticket)
            return

        message_text = message.text
        appeal_type = user_state['type']
        appeal_id = await save_new_appeal(user_id, appeal_type, message_text)
        await message.answer(f"Ваше обращение принято в обработку. Номер вашего обращения: {appeal_id}. С вами свяжется первый освободившийся оператор!")
    else:
        await message.answer("Выберите тип обращения:", reply_markup=type_keyboard)


async def save_new_appeal(user_id, appeal_type, message):
    async with aiohttp.ClientSession() as session:
        async with session.post('http://localhost:8000/appeals/', data={
            'email': user_id,
            'category': appeal_type,
            'description': message
        }) as response:
            if response.status == 200:
                data = await response.json()
                appeal_id = data['ticket_id']
                async with session.post(f'http://localhost:8000/send_message/{appeal_id}', data={
                    "message": message, "operator_id": -1
                }) as response:
                    user_tickets[user_id] = data['ticket_id']
                    return data['ticket_id']
            else:
                logging.error(f"Failed to save appeal: {response.status}")
                return None


async def add_to_existing_appeal(message, ticket_id):
    async with aiohttp.ClientSession() as session:
        async with session.post(f'http://localhost:8000/send_message/{ticket_id}', data={
            "message": message, "operator_id": -1
        }) as response:
            return response.status


async def register_user(user_id, full_name='Undefined',
                        dob=datetime.now().isoformat() + 'Z',
                        phone_number='Undefined', membership_type='Undefined'):
    registration_date = datetime.now().isoformat() + 'Z'
    async with aiohttp.ClientSession() as session:
        async with session.post('http://localhost:8000/clients/', json={
            'full_name': full_name,
            'email': str(user_id),
            'dob': dob,
            'phone_number': phone_number,
            'registration_date': registration_date,
            'membership_type': membership_type,
            'payment_details': 'Undefined',
            'ride_history': 'Undefined',
            'active_bookings': 'Undefined'
        }) as response:
            if response.status == 200:
                logging.error("Successfully saved")
                data = await response.json()
                return data
            else:
                logging.error(f"Failed to save or update user data: {response.status}")
                return None


if __name__ == '__main__':
    dp.middleware.setup(TimeoutMiddleware())
    executor.start_polling(dp, skip_updates=True)
