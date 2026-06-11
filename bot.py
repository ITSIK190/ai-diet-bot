import asyncio
import json
import logging
import os
import urllib.parse
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import BotCommand, CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from local_db import init_db, get_user, save_user, get_schedules, add_schedule, delete_schedule, update_schedule
from keyboards import profile_webapp_keyboard, schedule_keyboard
from bmi_calculator import calculate_goal_calories
from ai_manager import generate_response, generate_nudge
from schedule_manager import send_scheduled_messages

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
log = logging.getLogger(__name__)

bot = Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"))
dp = Dispatcher(storage=MemoryStorage())

WEBAPP_URL = os.getenv("WEBAPP_URL", "https://itsik190.github.io/ai-diet-bot/")

user_memory: dict[str, list[dict]] = {}


class P(StatesGroup):
    sched_time = State()
    sched_comment = State()
    sched_edit_time = State()
    sched_edit_comment = State()


def prof(data: dict) -> str:
    if not data:
        return "No profile yet. Tap Edit Profile below to start!"
    lines = []
    if data.get("name"): lines.append(f"Name: {data['name']}")
    if data.get("age"): lines.append(f"Age: {data['age']}")
    if data.get("gender"): lines.append(f"Gender: {data['gender']}")
    if data.get("height_cm"): lines.append(f"Height: {data['height_cm']} cm")
    if data.get("weight_kg"): lines.append(f"Weight: {data['weight_kg']} kg")
    if data.get("goal_kg"): lines.append(f"Goal: {data['goal_kg']} kg")
    if data.get("activity"): lines.append(f"Activity: {data['activity']}")
    if data.get("diet"): lines.append(f"Diet: {data['diet']}")
    if data.get("meals_per_day"): lines.append(f"Meals/day: {data['meals_per_day']}")
    if data.get("fasting"):
        lines.append(f"Fasting: {data.get('fasting_start','')} - {data.get('fasting_stop','')}")
    if data.get("bmi"): lines.append(f"BMI: {data['bmi']:.1f}")
    if data.get("daily_calories"): lines.append(f"Calories: {data['daily_calories']} kcal")

    missing = []
    for k, label in [("name","Name"),("age","Age"),("gender","Gender"),("height_cm","Height"),("weight_kg","Weight"),("goal_kg","Goal"),("activity","Activity"),("diet","Diet"),("meals_per_day","Meals")]:
        if not data.get(k, 0):
            missing.append(label)

    text = "Profile\n\n" + "\n".join(lines) if lines else "Profile\n\n(empty)"
    if missing:
        text += f"\n\nMissing: {', '.join(missing)}"
    return text


async def upd(msg, text, **kw):
    try:
        await msg.edit_text(text, **kw)
    except TelegramBadRequest as e:
        if "not modified" not in str(e).lower():
            try:
                await msg.answer(text, **kw)
            except:
                pass


async def ans(cb, **kw):
    try:
        await cb.answer(**kw)
    except:
        pass


async def go_home(message, uid, state=None):
    if state:
        await state.clear()
    data = await get_user(uid)
    url = _build_webapp_url(data)
    await message.answer(prof(data), reply_markup=profile_webapp_keyboard(url))


async def go_home_cb(cb, uid, state=None):
    if state:
        await state.clear()
    data = await get_user(uid)
    url = _build_webapp_url(data)
    await upd(cb.message, prof(data), reply_markup=profile_webapp_keyboard(url))


def _build_webapp_url(data: dict) -> str:
    params = {}
    if data.get("name"): params["name"] = data["name"]
    if data.get("age"): params["age"] = str(data["age"])
    if data.get("gender"): params["gender"] = data["gender"]
    if data.get("height_cm"): params["height"] = str(data["height_cm"])
    if data.get("weight_kg"): params["weight"] = str(data["weight_kg"])
    if data.get("goal_kg"): params["goal"] = str(data["goal_kg"])
    if data.get("activity"): params["activity"] = data["activity"]
    if data.get("diet"): params["diet"] = data["diet"]
    if data.get("meals_per_day"): params["meals"] = str(data["meals_per_day"])
    if data.get("fasting"):
        params["fasting"] = "1"
        params["fasting_start"] = data.get("fasting_start", "12:00")
        params["fasting_stop"] = data.get("fasting_stop", "20:00")
    if params:
        return WEBAPP_URL + "?" + urllib.parse.urlencode(params)
    return WEBAPP_URL


def add_mem(uid, role, content):
    if uid not in user_memory:
        user_memory[uid] = []
    user_memory[uid].append({"role": role, "content": content})
    if len(user_memory[uid]) > 20:
        user_memory[uid] = user_memory[uid][-20:]


# /start
@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    uid = str(message.from_user.id)
    existing = await get_user(uid)
    if not existing.get("name"):
        await save_user(uid, {"name": message.from_user.first_name or "Friend"})
    await go_home(message, uid)


# /schedule
@dp.message(Command("schedule"))
async def cmd_sched(message: Message):
    uid = str(message.from_user.id)
    ss = await get_schedules(uid)
    if ss:
        lines = [f"{i+1}. {s['time']} - {s['comment']}" for i, s in enumerate(ss)]
        text = "Your Scheduled Nudges\n\n" + "\n".join(lines)
    else:
        text = "No scheduled nudges."
    await message.answer(text, reply_markup=schedule_keyboard())


# /cancel
@dp.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    await go_home(message, str(message.from_user.id), state)


# catch-all -> AI (only when no FSM state is active)
@dp.message(F.text)
async def catch_all(message: Message, state: FSMContext):
    uid = str(message.from_user.id)
    text = message.text.strip()
    if not text:
        return
    add_mem(uid, "user", text)
    resp = await generate_response(uid, text, user_memory.get(uid))
    add_mem(uid, "assistant", resp)
    await message.answer(resp)


# Nudge button callback
@dp.callback_query(F.data == "nudge_me")
async def cb_nudge(callback: CallbackQuery):
    uid = str(callback.from_user.id)
    resp = await generate_nudge(uid)
    await callback.answer()
    await callback.message.answer(f"💪 {resp}")


# WebApp data handler
@dp.message(F.web_app_data)
async def webapp_submit(message: Message):
    data = json.loads(message.web_app_data.data)
    uid = str(message.from_user.id)
    await save_user(uid, {
        "name": data.get("name", ""),
        "age": int(data.get("age", 0)),
        "gender": data.get("gender", ""),
        "height_cm": int(data.get("height", 0)),
        "weight_kg": float(data.get("weight", 0)),
        "goal_kg": float(data.get("goal", 0)),
        "activity": data.get("activity", "sedentary"),
        "diet": data.get("diet", ""),
        "meals_per_day": int(data.get("meals", 0)),
        "fasting": 1 if data.get("fasting") else 0,
        "fasting_start": data.get("fasting_start", ""),
        "fasting_stop": data.get("fasting_stop", ""),
    })
    d = await get_user(uid)
    w = d.get("weight_kg", 0)
    h = d.get("height_cm", 0)
    age = d.get("age", 0)
    gender = d.get("gender", "")
    goal = d.get("goal_kg", 0)
    activity = d.get("activity", "sedentary")
    if all([w, h, age, gender, goal]):
        bmi = w / ((h / 100) ** 2)
        cal = calculate_goal_calories(w, h, age, gender, activity, goal)
        await save_user(uid, {"bmi": round(bmi, 2), "daily_calories": cal})
    await go_home(message, uid)


# Profile callbacks
@dp.callback_query(F.data.startswith("profile_"))
async def profile_cb(callback: CallbackQuery, state: FSMContext):
    uid = str(callback.from_user.id)
    action = callback.data.split("_", 1)[1]

    if action == "back":
        await go_home_cb(callback, uid, state)
    else:
        await ans(callback)
        return
    await ans(callback)


# Schedule callbacks
@dp.callback_query(F.data == "sched_view")
async def s_view(callback: CallbackQuery):
    uid = str(callback.from_user.id)
    ss = await get_schedules(uid)
    if ss:
        lines = [f"{i+1}. {s['time']} - {s['comment']}" for i, s in enumerate(ss)]
        text = "Your Scheduled Nudges\n\n" + "\n".join(lines)
    else:
        text = "No scheduled nudges."
    await upd(callback.message, text, reply_markup=schedule_keyboard())
    await ans(callback)


@dp.callback_query(F.data == "sched_add")
async def s_add(callback: CallbackQuery, state: FSMContext):
    uid = str(callback.from_user.id)
    if len(await get_schedules(uid)) >= 10:
        await ans(callback, text="Max 10!", show_alert=True)
        return
    await state.set_state(P.sched_time)
    await upd(callback.message, "Enter time (HH:MM):\nExample: 08:00")
    await ans(callback)


@dp.message(P.sched_time)
async def s_time(message: Message, state: FSMContext):
    t = message.text.strip()
    try:
        datetime.strptime(t, "%H:%M")
    except ValueError:
        await message.answer("Use HH:MM format")
        return
    await state.update_data(st=t)
    await state.set_state(P.sched_comment)
    await message.answer("Enter the nudge message:")


@dp.message(P.sched_comment)
async def s_comment(message: Message, state: FSMContext):
    d = await state.get_data()
    await add_schedule(str(message.from_user.id), d["st"], message.text.strip())
    await message.answer(f"Nudge scheduled for {d['st']}!", reply_markup=schedule_keyboard())
    await state.clear()


@dp.callback_query(F.data == "sched_edit")
async def s_edit(callback: CallbackQuery):
    uid = str(callback.from_user.id)
    ss = await get_schedules(uid)
    if not ss:
        await ans(callback, text="No schedules.", show_alert=True)
        return
    lines = [f"{i+1}. {s['time']} - {s['comment']}" for i, s in enumerate(ss)]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        *[[InlineKeyboardButton(text=f"#{i+1} {s['time']}", callback_data=f"se_{s['id']}")] for i, s in enumerate(ss)],
        [InlineKeyboardButton(text="Back", callback_data="profile_back")],
    ])
    await upd(callback.message, "Select to edit:\n" + "\n".join(lines), reply_markup=kb)
    await ans(callback)


@dp.callback_query(F.data.startswith("se_"))
async def s_edit_sel(callback: CallbackQuery, state: FSMContext):
    sid = int(callback.data[3:])
    await state.update_data(eid=sid)
    await state.set_state(P.sched_edit_time)
    await upd(callback.message, "Enter new time (HH:MM):")
    await ans(callback)


@dp.message(P.sched_edit_time)
async def s_edit_time(message: Message, state: FSMContext):
    t = message.text.strip()
    try:
        datetime.strptime(t, "%H:%M")
    except ValueError:
        await message.answer("Use HH:MM format")
        return
    await state.update_data(et=t)
    await state.set_state(P.sched_edit_comment)
    await message.answer("Enter new comment:")


@dp.message(P.sched_edit_comment)
async def s_edit_comment(message: Message, state: FSMContext):
    d = await state.get_data()
    await update_schedule(str(message.from_user.id), d["eid"], d["et"], message.text.strip())
    await message.answer("Schedule updated!", reply_markup=schedule_keyboard())
    await state.clear()


@dp.callback_query(F.data == "sched_delete")
async def s_del(callback: CallbackQuery):
    uid = str(callback.from_user.id)
    ss = await get_schedules(uid)
    if not ss:
        await ans(callback, text="No schedules.", show_alert=True)
        return
    lines = [f"{i+1}. {s['time']} - {s['comment']}" for i, s in enumerate(ss)]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        *[[InlineKeyboardButton(text=f"DEL #{i+1} {s['time']}", callback_data=f"sd_{s['id']}")] for i, s in enumerate(ss)],
        [InlineKeyboardButton(text="Back", callback_data="profile_back")],
    ])
    await upd(callback.message, "Select to delete:\n" + "\n".join(lines), reply_markup=kb)
    await ans(callback)


@dp.callback_query(F.data.startswith("sd_"))
async def s_del_confirm(callback: CallbackQuery):
    sid = int(callback.data[3:])
    await delete_schedule(str(callback.from_user.id), sid)
    await upd(callback.message, "Deleted!", reply_markup=schedule_keyboard())
    await ans(callback)


# Bot commands
async def set_commands():
    await bot.set_my_commands([
        BotCommand(command="start", description="Profile"),
        BotCommand(command="schedule", description="Scheduled nudges"),
    ])


async def main():
    await init_db()
    await set_commands()
    asyncio.create_task(send_scheduled_messages(bot))
    log.info("Bot started")
    await dp.start_polling(bot, drop_pending_updates=True)


if __name__ == "__main__":
    asyncio.run(main())
