import os
from dotenv import load_dotenv

load_dotenv()

# ── Bot ───────────────────────────────────────────────────────────────────────
BOT_TOKEN      = os.getenv("BOT_TOKEN", "")
ADMIN_ID       = int(os.getenv("ADMIN_ID", "0"))       # your Telegram user ID
CHANNEL_ID     = os.getenv("CHANNEL_ID", "@yourchannel")  # e.g. @mychannel or -100123...

# ── AI ────────────────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")       # free at aistudio.google.com

# ── Mini App ──────────────────────────────────────────────────────────────────
MINI_APP_URL   = os.getenv("MINI_APP_URL", "http://localhost:5000")  # must be HTTPS in prod
FLASK_PORT     = int(os.getenv("FLASK_PORT", "5000"))

# ── Watermark ─────────────────────────────────────────────────────────────────
WATERMARK_TEXT = os.getenv("WATERMARK_TEXT", "@yourchannel")
WATERMARK_LOGO = os.getenv("WATERMARK_LOGO", "")       # optional: path to a .png logo

# ── Post scheduling ───────────────────────────────────────────────────────────
POST_TIMES     = ["10:00", "18:00"]                    # times to generate+send drafts (UTC)

# ── DB ────────────────────────────────────────────────────────────────────────
DB_PATH        = "bot.db"
