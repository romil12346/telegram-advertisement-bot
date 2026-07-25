import json
from datetime import datetime, timedelta, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatMemberStatus
from telegram.ext import ContextTypes, ConversationHandler
from telegram.error import TelegramError
from .database import now_iso
from .keyboards import dashboard_keyboard, back_home, cancel_keyboard, ad_actions, language_keyboard
from .services import parse_buttons, send_ad, calculate_next_run, referral_code

AD_NAME, AD_CONTENT, AD_BUTTONS, CAMP_INTERVAL, CAMP_CHATS = range(5)

def is_private(update: Update) -> bool:
    return bool(update.effective_chat and update.effective_chat.type == "private")

async def get_language(db, user_id: int) -> str:
    row = await db.fetchone("SELECT language FROM users WHERE user_id=?", (user_id,))
    return (row or {}).get("language", "en")

async def dashboard_stats(db, user_id: int) -> dict:
    ads = await db.fetchone("SELECT COUNT(*) n FROM ads WHERE owner_user_id=?", (user_id,))
    campaigns = await db.fetchone(
        "SELECT COUNT(*) n FROM campaigns WHERE owner_user_id=? AND status='active'", (user_id,)
    )
    chats = await db.fetchone(
        "SELECT COUNT(*) n FROM chats WHERE owner_user_id=? AND is_active=1 AND bot_can_post=1", (user_id,)
    )
    sent = await db.fetchone(
        """SELECT COUNT(*) n FROM deliveries d
           JOIN campaigns c ON c.id=d.campaign_id
           WHERE c.owner_user_id=? AND d.status='success'""", (user_id,)
    )
    return {
        "ads": (ads or {}).get("n", 0),
        "campaigns": (campaigns or {}).get("n", 0),
        "chats": (chats or {}).get("n", 0),
        "sent": (sent or {}).get("n", 0),
    }

async def admin_status(db, user_id: int, owner_id: int) -> bool:
    if user_id == owner_id:
        return True
    return bool(await db.fetchone("SELECT 1 FROM admins WHERE user_id=?", (user_id,)))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = context.application.bot_data["db"]
    cfg = context.application.bot_data["config"]
    user = update.effective_user
    await db.upsert_user(user)

    if context.args and context.args[0].startswith("ref_"):
        try:
            referrer = int(context.args[0].split("_", 1)[1])
            if referrer != user.id:
                await db.execute(
                    "INSERT OR IGNORE INTO referrals(referrer_id,referred_id,created_at) VALUES(?,?,?)",
                    (referrer, user.id, now_iso()),
                )
        except ValueError:
            pass

    lang = await get_language(db, user.id)
    stats = await dashboard_stats(db, user.id)
    admin = await admin_status(db, user.id, cfg.owner_id)

    if lang == "hi":
        text = (
            "╭━━━━━━━━━━━━━━━━━━━━╮\\n"
            "   🚀 <b>PRACHARIKA CONTROL</b>\\n"
            "╰━━━━━━━━━━━━━━━━━━━━╯\\n\\n"
            f"नमस्ते <b>{user.first_name}</b> 👋\\n"
            "आपका स्मार्ट Telegram विज्ञापन डैशबोर्ड तैयार है।\\n\\n"
            "📌 <b>आज की स्थिति</b>\\n"
            f"├ 📢 कुल विज्ञापन: <b>{stats['ads']}</b>\\n"
            f"├ 🗓 सक्रिय अभियान: <b>{stats['campaigns']}</b>\\n"
            f"├ 👥 जुड़े समूह/चैनल: <b>{stats['chats']}</b>\\n"
            f"└ ✅ सफल पोस्ट: <b>{stats['sent']}</b>\\n\\n"
            "नीचे से अपनी कार्रवाई चुनें 👇"
        )
    else:
        text = (
            "╭━━━━━━━━━━━━━━━━━━━━╮\\n"
            "   🚀 <b>PRACHARIKA CONTROL</b>\\n"
            "╰━━━━━━━━━━━━━━━━━━━━╯\\n\\n"
            f"Welcome, <b>{user.first_name}</b> 👋\\n"
            "Your smart Telegram advertising workspace is ready.\\n\\n"
            "📌 <b>Account Overview</b>\\n"
            f"├ 📢 Total advertisements: <b>{stats['ads']}</b>\\n"
            f"├ 🗓 Active campaigns: <b>{stats['campaigns']}</b>\\n"
            f"├ 👥 Connected chats: <b>{stats['chats']}</b>\\n"
            f"└ ✅ Successful posts: <b>{stats['sent']}</b>\\n\\n"
            "Choose an action below 👇"
        )

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            text, parse_mode="HTML", reply_markup=dashboard_keyboard(admin, lang)
        )
    else:
        await update.effective_message.reply_text(
            text, parse_mode="HTML", reply_markup=dashboard_keyboard(admin, lang)
        )

async def language_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = context.application.bot_data["db"]
    lang = await get_language(db, update.effective_user.id)
    text = (
        "🌐 <b>भाषा चुनें / Choose Language</b>\\n\\n"
        "आप कभी भी अपनी पसंद की भाषा बदल सकते हैं।\\n"
        "You can change your preferred language anytime."
    )
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        text, parse_mode="HTML", reply_markup=language_keyboard(lang)
    )

async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = context.application.bot_data["db"]
    lang = update.callback_query.data.split(":", 1)[1]
    if lang not in {"hi", "en"}:
        lang = "en"
    await db.execute("UPDATE users SET language=? WHERE user_id=?", (lang, update.effective_user.id))
    await update.callback_query.answer("भाषा बदल दी गई ✅" if lang == "hi" else "Language updated ✅")
    await start(update, context)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        "<b>Commands</b>\n"
        "/newad – create advertisement\n/myads – list advertisements\n"
        "/groups – connected chats\n/analytics – statistics\n/plans – plans\n"
        "/connect – connect current group/channel\n/cancel – cancel operation",
        parse_mode="HTML", reply_markup=back_home(),
    )

async def connect_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        await update.effective_message.reply_text("Use /connect inside the group or channel.")
        return
    db = context.application.bot_data["db"]
    user = update.effective_user
    await db.upsert_user(user)
    try:
        member = await context.bot.get_chat_member(update.effective_chat.id, context.bot.id)
        can_post = member.status == ChatMemberStatus.ADMINISTRATOR and (
            getattr(member, "can_post_messages", False) or update.effective_chat.type != "channel"
        )
        can_delete = member.status == ChatMemberStatus.ADMINISTRATOR and getattr(member, "can_delete_messages", False)
        if not can_post:
            await update.effective_message.reply_text(
                "❌ Please promote me as administrator with permission to post messages."
            )
            return
        chat = update.effective_chat
        await db.execute(
            """INSERT INTO chats(chat_id,owner_user_id,title,username,chat_type,is_active,
               bot_can_post,bot_can_delete,connected_at,last_checked_at)
               VALUES(?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(chat_id) DO UPDATE SET title=excluded.title,username=excluded.username,
               is_active=1,bot_can_post=excluded.bot_can_post,bot_can_delete=excluded.bot_can_delete,
               last_checked_at=excluded.last_checked_at""",
            (chat.id, user.id, chat.title or str(chat.id), chat.username, chat.type, 1,
             int(can_post), int(can_delete), now_iso(), now_iso()),
        )
        await db.log(user.id, "connect_chat", {"chat_id": chat.id})
        await update.effective_message.reply_text("✅ Chat connected successfully.")
    except TelegramError as e:
        await update.effective_message.reply_text(f"❌ Could not verify permissions: {e}")

async def new_ad_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_private(update):
        await update.effective_message.reply_text("Create advertisements in private chat with me.")
        return ConversationHandler.END
    context.user_data["new_ad"] = {}
    msg = "📝 Send a short name for this advertisement."
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(msg, reply_markup=cancel_keyboard())
    else:
        await update.effective_message.reply_text(msg, reply_markup=cancel_keyboard())
    return AD_NAME

async def new_ad_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_ad"]["name"] = update.effective_message.text[:80]
    await update.effective_message.reply_text(
        "📨 Now send the advertisement content.\n\n"
        "Supported: text, photo, video, GIF/animation, document or audio.",
        reply_markup=cancel_keyboard(),
    )
    return AD_CONTENT

async def new_ad_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = update.effective_message
    data = context.user_data["new_ad"]
    if m.photo:
        data.update(content_type="photo", file_id=m.photo[-1].file_id, caption=m.caption)
    elif m.video:
        data.update(content_type="video", file_id=m.video.file_id, caption=m.caption)
    elif m.animation:
        data.update(content_type="animation", file_id=m.animation.file_id, caption=m.caption)
    elif m.document:
        data.update(content_type="document", file_id=m.document.file_id, caption=m.caption)
    elif m.audio:
        data.update(content_type="audio", file_id=m.audio.file_id, caption=m.caption)
    elif m.text:
        data.update(content_type="text", text=m.text)
    else:
        await m.reply_text("Unsupported content. Send text or one supported media file.")
        return AD_CONTENT
    await m.reply_text(
        "🔗 Send buttons using this format:\n"
        "<code>Website|https://example.com; Support|https://t.me/example</code>\n\n"
        "Use a new line for a new button row. Send <code>skip</code> for no buttons.",
        parse_mode="HTML", reply_markup=cancel_keyboard(),
    )
    return AD_BUTTONS

async def new_ad_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = context.application.bot_data["db"]
    try:
        buttons = parse_buttons(update.effective_message.text)
    except ValueError as e:
        await update.effective_message.reply_text(f"❌ {e}\nPlease try again.")
        return AD_BUTTONS
    d = context.user_data["new_ad"]
    now = now_iso()
    ad_id = await db.execute(
        """INSERT INTO ads(owner_user_id,name,content_type,text,file_id,caption,buttons_json,
           status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)""",
        (update.effective_user.id, d["name"], d["content_type"], d.get("text"), d.get("file_id"),
         d.get("caption"), json.dumps(buttons), "draft", now, now),
    )
    await db.log(update.effective_user.id, "create_ad", {"ad_id": ad_id})
    await update.effective_message.reply_text(
        f"✅ Advertisement <b>#{ad_id}</b> created.",
        parse_mode="HTML", reply_markup=ad_actions(ad_id, "draft"),
    )
    context.user_data.pop("new_ad", None)
    return ConversationHandler.END

async def list_ads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = context.application.bot_data["db"]
    ads = await db.fetchall(
        "SELECT * FROM ads WHERE owner_user_id=? ORDER BY id DESC LIMIT 30",
        (update.effective_user.id,),
    )
    rows = [[InlineKeyboardButton(f"#{a['id']} • {a['name']} • {a['status']}",
                                  callback_data=f"ad:view:{a['id']}")] for a in ads]
    rows.append([InlineKeyboardButton("➕ Create Advertisement", callback_data="ad:new")])
    rows.append([InlineKeyboardButton("🏠 Home", callback_data="home")])
    text = "📢 <b>My Advertisements</b>\n\n" + (f"Total shown: {len(ads)}" if ads else "No advertisements yet.")
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, parse_mode="HTML",
                                                      reply_markup=InlineKeyboardMarkup(rows))
    else:
        await update.effective_message.reply_text(text, parse_mode="HTML",
                                                  reply_markup=InlineKeyboardMarkup(rows))

async def view_ad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    db = context.application.bot_data["db"]
    ad_id = int(q.data.rsplit(":", 1)[1])
    ad = await db.fetchone("SELECT * FROM ads WHERE id=? AND owner_user_id=?",
                           (ad_id, update.effective_user.id))
    await q.answer()
    if not ad:
        await q.edit_message_text("Advertisement not found.", reply_markup=back_home())
        return
    await q.edit_message_text(
        f"📢 <b>Advertisement #{ad_id}</b>\n\n"
        f"<b>Name:</b> {ad['name']}\n<b>Type:</b> {ad['content_type']}\n"
        f"<b>Status:</b> {ad['status']}\n"
        f"<b>Delete previous:</b> {'Yes' if ad['delete_previous'] else 'No'}",
        parse_mode="HTML", reply_markup=ad_actions(ad_id, ad["status"]),
    )

async def preview_ad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    db = context.application.bot_data["db"]
    ad_id = int(q.data.rsplit(":", 1)[1])
    ad = await db.fetchone("SELECT * FROM ads WHERE id=? AND owner_user_id=?",
                           (ad_id, update.effective_user.id))
    await q.answer("Preview sent")
    if ad:
        await send_ad(context.bot, update.effective_user.id, ad)

async def set_ad_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    _, action, raw_id = q.data.split(":")
    status = "active" if action == "activate" else "paused"
    db = context.application.bot_data["db"]
    await db.execute("UPDATE ads SET status=?,updated_at=? WHERE id=? AND owner_user_id=?",
                     (status, now_iso(), int(raw_id), update.effective_user.id))
    await q.answer(f"Advertisement {status}")
    q.data = f"ad:view:{raw_id}"
    await view_ad(update, context)

async def duplicate_ad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    db = context.application.bot_data["db"]
    ad_id = int(q.data.rsplit(":", 1)[1])
    ad = await db.fetchone("SELECT * FROM ads WHERE id=? AND owner_user_id=?",
                           (ad_id, update.effective_user.id))
    if not ad:
        await q.answer("Not found", show_alert=True)
        return
    now = now_iso()
    new_id = await db.execute(
        """INSERT INTO ads(owner_user_id,name,content_type,text,file_id,caption,parse_mode,
        buttons_json,status,delete_previous,created_at,updated_at)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
        (ad["owner_user_id"], ad["name"]+" Copy", ad["content_type"], ad["text"], ad["file_id"],
         ad["caption"], ad["parse_mode"], ad["buttons_json"], "draft", ad["delete_previous"], now, now),
    )
    await q.answer(f"Copied as #{new_id}", show_alert=True)

async def delete_ad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    db = context.application.bot_data["db"]
    ad_id = int(q.data.rsplit(":", 1)[1])
    used = await db.fetchone("SELECT 1 FROM campaigns WHERE ad_id=? LIMIT 1", (ad_id,))
    if used:
        await q.answer("Pause/delete its campaigns first.", show_alert=True)
        return
    await db.execute("DELETE FROM ads WHERE id=? AND owner_user_id=?",
                     (ad_id, update.effective_user.id))
    await q.answer("Deleted")
    await list_ads(update, context)

async def new_campaign_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    ad_id = int(q.data.rsplit(":", 1)[1])
    context.user_data["new_campaign"] = {"ad_id": ad_id}
    await q.answer()
    await q.edit_message_text(
        "⏱ Send the posting interval in minutes.\nMinimum: 2 minutes.",
        reply_markup=cancel_keyboard(),
    )
    return CAMP_INTERVAL

async def campaign_interval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        minutes = int(update.effective_message.text)
        if minutes < 2 or minutes > 43200:
            raise ValueError
    except ValueError:
        await update.effective_message.reply_text("Send a number between 2 and 43200.")
        return CAMP_INTERVAL
    context.user_data["new_campaign"]["interval"] = minutes
    db = context.application.bot_data["db"]
    chats = await db.fetchall(
        "SELECT * FROM chats WHERE owner_user_id=? AND is_active=1 AND bot_can_post=1",
        (update.effective_user.id,),
    )
    if not chats:
        await update.effective_message.reply_text(
            "No connected group/channel. Add me there as admin and send /connect.",
            reply_markup=back_home(),
        )
        return ConversationHandler.END
    rows = [[InlineKeyboardButton(c["title"], callback_data=f"campchat:{c['chat_id']}")] for c in chats[:40]]
    rows.append([InlineKeyboardButton("✅ Finish Selection", callback_data="campchat:finish")])
    context.user_data["new_campaign"]["selected"] = []
    await update.effective_message.reply_text(
        "Select one or more target chats, then tap Finish Selection.",
        reply_markup=InlineKeyboardMarkup(rows),
    )
    return CAMP_CHATS

async def campaign_chat_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    db = context.application.bot_data["db"]
    cfg = context.application.bot_data["config"]
    value = q.data.split(":", 1)[1]
    data = context.user_data.get("new_campaign")
    if not data:
        await q.answer("Session expired", show_alert=True)
        return ConversationHandler.END
    if value != "finish":
        cid = int(value)
        selected = data["selected"]
        if cid in selected:
            selected.remove(cid)
            await q.answer("Removed")
        else:
            selected.append(cid)
            await q.answer("Selected")
        return CAMP_CHATS
    if not data["selected"]:
        await q.answer("Select at least one chat.", show_alert=True)
        return CAMP_CHATS
    now = datetime.now(timezone.utc)
    next_run = now + timedelta(minutes=data["interval"])
    camp_id = await db.execute(
        """INSERT INTO campaigns(owner_user_id,ad_id,name,status,schedule_type,interval_minutes,
        timezone,next_run_at,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)""",
        (update.effective_user.id, data["ad_id"], f"Campaign for Ad #{data['ad_id']}",
         "active", "interval", data["interval"], cfg.timezone, next_run.isoformat(), now_iso(), now_iso()),
    )
    for cid in data["selected"]:
        await db.execute("INSERT INTO campaign_chats(campaign_id,chat_id) VALUES(?,?)", (camp_id, cid))
    await db.execute("UPDATE ads SET status='active',updated_at=? WHERE id=?", (now_iso(), data["ad_id"]))
    await db.log(update.effective_user.id, "create_campaign", {"campaign_id": camp_id})
    context.user_data.pop("new_campaign", None)
    await q.answer("Campaign activated")
    await q.edit_message_text(
        f"✅ Campaign <b>#{camp_id}</b> activated.\n"
        f"It will post every {data['interval']} minutes.",
        parse_mode="HTML", reply_markup=back_home(),
    )
    return ConversationHandler.END

async def list_campaigns(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = context.application.bot_data["db"]
    camps = await db.fetchall(
        "SELECT * FROM campaigns WHERE owner_user_id=? ORDER BY id DESC LIMIT 30",
        (update.effective_user.id,),
    )
    rows = []
    for c in camps:
        rows.append([
            InlineKeyboardButton(f"#{c['id']} {c['name'][:25]}", callback_data="noop"),
            InlineKeyboardButton("⏸" if c["status"] == "active" else "▶️",
                                 callback_data=f"camp:toggle:{c['id']}"),
        ])
    rows.append([InlineKeyboardButton("🏠 Home", callback_data="home")])
    text = "⏰ <b>Campaigns</b>\n\n" + (f"Total shown: {len(camps)}" if camps else "No campaigns yet.")
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, parse_mode="HTML",
                                                      reply_markup=InlineKeyboardMarkup(rows))
    else:
        await update.effective_message.reply_text(text, parse_mode="HTML",
                                                  reply_markup=InlineKeyboardMarkup(rows))

async def toggle_campaign(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    db = context.application.bot_data["db"]
    camp_id = int(q.data.rsplit(":", 1)[1])
    c = await db.fetchone("SELECT * FROM campaigns WHERE id=? AND owner_user_id=?",
                          (camp_id, update.effective_user.id))
    if not c:
        await q.answer("Not found", show_alert=True)
        return
    status = "paused" if c["status"] == "active" else "active"
    next_run = calculate_next_run(c).isoformat() if status == "active" else c.get("next_run_at")
    await db.execute("UPDATE campaigns SET status=?,next_run_at=?,updated_at=? WHERE id=?",
                     (status, next_run, now_iso(), camp_id))
    await q.answer(f"Campaign {status}")
    await list_campaigns(update, context)

async def list_chats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = context.application.bot_data["db"]
    chats = await db.fetchall("SELECT * FROM chats WHERE owner_user_id=? ORDER BY connected_at DESC",
                              (update.effective_user.id,))
    lines = ["👥 <b>Connected Groups & Channels</b>", ""]
    for c in chats[:40]:
        icon = "✅" if c["is_active"] and c["bot_can_post"] else "⚠️"
        lines.append(f"{icon} <b>{c['title']}</b> — <code>{c['chat_id']}</code>")
    if not chats:
        lines.append("No chats connected.\n\nAdd me as admin and send /connect there.")
    text = "\n".join(lines)
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, parse_mode="HTML", reply_markup=back_home())
    else:
        await update.effective_message.reply_text(text, parse_mode="HTML", reply_markup=back_home())

async def analytics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = context.application.bot_data["db"]
    uid = update.effective_user.id
    stats = await db.fetchone(
        """SELECT COUNT(*) total,
           SUM(CASE WHEN d.status='success' THEN 1 ELSE 0 END) successful,
           SUM(CASE WHEN d.status='failed' THEN 1 ELSE 0 END) failed
           FROM deliveries d JOIN campaigns c ON c.id=d.campaign_id
           WHERE c.owner_user_id=?""", (uid,)
    )
    groups = await db.fetchone("SELECT COUNT(*) n FROM chats WHERE owner_user_id=? AND is_active=1", (uid,))
    campaigns = await db.fetchone("SELECT COUNT(*) n FROM campaigns WHERE owner_user_id=? AND status='active'", (uid,))
    text = (
        "📊 <b>Analytics Dashboard</b>\n\n"
        f"👥 Active chats: <b>{groups['n']}</b>\n"
        f"⏰ Active campaigns: <b>{campaigns['n']}</b>\n"
        f"📨 Total deliveries: <b>{stats['total'] or 0}</b>\n"
        f"✅ Successful: <b>{stats['successful'] or 0}</b>\n"
        f"❌ Failed: <b>{stats['failed'] or 0}</b>\n\n"
        "Note: Telegram URL buttons open external URLs directly. Exact URL-click tracking "
        "requires a redirect-domain integration."
    )
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, parse_mode="HTML", reply_markup=back_home())
    else:
        await update.effective_message.reply_text(text, parse_mode="HTML", reply_markup=back_home())

async def plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = context.application.bot_data["db"]
    user = await db.fetchone("SELECT * FROM users WHERE user_id=?", (update.effective_user.id,))
    text = (
        "💳 <b>Subscription Plans</b>\n\n"
        "🆓 <b>Free</b> — 1 connected chat, basic scheduling\n"
        "⭐ <b>Basic</b> — 5 chats, media, buttons and reports\n"
        "💎 <b>Premium</b> — 25 chats, rotations, team access and advanced analytics\n"
        "🏢 <b>Business</b> — custom limits and priority support\n\n"
        f"Your current plan: <b>{(user or {}).get('plan', 'free').title()}</b>\n\n"
        "Payment approval can be managed manually by the owner. Never send sensitive "
        "banking credentials inside the bot."
    )
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, parse_mode="HTML", reply_markup=back_home())
    else:
        await update.effective_message.reply_text(text, parse_mode="HTML", reply_markup=back_home())

async def admin_home(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = context.application.bot_data["db"]
    cfg = context.application.bot_data["config"]
    if not await admin_status(db, update.effective_user.id, cfg.owner_id):
        if update.callback_query:
            await update.callback_query.answer("Access denied", show_alert=True)
        return
    users = await db.fetchone("SELECT COUNT(*) n FROM users")
    chats = await db.fetchone("SELECT COUNT(*) n FROM chats")
    deliveries = await db.fetchone("SELECT COUNT(*) n FROM deliveries")
    text = (
        "🛡 <b>Admin Panel</b>\n\n"
        f"👤 Users: <b>{users['n']}</b>\n"
        f"👥 Connected chats: <b>{chats['n']}</b>\n"
        f"📨 Delivery records: <b>{deliveries['n']}</b>\n\n"
        "<b>Owner commands</b>\n"
        "<code>/addadmin USER_ID</code>\n"
        "<code>/removeadmin USER_ID</code>\n"
        "<code>/setplan USER_ID premium DAYS</code>\n"
        "<code>/broadcast your message</code>"
    )
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, parse_mode="HTML", reply_markup=back_home())
    else:
        await update.effective_message.reply_text(text, parse_mode="HTML", reply_markup=back_home())

async def owner_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = context.application.bot_data["db"]
    cfg = context.application.bot_data["config"]
    if update.effective_user.id != cfg.owner_id:
        return
    cmd = update.effective_message.text.split()[0].split("@")[0]
    args = context.args
    try:
        if cmd == "/addadmin":
            uid = int(args[0])
            await db.execute(
                "INSERT OR REPLACE INTO admins(user_id,role,permissions_json,added_by,created_at) VALUES(?,?,?,?,?)",
                (uid, "manager", '["ads","groups","reports"]', cfg.owner_id, now_iso()),
            )
            result = f"✅ Admin {uid} added."
        elif cmd == "/removeadmin":
            uid = int(args[0])
            await db.execute("DELETE FROM admins WHERE user_id=?", (uid,))
            result = f"✅ Admin {uid} removed."
        elif cmd == "/setplan":
            uid, plan, days = int(args[0]), args[1].lower(), int(args[2])
            exp = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()
            await db.execute("UPDATE users SET plan=?,plan_expires_at=? WHERE user_id=?", (plan, exp, uid))
            result = f"✅ Plan updated for {uid}: {plan}, {days} days."
        elif cmd == "/broadcast":
            body = update.effective_message.text.partition(" ")[2]
            if not body:
                raise ValueError
            users = await db.fetchall("SELECT user_id FROM users")
            sent = 0
            for row in users:
                try:
                    await context.bot.send_message(row["user_id"], body)
                    sent += 1
                except Exception:
                    pass
            result = f"✅ Broadcast sent to {sent} users."
        else:
            return
    except (ValueError, IndexError):
        result = "❌ Invalid command format. Open /admin for examples."
    await update.effective_message.reply_text(result)

async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cfg = context.application.bot_data["config"]
    text = "🆘 <b>Support</b>\n\n"
    if cfg.support_username:
        text += f"Contact: @{cfg.support_username}"
    else:
        text += "Support username has not been configured yet."
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, parse_mode="HTML", reply_markup=back_home())
    else:
        await update.effective_message.reply_text(text, parse_mode="HTML", reply_markup=back_home())

async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "⚙️ <b>Settings</b>\n\n"
        "Current release supports persistent campaigns, interval scheduling, target selection, "
        "automatic retry, previous-message deletion and permission checks.\n\n"
        "Working hours, expiry, random delay and maximum-post columns are already included in "
        "the database and scheduler for advanced configuration."
    )
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, parse_mode="HTML", reply_markup=back_home())

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("Operation cancelled.", reply_markup=back_home())
    else:
        await update.effective_message.reply_text("Operation cancelled.", reply_markup=back_home())
    return ConversationHandler.END

async def noop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    import logging
    logging.getLogger(__name__).exception("Unhandled exception", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "⚠️ Something went wrong. Your saved data is safe. Please open /start and try again."
            )
        except Exception:
            pass
