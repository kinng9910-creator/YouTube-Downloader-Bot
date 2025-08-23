import logging
import requests
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, ContextTypes, MessageHandler, filters,
    CallbackQueryHandler, CommandHandler
)

# --- CONFIG ---
TOKEN = "8471538027:AAEAhqZFfvVXJfD52fOcWC5wNWO_LqpjuD0"
CHANNEL_ID = -1002876982200
CHANNEL_LINK = "https://t.me/ZALIM_MODZ_OFFICIAL"

MP3_API = "https://ytdownloader.anshppt19.workers.dev/?url="
MP4_API = "https://youtube.anshppt19.workers.dev/anshapi"

# --- LOGGING ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# --- CHECK MEMBER ---
async def is_user_member(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

# --- START ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if await is_user_member(user_id, context):
        await update.message.reply_text("🎵 Send me a YouTube video link to download MP3 or MP4.")
    else:
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔗 Join Channel", url=CHANNEL_LINK)],
            [InlineKeyboardButton("✅ I Joined", callback_data="check_join")]
        ])
        await update.message.reply_text("🚫 You must join our channel to use this bot:", reply_markup=buttons)

# --- BUTTON HANDLER ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "check_join":
        if await is_user_member(user_id, context):
            await query.edit_message_text("✅ Thank you for joining!\nNow send me a YouTube video link to download.")
        else:
            buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔗 Join Channel", url=CHANNEL_LINK)],
                [InlineKeyboardButton("✅ I Joined", callback_data="check_join")]
            ])
            await query.edit_message_text(
                "❌ You're still not a member.\nPlease join the channel and then click 'I Joined'.",
                reply_markup=buttons
            )
        return

    # MP3 or MP4 Action
    action, url = query.data.split("|", 1)

    wait_msg = await context.bot.send_message(
        chat_id=query.message.chat_id,
        text="⏳ Please wait while we prepare your file..."
    )

    await asyncio.sleep(1)

    try:
        if action == "mp3":
            # ✅ Direct Audio system
            res = requests.get(MP3_API + url).json()
            if res.get("status") == "success":
                audio_url = res["download_url"]
                title = res["title"]

                await context.bot.delete_message(
                    chat_id=query.message.chat_id,
                    message_id=wait_msg.message_id
                )

                await context.bot.send_audio(
                    chat_id=query.message.chat_id,
                    audio=audio_url,
                    title=title,
                    caption=f"🎧 {title}"
                )
            else:
                await query.edit_message_text("❌ Failed to fetch MP3.")

        elif action == "mp4":
            # 🔗 Old Link-based system (keep same as before)
            params = {"url": url, "format": "mp4hd"}
            response = requests.get(MP4_API, params=params)
            data = response.json()

            if data.get("success"):
                video_url = data["data"]["url_mp4_youtube"]
                video_name = data["data"]["name_mp4"]

                # shorten link
                short_api = f"http://tinyurl.com/api-create.php?url={video_url}"
                short_link = requests.get(short_api).text

                await context.bot.delete_message(
                    chat_id=query.message.chat_id,
                    message_id=wait_msg.message_id
                )

                button = InlineKeyboardMarkup([
                    [InlineKeyboardButton("📥 Download Video", url=short_link)]
                ])
                await query.edit_message_text(f"🎬 {video_name}", reply_markup=button)
            else:
                await query.edit_message_text("❌ Failed to fetch MP4.")
    except Exception as e:
        await query.edit_message_text(f"❌ Error: {str(e)}")

# --- HANDLE MESSAGE ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await is_user_member(user_id, context):
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔗 Join Channel", url=CHANNEL_LINK)],
            [InlineKeyboardButton("✅ I Joined", callback_data="check_join")]
        ])
        await update.message.reply_text("🚫 You must join our channel to use this bot:", reply_markup=buttons)
        return

    url = update.message.text.strip()
    if "youtube.com/watch" in url or "youtu.be/" in url:
        keyboard = [
            [
                InlineKeyboardButton("🎧 MP3 (Audio)", callback_data=f"mp3|{url}"),
                InlineKeyboardButton("🎬 MP4 (Video)", callback_data=f"mp4|{url}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("👇 Choose format to download:", reply_markup=reply_markup)

# --- MAIN ---
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("🚀 Bot is running...")
    app.run_polling()
