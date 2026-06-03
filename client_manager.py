from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import (
    SessionPasswordNeededError,
    AuthKeyUnregisteredError,
    AuthKeyInvalidError,
    UserDeactivatedBanError,
    PhoneNumberBannedError,
)
from config import SESSION_DIR
import asyncio
import aiosqlite

class ClientManager:
    def __init__(self):
        self.active_clients = {}  # {user_id: {account_id: TelegramClient}}

    async def create_client(self, user_id, account_id, api_id, api_hash, session_string=None):
        """Create or reconnect Telethon client. Handles session expiry gracefully."""

        if user_id not in self.active_clients:
            self.active_clients[user_id] = {}

        # Reuse if already connected and authorized
        if account_id in self.active_clients[user_id]:
            client = self.active_clients[user_id][account_id]
            try:
                if client.is_connected() and await client.is_user_authorized():
                    return client
            except Exception:
                pass  # stale client, recreate below

        try:
            session = StringSession(session_string) if session_string else StringSession()
            client = TelegramClient(session, api_id, api_hash)
            await client.connect()

            if not await client.is_user_authorized():
                # Session expired / revoked by Telegram
                print(f"⚠️ Session not authorized for user {user_id} account {account_id}")
                await client.disconnect()
                # Mark account as needing re-login in DB
                await self._mark_session_expired(user_id, account_id)
                return None

            self.active_clients[user_id][account_id] = client
            return client

        except (AuthKeyUnregisteredError, AuthKeyInvalidError):
            print(f"❌ Auth key invalid/unregistered for user {user_id} — session revoked by Telegram")
            await self._mark_session_expired(user_id, account_id)
            return None

        except (UserDeactivatedBanError, PhoneNumberBannedError) as e:
            print(f"❌ Account banned for user {user_id}: {e}")
            return None

        except Exception as e:
            print(f"❌ create_client error for user {user_id}: {e}")
            return None

    async def _mark_session_expired(self, user_id, account_id):
        """Mark account session as expired so user gets notified to re-login."""
        try:
            from config import DB_NAME
            async with aiosqlite.connect(DB_NAME) as db:
                await db.execute(
                    'UPDATE accounts SET session_string = NULL, is_active = 0 WHERE id = ? AND user_id = ?',
                    (account_id, user_id)
                )
                await db.commit()
        except Exception as e:
            print(f"⚠️ Could not mark session expired: {e}")

    async def get_client(self, user_id, account_id):
        """Get active client, auto-reconnect if disconnected."""
        if user_id in self.active_clients and account_id in self.active_clients[user_id]:
            client = self.active_clients[user_id][account_id]
            try:
                if not client.is_connected():
                    print(f"🔄 Reconnecting client for user {user_id}...")
                    await client.connect()
                if await client.is_user_authorized():
                    return client
                else:
                    print(f"⚠️ Client not authorized after reconnect for user {user_id}")
                    return None
            except Exception as e:
                print(f"⚠️ get_client reconnect error for user {user_id}: {e}")
                return None
        return None

    async def ensure_client(self, user_id, account_id, api_id, api_hash, session_string):
        """Get existing client OR create one — always returns a ready client or None."""
        client = await self.get_client(user_id, account_id)
        if client:
            return client
        return await self.create_client(user_id, account_id, api_id, api_hash, session_string)

    async def remove_client(self, user_id, account_id):
        """Remove and disconnect client."""
        if user_id in self.active_clients and account_id in self.active_clients[user_id]:
            client = self.active_clients[user_id][account_id]
            try:
                await client.disconnect()
            except Exception:
                pass
            del self.active_clients[user_id][account_id]

    async def get_session_string(self, client):
        """Get session string for persistence."""
        return client.session.save()

    def get_all_user_clients(self, user_id):
        """Get all clients for a user."""
        return self.active_clients.get(user_id, {})


client_manager = ClientManager()
