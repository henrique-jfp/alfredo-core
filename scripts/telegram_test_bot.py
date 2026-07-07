"""
Bot Telegram para testes do Alfredo.
Manda um áudio, o bot repassa pro Alfredo e devolve a resposta.
"""
import os, sys, io, time, json, logging, subprocess, tempfile
from pathlib import Path

import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("alfredo.tgbot")

# ====== CONFIG ======
TELEGRAM_TOKEN = "8143006820:AAH6trfj9elf90mzLufR8B4y6jxJzvaj6T8"
ALFREDO_URL = "http://192.168.0.56:10001"
ALFREDO_TOKEN = "secret-token-123"
DEVICE_ID = "telegram-bot"
ROOM_ID = "ROOM_LIVING"
# ====================


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Manda um audio que eu passo pro Alfredo!\n"
        "Ele transcreve, processa e responde."
    )


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    audio = msg.voice or msg.audio
    if not audio:
        await msg.reply_text("Manda um audio!")
        return

    await msg.reply_chat_action("typing")

    file = await audio.get_file()
    tmp_dir = tempfile.gettempdir()
    ts = int(time.time())
    ogg_path = os.path.join(tmp_dir, f"tg_{ts}.ogg")
    wav_path = os.path.join(tmp_dir, f"tg_{ts}.wav")
    mp3_path = os.path.join(tmp_dir, f"tg_{ts}.mp3")

    try:
        await file.download_to_drive(ogg_path)
        subprocess.run([
            "ffmpeg", "-y", "-i", ogg_path,
            "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le",
            wav_path
        ], capture_output=True)

        if not os.path.exists(wav_path):
            await msg.reply_text("Erro ao converter audio.")
            return

        headers = {
            "X-Device-ID": DEVICE_ID,
            "X-Room-ID": ROOM_ID,
            "Authorization": f"Bearer {ALFREDO_TOKEN}"
        }
        t0 = time.time()
        resp = requests.post(
            f"{ALFREDO_URL}/api/voice",
            headers=headers,
            files={"file": ("audio.wav", open(wav_path, "rb"), "audio/wav")},
            timeout=120
        )

        elapsed = time.time() - t0

        if resp.status_code != 200:
            await msg.reply_text(f"Alfredo erro {resp.status_code}: {resp.text[:200]}")
            return

        ct = resp.headers.get("content-type", "")
        if "audio" in ct:
            with open(mp3_path, "wb") as f:
                f.write(resp.content)

            if os.path.getsize(mp3_path) > 500:
                with open(mp3_path, "rb") as f:
                    await msg.reply_audio(
                        f,
                        title=f"Alfredo | {elapsed:.1f}s",
                        performer="Alfredo",
                        duration=0
                    )
            else:
                await msg.reply_text(f"[audio vazio, {elapsed:.1f}s]")
        else:
            await msg.reply_text(f"[{elapsed:.1f}s] {resp.text[:200]}")

    except Exception as e:
        logger.error(f"Erro: {e}")
        await msg.reply_text(f"Erro: {e}")
    finally:
        for p in [ogg_path, wav_path, mp3_path]:
            try: os.remove(p)
            except: pass


def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice))
    logger.info("Bot Telegram rodando... Manda um audio!")
    app.run_polling()


if __name__ == "__main__":
    main()
