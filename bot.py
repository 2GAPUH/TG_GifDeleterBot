import asyncio
import os
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
import imagehash
from PIL import Image

TOKEN = "8310127654:AAGX4xWVueRTWm9c76JBqPQ5KG91NTCC86E"
# Список хешей «запрещенок» (примеры хешей)
FORBIDDEN_HASHES = ["8c0c0c0c0c0c0c0c"]

bot = Bot(token=TOKEN)
dp = Dispatcher()


@dp.message(F.animation)
async def handle_gifs(message: Message):
    # 1. Скачиваем файл во временную папку
    file_id = message.animation.file_id
    file = await bot.get_file(file_id)
    file_path = f"temp_{file_id}.mp4"  # Telegram часто отдает GIF как MP4
    await bot.download_file(file.file_path, file_path)

    try:
        # 2. Извлекаем первый кадр и считаем хеш
        # (Для простоты используем библиотеку Pillow, она умеет открывать кадры)
        with Image.open(file_path) as img:
            # Считаем разностный хеш (dhash)
            current_hash = str(imagehash.dhash(img))
            print(f"Хеш присланной гифки: {current_hash}")

            # 3. Сравниваем
            if current_hash in FORBIDDEN_HASHES:
                await message.delete()
                print("Удалено по хешу!")

    except Exception as e:
        print(f"Ошибка анализа: {e}")
    finally:
        # 4. Обязательно удаляем временный файл с сервера
        if os.path.exists(file_path):
            os.remove(file_path)


async def main():
    print("Бот с анализом хешей запущен...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())