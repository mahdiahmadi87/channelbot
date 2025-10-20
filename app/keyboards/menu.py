# app/keyboards/menu.py

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_start_menu(user_role: str) -> InlineKeyboardMarkup:
    """
    Generates the start menu keyboard based on the user's role.
    """
    buttons = [
        [InlineKeyboardButton(text="✍️ ارسال پست جدید", callback_data="start_submit")]
    ]

    if user_role == "owner":
        buttons.extend([
            [InlineKeyboardButton(text="➕ افزودن ادمین", callback_data="start_add_admin")],
            [InlineKeyboardButton(text="➖ حذف ادمین", callback_data="start_remove_admin")]
        ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)
