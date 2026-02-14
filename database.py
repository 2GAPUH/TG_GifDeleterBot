import os
import json
import logging
from config import DATA_FILE

TRIGGERS_DB = {}

def load_data():
    global TRIGGERS_DB
    if not os.path.exists(DATA_FILE):
        initial_data = {
            "фемб": {
                "mode": "fulltrigger",
                "answers": ["Да, это фембой!", "Осуждаю."]
            }
        }
        save_data(initial_data)
        TRIGGERS_DB = initial_data
    else:
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            migrated = False
            for k, v in data.items():
                if isinstance(v, list):
                    data[k] = {"mode": "common", "answers": v}
                    migrated = True
            TRIGGERS_DB = data
            if migrated:
                save_data()
            logging.info(f"База загружена. Триггеров: {len(TRIGGERS_DB)}")
        except json.JSONDecodeError:
            TRIGGERS_DB = {}

def save_data(data=None):
    if data is None:
        data = TRIGGERS_DB
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# Инициализируем базу при импорте
load_data()