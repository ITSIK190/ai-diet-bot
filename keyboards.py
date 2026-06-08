from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo


def profile_webapp_keyboard(webapp_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Edit Profile", web_app=WebAppInfo(url=webapp_url))],
        [InlineKeyboardButton(text="Calc BMI", callback_data="profile_bmi")],
    ])


def schedule_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Add", callback_data="sched_add"),
            InlineKeyboardButton(text="View", callback_data="sched_view"),
        ],
        [
            InlineKeyboardButton(text="Edit", callback_data="sched_edit"),
            InlineKeyboardButton(text="Delete", callback_data="sched_delete"),
        ],
        [InlineKeyboardButton(text="Back", callback_data="profile_back")],
    ])


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="My Profile", callback_data="menu_profile")],
        [InlineKeyboardButton(text="Schedules", callback_data="menu_schedules")],
        [InlineKeyboardButton(text="AI Coach", callback_data="menu_chat")],
    ])
