from aiogram import types
from aiogram.filters import Command
from firebase_config import db
from bot import dp

MAX_SCHEDULES = 10

@dp.message_handler(Command("myschedules"))
async def view_schedules(message: types.Message):
    """Displays the user's current encouragement schedules."""
    user_id = str(message.from_user.id)
    schedules_ref = db.collection("users").document(user_id).collection("scheduled_messages")
    schedules = schedules_ref.stream()

    schedule_list = []
    for schedule in schedules:
        data = schedule.to_dict()
        schedule_list.append(f"🕒 {data['time']} - {data['comment']} ({len(data.get('cached_encouragements', []))}/5 cached)")

    if schedule_list:
        response = "\n".join(schedule_list)
    else:
        response = "You have no scheduled encouragements. Add one with /addschedule"

    await message.answer(response)


@dp.message_handler(Command("addschedule"))
async def add_schedule(message: types.Message):
    """Adds a new encouragement schedule (if under 10)."""
    user_id = str(message.from_user.id)
    schedules_ref = db.collection("users").document(user_id).collection("scheduled_messages")
    schedules = schedules_ref.stream()

    if sum(1 for _ in schedules) >= MAX_SCHEDULES:
        await message.answer("❌ You already have 10 schedules. Delete one with /deleteschedule")
        return

    msg_parts = message.text.split(" ", 2)  # Expect format: /addschedule HH:MM comment
    if len(msg_parts) < 3:
        await message.answer("⚠️ Usage: `/addschedule HH:MM Your comment` (e.g., `/addschedule 08:00 Morning boost!`)", parse_mode="Markdown")
        return

    time_str, comment = msg_parts[1], msg_parts[2]

    # Validate time format
    if not (len(time_str) == 5 and time_str[2] == ":" and time_str[:2].isdigit() and time_str[3:].isdigit()):
        await message.answer("⚠️ Invalid time format! Use HH:MM (e.g., 08:00)")
        return

    schedules_ref.add({
        "time": time_str,
        "comment": comment,
        "cached_encouragements": []  # Will be populated by cache_encouragements()
    })

    await message.answer(f"✅ Added schedule for {time_str} - {comment}")


@dp.message_handler(Command("deleteschedule"))
async def delete_schedule(message: types.Message):
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
        await message.answer("⚠️ Usage: `/deleteschedule <number>` (Get numbers from /myschedules)", parse_mode="Markdown")
        return

    schedule_num = int(msg_parts[1])
    if schedule_num not in schedule_list:
        await message.answer("⚠️ Invalid schedule number! Use /myschedules to see available schedules.")
        return

    schedule_id = schedule_list[schedule_num]
    schedules_ref.document(schedule_id).delete()
    await message.answer("✅ Schedule deleted!")


@dp.message_handler(Command("editschedule"))
async def edit_schedule(message: types.Message):
    """Edits an existing schedule's time or comment."""
    user_id = str(message.from_user.id)
    schedules_ref = db.collection("users").document(user_id).collection("scheduled_messages")
    schedules = schedules_ref.stream()

    schedule_list = {idx: schedule.id for idx, schedule in enumerate(schedules, 1)}
    
    if not schedule_list:
        await message.answer("❌ You have no schedules to edit.")
        return

    msg_parts = message.text.split(" ", 3)  # Expect: /editschedule <number> <HH:MM> <new comment>
    if len(msg_parts) < 4:
        await message.answer("⚠️ Usage: `/editschedule <number> <HH:MM> <new comment>`", parse_mode="Markdown")
        return

    schedule_num = int(msg_parts[1])
    new_time = msg_parts[2]
    new_comment = msg_parts[3]

    # Validate time
    if not (len(new_time) == 5 and new_time[2] == ":" and new_time[:2].isdigit() and new_time[3:].isdigit()):
        await message.answer("⚠️ Invalid time format! Use HH:MM (e.g., 08:00)")
        return

    if schedule_num not in schedule_list:
        await message.answer("⚠️ Invalid schedule number! Use /myschedules to see available schedules.")
        return

    schedule_id = schedule_list[schedule_num]
    schedules_ref.document(schedule_id).update({"time": new_time, "comment": new_comment})

    await message.answer(f"✅ Schedule updated to {new_time} - {new_comment}")

