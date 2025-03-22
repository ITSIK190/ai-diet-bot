import asyncio
import pytz
from datetime import datetime
from ai_manager import chat_with_huggingchat, generate_encouragement  # Directly use HuggingChat
from firebase_config import db, get_users_with_retry 


async def update_schedule(user_id, new_schedule):
    """Update schedule in Firestore."""
    db.collection("users").document(user_id).collection("scheduled_messages").document(new_schedule["id"]).set(new_schedule)

async def get_users_with_schedules():
    """Fetch all users with scheduled messages."""
    users = db.collection("users").stream()
    return [user for user in users if db.collection("users").document(user.id).collection("scheduled_messages").stream()]

async def send_scheduled_messages(bot):
    """Send both user-defined and fixed-time encouragement messages."""
    timezone = pytz.timezone("Asia/Jerusalem")  # ✅ Fixed timezone for now
    
    while True:
        now = datetime.now(timezone).strftime("%H:%M")  # ✅ Get current time in Asia/Jerusalem

        users = await get_users_with_retry()  # ✅ Fetch all users

        if users:  
            for user in users:
                user_id = user.id
                user_data = user.to_dict()
                user_name = user_data.get("name", "Friend")

                # ✅ Send the global 08:00 encouragement message
                if now == "08:00":
                    response = await generate_encouragement(user_id, user_name)
                    try:
                        await bot.send_message(user_id, response)
                        await asyncio.sleep(1)  # ✅ Prevent Telegram rate limiting
                    except Exception as e:
                        print(f"Telegram Error for user {user_id}: {e}")

                # ✅ Send user-scheduled messages
                schedules = list(db.collection("users").document(user_id).collection("scheduled_messages").stream())

                for schedule in schedules:
                    schedule_data = schedule.to_dict() or {}
                    scheduled_time = schedule_data.get("time", "").strip()

                    if scheduled_time == now:
                        message = chat_with_huggingchat(f"Give {user_name} a short encouragement for dieting.")
                        try:
                            await bot.send_message(user_id, message)
                        except Exception as e:
                            print(f"Error sending scheduled message to {user_id}: {e}")

        await asyncio.sleep(60)  # ✅ Check every minute
