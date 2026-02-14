#legacy version

'''import asyncio
import os
import random
import json
import re
import logging
import sys
import aiohttp
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, BotCommand, BotCommandScopeDefault
from aiogram.enums import ChatAction
import imagehash
from PIL import Image
import cv2

# Включаем логирование
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


# --- ЗАГРУЗКА КЛЮЧЕЙ ---
def load_api_keys():
    if not os.path.exists("api_keys.json"):
        logging.critical("Файл api_keys.json не найден! Бот остановлен.")
        sys.exit(1)

    try:
        with open("api_keys.json", "r", encoding="utf-8") as f:
            keys = json.load(f)
            tg_key = keys.get("telegram_api_key")
            ds_key = keys.get("deepseek_api_key")

            if not tg_key or not ds_key:
                logging.critical("В файле api_keys.json отсутствуют нужные ключи! Бот остановлен.")
                sys.exit(1)

            return tg_key, ds_key
    except json.JSONDecodeError:
        logging.critical("Ошибка синтаксиса в api_keys.json. Проверьте запятые и кавычки!")
        sys.exit(1)


# Инициализация ключей и бота
TOKEN, DEEPSEEK_TOKEN = load_api_keys()
bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- НАСТРОЙКИ ---
FORBIDDEN_HASHES = ["2f71f1f2f0608838"]
DATA_FILE = "triggers.json"
TRIGGERS_DB = {}


# --- Функции работы с данными ---
def load_data():
    global TRIGGERS_DB
    if not os.path.exists(DATA_FILE):
        initial_data = {
            "фемб": {
                "mode": "fulltrigger",
                "answers": ["Да, это фембой!", "Осуждаю."]
            }
        }
        save_data(initial_data)
        TRIGGERS_DB = initial_data
    else:
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            migrated = False
            for k, v in data.items():
                if isinstance(v, list):
                    data[k] = {"mode": "common", "answers": v}
                    migrated = True
            TRIGGERS_DB = data
            if migrated:
                save_data()
            logging.info(f"База загружена. Триггеров: {len(TRIGGERS_DB)}")
        except json.JSONDecodeError:
            TRIGGERS_DB = {}


def save_data(data=None):
    if data is None:
        data = TRIGGERS_DB
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


load_data()


# --- Настройка меню команд ---
async def set_main_menu(bot: Bot):
    main_menu_commands = [
        BotCommand(command="factcheck", description="Проверить факт (в ответ на сообщение)"),
        BotCommand(command="add", description="Добавить триггер: @bot add \"слово\" \"ответ\""),
        BotCommand(command="help", description="Справка по боту")
    ]
    await bot.set_my_commands(main_menu_commands, scope=BotCommandScopeDefault())


# --- Хендлер: FACT CHECKING ---
@dp.message(F.text.lower().contains("fact checking") | (F.text.lower() == "/factcheck"))
async def fact_check_handler(message: Message):
    bot_user = await bot.get_me()
    bot_mention = f"@{bot_user.username}"
    text = message.text.lower()

    if "/factcheck" not in text and bot_mention.lower() not in text:
        return

    if not message.reply_to_message or not message.reply_to_message.text:
        await message.reply("⚠️ Эту команду нужно использовать **в ответ** (Reply) на сообщение с текстом.")
        return

    original_text = message.reply_to_message.text
    logging.info(f"Запрос Fact Check для: {original_text[:50]}...")

    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    url = "https://api.deepseek.com/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_TOKEN}"
    }

    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "Ты факт-чекер. Проверь утверждение. Ответь кратко на русском."},
            {"role": "user", "content": f"Правда ли это: {original_text}"}
        ],
        "stream": False
    }

    try:
        timeout = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    answer = result['choices'][0]['message']['content']
                    await message.reply_to_message.reply(f"🧠 **Анализ DeepSeek:**\n\n{answer}", parse_mode="Markdown")
                else:
                    error_text = await response.text()
                    logging.error(f"DeepSeek API Error {response.status}: {error_text}")
                    await message.reply(f"❌ Ошибка API ({response.status}). Проверьте логи.")
    except asyncio.TimeoutError:
        logging.error("DeepSeek API Timeout")
        await message.reply("⌛️ DeepSeek долго не отвечает (тайм-аут).")
    except Exception as e:
        logging.exception(f"Критическая ошибка при запросе: {e}")
        await message.reply("❌ Произошла внутренняя ошибка при запросе.")


# --- Хендлер: ADD ---
@dp.message(F.text.lower().contains("add"))
async def add_new_trigger(message: Message):
    text = message.text.strip()
    bot_user = await bot.get_me()
    bot_mention = f"@{bot_user.username}"

    if bot_mention.lower() not in text.lower():
        return

    clean_text = re.sub(re.escape(bot_mention), "", text, flags=re.IGNORECASE).strip()
    mode = "common"

    if "-fulltrigger" in clean_text.lower():
        mode = "fulltrigger"
        clean_text = re.sub(r"-fulltrigger", "", clean_text, flags=re.IGNORECASE)
    elif "-common" in clean_text.lower():
        mode = "common"
        clean_text = re.sub(r"-common", "", clean_text, flags=re.IGNORECASE)

    if not clean_text.lower().startswith("add"):
        return

    args_text = clean_text[3:].strip()
    matches = re.findall(r'"([^"]+)"', args_text)

    if len(matches) < 2:
        await message.reply("⚠️ Формат: `@bot add \"триггер\" \"ответ\"`")
        return

    trigger_word = matches[0].lower()
    new_answers = matches[1:]

    if len(trigger_word) < 3:
        await message.reply("Слово слишком короткое.")
        return

    if trigger_word not in TRIGGERS_DB:
        TRIGGERS_DB[trigger_word] = {"mode": mode, "answers": []}
        msg = f"🆕 Добавлен триггер **\"{trigger_word}\"**"
    else:
        TRIGGERS_DB[trigger_word]["mode"] = mode
        msg = f"✏️ Обновлен триггер **\"{trigger_word}\"**"

    for ans in new_answers:
        if ans not in TRIGGERS_DB[trigger_word]["answers"]:
            TRIGGERS_DB[trigger_word]["answers"].append(ans)

    save_data()
    await message.reply(f"{msg}.")


# --- Хендлер: GIF ---
@dp.message(F.animation)
async def handle_gifs(message: Message):
    file_id = message.animation.file_id
    file = await bot.get_file(file_id)
    file_path = f"temp_{file_id}.mp4"
    await bot.download_file(file.file_path, file_path)
    try:
        cap = cv2.VideoCapture(file_path)
        success, frame = cap.read()
        cap.release()
        if success:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame_rgb)
            current_hash = str(imagehash.dhash(img))
            if current_hash in FORBIDDEN_HASHES:
                await message.delete()
    except Exception as e:
        logging.error(f"Error handling GIF: {e}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


# --- УНИВЕРСАЛЬНЫЙ ХЕНДЛЕР: ТРИГГЕРЫ + НЕИЗВЕСТНЫЕ КОМАНДЫ ---
@dp.message(F.text)
async def process_text_and_unknown_commands(message: Message):
    msg_text = message.text.lower()
    bot_user = await bot.get_me()
    bot_mention = f"@{bot_user.username}".lower()

    trigger_fired = False
    for trigger, data in TRIGGERS_DB.items():
        mode = data.get("mode", "common")
        answers = data.get("answers", [])

        match = False
        if mode == "fulltrigger":
            if trigger in msg_text: match = True
        elif mode == "common":
            if re.search(r'\b' + re.escape(trigger) + r'\b', msg_text): match = True

        if match and answers:
            await message.reply(random.choice(answers))
            trigger_fired = True
            break

    if not trigger_fired:
        if bot_mention in msg_text:
            await message.reply("🤔 Я не знаю такой команды.\nПопробуйте `/factcheck` или `add`.")


async def main():
    await set_main_menu(bot)
    logging.info("Бот запущен. Ожидание сообщений...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())'''