# Telegram Channel Bot + Mini App

A complete Telegram bot that:
- 📸 **Watermarks** any image you send (bottom-right corner)
- 🤖 **AI-generates** channel posts in your style, 1–2 per day
- ✅ **Admin approval** flow before anything gets published
- 🖼️ **AI image generation** for every post (free, no key needed)
- 🖥️ **Mini App** to manage example posts from inside Telegram

---

## Setup (5 steps)

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Create your bot
1. Open Telegram → talk to **@BotFather**
2. `/newbot` → follow prompts → copy the token

### 3. Get free AI keys
- **Gemini** (text): https://aistudio.google.com/app/apikey → create key, it's free
- **Images**: No key needed — uses Pollinations.ai automatically

### 4. Find your Telegram user ID
Talk to **@userinfobot** on Telegram — it shows your numeric ID.

### 5. Configure
```bash
cp .env.example .env
# Edit .env with your values
```

---

## Running locally

```bash
python run.py
```

This starts:
- The Telegram bot (polling for messages)
- The Flask server on port 5000 (Mini App + API)
- The daily scheduler (generates posts at 10:00 and 18:00 UTC)

---

## Mini App setup

The Mini App must be served over **HTTPS** for Telegram to load it.

**For local development** (use ngrok):
```bash
# Install ngrok from ngrok.com, then:
ngrok http 5000
# Copy the https://xxxx.ngrok-free.app URL
# Set it as MINI_APP_URL in your .env
```

**Register the Mini App with BotFather:**
1. Talk to @BotFather → `/newapp`
2. Select your bot
3. Enter the HTTPS URL
4. BotFather gives you the Mini App link

---

## Hosting (24/7)

### Option A — Railway (easiest, free)
1. Push this folder to GitHub
2. Go to railway.app → New Project → Deploy from GitHub
3. Add environment variables (same as .env)
4. Done — Railway gives you an HTTPS URL for the Mini App

### Option B — VPS (Hetzner, DigitalOcean ~€4/mo)
```bash
# On your server:
git clone your-repo && cd telegram_bot
pip install -r requirements.txt
cp .env.example .env && nano .env

# Run with systemd or screen:
screen -S bot
python run.py
# Ctrl+A then D to detach

# For HTTPS on VPS, use Caddy:
# apt install caddy
# In Caddyfile: your.domain { reverse_proxy localhost:5000 }
```

---

## How the workflow works

```
Daily at 10:00 + 18:00 UTC
    │
    ▼
Scheduler reads your example posts from DB
    │
    ▼
Gemini 1.5 Flash writes a new post in your style
    │
    ▼
Pollinations.ai generates a matching image (free)
    │
    ▼
Draft sent to YOU (admin) with ✅ Approve / ❌ Reject / ✏️ Edit buttons
    │
    ▼ (you tap Approve)
Post + image published to your channel
```

---

## Adding example posts

1. Open the Mini App from the bot's /start menu
2. Go to ➕ Add tab
3. Paste 3–10 of your best posts (the more, the better the AI output)

Or via bot command: the admin can also use `/generate` to trigger a draft immediately.

---

## Customising the watermark

**Text watermark** (default):
```
WATERMARK_TEXT=@yourchannel
```

**Logo watermark**:
```
WATERMARK_LOGO=logo.png    # transparent PNG, put in project folder
```

---

## File structure

```
telegram_bot/
├── run.py                   ← entry point (start here)
├── bot.py                   ← all Telegram handlers
├── config.py                ← config / env vars
├── database.py              ← SQLite operations
├── web_server.py            ← Flask (Mini App + REST API)
├── services/
│   ├── ai_service.py        ← Gemini + Pollinations
│   ├── watermark_service.py ← Pillow watermarking
│   └── scheduler.py        ← daily post generation
├── miniapp/
│   └── index.html           ← Telegram Mini App UI
├── requirements.txt
└── .env.example
```

---

## Free AI limits

| Service | What it does | Free limit |
|---|---|---|
| Gemini 1.5 Flash | Post text generation | 1,500 requests/day |
| Pollinations.ai | Image generation | Unlimited (no key) |

Both are more than enough for 1–2 posts per day.
