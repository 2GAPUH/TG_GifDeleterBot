import aiohttp
import logging
import asyncio
from config import DEEPSEEK_TOKEN

async def check_fact_with_ai(original_text: str) -> str:
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

    try:
        timeout = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    return result['choices'][0]['message']['content']
                else:
                    error_text = await response.text()
                    logging.error(f"DeepSeek API Error {response.status}: {error_text}")
                    return f"❌ Ошибка API ({response.status}). Проверьте логи."
    except asyncio.TimeoutError:
        logging.error("DeepSeek API Timeout")
        return "⌛️ DeepSeek долго не отвечает (тайм-аут)."
    except Exception as e:
        logging.exception(f"Критическая ошибка при запросе: {e}")
        return "❌ Произошла внутренняя ошибка при запросе."