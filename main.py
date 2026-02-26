import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import TOKEN
from utils.commands import set_main_menu

# Импортируем роутеры из хендлеров
from handlers.factcheck import router as factcheck_router
from handlers.question import router as question_router
from handlers.media import router as media_router
from handlers.triggers import router as triggers_router


async def main():
    # Настраиваем логирование
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    # Инициализация бота и диспетчера
    bot = Bot(token=TOKEN)
    dp = Dispatcher()

    # Регистрация роутеров. Порядок важен!
    dp.include_router(factcheck_router)
    dp.include_router(question_router)
    dp.include_router(media_router)
    dp.include_router(triggers_router)  # Универсальный перехватчик текста всегда последний

    # Настройка меню
    await set_main_menu(bot)

    logging.info("Бот успешно запущен. Ожидание сообщений...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())