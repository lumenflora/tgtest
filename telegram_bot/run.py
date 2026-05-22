"""
run.py — entry point
Starts the Flask web server (Mini App) and the Telegram bot together.
"""

import asyncio
import logging
import threading

import database as db
from bot import build_app
from services.scheduler import start_scheduler
from web_server import run_flask

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def main():
    # 1. Init DB
    await db.init_db()
    logger.info("Database initialised.")

    # 2. Start Flask in a background thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logger.info("Flask server started (Mini App).")

    # 3. Build and start Telegram bot
    application = build_app()

    # 4. Start daily post scheduler
    scheduler = start_scheduler(application.bot)

    logger.info("Bot is running. Press Ctrl+C to stop.")

    async with application:
        await application.start()
        await application.updater.start_polling(drop_pending_updates=True)

        # Keep running until Ctrl+C
        try:
            await asyncio.Event().wait()
        except (KeyboardInterrupt, SystemExit):
            pass
        finally:
            scheduler.shutdown()
            await application.updater.stop()
            await application.stop()


if __name__ == "__main__":
    asyncio.run(main())
