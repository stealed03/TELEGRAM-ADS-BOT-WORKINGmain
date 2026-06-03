from telethon.sessions import StringSession
from telethon import TelegramClient
from telethon.errors import (
    PhoneCodeExpiredError,
    PhoneCodeInvalidError,
    SessionPasswordNeededError,
    FloodWaitError,
    PhoneNumberBannedError,
    AuthKeyUnregisteredError,
)
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import ContextTypes, ConversationHandler
from database import db
from client_manager import client_manager
from config import BOT_TOKEN, ADMIN_IDS, is_admin

# Conversation states
API_ID, API_HASH, PHONE, OTP, PASSWORD = range(5)


class LoginHandler:
    def __init__(self):
        self.temp_data = {}

    async def start_login(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            "🔐 **Account Login Process**\n\n"
            "Please enter your **API ID**:\n\n"
            "📍 Get it from: https://my.telegram.org\n\n"
            "─────────────────\n"
            "❌ Beech mein rokna ho to: /cancel",
            parse_mode='Markdown'
        )
        self.temp_data[user_id] = {}
        return API_ID

    async def receive_api_id(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        try:
            api_id = int(update.message.text.strip())
            self.temp_data[user_id]['api_id'] = api_id
            await update.message.reply_text(
                "✅ API ID received!\n\nNow send your **API HASH**:",
                parse_mode='Markdown'
            )
            return API_HASH
        except ValueError:
            await update.message.reply_text("❌ Invalid API ID. Please send numbers only.")
            return API_ID

    async def receive_api_hash(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        self.temp_data[user_id]['api_hash'] = update.message.text.strip()
        await update.message.reply_text(
            "✅ API HASH received!\n\n"
            "Now send your **Phone Number** (with country code):\n"
            "Example: +1234567890",
            parse_mode='Markdown'
        )
        return PHONE

    async def _send_otp(self, user_id, phone):
        """Connect client and request OTP. Saves phone_code_hash for sign_in."""
        api_id = self.temp_data[user_id]['api_id']
        api_hash = self.temp_data[user_id]['api_hash']

        # Disconnect old client if exists
        old_client = self.temp_data[user_id].get('temp_client')
        if old_client:
            try:
                await old_client.disconnect()
            except Exception:
                pass

        client = TelegramClient(StringSession(), api_id, api_hash)
        await client.connect()

        # send_code_request returns SentCode object with phone_code_hash
        sent = await client.send_code_request(phone)
        self.temp_data[user_id]['temp_client'] = client
        self.temp_data[user_id]['phone_code_hash'] = sent.phone_code_hash
        return client

    async def receive_phone(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        phone = update.message.text.strip()
        self.temp_data[user_id]['phone'] = phone

        try:
            await self._send_otp(user_id, phone)
            await update.message.reply_text(
                "📱 **OTP Sent!**\n\n"
                "Telegram ne aapke number par code bheja hai.\n"
                "Telegram app kholo aur code enter karo:\n\n"
                "⚡ Code jaldi enter karo — sirf **2 minute** valid rehta hai!\n\n"
                "📌 Format: sirf numbers, e.g. `83734`",
                parse_mode='Markdown'
            )
            return OTP

        except FloodWaitError as e:
            await update.message.reply_text(
                f"⏳ **Flood Wait!**\n\n"
                f"Telegram ne temporarily block kiya hai.\n"
                f"**{e.seconds} seconds** baad dobara try karo.",
                parse_mode='Markdown'
            )
            return ConversationHandler.END
        except PhoneNumberBannedError:
            await update.message.reply_text(
                "❌ **Number Banned!**\n\nYe phone number Telegram par ban hai.",
                parse_mode='Markdown'
            )
            return ConversationHandler.END
        except Exception as e:
            await update.message.reply_text(
                f"❌ OTP send karne mein error:\n`{str(e)}`\n\n/start se restart karo.",
                parse_mode='Markdown'
            )
            return ConversationHandler.END

    async def receive_otp(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        otp = update.message.text.strip().replace('-', '').replace(' ', '')

        if user_id not in self.temp_data:
            await update.message.reply_text("❌ Session khatam ho gayi. /start se dobara shuru karo.")
            return ConversationHandler.END

        client = self.temp_data[user_id].get('temp_client')
        phone = self.temp_data[user_id].get('phone')
        phone_code_hash = self.temp_data[user_id].get('phone_code_hash')

        if not client or not phone or not phone_code_hash:
            await update.message.reply_text("❌ Session data missing. /start se dobara shuru karo.")
            return ConversationHandler.END

        try:
            # phone_code_hash pass karna zaroori hai — ye Telegram block prevent karta hai
            await client.sign_in(phone, otp, phone_code_hash=phone_code_hash)
            await self._save_session(update, user_id, client, password=None)
            return ConversationHandler.END

        except PhoneCodeExpiredError:
            try:
                await self._send_otp(user_id, phone)
                await update.message.reply_text(
                    "⏰ **OTP Expire Ho Gayi Thi!**\n\n"
                    "✅ **Naya OTP bhej diya gaya hai!**\n\n"
                    "Telegram app mein naya code dekho aur jaldi enter karo.\n"
                    "⚡ Abki baar 2 minute ke andar daalna!",
                    parse_mode='Markdown'
                )
                return OTP
            except Exception as resend_err:
                await update.message.reply_text(
                    f"❌ Naya OTP bhi send nahi hua:\n`{str(resend_err)}`\n\n/start se restart karo.",
                    parse_mode='Markdown'
                )
                return ConversationHandler.END

        except PhoneCodeInvalidError:
            await update.message.reply_text(
                "❌ **Galat OTP!**\n\n"
                "Code wrong hai. Telegram app mein sahi code dekho aur dobara enter karo.\n\n"
                "📌 Sirf numbers, e.g. `83734`",
                parse_mode='Markdown'
            )
            return OTP

        except SessionPasswordNeededError:
            await update.message.reply_text(
                "🔐 **2FA Enabled Hai!**\n\n"
                "Apna **Cloud Password** enter karo\n"
                "(jo Telegram Settings → Privacy → Two-Step Verification mein set kiya hai):",
                parse_mode='Markdown'
            )
            return PASSWORD

        except FloodWaitError as e:
            await update.message.reply_text(
                f"⏳ **Flood Wait!**\n\nBahut zyada attempts. **{e.seconds} seconds** baad dobara try karo.",
                parse_mode='Markdown'
            )
            return ConversationHandler.END

        except Exception as e:
            err = str(e)
            if "expired" in err.lower() or "signinrequest" in err.lower():
                try:
                    await self._send_otp(user_id, phone)
                    await update.message.reply_text(
                        "⏰ **Code Expire Ho Gaya!**\n\n✅ **Naya OTP bhej diya!** Jaldi enter karo.",
                        parse_mode='Markdown'
                    )
                    return OTP
                except Exception:
                    pass
            await update.message.reply_text(
                f"❌ Login failed:\n`{err}`\n\n/start se restart karo.",
                parse_mode='Markdown'
            )
            return ConversationHandler.END

    async def receive_password(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        password = update.message.text.strip()

        try:
            client = self.temp_data[user_id]['temp_client']
            await client.sign_in(password=password)
            await self._save_session(update, user_id, client, password=password)
            return ConversationHandler.END

        except Exception as e:
            err = str(e).lower()
            if "password" in err or "invalid" in err:
                await update.message.reply_text(
                    "❌ **Wrong Password!**\n\n2FA password galat hai. Dobara try karo:",
                    parse_mode='Markdown'
                )
                return PASSWORD
            await update.message.reply_text(
                f"❌ 2FA error:\n`{str(e)}`\n\n/start se try again.",
                parse_mode='Markdown'
            )
            return ConversationHandler.END

    async def _save_session(self, update, user_id, client, password=None):
        try:
            session_string = client.session.save()
            me = await client.get_me()

            api_id = self.temp_data[user_id]['api_id']
            api_hash = self.temp_data[user_id]['api_hash']
            phone = self.temp_data[user_id]['phone']

            account_id = await db.add_account(
                user_id, phone, api_id, api_hash, session_string, password
            )

            await client_manager.create_client(user_id, account_id, api_id, api_hash, session_string)

            from auto_reply import auto_reply_handler
            await auto_reply_handler.setup_auto_reply(user_id, account_id, client)

            if user_id in self.temp_data:
                del self.temp_data[user_id]

            bot = Bot(token=BOT_TOKEN)

            if not is_admin(user_id):
                access_status = await db.check_user_access(user_id)

                if access_status != 'approved':
                    user_obj = update.effective_user
                    await db.create_access_request(
                        user_id,
                        user_obj.username,
                        user_obj.first_name,
                        user_obj.last_name
                    )

                    await bot.send_message(
                        chat_id=user_id,
                        text=(
                            f"✅ **Account Linked Successfully!**\n\n"
                            f"👤 Name: {me.first_name}\n"
                            f"📱 Phone: {phone}\n\n"
                            f"⏳ **Awaiting Admin Approval**\n\n"
                            f"Your account is saved. You will be notified once an admin approves your access."
                        ),
                        parse_mode='Markdown'
                    )

                    for admin_id in ADMIN_IDS:
                        try:
                            keyboard = InlineKeyboardMarkup([[
                                InlineKeyboardButton("✅ Approve", callback_data=f"admin_approve_{user_id}"),
                                InlineKeyboardButton("❌ Reject", callback_data=f"admin_reject_{user_id}")
                            ]])
                            await bot.send_message(
                                chat_id=admin_id,
                                text=(
                                    f"🔔 **New Access Request**\n\n"
                                    f"👤 Name: {me.first_name} {me.last_name or ''}\n"
                                    f"🆔 User ID: `{user_id}`\n"
                                    f"📱 Phone: `{phone}`\n"
                                    f"🔗 Username: @{update.effective_user.username or 'N/A'}\n\n"
                                    f"Approve or reject below:"
                                ),
                                parse_mode='Markdown',
                                reply_markup=keyboard
                            )
                        except Exception as admin_err:
                            print(f"⚠️ Could not notify admin {admin_id}: {admin_err}")
                    return

            await bot.send_message(
                chat_id=user_id,
                text=(
                    f"✅ **Login Successful!**\n\n"
                    f"👤 Name: {me.first_name}\n"
                    f"📱 Phone: {phone}\n"
                    f"🆔 ID: {me.id}\n\n"
                    f"🎯 Features enabled:\n"
                    f"• ⚡ Instant messaging\n"
                    f"• ⏰ Scheduler (India time)\n"
                    f"• 📢 Group auto-messages\n"
                    f"• 🤖 Auto-reply (personal)\n\n"
                    f"Use /start to see menu."
                ),
                parse_mode='Markdown'
            )

            await db.log_action(user_id, 'account_added', {'phone': phone})
            print(f"✅ User {user_id} logged in as {phone}")

        except Exception as e:
            print(f"❌ Error saving session: {e}")

    async def cancel_login(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id in self.temp_data:
            if 'temp_client' in self.temp_data[user_id]:
                try:
                    await self.temp_data[user_id]['temp_client'].disconnect()
                except Exception:
                    pass
            del self.temp_data[user_id]
        await update.message.reply_text("❌ Login cancelled.")
        return ConversationHandler.END

    async def restart_login(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start mid-conversation: clean up and re-run start"""
        user_id = update.effective_user.id
        if user_id in self.temp_data:
            if 'temp_client' in self.temp_data[user_id]:
                try:
                    await self.temp_data[user_id]['temp_client'].disconnect()
                except Exception:
                    pass
            del self.temp_data[user_id]
        from bot import start
        await start(update, context)
        return ConversationHandler.END


login_handler = LoginHandler()
