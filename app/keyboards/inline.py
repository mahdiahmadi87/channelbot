from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_approval_keyboard(submitter_id: int, subject: str) -> InlineKeyboardMarkup:
    """Generates the inline keyboard for report messages."""
    
    # NOTE: Callback data has a 64-byte limit. Be mindful of subject length.
    # We truncate the subject to ensure it fits.
    truncated_subject = (subject[:30] + '..') if len(subject) > 30 else subject

    buttons = [
        [
            InlineKeyboardButton(text="تایید ✅", callback_data=f"approve:{submitter_id}:{truncated_subject}"),
            InlineKeyboardButton(text="حذف ❌", callback_data=f"delete:{submitter_id}")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)