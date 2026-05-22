"""
scheduler.py
Runs daily at configured times, generates a post draft via AI,
and sends it to the admin for review.
"""

import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

import database as db
from services.ai_service import generate_post_text, generate_post_image
from config import ADMIN_ID, POST_TIMES

logger = logging.getLogger(__name__)


async def generate_and_send_draft(bot: Bot) -> None:
    """
    Core job: generate a post draft and send to admin for approval.
    """
    logger.info("Scheduler: generating draft post…")

    # 1. Fetch example posts from DB
    examples = await db.get_examples(limit=8)
    if not examples:
        await bot.send_message(
            ADMIN_ID,
            "⚠️ No example posts found.\n\nAdd some via the Mini App first so the AI can learn your style.",
        )
        return

    # 2. Generate text
    post_text = await generate_post_text(examples)

    # 3. Generate image
    image_bytes = await generate_post_image(post_text)

    # 4. Save to DB as pending
    post_id = await db.add_pending_post(post_text)

    # 5. Send draft to admin with approval buttons
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Approve & Post", callback_data=f"approve:{post_id}"),
            InlineKeyboardButton("❌ Reject",          callback_data=f"reject:{post_id}"),
        ],
        [
            InlineKeyboardButton("✏️ Edit text",       callback_data=f"edit:{post_id}"),
        ],
    ])

    caption = (
        f"📝 *New AI Draft — Post #{post_id}*\n\n"
        f"{post_text}\n\n"
        f"_Generated from {len(examples)} example(s)_"
    )

    try:
        if image_bytes:
            await bot.send_photo(
                chat_id=ADMIN_ID,
                photo=image_bytes,
                caption=caption,
                parse_mode="Markdown",
                reply_markup=keyboard,
            )
        else:
            await bot.send_message(
                chat_id=ADMIN_ID,
                text=caption,
                parse_mode="Markdown",
                reply_markup=keyboard,
            )
        logger.info(f"Draft post #{post_id} sent to admin.")
    except Exception as e:
        logger.error(f"Failed to send draft to admin: {e}")


def start_scheduler(bot: Bot) -> AsyncIOScheduler:
    """
    Registers all scheduled jobs and starts the scheduler.
    Returns the scheduler so the caller can stop it on shutdown.
    """
    scheduler = AsyncIOScheduler()

    for time_str in POST_TIMES:
        hour, minute = map(int, time_str.split(":"))
        scheduler.add_job(
            generate_and_send_draft,
            CronTrigger(hour=hour, minute=minute),
            args=[bot],
            id=f"post_{time_str}",
            replace_existing=True,
        )
        logger.info(f"Scheduled daily post at {time_str} UTC")

    scheduler.start()
    return scheduler
