from database import db
from telethon import events

class AutoReplyHandler:
    
    async def setup_auto_reply(self, user_id, account_id, client):
        """Setup auto-reply for PERSONAL CHATS ONLY"""
        try:
            @client.on(events.NewMessage(incoming=True))
            async def handle_personal_message(event):
                try:
                    # ONLY PERSONAL CHATS
                    if event.is_group or event.is_channel:
                        return
                    
                    # Don't reply to self
                    me = await client.get_me()
                    if event.sender_id == me.id:
                        return
                    
                    auto_reply = await db.get_auto_reply(user_id, account_id)
                    
                    if not auto_reply:
                        return
                    
                    await event.respond(auto_reply['reply_text'])
                    
                    print(f"✅ Auto-reply sent to {event.sender_id}")
                    
                    await db.log_action(
                        user_id,
                        'auto_reply_sent',
                        {'chat_id': event.chat_id, 'sender': event.sender_id}
                    )
                
                except Exception as e:
                    print(f"❌ Auto-reply error: {e}")
            
            print(f"✅ Auto-reply setup for user {user_id}")
            
        except Exception as e:
            print(f"❌ Setup error: {e}")

auto_reply_handler = AutoReplyHandler()
