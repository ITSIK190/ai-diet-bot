import os
import json
import firebase_admin
from firebase_admin import credentials, firestore
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from fastapi import FastAPI

# Load Firebase credentials
import json
from firebase_admin import credentials

firebase_credentials = json.loads(os.getenv("FIREBASE_CREDENTIALS"))
cred = credentials.Certificate(firebase_credentials)

firebase_admin.initialize_app(cred)
db = firestore.client()

# Load Telegram token from Railway env
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
app = FastAPI()

@app.get("/")
async def home():
    return {"message": "AI Dietitian Bot is running!"}

@dp.message(Command("start"))
async def start(message: types.Message):
    user_id = str(message.from_user.id)
    
    # Check if user exists in Firebase
    user_ref = db.collection("users").document(user_id)
    user = user_ref.get()

    if user.exists:
        await message.answer("Welcome back! How’s your diet going?")
    else:
        # New user, ask for weight
        await message.answer("Welcome! Please enter your weight (kg):")
        user_ref.set({"user_id": user_id})  # Create user entry

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
