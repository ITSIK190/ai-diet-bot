import asyncio
import logging
import os
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import BotCommand, CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from local_db import init_db, get_user, save_user, get_schedules, add_schedule, delete_schedule, update_schedule
from keyboards import (
    profile_keyboard, gender_keyboard, activity_keyboard,
    fasting_keyboard, meals_keyboard, cancel_keyboard, schedule_keyboard,
)
from bmi_calculator import calculate_goal_calories
from ai_manager import generate_response
from schedule_manager import send_scheduled_messages

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
log = logging.getLogger(__name__)

bot = Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"))
dp = Dispatcher(storage=MemoryStorage())

user_memory: dict[str, list[dict]] = {}


class P(StatesGroup):
    name = State()
    age = State()
    height = State()
    weight = State()
    goal = State()
    diet = State()
    fasting_start = State()
    fasting_stop = State()
    sched_time = State()
    sched_comment = State()
    sched_edit_time = State()
    sched_edit_comment = State()


def prof(data: dict) -> str:
    if not data:
        return "No profile yet. Tap a field below to start!"
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

    text = "Your Profile\n\n" + "\n".join(lines) if lines else "Your Profile\n\n(empty)"
    if missing:
        text += f"\n\nMissing: {', '.join(missing)}"
    return text + "\n\nTap a field to update it"


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
    await message.answer(prof(data), reply_markup=profile_keyboard(uid))


async def go_home_cb(cb, uid, state=None):
    if state:
        await state.clear()
    data = await get_user(uid)
    await upd(cb.message, prof(data), reply_markup=profile_keyboard(uid))


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


# /bmi
@dp.message(Command("bmi"))
async def cmd_bmi(message: Message):
    uid = str(message.from_user.id)
    d = await get_user(uid)
    w, h = d.get("weight_kg", 0), d.get("height_cm", 0)
    age, gender = d.get("age", 0), d.get("gender", "")
    goal, activity = d.get("goal_kg", 0), d.get("activity", "sedentary")
    if not all([w, h, age, gender, goal]):
        await message.answer("Missing data! Complete your profile first.", reply_markup=profile_keyboard(uid))
        return
    bmi = w / ((h / 100) ** 2)
    cal = calculate_goal_calories(w, h, age, gender, activity, goal)
    await save_user(uid, {"bmi": round(bmi, 2), "daily_calories": cal})
    status = "normal" if 18.5 <= bmi <= 25 else "overweight" if bmi <= 30 else "obese"
    await message.answer(f"BMI: {bmi:.1f} ({status})\nCalories: {cal} kcal/day")


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


# /test
@dp.message(Command("test"))
async def cmd_test(message: Message):
    parts = message.text.split(" ", 1)
    if len(parts) < 2:
        await message.answer("Usage: /test <message>")
        return
    uid = str(message.from_user.id)
    add_mem(uid, "user", parts[1])
    resp = await generate_response(uid, parts[1])
    add_mem(uid, "assistant", resp)
    await message.answer(resp)


# catch-all -> AI
@dp.message()
async def catch_all(message: Message, state: FSMContext):
    if await state.get_state():
        return
    uid = str(message.from_user.id)
    text = message.text.strip() if message.text else ""
    if not text:
        return
    add_mem(uid, "user", text)
    resp = await generate_response(uid, text)
    add_mem(uid, "assistant", resp)
    await message.answer(resp)


# Profile callbacks
@dp.callback_query(F.data.startswith("profile_"))
async def profile_cb(callback: CallbackQuery, state: FSMContext):
    uid = str(callback.from_user.id)
    action = callback.data.split("_", 1)[1]

    if action == "view":
        await upd(callback.message, prof(await get_user(uid)) + "\n\nTap a field to update it", reply_markup=profile_keyboard(uid))
    elif action == "back":
        await go_home_cb(callback, uid, state)
    elif action == "bmi":
        await cmd_bmi(callback.message)
    elif action == "gender":
        await upd(callback.message, "Select your gender:", reply_markup=gender_keyboard())
    elif action == "activity":
        await upd(callback.message, "Select your activity level:", reply_markup=activity_keyboard())
    elif action == "fasting":
        await upd(callback.message, "Enable intermittent fasting?", reply_markup=fasting_keyboard())
    elif action == "meals":
        await upd(callback.message, "How many meals per day?", reply_markup=meals_keyboard())
    elif action == "name":
        await state.clear()
        await state.set_state(P.name)
        await upd(callback.message, "Enter your name:", reply_markup=cancel_keyboard())
    elif action == "age":
        await state.clear()
        await state.set_state(P.age)
        await upd(callback.message, "Enter your age:", reply_markup=cancel_keyboard())
    elif action == "height":
        await state.clear()
        await state.set_state(P.height)
        await upd(callback.message, "Enter your height in cm:", reply_markup=cancel_keyboard())
    elif action == "weight":
        await state.clear()
        await state.set_state(P.weight)
        await upd(callback.message, "Enter your weight in kg:", reply_markup=cancel_keyboard())
    elif action == "goal":
        await state.clear()
        await state.set_state(P.goal)
        await upd(callback.message, "Enter your goal weight in kg:", reply_markup=cancel_keyboard())
    elif action == "diet":
        await state.clear()
        await state.set_state(P.diet)
        await upd(callback.message, "Enter your diet type (keto, vegan, etc.):", reply_markup=cancel_keyboard())
    else:
        await ans(callback)
        return
    await ans(callback)


# Gender / Activity / Fasting / Meals
@dp.callback_query(F.data.startswith("gender_"))
async def cb_gender(callback: CallbackQuery, state: FSMContext):
    g = callback.data.split("_", 1)[1]
    await save_user(str(callback.from_user.id), {"gender": g})
    await upd(callback.message, "Gender saved!", reply_markup=profile_keyboard(str(callback.from_user.id)))
    await ans(callback)


@dp.callback_query(F.data.startswith("activity_"))
async def cb_activity(callback: CallbackQuery, state: FSMContext):
    a = callback.data.split("_", 1)[1]
    await save_user(str(callback.from_user.id), {"activity": a})
    await upd(callback.message, "Activity saved!", reply_markup=profile_keyboard(str(callback.from_user.id)))
    await ans(callback)


@dp.callback_query(F.data.startswith("fasting_"))
async def cb_fasting(callback: CallbackQuery, state: FSMContext):
    v = callback.data.split("_", 1)[1]
    uid = str(callback.from_user.id)
    if v == "yes":
        await state.set_state(P.fasting_start)
        await upd(callback.message, "Enter fasting START time (HH:MM):", reply_markup=cancel_keyboard())
    else:
        await save_user(uid, {"fasting": 0, "fasting_start": "", "fasting_stop": ""})
        await upd(callback.message, "Fasting disabled!", reply_markup=profile_keyboard(uid))
    await ans(callback)


@dp.callback_query(F.data.startswith("meals_"))
async def cb_meals(callback: CallbackQuery, state: FSMContext):
    n = int(callback.data.split("_", 1)[1])
    await save_user(str(callback.from_user.id), {"meals_per_day": n})
    await upd(callback.message, f"Meals set to {n}/day!", reply_markup=profile_keyboard(str(callback.from_user.id)))
    await ans(callback)


# Text field handlers
@dp.message(P.name)
async def set_name(message: Message, state: FSMContext):
    await save_user(str(message.from_user.id), {"name": message.text.strip()})
    await go_home(message, str(message.from_user.id), state)


@dp.message(P.age)
async def set_age(message: Message, state: FSMContext):
    try:
        v = int(message.text.strip())
        await save_user(str(message.from_user.id), {"age": v})
        await go_home(message, str(message.from_user.id), state)
    except ValueError:
        await message.answer("Enter a valid number.")


@dp.message(P.height)
async def set_height(message: Message, state: FSMContext):
    try:
        v = int(message.text.strip())
        await save_user(str(message.from_user.id), {"height_cm": v})
        await go_home(message, str(message.from_user.id), state)
    except ValueError:
        await message.answer("Enter a valid number (cm).")


@dp.message(P.weight)
async def set_weight(message: Message, state: FSMContext):
    try:
        v = float(message.text.strip())
        await save_user(str(message.from_user.id), {"weight_kg": v})
        await go_home(message, str(message.from_user.id), state)
    except ValueError:
        await message.answer("Enter a valid number (kg).")


@dp.message(P.goal)
async def set_goal(message: Message, state: FSMContext):
    try:
        v = float(message.text.strip())
        await save_user(str(message.from_user.id), {"goal_kg": v})
        await go_home(message, str(message.from_user.id), state)
    except ValueError:
        await message.answer("Enter a valid number (kg).")


@dp.message(P.diet)
async def set_diet(message: Message, state: FSMContext):
    await save_user(str(message.from_user.id), {"diet": message.text.strip()})
    await go_home(message, str(message.from_user.id), state)


# Fasting time
@dp.message(P.fasting_start)
async def f_start(message: Message, state: FSMContext):
    t = message.text.strip()
    try:
        datetime.strptime(t, "%H:%M")
    except ValueError:
        await message.answer("Use HH:MM format (e.g. 12:00)")
        return
    await state.update_data(fs=t)
    await state.set_state(P.fasting_stop)
    await message.answer("Enter fasting STOP time (HH:MM):", reply_markup=cancel_keyboard())


@dp.message(P.fasting_stop)
async def f_stop(message: Message, state: FSMContext):
    t = message.text.strip()
    try:
        datetime.strptime(t, "%H:%M")
    except ValueError:
        await message.answer("Use HH:MM format (e.g. 20:00)")
        return
    d = await state.get_data()
    await save_user(str(message.from_user.id), {"fasting": 1, "fasting_start": d["fs"], "fasting_stop": t})
    await go_home(message, str(message.from_user.id), state)


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
    await upd(callback.message, "Enter time (HH:MM):\nExample: 08:00", reply_markup=cancel_keyboard())
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
    await message.answer("Enter the nudge message:", reply_markup=cancel_keyboard())


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
    await upd(callback.message, "Enter new time (HH:MM):", reply_markup=cancel_keyboard())
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
    await message.answer("Enter new comment:", reply_markup=cancel_keyboard())


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


# cancel button callback
@dp.callback_query(F.data == "profile_cancel")
async def cb_cancel(callback: CallbackQuery, state: FSMContext):
    await go_home_cb(callback, str(callback.from_user.id), state)


# Bot commands
async def set_commands():
    await bot.set_my_commands([
        BotCommand(command="start", description="Your profile"),
        BotCommand(command="bmi", description="Calculate BMI"),
        BotCommand(command="schedule", description="Scheduled nudges"),
        BotCommand(command="test", description="Ask AI"),
    ])


async def main():
    await init_db()
    await set_commands()
    asyncio.create_task(send_scheduled_messages(bot))
    log.info("Bot started")
    await dp.start_polling(bot, drop_pending_updates=True)


if __name__ == "__main__":
    asyncio.run(main())
