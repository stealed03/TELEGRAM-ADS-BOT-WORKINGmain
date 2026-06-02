# 🤖 Telegram Pro Automation Bot

A Telegram bot with userbot capabilities — escrow monitoring, scheduled messages, group auto-messages, admin approval system, and more.

---

## ⚠️ Account Safety & Ban Risk

Using a **userbot** (Telethon) means your real Telegram account is logged in programmatically. Telegram monitors unusual activity.

### 🟢 Low Risk (this bot does this)
- Replying **once** to an escrow form per message
- Sending scheduled messages to individual users

### 🟡 Medium Risk
- Group auto-messages with intervals **under 5 minutes**
- Scraping large numbers of members (500+)

### 🔴 High Risk (avoid)
- Interval under 1–2 minutes repeatedly
- Mass messaging hundreds of users quickly
- Joining many groups rapidly

### Tips to Stay Safe
- Set group message interval to **5 minutes minimum**
- Use a **secondary Telegram account**, not your main one
- Don't scrape more than 200–300 members at a time
- Keep the bot running on a stable server (VPS), not restarting repeatedly

---

## ✨ Features

| Feature | Description |
|---|---|
| 🔐 Admin Approval | Users must be approved by admin before using the bot |
| 💼 Escrow Monitor | Auto-detects Boss Escrow Deal forms in groups and replies BOTH AGREE at the next minute boundary |
| 📢 Group Messages | Send a fixed message to multiple groups, each with its own interval (e.g. every 2 min) |
| ⏰ Scheduler | Schedule messages to any user/group at a specific time (India timezone) |
| 🤖 Auto Reply | Auto-reply to personal DMs when you're away |
| 🔍 Scraper | Scrape group member lists to CSV |
| 👥 Multi-Account | Manage multiple Telegram accounts |
| 📊 Analytics | View message stats and activity |
| 📢 Broadcast | Admin can broadcast to all / approved / unapproved users |

---

## 🛠️ Requirements

- Python 3.10+
- A Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- Telegram API credentials (from [my.telegram.org](https://my.telegram.org))

---

## 🚀 Quick Setup

See **SETUP.md** for full installation instructions.

---

## 📁 File Structure

```
├── bot.py              # Main bot — all handlers and routing
├── config.py           # Config: BOT_TOKEN, ADMIN_IDS
├── database.py         # SQLite DB — all tables and queries
├── escrow.py           # Escrow form detection and BOTH AGREE reply
├── group_messages.py   # Group auto-message scheduler
├── login.py            # Telethon login flow + admin approval
├── menu.py             # Inline keyboard menus
├── messaging.py        # Send message via Telethon
├── scheduler.py        # Time-based message scheduler
├── scraper.py          # Group member scraper
├── auto_reply.py       # Auto-reply for personal DMs
├── analytics.py        # User stats
├── client_manager.py   # Telethon client pool
├── requirements.txt    # Python dependencies
├── .env                # Your secrets (never commit this)
└── automation.db       # SQLite database (auto-created)
```

---

## 👑 Admin Commands (via bot)

| Button | Action |
|---|---|
| 👥 All Users & Accounts | View every user's API ID, API Hash, Phone, Password |
| 📝 Access Requests | Approve or reject pending users |
| 📢 Broadcast (All) | Message all registered users |
| 📢 Broadcast (Approved) | Message only approved users |
| 📢 Broadcast (Unapproved) | Message only pending users |

---

## 💼 Escrow System

The bot monitors configured groups for the **Boss Escrow Deal** form.

- ✅ Replies only when **ALL fields are filled** (blank form = no reply)
- ✅ Replies only when the logged-in account is an **admin** in that group
- ✅ Works with **public groups** (@username), **private groups** (invite link or numeric ID)
- ⏰ Replies at the **start of the next minute** after the form is sent
  - Form sent at `09:56:23` → reply at `09:57:00`
  - Form sent at `07:45:23` → reply at `07:46:00`

---

## 📄 License

For personal use only. Do not redistribute.

CREDIT GOES TO 
TELEGRAM USER
@TALK_WITH_STEALED
