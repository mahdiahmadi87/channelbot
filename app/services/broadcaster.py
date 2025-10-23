# app/services/broadcaster.py

import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, List, Union

from aiogram import Bot
from aiogram.exceptions import TelegramRetryAfter
from aiogram.types import InlineKeyboardMarkup, Message

from app.utils.message_helpers import convert_messages_to_input_media

class Broadcaster:
    @staticmethod
    async def forward_to_report_group(
        bot: Bot,
        messages: List[Message], # Now always a list
        header: str,
        keyboard: InlineKeyboardMarkup,
        config: Dict,
    ):
        """Forwards a user's submission (single or media group) to the report group."""
        try:
            sent_header = await bot.send_message(
                config["report_group_id"], header, disable_web_page_preview=True
            )

            if len(messages) > 1:
                # Handle media group (album)
                media = convert_messages_to_input_media(messages)
                # Note: Inline keyboards can't be attached to media groups directly.
                # We send the keyboard in a subsequent message.
                await bot.send_media_group(chat_id=config["report_group_id"], media=media)
                await bot.send_message(config["report_group_id"], "👇 گزینه‌های مدیریت برای آلبوم بالا 👇", reply_markup=keyboard)
            else:
                # Handle single message
                single_message = messages[0]
                await bot.copy_message(
                    chat_id=config["report_group_id"],
                    from_chat_id=single_message.chat.id,
                    message_id=single_message.message_id,
                    reply_to_message_id=sent_header.message_id,
                    reply_markup=keyboard,
                )
        except Exception as e:
            logging.error(f"Failed to forward message to report group: {e}")

    @staticmethod
    async def post_to_output_channel(
        bot: Bot,
        messages: List[Message], # Now always a list
        subject: str,
        config: Dict,
        loc_path: Path,
        is_regular_user_post: bool = False,
    ):
        """Posts a message or media group to the output channel."""
        if not messages:
            logging.error("post_to_output_channel called with an empty list of messages.")
            return False

        with open(loc_path, "r", encoding="utf-8") as f:
            loc = json.load(f)

        footer = loc["output_channel_footer"].format(
            subject=subject, channel_id=config["output_channel_id"]
        )
        tag = "\n#ارسالی" if is_regular_user_post else ""

        try:
            if len(messages) > 1:
                # Handle Media Group (album)
                first_message = messages[0]
                base_caption = first_message.caption if first_message.caption else ""
                final_caption = f"{base_caption}{footer}{tag}"
                media = convert_messages_to_input_media(messages, final_caption)
                await bot.send_media_group(chat_id=config["output_channel_id"], media=media)
            else:
                # Handle Single Message
                single_message = messages[0]
                if single_message.text:
                    final_text = f"{single_message.text}{footer}{tag}"
                    await bot.send_message(chat_id=config["output_channel_id"], text=final_text)
                else: # Single Media
                    base_caption = single_message.caption if single_message.caption else ""
                    final_caption = f"{base_caption}{footer}{tag}"
                    await bot.copy_message(
                        chat_id=config["output_channel_id"],
                        from_chat_id=single_message.chat.id,
                        message_id=single_message.message_id,
                        caption=final_caption,
                    )
            return True
        except Exception as e:
            logging.error(f"Failed to post to output channel: {e}")
            await bot.send_message(config["owner_id"], f"Failed to post to channel. Error: {e}")
            return False