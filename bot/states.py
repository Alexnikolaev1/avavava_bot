from aiogram.fsm.state import State, StatesGroup


class AvatarFlow(StatesGroup):
    choosing_animal = State()
    choosing_gender = State()
    choosing_style = State()
    choosing_emotion = State()
    waiting_custom_animal = State()
    waiting_photo_or_generate = State()
    waiting_for_audio = State()
    naming_favorite = State()


class PhotoFlow(StatesGroup):
    waiting_for_photo = State()
    waiting_for_audio = State()
