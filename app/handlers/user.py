# app/handlers/user.py

import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, List

from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.keyboards.inline import get_approval_keyboard
from app.keyboards.menu import get_start_menu
from app.services.broadcaster import Broadcaster
from app.states.user_states import UserSubmission
from app.utils.message_helpers import get_message_type, get_report_header, get_log_message

router = Router()

# Caches for media group handling - used by BOTH workflows now
media_group_cache = {}
media_group_tasks = {}

# --- Universal Helper Functions ---

@router.message(CommandStart())
async def cmd_start(message: Message, user_role: str, loc_path: Path):
    with open(loc_path, 'r', encoding='utf-8') as f:
        loc = json.load(f)
    keyboard = get_start_menu(user_role)
    await message.answer(loc["welcome"], reply_markup=keyboard)

def is_admin_or_owner(user_role: str) -> bool:
    return user_role in ["admin", "owner"]

async def handle_submission(
    bot: Bot, messages: List[Message], subject: str, user_role: str,
    user_alias: str, config: Dict, loc_path: Path
):
    """Unified submission handler. Now robust for all workflows."""
    if not messages:
        logging.error("handle_submission called with no messages.")
        return

    is_group = len(messages) > 1
    message_to_log = messages[0]

    if is_admin_or_owner(user_role):
        success = await Broadcaster.post_to_output_channel(
            bot=bot, messages=messages, subject=subject, config=config,
            loc_path=loc_path, is_regular_user_post=False
        )
        if success:
            log_text = get_log_message(
                "admin_direct_post_log", loc_path,
                admin_alias=user_alias, admin_id=message_to_log.from_user.id
            )
            await bot.send_message(config["report_group_id"], log_text)
            await bot.send_message(message_to_log.chat.id, "پست شما با موفقیت مستقیماً در کانال منتشر شد.")
    else:
        report_header = get_report_header(
            loc_path, user_id=message_to_log.from_user.id, role='کاربر',
            subject=subject, message_type="album" if is_group else get_message_type(message_to_log)
        )
        keyboard = get_approval_keyboard(message_to_log.from_user.id, subject)
        await Broadcaster.forward_to_report_group(bot, messages, report_header, keyboard, config)
        with open(loc_path, 'r', encoding='utf-8') as f:
            loc = json.load(f)
        await bot.send_message(message_to_log.chat.id, loc["submission_received"])


# =============================================================================
# WORKFLOW 1: Using the /submit command
# =============================================================================

async def process_submitted_media_group(
    media_group_id: str, bot: Bot, state: FSMContext, user_role: str,
    user_alias: str, loc_path: Path, config: Dict
):
    """Delayed function to process a media group from the /submit workflow."""
    messages = media_group_cache.pop(media_group_id, [])
    media_group_tasks.pop(media_group_id, None)
    if not messages:
        return
        
    data = await state.get_data()
    subject = data.get("subject", "نامشخص")
    await state.clear()
    await handle_submission(bot, messages, subject, user_role, user_alias, config, loc_path)


@router.message(Command("submit"))
async def cmd_submit(message: Message, state: FSMContext, loc_path: Path):
    """Step 1: User starts the submission with /submit."""
    with open(loc_path, 'r', encoding='utf-8') as f:
        loc = json.load(f)
    await message.answer(loc["ask_for_subject"])
    await state.set_state(UserSubmission.awaiting_subject)


@router.message(UserSubmission.awaiting_subject)
async def process_subject_from_command(message: Message, state: FSMContext):
    """Step 2: User sends the subject, bot asks for content."""
    await state.update_data(subject=message.text)
    await message.answer("اکنون محتوای خود را ارسال کنید (متن، عکس، ویدیو و غیره).")
    await state.set_state(UserSubmission.awaiting_content)


@router.message(UserSubmission.awaiting_content)
async def process_content_from_command(
    message: Message, bot: Bot, state: FSMContext, user_role: str,
    user_alias: str, loc_path: Path, config: Dict
):
    """Step 3: User sends content. This now handles both single and group media."""
    if message.media_group_id:
        # If the message is part of a media group, use the debouncing logic
        media_group_id = message.media_group_id
        if media_group_id not in media_group_cache:
            media_group_cache[media_group_id] = []
        media_group_cache[media_group_id].append(message)

        if media_group_id in media_group_tasks:
            media_group_tasks[media_group_id].cancel()

        loop = asyncio.get_event_loop()
        task = loop.call_later(
            1.5, # Increased delay slightly for stability
            lambda: asyncio.create_task(
                process_submitted_media_group(
                    media_group_id, bot, state, user_role, user_alias, loc_path, config
                )
            )
        )
        media_group_tasks[media_group_id] = task
    else:
        # If it's a single message, process it immediately
        data = await state.get_data()
        subject = data.get("subject", "نامشخص")
        await state.clear()
        await handle_submission(bot, [message], subject, user_role, user_alias, config, loc_path)


# =============================================================================
# WORKFLOW 2: Sending a direct message
# =============================================================================

async def process_direct_media_group(media_group_id: str, bot: Bot, state: FSMContext):
    """Delayed function to ask for subject for a direct media group."""
    messages = media_group_cache.pop(media_group_id, [])
    media_group_tasks.pop(media_group_id, None)
    if not messages:
        return
    messages_json = [msg.model_dump_json() for msg in messages]
    await state.update_data(original_messages=messages_json)
    await bot.send_message(messages[0].chat.id, "لطفاً نام سوژه را برای این آلبوم وارد کنید:")
    await state.set_state(UserSubmission.awaiting_subject_for_direct_message)


@router.message(UserSubmission.awaiting_subject_for_direct_message)
async def process_subject_for_direct_message(
    message: Message, bot: Bot, state: FSMContext, user_role: str,
    user_alias: str, loc_path: Path, config: Dict
):
    """Handles receiving the subject after a direct message/album was sent."""
    data = await state.get_data()
    subject = message.text
    
    if 'original_messages' in data: # Media Group
        original_messages_json = data.get("original_messages", [])
        original_messages = [Message.model_validate_json(msg_json) for msg_json in original_messages_json]
    else: # Single Message
        original_message_json = data.get("original_message")
        original_messages = [Message.model_validate_json(original_message_json)] if original_message_json else []

    await state.clear()
    await handle_submission(bot, original_messages, subject, user_role, user_alias, config, loc_path)


@router.message(F.chat_type == "private", F.media_group_id)
async def handle_direct_media_group(message: Message, bot: Bot, state: FSMContext):
    """Collects all messages from a direct media group submission."""
    media_group_id = message.media_group_id
    if media_group_id not in media_group_cache:
        media_group_cache[media_group_id] = []
    media_group_cache[media_group_id].append(message)

    if media_group_id in media_group_tasks:
        media_group_tasks[media_group_id].cancel()

    loop = asyncio.get_event_loop()
    task = loop.call_later(1.5, lambda: asyncio.create_task(process_direct_media_group(media_group_id, bot, state)))
    media_group_tasks[media_group_id] = task


@router.message(F.chat.type == "private")
async def direct_submission(message: Message, state: FSMContext, loc_path: Path):
    """Handles a single direct message as the start of a submission."""
    message_json = message.model_dump_json()
    await state.update_data(original_message=message_json)
    with open(loc_path, 'r', encoding='utf-8') as f:
        loc = json.load(f)
    await message.answer(loc["ask_for_subject"])
    await state.set_state(UserSubmission.awaiting_subject_for_direct_message)