from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.utils import executor
from aiogram.types import ParseMode
import aiohttp

API_TOKEN = '7377112405:AAHR0wY1fcYs0Yknd58QJpZ9yUA6z9Geig8'
API_URL = 'http://127.0.0.1:8080/api/scooters'  # Ваш API эндпоинт для получения данных о самокатах

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())


async def fetch_scooters():
    async with aiohttp.ClientSession() as session:
        async with session.get(API_URL) as response:
            return await response.json()


@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    await message.reply("Привет! Я бот для курьеров. Используйте команду /today, чтобы получить расписание на сегодня.")


@dp.message_handler(commands=['today'])
async def get_today_schedule(message: types.Message):
    scooters = await fetch_scooters()
    response_message = "Расписание на сегодня:\n\n"

    for scooter in scooters:
        response_message += (f"Самокат ID: {scooter['id']}\n"
                             f"Тип поломки: {scooter['breakdown_type']}\n"
                             f"Описание: {scooter['description']}\n"
                             f"Приоритет: {scooter['priority']}\n"
                             f"Статус: {scooter['status']}\n\n")

    await message.reply(response_message, parse_mode=ParseMode.MARKDOWN)


@dp.message_handler(commands=['report'])
async def report_issue(message: types.Message):
    args = message.get_args().split(',')

    if len(args) < 5:
        await message.reply("Используйте формат: /report <ID>,<Тип поломки>,<Описание>,<Приоритет>,<Статус>")
        return

    scooter_id, breakdown_type, description, priority, status = args

    data = {
        "id": scooter_id,
        "breakdown_type": breakdown_type,
        "description": description,
        "priority": priority,
        "status": status
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(API_URL, json=data) as response:
            if response.status == 200:
                await message.reply("Информация о поломке успешно добавлена.")
            else:
                await message.reply("Ошибка при добавлении информации о поломке.")


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
