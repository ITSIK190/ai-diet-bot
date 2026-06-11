import os
import datetime
import asyncio
import pytz
from openai import AsyncOpenAI, APIStatusError, APIConnectionError, APITimeoutError, RateLimitError
from local_db import get_user

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL = "openrouter/owl-alpha"

client = AsyncOpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1",
    timeout=120,
    max_retries=0,
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

    prompt = f"You are {name}'s personal dietitian and coach. "
    prompt += f"Profile: {age} years old, {gender}, {height}cm, {weight}kg, goal {goal}kg. "
    prompt += f"Activity: {activity}. Diet: {diet}. Meals/day: {meals}. "
    if bmi:
        prompt += f"BMI: {bmi:.1f}. "
    if calories and calories > 0:
        prompt += f"Daily calorie target: {calories}. "
    if fasting and fasting_start and fasting_end:
        prompt += f"Fasting window: {fasting_start}-{fasting_end}. "
    prompt += f"Current time in Israel: {now}. "
    prompt += "Be conversational, warm, and motivating. Keep responses under 80 words. "
    prompt += "Remember context from the conversation and refer back to things the user mentioned."
    return prompt


async def _call_api(messages: list, max_tokens: int = 200, temperature: float = 0.7) -> str:
    last_error = None
    for attempt in range(4):
        try:
            resp = await client.chat.completions.create(
                model=MODEL,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            content = resp.choices[0].message.content
            if content:
                return content.strip()
            last_error = "Empty response"
        except RateLimitError:
            last_error = "rate_limit"
            await asyncio.sleep(3 * (attempt + 1))
        except APITimeoutError:
            last_error = "timeout"
            await asyncio.sleep(2 * (attempt + 1))
        except APIConnectionError:
            last_error = "connection"
            await asyncio.sleep(2 * (attempt + 1))
        except APIStatusError as e:
            if e.status_code == 429:
                last_error = "rate_limit"
                await asyncio.sleep(3 * (attempt + 1))
            elif e.status_code >= 500:
                last_error = "server"
                await asyncio.sleep(2 * (attempt + 1))
            else:
                last_error = f"api_{e.status_code}"
                break
        except Exception as e:
            last_error = str(e)
            await asyncio.sleep(1)

    if last_error == "rate_limit":
        return "Sorry, I'm getting a lot of requests right now. Please try again in a minute."
    elif last_error == "timeout":
        return "Sorry, the response took too long. Please try again."
    elif last_error == "connection":
        return "Sorry, I'm having trouble connecting. Please check your internet and try again."
    elif last_error == "server":
        return "Sorry, the AI service is temporarily down. Please try again shortly."
    else:
        return "Sorry, something unexpected happened. Please try again."


async def generate_response(user_id: str, prompt: str, memory: list = None) -> str:
    user_data = await get_user(user_id) or {}
    system_prompt = _build_system_prompt(user_data)

    messages = [{"role": "system", "content": system_prompt}]

    if memory:
        for m in memory[-20:]:
            content = m.get("content", "").strip()
            if content:
                messages.append({"role": m["role"], "content": content})

    messages.append({"role": "user", "content": prompt})

    return await _call_api(messages, max_tokens=250, temperature=0.7)


async def generate_nudge(user_id: str, memory: list = None) -> str:
    user_data = await get_user(user_id) or {}
    system_prompt = _build_system_prompt(user_data)
    system_prompt += " Give a short personalized encouragement (2-3 sentences). "
    system_prompt += "Be warm and specific to the user's situation. No questions, just motivation. "
    system_prompt += "If you know their recent struggles or goals from conversation history, reference them."

    messages = [{"role": "system", "content": system_prompt}]

    if memory:
        for m in memory[-20:]:
            content = m.get("content", "").strip()
            if content:
                messages.append({"role": m["role"], "content": content})

    messages.append({"role": "user", "content": "Give me a quick encouragement boost!"})

    return await _call_api(messages, max_tokens=150, temperature=0.8)
