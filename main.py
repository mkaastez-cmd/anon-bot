# main.py
import os
import logging
import asyncio
from threading import Thread
from flask import Flask, Response
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ======= Minimal logging (avoid huge logs) =======
logging.getLogger().setLevel(logging.ERROR)
logging.getLogger("telegram").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.ERROR)

# ======= Flask health endpoint (for cron / keepalive) =======
flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    # extremely small response so cron won't complain
    return Response("OK", mimetype="text/plain")

# ======= Bot data stores =======
waiting_users = []      # FIFO queue of waiting user_ids
active_chats = {}       # user_id -> partner_id

# ======= Bot token (REPLACE this with your token or use env in Render) =======
BOT_TOKEN = os.environ.get("7996920244:AAHgItacKJBawOCjo5sTq9RvB6fjz3FLcZ4") or "YOUR_BOT_TOKEN_HERE"

# ======= Helper utilities =======
def pair_users(u1, u2):
    active_chats[u1] = u2
    active_chats[u2] = u1

def unpair_user(u):
    partner = active_chats.pop(u, None)
    if partner:
        active_chats.pop(partner, None)
    return partner

# ======= Command handlers =======
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "👋 *Welcome to Anonymous Chat!* \n\n"
        "Commands:\n"
        "/find — Find a random partner 🔎\n"
        "/next — Skip current partner ⏭️\n"
        "/stop — End chat 🚪\n\n"
        "You can send text, photos, stickers, voice, video, or files."
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def find_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user.id

    # already chatting?
    if user in active_chats:
        await update.message.reply_text("❗ You are already chatting. Use /next to skip or /stop to end.")
        return

    # already waiting?
    if user in waiting_users:
        await update.message.reply_text("➡️ You're already in the queue. Please wait...")
        return

    # match with first waiting user if any
    if waiting_users:
        partner = waiting_users.pop(0)
        if partner == user:
            # shouldn't happen but guard
            waiting_users.append(user)
            await update.message.reply_text("🔎 Waiting for a partner...")
            return
        pair_users(user, partner)
        await context.bot.send_message(chat_id=partner, text="🎯 Partner found! Say hi 👋")
        await update.message.reply_text("🎯 Partner found! Say hi 👋")
    else:
        waiting_users.append(user)
        await update.message.reply_text("🔎 Searching for a partner... Please wait ⏳")

async def next_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user.id

    if user not in active_chats:
        await update.message.reply_text("⚠ You're not chatting. Use /find to start.")
        return

    partner = unpair_user(user)
    if partner:
        await context.bot.send_message(chat_id=partner, text="⚠️ Your partner skipped you. Use /find to get a new one.")
    await update.message.reply_text("🔄 Looking for a new partner...")
    # put user back into queue and attempt immediate match
    if waiting_users:
        new_partner = waiting_users.pop(0)
        if new_partner != user:
            pair_users(user, new_partner)
            await context.bot.send_message(chat_id=new_partner, text="🎯 Partner found! Say hi 👋")
            await update.message.reply_text("🎯 Partner found! Say hi 👋")
            return
        else:
            # unexpected, put back
            waiting_users.append(user)
            await update.message.reply_text("⏳ Waiting for a partner...")
            return
    else:
        waiting_users.append(user)
        await update.message.reply_text("⏳ Waiting for a partner...")

async def stop_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user.id
    if user in waiting_users:
        waiting_users.remove(user)
        await update.message.reply_text("🛑 You left the waiting queue.")
        return

    if user in active_chats:
        partner = unpair_user(user)
        if partner:
            await context.bot.send_message(chat_id=partner, text="❌ Your partner ended the chat.")
        await update.message.reply_text("✅ You ended the chat.")
    else:
        await update.message.reply_text("ℹ You are not in a chat right now.")

# ======= Message forwarding (text, stickers, photos, video, voice, audio, docs) =======
async def relay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user.id
    if user not in active_chats:
        await update.message.reply_text("⚠ You are not chatting. Use /find to start.")
        return

    partner = active_chats[user]
    msg = update.message

    try:
        if msg.text:
            await context.bot.send_message(chat_id=partner, text=msg.text)
        elif msg.sticker:
            await context.bot.send_sticker(chat_id=partner, sticker=msg.sticker.file_id)
        elif msg.photo:
            await context.bot.send_photo(chat_id=partner, photo=msg.photo[-1].file_id, caption=msg.caption or "")
        elif msg.video:
            await context.bot.send_video(chat_id=partner, video=msg.video.file_id, caption=msg.caption or "")
        elif msg.voice:
            await context.bot.send_voice(chat_id=partner, voice=msg.voice.file_id)
        elif msg.audio:
            await context.bot.send_audio(chat_id=partner, audio=msg.audio.file_id, caption=msg.caption or "")
        elif msg.document:
            await context.bot.send_document(chat_id=partner, document=msg.document.file_id, caption=msg.caption or "")
        else:
            # fallback: try copy_message if available
            try:
                await context.bot.copy_message(chat_id=partner, from_chat_id=user, message_id=msg.message_id)
            except Exception:
                await update.message.reply_text("⚠ Unsupported message type.")
    except Exception:
        # If sending to partner fails, unpair and inform sender
        unpair_user(user)
        await update.message.reply_text("⚠️ Failed to deliver. Chat ended.")

# ======= Run bot (async) =======
async def run_bot():
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start_cmd))
    application.add_handler(CommandHandler("find", find_cmd))
    application.add_handler(CommandHandler("next", next_cmd))
    application.add_handler(CommandHandler("stop", stop_cmd))
    # relay everything except commands
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, relay))

    # start polling (async)
    await application.run_polling()

# ======= Entry point for Render =======
if __name__ == "__main__":
    # start bot in background thread
    def _start_bot_thread():
        asyncio.run(run_bot())

    t = Thread(target=_start_bot_thread, daemon=True)
    t.start()

    # run flask on port Render gives (default 10000)
    port = int(os.environ.get("PORT", 10000))
    # ensure no noisy logging from Flask
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    flask_app.run(host="0.0.0.0", port=port)
