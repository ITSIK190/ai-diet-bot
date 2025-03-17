import logging
from aiogram import Router, types
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from firebase_config import db

MAX_SCHEDULES = 10
commandsrouter = Router(name="commandsrouter")
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def get_schedules_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Add Schedule", callback_data="add_schedule")],
        [InlineKeyboardButton(text="✏️ Edit Schedule", callback_data="edit_schedule")],
        [InlineKeyboardButton(text="❌ Delete Schedule", callback_data="delete_schedule")]
    ])
    return keyboard

@commandsrouter.message(Command("myschedules"))
async def view_schedules(message: Message):
    print(f"Received /myschedules from user {message.from_user.id}")  # Debugging
    """Displays the user's current encouragement schedules with a keyboard."""
    user_id = str(message.from_user.id)
    schedules_ref = db.collection("users").document(user_id).collection("scheduled_messages")
    schedules = schedules_ref.stream()

    schedule_list = []
    for schedule in schedules:
        data = schedule.to_dict()
        schedule_list.append(f"\U0001F551 {data['time']} - {data['comment']} ({len(data.get('cached_encouragements', []))}/5 cached)")

    response = "\n".join(schedule_list) if schedule_list else "You have no scheduled encouragements. Add one with /addschedule"

    keyboard = get_schedules_keyboard()  # Attach keyboard to message
    await message.answer(response)
    # await message.answer(response, reply_markup=keyboard)

@commandsrouter.message(Command("addschedule"))
async def add_schedule(message: Message):
    """Adds a new encouragement schedule (if under 10)."""
    user_id = str(message.from_user.id)
    schedules_ref = db.collection("users").document(user_id).collection("scheduled_messages")
    schedules = schedules_ref.stream()

    if sum(1 for _ in schedules) >= MAX_SCHEDULES:
        await message.answer("❌ You already have 10 schedules. Delete one with /deleteschedule")
        return

    msg_parts = message.text.split(" ", 2)
    if len(msg_parts) < 3:
        await message.answer("⚠️ Usage: `/addschedule HH:MM Your comment`", parse_mode="Markdown")
        return

    time_str, comment = msg_parts[1], msg_parts[2]
    if not (len(time_str) == 5 and time_str[2] == ":" and time_str[:2].isdigit() and time_str[3:].isdigit()):
        await message.answer("⚠️ Invalid time format! Use HH:MM (e.g., 08:00)")
        return

    schedules_ref.add({"time": time_str, "comment": comment, "cached_encouragements": []})
    await message.answer(f"✅ Added schedule for {time_str} - {comment}")

@commandsrouter.message(Command("deleteschedule"))
async def delete_schedule(message: Message):
    """Deletes a user's encouragement schedule."""
    user_id = str(message.from_user.id)
    schedules_ref = db.collection("users").document(user_id).collection("scheduled_messages")
    schedules = schedules_ref.stream()

    schedule_list = {idx: schedule.id for idx, schedule in enumerate(schedules, 1)}
    if not schedule_list:
        await message.answer("❌ You have no schedules to delete.")
        return

    msg_parts = message.text.split()
    if len(msg_parts) < 2 or not msg_parts[1].isdigit():
        await message.answer("⚠️ Usage: `/deleteschedule <number>`", parse_mode="Markdown")
        return

    schedule_num = int(msg_parts[1])
    if schedule_num not in schedule_list:
        await message.answer("⚠️ Invalid schedule number! Use /myschedules to see available schedules.")
        return

    schedule_id = schedule_list[schedule_num]
    schedules_ref.document(schedule_id).delete()
    await message.answer("✅ Schedule deleted!")

@commandsrouter.message(Command("editschedule"))
async def edit_schedule(message: Message):
    """Edits an existing schedule's time or comment."""
    user_id = str(message.from_user.id)
    schedules_ref = db.collection("users").document(user_id).collection("scheduled_messages")
    schedules = schedules_ref.stream()

    schedule_list = {idx: schedule.id for idx, schedule in enumerate(schedules, 1)}
    if not schedule_list:
        await message.answer("❌ You have no schedules to edit.")
        return

    msg_parts = message.text.split(" ", 3)
    if len(msg_parts) < 4:
        await message.answer("⚠️ Usage: `/editschedule <number> <HH:MM> <new comment>`", parse_mode="Markdown")
        return

    schedule_num = int(msg_parts[1])
    new_time = msg_parts[2]
    new_comment = msg_parts[3]

    if not (len(new_time) == 5 and new_time[2] == ":" and new_time[:2].isdigit() and new_time[3:].isdigit()):
        await message.answer("⚠️ Invalid time format! Use HH:MM (e.g., 08:00)")
        return

    if schedule_num not in schedule_list:
        await message.answer("⚠️ Invalid schedule number! Use /myschedules to see available schedules.")
        return

    schedule_id = schedule_list[schedule_num]
    schedules_ref.document(schedule_id).update({"time": new_time, "comment": new_comment})
    await message.answer(f"✅ Schedule updated to {new_time} - {new_comment}")


@commandsrouter.message(Command("test"))
async def test_command(message: Message):
    await message.answer("Test command works!")



@commandsrouter.message(Command("setheight"))
async def set_height(message: types.Message):
    """Handles setting the user's height in Firebase."""
    user_id = str(message.from_user.id)
    parts = message.text.split()

    if len(parts) < 2:
        await message.answer("📏 *Set Your Height*\n\n"
                             "Please enter your height in cm.\n"
                             "Example: `/setheight 175`",
                             parse_mode="Markdown")
        return

    try:
        height = int(parts[1])
        db.collection("users").document(user_id).update({"height": height})

        await message.answer(f"✅ *Height Updated!*\n\n"
                             f"📏 Your height is now *{height} cm*.",
                             parse_mode="Markdown")
    except ValueError:
        await message.answer("⚠️ *Invalid input!*\n\n"
                             "Please enter a valid number. Example: `/setheight 175`",
                             parse_mode="Markdown")

@commandsrouter.message(Command("setage"))
async def set_age(message: types.Message):
    """Handles setting the user's age in Firebase."""
    user_id = str(message.from_user.id)
    parts = message.text.split()

    if len(parts) < 2:
        await message.answer("🎂 *Set Your Age*\n\n"
                             "Please enter your age.\n"
                             "Example: `/setage 30`",
                             parse_mode="Markdown")
        return

    try:
        age = int(parts[1])
        db.collection("users").document(user_id).update({"age": age})

        await message.answer(f"✅ *Age Updated!*\n\n"
                             f"🎂 Your age is now *{age}* years old.",
                             parse_mode="Markdown")
    except ValueError:
        await message.answer("⚠️ *Invalid input!*\n\n"
                             "Please enter a valid number. Example: `/setage 30`",
                             parse_mode="Markdown")

@commandsrouter.message(Command("setgender"))
async def set_gender(message: types.Message):
    """Handles setting the user's gender in Firebase."""
    user_id = str(message.from_user.id)
    parts = message.text.split()

    if len(parts) < 2:
        await message.answer("🚻 *Set Your Gender*\n\n"
                             "Please enter your gender (Male/Female/Other).\n"
                             "Example: `/setgender Male`",
                             parse_mode="Markdown")
        return

    gender = parts[1].capitalize()
    if gender not in ["Male", "Female", "Other"]:
        await message.answer("⚠️ *Invalid input!*\n\n"
                             "Please enter `Male`, `Female`, or `Other`.\n"
                             "Example: `/setgender Male`",
                             parse_mode="Markdown")
        return

    db.collection("users").document(user_id).update({"gender": gender})

    await message.answer(f"✅ *Gender Updated!*\n\n"
                         f"🚻 Your gender is now *{gender}*.",
                         parse_mode="Markdown")
    

@commandsrouter.message(Command("test2"))
async def help_handler(message: Message):
    await message.answer("Here are the available commands...")


def register_handlers(router: Router):
    @router.message(Command("test3"))
    async def test_command(message: types.Message):
        await message.answer("✅ Test command works!")

register_handlers(commandsrouter)


