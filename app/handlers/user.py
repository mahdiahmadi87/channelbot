# app/handlers/user.py

import asyncio
import json
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

# --- MEDIA GROUP HANDLING ---
# A simple in-memory cache for media groups. Key: media_group_id, Value: list of messages.
media_group_cache = {}
# A cache for scheduled tasks. Key: media_group_id, Value: asyncio.Task
media_group_tasks = {}

async def process_media_group(
    media_group_id: str, bot: Bot, state: FSMContext, user_role: str,
    user_alias: str, loc_path: Path, config: Dict
):
    """
    This function is called after a short delay to process the collected media group.
    """
    messages = media_group_cache.pop(media_group_id, [])
    media_group_tasks.pop(media_group_id, None)

    if not messages:
        return

    # Now that we have the full group, ask for the subject
    messages_json = [msg.model_dump_json() for msg in messages]
    await state.update_data(original_messages=messages_json)

    with open(loc_path, 'r', encoding='utf-8') as f:
        loc = json.load(f)
    await bot.send_message(messages[0].chat.id, loc["ask_for_subject"])
    await state.set_state(UserSubmission.awaiting_subject_for_direct_message)


@router.message(CommandStart())
async def cmd_start(message: Message, user_role: str, loc_path: Path):
    # ... (same as before)
    with open(loc_path, 'r', encoding='utf-8') as f:
        loc = json.load(f)
    keyboard = get_start_menu(user_role)
    await message.answer(loc["welcome"], reply_markup=keyboard)


def is_admin_or_owner(user_role: str) -> bool:
    # ... (same as before)
    return user_role in ["admin", "owner"]


async def handle_submission(
    bot: Bot,
    messages: List[Message], # <-- Now always expects a list
    subject: str,
    user_role: str,
    user_alias: str,
    config: Dict,
    loc_path: Path
):
    """Unified submission handler. Now handles lists of messages."""
    is_group = len(messages) > 1
    message_to_log = messages[0] # Use the first message for logging info

    if is_admin_or_owner(user_role):
        await Broadcaster.post_to_output_channel(
            bot=bot, messages=messages, subject=subject, config=config,
            loc_path=loc_path, is_regular_user_post=False
        )
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


@router.message(UserSubmission.awaiting_subject_for_direct_message)
async def process_subject_for_direct_message(
    message: Message, bot: Bot, state: FSMContext, user_role: str,
    user_alias: str, loc_path: Path, config: Dict
):
    data = await state.get_data()
    subject = message.text
    
    # Handle both single and multiple messages from state
    if 'original_messages' in data: # Media Group
        original_messages_json = data.get("original_messages", [])
        original_messages = [Message.model_validate_json(msg_json) for msg_json in original_messages_json]
    else: # Single Message
        original_message_json = data.get("original_message")
        original_messages = [Message.model_validate_json(original_message_json)] if original_message_json else []

    if not original_messages:
        await state.clear()
        return

    await state.clear()
    await handle_submission(bot, original_messages, subject, user_role, user_alias, config, loc_path)


@router.message(F.chat.type == "private", F.media_group_id)
async def handle_media_group(
    message: Message, bot: Bot, state: FSMContext, user_role: str,
    user_alias: str, loc_path: Path, config: Dict
):
    """Collects messages from a media group and schedules processing."""
    media_group_id = message.media_group_id
    if media_group_id not in media_group_cache:
        media_group_cache[media_group_id] = []
    media_group_cache[media_group_id].append(message)

    # If a task is already scheduled for this group, cancel it
    if media_group_id in media_group_tasks:
        media_group_tasks[media_group_id].cancel()

    # Schedule a new task to process the group after a short delay
    loop = asyncio.get_event_loop()
    media_group_tasks[media_group_id] = loop.create_task(
        asyncio.sleep(1.0, result=True),
        name=f"process_media_group:{media_group_id}"
    )
    # Using a weak reference to the task might be better in production
    # but for simplicity, we directly schedule the processing function
    loop.call_later(1.0, asyncio.create_task, process_media_group(
        media_group_id, bot, state, user_role, user_alias, loc_path, config
    ))

@router.message(F.chat.type == "private")
async def direct_submission(message: Message, state: FSMContext, loc_path: Path):
    """Handles single messages."""
    message_json = message.model_dump_json()
    await state.update_data(original_message=message_json)
    with open(loc_path, 'r', encoding='utf-8') as f:
        loc = json.load(f)
    await message.answer(loc["ask_for_subject"])
    await state.set_state(UserSubmission.awaiting_subject_for_direct_message)

# Handlers for /submit are omitted for brevity but would need similar media group logic