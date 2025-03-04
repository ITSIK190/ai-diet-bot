from aiogram import Router, types
from aiogram.filters import Command
from firebase_admin import firestore
from bmi_calculator import fetch_and_store_bmi

router = Router()

@router.message(Command("bmi"))
async def bmi_command(message: types.Message):
    """Handles the /bmi command by fetching user data, calculating BMI, and storing the result."""
    user_id = str(message.from_user.id)
    db = firestore.client()
    user_doc = db.collection("users").document(user_id).get()

    if not user_doc.exists:
        await message.answer("❌ *No data found!*\n\nPlease set your weight, height, age, and gender first.", parse_mode="Markdown")
        return

    user_data = user_doc.to_dict()

    try:
        weight = user_data.get("weight_lbs")
        height = user_data.get("height_inches")
        age = user_data.get("age")
        gender = user_data.get("gender")
        goal_weight = user_data.get("goal")

        if not all([weight, height, age, gender]):
            await message.answer("⚠️ *Missing information!*\n\nPlease set your weight, height, age, and gender using the appropriate commands.", parse_mode="Markdown")
            return

        # Calculate BMI & daily calories
        bmi_result = fetch_and_store_bmi(
            user_id=user_id,
            weight_lbs=weight,
            height_inches=height,
            age=age,
            gender=gender,
            goal_weight=goal_weight
        )

        # Store BMI and daily calories in Firestore
        db.collection("users").document(user_id).update({
            "bmi": bmi_result.get("bmi"),
            "daily_calories": bmi_result.get("daily_calories")
        })

        # Send response to the user
        await message.answer(
            f"📊 *Your BMI & Calories Stored!*\n\n"
            f"💪 *BMI:* {bmi_result.get('bmi'):.2f}\n"
            f"🔥 *Daily Calories:* {bmi_result.get('daily_calories')} kcal\n\n"
            f"🎯 Goal: {goal_weight} kg",
            parse_mode="Markdown"
        )

    except Exception as e:
        await message.answer(f"⚠️ *Error:* {str(e)}", parse_mode="Markdown")
