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
        messages: Union[Message, List[Message]],
        header: str,
        keyboard: InlineKeyboardMarkup,
        config: Dict,
    ):
        """Forwards a user's submission (single or media group) to the report group."""
        try:
            sent_header = await bot.send_message(
                config["report_group_id"], header, disable_web_page_preview=True
            )

            if isinstance(messages, list):
                # Handle media group
                media = convert_messages_to_input_media(messages)
                await bot.send_media_group(chat_id=config["report_group_id"], media=media)
                # Buttons must be sent separately for media groups
                await bot.send_message(config["report_group_id"], "👇", reply_markup=keyboard)
            else:
                # Handle single message
                await bot.copy_message(
                    chat_id=config["report_group_id"],
                    from_chat_id=messages.chat.id,
                    message_id=messages.message_id,
                    reply_to_message_id=sent_header.message_id,
                    reply_markup=keyboard,
                )
        except Exception as e:
            logging.error(f"Failed to forward message to report group: {e}")

    @staticmethod
    async def post_to_output_channel(
        bot: Bot,
        messages: Union[Message, List[Message]],
        subject: str,
        config: Dict,
        loc_path: Path,
        is_regular_user_post: bool = False,
    ):
        """Posts a message or media group to the output channel."""
        with open(loc_path, "r", encoding="utf-8") as f:
            loc = json.load(f)

        footer = loc["output_channel_footer"].format(
            subject=subject, channel_id=config["output_channel_id"]
        )
        tag = "\n#ارسالی" if is_regular_user_post else ""

        try:
            if isinstance(messages, list):
                # Handle Media Group
                base_caption = messages[0].caption if messages[0].caption else ""
                final_caption = f"{base_caption}{footer}{tag}"
                media = convert_messages_to_input_media(messages, final_caption)
                await bot.send_media_group(chat_id=config["output_channel_id"], media=media)
            else:
                # Handle Single Message
                if messages.text:
                    final_text = f"{messages.text}{footer}{tag}"
                    await bot.send_message(chat_id=config["output_channel_id"], text=final_text)
                else: # Media
                    base_caption = messages.caption if messages.caption else ""
                    final_caption = f"{base_caption}{footer}{tag}"
                    await bot.copy_message(
                        chat_id=config["output_channel_id"],
                        from_chat_id=messages.chat.id,
                        message_id=messages.message_id,
                        caption=final_caption,
                    )
            return True
        except Exception as e:
            logging.error(f"Failed to post to output channel: {e}")
            await bot.send_message(config["owner_id"], f"Failed to post to channel. Error: {e}")
            return False