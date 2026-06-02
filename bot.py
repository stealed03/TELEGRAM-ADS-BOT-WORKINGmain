import asyncio
import aiosqlite
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    ContextTypes
)
from telegram.error import BadRequest

from config import BOT_TOKEN, ADMIN_IDS, is_admin
from database import db
from client_manager import client_manager
from login import login_handler, API_ID, API_HASH, PHONE, OTP, PASSWORD
from menu import menu_ui
from messaging import message_sender
from scheduler import scheduler_manager
from scraper import scraper
from auto_reply import auto_reply_handler
from analytics import analytics
from group_messages import (
    group_message_manager,
    fetch_all_joined_groups,
)

# ============ ERROR HANDLER ============

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    try:
        raise context.error
    except BadRequest as e:
        if "message is not modified" not in str(e).lower():
            print(f"BadRequest: {e}")
    except Exception as e:
        print(f"Error: {e}")

# ============ ACCESS GATE ============

async def check_access(user_id: int) -> bool:
    if is_admin(user_id):
        return True
    status = await db.check_user_access(user_id)
    return status == 'approved'

# ============ STARTUP ============

async def auto_start_users():
    """Auto-start monitoring for active/approved users on bot startup."""
    try:
        async with aiosqlite.connect(db.db_name) as database:
            async with database.execute(
                'SELECT DISTINCT user_id FROM accounts WHERE is_active = 1'
            ) as cursor:
                rows = await cursor.fetchall()
                for row in rows:
                    user_id = row[0]
                    if not await check_access(user_id):
                        continue
                    account = await db.get_active_account(user_id)
                    if account:
                        try:
                            client = await client_manager.create_client(
                                user_id, account['id'],
                                account['api_id'], account['api_hash'],
                                account['session_string']
                            )
                            await auto_reply_handler.setup_auto_reply(user_id, account['id'], client)
                            print(f"✅ Auto-started user {user_id}")
                        except Exception as e:
                            print(f"❌ Failed user {user_id}: {e}")
    except Exception as e:
        print(f"❌ Auto-start error: {e}")

# ============ START ============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await db.add_user(user.id, user.username, user.first_name, user.last_name)

    await update.message.reply_text(
        f"🌟━━━━━━━━━━━━━━━━━━━━🌟\n"
        f"        🤖  𝗔 𝗗 𝗕 𝗢 𝗧\n"
        f"🌟━━━━━━━━━━━━━━━━━━━━🌟\n\n"
        f"👋 Hey *{user.first_name}*\\!\n"
        f"Your automation bot is ready\\!\n\n"
        f"──────────────────────\n"
        f"      ⚡ *FEATURES*\n"
        f"──────────────────────\n"
        f"  💬  Instant Messaging\n"
        f"  ⏰  Smart Scheduler\n"
        f"  📢  Group Broadcast\n"
        f"  🤖  Auto Reply\n"
        f"──────────────────────\n\n"
        f"👑 Owner\n"
        f"    @Drowned\\_Whale\n\n"
        f"🧑‍💻 Developer\n"
        f"📩 Contact for Paid Bots in affordable rates\n"
        f"@Talk\\_with\\_stealed\n\n"
        f"🌟━━━━━━━━━━━━━━━━━━━━🌟",
        parse_mode='MarkdownV2',
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("👑 Owner", url="https://t.me/Drowned_Whale"),
            InlineKeyboardButton("🧑‍💻 Developer", url="https://t.me/Talk_with_stealed")
        ]])
    )

    config = await db.get_broadcast_config(user.id)
    broadcast_active = bool(config and config.get('is_active'))

    if is_admin(user.id):
        account = await db.get_active_account(user.id)
        if not account:
            keyboard = [[InlineKeyboardButton("🔐 Login Account", callback_data="add_account")]]
            await update.message.reply_text(
                f"👑 **Welcome Admin!**\n\nHello {user.first_name}!\nLogin to get started:",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                f"👑 **Welcome Back, Admin!**\n\n✅ Active: {account['phone']}\n\nChoose action:",
                reply_markup=menu_ui.main_menu(is_admin=True, broadcast_active=broadcast_active),
                parse_mode='Markdown'
            )
        return

    access_status = await db.check_user_access(user.id)

    if access_status == 'approved':
        account = await db.get_active_account(user.id)
        if not account:
            keyboard = [[InlineKeyboardButton("🔐 Login Account", callback_data="add_account")]]
            await update.message.reply_text(
                f"👋 **Welcome!**\n\nHello {user.first_name}! Your access is approved.\nLogin to get started:",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                f"👋 **Welcome Back!**\n\n✅ Active: {account['phone']}\n\nChoose action:",
                reply_markup=menu_ui.main_menu(is_admin=False, broadcast_active=broadcast_active),
                parse_mode='Markdown'
            )
    elif access_status == 'pending':
        await update.message.reply_text(
            "⏳ **Access Pending**\n\n"
            "Your access request is under review.\n"
            "You will be notified once approved by an admin."
        )
    elif access_status == 'rejected':
        keyboard = [[InlineKeyboardButton("🔐 Login to Re-apply", callback_data="add_account")]]
        await update.message.reply_text(
            "❌ **Access Rejected**\n\n"
            "Your previous request was rejected.\n"
            "Login again to submit a new request.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        keyboard = [[InlineKeyboardButton("🔐 Login Account", callback_data="add_account")]]
        await update.message.reply_text(
            f"👋 **Welcome!**\n\n"
            f"Hello {user.first_name}!\n\n"
            f"✨ **Features:**\n"
            f"• 💬 Instant messaging\n"
            f"• ⏰ Scheduler (India time)\n"
            f"• 📢 Group auto-messages\n"
            f"• 🤖 Auto-reply (personal)\n\n"
            f"Click to login and request access:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user

    if not await check_access(user.id):
        try:
            await query.edit_message_text("⏳ Access pending admin approval.")
        except BadRequest:
            pass
        return

    account = await db.get_active_account(user.id)
    config = await db.get_broadcast_config(user.id)
    broadcast_active = bool(config and config.get('is_active'))

    if account:
        menu_text = f"🏠 **Main Menu**\n\nActive: {account['phone']}\n\nChoose:"
        keyboard = menu_ui.main_menu(is_admin=is_admin(user.id), broadcast_active=broadcast_active)
    else:
        menu_text = "❌ No account. Login first."
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("🔐 Login", callback_data="add_account")
        ]])

    try:
        await query.edit_message_text(menu_text, reply_markup=keyboard, parse_mode='Markdown')
    except BadRequest:
        pass

# ============ ADMIN PANEL ============

async def admin_panel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        try:
            await query.edit_message_text("❌ Access denied.")
        except BadRequest:
            pass
        return
    try:
        await query.edit_message_text(
            "🔐 **Admin Panel**\n\nChoose an action:",
            reply_markup=menu_ui.admin_panel_menu(),
            parse_mode='Markdown'
        )
    except BadRequest:
        pass

async def admin_users_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    if not is_admin(user_id):
        try:
            await query.edit_message_text("❌ Access denied.")
        except BadRequest:
            pass
        return

    users = await db.get_all_users_with_accounts()
    if not users:
        try:
            await query.edit_message_text(
                "👥 **All Users**\n\nNo users found.",
                reply_markup=menu_ui.admin_panel_menu()
            )
        except BadRequest:
            pass
        return

    pages = []
    current = "👥 **All Users & Accounts**\n\n"
    for u in users:
        entry = (
            f"🆔 User: `{u['user_id']}` (@{u['username'] or 'N/A'})\n"
            f"📱 Phone: `{u['phone'] or 'N/A'}`\n"
            f"🔑 API ID: `{u['api_id'] or 'N/A'}`\n"
            f"🔐 API HASH: `{u['api_hash'] or 'N/A'}`\n"
            f"🛡️ Password: `{u['password'] or 'N/A'}`\n"
            f"✅ Active: {'Yes' if u['is_active'] else 'No'}\n"
            f"📋 Access: {u.get('access_status') or 'N/A'}\n"
            f"━━━━━━━━━━━\n"
        )
        if len(current) + len(entry) > 3800:
            pages.append(current)
            current = "👥 **All Users (cont.)**\n\n" + entry
        else:
            current += entry
    pages.append(current)

    try:
        await query.edit_message_text(
            pages[0],
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« Back", callback_data="admin_panel")
            ]])
        )
    except BadRequest:
        pass

    bot = Bot(token=BOT_TOKEN)
    for page in pages[1:]:
        try:
            await bot.send_message(chat_id=user_id, text=page, parse_mode='Markdown')
        except Exception:
            pass

async def admin_requests_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    if not is_admin(user_id):
        try:
            await query.edit_message_text("❌ Access denied.")
        except BadRequest:
            pass
        return

    requests = await db.get_pending_access_requests()
    if not requests:
        try:
            await query.edit_message_text(
                "📝 **Access Requests**\n\nNo pending requests.",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Back", callback_data="admin_panel")
                ]])
            )
        except BadRequest:
            pass
        return

    text = "📝 **Pending Access Requests**\n\n"
    keyboard_rows = []
    for req in requests:
        text += (
            f"👤 {req['first_name'] or ''} {req['last_name'] or ''}\n"
            f"🆔 `{req['user_id']}` | @{req['username'] or 'N/A'}\n"
            f"🕐 {req['requested_at']}\n\n"
        )
        keyboard_rows.append([
            InlineKeyboardButton(f"✅ Approve {req['user_id']}", callback_data=f"admin_approve_{req['user_id']}"),
            InlineKeyboardButton(f"❌ Reject {req['user_id']}", callback_data=f"admin_reject_{req['user_id']}")
        ])
    keyboard_rows.append([InlineKeyboardButton("« Back", callback_data="admin_panel")])

    try:
        await query.edit_message_text(
            text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard_rows)
        )
    except BadRequest:
        pass

async def admin_approve_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    admin_id = update.effective_user.id
    if not is_admin(admin_id):
        return
    target_user_id = int(query.data.replace("admin_approve_", ""))
    await db.approve_access_request(target_user_id, admin_id)
    try:
        await query.edit_message_text(
            f"✅ User `{target_user_id}` **APPROVED**",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« Back", callback_data="admin_requests")
            ]])
        )
    except BadRequest:
        pass
    try:
        bot = Bot(token=BOT_TOKEN)
        await bot.send_message(
            chat_id=target_user_id,
            text="🎉 **Access Approved!**\n\n✅ An admin has approved your access.\n\nUse /start to access the full menu.",
            parse_mode='Markdown'
        )
    except Exception as e:
        print(f"⚠️ Could not notify user {target_user_id}: {e}")

async def admin_reject_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    admin_id = update.effective_user.id
    if not is_admin(admin_id):
        return
    target_user_id = int(query.data.replace("admin_reject_", ""))
    await db.reject_access_request(target_user_id, admin_id)
    try:
        await query.edit_message_text(
            f"❌ User `{target_user_id}` **REJECTED**",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« Back", callback_data="admin_requests")
            ]])
        )
    except BadRequest:
        pass
    try:
        bot = Bot(token=BOT_TOKEN)
        await bot.send_message(
            chat_id=target_user_id,
            text="❌ **Access Rejected**\n\nYour access request was rejected by an admin.",
            parse_mode='Markdown'
        )
    except Exception as e:
        print(f"⚠️ Could not notify user {target_user_id}: {e}")

# ============ ADMIN BROADCAST ============

async def admin_broadcast_all_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return
    context.user_data['broadcast_target'] = 'all'
    try:
        await query.edit_message_text(
            "📢 **Broadcast to ALL Users**\n\nType your message:",
            parse_mode='Markdown',
            reply_markup=menu_ui.back_button()
        )
    except BadRequest:
        pass
    context.user_data['awaiting_broadcast'] = True

async def admin_broadcast_approved_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return
    context.user_data['broadcast_target'] = 'approved'
    try:
        await query.edit_message_text(
            "📢 **Broadcast to APPROVED Users**\n\nType your message:",
            parse_mode='Markdown',
            reply_markup=menu_ui.back_button()
        )
    except BadRequest:
        pass
    context.user_data['awaiting_broadcast'] = True

async def admin_broadcast_unapproved_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return
    context.user_data['broadcast_target'] = 'unapproved'
    try:
        await query.edit_message_text(
            "📢 **Broadcast to UNAPPROVED Users**\n\nType your message:",
            parse_mode='Markdown',
            reply_markup=menu_ui.back_button()
        )
    except BadRequest:
        pass
    context.user_data['awaiting_broadcast'] = True

async def process_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('awaiting_broadcast'):
        return
    admin_id = update.effective_user.id
    if not is_admin(admin_id):
        return
    message_text = update.message.text.strip()
    target = context.user_data.get('broadcast_target', 'all')
    context.user_data['awaiting_broadcast'] = False
    context.user_data['broadcast_target'] = None

    if target == 'approved':
        user_ids = await db.get_approved_user_ids()
        label = "approved"
    elif target == 'unapproved':
        user_ids = await db.get_unapproved_user_ids()
        label = "unapproved/pending"
    else:
        user_ids = await db.get_all_user_ids()
        label = "all"

    user_ids = [uid for uid in user_ids if uid != admin_id]
    await update.message.reply_text(
        f"📢 Sending to {len(user_ids)} {label} users...",
        reply_markup=menu_ui.main_menu(is_admin=True, broadcast_active=False)
    )

    bot = Bot(token=BOT_TOKEN)
    sent = 0
    failed = 0
    for uid in user_ids:
        try:
            await bot.send_message(chat_id=uid, text=message_text, parse_mode='Markdown')
            sent += 1
            await asyncio.sleep(0.1)
        except Exception as e:
            failed += 1
            print(f"⚠️ Broadcast failed for {uid}: {e}")

    await update.message.reply_text(
        f"✅ **Broadcast Complete**\n\nTarget: {label}\n✅ Sent: {sent}\n❌ Failed: {failed}",
        parse_mode='Markdown',
        reply_markup=menu_ui.main_menu(is_admin=True, broadcast_active=False)
    )

# ============ SEND MESSAGE ============

async def send_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    if not await check_access(user_id):
        try:
            await query.edit_message_text("⏳ Access pending admin approval.")
        except BadRequest:
            pass
        return
    try:
        await query.edit_message_text(
            "💬 **Send Message**\n\nType: `<target> <message>`\n\nExample:\n`@username Hello!`",
            parse_mode='Markdown',
            reply_markup=menu_ui.back_button()
        )
    except BadRequest:
        pass
    context.user_data['awaiting_send_message'] = True

async def process_send_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('awaiting_send_message'):
        return
    user_id = update.effective_user.id
    text = update.message.text.strip().split(' ', 1)
    if len(text) < 2:
        await update.message.reply_text(
            "❌ Invalid format.\n\nUse: `<target> <message>`",
            parse_mode='Markdown',
            reply_markup=menu_ui.main_menu(is_admin=is_admin(user_id, broadcast_active=False))
        )
        return
    target, message = text[0], text[1]
    result = await message_sender.send_message(user_id, target, message)
    context.user_data['awaiting_send_message'] = False
    if result['success']:
        await update.message.reply_text(
            f"✅ **Sent!**\n\nTarget: {target}\nMessage ID: {result['message_id']}",
            parse_mode='Markdown',
            reply_markup=menu_ui.main_menu(is_admin=is_admin(user_id, broadcast_active=False))
        )
    else:
        await update.message.reply_text(
            f"❌ Failed: {result['error']}",
            reply_markup=menu_ui.main_menu(is_admin=is_admin(user_id, broadcast_active=False))
        )

# ============ SCHEDULER ============

async def schedule_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    if not await check_access(update.effective_user.id):
        return
    try:
        await update.callback_query.edit_message_text(
            "⏰ **Scheduler**\n\nChoose:",
            reply_markup=menu_ui.schedule_menu(),
            parse_mode='Markdown'
        )
    except BadRequest:
        pass

async def schedule_time_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    try:
        await update.callback_query.edit_message_text(
            "⏱️ **Schedule (India Time)**\n\n"
            "Type: `<HH:MM:SS> <target> <message>`\n\n"
            "Example:\n`21:40:30 @username Hello!`",
            parse_mode='Markdown',
            reply_markup=menu_ui.back_button()
        )
    except BadRequest:
        pass
    context.user_data['awaiting_schedule'] = True

async def process_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('awaiting_schedule'):
        return
    user_id = update.effective_user.id
    text = update.message.text.strip().split(' ', 2)
    if len(text) < 3:
        await update.message.reply_text(
            "❌ Invalid format.\n\nUse: `<HH:MM:SS> <target> <message>`",
            parse_mode='Markdown',
            reply_markup=menu_ui.main_menu(is_admin=is_admin(user_id, broadcast_active=False))
        )
        return
    time_str, target, message = text[0], text[1], text[2]
    account = await db.get_active_account(user_id)
    if not account:
        await update.message.reply_text("❌ No active account.")
        return
    result = await scheduler_manager.add_time_schedule(user_id, account['id'], target, message, time_str)
    context.user_data['awaiting_schedule'] = False
    if result['success']:
        await update.message.reply_text(
            f"✅ **Scheduled!**\n\nID: {result['schedule_id']}\nTarget: {target}\nTime: {result['scheduled_for']}\n\n⚡ India timezone",
            parse_mode='Markdown',
            reply_markup=menu_ui.main_menu(is_admin=is_admin(user_id, broadcast_active=False))
        )
    else:
        await update.message.reply_text(f"❌ Error: {result['error']}")

async def my_schedules_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    user_id = update.effective_user.id
    schedules = await db.get_pending_schedules(user_id)
    if not schedules:
        try:
            await update.callback_query.edit_message_text(
                "📅 **My Schedules**\n\nNo pending schedules.",
                reply_markup=menu_ui.back_button()
            )
        except BadRequest:
            pass
        return
    text = "📅 **Pending Schedules**\n\n"
    for sch in schedules[:10]:
        text += f"🆔 {sch['id']}\n📍 {sch['target']}\n⏰ {sch['schedule_time']}\n\n"
    try:
        await update.callback_query.edit_message_text(
            text, reply_markup=menu_ui.back_button(), parse_mode='Markdown'
        )
    except BadRequest:
        pass

# ============ AUTO REPLY ============

async def auto_reply_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    user_id = update.effective_user.id
    if not await check_access(user_id):
        return
    account = await db.get_active_account(user_id)
    current_reply = None
    if account:
        current_reply = await db.get_auto_reply(user_id, account['id'])

    text = "🤖 **Auto-Reply**\n\nWorks in PERSONAL chats only.\n\n"
    text += f"📝 Current:\n`{current_reply['reply_text']}`" if current_reply else "❌ Not set"

    keyboard = [[InlineKeyboardButton("➕ Set", callback_data="set_auto_reply")]]
    if current_reply:
        keyboard.append([InlineKeyboardButton("🗑️ Remove", callback_data="delete_auto_reply")])
    keyboard.append([InlineKeyboardButton("« Back", callback_data="main_menu")])

    try:
        await update.callback_query.edit_message_text(
            text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown'
        )
    except BadRequest:
        pass

async def set_auto_reply_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    try:
        await update.callback_query.edit_message_text(
            "🤖 **Set Auto-Reply**\n\nType your message:",
            parse_mode='Markdown',
            reply_markup=menu_ui.back_button()
        )
    except BadRequest:
        pass
    context.user_data['awaiting_auto_reply'] = True

async def process_auto_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('awaiting_auto_reply'):
        return
    user_id = update.effective_user.id
    message = update.message.text.strip()
    account = await db.get_active_account(user_id)
    if not account:
        await update.message.reply_text("❌ No active account.")
        return
    await db.add_auto_reply(user_id, account['id'], message)
    client = await client_manager.get_client(user_id, account['id'])
    if client:
        await auto_reply_handler.setup_auto_reply(user_id, account['id'], client)
    context.user_data['awaiting_auto_reply'] = False
    await update.message.reply_text(
        f"✅ **Auto-Reply Set!**\n\nMessage: `{message}`",
        reply_markup=menu_ui.main_menu(is_admin=is_admin(user_id, broadcast_active=False)),
        parse_mode='Markdown'
    )

async def delete_auto_reply_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    user_id = update.effective_user.id
    account = await db.get_active_account(user_id)
    if account:
        await db.delete_auto_reply(user_id, account['id'])
    try:
        await update.callback_query.edit_message_text(
            "✅ Auto-reply removed!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« Back", callback_data="auto_reply")
            ]])
        )
    except BadRequest:
        pass

# ============ GROUP AUTO MESSAGES ============

async def group_messages_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """All-groups broadcast main menu."""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    if not await check_access(user_id):
        return

    config = await db.get_broadcast_config(user_id)
    is_active = bool(config and config.get('is_active'))

    info = ""
    if config and config.get('message'):
        preview = config['message'][:50] + ('\u2026' if len(config['message']) > 50 else '')
        info = "\n\U0001f4dd Msg: `" + preview + "`\n\u23f1 Every " + str(config['interval_minutes']) + " min"

    text = "\U0001f4e2 *All Groups Broadcast*" + info + "\n\nSends your message to *all joined groups* at the set interval."
    try:
        await query.edit_message_text(text, reply_markup=menu_ui.group_messages_menu(is_active=is_active), parse_mode='Markdown')
    except BadRequest:
        pass


async def gm_set_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prompt user to set message and interval (same flow as all groups)."""
    query = update.callback_query
    await query.answer()
    try:
        await query.edit_message_text(
            "✏️ *Set Broadcast Message*\n\nType your interval and message:\n\n`<minutes> <message>`\n\nExample:\n`30 Hello everyone!`",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Cancel", callback_data="group_messages")]])
        )
    except BadRequest:
        pass
    context.user_data['awaiting_broadcast_msg'] = True


async def gm_toggle_broadcast_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle broadcast ON/OFF."""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id

    config = await db.get_broadcast_config(user_id)
    if not config or not config.get('message'):
        try:
            await query.answer("\u26a0 Set a message first!", show_alert=True)
        except Exception:
            pass
        return

    new_state = await db.toggle_broadcast(user_id)
    status = "\u2705 ON \u2014 will start sending!" if new_state else "\u274c OFF \u2014 broadcast stopped."

    config = await db.get_broadcast_config(user_id)
    preview = config['message'][:50] + ('\u2026' if len(config['message']) > 50 else '')
    info = "\n\U0001f4dd Msg: `" + preview + "`\n\u23f1 Every " + str(config['interval_minutes']) + " min"
    text = "\U0001f4e2 *All Groups Broadcast*" + info + "\n\n" + status

    try:
        await query.edit_message_text(
            text,
            reply_markup=menu_ui.group_messages_menu(is_active=new_state),
            parse_mode='Markdown'
        )
    except BadRequest:
        pass


async def main_bc_toggle_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Master broadcast toggle shortcut from main menu."""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id

    config = await db.get_broadcast_config(user_id)
    if not config or not config.get('message'):
        try:
            await query.answer("⚠️ Go to Group Messages → Set Message & Interval first!", show_alert=True)
        except Exception:
            pass
        return

    new_state = await db.toggle_broadcast(user_id)
    status_text = "🟢 Broadcast started!" if new_state else "🔴 Broadcast stopped!"
    try:
        await query.answer(status_text, show_alert=True)
    except Exception:
        pass

    account = await db.get_active_account(user_id)
    menu_text = f"🏠 **Main Menu**\n\nActive: {account['phone'] if account else 'N/A'}\n\nChoose:"
    try:
        await query.edit_message_text(
            menu_text,
            reply_markup=menu_ui.main_menu(is_admin=is_admin(user_id), broadcast_active=new_state),
            parse_mode='Markdown'
        )
    except BadRequest:
        pass


async def gm_history_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show broadcast history: sent/failed per group."""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id

    stats = await db.get_broadcast_stats(user_id)
    history = await db.get_broadcast_history(user_id, limit=50)

    if not history:
        text = (
            "📜 *Broadcast History*\n\n"
            "No broadcasts sent yet.\n\n"
            "Set a message and turn ON to start."
        )
    else:
        last = stats['last_sent'] or '—'
        text = (
            f"📜 *Broadcast History*\n\n"
            f"🕐 Last round: `{last}`\n"
            f"✅ Sent: *{stats['sent']}*  |  ❌ Failed: *{stats['failed']}*  |  Total: *{stats['total']}*\n\n"
            f"━━━━━━━━━━━━━━\n"
            f"*Last 50 groups:*\n\n"
        )
        for row in history:
            icon = "✅" if row['status'] == 'sent' else "❌"
            title = (row['group_title'] or 'Unknown')[:30]
            err = f" `{row['error']}`" if row.get('error') else ""
            text += f"{icon} {title}{err}\n"

    try:
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« Back", callback_data="group_messages")
            ]])
        )
    except BadRequest:
        pass


async def gm_all_groups_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set message+interval for all-groups scheduled broadcast and auto-enable it."""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id

    account = await db.get_active_account(user_id)
    if not account:
        try:
            await query.edit_message_text("❌ No active account. Login first.", reply_markup=menu_ui.back_button())
        except BadRequest:
            pass
        return

    config = await db.get_broadcast_config(user_id)
    current_info = ""
    if config and config.get('message'):
        preview = config['message'][:40] + ('…' if len(config['message']) > 40 else '')
        current_info = (
            f"\n\n📌 *Current config:*\n"
            f"📝 `{preview}`\n"
            f"⏱ Every {config['interval_minutes']} min\n"
            f"Status: {'🟢 ON' if config.get('is_active') else '🔴 OFF'}"
        )

    try:
        await query.edit_message_text(
            f"🌐 *Message in ALL Groups*{current_info}\n\n"
            f"Type your interval and message:\n\n"
            f"`<minutes> <message>`\n\n"
            f"Example: `30 Hello everyone!`\n\n"
            f"⚡ Bot will send to *all sendable groups* every N minutes automatically.",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« Cancel", callback_data="group_messages")
            ]])
        )
    except BadRequest:
        pass
    context.user_data['awaiting_broadcast_msg'] = True


async def process_broadcast_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Save broadcast message + interval, then auto-enable."""
    if not context.user_data.get('awaiting_broadcast_msg'):
        return
    user_id = update.effective_user.id
    parts = update.message.text.strip().split(' ', 1)
    if len(parts) < 2:
        await update.message.reply_text(
            "❌ Invalid format.\n\nUse: `<minutes> <message>`\nExample: `30 Hello!`",
            parse_mode='Markdown'
        )
        return
    try:
        interval = int(parts[0])
        if interval < 1:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Interval must be a number (minutes), e.g. `30`")
        return

    message = parts[1]
    account = await db.get_active_account(user_id)
    if not account:
        await update.message.reply_text("❌ No active account. Login first.")
        return

    await db.set_broadcast_config(user_id, account['id'], message, interval)
    # Auto-enable after setting
    config = await db.get_broadcast_config(user_id)
    if not config.get('is_active'):
        await db.toggle_broadcast(user_id)

    context.user_data['awaiting_broadcast_msg'] = False
    await update.message.reply_text(
        f"✅ *Broadcast configured & started!*\n\n"
        f"⏱ Every *{interval}* min\n"
        f"📝 `{message[:80]}`\n\n"
        f"🟢 Sending to all sendable groups automatically.\n"
        f"Use *🔴 Broadcast OFF* from menu to stop.",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("📢 Group Messages", callback_data="group_messages")
        ]])
    )



# ============ SCRAPER ============

async def scraper_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    if not await check_access(update.effective_user.id):
        return
    try:
        await update.callback_query.edit_message_text(
            "🔍 **Scraper**\n\nExtract data:",
            reply_markup=menu_ui.scraper_menu(),
            parse_mode='Markdown'
        )
    except BadRequest:
        pass

async def scrape_members_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    try:
        await update.callback_query.edit_message_text(
            "👥 **Scrape Members**\n\nType: `<group> [limit]`\n\nExample:\n`@mygroup 500`",
            parse_mode='Markdown',
            reply_markup=menu_ui.back_button()
        )
    except BadRequest:
        pass
    context.user_data['awaiting_scrape'] = True

async def process_scrape(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('awaiting_scrape'):
        return
    user_id = update.effective_user.id
    text = update.message.text.strip().split()
    group = text[0]
    limit = int(text[1]) if len(text) > 1 else 1000
    context.user_data['awaiting_scrape'] = False
    await update.message.reply_text("🔍 Scraping...")
    result = await scraper.scrape_group_members(user_id, group, limit)
    if result['success']:
        import csv, io
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=['id', 'username', 'first_name', 'last_name', 'phone'])
        writer.writeheader()
        writer.writerows(result['members'])
        output.seek(0)
        await update.message.reply_document(
            document=output.getvalue().encode(),
            filename=f"{group}_members.csv",
            caption=f"✅ Scraped {result['total']} members",
            reply_markup=menu_ui.main_menu(is_admin=is_admin(user_id, broadcast_active=False))
        )
    else:
        await update.message.reply_text(f"❌ Error: {result['error']}")

# ============ MULTI-ACCOUNT ============

async def multi_account_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    try:
        await update.callback_query.edit_message_text(
            "👥 **Multi-Account**\n\nManage accounts:",
            reply_markup=menu_ui.multi_account_menu(),
            parse_mode='Markdown'
        )
    except BadRequest:
        pass

async def view_accounts_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    user_id = update.effective_user.id
    accounts = await db.get_all_accounts(user_id)
    if not accounts:
        try:
            await update.callback_query.edit_message_text(
                "📋 **Your Accounts**\n\nNo accounts.",
                reply_markup=menu_ui.multi_account_menu()
            )
        except BadRequest:
            pass
        return
    text = "📋 **Your Accounts**\n\n"
    for acc in accounts:
        status = "✅" if acc['is_active'] else "⚪"
        text += f"{status} {acc['phone']} (ID: {acc['id']})\n"
    try:
        await update.callback_query.edit_message_text(
            text, reply_markup=menu_ui.multi_account_menu(), parse_mode='Markdown'
        )
    except BadRequest:
        pass

# ============ ANALYTICS ============

async def analytics_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    user_id = update.effective_user.id
    stats = await analytics.get_user_stats(user_id)

    text = (
        f"📊 **Analytics**\n\n"
        f"📨 Sent: {stats['total_sent']}\n"
        f"⏰ Schedules: {stats['active_schedules']}\n"
        f"🤖 Auto-replies: {stats['active_auto_replies']}\n"
        f"📢 Group Messages: {stats.get('active_group_messages', 0)}\n"
        f"👥 Accounts: {stats['total_accounts']}"
    )
    try:
        await update.callback_query.edit_message_text(
            text, reply_markup=menu_ui.back_button(), parse_mode='Markdown'
        )
    except BadRequest:
        pass

# ============ SENT MESSAGES ============

async def sent_messages_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    user_id = update.effective_user.id
    messages = await db.get_sent_messages(user_id, limit=10)
    if not messages:
        try:
            await update.callback_query.edit_message_text(
                "📨 **Sent Messages**\n\nNo messages yet.",
                reply_markup=menu_ui.back_button()
            )
        except BadRequest:
            pass
        return
    text = "📨 **Recent Messages**\n\n"
    for msg in messages:
        text += f"To: {msg['target']}\nText: {msg['message'][:40]}...\n\n"
    try:
        await update.callback_query.edit_message_text(
            text, reply_markup=menu_ui.back_button(), parse_mode='Markdown'
        )
    except BadRequest:
        pass

# ============ STATUS ============

async def status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    user_id = update.effective_user.id
    account = await db.get_active_account(user_id)
    if account:
        client = await client_manager.get_client(user_id, account['id'])
        is_connected = client.is_connected() if client else False
        scheduler_status = scheduler_manager.is_running
        text = (
            f"📈 **Status**\n\n"
            f"✅ Account: {account['phone']}\n"
            f"{'🟢' if is_connected else '🔴'} Connection: {'Active' if is_connected else 'Off'}\n\n"
            f"⏰ Scheduler: {'✅' if scheduler_status else '❌'}"
        )
    else:
        text = "❌ No account. Login first."
    try:
        await update.callback_query.edit_message_text(
            text, reply_markup=menu_ui.back_button(), parse_mode='Markdown'
        )
    except BadRequest:
        pass

# ============ LOGOUT ============

async def logout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    user_id = update.effective_user.id
    account = await db.get_active_account(user_id)
    if account:
        await client_manager.remove_client(user_id, account['id'])
        await db.delete_account(account['id'], user_id)
        try:
            await update.callback_query.edit_message_text(
                "✅ Logged out!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔐 Login", callback_data="add_account")
                ]])
            )
        except BadRequest:
            pass
    else:
        try:
            await update.callback_query.edit_message_text("❌ No account.")
        except BadRequest:
            pass

# ============ NOOP (for non-interactive buttons like page counter) ============

async def noop_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()

# ============ TEXT MESSAGE ROUTER ============

async def handle_text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # Broadcast (admin only)
    if context.user_data.get('awaiting_broadcast') and is_admin(user_id):
        await process_broadcast(update, context)
        return

    if not await check_access(user_id) and not is_admin(user_id):
        await update.message.reply_text("⏳ Your access is pending admin approval.")
        return

    if context.user_data.get('awaiting_auto_reply'):
        await process_auto_reply(update, context)
    elif context.user_data.get('awaiting_schedule'):
        await process_schedule(update, context)
    elif context.user_data.get('awaiting_send_message'):
        await process_send_message(update, context)
    elif context.user_data.get('awaiting_scrape'):
        await process_scrape(update, context)
    elif context.user_data.get('awaiting_broadcast_msg'):
        await process_broadcast_msg(update, context)
    else:
        await update.message.reply_text(
            "👋 Use /start for menu!",
            reply_markup=menu_ui.main_menu(is_admin=is_admin(user_id, broadcast_active=False))
        )

# ============ POST INIT ============

async def post_init(application: Application):
    await db.init_db()
    scheduler_manager.start_scheduler_job()
    await auto_start_users()
    asyncio.create_task(group_message_manager.start_group_message_job())
    print("✅ Bot initialized!")
    print("⏰ Scheduler running")
    print("📢 Group message job started")
    print("📡 Auto-start complete")

# ============ MAIN ============

async def login_in_progress_warning(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tell user login is in progress when they type any command mid-login."""
    await update.message.reply_text(
        "⚠️ *Login chal raha hai!*\n\n"
        "Pehle login complete karo.\n"
        "Beech mein commands kaam nahi karenge.\n\n"
        "➡️ Jo step pe ho woh complete karo, ya /cancel likho login band karne ke liye.",
        parse_mode='Markdown'
    )


def main():
    application = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    application.add_error_handler(error_handler)

    # Login conversation
    login_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(login_handler.start_login, pattern='^add_account$')],
        states={
            API_ID:    [MessageHandler(filters.TEXT & ~filters.COMMAND, login_handler.receive_api_id)],
            API_HASH:  [MessageHandler(filters.TEXT & ~filters.COMMAND, login_handler.receive_api_hash)],
            PHONE:     [MessageHandler(filters.TEXT & ~filters.COMMAND, login_handler.receive_phone)],
            OTP:       [MessageHandler(filters.TEXT & ~filters.COMMAND, login_handler.receive_otp)],
            PASSWORD:  [MessageHandler(filters.TEXT & ~filters.COMMAND, login_handler.receive_password)],
        },
        fallbacks=[
            CommandHandler('cancel', login_handler.cancel_login),
            CommandHandler('start', login_in_progress_warning),
            MessageHandler(filters.COMMAND, login_in_progress_warning),
        ],
        allow_reentry=False,
    )

    application.add_handler(CommandHandler('start', start))
    application.add_handler(login_conv)

    # Main navigation
    application.add_handler(CallbackQueryHandler(show_main_menu, pattern='^main_menu$'))
    application.add_handler(CallbackQueryHandler(send_message_handler, pattern='^send_message$'))
    application.add_handler(CallbackQueryHandler(multi_account_handler, pattern='^multi_account$'))
    application.add_handler(CallbackQueryHandler(view_accounts_handler, pattern='^view_accounts$'))

    application.add_handler(CallbackQueryHandler(schedule_handler, pattern='^schedule$'))
    application.add_handler(CallbackQueryHandler(schedule_time_handler, pattern='^schedule_time$'))
    application.add_handler(CallbackQueryHandler(my_schedules_handler, pattern='^my_schedules$'))

    application.add_handler(CallbackQueryHandler(auto_reply_menu_handler, pattern='^auto_reply$'))
    application.add_handler(CallbackQueryHandler(set_auto_reply_handler, pattern='^set_auto_reply$'))
    application.add_handler(CallbackQueryHandler(delete_auto_reply_handler, pattern='^delete_auto_reply$'))

    application.add_handler(CallbackQueryHandler(scraper_handler, pattern='^scraper$'))
    application.add_handler(CallbackQueryHandler(scrape_members_handler, pattern='^scrape_members$'))

    application.add_handler(CallbackQueryHandler(analytics_handler, pattern='^analytics$'))
    application.add_handler(CallbackQueryHandler(sent_messages_handler, pattern='^sent_messages$'))
    application.add_handler(CallbackQueryHandler(status_handler, pattern='^status$'))
    application.add_handler(CallbackQueryHandler(logout_handler, pattern='^logout$'))

    # Group Messages — All Groups Broadcast
    application.add_handler(CallbackQueryHandler(group_messages_handler, pattern='^group_messages$'))
    application.add_handler(CallbackQueryHandler(gm_all_groups_handler, pattern='^gm_all_groups$'))
    application.add_handler(CallbackQueryHandler(gm_set_message_handler, pattern='^gm_set_message$'))
    application.add_handler(CallbackQueryHandler(gm_toggle_broadcast_handler, pattern='^gm_toggle_broadcast$'))
    application.add_handler(CallbackQueryHandler(gm_history_handler, pattern='^gm_history$'))
    application.add_handler(CallbackQueryHandler(main_bc_toggle_handler, pattern='^main_bc_toggle$'))

    # Admin panel
    application.add_handler(CallbackQueryHandler(admin_panel_handler, pattern='^admin_panel$'))
    application.add_handler(CallbackQueryHandler(admin_users_handler, pattern='^admin_users$'))
    application.add_handler(CallbackQueryHandler(admin_requests_handler, pattern='^admin_requests$'))
    application.add_handler(CallbackQueryHandler(admin_broadcast_all_handler, pattern='^admin_broadcast_all$'))
    application.add_handler(CallbackQueryHandler(admin_broadcast_approved_handler, pattern='^admin_broadcast_approved$'))
    application.add_handler(CallbackQueryHandler(admin_broadcast_unapproved_handler, pattern='^admin_broadcast_unapproved$'))
    application.add_handler(CallbackQueryHandler(admin_approve_handler, pattern='^admin_approve_'))
    application.add_handler(CallbackQueryHandler(admin_reject_handler, pattern='^admin_reject_'))

    # Noop (non-interactive buttons)
    application.add_handler(CallbackQueryHandler(noop_handler, pattern='^noop$'))

    # Text handler (must be last)
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE,
        handle_text_messages
    ))

    print("🚀 Starting bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
