import json
from pathlib import Path
from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware, Bot
from aiogram.types import TelegramObject, User

from app.services.storage import StorageService

class ACLMiddleware(BaseMiddleware):
    def __init__(self, storage_service: StorageService, config: Dict):
        self.storage = storage_service
        self.config = config

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user: User = data.get("event_from_user")
        if not user:
            return await handler(event, data)

        role = "user"
        alias = None
        
        # 1. Check for Owner
        if user.id == self.config["owner_id"]:
            role = "owner"
            alias = "Owner"
        else:
            # 2. Check for Admin
            admins = await self.storage.get_admins()
            for admin in admins:
                if admin["id"] == user.id:
                    role = "admin"
                    alias = admin["alias"]
                    break
        
        # Mandatory Membership Check for Admins and Owner
        if role in ["admin", "owner"]:
            bot: Bot = data.get("bot")
            try:
                member = await bot.get_chat_member(
                    chat_id=self.config["required_channel_id"],
                    user_id=user.id
                )
                if member.status not in ["creator", "administrator", "member"]:
                    loc_path: Path = data.get("loc_path")
                    with open(loc_path, 'r', encoding='utf-8') as f:
                        loc = json.load(f)
                    
                    # You might want to get the channel invite link or username
                    channel_link = f"@{self.config['required_channel_id']}"
                    await bot.send_message(
                        user.id,
                        loc["must_be_member"].format(channel_link=channel_link)
                    )
                    return # Stop processing
            except Exception:
                # Bot might not be admin in the channel, or channel is invalid
                await bot.send_message(
                    self.config["owner_id"],
                    f"Error: Could not check membership for user {user.id} in required channel {self.config['required_channel_id']}."
                )
                return # Stop processing

        data["user_role"] = role
        data["user_alias"] = alias
        return await handler(event, data)