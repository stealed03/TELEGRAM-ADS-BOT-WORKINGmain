from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
from database import db
from messaging import message_sender
import pytz

class SchedulerManager:
    def __init__(self):
        self.scheduler = AsyncIOScheduler(timezone=pytz.timezone('Asia/Kolkata'))
        self.scheduler.start()
        self.is_running = False
    
    async def check_and_send_scheduled(self):
        """Check and send scheduled messages"""
        try:
            due_schedules = await db.get_due_schedules()
            
            for schedule in due_schedules:
                result = await message_sender.send_message(
                    schedule['user_id'],
                    schedule['target'],
                    schedule['message'],
                    schedule['account_id']
                )
                
                if result['success']:
                    if not schedule['is_recurring']:
                        await db.mark_schedule_sent(schedule['id'])
                    
                    await db.log_action(
                        schedule['user_id'],
                        'scheduled_message_sent',
                        {'target': schedule['target'], 'schedule_id': schedule['id']}
                    )
                    
                    print(f"✅ Scheduled message sent: {schedule['id']}")
        
        except Exception as e:
            print(f"❌ Scheduler error: {e}")
    
    def start_scheduler_job(self):
        """Start scheduler - checks every second"""
        if not self.is_running:
            self.scheduler.add_job(
                self.check_and_send_scheduled,
                'interval',
                seconds=1,
                id='check_schedules',
                replace_existing=True
            )
            self.is_running = True
            print("✅ Scheduler started (India timezone, 1s interval)")
    
    async def add_time_schedule(self, user_id, account_id, target, message, time_str):
        """Add schedule with HH:MM:SS format (India timezone)"""
        try:
            time_parts = time_str.split(':')
            hour = int(time_parts[0])
            minute = int(time_parts[1])
            second = int(time_parts[2]) if len(time_parts) > 2 else 0
            
            india_tz = pytz.timezone('Asia/Kolkata')
            now = datetime.now(india_tz)
            
            schedule_time = now.replace(hour=hour, minute=minute, second=second, microsecond=0)
            
            if schedule_time <= now:
                schedule_time += timedelta(days=1)
            
            schedule_time_utc = schedule_time.astimezone(pytz.UTC)
            
            schedule_id = await db.add_scheduled_message(
                user_id, account_id, target, message, schedule_time_utc, False, None
            )
            
            return {
                'success': True,
                'schedule_id': schedule_id,
                'scheduled_for': schedule_time.strftime('%Y-%m-%d %H:%M:%S IST')
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}

scheduler_manager = SchedulerManager()
