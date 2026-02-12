import asyncio
import os
import random  # Для случайного выбора
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
import imagehash
from PIL import Image
import cv2

TOKEN = "8310127654:AAGX4xWVueRTWm9c76JBqPQ5KG91NTCC86E"
FORBIDDEN_HASHES = ["2f71f1f2f0608838"]
ANSWERS_FILE = "answers.txt"

bot = Bot(token=TOKEN)
dp = Dispatcher()


# Функция загрузки ответов из файла
def load_answers():
    if not os.path.exists(ANSWERS_FILE):
        print(f"Файл {ANSWERS_FILE} не найден! Создайте его.")
        return []

    with open(ANSWERS_FILE, "r", encoding="utf-8") as f:
        # Читаем строки и убираем пробелы/переносы
        lines = [line.strip() for line in f if line.strip()]
    return lines


# Загружаем ответы в память при запуске
ANSWERS_POOL = load_answers()


# --- Хендлер для текста, содержащего "фемб" ---
@dp.message(F.text.lower().contains("фемб"))
async def handle_keywords(message: Message):
    if ANSWERS_POOL:
        # Выбираем случайный ответ
        random_answer = random.choice(ANSWERS_POOL)
        # Отвечаем на сообщение
        await message.reply(random_answer)
    else:
        print("Список ответов пуст или файл не найден.")


# --- Хендлер для GIF ---
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
        else:
            print("Не удалось прочитать кадр из видео")

    except Exception as e:
        print(f"Ошибка анализа: {e}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


async def main():
    print(f"Бот запущен. Загружено ответов: {len(ANSWERS_POOL)}")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())