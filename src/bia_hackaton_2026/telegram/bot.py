import asyncio
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

from bia_hackaton_2026.notify.telegram_family import add_family, remove_family, send_family_alert
from bia_hackaton_2026.pipeline import handle_message, reset_chat

# Setup clean console printing format
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# httpx logs full request URLs, which contain the bot token. Keep them out of console/log files.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

WELCOME = (
    "Hello, I am Sahayi, your assistant. You can talk to me in English or Malayalam.\n\n"
    "Send me a voice message, a text message or a photo, and tell me how you are or what you need. "
    "I will listen and answer."
)
ALERT_FAILED = (
    "I could not reach your family contact just now. Please call them yourself. "
    "If you need urgent help, call 112 or ask someone nearby."
)
FRIENDLY_ERROR = "Sorry, something went wrong on my side. Please try again in a moment."


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


async def download_bytes(media) -> bytes:
    """Download a Telegram file into memory (no file is written to disk)."""
    return bytes(await (await media.get_file()).download_as_bytearray())


async def respond(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str = "", audio=None, image=None) -> None:
    """Run the Sahayi pipeline (STT -> image check -> agent) off the event loop and reply in the chat."""
    chat_id = update.effective_chat.id
    await context.bot.send_chat_action(chat_id, ChatAction.TYPING)
    try:
        out = await asyncio.to_thread(handle_message, chat_id, text, audio, image)
    except Exception as e:  # never leave the user without an answer
        logging.exception("pipeline failed")
        await update.effective_message.reply_text(FRIENDLY_ERROR)
        return

    await update.effective_message.reply_text(out["reply"] or FRIENDLY_ERROR)

    # Console summary for the team (family alert delivery comes next, so it is only logged for now)
    print(f"[SAHAYI] chat={chat_id} level={out['level']} family_send={out['family_send']} "
          f"lang={out['language'] or '-'} image={out['image_status'] or '-'} {out['seconds']}s"
          + (f" ERROR={out['error']}" if out["error"] else ""))
    if out["transcript"]:
        print(f"[SAHAYI] transcript: {out['transcript']}")
    if out["family_send"] or out["level"] >= 2:
        name = update.effective_user.first_name or "A Sahayi user"
        res = await send_family_alert(context.bot, chat_id, name, out["alert"], out["level"])
        print(f"[SAHAYI] family alert: registered={res['registered']} delivered={res['delivered']} "
              f"failed={res['failed']} skipped={res['skipped'] or '-'}")
        if not res["delivered"]:
            # The agent's reply may have said the family is being informed; correct it if delivery failed.
            await update.effective_message.reply_text(ALERT_FAILED)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Activate the bot for this chat and start a fresh conversation."""
    reset_chat(update.effective_chat.id)
    await update.message.reply_text(WELCOME)


async def family_join(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """A family member sends /family to receive Sahayi alerts in this chat."""
    user = update.effective_user
    add_family(update.effective_chat.id, user.first_name or "family")
    await update.message.reply_text(
        "You are now registered as a family contact. You will get a message here when Sahayi "
        "thinks a member needs attention. Send /stopfamily to stop."
    )


async def family_leave(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    gone = remove_family(update.effective_chat.id)
    await update.message.reply_text("You will no longer get family alerts." if gone else "You were not registered.")


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await respond(update, context, text=update.message.text)


async def on_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    media = update.message.voice or update.message.audio
    data = await download_bytes(media)
    # Telegram voice notes are OGG/Opus; our STT accepts them as is
    await respond(update, context, text=update.message.caption or "", audio=(data, "voice.ogg"))


async def on_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Thank you, I am looking at your photo.")  # image check can take several seconds
    data = await download_bytes(update.message.photo[-1])  # largest size
    await respond(update, context, text=update.message.caption or "", image=(data, "image/jpeg"))


async def on_image_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    doc = update.message.document
    data = await download_bytes(doc)
    await respond(update, context, text=update.message.caption or "", image=(data, doc.mime_type or "image/jpeg"))


if __name__ == '__main__':
    load_dotenv()
    app = ApplicationBuilder().token(os.environ["TELEGRAM_TOKEN"]).build()

    # 1. This prints ALL interactions to the console (Type filters.ALL catches text, photos, stickers, commands, etc.)
    app.add_handler(MessageHandler(filters.ALL, log_interaction), group=-1)

    # 2. These actually handle replying to the user
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("family", family_join))
    app.add_handler(CommandHandler("stopfamily", family_leave))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, on_voice))
    app.add_handler(MessageHandler(filters.PHOTO, on_photo))
    app.add_handler(MessageHandler(filters.Document.IMAGE, on_image_document))

    print("Bot is running... Go send something to it on Telegram!")
    app.run_polling()
