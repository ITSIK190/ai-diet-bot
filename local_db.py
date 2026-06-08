import os
import aiosqlite

DB_PATH = os.path.join(os.path.dirname(__file__), "diet_bot.db")


async def get_db():
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    return db


async def init_db():
    db = await get_db()
    await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            name TEXT DEFAULT '',
            age INTEGER DEFAULT 0,
            gender TEXT DEFAULT '',
            height_cm INTEGER DEFAULT 0,
            weight_kg REAL DEFAULT 0,
            goal_kg REAL DEFAULT 0,
            activity TEXT DEFAULT 'sedentary',
            diet TEXT DEFAULT '',
            meals_per_day INTEGER DEFAULT 0,
            fasting INTEGER DEFAULT 0,
            fasting_start TEXT DEFAULT '',
            fasting_stop TEXT DEFAULT '',
            bmi REAL DEFAULT 0,
            daily_calories REAL DEFAULT 0
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            time TEXT NOT NULL,
            comment TEXT DEFAULT ''
        )
    """)
    await db.commit()
    await db.close()


async def get_user(user_id: str) -> dict:
    db = await get_db()
    async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
        row = await cursor.fetchone()
    await db.close()
    return dict(row) if row else {}


async def save_user(user_id: str, data: dict):
    db = await get_db()
    keys = list(data.keys())
    values = list(data.values())
    placeholders = ", ".join("?" for _ in keys)
    set_clause = ", ".join(f"{k} = excluded.{k}" for k in keys)
    await db.execute(
        f"INSERT INTO users (user_id, {', '.join(keys)}) VALUES (?, {placeholders}) "
        f"ON CONFLICT(user_id) DO UPDATE SET {set_clause}",
        [user_id] + values,
    )
    await db.commit()
    await db.close()


async def get_users_with_schedules() -> list:
    db = await get_db()
    async with db.execute(
        "SELECT DISTINCT u.* FROM users u INNER JOIN schedules s ON u.user_id = s.user_id"
    ) as cursor:
        rows = await cursor.fetchall()
    await db.close()
    return [dict(r) for r in rows]


async def get_schedules(user_id: str) -> list:
    db = await get_db()
    async with db.execute("SELECT * FROM schedules WHERE user_id = ?", (user_id,)) as cursor:
        rows = await cursor.fetchall()
    await db.close()
    return [dict(r) for r in rows]


async def add_schedule(user_id: str, time: str, comment: str):
    db = await get_db()
    await db.execute("INSERT INTO schedules (user_id, time, comment) VALUES (?, ?, ?)", (user_id, time, comment))
    await db.commit()
    await db.close()


async def delete_schedule(user_id: str, schedule_id: int):
    db = await get_db()
    await db.execute("DELETE FROM schedules WHERE user_id = ? AND id = ?", (user_id, schedule_id))
    await db.commit()
    await db.close()


async def update_schedule(user_id: str, schedule_id: int, time: str, comment: str):
    db = await get_db()
    await db.execute("UPDATE schedules SET time = ?, comment = ? WHERE user_id = ? AND id = ?", (time, comment, user_id, schedule_id))
    await db.commit()
    await db.close()
