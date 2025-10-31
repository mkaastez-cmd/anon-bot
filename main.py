from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import logging, asyncio, os
from flask import Flask, request

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"

app = Flask(__name__)

# Telegram bot setup
bot_app = ApplicationBuilder().token(BOT_TOKEN).build()

# store chat pairs
waiting = set()
pairs = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Welcome!\nUse /find to connect with a random person!")

async def find(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_chat.id
    if user in pairs:
        await update.message.reply_text("You're already chatting! Use /stop to end.")
        return
    if waiting and user not in waiting:
        partner = waiting.pop()
        pairs[user] = partner
        pairs[partner] = user
        await context.bot.send_message(chat_id=user, text="🎉 Connected! Say hi 👋")
        await context.bot.send_message(chat_id=partner, text="🎉 Connected! Say hi 👋")
    else:
        waiting.add(user)
        await update.message.reply_text("⌛ Waiting for someone to connect...")

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_chat.id
    partner = pairs.pop(user, None)
    if partner:
        pairs.pop(partner, None)
        await context.bot.send_message(chat_id=partner, text="❌ Partner left the chat.")
    if user in waiting:
        waiting.remove(user)
    await update.message.reply_text("Chat ended. Use /find to start again.")

async def forward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_chat.id
    if user in pairs:
        partner = pairs[user]
        msg = update.message
        if msg.text:
            await context.bot.send_message(chat_id=partner, text=msg.text)
        elif msg.sticker:
            await context.bot.send_sticker(chat_id=partner, sticker=msg.sticker.file_id)
        elif msg.voice:
            await context.bot.send_voice(chat_id=partner, voice=msg.voice.file_id)
        elif msg.photo:
            await context.bot.send_photo(chat_id=partner, photo=msg.photo[-1].file_id)
        elif msg.video:
            await context.bot.send_video(chat_id=partner, video=msg.video.file_id)

bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CommandHandler("find", find))
bot_app.add_handler(CommandHandler("stop", stop))
bot_app.add_handler(MessageHandler(filters.ALL, forward))

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot_app.bot)
    asyncio.run(bot_app.process_update(update))
    return "ok"

@app.route("/")
def home():
    return "Bot running"

if __name__ == "__main__":
    import asyncio
    asyncio.get_event_loop().run_until_complete(bot_app.initialize())
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
