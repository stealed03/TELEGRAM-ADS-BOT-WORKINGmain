from telethon import TelegramClient
from telethon.errors import FloodWaitError, UserPrivacyRestrictedError
from database import db
from client_manager import client_manager
import asyncio

class MessageSender:
    
    async def send_message(self, user_id, target, message, account_id=None):
        """
        Send message from user account
        
        Args:
            user_id: Bot user ID
            target: Username, user ID, or group ID
            message: Message text
            account_id: Specific account ID (optional)
        """
        try:
            # Get account
            if account_id is None:
                account = await db.get_active_account(user_id)
            else:
                account = await db.get_active_account(user_id)
                if account['id'] != account_id:
                    accounts = await db.get_all_accounts(user_id)
                    account = next((acc for acc in accounts if acc['id'] == account_id), None)
            
            if not account:
                return {'success': False, 'error': 'No active account found'}
            
            # Get or create client
            client = await client_manager.get_client(user_id, account['id'])
            if not client:
                client = await client_manager.create_client(
                    user_id, account['id'], 
                    account['api_id'], account['api_hash'], 
                    account['session_string']
                )
            
            # Parse target
            if isinstance(target, str):
                if target.startswith('@'):
                    target = target[1:]
                elif target.startswith('+'):
                    # Phone number
                    pass
                elif target.isdigit() or (target.startswith('-') and target[1:].isdigit()):
                    # User/Chat ID
                    target = int(target)
            
            # Send message (NO DELAY)
            sent_message = await client.send_message(target, message)
            
            # Log message
            await db.log_sent_message(user_id, account['id'], str(target), message)
            
            return {
                'success': True,
                'message_id': sent_message.id,
                'chat_id': sent_message.chat_id
            }
            
        except FloodWaitError as e:
            return {'success': False, 'error': f'Flood wait: {e.seconds} seconds'}
        except UserPrivacyRestrictedError:
            return {'success': False, 'error': 'User privacy settings prevent messaging'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def send_to_multiple(self, user_id, targets, message, account_id=None):
        """Send message to multiple targets"""
        results = []
        
        for target in targets:
            result = await self.send_message(user_id, target, message, account_id)
            results.append({
                'target': target,
                'result': result
            })
            # Small delay between messages to different users
            await asyncio.sleep(0.1)
        
        return results
    
    async def get_chat_info(self, user_id, target, account_id=None):
        """Get information about a chat/user"""
        try:
            if account_id is None:
                account = await db.get_active_account(user_id)
            else:
                accounts = await db.get_all_accounts(user_id)
                account = next((acc for acc in accounts if acc['id'] == account_id), None)
            
            if not account:
                return None
            
            client = await client_manager.get_client(user_id, account['id'])
            if not client:
                client = await client_manager.create_client(
                    user_id, account['id'],
                    account['api_id'], account['api_hash'],
                    account['session_string']
                )
            
            entity = await client.get_entity(target)
            return entity
            
        except Exception as e:
            print(f"Error getting chat info: {e}")
            return None

message_sender = MessageSender()
