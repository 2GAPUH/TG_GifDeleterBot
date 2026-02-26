from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeDefault

async def set_main_menu(bot: Bot):
    main_menu_commands = [
        BotCommand(command="factcheck", description="Проверить факт (в ответ на сообщение)"),
        BotCommand(command="question", description="Задать вопрос DeepSeek"),
        BotCommand(command="add", description="Добавить триггер: @bot add \"слово\" \"ответ\""),
        BotCommand(command="help", description="Справка по боту")
    ]
    await bot.set_my_commands(main_menu_commands, scope=BotCommandScopeDefault())