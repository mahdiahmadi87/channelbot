import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from aiogram.types import Message

def get_message_type(message: Message) -> str:
    """Determines the type of a message for logging."""
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
    """Formats the header for a message in the report group."""
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
    """Formats a log message for the report group from localization."""
    with open(loc_path, 'r', encoding='utf-8') as f:
        loc = json.load(f)
    
    timestamp = datetime.utcnow().isoformat() + "Z"
    kwargs["timestamp"] = timestamp
    
    return loc[log_key].format(**kwargs)