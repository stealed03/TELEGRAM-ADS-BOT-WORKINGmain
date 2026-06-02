import os
from dotenv import load_dotenv

load_dotenv()

# Bot Configuration
BOT_TOKEN = os.getenv('BOT_TOKEN', 'YOUR_BOT_TOKEN')
ADMIN_IDS = list(map(int, os.getenv('ADMIN_IDS', '').split(','))) if os.getenv('ADMIN_IDS') else []

# Require admin approval to use bot
REQUIRE_ADMIN = os.getenv('REQUIRE_ADMIN', 'True').lower() == 'true'

# Database
DB_NAME = 'automation.db'

# Session Storage
SESSION_DIR = 'sessions/'
os.makedirs(SESSION_DIR, exist_ok=True)

# Escrow Configuration
ESCROW_TIMEOUT = 3600

# Helper functions
def is_admin(user_id):
    """Check if user is admin"""
    return user_id in ADMIN_IDS

def check_admin_access(user_id):
    """Check if user can access bot (admin bypasses approval requirement)"""
    if is_admin(user_id):
        return True
    if not REQUIRE_ADMIN:
        return True
    return False
    
