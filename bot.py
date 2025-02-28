# -*- coding: utf-8 -*-
import os
import json
import base64
import firebase_admin
import asyncio
import pytz
from firebase_admin import credentials, firestore
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from fastapi import FastAPI
from datetime import datetime
from gradio_client import Client

# Load Firebase credentials from Base64 environment variable
firebase_credentials_b64 = os.getenv("FIREBASE_CREDENTIALS")
if firebase_credentials_b64:
    firebase_credentials_json = base64.b64decode(firebase_credentials_b64).decode("utf-8")
    firebase_credentials = json.loads(firebase_credentials_json)
else:
    raise ValueError("FIREBASE_CREDENTIALS is not set or invalid.")

# Initialize Firebase
cred = credentials.Certificate(firebase_credentials)
firebase_admin.initialize_app(cred)
db = firestore.client()

# Load Telegram bot token from environment variable
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN is not set!")

# Initialize bot and dispatcher
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
app = FastAPI()

# Initialize Gradio Client
HF_SPACE_NAME = "Itsik190/ai-diet-coach"
client = Client(HF_SPACE_NAME)

# Scheduled Messages Dictionary
SCHEDULED_MESSAGES = {
    "08:00": "☕ Make yourself a coffee, have a great day, and stay strong!",
    # "11:00": "🍽️ Just one more hour until lunch.",
    # "12:00": "🍲 Enjoy your meal!",
    # "18:00": "🥗 Start preparing dinner and get ready for the fast."
}

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

def chat_with_ai(prompt):
    """Send user message to Hugging Face model and return response."""
    try:
        print(f"Sending to HF: {prompt}")  # Debug log
        response = client.predict(
            message=prompt,  # Ensure correct format
            api_name="/chat"  # Use the same endpoint as /advice
        )
        print(f"HF Response: {response}")  # Debug log
        return response
    except Exception as e:
        print("Error:", e)
        return "Sorry, something went wrong! Please try again later."



@dp.message()
async def handle_chat(message: types.Message):
    """Handles regular chat messages and sends them to the AI model."""
    user_input = message.text.strip()
    if user_input:  # Ensure message is not empty
        response = chat_with_ai(user_input)
        await message.answer(response)


@dp.message(Command("start"))
async def start(message: types.Message):
    user_id = str(message.from_user.id)
    user_name = message.from_user.first_name
    user_ref = db.collection("users").document(user_id)
    user = user_ref.get()

    if user.exists:
        user_data = user.to_dict()
        weight = user_data.get("weight", "Unknown")
        goal = user_data.get("goal", "Not set")
        await message.answer(WELCOME_BACK.format(name=user_name, weight=weight, goal=goal))
    else:
        await message.answer(WELCOME_NEW.format(name=user_name))
        user_ref.set({"user_id": user_id, "name": user_name})

@dp.message(Command("setgoal"))
async def set_goal(message: types.Message):
    user_id = str(message.from_user.id)
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Please enter your target weight. Example: /setgoal 75")
        return
    try:
        goal_weight = float(parts[1])
        db.collection("users").document(user_id).update({"goal": goal_weight})
        await message.answer(GOAL_SET.format(goal=goal_weight))
    except ValueError:
        await message.answer(INVALID_WEIGHT)

@dp.message(Command("logweight"))
async def log_weight(message: types.Message):
    user_id = str(message.from_user.id)
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Please enter your current weight. Example: /logweight 82.5")
        return
    try:
        weight = float(parts[1])
        db.collection("users").document(user_id).update({"weight": weight})
        await message.answer(WEIGHT_LOGGED.format(weight=weight))
    except ValueError:
        await message.answer(INVALID_WEIGHT)

@dp.message(Command("advice"))
async def get_advice(message: types.Message):
    user_input = message.text.replace("/advice", "").strip()
    if not user_input:
        user_input = "Give me a healthy ketogenic meal plan for today."
    response = chat_with_ai(user_input)
    await message.answer(ADVICE_PREFIX + response)

async def send_scheduled_messages():
    timezone = pytz.timezone("Asia/Jerusalem")
    while True:
        now = datetime.now(timezone).strftime("%H:%M")
        if now in SCHEDULED_MESSAGES:
            users = db.collection("users").stream()
            for user in users:
                user_id = user.id
                await bot.send_message(user_id, SCHEDULED_MESSAGES[now])
        await asyncio.sleep(60)  # Check every minute

@dp.message()
async def handle_chat(message: types.Message):
    user_input = message.text.strip()
    response = chat_with_ai(user_input)
    await message.answer(response)


async def main():
    asyncio.create_task(send_scheduled_messages())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
