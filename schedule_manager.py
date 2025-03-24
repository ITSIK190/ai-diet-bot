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
    timezone = pytz.timezone("Asia/Jerusalem")  # ✅ Fixed timezone for now
    
    while True:
        now = datetime.now(timezone).strftime("%H:%M")  # ✅ Get current time in Asia/Jerusalem

        users = await get_users_with_retry()  # ✅ Fetch all users

        if users:
            for user in users:
                user_id = user.id
                user_data = user.to_dict()
                user_name = user_data.get("name", "Friend")

                # ✅ Fetch user-scheduled messages
                schedules = list(db.collection("users").document(user_id).collection("scheduled_messages").stream())

                for schedule in schedules:
                    schedule_data = schedule.to_dict() or {}
                    scheduled_time = schedule_data.get("time", "").strip()
                    comment = schedule_data.get("comment", "").strip()  # 🔹 Get the comment (difficulty)

                    if scheduled_time == now:
                        try:
                            # 🔹 Pass the comment to the function
                            await send_scheduled_encouragement(bot, user_id, user_name, comment)
                        except Exception as e:
                            print(f"Error sending scheduled message to {user_id}: {e}")

        await asyncio.sleep(60)  # ✅ Check every minute




import logging
import sys
from hugchat.message import Message  # Ensure Message class is imported

# Make sure logging works across threads
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]  # Forces logs to appear in terminal
)


async def send_scheduled_encouragement(bot, user_id, user_name, comment):
    print(f"📤 (Async) Sending encouragement to {user_id} - {user_name}: {comment}")
    sys.stdout.flush()

    try:
        response = await generate_huggingchat_response(user_id, comment)

        # DEBUG LOGGING
        print(f"🔹 Response Type: {type(response)}")
        print(f"🔹 Response Attributes: {dir(response)}")
        print(f"🔹 Response Value: {response}")
        sys.stdout.flush()

        # Ensure response is always a string
        if isinstance(response, str):
            message_text = response
        elif isinstance(response, Message):  # Check if it's a Message instance
            message_text = str(response)  # Force conversion to string
        elif hasattr(response, "text"):  
            message_text = response.text  # Extract text if it exists
        else:
            message_text = str(response)  # Fallback to string conversion

        print(f"📨 (Async) Processed message: {message_text}")
        sys.stdout.flush()

        # Send the message
        await bot.send_message(user_id, message_text)
        print(f"✅ (Async) Message sent successfully!")
        sys.stdout.flush()

    except Exception as e:
        print(f"❌ (Async) Error in send_scheduled_encouragement(): {e}")
        sys.stdout.flush()