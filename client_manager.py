from telethon import TelegramClient
from telethon.sessions import StringSession
from config import SESSION_DIR
import asyncio

class ClientManager:
    def __init__(self):
        self.active_clients = {}  # {user_id: {account_id: TelegramClient}}
    
    async def create_client(self, user_id, account_id, api_id, api_hash, session_string=None):
        """Create or get existing Telethon client"""
        
        if user_id not in self.active_clients:
            self.active_clients[user_id] = {}
        
        # Check if client already exists and is connected
        if account_id in self.active_clients[user_id]:
            client = self.active_clients[user_id][account_id]
            if client.is_connected():
                return client
        
        # Create new client
        if session_string:
            session = StringSession(session_string)
        else:
            session = StringSession()
        
        client = TelegramClient(session, api_id, api_hash)
        await client.connect()
        
        self.active_clients[user_id][account_id] = client
        return client
    
    async def get_client(self, user_id, account_id):
        """Get active client"""
        if user_id in self.active_clients and account_id in self.active_clients[user_id]:
            return self.active_clients[user_id][account_id]
        return None
    
    async def remove_client(self, user_id, account_id):
        """Remove and disconnect client"""
        if user_id in self.active_clients and account_id in self.active_clients[user_id]:
            client = self.active_clients[user_id][account_id]
            await client.disconnect()
            del self.active_clients[user_id][account_id]
    
    async def get_session_string(self, client):
        """Get session string for persistence"""
        return client.session.save()
    
    def get_all_user_clients(self, user_id):
        """Get all clients for a user"""
        return self.active_clients.get(user_id, {})

client_manager = ClientManager()
