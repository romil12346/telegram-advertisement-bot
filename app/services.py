import json
import secrets
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError

def parse_buttons(raw: str) -> list[list[dict]]:
    """Format: Label|https://url ; Label2|https://url on each row."""
    raw = raw.strip()
    if not raw or raw.lower() in {"skip", "none", "no"}:
        return []
    rows = []
    for line in raw.splitlines():
        row = []
        for part in line.split(";"):
            if "|" not in part:
                raise ValueError("Each button must use Label|https://example.com")
            label, url = [x.strip() for x in part.split("|", 1)]
            if not label or not url.startswith(("https://", "http://", "tg://")):
                raise ValueError("Button URL must start with https://, http:// or tg://")
            row.append({"text": label[:64], "url": url})
        if row:
            rows.append(row[:8])
    return rows[:8]

def build_keyboard(buttons_json: str, ad_id: int | None = None, campaign_id: int | None = None):
    buttons = json.loads(buttons_json or "[]")
    if not buttons:
        return None
    rows = []
    for i, row in enumerate(buttons):
        out = []
        for j, b in enumerate(row):
            # Telegram URL buttons cannot report clicks directly. A redirect service
            # can later replace this URL; delivery analytics are still recorded.
            out.append(InlineKeyboardButton(b["text"], url=b["url"]))
        rows.append(out)
    return InlineKeyboardMarkup(rows)

async def send_ad(bot, chat_id: int, ad: dict):
    kb = build_keyboard(ad.get("buttons_json", "[]"), ad.get("id"))
    kind = ad["content_type"]
    if kind == "text":
        return await bot.send_message(
            chat_id=chat_id, text=ad.get("text") or " ", parse_mode=ad.get("parse_mode") or "HTML",
            reply_markup=kb, disable_web_page_preview=False,
        )
    method = {
        "photo": bot.send_photo,
        "video": bot.send_video,
        "animation": bot.send_animation,
        "document": bot.send_document,
        "audio": bot.send_audio,
    }.get(kind)
    if not method:
        raise ValueError(f"Unsupported content type: {kind}")
    kwargs = {
        "chat_id": chat_id,
        kind if kind != "animation" else "animation": ad["file_id"],
        "caption": ad.get("caption"),
        "parse_mode": ad.get("parse_mode") or "HTML",
        "reply_markup": kb,
    }
    return await method(**kwargs)

def calculate_next_run(campaign: dict, from_dt: datetime | None = None) -> datetime | None:
    now = from_dt or datetime.now(timezone.utc)
    if campaign["schedule_type"] == "once":
        if not campaign.get("run_at"):
            return None
        dt = datetime.fromisoformat(campaign["run_at"])
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    minutes = int(campaign.get("interval_minutes") or 60)
    return now + timedelta(minutes=max(2, minutes))

def within_working_hours(campaign: dict, at: datetime | None = None) -> bool:
    start = campaign.get("working_start")
    end = campaign.get("working_end")
    if not start or not end:
        return True
    tz = ZoneInfo(campaign.get("timezone") or "Asia/Kolkata")
    local = (at or datetime.now(timezone.utc)).astimezone(tz)
    current = local.strftime("%H:%M")
    if start <= end:
        return start <= current <= end
    return current >= start or current <= end

def referral_code(user_id: int) -> str:
    return f"ref_{user_id}"
