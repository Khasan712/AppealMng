from aiogram.fsm.state import State, StatesGroup


class NewAppeal(StatesGroup):
    category = State()
    description = State()
