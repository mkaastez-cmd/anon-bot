import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import nest_asyncio

# Fix event loop issue on servers
nest_asyncio.apply()

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Your Bot Token (replace this with your real token)
BOT_TOKEN = "7996920244:AAHgItacKJBawOCjo5sTq9RvB6fjz3FLcZ4"

# User pairing data
waiting_users = []
active_chats = {}

# Start command
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

# Stop command
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
        await update.message.reply_text("You are not chatting with anyone currently.")

# Skip command (find new partner)
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

# Forward messages between users
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in active_chats:
        partner_id = active_chats[user_id]
        # Forward text
        if update.message.text:
            await context.bot.send_message(chat_id=partner_id, text=update.message.text)
        # Forward photos, stickers, etc.
        elif update.message.sticker:
            await context.bot.send_sticker(chat_id=partner_id, sticker=update.message.sticker.file_id)
        elif update.message.photo:
            await context.bot.send_photo(chat_id=partner_id, photo=update.message.photo[-1].file_id)
        elif update.message.video:
            await context.bot.send_video(chat_id=partner_id, video=update.message.video.file_id)
        elif update.message.voice:
            await context.bot.send_voice(chat_id=partner_id, voice=update.message.voice.file_id)
        elif update.message.document:
            await context.bot.send_document(chat_id=partner_id, document=update.message.document.file_id)
    else:
        await update.message.reply_text("⚠️ You are not chatting right now. Type /start to find a partner.")

# Main function
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("skip", skip))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))

    logger.info("Bot started")
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
    from flask import Flask
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is alive!"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
