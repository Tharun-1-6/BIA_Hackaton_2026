import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Setup clean console printing format
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def save_file(media, subdir: str, name: str) -> None:
    folder = Path(__file__).parent / subdir
    folder.mkdir(exist_ok=True)
    await (await media.get_file()).download_to_drive(folder / name)
    print(f"Saved to: {folder / name}")

# A catch-all function that prints any interaction to the console
async def log_interaction(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message = update.effective_message
    
    print("\n--- NEW INTERACTION DETECTED ---")
    print(f"User: {user.first_name} {user.last_name or ''} (@{user.username or 'No Username'})")
    print(f"User ID: {user.id}")
    
    if message:
        if message.text:
            print(f"Interaction Type: Text / Command")
            print(f"Content: \"{message.text}\"")
        elif message.photo:
            print(f"Interaction Type: Photo")
            print(f"Caption: \"{message.caption or '[No Caption]'}\"")
            # Opt-in: SAVE_IMAGES=1 in .env; photo[-1] is the largest size
            if os.getenv("SAVE_IMAGES") == "1":
                await save_file(message.photo[-1], "images", "image.jpg")
        elif message.voice or message.audio:
            print(f"Interaction Type: Audio")
            # Opt-in: SAVE_AUDIO=1 in .env
            if os.getenv("SAVE_AUDIO") == "1":
                media = message.voice or message.audio
                await save_file(media, "audio", "audio.ogg")
        elif message.sticker:
            print(f"Interaction Type: Sticker")
            print(f"Emoji: {message.sticker.emoji}")
        else:
            print(f"Interaction Type: Other Media/File")
    print("---------------------------------\n")

# Simple reply handlers so the bot responds to the user
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Hi! Everything you send or do here will be printed to my terminal console.")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f"Echo: {update.message.text}")

if __name__ == '__main__':
    load_dotenv()
    app = ApplicationBuilder().token(os.environ["TELEGRAM_TOKEN"]).build()
    
    # 1. This prints ALL interactions to the console (Type filters.ALL catches text, photos, stickers, commands, etc.)
    app.add_handler(MessageHandler(filters.ALL, log_interaction), group=-1)
    
    # 2. These actually handle replying to the user
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    
    print("Bot is running... Go send something to it on Telegram!")
    app.run_polling()
