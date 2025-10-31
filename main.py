import logging
import os
from threading import Thread
from flask import Flask
import nest_asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# Fix event loop issue
nest_asyncio.apply()

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Your Bot Token (replace it with your real one)
BOT_TOKEN = "7996920244:AAHgItacKJBawOCjo5sTq9RvB6fjz3FLcZ4"

# Flask app to keep Render alive
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "✅ Bot is alive and running on Render!"

def run_flask():
    port = int(os.environ.get("PORT", 5000))  # Render auto-assigns a port
    flask_app.run(host='0.0.0.0', port=port)

Thread(target=run_flask).start()

# User pairing data
waiting_users = []
active_chats = {}

# Commands
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in active_chats:
        await update.message.reply_text("💬 You're already chatting. Type /stop to end it.")
        return

    if user_id in waiting_users:
        await update.message.reply_text("⏳ You're already in queue, please wait...")
        return

    if waiting_users:
        partner_id = waiting_users.pop(0)
        active_chats[user_id] = partner_id
        active_chats[partner_id] = user_id
        await context.bot.send_message(chat_id=user_id, text="🎯 Partner found! Say hi 👋")
        await context.bot.send_message(chat_id=partner_id, text="🎯 Partner found! Say hi 👋")
    else:
        waiting_users.append(user_id)
        await update.message.reply_text("🔍 Waiting for a partner... Please wait.")

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in active_chats:
        partner_id = active_chats[user_id]
        await context.bot.send_message(chat_id=partner_id, text="❌ Your partner left the chat.")
        await context.bot.send_message(chat_id=user_id, text="✅ You left the chat.")
        del active_chats[partner_id]
        del active_chats[user_id]
    elif user_id in waiting_users:
        waiting_users.remove(user_id)
        await update.message.reply_text("❌ You left the waiting queue.")
    else:
        await update.message.reply_text("⚠️ You are not chatting with anyone currently.")

async def skip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in active_chats:
        partner_id = active_chats[user_id]
        await context.bot.send_message(chat_id=partner_id, text="⚠️ Your partner skipped to someone else.")
        del active_chats[partner_id]
        del active_chats[user_id]
        waiting_users.append(user_id)
        await update.message.reply_text("🔄 Searching for a new partner...")
        await start(update, context)
    else:
        await update.message.reply_text("You're not in a chat. Type /start to begin.")

# Forward messages
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
        await update.message.reply_text("⚠️ You're not chatting right now. Type /start to find a partner.")

# Main function
async def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stop", stop))
    application.add_handler(CommandHandler("skip", skip))
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))

    logger.info("🚀 Bot started successfully!")
    await application.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())    
