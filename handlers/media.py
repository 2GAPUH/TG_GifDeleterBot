import os
import logging
from aiogram import Router, F
from aiogram.types import Message
import imagehash
from PIL import Image
import cv2
from config import FORBIDDEN_HASHES

router = Router()


@router.message(F.animation)
async def handle_gifs(message: Message):
    file_id = message.animation.file_id
    file = await message.bot.get_file(file_id)
    file_path = f"temp_{file_id}.mp4"
    await message.bot.download_file(file.file_path, file_path)

    try:
        cap = cv2.VideoCapture(file_path)
        success, frame = cap.read()
        cap.release()
        if success:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame_rgb)
            current_hash = str(imagehash.dhash(img))
            if current_hash in FORBIDDEN_HASHES:
                await message.delete()
    except Exception as e:
        logging.error(f"Error handling GIF: {e}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)