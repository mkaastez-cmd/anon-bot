from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import asyncio
import os

# =======================
# 🔧 CONFIGURATION
# =======================
BOT_TOKEN = "7996920244:AAHgItacKJBawOCjo5sTq9RvB6fjz3FLcZ4"  # 👈 Replace this
app = Flask(__name__)

# =======================
# 🤖 Telegram Bot Setup
# =======================
bot_app = ApplicationBuilder().token(BOT_TOKEN).build()

waiting = set()
pairs = {}


# =======================
# 🔹 Commands
# =======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Welcome! Use /find to chat with a random person.")


async def find(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_chat.id
    if user in pairs:
        await update.message.reply_text("You're already chatting! Use /stop to end.")
        return
    if waiting:
        partner = waiting.pop()
        pairs[user] = partner
        pairs[partner] = user
        await context.bot.send_message(partner, "🎉 Connected! Say hi 👋")
        await update.message.reply_text("🎉 Connected! Say hi 👋")
    else:
        waiting.add(user)
        await update.message.reply_text("⌛ Waiting for a partner...")


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_chat.id
    partner = pairs.pop(user, None)
    if partner:
        pairs.pop(partner, None)
        await context.bot.send_message(partner, "❌ Your partner left.")
    if user in waiting:
        waiting.remove(user)
    await update.message.reply_text("Chat ended. Use /find to start again.")


# =======================
# 💬 Forward Messages (text, media, stickers, voice)
# =======================
async def forward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_chat.id
    if user not in pairs:
        return
    partner = pairs[user]
    msg = update.message

    if msg.text:
        await context.bot.send_message(partner, msg.text)
    elif msg.sticker:
        await context.bot.send_sticker(partner, msg.sticker.file_id)
    elif msg.voice:
        await context.bot.send_voice(partner, msg.voice.file_id)
    elif msg.photo:
        await context.bot.send_photo(partner, msg.photo[-1].file_id)
    elif msg.video:
        await context.bot.send_video(partner, msg.video.file_id)


# =======================
# 🧩 Handlers
# =======================
bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CommandHandler("find", find))
bot_app.add_handler(CommandHandler("stop", stop))
bot_app.add_handler(MessageHandler(filters.ALL, forward))


# =======================
# 🌐 Flask Webhook Setup
# =======================
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot_app.bot)
    asyncio.run(bot_app.process_update(update))
    return "ok"


@app.route("/")
def home():
    return "Bot running successfully ✅"


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(bot_app.initialize())
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
