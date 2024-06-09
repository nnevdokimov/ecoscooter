from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.utils import executor
from aiogram.types import ParseMode

API_TOKEN = 'YOUR_BOT_API_TOKEN'

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())

# Статический список адресов и номеров самокатов
scooter_data = [
    {
        "address": "Улица Ленина, 10",
        "scooters": [1, 2, 3]
    },
    {
        "address": "Проспект Мира, 25",
        "scooters": [4, 5]
    },
    {
        "address": "Улица Гагарина, 3",
        "scooters": [6, 7, 8, 9]
    }
]


@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    await message.reply("Привет! Я бот для курьеров. Используйте команду /today, чтобы получить расписание на сегодня.")


@dp.message_handler(commands=['today'])
async def get_today_schedule(message: types.Message):
    response_message = "Расписание на сегодня:\n\n"

    for entry in scooter_data:
        scooters_list = ", ".join(map(str, entry['scooters']))
        response_message += (f"*Адрес:* {entry['address']}\n"
                             f"*Самокаты:* {scooters_list}\n\n")

    await message.reply(response_message, parse_mode=ParseMode.MARKDOWN)


@dp.message_handler(commands=['report'])
async def report_issue(message: types.Message):
    await message.reply("Используйте команду /report в формате: /report <ID самоката>,<Описание поломки>")


@dp.message_handler(lambda message: message.text.startswith('/report '))
async def handle_report(message: types.Message):
    args = message.text[len('/report '):].split(',', 1)

    if len(args) < 2:
        await message.reply("Неверный формат. Используйте: /report <ID самоката>,<Описание поломки>")
        return

    scooter_id, description = args
    response_message = (f"Получен отчет о поломке:\n"
                        f"*ID самоката:* {scooter_id}\n"
                        f"*Описание:* {description}")

    await message.reply(response_message, parse_mode=ParseMode.MARKDOWN)


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
