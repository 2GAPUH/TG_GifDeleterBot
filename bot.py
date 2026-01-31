import asyncio
import os
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
import imagehash
from PIL import Image
import cv2 # Добавь этот импорт в начало файла

TOKEN = "8310127654:AAGX4xWVueRTWm9c76JBqPQ5KG91NTCC86E"
# Список хешей «запрещенок» (примеры хешей)
FORBIDDEN_HASHES = ["2f71f1f2f0608838"]

bot = Bot(token=TOKEN)
dp = Dispatcher()


@dp.message(F.animation)
async def handle_gifs(message: Message):
    file_id = message.animation.file_id
    file = await bot.get_file(file_id)
    file_path = f"temp_{file_id}.mp4"
    await bot.download_file(file.file_path, file_path)

    try:
        # Пробуем достать кадр через OpenCV
        cap = cv2.VideoCapture(file_path)
        success, frame = cap.read()
        cap.release()

        if success:
            # Превращаем кадр OpenCV в формат Pillow для хеширования
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
    print("Бот с анализом хешей запущен...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())