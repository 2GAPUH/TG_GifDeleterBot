import os
import json
import sys
import logging

FORBIDDEN_HASHES = ["2f71f1f2f0608838"]
DATA_FILE = "triggers.json"

def load_api_keys():
    if not os.path.exists("api_keys.json"):
        logging.critical("Файл api_keys.json не найден! Бот остановлен.")
        sys.exit(1)

    try:
        with open("api_keys.json", "r", encoding="utf-8") as f:
            keys = json.load(f)
            tg_key = keys.get("telegram_api_key")
            ds_key = keys.get("deepseek_api_key")

            if not tg_key or not ds_key:
                logging.critical("В файле api_keys.json отсутствуют нужные ключи! Бот остановлен.")
                sys.exit(1)

            return tg_key, ds_key
    except json.JSONDecodeError:
        logging.critical("Ошибка синтаксиса в api_keys.json. Проверьте запятые и кавычки!")
        sys.exit(1)

TOKEN, DEEPSEEK_TOKEN = load_api_keys()