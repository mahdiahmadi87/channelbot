import asyncio
import json
import logging
from pathlib import Path
from typing import List, Union

from aiogram import Bot
from aiogram.exceptions import TelegramRetryAfter
from aiogram.types import (
    InlineKeyboardMarkup,
    Message,
    InputMediaPhoto,
    InputMediaVideo,
    InputMediaDocument,
    InputMediaAudio,
)

# A type hint for the list of media objects that send_media_group accepts
T_InputMedia = Union[InputMediaPhoto, InputMediaVideo, InputMediaDocument, InputMediaAudio]

def _build_media_group(messages: List[Message], caption: str = None) -> List[T_InputMedia]:
    """Helper function to build a list of InputMedia objects for send_media_group."""
    media_group = []
    for i, msg in enumerate(messages):
        caption_to_set = caption if i == 0 else None  # Caption only on the first item
        if msg.photo:
            media_group.append(InputMediaPhoto(media=msg.photo[-1].file_id, caption=caption_to_set))
        elif msg.video:
            media_group.append(InputMediaVideo(media=msg.video.file_id, caption=caption_to_set))
        elif msg.document:
            media_group.append(InputMediaDocument(media=msg.document.file_id, caption=caption_to_set))
        elif msg.audio:
            media_group.append(InputMediaAudio(media=msg.audio.file_id, caption=caption_to_set))
    return media_group


class Broadcaster:
    @staticmethod
    async def forward_to_report_group(
        bot: Bot,
        messages: List[Message],
        header: str,
        keyboard: InlineKeyboardMarkup,
        config: Dict,
    ):
        """Forwards a user's submission (single or album) to the report group."""
        try:
            sent_header = await bot.send_message(
                config["report_group_id"], header, disable_web_page_preview=True
            )

            if len(messages) > 1:
                # This is an album
                media_group = _build_media_group(messages)
                await bot.send_media_group(
                    chat_id=config["report_group_id"],
                    media=media_group,
                    reply_to_message_id=sent_header.message_id,
                )
                # We can't attach a keyboard to a media group directly.
                # A common workaround is to send a follow-up message with the keyboard.
                await bot.send_message(
                    config["report_group_id"],
                    "گزینه‌های مدیریت برای این آلبوم:",
                    reply_markup=keyboard
                )
            else:
                # This is a single message
                await bot.copy_message(
                    chat_id=config["report_group_id"],
                    from_chat_id=messages[0].chat.id,
                    message_id=messages[0].message_id,
                    reply_to_message_id=sent_header.message_id,
                    reply_markup=keyboard,
                )
        except Exception as e:
            logging.error(f"Failed to forward message to report group: {e}")

    @staticmethod
    async def post_to_output_channel(
        bot: Bot,
        messages: List[Message], # <-- Now accepts a list
        subject: str,
        config: Dict,
        loc_path: Path,
        is_regular_user_post: bool = False,
        retries: int = 3,
        delay: int = 2,
    ):
        """Posts a message or media group to the output channel."""
        with open(loc_path, "r", encoding="utf-8") as f:
            loc = json.load(f)

        footer = loc["output_channel_footer"].format(
            subject=subject, channel_id=config["output_channel_id"]
        )
        tag = "\n#ارسالی" if is_regular_user_post else ""

        for attempt in range(retries):
            try:
                # Handle single text message
                if len(messages) == 1 and messages[0].text:
                    final_text = f"{messages[0].text}{footer}{tag}"
                    await bot.send_message(
                        chat_id=config["output_channel_id"], text=final_text
                    )
                else:
                    # Handle all media (single or group)
                    base_caption = messages[0].caption if messages[0].caption else ""
                    final_caption = f"{base_caption}{footer}{tag}"
                    media_group = _build_media_group(messages, final_caption)
                    await bot.send_media_group(
                        chat_id=config["output_channel_id"], media=media_group
                    )
                
                return True

            except TelegramRetryAfter as e:
                logging.warning(f"Flood control exceeded. Retrying...: {e}")
                await asyncio.sleep(e.retry_after)
            except Exception as e:
                logging.error(f"Failed to post to output channel: {e}. Attempt {attempt + 1}/{retries}")
                if attempt + 1 == retries:
                    await bot.send_message(config["owner_id"], f"Failed to post to output channel. Error: {e}")
                    return False
                await asyncio.sleep(delay * (2**attempt))
        return False