import os
import json
import base64
import firebase_admin
import groq
from firebase_admin import credentials, firestore
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from fastapi import FastAPI

# 🔹 Load API keys from environment variables
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY is not set!")
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN is not set!")

# 🔹 Initialize Groq client
client = groq.Client(api_key=GROQ_API_KEY)

# 🔹 Load Firebase credentials from Base64 environment variable
firebase_credentials_b64 = os.getenv("FIREBASE_CREDENTIALS")
if firebase_credentials_b64:
    firebase_credentials_json = base64.b64decode(firebase_credentials_b64).decode("utf-8")
    firebase_credentials = json.loads(firebase_credentials_json)
else:
    raise ValueError("FIREBASE_CREDENTIALS is not set or invalid.")

# 🔹 Initialize Firebase
cred = credentials.Certificate(firebase_credentials)
firebase_admin.initialize_app(cred)
db = firestore.client()

# 🔹 Initialize Telegram bot & FastAPI
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
app = FastAPI()

@app.get("/")
async def home():
    return {"message": "AI Dietitian Bot is running!"}

# 🔹 Telegram Bot Commands
@dp.message(Command("start"))
async def start(message: types.Message):
    user_id = str(message.from_user.id)
    user_ref = db.collection("users").document(user_id)
    user = user_ref.get()

    if user.exists:
        user_data = user.to_dict()
        weight = user_data.get("weight", "Unknown")
        goal = user_data.get("goal", "Not set")
        await message.answer(f"Welcome back!\nYour last recorded weight: {weight} kg\nYour goal: {goal}")
    else:
        await message.answer("Welcome! Please enter your weight (kg):")
        user_ref.set({"user_id": user_id})  # Create user entry

@dp.message(Command("setgoal"))
async def set_goal(message: types.Message):
    user_id = str(message.from_user.id)
    parts = message.text.split()
    
    if len(parts) < 2:
        await message.answer("Please enter your goal weight. Example: /setgoal 75")
        return

    try:
        goal_weight = float(parts[1])
        db.collection("users").document(user_id).update({"goal": goal_weight})
        await message.answer(f"Goal weight set to {goal_weight} kg! Keep going! 💪")
    except ValueError:
        await message.answer("Invalid weight. Please enter a number.")

@dp.message(Command("logweight"))
async def log_weight(message: types.Message):
    user_id = str(message.from_user.id)
    parts = message.text.split()

    if len(parts) < 2:
        await message.answer("Please enter your weight. Example: /logweight 82.5")
        return

    try:
        weight = float(parts[1])
        db.collection("users").document(user_id).update({"weight": weight})
        await message.answer(f"Got it! Your weight is now recorded as {weight} kg. 🎯")
    except ValueError:
        await message.answer("Invalid weight. Please enter a number.")

# 🔹 AI Diet Advice Command
@dp.message(Command("advice"))
async def get_advice(message: types.Message):
    user_input = message.text.replace("/advice", "").strip()
    
    if not user_input:
        user_input = "Give me a healthy keto meal plan for today."

    response = client.chat.completions.create(
        model="llama3-8b-8192",
        messages=[
            {"role": "system", "content": "You are a diet assistant. Provide helpful and healthy meal suggestions."},
            {"role": "user", "content": user_input}
        ]
    )

    diet_tip = response.choices[0].message.content  # Extract the generated response
    await message.answer(f"🧠 AI Advice: {diet_tip}")

# 🔹 Start the bot
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
