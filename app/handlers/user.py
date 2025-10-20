import json
from pathlib import Path
from typing import Dict

from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.keyboards.inline import get_approval_keyboard
from app.services.broadcaster import Broadcaster
from app.states.user_states import UserSubmission
from app.utils.message_helpers import get_message_type, get_report_header

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message, loc_path: Path):
    with open(loc_path, 'r', encoding='utf-8') as f:
        loc = json.load(f)
    await message.answer(loc["welcome"])

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
    message: Message,
    bot: Bot,
    state: FSMContext,
    user_role: str,
    user_alias: str,
    loc_path: Path,
    config: Dict
):
    data = await state.get_data()
    subject = data.get("subject", "نامشخص")

    report_header = get_report_header(
        loc_path,
        user_id=message.from_user.id,
        role=user_alias if user_role in ['admin', 'owner'] else 'کاربر',
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
    await state.clear()

# Handler for direct submissions without /submit command
@router.message(F.chat.type == "private")
async def direct_submission(message: Message, state: FSMContext, loc_path: Path):
    # Store the message and ask for the subject
    # We serialize the message to JSON to store it in the FSM context
    message_json = message.model_dump_json()
    await state.update_data(original_message=message_json)
    
    with open(loc_path, 'r', encoding='utf-8') as f:
        loc = json.load(f)
    await message.answer(loc["ask_for_subject"])
    await state.set_state(UserSubmission.awaiting_subject_for_direct_message)

@router.message(UserSubmission.awaiting_subject_for_direct_message)
async def process_subject_for_direct_message(
    message: Message,
    bot: Bot,
    state: FSMContext,
    user_role: str,
    user_alias: str,
    loc_path: Path,
    config: Dict
):
    data = await state.get_data()
    subject = message.text
    
    # Deserialize the original message
    original_message_json = data.get("original_message")
    if not original_message_json:
        await state.clear()
        return
        
    original_message = Message.model_validate_json(original_message_json)
    # Important: Create a new bot instance for the deserialized message context
    original_message.bot = bot

    report_header = get_report_header(
        loc_path,
        user_id=original_message.from_user.id,
        role=user_alias if user_role in ['admin', 'owner'] else 'کاربر',
        subject=subject,
        message_type=get_message_type(original_message)
    )

    keyboard = get_approval_keyboard(original_message.from_user.id, subject)

    await Broadcaster.forward_to_report_group(
        bot, original_message, report_header, keyboard, config
    )
    
    with open(loc_path, 'r', encoding='utf-8') as f:
        loc = json.load(f)
    await message.answer(loc["submission_received"])
    await state.clear()