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


class MascotFlow(StatesGroup):
    waiting_for_photo = State()
    waiting_for_audio = State()


class PhotoFlow(StatesGroup):
    waiting_for_photo = State()
    waiting_for_audio = State()


class PhotoshootFlow(StatesGroup):
    choosing_preset = State()
    waiting_for_photos = State()
    choosing_background = State()
    choosing_gender = State()
    choosing_art_style = State()
    choosing_pm_style = State()
    waiting_custom_prompt = State()


class MotionFlow(StatesGroup):
    choosing_mode = State()
    waiting_for_video = State()
    waiting_for_photo = State()


class RestoreFlow(StatesGroup):
    choosing_mode = State()
    waiting_for_photo = State()


class SceneFlow(StatesGroup):
    choosing_type = State()
    choosing_preset = State()
    waiting_for_photo = State()


class I2VFlow(StatesGroup):
    waiting_for_photo = State()
    waiting_for_prompt = State()
    choosing_duration = State()


class VoiceFlow(StatesGroup):
    waiting_for_sample = State()
    choosing_language = State()
    waiting_for_text = State()


class SingingFlow(StatesGroup):
    waiting_for_photo = State()
    waiting_for_audio = State()


class StickerFlow(StatesGroup):
    waiting_for_photo = State()


class SubtitlesFlow(StatesGroup):
    waiting_for_video = State()
