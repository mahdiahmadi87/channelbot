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

    # --- LOGIC CORRECTED HERE ---
    # The message with the user's content is query.message itself.
    message_to_approve = query.message
    # ----------------------------

    parts = query.data.split(":", 2)
    submitter_id = int(parts[1])
    subject = parts[2]

    try:
        # Post the correct message to the output channel
        await Broadcaster.post_to_output_channel(bot, message_to_approve, subject, config, loc_path)

        # Log approval to report group
        log_message_text = get_log_message(
            "report_approved_log",
            loc_path,
            admin_alias=user_alias,
            admin_id=query.from_user.id,
            submitter_id=submitter_id
        )
        await bot.send_message(config["report_group_id"], log_message_text)

        # Edit the report message to show it's handled by removing the buttons
        # and adding a note to the caption/text.
        new_text = f"✅ تایید شده توسط {user_alias}"
        if message_to_approve.caption:
            await bot.edit_message_caption(
                chat_id=query.message.chat.id,
                message_id=query.message.message_id,
                caption=f"{message_to_approve.caption}\n\n{new_text}",
                reply_markup=None
            )
        else:
            # If it was just text, we can't edit a caption, so we just remove the keyboard
            await query.message.edit_reply_markup(reply_markup=None)

        await query.answer("پست تایید و در کانال منتشر شد.")

    except Exception as e:
        logging.error(f"Error during approval: {e}")
        await query.answer("An error occurred during approval.", show_alert=True)


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
        "report_deleted_log",
        loc_path,
        admin_alias=user_alias,
        admin_id=query.from_user.id,
        submitter_id=submitter_id
    )
    await bot.send_message(config["report_group_id"], log_message_text)

    # --- LOGIC CORRECTED HERE ---
    # Delete the content message AND the header message for cleanliness.
    try:
        # Delete the content message (the one with the buttons)
        await bot.delete_message(
            chat_id=query.message.chat.id,
            message_id=query.message.message_id
        )
        # If it was a reply, delete the header message too
        if query.message.reply_to_message:
            await bot.delete_message(
                chat_id=query.message.chat.id,
                message_id=query.message.reply_to_message.message_id
            )
    except Exception as e:
        logging.warning(f"Could not delete message, maybe it was already deleted: {e}")
    # ----------------------------

    await query.answer("گزارش حذف شد.")