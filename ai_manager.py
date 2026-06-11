import os
import datetime
import asyncio
import pytz
from openai import AsyncOpenAI, APIStatusError
from local_db import get_user

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL = "openrouter/owl-alpha"

client = AsyncOpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1",
    timeout=120,
    max_retries=3,
)


def _build_system_prompt(user_data: dict) -> str:
    name = user_data.get("name", "Friend") or "Friend"
    diet = user_data.get("diet", "") or "unspecified"
    weight = user_data.get("weight_kg", 0) or "unknown"
    goal = user_data.get("goal_kg", 0) or "not set"
    meals = user_data.get("meals_per_day", 0) or "unknown"
    activity = user_data.get("activity", "") or "unspecified"
    gender = user_data.get("gender", "") or "unspecified"
    age = user_data.get("age", 0) or "unknown"
    height = user_data.get("height_cm", 0) or "unknown"
    bmi = user_data.get("bmi", 0)
    calories = user_data.get("daily_calories", 0)
    fasting = user_data.get("fasting", 0)
    fasting_start = user_data.get("fasting_start", "")
    fasting_end = user_data.get("fasting_stop", "")

    tz = pytz.timezone("Asia/Jerusalem")
    now = datetime.datetime.now(tz).strftime("%H:%M")

    prompt = f"You are {name}'s personal dietitian. "
    prompt += f"Profile: {age} years old, {gender}, {height}cm, {weight}kg, goal {goal}kg. "
    prompt += f"Activity: {activity}. Diet: {diet}. Meals/day: {meals}. "
    if bmi:
        prompt += f"BMI: {bmi:.1f}. "
    if calories:
        prompt += f"Daily calorie target: {calories}. "
    if fasting and fasting_start and fasting_end:
        prompt += f"Fasting window: {fasting_start}-{fasting_end}. "
    prompt += f"Current time in Israel: {now}. "
    prompt += "Keep responses under 60 words. Be motivating and concise."
    return prompt


async def generate_response(user_id: str, prompt: str, memory: list = None) -> str:
    try:
        user_data = await get_user(user_id)
        if not user_data:
            user_data = {}

        system_prompt = _build_system_prompt(user_data)

        messages = [{"role": "system", "content": system_prompt}]

        if memory:
            for m in memory[-10:]:
                content = m.get("content", "").strip()
                if content:
                    messages.append({"role": m["role"], "content": content})

        messages.append({"role": "user", "content": prompt})

        for attempt in range(3):
            try:
                resp = await client.chat.completions.create(
                    model=MODEL,
                    messages=messages,
                    max_tokens=200,
                    temperature=0.7,
                )
                return resp.choices[0].message.content.strip()
            except APIStatusError as e:
                if e.status_code == 429:
                    await asyncio.sleep(2 * (attempt + 1))
                    continue
                raise
        return "Sorry, the AI is busy right now. Please try again in a moment."

    except Exception as e:
        print(f"AI error: {e}")
        return "Sorry, something went wrong. Please try again."


async def generate_nudge(user_id: str) -> str:
    try:
        user_data = await get_user(user_id)
        if not user_data:
            user_data = {}

        system_prompt = _build_system_prompt(user_data)
        system_prompt += " Give a short personalized encouragement (2-3 sentences). No questions, just motivation."

        for attempt in range(3):
            try:
                resp = await client.chat.completions.create(
                    model=MODEL,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": "Give me a quick encouragement boost!"},
                    ],
                    max_tokens=100,
                    temperature=0.8,
                )
                return resp.choices[0].message.content.strip()
            except APIStatusError as e:
                if e.status_code == 429:
                    await asyncio.sleep(2 * (attempt + 1))
                    continue
                raise
        return "Keep going, you're doing great!"

    except Exception as e:
        print(f"AI error: {e}")
        return "Keep going, you're doing great!"
