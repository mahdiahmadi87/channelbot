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
            # Send the header text first
            sent_header = await bot.send_message(
                config["report_group_id"],
                header,
                disable_web_page_preview=True
            )
            # Reply to the header with the original content and keyboard
            await message.copy_to(
                chat_id=config["report_group_id"],
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
    
    # Check if there is media to handle caption correctly
    caption = ""
    if message.text:
        caption = f"{message.text}{footer}"
    elif message.caption:
        caption = f"{message.caption}{footer}"
    else:
        caption = footer

    for attempt in range(retries):
        try:
            await message.copy_to(
                chat_id=config["output_channel_id"],
                caption=caption if message.text is None else None, # Only use caption for media
                text=caption if message.text is not None else None,
            )
            return True
        except TelegramRetryAfter as e:
            logging.warning(f"Flood control exceeded. Retrying in {e.retry_after} seconds. Attempt {attempt + 1}/{retries}")
            if attempt + 1 == retries:
                logging.error("Max retries reached. Giving up on posting message.")
                await bot.send_message(
                    config["owner_id"],
                    f"Failed to post a message to output channel after {retries} retries due to flood limits."
                )
                return False
            await asyncio.sleep(e.retry_after)
        except Exception as e:
            logging.error(f"Failed to post to output channel: {e}. Attempt {attempt + 1}/{retries}")
            if attempt + 1 == retries:
                logging.error("Max retries reached. Giving up on posting message.")
                await bot.send_message(
                    config["owner_id"],
                    f"Failed to post a message to output channel after {retries} retries. Error: {e}"
                )
                return False
            await asyncio.sleep(delay * (2 ** attempt)) # Exponential backoff
    return False