import time
import json
from pathlib import Path
from typing import Callable, Dict, Any, Awaitable, MutableMapping

from aiogram import BaseMiddleware
from aiogram.types import Message

# Use a simple in-memory cache. For distributed systems, use Redis or similar.
caches: Dict[str, MutableMapping[int, list[float]]] = {
    "default": {}
}

class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, limit: int, period: int, loc_path: Path):
        """
        Initializes the middleware.
        :param limit: The maximum number of requests allowed.
        :param period: The time period in seconds.
        :param loc_path: Path to the localization file.
        """
        self.limit = limit
        self.period = period
        self.loc_path = loc_path
        self.cache = caches["default"]

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:
        user_id = event.from_user.id
        now = time.time()

        # Check and clean up old timestamps
        if user_id in self.cache:
            # Keep only timestamps within the current period
            self.cache[user_id] = [t for t in self.cache[user_id] if now - t < self.period]
        else:
            self.cache[user_id] = []

        # Check if the limit is exceeded
        if len(self.cache[user_id]) >= self.limit:
            with open(self.loc_path, 'r', encoding='utf-8') as f:
                loc = json.load(f)
            # You can add a new string for this message in fa.json
            await event.answer(loc.get("rate_limit_exceeded", "Rate limit exceeded. Try again later."))
            return  # Stop processing the event

        # Add current timestamp and proceed
        self.cache[user_id].append(now)
        return await handler(event, data)