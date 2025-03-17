from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

BASE_URL = "https://ai-diet-bot-production.up.railway.app/"

def get_start_keyboard(user_id: str):
    """Generate the start keyboard with inline buttons."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📋 Set Diet", callback_data="set_diet"),
            InlineKeyboardButton(text="⏳ Set Fasting", callback_data="set_fasting")
        ],
        [
            InlineKeyboardButton(text="🍱 Set Meals", callback_data="set_meals"),
            InlineKeyboardButton(text="⚖️ Set Weight", callback_data="set_weight")
        ],
        [
            InlineKeyboardButton(text="🎯 Set Goal", callback_data="set_goal"),
            InlineKeyboardButton(text="📊 View Status", callback_data="view_status")
        ],
        [
            InlineKeyboardButton(text="📝 Edit Profile", url=f"{BASE_URL}?user_id={user_id}"),
            InlineKeyboardButton(text="🚀 Mini App", url=f"{BASE_URL}?user_id={user_id}&mini_app=true")
        ]
    ])
    return keyboard
