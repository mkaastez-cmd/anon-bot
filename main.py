import os
import logging
import nest_asyncio
import asyncio
from threading import Thread
from flask import Flask
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# Fix loop issues
nest_asyncio.apply()

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask App (for Render health check)
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Bot is alive and running on Render!"

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

# ------------------------
# Telegram Bot Definition
# ------------------------
BOT_TOKEN = "7996920244:AAHgItacKJBawOCjo5sTq9RvB6fjz3FLcZ4"

waiting_users = []
active_chats = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in active_chats:
        await update.message.reply_text("You are already chatting. Type /stop to end the chat.")
        return
    if user_id in waiting_users:
        await update.message.reply_text("You are already in queue. Please wait for a partner.")
        return
    if waiting_users:
        partner_id = waiting_users.pop(0)
        active_chats[user_id] = partner_id
        active_chats[partner_id] = user_id
        await context.bot.send_message(chat_id=user_id, text="🎯 Partner found! Say hi 👋")
        await context.bot.send_message(chat_id=partner_id, text="🎯 Partner found! Say hi 👋")
    else:
        waiting_users.append(user_id)
        await update.message.reply_text("⏳ Waiting for a partner... Please wait.")

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in active_chats:
        partner_id = active_chats[user_id]
        await context.bot.send_message(chat_id=partner_id, text="❌ Your partner left the chat.")
        await update.message.reply_text("✅ You left the chat.")
        del active_chats[partner_id]
        del active_chats[user_id]
    elif user_id in waiting_users:
        waiting_users.remove(user_id)
        await update.message.reply_text("❌ You left the waiting queue.")
    else:
        await update.message.reply_text("You're not chatting with anyone right now.")

async def skip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in active_chats:
        partner_id = active_chats[user_id]
        await context.bot.send_message(chat_id=partner_id, text="⚠️ Your partner skipped you.")
        del active_chats[partner_id]
        del active_chats[user_id]
        waiting_users.append(user_id)
        await update.message.reply_text("🔄 Searching for a new partner...")
        await start(update, context)
    else:
        await update.message.reply_text("You're not in a chat. Type /start to begin.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in active_chats:
        partner_id = active_chats[user_id]
        msg = update.message
        if msg.text:
            await context.bot.send_message(chat_id=partner_id, text=msg.text)
        elif msg.sticker:
            await context.bot.send_sticker(chat_id=partner_id, sticker=msg.sticker.file_id)
        elif msg.photo:
            await context.bot.send_photo(chat_id=partner_id, photo=msg.photo[-1].file_id)
        elif msg.video:
            await context.bot.send_video(chat_id=partner_id, video=msg.video.file_id)
        elif msg.voice:
            await context.bot.send_voice(chat_id=partner_id, voice=msg.voice.file_id)
        elif msg.document:
            await context.bot.send_document(chat_id=partner_id, document=msg.document.file_id)
    else:
        await update.message.reply_text("⚠️ You are not chatting right now. Type /start to find a partner.")

async def bot_main():
    bot_app = ApplicationBuilder().token(BOT_TOKEN).build()
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(CommandHandler("stop", stop))
    bot_app.add_handler(CommandHandler("skip", skip))
    bot_app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
    logger.info("🤖 Bot started and polling...")
    await bot_app.run_polling()

# Run both Flask and Bot in parallel
def run_bot():
    asyncio.run(bot_main())

if __name__ == "__main__":
    Thread(target=run_flask).start()
    run_bot()
