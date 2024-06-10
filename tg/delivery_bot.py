from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor
from aiogram.types import ParseMode, ReplyKeyboardMarkup, KeyboardButton
import aiohttp
import datetime

API_TOKEN = 'API_TOKEN'
API_URL_SCOOTERS = 'http://127.0.0.1:8080/api/scooters'
API_URL_PARKINGS = 'http://127.0.0.1:8000/api/parkings'

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(LoggingMiddleware())

AUTHORIZED_USERS = [123456789, 987654321]


async def is_authorized(user_id):
    return True


async def fetch_parkings():
    async with aiohttp.ClientSession() as session:
        async with session.get(API_URL_PARKINGS) as response:
            return await response.json()


start_end_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
start_end_keyboard.add(KeyboardButton('Начать рабочий день'), KeyboardButton('Закончить рабочий день'))
start_end_keyboard.add(KeyboardButton('Поломка'))


class BreakdownForm(StatesGroup):
    waiting_for_scooter_number = State()
    waiting_for_problem_description = State()


@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    if not await is_authorized(message.from_user.id):
        await message.reply("Вы не авторизованы для использования этого бота.")
        return

    welcome_message = await message.reply(
        "Привет! Я бот для курьеров. Используйте кнопки ниже, чтобы начать или закончить рабочий день.",
        reply_markup=start_end_keyboard
    )

    await bot.pin_chat_message(chat_id=message.chat.id, message_id=welcome_message.message_id)


@dp.message_handler(lambda message: message.text == 'Начать рабочий день')
async def start_workday(message: types.Message):
    if not await is_authorized(message.from_user.id):
        await message.reply("Вы не авторизованы для использования этого бота.")
        return

    # parkings = await fetch_parkings()
    try:
        parkings = [
            {'id': 1,
             'address': 'Улица Пушкина д Колотушкина',
             'scooter': '1, 3, 40'},
            {'id': 2,
             'address': 'Улица Шаболовская д 16'},
            {'id': 3,
             'address': 'Улица Крымская д 12',
             'scooter': '15, 40, 36'},
        ]
        response_message = f"Здравствуйте, Андрей. Сегодня вам нужно посетить следующие парковки:\n\n"

        for parking in parkings:
            response_message += f"Парковка ID: {parking['id']}\nАдрес: {parking.get('address', 'Не указан')}\n"
            if parking.get('scooter', None) is not None:
                response_message += f"И проверить самокат(ы) на наличие неисправности и забрать с номерами {parking['scooter']}\n\n"
            else:
                response_message += f"\n"

        await message.reply(response_message, parse_mode=ParseMode.MARKDOWN)

        start_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        await message.reply(f"Рабочий день начат в {start_time}.")
    except Exception as e:
        print(e)


@dp.message_handler(lambda message: message.text == 'Закончить рабочий день')
async def end_workday(message: types.Message):
    if not await is_authorized(message.from_user.id):
        await message.reply("Вы не авторизованы для использования этого бота.")
        return

    end_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    await message.reply(f"Рабочий день закончен в {end_time}. Спасибо за работу")


@dp.message_handler(lambda message: message.text == 'Поломка')
async def report_scooter_breakdown(message: types.Message):
    if not await is_authorized(message.from_user.id):
        await message.reply("Вы не авторизованы для использования этого бота.")
        return

    await message.reply("Пожалуйста, введите номер самоката:")
    await BreakdownForm.waiting_for_scooter_number.set()


@dp.message_handler(state=BreakdownForm.waiting_for_scooter_number, content_types=types.ContentTypes.TEXT)
async def get_scooter_number(message: types.Message, state: FSMContext):
    await state.update_data(scooter_number=message.text)
    await message.reply("Пожалуйста, опишите проблему:")
    await BreakdownForm.waiting_for_problem_description.set()


@dp.message_handler(state=BreakdownForm.waiting_for_problem_description, content_types=types.ContentTypes.TEXT)
async def get_problem_description(message: types.Message, state: FSMContext):
    data = await state.get_data()
    scooter_number = data['scooter_number']
    problem_description = message.text
    await message.reply(
        f"Спасибо, записали новую поломку у самоката номер {scooter_number}. Со следующим пояснением: {problem_description}"
    )
    await state.finish()


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
