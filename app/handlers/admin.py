import json
from pathlib import Path
from typing import Dict

from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from app.states.admin_states import AdminManagement
from app.services.storage import StorageService

router = Router()

# This handler now manages the state after the "add admin" button is pressed
@router.message(AdminManagement.awaiting_add_admin_details)
async def process_add_admin_details(
    message: Message,
    state: FSMContext, # <-- Add state here
    storage_service: StorageService,
    loc_path: Path
):
    args = message.text.split()
    if len(args) != 2 or not args[0].isdigit():
        await message.answer("فرمت اشتباه است. لطفاً ID عددی و نام مستعار را با یک فاصله ارسال کنید.\nمثال: `123456789 ali`")
        return

    user_id = int(args[0])
    alias = args[1]
    await storage_service.add_admin(user_id, alias)

    with open(loc_path, 'r', encoding='utf-8') as f:
        loc = json.load(f)
    await message.answer(loc["admin_added"].format(alias=alias, user_id=user_id))
    
    # --- CORRECTED LINE ---
    await state.clear()


# This handler now manages the state after the "remove admin" button is pressed
@router.message(AdminManagement.awaiting_remove_admin_id)
async def process_remove_admin_id(
    message: Message,
    state: FSMContext, # <-- Add state here
    storage_service: StorageService,
    loc_path: Path
):
    if not message.text.isdigit():
        await message.answer("فرمت اشتباه است. لطفاً فقط ID عددی ادمین را ارسال کنید.")
        return

    user_id = int(message.text)
    if await storage_service.remove_admin(user_id):
        with open(loc_path, 'r', encoding='utf-8') as f:
            loc = json.load(f)
        await message.answer(loc["admin_removed"].format(user_id=user_id))
    else:
        with open(loc_path, 'r', encoding='utf-8') as f:
            loc = json.load(f)
        await message.answer(loc["admin_not_found"].format(user_id=user_id))
        
    # --- CORRECTED LINE ---
    await state.clear()