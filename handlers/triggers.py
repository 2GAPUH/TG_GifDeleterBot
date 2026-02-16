import re
import random
from collections import deque
from aiogram import Router, F
from aiogram.types import Message
from aiogram.enums import ChatAction  # <--- ИСПРАВЛЕНО: берем из enums
from database import TRIGGERS_DB, save_data
# Убедитесь, что deepseek.py лежит в папке services, иначе поменяйте на просто 'deepseek'
from services.deepseek import generate_rofl_response

router = Router()

# Глобальный словарь для хранения истории сообщений
CHAT_HISTORY = {}


@router.message(F.text.lower().contains("add"))
async def add_new_trigger(message: Message):
    text = message.text.strip()
    bot_user = await message.bot.get_me()
    bot_mention = f"@{bot_user.username}"

    if bot_mention.lower() not in text.lower():
        return

    clean_text = re.sub(re.escape(bot_mention), "", text, flags=re.IGNORECASE).strip()
    mode = "common"

    if "-fulltrigger" in clean_text.lower():
        mode = "fulltrigger"
        clean_text = re.sub(r"-fulltrigger", "", clean_text, flags=re.IGNORECASE)
    elif "-common" in clean_text.lower():
        mode = "common"
        clean_text = re.sub(r"-common", "", clean_text, flags=re.IGNORECASE)

    if not clean_text.lower().startswith("add"):
        return

    args_text = clean_text[3:].strip()
    matches = re.findall(r'"([^"]+)"', args_text)

    if len(matches) < 2:
        await message.reply("⚠️ Формат: `@bot add \"триггер\" \"ответ\"`")
        return

    trigger_word = matches[0].lower()
    new_answers = matches[1:]

    if len(trigger_word) < 3:
        await message.reply("Слово слишком короткое.")
        return

    if trigger_word not in TRIGGERS_DB:
        TRIGGERS_DB[trigger_word] = {"mode": mode, "answers": []}
        msg = f"🆕 Добавлен триггер **\"{trigger_word}\"**"
    else:
        TRIGGERS_DB[trigger_word]["mode"] = mode
        msg = f"✏️ Обновлен триггер **\"{trigger_word}\"**"

    for ans in new_answers:
        if ans not in TRIGGERS_DB[trigger_word]["answers"]:
            TRIGGERS_DB[trigger_word]["answers"].append(ans)

    save_data()
    await message.reply(f"{msg}.")


@router.message(F.text)
async def process_text_and_unknown_commands(message: Message):
    chat_id = message.chat.id
    user_name = message.from_user.first_name
    msg_text = message.text

    # 1. СОХРАНЯЕМ КОНТЕКСТ
    if chat_id not in CHAT_HISTORY:
        CHAT_HISTORY[chat_id] = deque(maxlen=30)

    # Формат: "Имя: текст сообщения"
    CHAT_HISTORY[chat_id].append(f"{user_name}: {msg_text}")

    # 2. ПРОВЕРЯЕМ ШАНС 1% (ROFL MODE)
    if random.randint(1, 1000) == 1 and len(CHAT_HISTORY[chat_id]) > 2:
        # Теперь ChatAction работает корректно через enums
        await message.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

        history_list = list(CHAT_HISTORY[chat_id])
        rofl_answer = await generate_rofl_response(history_list)

        if rofl_answer:
            await message.reply(rofl_answer)
            return

    # 3. СТАНДАРТНАЯ ЛОГИКА ТРИГГЕРОВ
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