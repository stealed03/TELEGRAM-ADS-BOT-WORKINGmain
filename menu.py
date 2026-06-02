from telegram import InlineKeyboardButton, InlineKeyboardMarkup


class MenuUI:

    @staticmethod
    def main_menu(is_admin=False, broadcast_active=False):
        """Main menu"""
        bc_label = "🔴 Broadcast OFF" if broadcast_active else "🟢 Broadcast ON"
        keyboard = [
            [
                InlineKeyboardButton("💬 Send Message", callback_data="send_message"),
                InlineKeyboardButton("🤖 Auto Reply", callback_data="auto_reply")
            ],
            [
                InlineKeyboardButton("⏰ Schedule", callback_data="schedule"),
                InlineKeyboardButton("📅 My Schedules", callback_data="my_schedules")
            ],
            [
                InlineKeyboardButton("👥 Multi-Account", callback_data="multi_account"),
                InlineKeyboardButton("📊 Analytics", callback_data="analytics")
            ],
            [
                InlineKeyboardButton("🔍 Scraper", callback_data="scraper"),
                InlineKeyboardButton("📢 Group Messages", callback_data="group_messages")
            ],
            [
                InlineKeyboardButton(bc_label, callback_data="main_bc_toggle"),
                InlineKeyboardButton("📜 BC History", callback_data="gm_history")
            ],
            [
                InlineKeyboardButton("📨 Sent Messages", callback_data="sent_messages"),
                InlineKeyboardButton("📈 Status", callback_data="status")
            ],
        ]

        if is_admin:
            keyboard.append([
                InlineKeyboardButton("🔐 Admin Panel", callback_data="admin_panel")
            ])

        keyboard.append([
            InlineKeyboardButton("🚪 Logout", callback_data="logout")
        ])

        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def admin_panel_menu():
        """Admin panel menu"""
        keyboard = [
            [
                InlineKeyboardButton("👥 All Users & Accounts", callback_data="admin_users"),
                InlineKeyboardButton("📝 Access Requests", callback_data="admin_requests")
            ],
            [
                InlineKeyboardButton("📢 Broadcast (All)", callback_data="admin_broadcast_all"),
                InlineKeyboardButton("📢 Broadcast (Approved)", callback_data="admin_broadcast_approved"),
            ],
            [
                InlineKeyboardButton("📢 Broadcast (Unapproved)", callback_data="admin_broadcast_unapproved"),
            ],
            [
                InlineKeyboardButton("« Back", callback_data="main_menu")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def group_messages_menu(is_active: bool = False):
        """Group auto messages main menu"""
        toggle_label = "🔴 Stop Broadcast (OFF)" if is_active else "🟢 Start Broadcast (ON)"
        keyboard = [
            [InlineKeyboardButton(toggle_label, callback_data="gm_toggle_broadcast")],
            [InlineKeyboardButton("📢 Message in All Groups (One-Time)", callback_data="gm_all_groups")],
            [InlineKeyboardButton("✏️ Set Message & Interval", callback_data="gm_set_message")],
            [InlineKeyboardButton("📜 Broadcast History", callback_data="gm_history")],
            [InlineKeyboardButton("« Back", callback_data="main_menu")]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def multi_account_menu():
        """Multi-account menu"""
        keyboard = [
            [
                InlineKeyboardButton("➕ Add Account", callback_data="add_account"),
                InlineKeyboardButton("📋 View Accounts", callback_data="view_accounts")
            ],
            [InlineKeyboardButton("🔄 Switch Account", callback_data="switch_account")],
            [InlineKeyboardButton("« Back", callback_data="main_menu")]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def scraper_menu():
        """Scraper menu"""
        keyboard = [
            [InlineKeyboardButton("👥 Scrape Members", callback_data="scrape_members")],
            [InlineKeyboardButton("« Back", callback_data="main_menu")]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def schedule_menu():
        """Schedule menu"""
        keyboard = [
            [InlineKeyboardButton("⏱️ Schedule Time (HH:MM:SS)", callback_data="schedule_time")],
            [InlineKeyboardButton("« Back", callback_data="main_menu")]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def auto_reply_menu():
        """Auto-reply menu"""
        keyboard = [
            [InlineKeyboardButton("➕ Set Message", callback_data="set_auto_reply")],
            [InlineKeyboardButton("🗑️ Remove", callback_data="delete_auto_reply")],
            [InlineKeyboardButton("« Back", callback_data="main_menu")]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def back_button():
        """Back to main menu button"""
        return InlineKeyboardMarkup([[
            InlineKeyboardButton("« Back to Menu", callback_data="main_menu")
        ]])



menu_ui = MenuUI()
