import os
import time
import asyncio
import logging
import uuid
from fastapi import FastAPI
from fastapi.responses import FileResponse, PlainTextResponse
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from pytube import YouTube

# --- CONFIG ---
BOT_TOKEN = os.getenv("8471538027:AAEAhqZFfvVXJfD52fOcWC5wNWO_LqpjuD0")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "-1002876982200"))
CHANNEL_LINK = os.getenv("CHANNEL_LINK", "https://t.me/ZALIM_MODZ_OFFICIAL")
ADMIN_ID = int(os.getenv("ADMIN_ID", "7747120004"))
FILE_LIMIT = int(os.getenv("TG_FILE_LIMIT_BYTES", 40 * 1024 * 1024))  # 40MB
TEMP_TTL = int(os.getenv("TEMP_TTL_SECONDS", 1800))  # 30 minutes

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# --- LOGGING ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- FASTAPI APP ---
app = FastAPI()
temp_links = {}  # {file_id: {"path": path, "expire": ts}}

@app.get("/")
async def home():
    return {"status": "running"}

@app.get("/download/{file_id}")
async def download(file_id: str):
    if file_id not in temp_links:
        return PlainTextResponse("❌ Link expired.", status_code=404)

    file_info = temp_links[file_id]
    if time.time() > file_info["expire"]:
        try:
            os.remove(file_info["path"])
        except:
            pass
        del temp_links[file_id]
        return PlainTextResponse("❌ Link expired.", status_code=410)

    path = file_info["path"]
    del temp_links[file_id]
    return FileResponse(path, filename=os.path.basename(path), media_type="application/octet-stream")

# --- TELEGRAM BOT ---
async def is_user_member(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if await is_user_member(user_id, context):
        await update.message.reply_text("🎵 Send me a YouTube video link.")
    else:
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔗 Join Channel", url=CHANNEL_LINK)],
            [InlineKeyboardButton("✅ I Joined", callback_data="check_join")]
        ])
        await update.message.reply_text("🚫 You must join our channel:", reply_markup=buttons)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "check_join":
        if await is_user_member(user_id, context):
            await query.edit_message_text("✅ Thank you! Now send me a YouTube link.")
        else:
            buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔗 Join Channel", url=CHANNEL_LINK)],
                [InlineKeyboardButton("✅ I Joined", callback_data="check_join")]
            ])
            await query.edit_message_text("❌ You're still not a member.", reply_markup=buttons)
        return

    action, url = query.data.split("|", 1)
    wait_msg = await context.bot.send_message(chat_id=query.message.chat_id, text="⏳ Downloading...")

    try:
        yt = YouTube(url)
        title = yt.title
        if action == "mp3":
            stream = yt.streams.filter(only_audio=True).first()
            file_path = stream.download(output_path=DOWNLOAD_DIR, filename=f"{uuid.uuid4()}.mp3")

            await context.bot.delete_message(chat_id=query.message.chat_id, message_id=wait_msg.message_id)
            await context.bot.send_audio(chat_id=query.message.chat_id, audio=open(file_path, "rb"), title=title)
            os.remove(file_path)

        elif action == "mp4":
            stream = yt.streams.get_highest_resolution()
            file_path = stream.download(output_path=DOWNLOAD_DIR, filename=f"{uuid.uuid4()}.mp4")

            if os.path.getsize(file_path) <= FILE_LIMIT:
                await context.bot.delete_message(chat_id=query.message.chat_id, message_id=wait_msg.message_id)
                await context.bot.send_video(chat_id=query.message.chat_id, video=open(file_path, "rb"), caption=title)
                os.remove(file_path)
            else:
                file_id = str(uuid.uuid4())
                temp_links[file_id] = {"path": file_path, "expire": time.time() + TEMP_TTL}
                public_url = os.getenv("PUBLIC_BASE_URL")
                temp_url = f"{public_url}/download/{file_id}"

                button = InlineKeyboardMarkup([[InlineKeyboardButton("📥 Download Video (Temporary)", url=temp_url)]])
                await context.bot.delete_message(chat_id=query.message.chat_id, message_id=wait_msg.message_id)
                await query.edit_message_text(f"⚠️ Video too large for Telegram.\n🎬 {title}", reply_markup=button)

    except Exception as e:
        await context.bot.edit_message_text(chat_id=query.message.chat_id, message_id=wait_msg.message_id, text=f"❌ Error: {e}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await is_user_member(user_id, context):
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔗 Join Channel", url=CHANNEL_LINK)],
            [InlineKeyboardButton("✅ I Joined", callback_data="check_join")]
        ])
        await update.message.reply_text("🚫 You must join our channel:", reply_markup=buttons)
        return

    url = update.message.text.strip()
    if "youtube.com/watch" in url or "youtu.be/" in url:
        keyboard = [[
            InlineKeyboardButton("🎧 MP3 (Audio)", callback_data=f"mp3|{url}"),
            InlineKeyboardButton("🎬 MP4 (Video)", callback_data=f"mp4|{url}")
        ]]
        await update.message.reply_text("👇 Choose format:", reply_markup=InlineKeyboardMarkup(keyboard))

# --- STARTUP ---
def run():
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_handler))

    loop = asyncio.get_event_loop()
    loop.create_task(application.initialize())
    loop.create_task(application.start())
    loop.create_task(application.updater.start_polling())
    return app

app = run()
