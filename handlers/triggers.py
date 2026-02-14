import re
import random
from collections import deque
from aiogram import Router, F
from aiogram.types import Message, ChatAction
from database import TRIGGERS_DB, save_data
# Импортируем функцию генерации бреда
from services.deepseek import generate_rofl_response

router = Router()

# Глобальный словарь для хранения истории сообщений
# Ключ: chat_id, Значение: deque (очередь из 15 последних сообщений)
CHAT_HISTORY = {}


@router.message(F.text.lower().contains("add"))
async def add_new_trigger(message: Message):
    # ... (весь код функции добавления триггеров оставляем как был) ...
    text = message.text.strip()
    bot_user = await message.bot.get_me()
    bot_mention = f"@{bot_user.username}"

    if bot_mention.lower() not in text.lower():
        return

    # ... (остальной код функции add) ...
    clean_text = re.sub(re.escape(bot_mention), "", text, flags=re.IGNORECASE).strip()
    # ... и т.д., просто не меняй эту функцию, она ок ...
    pass


@router.message(F.text)
async def process_text_and_unknown_commands(message: Message):
    chat_id = message.chat.id
    user_name = message.from_user.first_name
    msg_text = message.text

    # 1. СОХРАНЯЕМ КОНТЕКСТ
    if chat_id not in CHAT_HISTORY:
        CHAT_HISTORY[chat_id] = deque(maxlen=15)

    # Формат: "Имя: текст сообщения"
    CHAT_HISTORY[chat_id].append(f"{user_name}: {msg_text}")

    # 2. ПРОВЕРЯЕМ ШАНС 1% (ROFL MODE)
    # Если выпало 1, и сообщений в истории хотя бы 3 (чтобы был контекст)
    if random.randint(1, 100) == 1 and len(CHAT_HISTORY[chat_id]) > 2:
        await message.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

        # Берем историю и отправляем в DeepSeek
        history_list = list(CHAT_HISTORY[chat_id])
        rofl_answer = await generate_rofl_response(history_list)

        if rofl_answer:
            # Отвечаем на текущее сообщение
            await message.reply(rofl_answer)
            return  # Прерываем выполнение, чтобы не сработали обычные триггеры

    # 3. СТАНДАРТНАЯ ЛОГИКА ТРИГГЕРОВ (как было у тебя)
    bot_user = await message.bot.get_me()
    bot_mention = f"@{bot_user.username}".lower()
    msg_text_lower = msg_text.lower()

    trigger_fired = False
    for trigger, data in TRIGGERS_DB.items():
        mode = data.get("mode", "common")
        answers = data.get("answers", [])

        match = False
        if mode == "fulltrigger":
            if trigger in msg_text_lower: match = True
        elif mode == "common":
            if re.search(r'\b' + re.escape(trigger) + r'\b', msg_text_lower): match = True

        if match and answers:
            await message.reply(random.choice(answers))
            trigger_fired = True
            break

    # Если триггер не сработал, но было упоминание бота
    if not trigger_fired:
        if bot_mention in msg_text_lower:
            await message.reply("🤔 Я не знаю такой команды.\nПопробуйте `/factcheck` или `add`.")