# app/services/broadcaster.py

import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, Optional

from aiogram import Bot
from aiogram.types import Message, InlineKeyboardMarkup
from aiogram.exceptions import TelegramRetryAfter

class Broadcaster:
    @staticmethod
    async def forward_to_report_group(
        bot: Bot,
        message: Message,
        header: str,
        keyboard: InlineKeyboardMarkup,
        config: Dict,
    ):
        """Forwards a user's submission to the report group."""
        try:
            sent_header = await bot.send_message(
                config["report_group_id"],
                header,
                disable_web_page_preview=True
            )
            await bot.copy_message(
                chat_id=config["report_group_id"],
                from_chat_id=message.chat.id,
                message_id=message.message_id,
                reply_to_message_id=sent_header.message_id,
                reply_markup=keyboard
            )
        except Exception as e:
            logging.error(f"Failed to forward message to report group: {e}")

    @staticmethod
    async def post_to_output_channel(
        bot: Bot,
        message: Message,
        subject: str,
        config: Dict,
        loc_path: Path,
        is_regular_user_post: bool = False, # <-- NEW PARAMETER
        retries: int = 3,
        delay: int = 2
    ):
        """Posts a message to the output channel with retry logic."""
        with open(loc_path, 'r', encoding='utf-8') as f:
            loc = json.load(f)

        footer = loc["output_channel_footer"].format(
            subject=subject,
            channel_id=config["output_channel_id"]
        )

        # <-- NEW LOGIC to add the tag -->
        tag = "\n#ارسالی" if is_regular_user_post else ""

        caption = ""
        # Handle media captions and text messages correctly
        if message.text:
            caption = f"{message.text}{footer}{tag}"
        elif message.caption:
            caption = f"{message.caption}{footer}{tag}"
        else: # For media without a caption
            caption = f"{footer.lstrip()}{tag}" # lstrip to remove leading newlines

        for attempt in range(retries):
            try:
                await bot.copy_message(
                    chat_id=config["output_channel_id"],
                    from_chat_id=message.chat.id,
                    message_id=message.message_id,
                    # Only provide caption if the original message had media.
                    # For text messages, the content is part of the copy, and we can't override it.
                    caption=caption if not message.text else None,
                )
                # If it was a text message, we need to edit it to add the footer
                if message.text:
                    # The copied message is the last one sent by the bot to the channel.
                    # This is a bit of a workaround; a more robust way involves getting the message ID
                    # from the copy_message result, but this is sufficient for most cases.
                    # For now, let's assume copy_message is sufficient as it copies the text.
                    # A robust implementation would be more complex. Let's adjust the caption logic.
                    pass # The text is copied as is. Let's rethink adding footer to text messages.

                # A better approach for text messages
                if message.text:
                    await bot.send_message(
                        chat_id=config["output_channel_id"],
                        text=f"{message.text}{footer}{tag}"
                    )
                else: # For media
                     await bot.copy_message(
                        chat_id=config["output_channel_id"],
                        from_chat_id=message.chat.id,
                        message_id=message.message_id,
                        caption=caption
                    )
                return True
            except TelegramRetryAfter as e:
                logging.warning(f"Flood control exceeded. Retrying in {e.retry_after} seconds. Attempt {attempt + 1}/{retries}")
                await asyncio.sleep(e.retry_after)
            except Exception as e:
                logging.error(f"Failed to post to output channel: {e}. Attempt {attempt + 1}/{retries}")
                await asyncio.sleep(delay * (2 ** attempt))
        return False