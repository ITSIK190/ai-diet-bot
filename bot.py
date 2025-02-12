import os
import json
import base64
import firebase_admin
import openai
import groq
import asyncio
from firebase_admin import credentials, firestore
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from fastapi import FastAPI
from datetime import datetime, timedelta

# Set Groq API Base & Key
openai.api_base = "https://api.groq.com/openai/v1"
openai.api_key = os.getenv("GROQ_API_KEY")

# Function to interact with the LLM
def chat_with_groq(prompt):
    response = openai.ChatCompletion.create(
        model="mixtral",
        messages=[{"role": "user", "content": prompt}]
    )
    return response["choices"][0]["message"]["content"]

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

# Hebrew translations
WELCOME_BACK = "ברוך שובך, {name}!\nהמשקל האחרון שלך: {weight} ק"ג\nהמטרה שלך: {goal} ק"ג"
WELCOME_NEW = "ברוך הבא, {name}! אנא הזן את המשקל שלך (בק"ג):"
GOAL_SET = "המטרה שלך נקבעה ל-{goal} ק"ג! המשך כך! 💪"
WEIGHT_LOGGED = "קיבלתי! המשקל שלך נרשם כ-{weight} ק"ג. 🎯"
INVALID_WEIGHT = "משקל לא תקין. אנא הזן מספר."
ADVICE_PREFIX = "🧠 עצת AI: "
ENCOURAGEMENT = "{name}, אתה עושה עבודה נהדרת! המשך לשמור על היעדים שלך! 🎯"

@app.get("/")
async def home():
    return {"message": "AI Dietitian Bot is running!"}

@dp.message(Command("start"))
async def start(message: types.Message):
    user_id = str(message.from_user.id)
    user_name = message.from_user.first_name
    
    # Check if user exists in Firebase
    user_ref = db.collection("users").document(user_id)
    user = user_ref.get()

    if user.exists:
        user_data = user.to_dict()
        weight = user_data.get("weight", "לא ידוע")
        goal = user_data.get("goal", "לא נקבע")
        await message.answer(WELCOME_BACK.format(name=user_name, weight=weight, goal=goal))
    else:
        await message.answer(WELCOME_NEW.format(name=user_name))
        user_ref.set({"user_id": user_id, "name": user_name})  # Create user entry

@dp.message(Command("setgoal"))
async def set_goal(message: types.Message):
    user_id = str(message.from_user.id)
    parts = message.text.split()
    
    if len(parts) < 2:
        await message.answer("אנא הזן את משקל היעד שלך. דוגמא: /setgoal 75")
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
        await message.answer("אנא הזן את המשקל שלך. דוגמא: /logweight 82.5")
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
        user_input = "תן לי תפריט קטוגני בריא להיום."

    response = chat_with_groq(user_input)
    await message.answer(ADVICE_PREFIX + response)

async def send_encouragements():
    while True:
        users = db.collection("users").stream()
        for user in users:
            user_data = user.to_dict()
            name = user_data.get("name", "חבר")
            user_id = user.id
            await bot.send_message(user_id, ENCOURAGEMENT.format(name=name))
        await asyncio.sleep(14400)  # 4 hours

async def main():
    asyncio.create_task(send_encouragements())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
