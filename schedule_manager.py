import asyncio
import pytz
from datetime import datetime
from ai_manager import generate_huggingchat_response  # Directly use HuggingChat
from firebase_config import db, get_users_with_retry 


async def update_schedule(user_id, new_schedule):
    """Update schedule in Firestore."""
    db.collection("users").document(user_id).collection("scheduled_messages").document(new_schedule["id"]).set(new_schedule)

async def get_users_with_schedules():
    """Fetch all users with scheduled messages."""
    users = db.collection("users").stream()
    return [user for user in users if db.collection("users").document(user.id).collection("scheduled_messages").stream()]

async def send_scheduled_messages(bot):
    """Send user-defined scheduled encouragement messages."""
    timezone = pytz.timezone("Asia/Jerusalem")  # ✅ Fixed timezone

    while True:
        now = datetime.now(timezone).strftime("%H:%M")  # ✅ Get current time in Asia/Jerusalem
        users = await get_users_with_retry()  # ✅ Fetch all users

        if users:
            for user in users:
                user_id = user.id
                user_data = user.to_dict()
                user_name = user_data.get("name", "Friend")

                # ✅ Fetch user-defined scheduled messages
                schedules = list(db.collection("users").document(user_id).collection("scheduled_messages").stream())
                
                tasks = []  # ✅ Store async tasks for concurrent execution
                
                for schedule in schedules:
                    schedule_data = schedule.to_dict() or {}
                    scheduled_time = schedule_data.get("time", "").strip()

                    if scheduled_time == now:
                        tasks.append(asyncio.create_task(send_scheduled_encouragement(bot, user_id, user_name)))

                # ✅ Execute all tasks concurrently
                if tasks:
                    await asyncio.gather(*tasks)

        await asyncio.sleep(60)  # ✅ Check every minute




async def send_scheduled_encouragement(bot, user_id, user_name, comment):
    """Send user-defined scheduled encouragement messages based on their specific difficulty."""
    try:
        # 🔹 Enhance the AI prompt with the user's specific difficulty
        prompt = (
            f"{user_name} is currently struggling with: {comment}. "
            f"Provide a short, motivational message that acknowledges this challenge "
            f"and gives encouragement to stay on track with their diet."
        )

        # 🔹 Generate AI response
        message = await generate_huggingchat_response(user_id, prompt)

        # 🔹 Send the message to the user
        await bot.send_message(user_id, message)
    
    except Exception as e:
        print(f"Error sending scheduled message to {user_id}: {e}")
