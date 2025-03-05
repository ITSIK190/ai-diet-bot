from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram import Router, types
from google.cloud import firestore
from aiogram.filters import Command

router = Router()

@router.message(Command("profile"))
async def profile_command(message: types.Message):
    """Sends an inline button to open the Web App form."""
    user_id = str(message.from_user.id)
    db = firestore.client()
    user_doc = db.collection("users").document(user_id).get()

    if not user_doc.exists:
        await message.answer("❌ *No data found!*\n\nPlease set your weight, height, age, and gender first.", parse_mode="Markdown")
        return

    # Inline button to open the Web App
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Edit Profile", web_app=WebAppInfo(url="https://your-web-app-url.com"))]
        ]
    )

    user_data = user_doc.to_dict()
    weight = user_data.get("weight_kg", "Not set")
    height = user_data.get("height_cm", "Not set")
    age = user_data.get("age", "Not set")
    gender = user_data.get("gender", "Not set")
    activity = user_data.get("activity", "Not set")
    goal = user_data.get("goal", "Not set")

    await message.answer(
        f"👤 *Your Profile:*\n"
        f"⚖️ Weight: {weight} kg\n"
        f"📏 Height: {height} cm\n"
        f"🎂 Age: {age}\n"
        f"🚻 Gender: {gender}\n"
        f"🏋️ Activity Level: {activity}\n"
        f"🎯 Goal Weight: {goal} kg\n\n"
        f"Click below to edit your profile:",
        parse_mode="Markdown",
        reply_markup=keyboard
    )
