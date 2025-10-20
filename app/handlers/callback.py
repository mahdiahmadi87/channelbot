import json
import logging
from pathlib import Path
from typing import Dict

from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery

from app.services.broadcaster import Broadcaster
from app.utils.message_helpers import get_log_message

router = Router()

@router.callback_query(F.data.startswith("approve:"))
async def approve_callback_handler(
    query: CallbackQuery,
    bot: Bot,
    user_role: str,
    user_alias: str,
    config: Dict,
    loc_path: Path,
):
    if user_role not in ["admin", "owner"]:
        with open(loc_path, 'r', encoding='utf-8') as f:
            loc = json.load(f)
        await query.answer(loc["permission_denied_callback"], show_alert=True)
        return

    # Extract data from callback
    # format: approve:<submitter_id>:<subject>
    parts = query.data.split(":", 2)
    submitter_id = int(parts[1])
    subject = parts[2]

    original_message = query.message.reply_to_message
    if not original_message:
        await query.answer("Error: Could not find original message to approve.", show_alert=True)
        return

    try:
        # Post to output channel
        await Broadcaster.post_to_output_channel(bot, original_message, subject, config, loc_path)

        # Log approval to report group
        log_message_text = get_log_message(
            "report_approved",
            loc_path,
            admin_alias=user_alias,
            admin_id=query.from_user.id,
            submitter_id=submitter_id
        )
        await bot.send_message(config["report_group_id"], log_message_text)

        # Edit the report message to show it's been handled
        await query.message.edit_text(
            f"{query.message.text}\n\n✅ تایید شده توسط {user_alias}",
            reply_markup=None
        )
        await query.answer("پست تایید و در کانال منتشر شد.")

    except Exception as e:
        logging.error(f"Error during approval: {e}")
        await query.answer("An error occurred.", show_alert=True)


@router.callback_query(F.data.startswith("delete:"))
async def delete_callback_handler(
    query: CallbackQuery,
    bot: Bot,
    user_role: str,
    user_alias: str,
    config: Dict,
    loc_path: Path,
):
    if user_role not in ["admin", "owner"]:
        with open(loc_path, 'r', encoding='utf-8') as f:
            loc = json.load(f)
        await query.answer(loc["permission_denied_callback"], show_alert=True)
        return

    submitter_id = int(query.data.split(":")[1])

    # Log deletion
    log_message_text = get_log_message(
        "report_deleted",
        loc_path,
        admin_alias=user_alias,
        admin_id=query.from_user.id,
        submitter_id=submitter_id
    )
    await bot.send_message(config["report_group_id"], log_message_text)

    # Delete the report message
    await query.message.delete()
    await query.answer("گزارش حذف شد.")