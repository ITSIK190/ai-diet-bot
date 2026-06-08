from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def profile_keyboard(user_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👤 Name", callback_data="profile_name"),
            InlineKeyboardButton(text="🎂 Age", callback_data="profile_age"),
        ],
        [
            InlineKeyboardButton(text="🚻 Gender", callback_data="profile_gender"),
            InlineKeyboardButton(text="📏 Height", callback_data="profile_height"),
        ],
        [
            InlineKeyboardButton(text="⚖️ Weight", callback_data="profile_weight"),
            InlineKeyboardButton(text="🎯 Goal", callback_data="profile_goal"),
        ],
        [
            InlineKeyboardButton(text="🏋️ Activity", callback_data="profile_activity"),
            InlineKeyboardButton(text="🍽 Diet", callback_data="profile_diet"),
        ],
        [
            InlineKeyboardButton(text="🍱 Meals/Day", callback_data="profile_meals"),
            InlineKeyboardButton(text="⏳ Fasting", callback_data="profile_fasting"),
        ],
        [
            InlineKeyboardButton(text="📊 View Profile", callback_data="profile_view"),
            InlineKeyboardButton(text="💪 Calc BMI", callback_data="profile_bmi"),
        ],
    ])


def gender_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="♂️ Male", callback_data="gender_Male"),
            InlineKeyboardButton(text="♀️ Female", callback_data="gender_Female"),
            InlineKeyboardButton(text="⚧ Other", callback_data="gender_Other"),
        ],
        [InlineKeyboardButton(text="🔙 Back", callback_data="profile_back")],
    ])


def activity_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🪑 Sedentary", callback_data="activity_sedentary"),
            InlineKeyboardButton(text="🚶 Light", callback_data="activity_light"),
        ],
        [
            InlineKeyboardButton(text="🏃 Moderate", callback_data="activity_moderate"),
            InlineKeyboardButton(text="💪 Active", callback_data="activity_active"),
        ],
        [
            InlineKeyboardButton(text="🔥 Very Active", callback_data="activity_very active"),
        ],
        [InlineKeyboardButton(text="🔙 Back", callback_data="profile_back")],
    ])


def fasting_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Enable", callback_data="fasting_yes"),
            InlineKeyboardButton(text="❌ Disable", callback_data="fasting_no"),
        ],
        [InlineKeyboardButton(text="🔙 Back", callback_data="profile_back")],
    ])


def meals_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="1", callback_data="meals_1"),
            InlineKeyboardButton(text="2", callback_data="meals_2"),
            InlineKeyboardButton(text="3", callback_data="meals_3"),
        ],
        [
            InlineKeyboardButton(text="4", callback_data="meals_4"),
            InlineKeyboardButton(text="5", callback_data="meals_5"),
            InlineKeyboardButton(text="6", callback_data="meals_6"),
        ],
        [InlineKeyboardButton(text="🔙 Back", callback_data="profile_back")],
    ])


def cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancel", callback_data="profile_cancel")],
    ])


def schedule_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Add", callback_data="sched_add"),
            InlineKeyboardButton(text="📋 View", callback_data="sched_view"),
        ],
        [
            InlineKeyboardButton(text="✏️ Edit", callback_data="sched_edit"),
            InlineKeyboardButton(text="🗑 Delete", callback_data="sched_delete"),
        ],
        [InlineKeyboardButton(text="🔙 Back", callback_data="profile_back")],
    ])


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 My Profile", callback_data="menu_profile")],
        [InlineKeyboardButton(text="⏰ Schedules", callback_data="menu_schedules")],
        [InlineKeyboardButton(text="💬 AI Coach", callback_data="menu_chat")],
    ])
