from telethon.tl.functions.channels import GetParticipantsRequest
from telethon.tl.types import ChannelParticipantsSearch
from database import db
from client_manager import client_manager

class Scraper:
    
    async def scrape_group_members(self, user_id, group_username, limit=1000):
        """Scrape members from a group"""
        try:
            account = await db.get_active_account(user_id)
            if not account:
                return {'success': False, 'error': 'No active account'}
            
            client = await client_manager.get_client(user_id, account['id'])
            if not client:
                client = await client_manager.create_client(
                    user_id, account['id'],
                    account['api_id'], account['api_hash'],
                    account['session_string']
                )
            
            # Get group entity
            group = await client.get_entity(group_username)
            
            members = []
            offset = 0
            
            while len(members) < limit:
                participants = await client(GetParticipantsRequest(
                    group,
                    ChannelParticipantsSearch(''),
                    offset,
                    100,
                    hash=0
                ))
                
                if not participants.users:
                    break
                
                for user in participants.users:
                    if not user.bot:
                        members.append({
                            'id': user.id,
                            'username': user.username,
                            'first_name': user.first_name,
                            'last_name': user.last_name,
                            'phone': user.phone
                        })
                
                offset += len(participants.users)
                
                if len(participants.users) < 100:
                    break
            
            return {
                'success': True,
                'members': members[:limit],
                'total': len(members)
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def scrape_message_replies(self, user_id, group_username, message_id, limit=100):
        """Scrape users who replied to a specific message"""
        try:
            account = await db.get_active_account(user_id)
            if not account:
                return {'success': False, 'error': 'No active account'}
            
            client = await client_manager.get_client(user_id, account['id'])
            if not client:
                client = await client_manager.create_client(
                    user_id, account['id'],
                    account['api_id'], account['api_hash'],
                    account['session_string']
                )
            
            # Get group and message
            group = await client.get_entity(group_username)
            
            # Get replies
            replies = await client.get_messages(
                group,
                reply_to=message_id,
                limit=limit
            )
            
            users = []
            seen_ids = set()
            
            for reply in replies:
                if reply.sender_id and reply.sender_id not in seen_ids:
                    sender = await reply.get_sender()
                    if not sender.bot:
                        users.append({
                            'id': sender.id,
                            'username': sender.username,
                            'first_name': sender.first_name,
                            'last_name': sender.last_name
                        })
                        seen_ids.add(sender.id)
            
            return {
                'success': True,
                'users': users,
                'total': len(users)
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def get_chat_messages(self, user_id, chat_username, limit=100):
        """Get recent messages from a chat"""
        try:
            account = await db.get_active_account(user_id)
            if not account:
                return {'success': False, 'error': 'No active account'}
            
            client = await client_manager.get_client(user_id, account['id'])
            if not client:
                client = await client_manager.create_client(
                    user_id, account['id'],
                    account['api_id'], account['api_hash'],
                    account['session_string']
                )
            
            messages = await client.get_messages(chat_username, limit=limit)
            
            message_list = []
            for msg in messages:
                message_list.append({
                    'id': msg.id,
                    'text': msg.text,
                    'sender_id': msg.sender_id,
                    'date': msg.date.isoformat()
                })
            
            return {
                'success': True,
                'messages': message_list,
                'total': len(message_list)
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}

scraper = Scraper()
