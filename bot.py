import asyncio
import os
import random
import json
import shlex  # Для правильного разбора строк в кавычках
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import Command
import imagehash
from PIL import Image
import cv2

TOKEN = "8310127654:AAGX4xWVueRTWm9c76JBqPQ5KG91NTCC86E"
FORBIDDEN_HASHES = ["2f71f1f2f0608838"]
DATA_FILE = "triggers.json"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Глобальная переменная для хранения базы триггеров
# Структура: {"слово": ["ответ1", "ответ2"], "фемб": ["...", "..."]}
TRIGGERS_DB = {}


# --- Функции работы с данными (JSON) ---
def load_data():
    """Загружает базу триггеров из JSON файла."""
    global TRIGGERS_DB
    if not os.path.exists(DATA_FILE):
        print(f"Файл {DATA_FILE} не найден. Создаю новый с примером.")
        # Создаем стартовый файл с примером для 'фемб'
        initial_data = {
            "фемб": ["Да, это фембой!", "Осуждаю.", "Интересно..."]
        }
        save_data(initial_data)
        TRIGGERS_DB = initial_data
    else:
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                TRIGGERS_DB = json.load(f)
            print(f"База загружена. Количество триггеров: {len(TRIGGERS_DB)}")
        except json.JSONDecodeError:
            print("Ошибка чтения JSON. Файл поврежден или пуст.")
            TRIGGERS_DB = {}


def save_data(data=None):
    """Сохраняет текущую базу в файл."""
    if data is None:
        data = TRIGGERS_DB
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


# Загружаем данные при старте
load_data()


# --- Хендлер для команды ADD ---
# Ловит сообщения, начинающиеся с "add" (регистр не важен) или команду /add
@dp.message(F.text.lower().startswith("add"))
async def add_new_trigger(message: Message):
    text = message.text

    # Убираем юзернейм бота, если он был упомянут (например, @bot add ...)
    bot_user = await bot.get_me()
    username = f"@{bot_user.username}"
    if username.lower() in text.lower():
        text = text.replace(username, "").replace(username.lower(), "")

    try:
        # shlex.split позволяет разбить строку с учетом кавычек
        # add "слово" "ответ 1" "ответ 2" -> ['add', 'слово', 'ответ 1', 'ответ 2']
        args = shlex.split(text)
    except ValueError:
        await message.reply("Ошибка в формате кавычек. Убедитесь, что все кавычки закрыты.")
        return

    # Проверка формата: должно быть минимум 3 элемента: add, слово, ответ
    if len(args) < 3:
        await message.reply(
            "Неверный формат.\n"
            "Используйте: `add \"слово\" \"ответ1\" \"ответ2\"`",
            parse_mode="Markdown"
        )
        return

    # args[0] это 'add'
    trigger_word = args[1].lower()  # Приводим триггер к нижнему регистру
    new_answers = args[2:]

    # Проверка длины слова
    if len(trigger_word) < 4:
        await message.reply("Слишком короткое слово. Минимум 4 символа.")
        return

    # Добавляем данные
    if trigger_word not in TRIGGERS_DB:
        TRIGGERS_DB[trigger_word] = []
        msg_prefix = f"Создан новый триггер **{trigger_word}**"
    else:
        msg_prefix = f"Обновлен триггер **{trigger_word}**"

    # Добавляем только уникальные ответы, чтобы не дублировать
    added_count = 0
    for ans in new_answers:
        if ans not in TRIGGERS_DB[trigger_word]:
            TRIGGERS_DB[trigger_word].append(ans)
            added_count += 1

    # Сохраняем в файл
    save_data()

    await message.reply(f"{msg_prefix}. Добавлено фраз: {added_count}.")


# --- Хендлер для проверки текста на наличие триггеров ---
# Срабатывает на любой текст, если это НЕ команда add
@dp.message(F.text)
async def check_keywords(message: Message):
    # Если это сообщение начинается с add, мы его не обрабатываем здесь (оно уйдет в хендлер выше)
    if message.text.lower().startswith("add") or message.text.lower().startswith("/add"):
        return

    msg_text = message.text.lower()

    # Проходимся по всем ключам (словам) из базы
    for trigger, answers in TRIGGERS_DB.items():
        if trigger in msg_text:
            if answers:
                response = random.choice(answers)
                await message.reply(response)
                # Если хотим, чтобы срабатывал только первый найденный триггер - выходим
                return

            # --- Хендлер для GIF (без изменений, кроме удаления лишнего) ---


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
            print(f"Хеш присланной гифки: {current_hash}")

            if current_hash in FORBIDDEN_HASHES:
                await message.delete()
                print("Удалено по хешу!")
    except Exception as e:
        print(f"Ошибка анализа: {e}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


async def main():
    print("Бот запущен.")
    print(f"Загруженные триггеры: {list(TRIGGERS_DB.keys())}")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())