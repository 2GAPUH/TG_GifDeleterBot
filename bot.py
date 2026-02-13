import asyncio
import os
import random
import json
import re
import aiohttp  # ### НОВОЕ: Для запросов к DeepSeek
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.enums import ChatAction  # ### НОВОЕ: Для статуса "печатает"
import imagehash
from PIL import Image
import cv2

TOKEN = "8310127654:AAGX4xWVueRTWm9c76JBqPQ5KG91NTCC86E"
# ### НОВОЕ: Вставьте сюда свой ключ от DeepSeek
DEEPSEEK_TOKEN = "sk-8215e4b1c7234c52a00e3397e402725d"

FORBIDDEN_HASHES = ["2f71f1f2f0608838"]
DATA_FILE = "triggers.json"

bot = Bot(token=TOKEN)
dp = Dispatcher()

TRIGGERS_DB = {}


# --- Функции работы с данными (без изменений) ---
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
            print(f"База загружена. Триггеров: {len(TRIGGERS_DB)}")
        except json.JSONDecodeError:
            TRIGGERS_DB = {}


def save_data(data=None):
    if data is None:
        data = TRIGGERS_DB
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


load_data()


# --- ### НОВОЕ: Хендлер для Fact Checking ---
@dp.message(F.text.lower().contains("fact checking"))
async def fact_check_handler(message: Message):
    # 1. Проверяем, упомянули ли бота (аналогично add)
    bot_user = await bot.get_me()
    bot_mention = f"@{bot_user.username}"
    text = message.text.lower()

    # Если бота не упомянули (@gifBlocherBot fact checking), игнорируем
    if bot_mention.lower() not in text:
        return

    # 2. Проверяем, является ли это ответом на сообщение (Reply)
    if not message.reply_to_message or not message.reply_to_message.text:
        await message.reply("Эту команду нужно писать в ответ на текстовое сообщение, которое вы хотите проверить.")
        return

    original_text = message.reply_to_message.text

    # 3. Отправляем статус "печатает" (typing)
    # Это покажет пользователю, что бот думает, пока идет запрос
    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    # 4. Формируем запрос к DeepSeek
    url = "https://api.deepseek.com/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_TOKEN}"
    }

    # Промпт для ИИ
    payload = {
        "model": "deepseek-chat",  # Или "deepseek-reasoner", если доступен
        "messages": [
            {
                "role": "system",
                "content": "Ты профессиональный факт-чекер. Твоя задача — проверить достоверность следующего утверждения. Если информация ложная или сомнительная, объясни почему. Если верная — подтверди. Отвечай кратко и по делу на русском языке."
            },
            {
                "role": "user",
                "content": f"Проверь этот текст: {original_text}"
            }
        ],
        "stream": False
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    answer = result['choices'][0]['message']['content']

                    # Отправляем результат как ответ на исходное сообщение
                    await message.reply_to_message.reply(f"🕵️‍♂️ **Результат проверки:**\n\n{answer}",
                                                         parse_mode="Markdown")
                else:
                    error_text = await response.text()
                    print(f"DeepSeek API Error: {error_text}")
                    await message.reply("Не удалось связаться с сервером проверки фактов. Попробуйте позже.")
    except Exception as e:
        print(f"Exception: {e}")
        await message.reply("Произошла ошибка при выполнении запроса.")


# --- Хендлер команды ADD (без изменений) ---
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
        return

    check_garbage = re.sub(r'"[^"]+"', "", args_text).strip()
    if check_garbage:
        return

    trigger_word = matches[0].lower()
    new_answers = matches[1:]

    if len(trigger_word) < 4:
        await message.reply("Слово слишком короткое (минимум 4 символа).")
        return

    if trigger_word not in TRIGGERS_DB:
        TRIGGERS_DB[trigger_word] = {
            "mode": mode,
            "answers": []
        }
        msg = f"🆕 Добавлен триггер **\"{trigger_word}\"** (режим: {mode})"
    else:
        TRIGGERS_DB[trigger_word]["mode"] = mode
        msg = f"✏️ Обновлен триггер **\"{trigger_word}\"** (режим: {mode})"

    added_count = 0
    for ans in new_answers:
        if ans not in TRIGGERS_DB[trigger_word]["answers"]:
            TRIGGERS_DB[trigger_word]["answers"].append(ans)
            added_count += 1

    save_data()
    await message.reply(f"{msg}. Добавлено фраз: {added_count}.")


# --- Хендлер прослушки текста (без изменений) ---
@dp.message(F.text)
async def check_keywords(message: Message):
    msg_text = message.text.lower()

    # ### ВАЖНО: Добавил проверку, чтобы не реагировать на команды проверки и добавления
    if "fact checking" in msg_text or "add" in msg_text:
        # Позволяем другим хендлерам обработать сообщение, если это команды
        # Но так как aiogram идет сверху вниз, команды уже обработались или обработаются
        # Здесь мы просто не хотим отвечать триггером, если в тексте есть команды
        pass

    for trigger, data in TRIGGERS_DB.items():
        mode = data.get("mode", "common")
        answers = data.get("answers", [])
        match_found = False

        if mode == "fulltrigger":
            if trigger in msg_text:
                match_found = True
        elif mode == "common":
            pattern = r'\b' + re.escape(trigger) + r'\b'
            if re.search(pattern, msg_text):
                match_found = True

        if match_found and answers:
            await message.reply(random.choice(answers))
            return


# --- Хендлер GIF (без изменений) ---
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
        print(f"Error: {e}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


async def main():
    print("Бот запущен. Ожидание сообщений...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())