# anon_bot.py
# PASTE your token into BOT_TOKEN below, then Run in Pydroid 3.
# Requires: python-telegram-bot==20.3

import asyncio
import uuid
import logging
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ------------------ CONFIG ------------------
BOT_TOKEN = "7996920244:AAHgItacKJBawOCjo5sTq9RvB6fjz3FLcZ4"  # <-- put your BotFather token here (keep private)
# --------------------------------------------

# Simple in-memory stores (works for testing; for production use Redis/Postgres)
users = {}      # user_id -> {"state": "idle/searching/chatting"}
queue = []      # list of user_ids waiting
sessions = {}   # session_id -> (user1, user2)

# ---------- helpers ----------
def find_partner(uid):
    """Return a waiting partner or None."""
    for partner in queue:
        if partner != uid:
            return partner
    return None

def get_session_of(uid):
    for s_id, pair in sessions.items():
        if uid in pair:
            return s_id, pair
    return None, None

def end_session_for(uid):
    sid, pair = get_session_of(uid)
    if not sid:
        return None, None
    sessions.pop(sid, None)
    u1, u2 = pair
    users.setdefault(u1, {"state":"idle"})
    users.setdefault(u2, {"state":"idle"})
    return u1, u2

def send_chat_buttons():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⏭️ Next", callback_data="next")],
        [InlineKeyboardButton("🚪 Stop", callback_data="stop")],
        [InlineKeyboardButton("⚠️ Report", callback_data="report")]
    ])

# ---------- command handlers ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    users.setdefault(uid, {"state":"idle"})
    await update.message.reply_text(
        "👋 Welcome to Anonymous Chat!\n\n"
        "Commands:\n"
        "/find - find a partner\n"
        "/next - skip to another partner\n"
        "/stop - leave chat\n\n"
        "You stay anonymous. Send text, photos, stickers, voice etc."
    )

async def find(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    users.setdefault(uid, {"state":"idle"})
    s_id, _ = get_session_of(uid)
    if s_id:
        await update.message.reply_text("You are already chatting. Use /next or /stop.")
        return

    if users[uid].get("state") == "searching":
        await update.message.reply_text("You are already in the queue. Wait or use /stop.")
        return

    partner = find_partner(uid)
    if partner:
        # pair them
        queue.remove(partner)
        sid = str(uuid.uuid4())
        sessions[sid] = (uid, partner)
        users[uid]["state"] = "chatting"
        users[partner]["state"] = "chatting"

        kb = send_chat_buttons()
        await context.bot.send_message(chat_id=uid, text="🔗 Connected anonymously. Say hi!", reply_markup=kb)
        await context.bot.send_message(chat_id=partner, text="🔗 Connected anonymously. Say hi!", reply_markup=kb)
    else:
        queue.append(uid)
        users[uid]["state"] = "searching"
        await update.message.reply_text("🔎 Searching for a partner...")

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    u1, u2 = end_session_for(uid)
    if not u1:
        await update.message.reply_text("You are not in a chat.")
        return
    other = u2 if uid == u1 else u1
    await context.bot.send_message(chat_id=other, text="🚪 Your partner left the chat.")
    await update.message.reply_text("✅ You left the chat.")

async def next_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    u1, u2 = end_session_for(uid)
    if u1:
        other = u2 if uid == u1 else u1
        await context.bot.send_message(chat_id=other, text="⚠️ Your partner skipped you.")
        await context.bot.send_message(chat_id=uid, text="🔄 Looking for a new partner...")
    # start finding again
    await find(update, context)

# ---------- callback (inline buttons) ----------
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    if query.data == "next":
        await next_cmd(update, context)
    elif query.data == "stop":
        await stop(update, context)
    elif query.data == "report":
        # simple report flow: end session and notify
        u1, u2 = end_session_for(uid)
        if u1:
            other = u2 if uid == u1 else u1
            await context.bot.send_message(chat_id=other, text="⚠️ You have been reported and removed from the chat.")
        await context.bot.send_message(chat_id=uid, text="Thanks — the chat was ended and moderators will review (stub).")
    else:
        await query.edit_message_text("Unknown action.")

# ---------- message relay (support text, stickers, photos, video, voice, docs) ----------
async def relay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    _, pair = get_session_of(uid)
    if not pair:
        await update.message.reply_text("You are not chatting. Use /find to search.")
        return
    partner = pair[0] if pair[1] == uid else pair[1]

    # Text
    if update.message.text:
        await context.bot.send_message(chat_id=partner, text=update.message.text)

    # Stickers
    elif update.message.sticker:
        await context.bot.send_sticker(chat_id=partner, sticker=update.message.sticker.file_id)

    # Photos
    elif update.message.photo:
        photo = update.message.photo[-1]  # highest quality
        await context.bot.send_photo(chat_id=partner, photo=photo.file_id, caption=update.message.caption or "")

    # Video
    elif update.message.video:
        await context.bot.send_video(chat_id=partner, video=update.message.video.file_id, caption=update.message.caption or "")

    # Voice (voice note)
    elif update.message.voice:
        await context.bot.send_voice(chat_id=partner, voice=update.message.voice.file_id)

    # Audio (voice file / music)
    elif update.message.audio:
        await context.bot.send_audio(chat_id=partner, audio=update.message.audio.file_id, caption=update.message.caption or "")

    # Document / file
    elif update.message.document:
        await context.bot.send_document(chat_id=partner, document=update.message.document.file_id, caption=update.message.caption or "")

    else:
        # fall back: try copying message (Telegram new method)
        try:
            await context.bot.copy_message(chat_id=partner, from_chat_id=uid, message_id=update.message.message_id)
        except Exception:
            await update.message.reply_text("This message type is not supported yet.")

# ---------- main ----------
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("find", find))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("next", next_cmd))
    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.ALL & (~filters.COMMAND), relay))
    logger.info("Bot started")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
