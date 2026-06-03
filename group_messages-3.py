"""
group_messages.py — All Groups Broadcast
=========================================
- User sets message + interval once
- Bot sends to ALL joined groups on that interval
- ON/OFF toggle
- Full history logging (sent / failed per group)
- Crash-safe: FloodWait handled, each group in try/except, bot loop never dies
"""

import asyncio
from datetime import datetime, timedelta

from database import db
from client_manager import client_manager


async def fetch_all_joined_groups(client) -> list:
    """Return groups where the user can actually send messages.
    Skips: broadcast channels, groups where send_messages is restricted.
    """
    from telethon.tl.types import Channel, Chat, ChatBannedRights
    try:
        dialogs = await client.get_dialogs(limit=None)
    except Exception as e:
        print(f"Warning: get_dialogs failed: {e}")
        return []

    groups = []
    for dialog in dialogs:
        entity = dialog.entity

        if not isinstance(entity, (Channel, Chat)):
            continue

        title = getattr(entity, 'title', str(entity.id))

        if isinstance(entity, Channel):
            # Broadcast channels — only admins post, skip
            if getattr(entity, 'broadcast', False):
                continue
            # User personally banned from sending
            banned: ChatBannedRights = getattr(entity, 'banned_rights', None)
            if banned and getattr(banned, 'send_messages', False):
                continue
            # Everyone banned by default and user is not admin
            default_banned: ChatBannedRights = getattr(entity, 'default_banned_rights', None)
            if default_banned and getattr(default_banned, 'send_messages', False):
                if not getattr(entity, 'admin_rights', None):
                    continue

        groups.append({'id': entity.id, 'title': title})

    return groups


class GroupMessageManager:
    def __init__(self):
        self.is_running = False

    async def _send_broadcast(self, config):
        """Send one broadcast round, fully crash-safe per group."""
        from telethon.errors import (
            FloodWaitError, ChatWriteForbiddenError,
            UserBannedInChannelError, ChannelPrivateError,
            SlowModeWaitError, PeerFloodError,
        )

        user_id = config['user_id']
        message = config['message']

        try:
            client = await client_manager.get_client(user_id, config['account_id'])
            if not client or not client.is_connected():
                print(f"Client not ready for user {user_id}, skipping")
                return
        except Exception as e:
            print(f"get_client failed for user {user_id}: {e}")
            return

        try:
            groups = await fetch_all_joined_groups(client)
        except Exception as e:
            print(f"fetch_groups failed for user {user_id}: {e}")
            return

        if not groups:
            print(f"No groups found for user {user_id}")
            return

        sent = 0
        failed = 0

        for group in groups:
            gid = group['id']
            gtitle = group['title']
            try:
                await client.send_message(gid, message)
                await db.log_broadcast(user_id, gid, gtitle, status='sent')
                sent += 1
                await asyncio.sleep(2)  # flood protection delay

            except FloodWaitError as e:
                wait = e.seconds
                print(f"FloodWait {wait}s for user {user_id}")
                await db.log_broadcast(user_id, gid, gtitle, status='failed',
                                       error=f'FloodWait {wait}s')
                failed += 1
                await asyncio.sleep(min(wait, 300))

            except (ChatWriteForbiddenError, UserBannedInChannelError,
                    ChannelPrivateError) as e:
                await db.log_broadcast(user_id, gid, gtitle, status='failed',
                                       error=type(e).__name__)
                failed += 1

            except SlowModeWaitError as e:
                await db.log_broadcast(user_id, gid, gtitle, status='failed',
                                       error=f'SlowMode {e.seconds}s')
                failed += 1

            except PeerFloodError:
                await db.log_broadcast(user_id, gid, gtitle, status='failed',
                                       error='PeerFlood - stopped')
                failed += 1
                print(f"PeerFlood for user {user_id}, stopping round")
                break

            except Exception as e:
                err_msg = str(e)[:100]
                await db.log_broadcast(user_id, gid, gtitle, status='failed', error=err_msg)
                failed += 1
                print(f"Group {gtitle}: {err_msg}")

        await db.update_broadcast_last_sent(user_id)
        print(f"Broadcast done: {sent} sent / {failed} failed / {len(groups)} total")

    async def check_and_send_broadcasts(self):
        try:
            active_broadcasts = await db.get_all_active_broadcasts()
        except Exception as e:
            print(f"get_all_active_broadcasts error: {e}")
            return

        for config in active_broadcasts:
            try:
                if config['last_sent']:
                    last_sent = datetime.fromisoformat(config['last_sent'])
                    next_send = last_sent + timedelta(minutes=int(config['interval_minutes']))
                    if datetime.now() < next_send:
                        continue
                await self._send_broadcast(config)
            except Exception as e:
                print(f"Broadcast error user {config.get('user_id')}: {e}")

    async def start_group_message_job(self):
        """Background loop - never crashes."""
        self.is_running = True
        print("Group broadcast job started (60s poll)")
        while self.is_running:
            try:
                await self.check_and_send_broadcasts()
            except Exception as e:
                print(f"Fatal broadcast job error (recovered): {e}")
            await asyncio.sleep(60)


group_message_manager = GroupMessageManager()


# ============ FORWARD MESSAGE MANAGER ============

class ForwardMessageManager:
    """Forwards a saved message (as-is, preserving premium emojis/media) to all groups."""

    def __init__(self):
        self.is_running = False

    async def _forward_broadcast(self, config):
        """Forward message to all sendable groups — crash-safe per group."""
        from telethon.errors import (
            FloodWaitError, ChatWriteForbiddenError,
            UserBannedInChannelError, ChannelPrivateError,
            SlowModeWaitError, PeerFloodError,
            MessageIdInvalidError,
        )

        user_id = config['user_id']
        source_chat_id = config['source_chat_id']
        message_id = config['message_id']
        forward_text = config.get('forward_text', '')
        is_original_source = bool(config.get('is_original_source', 0))

        try:
            client = await client_manager.get_client(user_id, config['account_id'])
            if not client or not client.is_connected():
                from database import db as _db
                account = await _db.get_active_account(user_id)
                if account:
                    client = await client_manager.create_client(
                        user_id, account['id'],
                        account['api_id'], account['api_hash'],
                        account['session_string']
                    )
                if not client or not client.is_connected():
                    print(f"[Forward] Client not ready for user {user_id}, skipping")
                    return
        except Exception as e:
            print(f"[Forward] get_client failed for user {user_id}: {e}")
            return

        try:
            groups = await fetch_all_joined_groups(client)
        except Exception as e:
            print(f"[Forward] fetch_groups failed for user {user_id}: {e}")
            return

        if not groups:
            print(f"[Forward] No groups found for user {user_id}")
            return

        sent = 0
        failed = 0

        for group in groups:
            gid = group['id']
            gtitle = group['title']
            try:
                if is_original_source:
                    # Original channel/group source — proper forward (preserves premium emojis)
                    await client.forward_messages(
                        entity=gid,
                        messages=message_id,
                        from_peer=source_chat_id
                    )
                else:
                    # Fallback — send the text/caption as new message
                    if forward_text:
                        await client.send_message(gid, forward_text)
                    else:
                        # No text — skip, nothing to send
                        print(f"[Forward] No text to send for user {user_id}, skipping group {gtitle}")
                        failed += 1
                        continue

                sent += 1
                await asyncio.sleep(2)  # flood protection

            except FloodWaitError as e:
                wait = e.seconds
                print(f"[Forward] FloodWait {wait}s for user {user_id}")
                failed += 1
                await asyncio.sleep(min(wait, 300))

            except MessageIdInvalidError:
                print(f"[Forward] Message no longer valid for user {user_id}")
                failed += 1
                break

            except (ChatWriteForbiddenError, UserBannedInChannelError, ChannelPrivateError):
                failed += 1

            except SlowModeWaitError:
                failed += 1

            except PeerFloodError:
                print(f"[Forward] PeerFlood for user {user_id}, stopping round")
                failed += 1
                break

            except Exception as e:
                err_msg = str(e)[:100]
                failed += 1
                print(f"[Forward] Group {gtitle}: {err_msg}")

        from database import db as _db
        await _db.update_forward_last_sent(user_id)
        print(f"[Forward] Done: {sent} sent / {failed} failed / {len(groups)} total")

    async def check_and_send_forwards(self):
        from database import db as _db
        try:
            active_forwards = await _db.get_all_active_forwards()
        except Exception as e:
            print(f"[Forward] get_all_active_forwards error: {e}")
            return

        for config in active_forwards:
            try:
                if config['last_sent']:
                    last_sent = datetime.fromisoformat(config['last_sent'])
                    next_send = last_sent + timedelta(minutes=int(config['interval_minutes']))
                    if datetime.now() < next_send:
                        continue
                await self._forward_broadcast(config)
            except Exception as e:
                print(f"[Forward] Error user {config.get('user_id')}: {e}")

    async def start_forward_job(self):
        """Background loop — never crashes."""
        self.is_running = True
        print("[Forward] Forward job started (60s poll)")
        while self.is_running:
            try:
                await self.check_and_send_forwards()
            except Exception as e:
                print(f"[Forward] Fatal error (recovered): {e}")
            await asyncio.sleep(60)


forward_message_manager = ForwardMessageManager()
