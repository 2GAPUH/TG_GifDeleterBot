import logging
import re
from aiogram import Router, F
from aiogram.types import Message
from aiogram.enums import ChatAction
from services.deepseek import ask_question_with_ai

router = Router()


@router.message(F.text.lower().contains("/question"))
async def question_handler(message: Message):
    """Обработчик команды /question с возможным контекстом (reply)"""
    bot_user = await message.bot.get_me()
    bot_mention = f"@{bot_user.username}"
    text = message.text

    # Проверяем что это именно команда /question (с возможным упоминанием бота)
    if not re.match(rf'^/question(@{bot_user.username})?', text.lower()):
        return

    # Извлекаем текст вопроса (убираем команду и упоминание бота)
    question_text = re.sub(rf'^/question(@{bot_user.username})?\s*', '', text, flags=re.IGNORECASE).strip()

    # Если есть ответ на сообщение - это контекст
    context = None
    if message.reply_to_message and message.reply_to_message.text:
        context = message.reply_to_message.text

    # Проверяем что есть либо вопрос, либо контекст
    if not question_text and not context:
        await message.reply(
            "⚠️ Использование:\n"
            "• `/question ваш вопрос` — задать вопрос\n"
            "• Ответить на сообщение + `/question ваш вопрос` — вопрос с контекстом\n"
            "• Ответить на сообщение + `/question` — проанализировать сообщение",
            parse_mode="Markdown"
        )
        return

    logging.info(f"Вопрос от {message.from_user.id}: {question_text[:50] if question_text else 'только контекст'}...")

    # Показываем статус "печатает"
    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    # Вызываем DeepSeek
    answer = await ask_question_with_ai(question=question_text, context=context)

    if answer:
        # Если был контекст (reply), отвечаем на исходное сообщение
        if context and message.reply_to_message:
            await message.reply_to_message.reply(f"🤖 **Ответ DeepSeek:**\n\n{answer}", parse_mode="Markdown")
        else:
            await message.reply(f"🤖 **Ответ DeepSeek:**\n\n{answer}", parse_mode="Markdown")
    else:
        await message.reply("❌ Не удалось получить ответ от DeepSeek. Попробуйте позже.")
