from aiogram import Router, types
from aiogram.filters import Command
from firebase_admin import firestore
from bmi_calculator import fetch_and_store_bmi, calculate_goal_calories

router = Router()
@router.message(Command("bmi"))
async def bmi_command(message: types.Message):
    """Handles the /bmi command by fetching user data, calculating BMI, TDEE, and goal calories."""
    user_id = str(message.from_user.id)
    db = firestore.client()
    user_doc = db.collection("users").document(user_id).get()

    if not user_doc.exists:
        await message.answer("❌ *No data found!*\n\nPlease set your weight, height, age, and gender first.", parse_mode="Markdown")
        return

    user_data = user_doc.to_dict()

    try:
        weight = user_data.get("weight_kg")
        height = user_data.get("height_cm")
        age = user_data.get("age")
        gender = user_data.get("gender")
        goal_weight = user_data.get("goal")
        activity_level = user_data.get("activity", "sedentary")  # Default to sedentary

        if not all([weight, height, age, gender, goal_weight]):
            await message.answer("⚠️ *Missing information!*\n\nPlease set your weight, height, age, and gender.", parse_mode="Markdown")
            return

        # Calculate BMI & goal calories
        bmi_result = weight / ((height / 100) ** 2)
        daily_calories = calculate_goal_calories(weight, height, age, gender, activity_level, goal_weight)

        # Store results in Firestore
        db.collection("users").document(user_id).update({
            "bmi": round(bmi_result, 2),
            "daily_calories": daily_calories
        })

        # Respond to user
        await message.answer(
            f"📊 *Your BMI & Goal Calories Stored!*\n\n"
            f"💪 *BMI:* {bmi_result:.2f}\n"
            f"🔥 *Calories Needed:* {daily_calories} kcal/day\n\n"
            f"🎯 Goal: {goal_weight} kg",
            parse_mode="Markdown"
        )

    except Exception as e:
        await message.answer(f"⚠️ *Error:* {str(e)}", parse_mode="Markdown")
