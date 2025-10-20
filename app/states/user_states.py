from aiogram.fsm.state import State, StatesGroup

class UserSubmission(StatesGroup):
    awaiting_subject = State()
    awaiting_content = State()
    awaiting_subject_for_direct_message = State()