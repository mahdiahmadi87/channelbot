import asyncio
import json
import logging
from pathlib import Path
from typing import Dict

from aiogram import Bot
from aiogram.exceptions import TelegramRetryAfter
from aiogram.types import InlineKeyboardMarkup, Message

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
                config["report_group_id"], header, disable_web_page_preview=True
            )
            await bot.copy_message(
                chat_id=config["report_group_id"],
                from_chat_id=message.chat.id,
                message_id=message.message_id,
                reply_to_message_id=sent_header.message_id,
                reply_markup=keyboard,
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
        is_regular_user_post: bool = False,
        retries: int = 3,
        delay: int = 2,
    ):
        """Posts a message to the output channel with retry logic. (REWRITTEN)"""
        with open(loc_path, "r", encoding="utf-8") as f:
            loc = json.load(f)

        footer = loc["output_channel_footer"].format(
            subject=subject, channel_id=config["output_channel_id"]
        )
        tag = "\n#ارسالی" if is_regular_user_post else ""

        for attempt in range(retries):
            try:
                # --- CLEANED UP LOGIC ---
                # There is now only one send/copy operation per attempt.

                if message.text:
                    # Handle text messages
                    final_text = f"{message.text}{footer}{tag}"
                    await bot.send_message(
                        chat_id=config["output_channel_id"], text=final_text
                    )

                else:
                    # Handle all media types (photo, video, etc.)
                    base_caption = message.caption if message.caption else ""
                    final_caption = f"{base_caption}{footer}{tag}"
                    await bot.copy_message(
                        chat_id=config["output_channel_id"],
                        from_chat_id=message.chat.id,
                        message_id=message.message_id,
                        caption=final_caption,
                    )
                
                return True # Success, exit the loop

            except TelegramRetryAfter as e:
                logging.warning(
                    f"Flood control exceeded. Retrying in {e.retry_after} seconds. Attempt {attempt + 1}/{retries}"
                )
                await asyncio.sleep(e.retry_after)
            except Exception as e:
                logging.error(
                    f"Failed to post to output channel: {e}. Attempt {attempt + 1}/{retries}"
                )
                if attempt + 1 == retries:
                    logging.error("Max retries reached. Giving up on posting message.")
                    await bot.send_message(
                        config["owner_id"],
                        f"Failed to post a message to output channel after {retries} retries. Error: {e}",
                    )
                    return False
                await asyncio.sleep(delay * (2**attempt))  # Exponential backoff
        return False