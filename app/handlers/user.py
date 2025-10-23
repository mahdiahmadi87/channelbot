import json
from pathlib import Path
from typing import Dict, List

from aiogram import F, Bot, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram_media_group import media_group_handler

from app.keyboards.inline import get_approval_keyboard
from app.keyboards.menu import get_start_menu
from app.services.broadcaster import Broadcaster
from app.states.user_states import UserSubmission
from app.utils.message_helpers import get_log_message, get_message_type, get_report_header

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
    messages: List[Message], # <-- Accepts a list
    subject: str,
    user_role: str,
    user_alias: str,
    config: Dict,
    loc_path: Path
):
    """Unified submission handler for both single messages and albums."""
    submitter_message = messages[0] # Use the first message for context

    if is_admin_or_owner(user_role):
        await Broadcaster.post_to_output_channel(
            bot=bot, messages=messages, subject=subject, config=config,
            loc_path=loc_path, is_regular_user_post=False
        )
        log_text = get_log_message(
            "admin_direct_post_log", loc_path,
            admin_alias=user_alias, admin_id=submitter_message.from_user.id
        )
        await bot.send_message(config["report_group_id"], log_text)
        await bot.send_message(submitter_message.chat.id, "پست شما با موفقیت مستقیماً در کانال منتشر شد.")
    else:
        report_header = get_report_header(
            loc_path, user_id=submitter_message.from_user.id, role='کاربر',
            subject=subject, message_type=f"آلبوم ({len(messages)})" if len(messages) > 1 else get_message_type(submitter_message)
        )
        keyboard = get_approval_keyboard(submitter_message.from_user.id, subject)
        await Broadcaster.forward_to_report_group(
            bot, messages, report_header, keyboard, config
        )
        with open(loc_path, 'r', encoding='utf-8') as f:
            loc = json.load(f)
        await bot.send_message(submitter_message.chat.id, loc["submission_received"])


async def start_submission_fsm(messages: List[Message], state: FSMContext, loc_path: Path):
    """Helper to start the FSM process for both single and group media."""
    messages_json = [msg.model_dump_json() for msg in messages]
    await state.update_data(original_messages=messages_json)
    with open(loc_path, 'r', encoding='utf-8') as f:
        loc = json.load(f)
    await messages[0].answer(loc["ask_for_subject"])
    await state.set_state(UserSubmission.awaiting_subject_for_direct_message)


# --- Command and State Handlers ---

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
@media_group_handler
async def process_content(
    messages: List[Message], bot: Bot, state: FSMContext, user_role: str,
    user_alias: str, loc_path: Path, config: Dict
):
    data = await state.get_data()
    subject = data.get("subject", "نامشخص")
    await state.clear()
    await handle_submission(bot, messages, subject, user_role, user_alias, config, loc_path)


@router.message(UserSubmission.awaiting_subject_for_direct_message)
async def process_subject_for_direct_message(
    message: Message, bot: Bot, state: FSMContext, user_role: str,
    user_alias: str, loc_path: Path, config: Dict
):
    data = await state.get_data()
    subject = message.text
    original_messages_json = data.get("original_messages")
    if not original_messages_json:
        await state.clear()
        return
    
    original_messages = [Message.model_validate_json(msg_json) for msg_json in original_messages_json]
    await state.clear()
    await handle_submission(bot, original_messages, subject, user_role, user_alias, config, loc_path)


# --- Direct Message Handlers ---

@router.message(F.chat.type == "private", F.media_group_id)
@media_group_handler
async def direct_album_submission(messages: List[Message], state: FSMContext, loc_path: Path):
    """Catches albums sent directly to the bot."""
    await start_submission_fsm(messages, state, loc_path)


@router.message(F.chat.type == "private")
async def direct_single_submission(message: Message, state: FSMContext, loc_path: Path):
    """Catches single messages sent directly to the bot."""
    await start_submission_fsm([message], state, loc_path)