from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def dashboard_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton("➕ Create Advertisement", callback_data="ad:new"),
         InlineKeyboardButton("📢 My Ads", callback_data="ad:list")],
        [InlineKeyboardButton("⏰ Campaigns", callback_data="camp:list"),
         InlineKeyboardButton("👥 My Groups", callback_data="chat:list")],
        [InlineKeyboardButton("📊 Analytics", callback_data="analytics"),
         InlineKeyboardButton("💳 Subscription", callback_data="plans")],
        [InlineKeyboardButton("⚙️ Settings", callback_data="settings"),
         InlineKeyboardButton("🆘 Support", callback_data="support")],
    ]
    if is_admin:
        rows.append([InlineKeyboardButton("🛡 Admin Panel", callback_data="admin:home")])
    return InlineKeyboardMarkup(rows)

def back_home() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Home", callback_data="home")]])

def cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="cancel")]])

def ad_actions(ad_id: int, status: str) -> InlineKeyboardMarkup:
    toggle = ("▶️ Activate", f"ad:activate:{ad_id}") if status != "active" else ("⏸ Pause", f"ad:pause:{ad_id}")
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👁 Preview", callback_data=f"ad:preview:{ad_id}"),
         InlineKeyboardButton("✏️ Edit", callback_data=f"ad:edit:{ad_id}")],
        [InlineKeyboardButton(toggle[0], callback_data=toggle[1]),
         InlineKeyboardButton("📅 Create Campaign", callback_data=f"camp:new:{ad_id}")],
        [InlineKeyboardButton("📄 Duplicate", callback_data=f"ad:duplicate:{ad_id}"),
         InlineKeyboardButton("🗑 Delete", callback_data=f"ad:delete:{ad_id}")],
        [InlineKeyboardButton("⬅️ Back", callback_data="ad:list")],
    ])
