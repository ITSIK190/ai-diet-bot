# -*- coding: utf-8 -*-
import os
import asyncio
import pytz
from aiogram import Bot, Dispatcher, types, Router, F
from aiogram.filters import Command
from fastapi import FastAPI
from datetime import datetime
from gradio_client import Client
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import BotCommand
from firebase_config import db  # Import Firebase Firestore instance
from bmi_handler import router as bmi_router  # Import the BMI command router



# Load Telegram bot token from environment variable
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN is not set!")

# Initialize bot and dispatcher
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
app = FastAPI()
router = Router()
# Register the BMI router
dp.include_router(bmi_router)

# Initialize Gradio Client
HF_SPACE_NAME = "Itsik190/ai-diet-coach"
client = Client(HF_SPACE_NAME)

# English Translations
WELCOME_BACK = "Welcome back, {name}!\nYour last recorded weight: {weight} kg\nYour goal: {goal} kg"
WELCOME_NEW = "Welcome, {name}! Please enter your weight (in kg):"
GOAL_SET = "Your goal is now set to {goal} kg! Keep up the great work! 💪"
WEIGHT_LOGGED = "Got it! Your weight has been logged as {weight} kg. 🎯"
INVALID_WEIGHT = "Invalid weight. Please enter a number."
ADVICE_PREFIX = "🧠 AI Advice: "
ENCOURAGEMENT = "{name}, you're doing great! Keep pushing towards your goals! 🎯"

@app.get("/")
async def home():
    return {"message": "AI Dietitian Bot is running!"}

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

    keyboard = get_start_keyboard()

    await message.answer(help_text, parse_mode="MarkdownV2", reply_markup=keyboard)




def get_start_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
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
                InlineKeyboardButton("Open Profile Form", url="http://yourdomain.com")  # Replace with your FastAPI URL
            ]
        ]
    )
    return keyboard


@dp.message(Command("start"))
async def start(message: types.Message):
    user_id = str(message.from_user.id)
    user_name = message.from_user.first_name
    user_ref = db.collection("users").document(user_id)
    user = user_ref.get()

    # Create menu buttons
    keyboard = get_start_keyboard() 
    

    if user.exists:
        user_data = user.to_dict()
        weight = user_data.get("weight", "Unknown")
        goal = user_data.get("goal", "Not set")
        await message.answer(WELCOME_BACK.format(name=user_name, weight=weight, goal=goal), reply_markup=keyboard)
    else:
        await message.answer(WELCOME_NEW.format(name=user_name), reply_markup=keyboard)
        user_ref.set({"user_id": user_id, "name": user_name})

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

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 Set Diet", callback_data="set_diet"),
             InlineKeyboardButton(text="⏳ Set Fasting", callback_data="set_fasting")],
            [InlineKeyboardButton(text="🍱 Set Meals", callback_data="set_meals"),
             InlineKeyboardButton(text="⚖️ Set Weight", callback_data="set_weight")],
            [InlineKeyboardButton(text="🎯 Set Goal", callback_data="set_goal"),
             InlineKeyboardButton(text="🕰 Set Eating Window", callback_data="set_eating_window")]
        ])

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


@dp.message(Command("advice"))
async def get_advice(message: types.Message):
    user_input = message.text.replace("/advice", "").strip()
    if not user_input:
        user_input = "Give me a healthy ketogenic meal plan for today."
    response = chat_with_ai(user_input)
    await message.answer(ADVICE_PREFIX + response)

async def generate_encouragement(user_id, user_name):
    """Generates a short AI-based encouragement message using stored user data."""
    user_ref = db.collection("users").document(user_id)
    user = user_ref.get()

    if not user.exists:
        return "I don’t have your details yet! Please log your weight with /logweight."

    user_data = user.to_dict()
    weight = user_data.get("weight")
    goal_weight = user_data.get("goal")

    # Ensure at least one parameter is included
    if weight and goal_weight:
        prompt = f"Give {user_name} a short, highly motivating message. They currently weigh {weight} kg and their goal is {goal_weight} kg. Keep it under 20 words."
    elif weight:
        prompt = f"Give {user_name} a short, highly motivating message. They currently weigh {weight} kg. Keep it under 20 words."
    elif goal_weight:
        prompt = f"Give {user_name} a short, highly motivating message. Their goal is {goal_weight} kg. Keep it under 20 words."
    else:
        prompt = f"Give {user_name} a short, highly motivating message about staying healthy and fit. Keep it under 20 words."

    return chat_with_ai(prompt)


@dp.message(Command("m"))
async def short_encouragement(message: types.Message):
    """Handles /m command to send motivation."""
    user_id = str(message.from_user.id)
    user_name = message.from_user.first_name  # Use Telegram first name
    response = await generate_encouragement(user_id, user_name)
    await message.answer(response)


async def send_scheduled_messages():
    timezone = pytz.timezone("Asia/Jerusalem")
    while True:
        now = datetime.now(timezone).strftime("%H:%M")

        if now == "08:00":
            users = db.collection("users").stream()
            for user in users:
                user_id = user.id
                user_data = user.to_dict()
                user_name = user_data.get("name", "Friend")

                response = await generate_encouragement(user_id, user_name)
                await bot.send_message(user_id, response)

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

def chat_with_ai(prompt):
    """Send user message to Hugging Face model and return response."""
    try:


        print(f"Sending to HF: {prompt}")  # Debug log
        
        response = client.predict(
            message=prompt,
            api_name="/chat"
        )

        if not response or not response.strip():  
            print("HF Response was empty or None")  
            return "I couldn't process your request. Please try again!"

        # Truncate AI response instead of user input
        truncated_response = truncate_text(response.strip(), max_words=30)

        print(f"HF Response: {truncated_response}")  # Debug log
        return truncated_response
    except Exception as e:
        print(f"Error communicating with HF: {e}")
        return "Sorry, something went wrong! Please try again later."
        
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
    ]
    await bot.set_my_commands(commands)

async def main():
    await set_bot_commands()  # Set commands inside main
    asyncio.create_task(send_scheduled_messages())  # Start scheduled messages
    await dp.start_polling(bot)

async def main():
    # Start long polling for the bot to receive messages
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())  # Correct polling method

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)

    
