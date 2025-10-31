import logging
import nest_asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# --- Apply asyncio patch (needed for mobile/Pydroid) ---
nest_asyncio.apply()

# --- Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Flask app ---
app = Flask(__name__)

# === Replace this with your real Telegram bot token ===
BOT_TOKEN = "7996920244:AAHgItacKJBawOCjo5sTq9RvB6fjz3FLcZ4"

# --- Telegram Bot setup ---
application = ApplicationBuilder().token(BOT_TOKEN).build()

# Store active chat pairs
active_chats = {}

# --- Commands ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text("👋 Welcome to Anonymous Chat!\nType /next to find someone new 🔍")

async def next_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # Try to find a partner
    for partner_id in list(active_chats.keys()):
        if active_chats[partner_id] is None and partner_id != user_id:
            active_chats[user_id] = partner_id
            active_chats[partner_id] = user_id

            await context.bot.send_message(chat_id=user_id, text="✅ Partner found! Start chatting 💬")
            await context.bot.send_message(chat_id=partner_id, text="✅ Partner found! Start chatting 💬")
            return

    active_chats[user_id] = None
    await update.message.reply_text("⏳ Waiting for a partner...")

async def stop_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    partner_id = active_chats.get(user_id)

    if partner_id:
        await context.bot.send_message(chat_id=partner_id, text="❌ Your partner left the chat.")
        active_chats[partner_id] = None
    active_chats[user_id] = None
    await update.message.reply_text("❌ You left the chat.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    partner_id = active_chats.get(user_id)

    if not partner_id:
        await update.message.reply_text("⚠️ You're not chatting with anyone. Type /next to start.")
        return

    # Forward text, media, stickers, voice, etc.
    if update.message.text:
        await context.bot.send_message(chat_id=partner_id, text=update.message.text)
    elif update.message.sticker:
        await context.bot.send_sticker(chat_id=partner_id, sticker=update.message.sticker.file_id)
    elif update.message.photo:
        await context.bot.send_photo(chat_id=partner_id, photo=update.message.photo[-1].file_id)
    elif update.message.video:
        await context.bot.send_video(chat_id=partner_id, video=update.message.video.file_id)
    elif update.message.voice:
        await context.bot.send_voice(chat_id=partner_id, voice=update.message.voice.file_id)
    else:
        await update.message.reply_text("⚠️ Unsupported message type.")

# --- Handlers ---
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("next", next_chat))
application.add_handler(CommandHandler("stop", stop_chat))
application.add_handler(MessageHandler(filters.ALL, handle_message))

# --- Flask route for keep-alive (Render Cron) ---
@app.route('/')
def home():
    return "✅ Bot is running!"

# --- Run both Flask and Telegram app together ---
import threading

def run_flask():
    app.run(host="0.0.0.0", port=10000)

threading.Thread(target=run_flask).start()

if __name__ == '__main__':
    logger.info("🚀 Bot started successfully!")
    application.run_polling()
