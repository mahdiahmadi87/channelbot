# app/states/admin_states.py

from aiogram.fsm.state import State, StatesGroup

class AdminManagement(StatesGroup):
    awaiting_add_admin_details = State()
    awaiting_remove_admin_id = State()
