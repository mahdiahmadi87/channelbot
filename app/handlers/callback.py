import json
from pathlib import Path
from typing import Dict

from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message

from app.services.storage import StorageService
from app.services.broadcaster import Broadcaster
from app.utils.message_helpers import get_log_message

router = Router()
# This filter should probably be removed to allow commands in the report group too,
# but for now we keep it as per the original design.
router.message.filter(F.chat.type == "private")


@router.message(Command("add_admin"))
async def add_admin_handler(
    message: Message,
    user_role: str,
    loc_path: Path,
    storage_service: StorageService,
    config: Dict
):
    if user_role != "owner":
        with open(loc_path, 'r', encoding='utf-8') as f:
            loc = json.load(f)
        await message.answer(loc["not_admin"].format(owner_id=config['owner_id']))
        return

    args = message.text.split()
    if len(args) != 3:
        with open(loc_path, 'r', encoding='utf-8') as f:
            loc = json.load(f)
        await message.answer(loc["invalid_command_format"].format(example="/add_admin <user_id> <alias>"))
        return

    try:
        user_id = int(args[1])
        alias = args[2]
        await storage_service.add_admin(user_id, alias)
        with open(loc_path, 'r', encoding='utf-8') as f:
            loc = json.load(f)
        await message.answer(loc["admin_added"].format(alias=alias, user_id=user_id))
    except (ValueError, IndexError):
        with open(loc_path, 'r', encoding='utf-8') as f:
            loc = json.load(f)
        await message.answer(loc["invalid_command_format"].format(example="/add_admin <user_id> <alias>"))


@router.message(Command("remove_admin"))
async def remove_admin_handler(
    message: Message,
    user_role: str,
    loc_path: Path,
    storage_service: StorageService,
    config: Dict
):
    if user_role != "owner":
        with open(loc_path, 'r', encoding='utf-8') as f:
            loc = json.load(f)
        await message.answer(loc["not_admin"].format(owner_id=config['owner_id']))
        return

    args = message.text.split()
    if len(args) != 2:
        with open(loc_path, 'r', encoding='utf-8') as f:
            loc = json.load(f)
        await message.answer(loc["invalid_command_format"].format(example="/remove_admin <user_id>"))
        return

    try:
        user_id = int(args[1])
        if await storage_service.remove_admin(user_id):
            with open(loc_path, 'r', encoding='utf-8') as f:
                loc = json.load(f)
            await message.answer(loc["admin_removed"].format(user_id=user_id))
        else:
            with open(loc_path, 'r', encoding='utf-8') as f:
                loc = json.load(f)
            await message.answer(loc["admin_not_found"].format(user_id=user_id))
    except ValueError:
        with open(loc_path, 'r', encoding='utf-8') as f:
            loc = json.load(f)
        await message.answer(loc["invalid_command_format"].format(example="/remove_admin <user_id>"))


@router.message(Command("post"))
async def admin_post_handler(
    message: Message,
    bot: Bot,
    user_role: str,
    user_alias: str,
    loc_path: Path,
    config: Dict
):
    if user_role not in ["admin", "owner"]:
        return

    if not message.reply_to_message:
        await message.answer("Please reply to a message to post it directly.")
        return

    subject = "پست مستقیم ادمین"

    await Broadcaster.post_to_output_channel(bot, message.reply_to_message, subject, config, loc_path)
    
    # Log to report group --- KEY CORRECTED HERE ---
    log_message = get_log_message(
        "admin_direct_post_log", # <-- CORRECTED
        loc_path,
        admin_alias=user_alias,
        admin_id=message.from_user.id
    )
    await bot.send_message(config["report_group_id"], log_message)