# app/handlers/user.py

import json
from pathlib import Path
from typing import Dict

from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.keyboards.inline import get_approval_keyboard
from app.keyboards.menu import get_start_menu # <-- IMPORT new menu
from app.services.broadcaster import Broadcaster
from app.states.user_states import UserSubmission
from app.utils.message_helpers import get_message_type, get_report_header, get_log_message

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message, user_role: str, loc_path: Path):
    with open(loc_path, 'r', encoding='utf-8') as f:
        loc = json.load(f)
    keyboard = get_start_menu(user_role)
    await message.answer(loc["welcome"], reply_markup=keyboard)


def is_admin_or_owner(user_role: str) -> bool:
    return user_role in ["admin", "owner"]


async def handle_submission(
    bot: Bot,
    message: Message,
    subject: str,
    user_role: str,
    user_alias: str,
    config: Dict,
    loc_path: Path
):
    """
    Unified submission handler. Routes post based on user role.
    """
    if is_admin_or_owner(user_role):
        # Admin/Owner: Post directly to output channel
        await Broadcaster.post_to_output_channel(
            bot=bot,
            message=message,
            subject=subject,
            config=config,
            loc_path=loc_path,
            is_regular_user_post=False
        )
        # Log the direct post to the report group
        log_text = get_log_message(
            "admin_direct_post_log",
            loc_path,
            admin_alias=user_alias,
            admin_id=message.from_user.id
        )
        await bot.send_message(config["report_group_id"], log_text)
        await message.answer("پست شما با موفقیت مستقیماً در کانال منتشر شد.")
    else:
        # Regular user: Forward to report group for moderation
        report_header = get_report_header(
            loc_path,
            user_id=message.from_user.id,
            role='کاربر',
            subject=subject,
            message_type=get_message_type(message)
        )
        keyboard = get_approval_keyboard(message.from_user.id, subject)
        await Broadcaster.forward_to_report_group(
            bot, message, report_header, keyboard, config
        )
        with open(loc_path, 'r', encoding='utf-8') as f:
            loc = json.load(f)
        await message.answer(loc["submission_received"])


# --- /submit command flow ---
@router.message(Command("submit"))
async def cmd_submit(message: Message, state: FSMContext, loc_path: Path):
    with open(loc_path, 'r', encoding='utf-8') as f:
        loc = json.load(f)
    await message.answer(loc["ask_for_subject"])
    await state.set_state(UserSubmission.awaiting_subject)

@router.message(UserSubmission.awaiting_subject)
async def process_subject(message: Message, state: FSMContext):
    await state.update_data(subject=message.text)
    await message.answer("اکنون محتوای خود را ارسال کنید (متن، عکس، ویدیو و غیره).")
    await state.set_state(UserSubmission.awaiting_content)

@router.message(UserSubmission.awaiting_content)
async def process_content(
    message: Message, bot: Bot, state: FSMContext, user_role: str,
    user_alias: str, loc_path: Path, config: Dict
):
    data = await state.get_data()
    subject = data.get("subject", "نامشخص")
    await state.clear()
    await handle_submission(bot, message, subject, user_role, user_alias, config, loc_path)


# --- Direct message flow ---
@router.message(UserSubmission.awaiting_subject_for_direct_message)
async def process_subject_for_direct_message(
    message: Message, bot: Bot, state: FSMContext, user_role: str,
    user_alias: str, loc_path: Path, config: Dict
):
    data = await state.get_data()
    subject = message.text
    original_message_json = data.get("original_message")
    if not original_message_json:
        await state.clear()
        return
    original_message = Message.model_validate_json(original_message_json)
    await state.clear()
    await handle_submission(bot, original_message, subject, user_role, user_alias, config, loc_path)


@router.message(F.chat.type == "private")
async def direct_submission(message: Message, state: FSMContext, loc_path: Path):
    message_json = message.model_dump_json()
    await state.update_data(original_message=message_json)
    with open(loc_path, 'r', encoding='utf-8') as f:
        loc = json.load(f)
    await message.answer(loc["ask_for_subject"])
    await state.set_state(UserSubmission.awaiting_subject_for_direct_message)