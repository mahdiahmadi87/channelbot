import asyncio
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

import yaml
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties # <-- IMPORT THIS
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
import os

from app.handlers import admin, user, callback
from app.middlewares.acl import ACLMiddleware
from app.middlewares.throttling import ThrottlingMiddleware
from app.services.storage import StorageService

def setup_logging(config):
    """Sets up logging configuration."""
    log_level = config.get("logging", {}).get("level", "INFO")
    log_file = config.get("logging", {}).get("file", "bot.log")
    rotation = config.get("logging", {}).get("rotation", "10 MB")

    # Convert rotation string to bytes
    size_in_bytes = 10 * 1024 * 1024 # default 10 MB
    if "MB" in rotation.upper():
        size_in_bytes = int(rotation.upper().replace("MB", "").strip()) * 1024 * 1024
    elif "KB" in rotation.upper():
        size_in_bytes = int(rotation.upper().replace("KB", "").strip()) * 1024

    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        handlers=[
            RotatingFileHandler(log_file, maxBytes=size_in_bytes, backupCount=5),
            logging.StreamHandler(),
        ],
    )
    logging.info("Logging configured.")

async def main():
    """Main function to start the bot."""
    # Load environment variables
    load_dotenv()
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        raise ValueError("BOT_TOKEN environment variable not set!")

    # Load configuration
    config_path = Path(__file__).parent.parent / "config.yaml"
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    # Setup logging
    setup_logging(config)
    
    # Initialize storage service
    admins_file_path = Path(__file__).parent.parent / "admins.json"
    storage_service = StorageService(admins_file_path)
    
    # Initialize localization
    loc_path = Path(__file__).parent.parent / "fa.json"
    
    # Initialize Bot and Dispatcher
    # --- THIS LINE IS CORRECTED ---
    bot = Bot(token=bot_token, default=DefaultBotProperties(parse_mode="HTML"))
    # ------------------------------
    
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Register global middlewares (like ACL)
    dp.update.middleware(ACLMiddleware(storage_service, config))
    
    # Register router-level middlewares (like Throttling)
    rate_limit_config = config.get("rate_limit", {"limit": 5, "period": 3600})
    user.router.message.middleware(
        ThrottlingMiddleware(
            limit=rate_limit_config["limit"],
            period=rate_limit_config["period"],
            loc_path=loc_path
        )
    )

    # Register routers
    dp.include_router(admin.router)
    dp.include_router(user.router)
    dp.include_router(callback.router)

    logging.info("Bot starting...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, config=config, storage_service=storage_service, loc_path=loc_path)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped.")