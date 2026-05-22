"""
bot.py — main Telegram bot
Handles:
  - /start, /help
  - Photo → watermark
  - Admin approval flow (inline keyboard callbacks)
  - Admin commands: /generate, /pending, /examples
  - Mini App web_app_data callbacks
"""

import logging

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
    WebAppInfo,
)
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import database as db
from config import (
    ADMIN_ID,
    BOT_TOKEN,
    CHANNEL_ID,
    MINI_APP_URL,
)
from services.ai_service import generate_post_text, generate_post_image
from services.scheduler import start_scheduler
from services.watermark_service import apply_watermark

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# ── /start ────────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    is_admin = user.id == ADMIN_ID

    text = (
        f"👋 Hello, {user.first_name}!\n\n"
        "📸 *Watermark tool:* Send me any photo and I'll add a watermark to the bottom-right corner.\n\n"
    )

    buttons = []

    if is_admin:
        text += (
            "🛠 *Admin tools:*\n"
            "  /generate — create a post draft now\n"
            "  /pending — show posts awaiting approval\n"
            "  /examples — list stored example posts\n\n"
        )
        buttons.append([
            InlineKeyboardButton(
                "🖥 Open Mini App",
                web_app=WebAppInfo(url=MINI_APP_URL),
            )
        ])

    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons) if buttons else None,
    )


# ── /help ─────────────────────────────────────────────────────────────────────

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "📖 *Commands*\n\n"
        "/start — welcome & quick guide\n"
        "/help — this message\n\n"
        "📸 Send any photo to get a watermarked version back.",
        parse_mode="Markdown",
    )


# ── Photo → watermark ─────────────────────────────────────────────────────────

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = await update.message.reply_text("⏳ Adding watermark…")

    photo_file = await update.message.photo[-1].get_file()
    image_bytes = await photo_file.download_as_bytearray()

    try:
        watermarked = apply_watermark(bytes(image_bytes))
    except Exception as e:
        await msg.edit_text(f"❌ Watermark failed: {e}")
        return

    await update.message.reply_photo(
        photo=watermarked,
        caption="✅ Here's your watermarked image!",
    )
    await msg.delete()


# ── /generate (admin only) ────────────────────────────────────────────────────

async def cmd_generate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_ID:
        return

    msg = await update.message.reply_text("🤖 Generating post draft…")

    examples = await db.get_examples(limit=8)
    if not examples:
        await msg.edit_text(
            "⚠️ No examples yet.\nAdd example posts in the Mini App first."
        )
        return

    post_text  = await generate_post_text(examples)
    image_bytes = await generate_post_image(post_text)
    post_id    = await db.add_pending_post(post_text)

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Approve & Post", callback_data=f"approve:{post_id}"),
            InlineKeyboardButton("❌ Reject",          callback_data=f"reject:{post_id}"),
        ],
        [InlineKeyboardButton("✏️ Edit text", callback_data=f"edit:{post_id}")],
    ])

    caption = (
        f"📝 *Draft #{post_id}*\n\n{post_text}\n\n"
        f"_Based on {len(examples)} example(s)_"
    )

    await msg.delete()

    if image_bytes:
        await update.message.reply_photo(
            photo=image_bytes,
            caption=caption,
            parse_mode="Markdown",
            reply_markup=keyboard,
        )
    else:
        await update.message.reply_text(
            caption, parse_mode="Markdown", reply_markup=keyboard
        )


# ── /pending (admin only) ─────────────────────────────────────────────────────

async def cmd_pending(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_ID:
        return

    posts = await db.get_all_pending()
    if not posts:
        await update.message.reply_text("✅ No posts pending approval.")
        return

    for post in posts:
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Approve", callback_data=f"approve:{post['id']}"),
                InlineKeyboardButton("❌ Reject",  callback_data=f"reject:{post['id']}"),
            ],
        ])
        await update.message.reply_text(
            f"*Draft #{post['id']}*\n\n{post['text']}",
            parse_mode="Markdown",
            reply_markup=keyboard,
        )


# ── /examples (admin only) ────────────────────────────────────────────────────

async def cmd_examples(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_ID:
        return

    examples = await db.get_examples(limit=5)
    if not examples:
        await update.message.reply_text(
            "No examples stored yet. Use the Mini App to add them."
        )
        return

    text = f"📚 *Stored examples ({len(examples)}):*\n\n"
    for ex in examples:
        preview = ex["text"][:120] + ("…" if len(ex["text"]) > 120 else "")
        text += f"*#{ex['id']}* — {preview}\n\n"

    await update.message.reply_text(text, parse_mode="Markdown")


# ── Approval callbacks ────────────────────────────────────────────────────────

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await query.answer("⛔ Admin only.", show_alert=True)
        return

    action, post_id_str = query.data.split(":", 1)
    post_id = int(post_id_str)
    post    = await db.get_pending_post(post_id)

    if not post:
        await query.edit_message_text("⚠️ Post not found (already processed?).")
        return

    if action == "approve":
        await _publish_post(context.bot, post)
        await db.update_post_status(post_id, "approved")
        await query.edit_message_caption(
            caption=f"✅ *Post #{post_id} approved and published!*",
            parse_mode="Markdown",
        ) if query.message.photo else await query.edit_message_text(
            f"✅ *Post #{post_id} approved and published!*",
            parse_mode="Markdown",
        )

    elif action == "reject":
        await db.update_post_status(post_id, "rejected")
        await query.edit_message_caption(
            caption=f"❌ *Post #{post_id} rejected.*",
            parse_mode="Markdown",
        ) if query.message.photo else await query.edit_message_text(
            f"❌ *Post #{post_id} rejected.*",
            parse_mode="Markdown",
        )

    elif action == "edit":
        context.user_data["editing_post_id"] = post_id
        await query.message.reply_text(
            f"✏️ Send me the new text for post #{post_id}:"
        )


async def handle_edit_reply(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Receives edited text for a pending post."""
    if update.effective_user.id != ADMIN_ID:
        return
    post_id = context.user_data.get("editing_post_id")
    if not post_id:
        return

    new_text = update.message.text
    async with __import__("aiosqlite").connect(__import__("config").DB_PATH) as db_conn:
        await db_conn.execute(
            "UPDATE pending_posts SET text = ? WHERE id = ?", (new_text, post_id)
        )
        await db_conn.commit()

    context.user_data.pop("editing_post_id", None)

    post    = await db.get_pending_post(post_id)
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Approve & Post", callback_data=f"approve:{post_id}"),
            InlineKeyboardButton("❌ Reject",          callback_data=f"reject:{post_id}"),
        ],
    ])
    await update.message.reply_text(
        f"✅ Text updated! Here's the revised post:\n\n{new_text}",
        reply_markup=keyboard,
    )


# ── Channel publishing ────────────────────────────────────────────────────────

async def _publish_post(bot, post: dict) -> None:
    if post.get("image_url"):
        await bot.send_photo(
            chat_id=CHANNEL_ID,
            photo=post["image_url"],
            caption=post["text"],
        )
    else:
        await bot.send_message(chat_id=CHANNEL_ID, text=post["text"])
    logger.info(f"Published post #{post['id']} to {CHANNEL_ID}")


# ── Mini App data handler ─────────────────────────────────────────────────────

async def handle_web_app_data(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Receives data sent from the Mini App."""
    import json
    data = json.loads(update.message.web_app_data.data)
    action = data.get("action")

    if action == "add_example":
        ex_id = await db.add_example(data["text"], data.get("image_url"))
        await update.message.reply_text(f"✅ Example #{ex_id} saved!")

    elif action == "delete_example":
        await db.delete_example(int(data["id"]))
        await update.message.reply_text("🗑️ Example deleted.")


# ── App setup ─────────────────────────────────────────────────────────────────

def build_app():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start",     cmd_start))
    app.add_handler(CommandHandler("help",      cmd_help))
    app.add_handler(CommandHandler("generate",  cmd_generate))
    app.add_handler(CommandHandler("pending",   cmd_pending))
    app.add_handler(CommandHandler("examples",  cmd_examples))

    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_web_app_data))

    # Catch edited text when admin is editing a post
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND & filters.User(ADMIN_ID),
            handle_edit_reply,
        )
    )

    return app
