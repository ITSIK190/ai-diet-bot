import asyncio
import pytz
import bot
from datetime import datetime
from firebase_config import db
from ai_manager import generate_encouragement

MAX_CACHED_MESSAGES = 5  # Number of pre-generated messages per user

async def get_users_with_schedules():
    """Fetch all users who have scheduled encouragements."""
    users = db.collection("users").stream()
    scheduled_users = []
    for user in users:
        user_id = user.id
        schedules = db.collection("users").document(user_id).collection("scheduled_messages").stream()
        if any(schedules):  # Only add users who have schedules
            scheduled_users.append(user)
    return scheduled_users

async def cache_encouragements():
    """Ensures each user's schedules have 5 pre-generated encouragement messages."""
    users = await get_users_with_schedules()
    for user in users:
        user_id = user.id
        schedules = db.collection("users").document(user_id).collection("scheduled_messages").stream()
        
        for schedule in schedules:
            schedule_id = schedule.id
            schedule_data = schedule.to_dict()
            cached_encouragements = schedule_data.get("cached_encouragements", [])

            # Fill up to 5 messages
            while len(cached_encouragements) < MAX_CACHED_MESSAGES:
                user_name = user.to_dict().get("name", "Friend")
                new_message = await generate_encouragement(user_id, user_name)
                cached_encouragements.append(new_message)

            # Update Firestore
            db.collection("users").document(user_id).collection("scheduled_messages").document(schedule_id).update({
                "cached_encouragements": cached_encouragements
            })

    print("✅ Encouragement messages cached successfully!")

async def send_scheduled_messages():
    """Send pre-generated messages at the scheduled time."""
    timezone = pytz.timezone("Asia/Jerusalem")

    while True:
        now = datetime.now(timezone).strftime("%H:%M")
        users = await get_users_with_schedules()

        for user in users:
            user_id = user.id
            schedules = db.collection("users").document(user_id).collection("scheduled_messages").stream()

            for schedule in schedules:
                schedule_id = schedule.id
                schedule_data = schedule.to_dict()
                scheduled_time = schedule_data.get("time")
                cached_encouragements = schedule_data.get("cached_encouragements", [])

                if scheduled_time == now and cached_encouragements:
                    # Send the first message and remove it from cache
                    message_to_send = cached_encouragements.pop(0)
                    await bot.send_message(user_id, message_to_send)

                    # Update Firestore after removing the used message
                    db.collection("users").document(user_id).collection("scheduled_messages").document(schedule_id).update({
                        "cached_encouragements": cached_encouragements
                    })

        await asyncio.sleep(60)  # Wait 1 minute before checking again
