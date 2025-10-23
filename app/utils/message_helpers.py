# app/utils/message_helpers.py

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

from aiogram.types import Message, InputMediaPhoto, InputMediaVideo, InputMediaDocument, InputMediaAudio

def get_message_type(message: Message) -> str:
    # ... (same as before)
    if message.text:
        return "text"
    if message.photo:
        return "photo"
    if message.video:
        return "video"
    if message.audio:
        return "audio"
    if message.voice:
        return "voice"
    if message.document:
        return "document"
    return "unknown"


def get_report_header(
    loc_path: Path,
    user_id: int,
    role: str,
    subject: str,
    message_type: str,
) -> str:
    # ... (same as before)
    with open(loc_path, 'r', encoding='utf-8') as f:
        loc = json.load(f)
    
    timestamp = datetime.utcnow().isoformat() + "Z"
    
    return loc["report_message_header"].format(
        user_id=user_id,
        role=role,
        subject=subject,
        message_type=message_type,
        timestamp=timestamp,
    )


def get_log_message(
    log_key: str,
    loc_path: Path,
    **kwargs: Any
) -> str:
    # ... (same as before)
    with open(loc_path, 'r', encoding='utf-8') as f:
        loc = json.load(f)
    
    timestamp = datetime.utcnow().isoformat() + "Z"
    kwargs["timestamp"] = timestamp
    
    return loc[log_key].format(**kwargs)


def convert_messages_to_input_media(messages: List[Message], caption: str = None) -> List:
    """
    Converts a list of Message objects into a list of InputMedia objects.
    Attaches the caption to the first item only.
    """
    media_list = []
    for i, msg in enumerate(messages):
        media_caption = caption if i == 0 else None
        
        if msg.photo:
            media_list.append(InputMediaPhoto(media=msg.photo[-1].file_id, caption=media_caption))
        elif msg.video:
            media_list.append(InputMediaVideo(media=msg.video.file_id, caption=media_caption))
        elif msg.document:
            media_list.append(InputMediaDocument(media=msg.document.file_id, caption=media_caption))
        elif msg.audio:
            media_list.append(InputMediaAudio(media=msg.audio.file_id, caption=media_caption))
            
    return media_list