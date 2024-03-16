import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import aiosqlite

API_TOKEN = '6476293936:AAFHclxqvsL3pLEXnhD6O3FqNokpKqzlwek'  # Замените на реальный токен вашего бота

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

phone_keyboard = ReplyKeyboardMarkup(resize_keyboard=True).add(
    KeyboardButton('Поделиться номером', request_contact=True))

# Создаём кнопки для выбора типа обращения
type_buttons = [
    InlineKeyboardButton('Рекомендация', callback_data='recommendation'),
    InlineKeyboardButton('Замечание', callback_data='remark')
]
type_keyboard = InlineKeyboardMarkup().row(*type_buttons)
restart_keyboard = InlineKeyboardMarkup().add(
    InlineKeyboardButton('Начать новое обращение', callback_data='start_new'))

user_states = {}


@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    """
    Эта команда будет вызвана, когда пользователь отправит `/start` или `/help`
    """
    # Отправляем приветственное сообщение с кнопкой для запроса номера телефона
    await message.answer("Привет! Чтобы начать, пожалуйста, поделись своим номером телефона.",
                         reply_markup=phone_keyboard)


@dp.message_handler(content_types=['contact'])
async def contact_handler(message: types.Message):
    user_id = message.from_user.id
    phone_number = message.contact.phone_number
    # Сохранить данные в базу данных
    await save_or_update_user_data(user_id, phone_number=phone_number)
    await message.reply("Выберите тип обращения:", reply_markup=type_keyboard)


@dp.message_handler(content_types=['contact'])
async def contact_handler(message: types.Message):
    """
    Обработчик события, когда пользователь делится своим контактом.
    """
    user_id = message.from_user.id
    phone_number = message.contact.phone_number
    # Здесь можно добавить логику для сохранения данных пользователя в базу данных
    # Пока просто переходим к выбору типа обращения
    await message.answer("Спасибо! Теперь выберите тип обращения.", reply_markup=type_keyboard)


@dp.callback_query_handler(lambda c: c.data in ['recommendation', 'remark'])
async def type_callback_handler(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    appeal_type = 'Рекомендация' if callback_query.data == 'recommendation' else 'Замечание'
    # Сохраняем тип обращения в состоянии пользователя
    user_states[user_id] = {'type': appeal_type}
    await bot.send_message(user_id, "Пожалуйста, напишите ваше обращение.")
    await callback_query.answer()


@dp.callback_query_handler(lambda c: c.data in ['start_new'])
async def type_callback_handler(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id

    await bot.send_message(user_id, "Выберите тип обращения:", reply_markup=type_keyboard)


@dp.message_handler(content_types=['text'])
async def message_handler(message: types.Message):
    user_id = message.from_user.id
    user_state = user_states.get(user_id)

    if user_state and 'type' in user_state:
        message_text = message.text
        appeal_type = user_state['type']
        appeal_id = await save_new_appeal(user_id, appeal_type, message_text)
        await message.answer(f"Ваше обращение принято в обработку. Номер вашего обращения: {appeal_id}.",
                             reply_markup=restart_keyboard)
        user_states[user_id] = None  # Сброс состояния пользователя после отправки обращения
    else:
        await message.answer("Выберите тип обращения:", reply_markup=type_keyboard)


async def save_new_appeal(user_id, appeal_type, message):
    async with aiosqlite.connect('instance/database.db') as db:
        await db.execute('''INSERT INTO appeals (user_id, appeal_type, message, status) 
                            VALUES (?, ?, ?, 'waiting')''',
                         (user_id, appeal_type, message))
        await db.commit()
        cursor = await db.execute('SELECT last_insert_rowid()')
        appeal_id = await cursor.fetchone()
        return appeal_id[0]

    # Функция для сохранения или обновления данных пользователя


async def save_or_update_user_data(user_id, phone_number=None, appeal_type=None):
    async with aiosqlite.connect('instance/database.db') as db:
        cursor = await db.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        user = await cursor.fetchone()
        if user:
            # Если пользователь найден, обновляем его данные
            await db.execute('''UPDATE users SET 
                                phone_number = COALESCE(?, phone_number), 
                                appeal_type = COALESCE(?, appeal_type)
                                WHERE user_id = ?''', (phone_number, appeal_type, user_id))
        else:
            # Если пользователь не найден, добавляем новую запись
            await db.execute('INSERT INTO users (user_id, phone_number, appeal_type) VALUES (?, ?, ?)',
                             (user_id, phone_number, appeal_type))
        await db.commit()


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
