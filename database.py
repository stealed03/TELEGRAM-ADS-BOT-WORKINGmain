import aiosqlite
import json
from datetime import datetime
from config import DB_NAME

class Database:
    def __init__(self):
        self.db_name = DB_NAME

    async def init_db(self):
        async with aiosqlite.connect(self.db_name) as db:
            # Users table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Accounts table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    phone TEXT,
                    api_id INTEGER,
                    api_hash TEXT,
                    password TEXT,
                    session_string TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''')

            # Scheduled messages
            await db.execute('''
                CREATE TABLE IF NOT EXISTS scheduled_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    account_id INTEGER,
                    target TEXT,
                    message TEXT,
                    schedule_time TIMESTAMP,
                    is_recurring BOOLEAN DEFAULT 0,
                    recurring_pattern TEXT,
                    is_sent BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''')

            # Auto reply rules
            await db.execute('''
                CREATE TABLE IF NOT EXISTS auto_reply_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    account_id INTEGER,
                    reply_text TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''')

            # Bot settings
            await db.execute('''
                CREATE TABLE IF NOT EXISTS bot_settings (
                    user_id INTEGER PRIMARY KEY,
                    auto_start BOOLEAN DEFAULT 1,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''')

            # Sent messages log
            await db.execute('''
                CREATE TABLE IF NOT EXISTS sent_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    account_id INTEGER,
                    target TEXT,
                    message TEXT,
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''')

            # Analytics
            await db.execute('''
                CREATE TABLE IF NOT EXISTS analytics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    action_type TEXT,
                    details TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''')

            # Broadcasts
            await db.execute('''
                CREATE TABLE IF NOT EXISTS broadcasts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    admin_id INTEGER,
                    message TEXT,
                    total_users INTEGER,
                    sent_count INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Group auto messages
            await db.execute('''
                CREATE TABLE IF NOT EXISTS group_auto_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    account_id INTEGER,
                    group_id TEXT,
                    group_name TEXT,
                    message TEXT,
                    interval_minutes INTEGER,
                    last_sent TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''')

            # Access requests
            await db.execute('''
                CREATE TABLE IF NOT EXISTS access_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER UNIQUE,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    status TEXT DEFAULT 'pending',
                    requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    approved_at TIMESTAMP,
                    approved_by INTEGER,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''')

            # All-groups broadcast config (one row per user)
            await db.execute('''
                CREATE TABLE IF NOT EXISTS broadcast_config (
                    user_id INTEGER PRIMARY KEY,
                    account_id INTEGER,
                    message TEXT,
                    interval_minutes INTEGER DEFAULT 60,
                    is_active BOOLEAN DEFAULT 0,
                    last_sent TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''')

            # Broadcast send history — one row per group per broadcast round
            await db.execute('''
                CREATE TABLE IF NOT EXISTS broadcast_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    group_id INTEGER,
                    group_title TEXT,
                    status TEXT DEFAULT 'sent',
                    error TEXT,
                    sent_at TIMESTAMP DEFAULT (datetime('now')),
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''')

            await db.commit()

    # ============ USER OPERATIONS ============

    async def add_user(self, user_id, username=None, first_name=None, last_name=None):
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute(
                'INSERT OR REPLACE INTO users (user_id, username, first_name, last_name) VALUES (?, ?, ?, ?)',
                (user_id, username, first_name, last_name)
            )
            await db.commit()

    # ============ ACCOUNT OPERATIONS ============

    async def add_account(self, user_id, phone, api_id, api_hash, session_string, password=None):
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute(
                'UPDATE accounts SET is_active = 0 WHERE user_id = ?',
                (user_id,)
            )
            cursor = await db.execute(
                '''INSERT INTO accounts (user_id, phone, api_id, api_hash, password, session_string, is_active)
                   VALUES (?, ?, ?, ?, ?, ?, 1)''',
                (user_id, phone, api_id, api_hash, password, session_string)
            )
            await db.commit()
            return cursor.lastrowid

    async def get_active_account(self, user_id):
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                'SELECT * FROM accounts WHERE user_id = ? AND is_active = 1',
                (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def get_all_accounts(self, user_id):
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                'SELECT * FROM accounts WHERE user_id = ? ORDER BY created_at DESC',
                (user_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def set_active_account(self, user_id, account_id):
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute(
                'UPDATE accounts SET is_active = 0 WHERE user_id = ?',
                (user_id,)
            )
            await db.execute(
                'UPDATE accounts SET is_active = 1 WHERE id = ? AND user_id = ?',
                (account_id, user_id)
            )
            await db.commit()

    async def delete_account(self, account_id, user_id):
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute(
                'DELETE FROM accounts WHERE id = ? AND user_id = ?',
                (account_id, user_id)
            )
            await db.commit()

    # ============ SCHEDULED MESSAGES ============

    async def add_scheduled_message(self, user_id, account_id, target, message, schedule_time,
                                     is_recurring=False, recurring_pattern=None):
        async with aiosqlite.connect(self.db_name) as db:
            cursor = await db.execute(
                '''INSERT INTO scheduled_messages
                   (user_id, account_id, target, message, schedule_time, is_recurring, recurring_pattern)
                   VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (user_id, account_id, target, message, schedule_time, is_recurring, recurring_pattern)
            )
            await db.commit()
            return cursor.lastrowid

    async def get_pending_schedules(self, user_id):
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                '''SELECT * FROM scheduled_messages
                   WHERE user_id = ? AND is_sent = 0
                   ORDER BY schedule_time''',
                (user_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def get_due_schedules(self):
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                '''SELECT * FROM scheduled_messages
                   WHERE is_sent = 0 AND schedule_time <= datetime('now')'''
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def mark_schedule_sent(self, schedule_id):
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute(
                'UPDATE scheduled_messages SET is_sent = 1 WHERE id = ?',
                (schedule_id,)
            )
            await db.commit()

    async def delete_schedule(self, schedule_id, user_id):
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute(
                'DELETE FROM scheduled_messages WHERE id = ? AND user_id = ?',
                (schedule_id, user_id)
            )
            await db.commit()

    # ============ AUTO REPLY ============

    async def add_auto_reply(self, user_id, account_id, reply_text):
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute(
                'UPDATE auto_reply_rules SET is_active = 0 WHERE user_id = ? AND account_id = ?',
                (user_id, account_id)
            )
            cursor = await db.execute(
                '''INSERT INTO auto_reply_rules (user_id, account_id, reply_text)
                   VALUES (?, ?, ?)''',
                (user_id, account_id, reply_text)
            )
            await db.commit()
            return cursor.lastrowid

    async def get_auto_reply(self, user_id, account_id):
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                'SELECT * FROM auto_reply_rules WHERE user_id = ? AND account_id = ? AND is_active = 1',
                (user_id, account_id)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def delete_auto_reply(self, user_id, account_id):
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute(
                'DELETE FROM auto_reply_rules WHERE user_id = ? AND account_id = ?',
                (user_id, account_id)
            )
            await db.commit()

    # ============ BOT SETTINGS ============

    async def get_user_setting(self, user_id, setting_key):
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                f'SELECT {setting_key} FROM bot_settings WHERE user_id = ?',
                (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return row[setting_key] if row else True

    async def set_user_setting(self, user_id, setting_key, value):
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute(
                f'''INSERT INTO bot_settings (user_id, {setting_key})
                    VALUES (?, ?)
                    ON CONFLICT(user_id) DO UPDATE SET {setting_key} = ?''',
                (user_id, value, value)
            )
            await db.commit()

    # ============ SENT MESSAGES LOG ============

    async def log_sent_message(self, user_id, account_id, target, message):
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute(
                'INSERT INTO sent_messages (user_id, account_id, target, message) VALUES (?, ?, ?, ?)',
                (user_id, account_id, target, message)
            )
            await db.commit()

    async def get_sent_messages(self, user_id, limit=50):
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                'SELECT * FROM sent_messages WHERE user_id = ? ORDER BY sent_at DESC LIMIT ?',
                (user_id, limit)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    # ============ ANALYTICS ============

    async def log_action(self, user_id, action_type, details=None):
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute(
                'INSERT INTO analytics (user_id, action_type, details) VALUES (?, ?, ?)',
                (user_id, action_type, json.dumps(details) if details else None)
            )
            await db.commit()

    async def get_user_analytics(self, user_id):
        async with aiosqlite.connect(self.db_name) as db:
            async with db.execute(
                'SELECT COUNT(*) FROM sent_messages WHERE user_id = ?', (user_id,)
            ) as cursor:
                total_sent = (await cursor.fetchone())[0]
            async with db.execute(
                'SELECT COUNT(*) FROM scheduled_messages WHERE user_id = ? AND is_sent = 0', (user_id,)
            ) as cursor:
                active_schedules = (await cursor.fetchone())[0]
            async with db.execute(
                'SELECT COUNT(*) FROM auto_reply_rules WHERE user_id = ? AND is_active = 1', (user_id,)
            ) as cursor:
                active_replies = (await cursor.fetchone())[0]
            async with db.execute(
                'SELECT COUNT(*) FROM accounts WHERE user_id = ?', (user_id,)
            ) as cursor:
                total_accounts = (await cursor.fetchone())[0]
            async with db.execute(
                'SELECT COUNT(*) FROM accounts WHERE user_id = ? AND is_active = 1', (user_id,)
            ) as cursor:
                active_accounts = (await cursor.fetchone())[0]
            async with db.execute(
                'SELECT COUNT(*) FROM group_auto_messages WHERE user_id = ? AND is_active = 1', (user_id,)
            ) as cursor:
                active_group_messages = (await cursor.fetchone())[0]

            return {
                'total_sent': total_sent,
                'active_schedules': active_schedules,
                'active_auto_replies': active_replies,
                'total_accounts': total_accounts,
                'active_accounts': active_accounts,
                'active_group_messages': active_group_messages,
            }

    # ============ BROADCAST ============

    async def create_broadcast(self, admin_id, message, total_users):
        async with aiosqlite.connect(self.db_name) as db:
            cursor = await db.execute(
                'INSERT INTO broadcasts (admin_id, message, total_users) VALUES (?, ?, ?)',
                (admin_id, message, total_users)
            )
            await db.commit()
            return cursor.lastrowid

    async def update_broadcast_progress(self, broadcast_id, sent_count, status='sending'):
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute(
                'UPDATE broadcasts SET sent_count = ?, status = ? WHERE id = ?',
                (sent_count, status, broadcast_id)
            )
            await db.commit()

    async def get_all_user_ids(self):
        async with aiosqlite.connect(self.db_name) as db:
            async with db.execute('SELECT DISTINCT user_id FROM users') as cursor:
                rows = await cursor.fetchall()
                return [row[0] for row in rows]

    async def get_approved_user_ids(self):
        async with aiosqlite.connect(self.db_name) as db:
            async with db.execute(
                "SELECT DISTINCT user_id FROM access_requests WHERE status = 'approved'"
            ) as cursor:
                rows = await cursor.fetchall()
                return [row[0] for row in rows]

    async def get_unapproved_user_ids(self):
        async with aiosqlite.connect(self.db_name) as db:
            async with db.execute(
                "SELECT DISTINCT user_id FROM access_requests WHERE status = 'pending'"
            ) as cursor:
                rows = await cursor.fetchall()
                return [row[0] for row in rows]

    # ============ GROUP AUTO MESSAGES ============

    async def add_group_auto_message(self, user_id, account_id, group_id, group_name, message, interval_minutes):
        async with aiosqlite.connect(self.db_name) as db:
            # Upsert: if same group_id + user_id already exists, update it
            cursor = await db.execute(
                '''INSERT INTO group_auto_messages
                   (user_id, account_id, group_id, group_name, message, interval_minutes)
                   VALUES (?, ?, ?, ?, ?, ?)''',
                (user_id, account_id, str(group_id), group_name, message, interval_minutes)
            )
            await db.commit()
            return cursor.lastrowid

    async def get_user_group_messages(self, user_id):
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                'SELECT * FROM group_auto_messages WHERE user_id = ? AND is_active = 1',
                (user_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def get_all_active_group_messages(self):
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                'SELECT * FROM group_auto_messages WHERE is_active = 1'
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def update_group_message_last_sent(self, message_id):
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute(
                "UPDATE group_auto_messages SET last_sent = datetime('now') WHERE id = ?",
                (message_id,)
            )
            await db.commit()

    async def delete_group_auto_message(self, message_id, user_id):
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute(
                'DELETE FROM group_auto_messages WHERE id = ? AND user_id = ?',
                (message_id, user_id)
            )
            await db.commit()

    # ============ ACCESS REQUEST OPERATIONS ============

    async def create_access_request(self, user_id, username, first_name, last_name):
        async with aiosqlite.connect(self.db_name) as db:
            async with db.execute(
                'SELECT id, status FROM access_requests WHERE user_id = ?', (user_id,)
            ) as cursor:
                existing = await cursor.fetchone()

            if existing:
                if existing[1] == 'rejected':
                    await db.execute(
                        '''UPDATE access_requests
                           SET status = 'pending', requested_at = datetime('now'),
                               username = ?, first_name = ?, last_name = ?
                           WHERE user_id = ?''',
                        (username, first_name, last_name, user_id)
                    )
                    await db.commit()
                return existing[0]
            else:
                cursor = await db.execute(
                    '''INSERT INTO access_requests (user_id, username, first_name, last_name)
                       VALUES (?, ?, ?, ?)''',
                    (user_id, username, first_name, last_name)
                )
                await db.commit()
                return cursor.lastrowid

    async def get_pending_access_requests(self):
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM access_requests WHERE status = 'pending' ORDER BY requested_at DESC"
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def approve_access_request(self, user_id, admin_id):
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute(
                '''UPDATE access_requests
                   SET status = 'approved', approved_at = datetime('now'), approved_by = ?
                   WHERE user_id = ?''',
                (admin_id, user_id)
            )
            await db.commit()

    async def reject_access_request(self, user_id, admin_id):
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute(
                '''UPDATE access_requests
                   SET status = 'rejected', approved_at = datetime('now'), approved_by = ?
                   WHERE user_id = ?''',
                (admin_id, user_id)
            )
            await db.commit()

    async def check_user_access(self, user_id):
        """Returns: 'approved', 'pending', 'rejected', or None"""
        async with aiosqlite.connect(self.db_name) as db:
            async with db.execute(
                "SELECT status FROM access_requests WHERE user_id = ? ORDER BY requested_at DESC LIMIT 1",
                (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None

    # ============ ADMIN: VIEW ALL USERS WITH FULL ACCOUNT DETAILS ============

    async def get_all_users_with_accounts(self):
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                '''SELECT
                       u.user_id,
                       u.username,
                       u.first_name,
                       u.last_name,
                       a.id as account_id,
                       a.phone,
                       a.api_id,
                       a.api_hash,
                       a.password,
                       a.is_active,
                       a.created_at,
                       ar.status as access_status
                   FROM users u
                   LEFT JOIN accounts a ON u.user_id = a.user_id
                   LEFT JOIN access_requests ar ON u.user_id = ar.user_id
                   ORDER BY a.created_at DESC'''
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]


    # ============ BROADCAST CONFIG ============

    async def get_broadcast_config(self, user_id):
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                'SELECT * FROM broadcast_config WHERE user_id = ?', (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def set_broadcast_config(self, user_id, account_id, message, interval_minutes):
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute(
                '''INSERT INTO broadcast_config (user_id, account_id, message, interval_minutes, is_active)
                   VALUES (?, ?, ?, ?, 0)
                   ON CONFLICT(user_id) DO UPDATE SET
                       account_id=excluded.account_id,
                       message=excluded.message,
                       interval_minutes=excluded.interval_minutes''',
                (user_id, account_id, message, interval_minutes)
            )
            await db.commit()

    async def toggle_broadcast(self, user_id):
        """Flip is_active, return new state (True/False)."""
        async with aiosqlite.connect(self.db_name) as db:
            async with db.execute(
                'SELECT is_active FROM broadcast_config WHERE user_id = ?', (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
            if row is None:
                return False
            new_state = 0 if row[0] else 1
            await db.execute(
                'UPDATE broadcast_config SET is_active = ? WHERE user_id = ?',
                (new_state, user_id)
            )
            await db.commit()
            return bool(new_state)

    async def get_all_active_broadcasts(self):
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                'SELECT * FROM broadcast_config WHERE is_active = 1 AND message IS NOT NULL'
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def update_broadcast_last_sent(self, user_id):
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute(
                "UPDATE broadcast_config SET last_sent = datetime('now') WHERE user_id = ?",
                (user_id,)
            )
            await db.commit()

    async def log_broadcast(self, user_id, group_id, group_title, status='sent', error=None):
        """Log one group's broadcast result."""
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute(
                '''INSERT INTO broadcast_log (user_id, group_id, group_title, status, error)
                   VALUES (?, ?, ?, ?, ?)''',
                (user_id, group_id, group_title, status, error)
            )
            await db.commit()

    async def get_broadcast_history(self, user_id, limit=100):
        """Get last N broadcast log entries for a user."""
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                '''SELECT * FROM broadcast_log WHERE user_id = ?
                   ORDER BY sent_at DESC LIMIT ?''',
                (user_id, limit)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    async def get_broadcast_stats(self, user_id):
        """Get total sent/failed counts from last broadcast round."""
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            # last_sent time from config
            async with db.execute(
                'SELECT last_sent FROM broadcast_config WHERE user_id = ?', (user_id,)
            ) as cur:
                cfg = await cur.fetchone()
            if not cfg or not cfg['last_sent']:
                return {'sent': 0, 'failed': 0, 'total': 0, 'last_sent': None}
            last_sent = cfg['last_sent']
            async with db.execute(
                '''SELECT status, COUNT(*) as cnt FROM broadcast_log
                   WHERE user_id = ? AND sent_at >= ?
                   GROUP BY status''',
                (user_id, last_sent)
            ) as cur:
                rows = await cur.fetchall()
            stats = {'sent': 0, 'failed': 0, 'last_sent': last_sent}
            for r in rows:
                stats[r['status']] = r['cnt']
            stats['total'] = stats['sent'] + stats['failed']
            return stats

db = Database()
