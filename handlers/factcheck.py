import logging
from aiogram import Router, F
from aiogram.types import Message
from aiogram.enums import ChatAction
from services.deepseek import check_fact_with_ai

router = Router()


@router.message(F.text.lower().contains("fact checking") | (F.text.lower() == "/factcheck"))
async def fact_check_handler(message: Message):
    bot_user = await message.bot.get_me()
    bot_mention = f"@{bot_user.username}"
    text = message.text.lower()

    if "/factcheck" not in text and bot_mention.lower() not in text:
        return

    if not message.reply_to_message or not message.reply_to_message.text:
        await message.reply("⚠️ Эту команду нужно использовать **в ответ** (Reply) на сообщение с текстом.")
        return

    original_text = message.reply_to_message.text
    logging.info(f"Запрос Fact Check для: {original_text[:50]}...")

    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    # Вызываем вынесенную логику
    answer = await check_fact_with_ai(original_text)

    await message.reply_to_message.reply(f"🧠 **Анализ DeepSeek:**\n\n{answer}", parse_mode="Markdown")