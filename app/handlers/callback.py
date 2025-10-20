# app/handlers/callback.py

import json
import logging
from pathlib import Path
from typing import Dict

from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.services.broadcaster import Broadcaster
from app.states.admin_states import AdminManagement
from app.states.user_states import UserSubmission
from app.utils.message_helpers import get_log_message

router = Router()

# --- New handlers for Start Menu buttons ---

@router.callback_query(F.data == "start_submit")
async def handle_start_submit(query: CallbackQuery, state: FSMContext, loc_path: Path):
    with open(loc_path, 'r', encoding='utf-8') as f:
        loc = json.load(f)
    await query.message.answer(loc["ask_for_subject"])
    await state.set_state(UserSubmission.awaiting_subject)
    await query.answer()

@router.callback_query(F.data == "start_add_admin")
async def handle_start_add_admin(query: CallbackQuery, state: FSMContext, user_role: str):
    if user_role != "owner":
        await query.answer("شما اجازه دسترسی ندارید.", show_alert=True)
        return
    await query.message.answer("لطفاً ID عددی و نام مستعار ادمین جدید را ارسال کنید.\nمثال: `123456789 ali`")
    await state.set_state(AdminManagement.awaiting_add_admin_details)
    await query.answer()

@router.callback_query(F.data == "start_remove_admin")
async def handle_start_remove_admin(query: CallbackQuery, state: FSMContext, user_role: str):
    if user_role != "owner":
        await query.answer("شما اجازه دسترسی ندارید.", show_alert=True)
        return
    await query.message.answer("لطفاً ID عددی ادمینی که قصد حذف آن را دارید، ارسال کنید.")
    await state.set_state(AdminManagement.awaiting_remove_admin_id)
    await query.answer()


# --- Existing handlers for Approve/Delete ---

@router.callback_query(F.data.startswith("approve:"))
async def approve_callback_handler(
    query: CallbackQuery, bot: Bot, user_role: str, user_alias: str, config: Dict, loc_path: Path
):
    if user_role not in ["admin", "owner"]:
        await query.answer("شما اجازه انجام این کار را ندارید.", show_alert=True)
        return

    message_to_approve = query.message
    parts = query.data.split(":", 2)
    submitter_id = int(parts[1])
    subject = parts[2]

    try:
        # Pass the flag to add the #ارسالی tag
        await Broadcaster.post_to_output_channel(
            bot, message_to_approve, subject, config, loc_path, is_regular_user_post=True
        )

        log_message_text = get_log_message(
            "report_approved_log", loc_path,
            admin_alias=user_alias, admin_id=query.from_user.id, submitter_id=submitter_id
        )
        await bot.send_message(config["report_group_id"], log_message_text)
        
        # Edit the message in the report group to show it's handled
        new_text = f"✅ تایید شده توسط {user_alias}"
        if message_to_approve.caption:
             await bot.edit_message_caption(chat_id=query.message.chat.id, message_id=query.message.message_id, caption=f"{message_to_approve.caption}\n\n{new_text}", reply_markup=None)
        else:
            await query.message.edit_reply_markup(reply_markup=None)

        await query.answer("پست تایید و در کانال منتشر شد.")
    except Exception as e:
        logging.error(f"Error during approval: {e}")
        await query.answer("An error occurred during approval.", show_alert=True)


@router.callback_query(F.data.startswith("delete:"))
async def delete_callback_handler(
    query: CallbackQuery, bot: Bot, user_role: str, user_alias: str, config: Dict, loc_path: Path
):
    if user_role not in ["admin", "owner"]:
        await query.answer("شما اجازه انجام این کار را ندارید.", show_alert=True)
        return

    submitter_id = int(query.data.split(":")[1])
    log_message_text = get_log_message(
        "report_deleted_log", loc_path,
        admin_alias=user_alias, admin_id=query.from_user.id, submitter_id=submitter_id
    )
    await bot.send_message(config["report_group_id"], log_message_text)

    try:
        await bot.delete_message(chat_id=query.message.chat.id, message_id=query.message.message_id)
        if query.message.reply_to_message:
            await bot.delete_message(chat_id=query.message.chat.id, message_id=query.message.reply_to_message.message_id)
    except Exception as e:
        logging.warning(f"Could not delete message: {e}")

    await query.answer("گزارش حذف شد.")