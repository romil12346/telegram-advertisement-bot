import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Config:
    bot_token: str
    owner_id: int
    database_path: str
    timezone: str
    support_username: str
    free_group_limit: int
    basic_group_limit: int
    premium_group_limit: int

def load_config() -> Config:
    token = os.getenv("BOT_TOKEN", "").strip()
    owner = os.getenv("OWNER_ID", "").strip()
    if not token:
        raise RuntimeError("BOT_TOKEN is missing.")
    if not owner.isdigit():
        raise RuntimeError("OWNER_ID must be a numeric Telegram user ID.")
    return Config(
        bot_token=token,
        owner_id=int(owner),
        database_path=os.getenv("DATABASE_PATH", "advertisement_bot.db"),
        timezone=os.getenv("BOT_TIMEZONE", "Asia/Kolkata"),
        support_username=os.getenv("SUPPORT_USERNAME", "").lstrip("@"),
        free_group_limit=int(os.getenv("FREE_GROUP_LIMIT", "1")),
        basic_group_limit=int(os.getenv("BASIC_GROUP_LIMIT", "5")),
        premium_group_limit=int(os.getenv("PREMIUM_GROUP_LIMIT", "25")),
    )
