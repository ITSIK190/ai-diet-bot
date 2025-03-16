# -*- coding: utf-8 -*-
import os
import asyncio
import pytz
import logging
import threading
from datetime import datetime
from aiogram import Bot, Dispatcher, types, Router, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BotCommand
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn  # Ensure it's imported after `web_app`
from firebase_config import db, get_users_with_retry  # Firebase Firestore instance
from bmi_handler import router as bmi_router  # Import BMI command router
from ai_manager import generate_encouragement, chat_with_ai
from schedule_manager import send_scheduled_messages, cache_encouragements
from commands import router as commands_router  # Rename to avoid conflicts
from web_app import app  # Import FastAPI app after defining it

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
router = Router()
dp.include_router(bmi_router)

# English Translations
WELCOME_BACK = "Welcome back, {name}!\nYour last recorded weight: {weight} kg\nYour goal: {goal} kg"
WELCOME_NEW = "Welcome, {name}! Please enter your weight (in kg):"
GOAL_SET = "Your goal is now set to {goal} kg! Keep up the great work! 💪"
WEIGHT_LOGGED = "Got it! Your weight has been logged as {weight} kg. 🎯"
INVALID_WEIGHT = "Invalid weight. Please enter a number."
ADVICE_PREFIX = "🧠 AI Advice: "
ENCOURAGEMENT = "{name}, you're doing great! Keep pushing towards your goals! 🎯"



# Custom error handler for FastAPI
@app.exception_handler(Exception)
async def unicorn_exception_handler(request: Request, exc: Exception):
    # Log the exception
    logger.error(f"Unhandled exception occurred: {exc}", exc_info=True)

    # Return a generic message to the user
    return JSONResponse(
        status_code=500,
        content={"message": "Internal server error, please try again later."},
    )

# Example route with exception handling
@app.get("/error")
async def trigger_error():
    try:
        # Simulate an error
        result = 1 / 0
    except Exception as e:
        logger.error(f"Error during operation: {str(e)}", exc_info=True)
        raise e  # Optionally, re-raise the error after logging

    return {"message": "This will not be reached if an error occurs."}



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




@dp.message(Command("help"))
async def help_command(message: types.Message):
    user_id = str(message.from_user.id)

    help_text = (
        "🤖 *AI Dietitian Bot \\- Command List:*\n\n"
        "⚡ /start \\- Restart the bot and show the main menu\n"
        "📋 /set\\_diet \\- Choose your diet type\n"
        "⏳ /set\\_fasting \\- Enable or disable intermittent fasting\n"
        "🍱 /set\\_meals \\- Set the number of meals per day\n"
        "⚖️ /set\\_weight \\- Update your weight\n"
        "🎯 /set\\_goal \\- Set your weight goal\n"
        "📊 /status \\- View your current settings\n"
        "❓ /help \\- Show this command list\n"
        "\nℹ️ *Tap a button below to update your details\\!*"
    )

    keyboard = get_start_keyboard(user_id)

    await message.answer(help_text, parse_mode="MarkdownV2", reply_markup=keyboard)




from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# 🎨 Start Keyboard with Mini App Integration
def get_start_keyboard(user_id: str):
    base_url = "https://ai-diet-bot-production.up.railway.app/"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📋 Set Diet", callback_data="set_diet"),
            InlineKeyboardButton(text="⏳ Set Fasting", callback_data="set_fasting")
        ],
        [
            InlineKeyboardButton(text="🍱 Set Meals", callback_data="set_meals"),
            InlineKeyboardButton(text="⚖️ Set Weight", callback_data="set_weight")
        ],
        [
            InlineKeyboardButton(text="🎯 Set Goal", callback_data="set_goal"),
            InlineKeyboardButton(text="📊 View Status", callback_data="view_status")
        ],
        [
            InlineKeyboardButton(text="📝 Edit Profile", url=f"{base_url}?user_id={user_id}"),
            InlineKeyboardButton(text="🚀 Mini App", url=f"{base_url}?user_id={user_id}&mini_app=true")
        ]
    ])

    return keyboard


# 🎯 Start Command Handler
@dp.message(Command("start"))
async def start(message: types.Message):
    user_id = str(message.from_user.id)  # Ensure user_id is a string
    user_name = message.from_user.first_name or "Friend"  # Default if name missing

    user_ref = db.collection("users").document(user_id)
    
    try:
        user = user_ref.get()
        keyboard = get_start_keyboard(user_id)
        print(f"Generated Keyboard: {keyboard}")
        if user.exists:
            user_data = user.to_dict()
            weight = user_data.get("weight", "Unknown")
            goal = user_data.get("goal", "Not set")
            await message.answer(
                f"Welcome back, {user_name}!\n\nYour current weight: {weight} kg\nGoal: {goal} kg",
                reply_markup=keyboard
            )
        else:
            # New user setup
            user_ref.set({"user_id": user_id, "name": user_name})
            await message.answer(
                f"Hello {user_name}! Welcome to the AI Diet Coach bot. Let's set up your profile!",
                reply_markup=keyboard
            )

    except Exception as e:
        await message.answer("⚠️ An error occurred while accessing your data. Please try again later.")
        print(f"Firestore Error: {e}")  # Log error for debugging




@dp.message(Command("status"))
async def status_command(message: types.Message):
    user_id = str(message.from_user.id)
    user_ref = db.collection("users").document(user_id)
    user = user_ref.get()

    if user.exists:
        user_data = user.to_dict()
        diet = user_data.get("diet", "Not set")
        fasting = "Enabled" if user_data.get("fasting", False) else "Disabled"
        meals = user_data.get("meals_per_day", "Not set")
        weight = user_data.get("weight", "Unknown")
        goal = user_data.get("goal", "Not set")
        eating_window = user_data.get("eating_window", "Not set")

        status_text = (
            f"📊 *Your Current Settings:*\n\n"
            f"🍽 *Diet:* {diet}\n"
            f"⏳ *Fasting:* {fasting}\n"
            f"🍱 *Meals per Day:* {meals}\n"
            f"⚖️ *Current Weight:* {weight} kg\n"
            f"🎯 *Goal Weight:* {goal} kg\n"
            f"🕰 *Eating Window:* {eating_window}\n\n"
            "💡 *Tap a button below to update your details!*"
        )

        keyboard = get_start_keyboard(user_id)  

        await message.answer(status_text, parse_mode="Markdown", reply_markup=keyboard)
    else:
        await message.answer("⚠️ No data found. Please use /start to set up your profile.")

@dp.message(Command("setgoal"))
async def set_goal(message: types.Message):
    """Handles setting the user's goal weight."""
    user_id = str(message.from_user.id)
    parts = message.text.split()

    if len(parts) < 2:
        await message.answer("🎯 *Set Your Goal Weight*\n\n"
                             "Please enter your target weight in kg.\n"
                             "Example: `/setgoal 75`",
                             parse_mode="Markdown")
        return

    try:
        goal_weight = float(parts[1])
        db.collection("users").document(user_id).update({"goal": goal_weight})

        await message.answer(f"✅ *Goal Updated!*\n\n"
                             f"🎯 Your target weight is now *{goal_weight} kg*.",
                             parse_mode="Markdown")
    except ValueError:
        await message.answer("⚠️ *Invalid input!*\n\n"
                             "Please enter a valid number. Example: `/setgoal 75`",
                             parse_mode="Markdown")


@dp.message(Command("logweight"))
async def log_weight(message: types.Message):
    """Handles logging the user's current weight."""
    user_id = str(message.from_user.id)
    parts = message.text.split()

    if len(parts) < 2:
        await message.answer("⚖️ *Log Your Current Weight*\n\n"
                             "Please enter your weight in kg.\n"
                             "Example: `/logweight 82.5`",
                             parse_mode="Markdown")
        return

    try:
        weight = float(parts[1])
        db.collection("users").document(user_id).update({"weight": weight})

        await message.answer(f"📊 *Weight Logged!*\n\n"
                             f"⚖️ Your current weight is *{weight} kg*.",
                             parse_mode="Markdown")
    except ValueError:
        await message.answer("⚠️ *Invalid input!*\n\n"
                             "Please enter a valid number. Example: `/logweight 82.5`",
                             parse_mode="Markdown")




@dp.message(Command("m"))
async def short_encouragement(message: types.Message):
    """Handles /m command to send motivation."""
    user_id = str(message.from_user.id)
    user_name = message.from_user.first_name  # Use Telegram first name
    response = await generate_encouragement(user_id, user_name)
    await message.answer(response)


# ⏰ Scheduled Message Sender
async def send_scheduled_messages(bot):  # Now expects bot
    timezone = pytz.timezone("Asia/Jerusalem")
    
    while True:
        now = datetime.now(timezone).strftime("%H:%M")

        if now == "08:00":
            users = await get_users_with_retry()
            if users:  # Only proceed if users were fetched successfully
                for user in users:
                    user_id = user.id
                    user_data = user.to_dict()
                    user_name = user_data.get("name", "Friend")

                    response = await generate_encouragement(user_id, user_name)

                    try:
                        await bot.send_message(user_id, response)  # ✅ bot is passed
                        await asyncio.sleep(1)  # Prevent Telegram rate limiting
                    except Exception as e:
                        print(f"Telegram Error for user {user_id}: {e}")

        await asyncio.sleep(60)  # Check every minute

        


@dp.message(Command("setdiet"))
async def set_diet(message: types.Message):
    """Set user's diet type."""
    user_id = str(message.from_user.id)
    parts = message.text.split(maxsplit=1)

    if len(parts) < 2:
        await message.answer("Please specify your diet type. Example: /setdiet keto")
        return

    diet_type = parts[1].strip().capitalize()

    allowed_diets = ["Keto", "Low-Carb", "Mediterranean", "Vegetarian", "Vegan", "Paleo", "Carnivore", "Standard", "Other"]

    if diet_type not in allowed_diets:
        await message.answer(f"Invalid diet type. Choose from: {', '.join(allowed_diets)}")
        return

    db.collection("users").document(user_id).update({"diet": diet_type})
    await message.answer(f"Your diet type is set to {diet_type} ✅")


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



@router.message(Command("setheight"))
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

@router.message(Command("setage"))
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

@router.message(Command("setgender"))
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


        
@dp.message()
async def handle_chat(message: types.Message):
    """Handles normal chat messages with AI, ensuring full messages are sent."""
    user_input = message.text.strip()

    if user_input.startswith("/"):
        return  # Ignore commands

    user_id = str(message.from_user.id)
    user_ref = db.collection("users").document(user_id)
    user = user_ref.get()

    user_name = message.from_user.first_name  # Default name
    diet = "unknown"
    fasting = "not specified"
    meals = "unknown"
    eating_window = ""

    if user.exists:
        user_data = user.to_dict()
        user_name = user_data.get("name", user_name)
        diet = user_data.get("diet", "unknown")
        fasting = "enabled" if user_data.get("fasting") else "disabled"
        meals = user_data.get("meals_per_day", "unknown")
        if user_data.get("fasting") and user_data.get("eating_window"):
            eating_window = f"Eating window: {user_data['eating_window']['start']} - {user_data['eating_window']['stop']}"

        # Construct full prompt with user details
        prompt = (
            f"You are {user_name}'s AI nutrition assistant. "
            f"They follow a {diet} diet, intermittent fasting is {fasting}, and they eat {meals} meals per day. {eating_window} "
            f"Avoid meal planning. Instead, provide general guidance and advice related to their question. "
            f"Please keep responses under 30 words. User message: {user_input}"
        )
    response = chat_with_ai(prompt)

    if response:
        await send_message_with_split(message.chat.id, response)
    else:
        await message.answer("Sorry, I didn't get that. Try again!")


async def set_bot_commands():
    commands = [
        BotCommand(command="start", description="Start the bot"),
        BotCommand(command="help", description="List available commands"),
        BotCommand(command="status", description="View your current progress"),
        BotCommand(command="setgoal", description="Set your target weight"),
        BotCommand(command="logweight", description="Log your current weight"),
        BotCommand(command="m", description="Get motivation"),
        BotCommand(command="myschedules", description="View your encouragement schedules"),
    ]
    await bot.set_my_commands(commands)

# # Flask app setup
# flask_app = Flask(__name__)




async def main():
    """Main async function to run the bot."""
    logger.info("Bot commands are being set...")
    await set_bot_commands()  

    # ✅ Ensure router is not already included
    dp.include_router(commands_router)  # ← Prevents duplicate registration

    # ✅ Start scheduled messages in the background
    asyncio.create_task(send_scheduled_messages(bot))  

    logger.info("Bot is starting polling...")
    await dp.start_polling(bot)  # ✅ Proper aiogram v3 polling


def run_bot():
    # Your bot logic here
    print("Bot is running...")

# Run FastAPI in a separate thread
def run_web_server():
    import uvicorn
    from web_app import app
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="debug")

async def on_startup(_):
    asyncio.create_task(send_scheduled_messages(bot))  # 🔹 Auto-send messages
    asyncio.create_task(cache_encouragements())  # 🔹 Keep cache full


# ✅ Run Web Server in a Separate Thread
thread = threading.Thread(target=run_web_server)
thread.daemon = True  # Make sure it stops with the main process
thread.start()

# ✅ Run the bot using asyncio event loop
if __name__ == "__main__":
    asyncio.run(main())  # Replaces custom event loop handling