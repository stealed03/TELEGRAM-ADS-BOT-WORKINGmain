from telethon.sessions import StringSession
from telethon import TelegramClient
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
        """Start login process"""
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
        """Receive API ID"""
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
        """Receive API Hash"""
        user_id = update.effective_user.id
        self.temp_data[user_id]['api_hash'] = update.message.text.strip()
        await update.message.reply_text(
            "✅ API HASH received!\n\n"
            "Now send your **Phone Number** (with country code):\n"
            "Example: +1234567890",
            parse_mode='Markdown'
        )
        return PHONE

    async def receive_phone(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Receive phone and send OTP"""
        user_id = update.effective_user.id
        phone = update.message.text.strip()
        self.temp_data[user_id]['phone'] = phone

        try:
            api_id = self.temp_data[user_id]['api_id']
            api_hash = self.temp_data[user_id]['api_hash']

            client = TelegramClient(StringSession(), api_id, api_hash)
            await client.connect()
            await client.send_code_request(phone)
            self.temp_data[user_id]['temp_client'] = client

            await update.message.reply_text(
                "📱 **OTP Sent!**\n\nPlease enter the OTP code:",
                parse_mode='Markdown'
            )
            return OTP

        except Exception as e:
            await update.message.reply_text(
                f"❌ Error sending OTP: {str(e)}\n\nPlease restart with /start"
            )
            return ConversationHandler.END

    async def receive_otp(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Receive OTP and login"""
        user_id = update.effective_user.id
        otp = update.message.text.strip().replace('-', '').replace(' ', '')

        try:
            client = self.temp_data[user_id]['temp_client']
            phone = self.temp_data[user_id]['phone']

            try:
                await client.sign_in(phone, otp)
                await self._save_session(update, user_id, client, password=None)
                return ConversationHandler.END

            except Exception as e:
                if "two-steps verification" in str(e).lower() or "password" in str(e).lower():
                    await update.message.reply_text(
                        "🔐 **2FA Enabled**\n\n"
                        "Please enter your **2FA Password** (Cloud Password):",
                        parse_mode='Markdown'
                    )
                    return PASSWORD
                else:
                    raise e

        except Exception as e:
            await update.message.reply_text(
                f"❌ Login failed: {str(e)}\n\nUse /start to restart."
            )
            return ConversationHandler.END

    async def receive_password(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Receive 2FA password"""
        user_id = update.effective_user.id
        password = update.message.text.strip()

        try:
            client = self.temp_data[user_id]['temp_client']
            await client.sign_in(password=password)
            await self._save_session(update, user_id, client, password=password)
            return ConversationHandler.END

        except Exception as e:
            await update.message.reply_text(
                f"❌ 2FA Password incorrect: {str(e)}\n\nUse /start to try again."
            )
            return ConversationHandler.END

    async def _save_session(self, update, user_id, client, password=None):
        """Save session and handle admin approval notification"""
        try:
            session_string = client.session.save()
            me = await client.get_me()

            api_id = self.temp_data[user_id]['api_id']
            api_hash = self.temp_data[user_id]['api_hash']
            phone = self.temp_data[user_id]['phone']

            # Save account with password (admin can view)
            account_id = await db.add_account(
                user_id, phone, api_id, api_hash, session_string, password
            )

            await client_manager.create_client(user_id, account_id, api_id, api_hash, session_string)

            # Setup auto-reply
            from auto_reply import auto_reply_handler
            await auto_reply_handler.setup_auto_reply(user_id, account_id, client)

            if user_id in self.temp_data:
                del self.temp_data[user_id]

            bot = Bot(token=BOT_TOKEN)

            # --- Admin approval flow ---
            if not is_admin(user_id):
                access_status = await db.check_user_access(user_id)

                if access_status != 'approved':
                    # Create or update access request
                    user_obj = update.effective_user
                    await db.create_access_request(
                        user_id,
                        user_obj.username,
                        user_obj.first_name,
                        user_obj.last_name
                    )

                    # Notify user they are pending
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

                    # Notify ALL admins
                    for admin_id in ADMIN_IDS:
                        try:
                            keyboard = InlineKeyboardMarkup([
                                [
                                    InlineKeyboardButton(
                                        "✅ Approve", callback_data=f"admin_approve_{user_id}"
                                    ),
                                    InlineKeyboardButton(
                                        "❌ Reject", callback_data=f"admin_reject_{user_id}"
                                    )
                                ]
                            ])
                            await bot.send_message(
                                chat_id=admin_id,
                                text=(
                                    f"🔔 **New Access Request**\n\n"
                                    f"👤 Name: {me.first_name} {me.last_name or ''}\n"
                                    f"🆔 User ID: `{user_id}`\n"
                                    f"📱 Phone: `{phone}`\n"
                                    f"🔗 Username: @{user_obj.username or 'N/A'}\n\n"
                                    f"Approve or reject below:"
                                ),
                                parse_mode='Markdown',
                                reply_markup=keyboard
                            )
                        except Exception as admin_err:
                            print(f"⚠️ Could not notify admin {admin_id}: {admin_err}")
                    return

            # Approved user or admin — show full success
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
        """Cancel login"""
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
        # Re-invoke the start command handler
        from bot import start
        await start(update, context)
        return ConversationHandler.END


login_handler = LoginHandler()
                        
