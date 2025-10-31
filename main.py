import os
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# === PUT YOUR TOKEN HERE ===
BOT_TOKEN = "7996920244:AAHgItacKJBawOCjo5sTq9RvB6fjz3FLcZ4"

# Flask app (for Render)
app = Flask(__name__)

# Telegram bot setup
application = Application.builder().token(BOT_TOKEN).build()

# === Matching system ===
waiting_users = []
active_chats = {}

# === Commands ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Welcome to Anonymous Chat!\nSend /find to connect with someone.")

async def find(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id
    if user_id in active_chats:
        await update.message.reply_text("You're already chatting. Send /stop to end the chat first.")
        return
    if waiting_users and waiting_users[0] != user_id:
        partner_id = waiting_users.pop(0)
        active_chats[user_id] = partner_id
        active_chats[partner_id] = user_id
        await context.bot.send_message(partner_id, "🔗 Connected! Say hi 👋")
        await update.message.reply_text("🔗 Connected! Say hi 👋")
    else:
        if user_id not in waiting_users:
            waiting_users.append(user_id)
            await update.message.reply_text("⌛ Waiting for a partner...")

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id
    if user_id in active_chats:
        partner_id = active_chats[user_id]
        await context.bot.send_message(partner_id, "❌ Your partner left the chat.")
        del active_chats[partner_id]
        del active_chats[user_id]
        await update.message.reply_text("❌ Chat ended. Send /find to meet someone new.")
    elif user_id in waiting_users:
        waiting_users.remove(user_id)
        await update.message.reply_text("❌ You left the waiting list.")
    else:
        await update.message.reply_text("You are not in a chat currently.")

async def next_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await stop(update, context)
    await find(update, context)

# === Forward all messages ===
async def forward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id
    if user_id not in active_chats:
        await update.message.reply_text("You're not chatting with anyone. Send /find to connect.")
        return
    partner_id = active_chats[user_id]
    msg = update.message
    if msg.text:
        await context.bot.send_message(partner_id, msg.text)
    elif msg.sticker:
        await context.bot.send_sticker(partner_id, msg.sticker.file_id)
    elif msg.voice:
        await context.bot.send_voice(partner_id, msg.voice.file_id)
    elif msg.photo:
        await context.bot.send_photo(partner_id, msg.photo[-1].file_id)
    elif msg.video:
        await context.bot.send_video(partner_id, msg.video.file_id)

# === Handlers ===
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("find", find))
application.add_handler(CommandHandler("stop", stop))
application.add_handler(CommandHandler("next", next_cmd))
application.add_handler(MessageHandler(filters.ALL, forward))

# === Flask route for Render webhook ===
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
async def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    await application.process_update(update)
    return "ok"

@app.route("/")
def home():
    return "Bot is live."

# === Run the bot correctly ===
async def run_bot():
    print("Bot started")
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    await asyncio.Event().wait()

if __name__ == "__main__":
    # Run Flask normally on Render (port required)
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
