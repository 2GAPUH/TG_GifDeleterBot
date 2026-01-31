import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message

# Вставь сюда свой токен, который дал BotFather
TOKEN = "8310127654:AAGX4xWVueRTWm9c76JBqPQ5KG91NTCC86E"

# Вставь сюда ID гифки, когда узнаешь его (см. Шаг 4)
FORBIDDEN_GIF_ID = "AgADRwkAAgHjJVA"

bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message(F.animation)
async def handle_gifs(message: Message):
    # Эта строка печатает ID любой присланной гифки в консоль
    print(f"ID гифки: {message.animation.file_unique_id}")

    # Проверка: если ID совпадает — удаляем
    if message.animation.file_unique_id == FORBIDDEN_GIF_ID:
        try:
            await message.delete()
        except Exception as e:
            print(f"Не удалось удалить: {e}")

async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())