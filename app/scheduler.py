import asyncio
import random
from datetime import datetime, timedelta, timezone
from telegram.error import Forbidden, BadRequest, RetryAfter, TimedOut, NetworkError
from .database import now_iso
from .services import send_ad, calculate_next_run, within_working_hours

async def campaign_tick(context):
    db = context.application.bot_data["db"]
    now = datetime.now(timezone.utc)
    campaigns = await db.fetchall(
        """SELECT * FROM campaigns
           WHERE status='active' AND next_run_at IS NOT NULL AND next_run_at<=?""",
        (now.isoformat(),),
    )
    for campaign in campaigns:
        await run_campaign(context, campaign)

async def run_campaign(context, campaign: dict):
    db = context.application.bot_data["db"]
    now = datetime.now(timezone.utc)

    if campaign.get("expires_at"):
        exp = datetime.fromisoformat(campaign["expires_at"])
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if now >= exp:
            await db.execute("UPDATE campaigns SET status='completed',updated_at=? WHERE id=?",
                             (now_iso(), campaign["id"]))
            return

    if campaign.get("max_posts") and campaign["posts_sent"] >= campaign["max_posts"]:
        await db.execute("UPDATE campaigns SET status='completed',updated_at=? WHERE id=?",
                         (now_iso(), campaign["id"]))
        return

    if not within_working_hours(campaign, now):
        next_run = now + timedelta(minutes=15)
        await db.execute("UPDATE campaigns SET next_run_at=?,updated_at=? WHERE id=?",
                         (next_run.isoformat(), now_iso(), campaign["id"]))
        return

    if campaign.get("random_delay_seconds"):
        await asyncio.sleep(random.randint(0, min(campaign["random_delay_seconds"], 120)))

    ad = await db.fetchone("SELECT * FROM ads WHERE id=?", (campaign["ad_id"],))
    targets = await db.fetchall(
        """SELECT cc.*, c.is_active, c.bot_can_post
           FROM campaign_chats cc JOIN chats c ON c.chat_id=cc.chat_id
           WHERE cc.campaign_id=?""",
        (campaign["id"],),
    )

    success = 0
    for target in targets:
        if not target["is_active"] or not target["bot_can_post"]:
            continue
        try:
            if ad["delete_previous"] and target.get("last_message_id"):
                try:
                    await context.bot.delete_message(target["chat_id"], target["last_message_id"])
                except Exception:
                    pass
            msg = await send_ad(context.bot, target["chat_id"], ad)
            await db.execute(
                "UPDATE campaign_chats SET last_message_id=? WHERE campaign_id=? AND chat_id=?",
                (msg.message_id, campaign["id"], target["chat_id"]),
            )
            await db.execute(
                """INSERT INTO deliveries(campaign_id,ad_id,chat_id,message_id,status,error,delivered_at)
                   VALUES(?,?,?,?,?,?,?)""",
                (campaign["id"], ad["id"], target["chat_id"], msg.message_id, "success", None, now_iso()),
            )
            success += 1
        except RetryAfter as e:
            await asyncio.sleep(min(float(e.retry_after), 30))
        except (Forbidden, BadRequest) as e:
            await db.execute("UPDATE chats SET bot_can_post=0,last_checked_at=? WHERE chat_id=?",
                             (now_iso(), target["chat_id"]))
            await db.execute(
                """INSERT INTO deliveries(campaign_id,ad_id,chat_id,status,error,delivered_at)
                   VALUES(?,?,?,?,?,?)""",
                (campaign["id"], ad["id"], target["chat_id"], "failed", str(e)[:500], now_iso()),
            )
        except (TimedOut, NetworkError, Exception) as e:
            await db.execute(
                """INSERT INTO deliveries(campaign_id,ad_id,chat_id,status,error,delivered_at)
                   VALUES(?,?,?,?,?,?)""",
                (campaign["id"], ad["id"], target["chat_id"], "failed", str(e)[:500], now_iso()),
            )

    next_dt = calculate_next_run(campaign, now)
    new_status = "completed" if campaign["schedule_type"] == "once" else "active"
    await db.execute(
        """UPDATE campaigns SET posts_sent=posts_sent+?,last_run_at=?,next_run_at=?,
           status=?,updated_at=? WHERE id=?""",
        (success, now_iso(), next_dt.isoformat() if next_dt else None, new_status, now_iso(), campaign["id"]),
    )
