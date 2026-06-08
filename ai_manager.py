import os
import datetime
import pytz
from openai import AsyncOpenAI
from local_db import get_user

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL = "openrouter/owl-alpha"

client = AsyncOpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1",
)


async def generate_response(user_id: str, prompt: str) -> str:
    try:
        user_data = await get_user(user_id)

        if user_data:
            name = user_data.get("name", "Friend") or "Friend"
            diet = user_data.get("diet", "") or "unspecified"
            weight = user_data.get("weight_kg", 0) or "unknown"
            goal = user_data.get("goal_kg", 0) or "not set"
            meals = user_data.get("meals_per_day", 0) or "unknown"
            fasting = user_data.get("fasting", 0)
            fasting_start = user_data.get("fasting_start", "")
            fasting_end = user_data.get("fasting_stop", "")
            bmi = user_data.get("bmi", 0)
            calories = user_data.get("daily_calories", 0)
        else:
            name, diet, weight, goal, meals = "Friend", "unspecified", "unknown", "not set", "unknown"
            fasting, fasting_start, fasting_end, bmi, calories = 0, "", "", 0, 0

        tz = pytz.timezone("Asia/Jerusalem")
        now = datetime.datetime.now(tz).strftime("%H:%M")

        ctx = f"You are {name}'s personal dietitian. "
        ctx += f"Diet: {diet}, Weight: {weight}kg, Goal: {goal}kg, Meals/day: {meals}. "
        if bmi:
            ctx += f"BMI: {bmi}. "
        if calories:
            ctx += f"Daily calories: {calories}. "
        if fasting and fasting_start and fasting_end:
            ctx += f"Fasting window: {fasting_start}-{fasting_end}. "
        ctx += f"Current time in Israel: {now}. "
        ctx += f"Keep responses under 60 words. "
        ctx += f"User message: {prompt}"

        resp = await client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are a motivating, concise personal dietitian."},
                {"role": "user", "content": ctx},
            ],
            max_tokens=200,
            temperature=0.7,
        )
        return resp.choices[0].message.content.strip()

    except Exception as e:
        print(f"AI error: {e}")
        return "Sorry, something went wrong. Please try again."
