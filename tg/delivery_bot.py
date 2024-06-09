from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.utils import executor
from aiogram.types import ParseMode
import aiohttp

API_TOKEN = 'YOUR_BOT_API_TOKEN'
API_URL = 'http://127.0.0.1:8080/api/scooters'  # Ваш API эндпоинт для получения данных о самокатах

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())

# Список авторизованных пользователей
AUTHORIZED_USERS = [123456789, 987654321]  # замените на реальные ID пользователей


# Проверка авторизации
async def is_authorized(user_id):
    return user_id in AUTHORIZED_USERS


# Функция для получения данных о самокатах
async def fetch_scooters():
    async with aiohttp.ClientSession() as session:
        async with session.get(API_URL) as response:
            return await response.json()


@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    if not await is_authorized(message.from_user.id):
        await message.reply("Вы не авторизованы для использования этого бота.")
        return

    await message.reply("Привет! Я бот для курьеров. Используйте команду /today, чтобы получить расписание на сегодня.")


@dp.message_handler(commands=['today'])
async def get_today_schedule(message: types.Message):
    if not await is_authorized(message.from_user.id):
        await message.reply("Вы не авторизованы для использования этого бота.")
        return

    scooters = await fetch_scooters()
    response_message = "Расписание на сегодня:\n\n"

    for scooter in scooters:
        response_message += (f"Самокат ID: {scooter['id']}\n"
                             f"Тип поломки: {scooter['breakdown_type']}\n"
                             f"Описание: {scooter['description']}\n"
                             f"Приоритет: {scooter['priority']}\n"
                             f"Статус: {scooter['status']}\n"
                             f"Адрес: {scooter.get('address', 'Не указан')}\n\n")

    await message.reply(response_message, parse_mode=ParseMode.MARKDOWN)


@dp.message_handler(commands=['addresses'])
async def get_scooter_addresses(message: types.Message):
    if not await is_authorized(message.from_user.id):
        await message.reply("Вы не авторизованы для использования этого бота.")
        return

    scooters = await fetch_scooters()
    response_message = "Адреса самокатов:\n\n"

    for scooter in scooters:
        response_message += (f"Самокат ID: {scooter['id']}\n"
                             f"Адрес: {scooter.get('address', 'Не указан')}\n\n")

    await message.reply(response_message, parse_mode=ParseMode.MARKDOWN)


@dp.message_handler(commands=['report'])
async def report_issue(message: types.Message):
    if not await is_authorized(message.from_user.id):
        await message.reply("Вы не авторизованы для использования этого бота.")
        return

    await message.reply("Используйте команду /report <ID самоката>,<Описание поломки>")


@dp.message_handler(lambda message: message.text.startswith('/report '))
async def handle_report(message: types.Message):
    if not await is_authorized(message.from_user.id):
        await message.reply("Вы не авторизованы для использования этого бота.")
        return

    args = message.text[len('/report '):].split(',', 1)

    if len(args) < 2:
        await message.reply("Неверный формат. Используйте: /report <ID самоката>,<Описание поломки>")
        return

    scooter_id, description = args
    response_message = (f"Получен отчет о поломке:\n"
                        f"*ID самоката:* {scooter_id}\n"
                        f"*Описание:* {description}")

    await message.reply(response_message, parse_mode=ParseMode.MARKDOWN)


@dp.message_handler(commands=['repair'])
async def mark_repaired(message: types.Message):
    if not await is_authorized(message.from_user.id):
        await message.reply("Вы не авторизованы для использования этого бота.")
        return

    await message.reply("Используйте команду /repair <ID самоката>")


@dp.message_handler(lambda message: message.text.startswith('/repair '))
async def handle_repair(message: types.Message):
    if not await is_authorized(message.from_user.id):
        await message.reply("Вы не авторизованы для использования этого бота.")
        return

    scooter_id = message.text[len('/repair '):]

    # Здесь вы можете добавить логику для отправки запроса к API для обновления статуса самоката
    # Например, изменение статуса на "repaired"

    await message.reply(f"Самокат с ID {scooter_id} отмечен как отремонтированный.")


@dp.message_handler(commands=['pickup'])
async def mark_picked_up(message: types.Message):
    if not await is_authorized(message.from_user.id):
        await message.reply("Вы не авторизованы для использования этого бота.")
        return

    await message.reply("Используйте команду /pickup <ID самоката>")


@dp.message_handler(lambda message: message.text.startswith('/pickup '))
async def handle_pickup(message: types.Message):
    if not await is_authorized(message.from_user.id):
        await message.reply("Вы не авторизованы для использования этого бота.")
        return

    scooter_id = message.text[len('/pickup '):]

    # Здесь вы можете добавить логику для отправки запроса к API для обновления статуса самоката
    # Например, изменение статуса на "picked up"

    await message.reply(f"Самокат с ID {scooter_id} отмечен как забранный.")


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
