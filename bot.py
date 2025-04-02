# -*- coding: utf-8 -*-
import os
import asyncio
import pytz
import logging
import aiogram
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BotCommand, Message
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from firebase_config import db, get_users_with_retry  # Firebase Firestore instance
from keyboards import get_start_keyboard  # ✅ Import keyboard from new file
from schedule_manager import send_scheduled_encouragement, send_scheduled_messages
from schedule_manager import send_scheduled_messages

#from web_app import app  # Import FastAPI app after defining it
import uvicorn  # Ensure it's imported after `web_app`

# Configure logging
log_level = os.getenv("LOG_LEVEL", "DEBUG").upper()
log_level = getattr(logging, log_level, logging.DEBUG)  # Convert string to logging level

logging.basicConfig(level=log_level, format="%(asctime)s - %(levelname)s - %(message)s")

logger = logging.getLogger(__name__)

# Prevent duplicate handlers
if not logger.hasHandlers():
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

logger.info("Logging is set up correctly!")


# Load Telegram bot token from environment variable
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN is not set!")

# Initialize bot and dispatcher
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
app = FastAPI()

from bmi_handler import bmirouter as bmi_router
from commands import commandsrouter as commands_router  # Rename to avoid conflicts

dp.include_routers(bmi_router, commands_router)





@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"An unexpected error occurred: {exc}", exc_info=True)
    return JSONResponse({"error": "An unexpected error occurred"}, status_code=500)

async def send_message_with_split(user_id, text):
    """Send a long message in chunks if needed."""
    chunk_size = 4096  # Telegram message limit
    if not text:
        print("Attempted to send an empty message.")  # Debug log
        return

    for i in range(0, len(text), chunk_size):
        await bot.send_message(user_id, text[i:i+chunk_size])




@dp.message(Command("setdiet"))
async def set_diet(message: types.Message):
    """Set user's diet type to any string."""
    user_id = str(message.from_user.id)
    parts = message.text.split(maxsplit=1)

    if len(parts) < 2:
        await message.answer("Please specify your diet type. Example: /setdiet keto")
        return

    diet_type = parts[1].strip()  # Keep the exact input without capitalization

    db.collection("users").document(user_id).update({"diet": diet_type})
    await message.answer(f"Your diet type is set to: {diet_type} ✅")


@dp.message(Command("setfasting"))
async def set_fasting(message: types.Message):
    """Enable/disable intermittent fasting and set eating window."""
    user_id = str(message.from_user.id)
    parts = message.text.split()

    if len(parts) < 2:
        await message.answer("Usage: /setfasting <yes/no> [start_time] [stop_time]\nExample: /setfasting yes 12:00 20:00")
        return

    fasting_status = parts[1].lower()

    if fasting_status not in ["yes", "no"]:
        await message.answer("Please enter 'yes' to enable fasting or 'no' to disable it.")
        return

    fasting_enabled = fasting_status == "yes"
    eating_window = None

    if fasting_enabled:
        if len(parts) < 4:
            await message.answer("Please specify start and stop time. Example: /setfasting yes 12:00 20:00")
            return

        start_time, stop_time = parts[2], parts[3]

        try:
            datetime.strptime(start_time, "%H:%M")
            datetime.strptime(stop_time, "%H:%M")
        except ValueError:
            await message.answer("Invalid time format. Use HH:MM (24-hour format). Example: 12:00 20:00")
            return

        eating_window = {"start": start_time, "stop": stop_time}

    db.collection("users").document(user_id).update({"fasting": fasting_enabled, "eating_window": eating_window})
    
    if fasting_enabled:
        await message.answer(f"Intermittent fasting enabled ✅\nEating window: {start_time} - {stop_time}")
    else:
        await message.answer("Intermittent fasting disabled ❌")


@dp.message(Command("test"))
async def test_schedule(message: Message):
    """Manually test the scheduled encouragement system with a difficulty comment."""
    

    user_id = str(message.from_user.id)
    
    # Check if a comment was provided
    msg_parts = message.text.split(" ", 1)
    if len(msg_parts) < 2:
        await message.answer("⚠️ Usage: `/test Your difficulty comment`", parse_mode="Markdown")
        return

    comment = msg_parts[1]  # Extract the difficulty comment

    # Fetch user details
    user_doc = db.collection("users").document(user_id).get()
    user_data = user_doc.to_dict() or {}
    user_name = user_data.get("name", "Friend")

    # Simulate the scheduled encouragement
    try:
        await send_scheduled_encouragement(bot, user_id, user_name, comment)
        logging.info("✅ Finished send_scheduled_encouragement()")
    except Exception as e:
        print(f"❌ Error testing scheduled message for {user_id}: {e}")
        await message.answer("❌ An error occurred while testing the scheduled encouragement.")



@dp.message(Command("setmeals"))
async def set_meals(message: types.Message):
    """Set number of meals per day."""
    user_id = str(message.from_user.id)
    parts = message.text.split()

    if len(parts) < 2:
        await message.answer("Please enter the number of meals per day. Example: /setmeals 2")
        return

    try:
        meals_per_day = int(parts[1])
        if meals_per_day < 1 or meals_per_day > 6:
            raise ValueError
    except ValueError:
        await message.answer("Invalid number. Enter a value between 1 and 6.")
        return

    db.collection("users").document(user_id).update({"meals_per_day": meals_per_day})
    await message.answer(f"Your meals per day is set to {meals_per_day} 🍽️")

def truncate_text(text, max_words=50):
    """Truncate text to a maximum number of words."""
    words = text.split()
    return " ".join(words[:max_words]) if len(words) > max_words else text


        
# @dp.message(lambda message: not message.text.startswith("/"))
# async def handle_chat(message: types.Message):
#     """Handles normal chat messages with AI, ensuring full messages are sent."""
#     user_input = message.text.strip()

#     if user_input.startswith("/"):
#         return  # Ignore commands

#     user_id = str(message.from_user.id)
#     user_ref = db.collection("users").document(user_id)
#     user = user_ref.get()

#     user_name = message.from_user.first_name  # Default name
#     diet = "unknown"
#     fasting = "not specified"
#     meals = "unknown"
#     eating_window = ""

#     if user.exists:
#         user_data = user.to_dict()
#         user_name = user_data.get("name", user_name)
#         diet = user_data.get("diet", "unknown")
#         fasting = "enabled" if user_data.get("fasting") else "disabled"
#         meals = user_data.get("meals_per_day", "unknown")
#         if user_data.get("fasting") and user_data.get("eating_window"):
#             eating_window = f"Eating window: {user_data['eating_window']['start']} - {user_data['eating_window']['stop']}"

#         # Construct full prompt with user details
#         prompt = (
#             f"You are {user_name}'s AI nutrition assistant. "
#             f"They follow a {diet} diet, intermittent fasting is {fasting}, and they eat {meals} meals per day. {eating_window} "
#             f"Avoid meal planning. Instead, provide general guidance and advice related to their question. "
#             f"Please keep responses under 30 words. User message: {user_input}"
#         )
#     response = chat_with_ai(prompt)

#     if response:
#         await send_message_with_split(message.chat.id, response)
#     else:
#         await message.answer("Sorry, I didn't get that. Try again!")


async def set_bot_commands():
    commands = [
        BotCommand(command="status", description="View your current progress"),
        BotCommand(command="setgoal", description="Set your target weight"),
        BotCommand(command="logweight", description="Log your current weight"),
        BotCommand(command="m", description="Get motivation"),
        BotCommand(command="setdiet", description="setdiet"),
        BotCommand(command="setmeals", description="setmeals"),
        BotCommand(command="setgender", description="setgender"),
        BotCommand(command="setage", description="setage"),
		BotCommand(command="setheight", description="setheight"),
		BotCommand(command="setfasting", description="setfasting"),
		BotCommand(command="deleteschedule", description="deleteschedule"),
        BotCommand(command="editschedule", description="editschedule"),
		BotCommand(command="test", description="test"),
		BotCommand(command="addschedule", description="addschedule"),
        BotCommand(command="bmi", description="bmi"),
        BotCommand(command="myschedules", description="myschedules"),
        
    ]
    await bot.set_my_commands(commands)



async def main():
    """Main async function."""
    logger.info("Bot commands are being set...")
    await set_bot_commands()  
    asyncio.create_task(send_scheduled_messages(bot))  
    asyncio.create_task(run_web_server())  # ✅ Start web server async
    print("Registered routers:", dp.sub_routers)
    logger.info(f"Running aiogram version: {aiogram.__version__}")
    await dp.start_polling(bot)  # ✅ This is the main blocking task

async def run_web_server():
    """Run FastAPI server asynchronously."""
    config = uvicorn.Config("web_app:app", host="0.0.0.0", port=8080, log_level="debug")
    server = uvicorn.Server(config)
    await server.serve()  # ✅ Proper async execution

# ✅ Run bot using asyncio
if __name__ == "__main__":
    asyncio.run(main())
