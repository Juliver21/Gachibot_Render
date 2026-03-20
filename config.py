# ════════════════════════════════════════════════════
# ⚙️  КОНФІГУРАЦІЯ БОТА
# ════════════════════════════════════════════════════

# ── Канали ──────────────────────────────────────────
WELCOME_CHANNEL_NAME  = "загальний"
MEMES_CHANNEL_NAME    = "меми"
ARCHIVE_CATEGORY_NAME = "АРХІВ"

# ── Роль-пікер ───────────────────────────────────────
ROLE_CHANNEL_ID = 1360928593806495775
ROLE_MESSAGE_ID = 1360940167321489510

# Емодзі ID → Роль ID
EMOJI_ROLE_MAP = {
    1360932844758761653: 896485804082335805,   # arthas  → Warcraft
    1360933334582300789: 815713290939924530,   # LOL     → League of Legends
    1360933673637122288: 879001741599862815,   # Dota2   → Dota
    1361084245245825045: 976498612370563122,   # grass   → Minecraft
    1361083930295402547: 1361084881504833576,  # csgo    → CS2
    1361084115641700612: 1361079686699946197,  # pubg    → PUBG
    1360933945725947924: 823219904739409920,   # Mafia   → Каскадська Мафія
}

MAFIA_EMOJI_ID = 1360933945725947924
MAFIA_ROLE_ID  = 823219904739409920

# ── Голосові канали → Звуки ──────────────────────────
ROOM_SOUNDS = {
    "Каскадське лігво":   "sounds/kaskad_gachi.mp3",
    "【⛏Minecraft":       "sounds/minecraft_gachi.mp3",
    "【♂ Warcraft 3":     "sounds/warcraft_gachi.mp3",
    "┏ ⚧ LoL Room 1":    "sounds/lol1_gachi.mp3",
    "┗ ⚧ LoL Room 2":    "sounds/lol2_gachi.mp3",
    "【♂ Dota-2":         "sounds/dota_gachi.mp3",
    "【⚣ Бабаджі Room 1": "sounds/pubg_gachi.mp3",
    "【⚣ Бабаджі Room 2": "sounds/pubg_gachi.mp3",
    "【☾ CS-2":           "sounds/cs2_gachi.mp3",
}

# ── Тригери → Мем URL ────────────────────────────────
MEME_TRIGGERS = {
    "аніка":         "https://i.imgur.com/2FQKJZK.jpg",
    "гачі":          "https://i.imgur.com/2FQKJZK.jpg",
    "м'язи":         "https://i.imgur.com/2FQKJZK.jpg",
    "billy":         "https://i.imgur.com/2FQKJZK.jpg",
    "are you ready": "https://i.imgur.com/2FQKJZK.jpg",
}

# ── Компліменти у VC ─────────────────────────────────
VOICE_COMPLIMENTS = [
    "Найс асс, Скаймен! 👀♂️",
    "Ти виглядаєш неймовірно м'язисто сьогодні, брате! 💪",
    "Аніка пишається тобою! ♂️",
    "Are you ready? Бо ти виглядаєш більш ніж готово! 😏",
    "Шикарні голоси тут... Feel the Power! 🔥",
    "Брат, ти сьогодні на висоті! Аніка схвалює! 🏛️",
]

# ── Вітання у каналах ────────────────────────────────
CHANNEL_GREETINGS = [
    "♂️ Привіт, брати! Як ваші м'язи сьогодні? 💪",
    "🏛️ Аніка перевіряє чи всі живі тут...",
    "♂️ *заглядає* Слава Аніці, брати! 🙏",
    "Are you ready, bros? 😏",
    "🔥 Каскадське Братство живе! ♂️",
]

# ── Система рангів (15 рівнів) ───────────────────────
RANKS = [
    {"name": "🐣 Пацан з Каскаду",        "xp": 0,     "role": "Пацан з Каскаду",        "color": 0x808080},
    {"name": "👀 Спостерігач Аніки",       "xp": 50,    "role": "Спостерігач Аніки",       "color": 0x778899},
    {"name": "💪 Підмайстер М'язів",       "xp": 150,   "role": "Підмайстер М'язів",       "color": 0xCD7F32},
    {"name": "🏋️ Качок Підземелля",        "xp": 300,   "role": "Качок Підземелля",        "color": 0xB87333},
    {"name": "⚔️ Воїн Гачі",              "xp": 500,   "role": "Воїн Гачі",              "color": 0xC0C0C0},
    {"name": "🛡️ Захисник Каскаду",        "xp": 750,   "role": "Захисник Каскаду",        "color": 0xA8A9AD},
    {"name": "🏛️ Страж Підземелля",        "xp": 1000,  "role": "Страж Підземелля",        "color": 0xFFD700},
    {"name": "🌟 Обранець Аніки",          "xp": 1500,  "role": "Обранець Аніки",          "color": 0xFFA500},
    {"name": "♂️ Справжній Аніка",         "xp": 2000,  "role": "Справжній Аніка",         "color": 0xFF4500},
    {"name": "🔱 Майстер Гачі",            "xp": 3000,  "role": "Майстер Гачі",            "color": 0x8B0000},
    {"name": "🦁 Лев Каскаду",             "xp": 4000,  "role": "Лев Каскаду",             "color": 0xDC143C},
    {"name": "🐉 Дракон Підземелля",       "xp": 5500,  "role": "Дракон Підземелля",       "color": 0x800080},
    {"name": "⚡ Громовержець Аніки",      "xp": 7500,  "role": "Громовержець Аніки",      "color": 0x00CED1},
    {"name": "👑 Легенда Каскаду",         "xp": 10000, "role": "Легенда Каскаду",         "color": 0xFFD700},
    {"name": "🔮 Безсмертний Аніка",       "xp": 15000, "role": "Безсмертний Аніка",       "color": 0xFF69B4},
]

# ── Lavalink (публічний безкоштовний сервер) ─────────
# Якщо один не працює — змінюй на інший з цього списку:
# https://lavalink.darrennathanael.com/NoSSL/lavalink-without-ssl/
LAVALINK_HOST = "lavalink.devamop.in"
LAVALINK_PORT = 443
LAVALINK_PASS = "DevamOP"
LAVALINK_SSL  = True   # True якщо порт 443

# ── Каскадський тест ─────────────────────────────────
CASCADE_TEST = [
    {
        "q": "♂️ Як звати легендарного Аніку?",
        "options": ["A) John Smith", "B) Billy Herrington", "C) Van Damme", "D) Mark Wolff"],
        "answer": "B",
        "explanation": "Billy Herrington — легендарний Аніка! ♂️",
    },
    {
        "q": "🏛️ Що таке 'Каскадське лігво'?",
        "options": ["A) Назва фільму", "B) Голосовий канал сервера", "C) Назва гри", "D) Мем"],
        "answer": "B",
        "explanation": "Каскадське лігво — наш головний голосовий канал! 🏛️",
    },
    {
        "q": "💪 Яка культова фраза Аніки?",
        "options": ["A) Are you ready?", "B) Just do it!", "C) Feel the power!", "D) Let's go!"],
        "answer": "A",
        "explanation": "ARE YOU READY?! ♂️",
    },
    {
        "q": "🎮 Яка гра НЕ представлена на сервері?",
        "options": ["A) CS-2", "B) Dota-2", "C) Valorant", "D) League of Legends"],
        "answer": "C",
        "explanation": "Valorant поки що не в списку! 👀",
    },
    {
        "q": "📜 Скільки часу для доступу до архіву?",
        "options": ["A) 1 місяць", "B) 3 місяці", "C) 6 місяців", "D) 1 рік"],
        "answer": "C",
        "explanation": "6 місяців — ціна архівного доступу! 📜",
    },
]
