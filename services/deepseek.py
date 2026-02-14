import aiohttp
import logging
import asyncio
from config import DEEPSEEK_TOKEN


# ... (ваш старый код check_fact_with_ai оставляем без изменений) ...

async def check_fact_with_ai(original_text: str) -> str:
    # ... (весь код функции check_fact_with_ai) ...
    url = "https://api.deepseek.com/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_TOKEN}"
    }

    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "Ты факт-чекер. Проверь утверждение. Ответь кратко на русском."},
            {"role": "user", "content": f"Правда ли это: {original_text}"}
        ],
        "stream": False
    }

    # ... (логика запроса, как была у тебя) ...
    try:
        timeout = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    return result['choices'][0]['message']['content']
                # ... обработка ошибок ...
                else:
                    return "Ошибка API"
    except Exception as e:
        return "Ошибка"


# 👇 ДОБАВЛЯЕМ НОВУЮ ФУНКЦИЮ 👇
async def generate_rofl_response(context_messages: list) -> str:
    url = "https://api.deepseek.com/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_TOKEN}"
    }

    # Формируем текст переписки для промпта
    history_text = "\n".join(context_messages)

    payload = {
        "model": "deepseek-chat",
        "messages": [
            {
                "role": "system",
                "content": (
                    "Ты — ехидный, циничный и очень смешной участник чата. "
                    "Твоя задача — прочитать контекст переписки и выдать короткий, "
                    "абсурдный, неожиданный или 'лютый' комментарий. "
                    "Можешь использовать сленг, мемы, черный юмор. "
                    "Главная цель — чтобы люди посмеялись или удивились твоему бреду."
                )
            },
            {"role": "user", "content": f"Вот последние сообщения в чате:\n{history_text}\n\nВыдай комментарий:"}
        ],
        "stream": False,
        "temperature": 1.3  # Повышаем температуру для большей креативности/бреда
    }

    try:
        timeout = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    return result['choices'][0]['message']['content']
                else:
                    logging.error(f"DeepSeek ROFL Error {response.status}")
                    return None
    except Exception as e:
        logging.exception(f"ROFL request failed: {e}")
        return None