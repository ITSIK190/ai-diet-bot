import os
import json
import base64
import firebase_admin
from firebase_admin import credentials, firestore
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from fastapi import FastAPI

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
