import os
from dotenv import load_dotenv

load_dotenv() 

class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:password@localhost/dbname")
    TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")
    ALLOWED_USERS = {int(id_.strip()) for id_ in os.getenv("ALLOWED_USER_IDS", "").split(",") if id_.strip()}