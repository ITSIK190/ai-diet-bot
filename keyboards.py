from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, ReplyKeyboardMarkup, KeyboardButton


def profile_webapp_keyboard(webapp_url: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Edit Profile", web_app=WebAppInfo(url=webapp_url))],
            [KeyboardButton(text="Nudge Me")],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
    )


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
