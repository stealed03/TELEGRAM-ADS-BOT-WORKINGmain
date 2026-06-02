from database import db


class Analytics:

    async def get_user_stats(self, user_id):
        """Get comprehensive user statistics."""
        stats = await db.get_user_analytics(user_id)
        accounts = await db.get_all_accounts(user_id)

        return {
            **stats,
            'total_accounts': len(accounts),
            'active_accounts': len([a for a in accounts if a['is_active']]),
        }

    async def get_recent_activity(self, user_id, days=7):
        return await db.get_user_analytics(user_id)

    async def get_daily_stats(self, user_id, days=7):
        return await self.get_user_stats(user_id)


analytics = Analytics()
