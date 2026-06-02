# 🛠️ Setup Guide — Telegram Pro Automation Bot

---

## Step 1 — Get Your Telegram API Credentials

1. Go to [https://my.telegram.org](https://my.telegram.org)
2. Log in with your Telegram account
3. Click **API development tools**
4. Create a new app (name/description don't matter)
5. Copy your **API ID** and **API Hash** — you'll need these when logging in via the bot

---

## Step 2 — Create a Telegram Bot

1. Open Telegram and message [@BotFather](https://t.me/BotFather)
2. Send `/newbot`
3. Follow the steps — give it a name and username
4. Copy the **Bot Token** (looks like `123456:ABC-DEF...`)

---

## Step 3 — Configure Environment

Create a `.env` file in the project root:

```env
BOT_TOKEN=your_bot_token_here
ADMIN_IDS=your_telegram_user_id_here
REQUIRE_ADMIN=True
```

**How to find your Telegram User ID:**
- Message [@userinfobot](https://t.me/userinfobot) on Telegram
- It will reply with your numeric ID (e.g. `987654321`)

**Multiple admins:**
```env
ADMIN_IDS=987654321,111222333
```

---

## Step 4 — Install Python Dependencies

### Option A — Standard (Linux/Mac/Windows)

```bash
# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate        # Linux/Mac
venv\Scripts\activate           # Windows

# Install dependencies
pip install -r requirements.txt
```

### Option B — If you get system package errors

```bash
pip install -r requirements.txt --break-system-packages
```

---

## Step 5 — Run the Bot

```bash
python bot.py
```

You should see:
```
🚀 Starting bot...
✅ Bot initialized!
⏰ Scheduler running
📢 Group message job started
📡 Auto-start complete
```

---

## Step 6 — First Login via Bot

1. Open your bot on Telegram
2. Send `/start`
3. Click **🔐 Login Account**
4. Enter your **API ID**, **API Hash**, **Phone Number**, **OTP**, and **2FA password** (if enabled)
5. Your account will be linked

> **Admin accounts** get full access immediately.  
> **Other users** must wait for admin approval.

---

## Step 7 — Add Escrow Group

1. In the bot, go to **💼 Escrow → ➕ Add Group**
2. Send one of:
   - `@groupusername` (public group)
   - `https://t.me/+InviteLink` (private group)
   - `-1001234567890` (numeric group ID)
3. Make sure your logged-in Telegram account is an **admin** in that group
4. The bot will confirm and start monitoring

---

## Step 8 — Add Group Auto Messages

1. Go to **📢 Group Messages → ➕ Add Group Message**
2. Send in format: `@group <interval_minutes> <message>`
   - Example: `@mygroup 5 Hello everyone! 👋`
3. The bot will send that message to the group every 5 minutes

> ⚠️ Keep interval at **5 minutes or more** to reduce ban risk.

---

## Deployment on VPS (Recommended)

Running on a VPS keeps the bot online 24/7.

### Using systemd (Linux)

Create `/etc/systemd/system/tgbot.service`:

```ini
[Unit]
Description=Telegram Pro Automation Bot
After=network.target

[Service]
Type=simple
WorkingDirectory=/path/to/your/bot
ExecStart=/path/to/your/bot/venv/bin/python bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl daemon-reload
sudo systemctl enable tgbot
sudo systemctl start tgbot
sudo systemctl status tgbot
```

### View logs:
```bash
sudo journalctl -u tgbot -f
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `BOT_TOKEN not set` | Check your `.env` file exists and has the correct token |
| `Phone code invalid` | Make sure you enter the OTP exactly as received |
| `FloodWaitError` | Telegram is rate-limiting you — wait the specified time |
| `ChatAdminRequiredError` | Your logged-in account is not admin in the group |
| Escrow not replying | Check the group is added, account is admin, and all form fields are filled |
| Bot not responding | Restart with `python bot.py` and check console for errors |

---

## ⚠️ Safety Reminders

- Use a **secondary Telegram account**, not your personal main account
- Never set group message interval below **5 minutes**
- Do not scrape more than **200–300 members** at a time
- If you get a `FloodWaitError`, the bot will pause automatically — do not restart it
