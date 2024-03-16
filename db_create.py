import aiosqlite


async def create_tables():
    async with aiosqlite.connect('instance/database.db') as db:
        # Создание таблицы users
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                phone_number TEXT,
                appeal_type TEXT,
                message TEXT,
                status TEXT
            );
        ''')

        # # Создание таблицы appeals
        # await db.execute('''
        #     CREATE TABLE IF NOT EXISTS appeals (
        #         appeal_id INTEGER PRIMARY KEY AUTOINCREMENT,
        #         user_id INTEGER,
        #         appeal_type TEXT,
        #         message TEXT,
        #         status TEXT,
        #         FOREIGN KEY (user_id) REFERENCES users(user_id)
        #     );
        # ''')

        await db.commit()


# Вызов функции для создания таблиц
import asyncio

asyncio.run(create_tables())
