# AvAvAvA Bot — говорящие мультяшные животные

Telegram-бот создаёт **мультяшного персонажа-животное** с выбором пола, стиля и эмоции, затем превращает его в **говорящее видео** с lip-sync.

**Пайплайн:** животное → пол → стиль → эмоция → Flux рисует портрет → SadTalker анимирует → ffmpeg сжимает под Telegram.

## Возможности

| Функция | Описание |
|---------|----------|
| 🐾 10 животных + свой текст | Кот, лиса, панда… или «розовый единорог» |
| ♂️♀️ Пол персонажа | Нейтральный, мальчик, девочка |
| 🎬 5 стилей | Мультфильм, Pixar, аниме, стикер, акварель |
| 😊 8 эмоций | Радость, восторг, крутость, грусть… |
| ⭐ Избранное | До 10 сохранённых персонажей (SQLite) |
| 📷 Режим /photo | Своё фото вместо AI-персонажа |
| 📸 /photoshoot | Нейрофотосессия: headshot, стили, свой промпт |
| 💃 /motion | Motion control: танец по референс-видео + фото |

## Структура

```
main.py
bot/
├── app.py
├── config.py
├── catalog.py              # животные, пол, стили, эмоции
├── models/avatar_config.py # единая модель персонажа
├── handlers/               # common, avatar, favorites, photo, mascot, photoshoot, motion
└── services/
    ├── pipeline.py         # оркестрация генерации
    ├── media.py            # Replicate, ffmpeg
    └── favorites.py        # SQLite-хранилище
```

## Локальный запуск

```bash
pip install -r requirements.txt
cp .env.example .env
python main.py
```

Нужен `ffmpeg`. База избранного создаётся в `data/bot.db`.

## Railway

1. Deploy from GitHub
2. Variables: `TELEGRAM_BOT_TOKEN`, `REPLICATE_API_TOKEN`
3. Подключи **Volume** к `/app/data` — иначе избранное сбросится при рестарте
4. Публичный домен не нужен (long polling)

## Команды

- `/start` — создать персонажа
- `/favorites` — избранные персонажи
- `/photo` — своё фото + аудио
- `/photoshoot` — нейрофотосессия по лицу
- `/motion` — танец / motion control (видео + фото)
- `/help` — справка

## Качество lip-sync

- Лучшие эмоции: **Радость**, **Восторг**
- Лучший стиль: **Стикер** (чёткие черты лица)
- SadTalker для мультяшек: без GFPGAN, `preprocess=crop`
- Для реальных фото: GFPGAN + `preprocess=full`

## Переменные окружения

| Переменная | По умолчанию |
|------------|--------------|
| `ALLOWED_USER_IDS` | пусто — бот открыт для всех; иначе whitelist по Telegram ID |
| `AVATAR_MODEL` | `black-forest-labs/flux-schnell` |
| `SADTALKER_MODEL` | `lucataco/sadtalker:85c698db...` (см. `.env.example`) |
| `PHOTOSHOOT_HEADSHOT_MODEL` | `flux-kontext-apps/professional-headshot` |
| `PHOTOSHOOT_STYLE_MODEL` | `fofr/face-to-many:edc6439a...` |
| `PHOTOSHOOT_CUSTOM_MODEL` | `mbukerepo/photomaker` |
| `MOTION_REPLACE_MODEL` | `wan-video/wan-2.2-animate-replace` |
| `MOTION_CONTROL_MODEL` | `kwaivgi/kling-v3-motion-control` |
| `MOTION_MAX_VIDEO_SECONDS` | `15` |
| `MAX_FAVORITES_PER_USER` | `10` |
| `DATABASE_PATH` | `data/bot.db` |
| `MAX_AUDIO_SECONDS` | `75` |
| `MAX_CONCURRENT_JOBS` | `2` |
