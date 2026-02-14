import re
import random
from aiogram import Router, F
from aiogram.types import Message
from database import TRIGGERS_DB, save_data

router = Router()

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
    msg_text = message.text.lower()
    bot_user = await message.bot.get_me()
    bot_mention = f"@{bot_user.username}".lower()

    trigger_fired = False
    for trigger, data in TRIGGERS_DB.items():
        mode = data.get("mode", "common")
        answers = data.get("answers", [])

        match = False
        if mode == "fulltrigger":
            if trigger in msg_text: match = True
        elif mode == "common":
            if re.search(r'\b' + re.escape(trigger) + r'\b', msg_text): match = True

        if match and answers:
            await message.reply(random.choice(answers))
            trigger_fired = True
            break

    # Если триггер не сработал, но было упоминание бота
    if not trigger_fired:
        if bot_mention in msg_text:
            await message.reply("🤔 Я не знаю такой команды.\nПопробуйте `/factcheck` или `add`.")