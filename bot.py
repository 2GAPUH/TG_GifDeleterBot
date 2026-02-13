import asyncio
import os
import random
import json
import re  # Для регулярных выражений (проверка кавычек и границ слов)
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
import imagehash
from PIL import Image
import cv2

TOKEN = "8310127654:AAGX4xWVueRTWm9c76JBqPQ5KG91NTCC86E"
FORBIDDEN_HASHES = ["2f71f1f2f0608838"]
DATA_FILE = "triggers.json"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Глобальная переменная для хранения базы
# Новая структура:
# {
#   "word": {
#       "mode": "common",       # или "fulltrigger"
#       "answers": ["ans1", "ans2"]
#   }
# }
TRIGGERS_DB = {}


# --- Функции работы с данными ---
def load_data():
    global TRIGGERS_DB
    if not os.path.exists(DATA_FILE):
        # Создаем стартовый файл с примером
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

            # Миграция старой базы (если был просто список), чтобы код не упал
            # Превращаем {"word": ["ans"]} -> {"word": {"mode": "common", "answers": ["ans"]}}
            migrated = False
            for k, v in data.items():
                if isinstance(v, list):
                    data[k] = {"mode": "common", "answers": v}
                    migrated = True

            TRIGGERS_DB = data
            if migrated:
                save_data()  # Сохраняем обновленную структуру
                print("База данных обновлена до нового формата.")

            print(f"База загружена. Триггеров: {len(TRIGGERS_DB)}")
        except json.JSONDecodeError:
            TRIGGERS_DB = {}


def save_data(data=None):
    if data is None:
        data = TRIGGERS_DB
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


load_data()


# --- Хендлер команды ADD ---
# Фильтр: сообщение должно содержать "add"
@dp.message(F.text.lower().contains("add"))
async def add_new_trigger(message: Message):
    text = message.text.strip()
    bot_user = await bot.get_me()
    bot_mention = f"@{bot_user.username}"

    # 1. Проверка: Есть ли упоминание бота? Если нет — игнорируем полностью.
    if bot_mention.lower() not in text.lower():
        return  # Просто выходим, бот делает вид, что не видит сообщение

    # Убираем упоминание бота из текста, чтобы было удобнее парсить
    # re.IGNORECASE позволяет заменить @Name, @name, @NAME
    clean_text = re.sub(re.escape(bot_mention), "", text, flags=re.IGNORECASE).strip()

    # 2. Определяем режим (флаги)
    mode = "common"  # По умолчанию
    if "-fulltrigger" in clean_text.lower():
        mode = "fulltrigger"
        # Вырезаем флаг из текста
        clean_text = re.sub(r"-fulltrigger", "", clean_text, flags=re.IGNORECASE)
    elif "-common" in clean_text.lower():
        mode = "common"
        clean_text = re.sub(r"-common", "", clean_text, flags=re.IGNORECASE)

    # 3. Проверка формата: add "слово" "ответ"...
    # Ищем слово 'add' в начале оставшейся строки
    if not clean_text.lower().startswith("add"):
        return  # Если после удаления ника не осталось add, уходим

    # Удаляем само слово add
    args_text = clean_text[3:].strip()

    # 4. ВАЖНО: Парсинг через регулярку, чтобы принимать ТОЛЬКО кавычки
    # Паттерн ищет все вхождения текста внутри двойных кавычек: "текст"
    # Если пользователь напишет слово без кавычек, оно не попадет в matches
    matches = re.findall(r'"([^"]+)"', args_text)

    # Валидация:
    # Если пользователь написал текст без кавычек, matches будет меньше, чем слов в сообщении.
    # Самый надежный способ проверить формат пользователя:
    # Проверяем, что остаток строки состоит ТОЛЬКО из кавычек и пробелов
    # Склеиваем найденное обратно и сравниваем длины (упрощенно) или просто доверяем regex.

    # Требование пользователя: "add "word" answer1 answer2" — не реагировать.
    # Regex `findall` найдет только "word". Длина matches будет 1.
    # Нам нужно минимум 2 элемента (1 триггер + 1 ответ)
    if len(matches) < 2:
        # Тут можно либо молчать, либо сказать ошибку.
        # По просьбе "не должен реагировать на ответы без кавычек" — лучше промолчим
        # или выдадим ошибку только если формат совсем плохой, но явно была попытка.
        # Сейчас сделаем строгий выход, если не нашли минимум 2 фразы в кавычках.
        return

        # Дополнительная проверка "строгости":
    # Если после удаления всех "..." и пробелов что-то осталось, значит был текст без кавычек.
    check_garbage = re.sub(r'"[^"]+"', "", args_text).strip()
    if check_garbage:
        # Если осталось что-то кроме пустоты (например, слово без кавычек), игнорируем
        # await message.reply("Ошибка: все аргументы должны быть в кавычках!") # Можно раскомментировать для отладки
        return

    trigger_word = matches[0].lower()  # Первое слово в кавычках — триггер
    new_answers = matches[1:]  # Остальное — ответы

    if len(trigger_word) < 4:
        await message.reply("Слово слишком короткое (минимум 4 символа).")
        return

    # Запись в базу
    if trigger_word not in TRIGGERS_DB:
        TRIGGERS_DB[trigger_word] = {
            "mode": mode,
            "answers": []
        }
        msg = f"🆕 Добавлен триггер **\"{trigger_word}\"** (режим: {mode})"
    else:
        # Если слово есть, обновляем режим на новый указанный (или оставляем старый?)
        # Обычно лучше обновить настройки, если пользователь их указал
        TRIGGERS_DB[trigger_word]["mode"] = mode
        msg = f"✏️ Обновлен триггер **\"{trigger_word}\"** (режим: {mode})"

    # Добавляем ответы (без дублей)
    added_count = 0
    for ans in new_answers:
        if ans not in TRIGGERS_DB[trigger_word]["answers"]:
            TRIGGERS_DB[trigger_word]["answers"].append(ans)
            added_count += 1

    save_data()
    await message.reply(f"{msg}. Добавлено фраз: {added_count}.")


# --- Хендлер прослушки текста ---
@dp.message(F.text)
async def check_keywords(message: Message):
    # Игнорируем команды, начинающиеся с add (они обрабатываются выше, если с тегом)
    # Но если юзер пишет просто "add word" без тега, этот хендлер это поймает.
    # Чтобы бот не реагировал на слово "add" как на триггер (если вдруг кто-то добавит его),
    # можно добавить проверку, но пока оставим как есть.

    msg_text = message.text.lower()

    for trigger, data in TRIGGERS_DB.items():
        mode = data.get("mode", "common")  # common по умолчанию
        answers = data.get("answers", [])

        match_found = False

        if mode == "fulltrigger":
            # Простой поиск подстроки
            if trigger in msg_text:
                match_found = True

        elif mode == "common":
            # Поиск отдельного слова.
            # \b означает "границу слова".
            # \bword\b найдет "word", "word.", "word!"
            # Но НЕ найдет "wordless", "sword".
            pattern = r'\b' + re.escape(trigger) + r'\b'
            if re.search(pattern, msg_text):
                match_found = True

        if match_found and answers:
            await message.reply(random.choice(answers))
            return  # Отвечаем только на первый найденный триггер


# --- Хендлер GIF ---
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