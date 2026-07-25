import aiosqlite
import json
from datetime import datetime, timezone
from typing import Any

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    full_name TEXT,
    plan TEXT NOT NULL DEFAULT 'free',
    plan_expires_at TEXT,
    trial_used INTEGER NOT NULL DEFAULT 0,
    referred_by INTEGER,
    created_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    language TEXT NOT NULL DEFAULT 'en'
);

CREATE TABLE IF NOT EXISTS admins (
    user_id INTEGER PRIMARY KEY,
    role TEXT NOT NULL,
    permissions_json TEXT NOT NULL DEFAULT '[]',
    added_by INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chats (
    chat_id INTEGER PRIMARY KEY,
    owner_user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    username TEXT,
    chat_type TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    bot_can_post INTEGER NOT NULL DEFAULT 0,
    bot_can_delete INTEGER NOT NULL DEFAULT 0,
    category TEXT NOT NULL DEFAULT 'General',
    connected_at TEXT NOT NULL,
    last_checked_at TEXT,
    FOREIGN KEY(owner_user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS ads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    content_type TEXT NOT NULL,
    text TEXT,
    file_id TEXT,
    caption TEXT,
    parse_mode TEXT NOT NULL DEFAULT 'HTML',
    buttons_json TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL DEFAULT 'draft',
    delete_previous INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(owner_user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS campaigns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_user_id INTEGER NOT NULL,
    ad_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'paused',
    schedule_type TEXT NOT NULL DEFAULT 'interval',
    interval_minutes INTEGER,
    run_at TEXT,
    working_start TEXT,
    working_end TEXT,
    timezone TEXT NOT NULL,
    max_posts INTEGER,
    posts_sent INTEGER NOT NULL DEFAULT 0,
    expires_at TEXT,
    random_delay_seconds INTEGER NOT NULL DEFAULT 0,
    next_run_at TEXT,
    last_run_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(owner_user_id) REFERENCES users(user_id),
    FOREIGN KEY(ad_id) REFERENCES ads(id)
);

CREATE TABLE IF NOT EXISTS campaign_chats (
    campaign_id INTEGER NOT NULL,
    chat_id INTEGER NOT NULL,
    last_message_id INTEGER,
    PRIMARY KEY(campaign_id, chat_id),
    FOREIGN KEY(campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE,
    FOREIGN KEY(chat_id) REFERENCES chats(chat_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS deliveries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id INTEGER NOT NULL,
    ad_id INTEGER NOT NULL,
    chat_id INTEGER NOT NULL,
    message_id INTEGER,
    status TEXT NOT NULL,
    error TEXT,
    delivered_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS button_clicks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ad_id INTEGER NOT NULL,
    campaign_id INTEGER,
    user_id INTEGER,
    button_index INTEGER NOT NULL,
    clicked_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS coupons (
    code TEXT PRIMARY KEY,
    plan TEXT NOT NULL,
    days INTEGER NOT NULL,
    max_uses INTEGER,
    uses INTEGER NOT NULL DEFAULT 0,
    expires_at TEXT,
    active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS coupon_redemptions (
    code TEXT NOT NULL,
    user_id INTEGER NOT NULL,
    redeemed_at TEXT NOT NULL,
    PRIMARY KEY(code, user_id)
);

CREATE TABLE IF NOT EXISTS referrals (
    referrer_id INTEGER NOT NULL,
    referred_id INTEGER PRIMARY KEY,
    reward_status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    actor_user_id INTEGER NOT NULL,
    action TEXT NOT NULL,
    details_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

class Database:
    def __init__(self, path: str):
        self.path = path

    async def init(self) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.executescript(SCHEMA)
            try:
                await db.execute("ALTER TABLE users ADD COLUMN language TEXT NOT NULL DEFAULT 'en'")
            except Exception:
                pass
            await db.commit()

    async def execute(self, sql: str, params: tuple = ()) -> int:
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute(sql, params)
            await db.commit()
            return cur.lastrowid

    async def fetchone(self, sql: str, params: tuple = ()) -> dict[str, Any] | None:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(sql, params)
            row = await cur.fetchone()
            return dict(row) if row else None

    async def fetchall(self, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(sql, params)
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

    async def upsert_user(self, user) -> None:
        now = now_iso()
        await self.execute(
            """INSERT INTO users(user_id, username, full_name, created_at, last_seen_at)
               VALUES(?,?,?,?,?)
               ON CONFLICT(user_id) DO UPDATE SET
               username=excluded.username, full_name=excluded.full_name,
               last_seen_at=excluded.last_seen_at""",
            (user.id, user.username, user.full_name, now, now),
        )

    async def log(self, actor_user_id: int, action: str, details: dict | None = None) -> None:
        await self.execute(
            "INSERT INTO audit_logs(actor_user_id,action,details_json,created_at) VALUES(?,?,?,?)",
            (actor_user_id, action, json.dumps(details or {}, ensure_ascii=False), now_iso()),
        )
