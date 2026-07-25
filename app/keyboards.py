from telegram import InlineKeyboardButton, InlineKeyboardMarkup

TEXT = {
    "en": {
        "create": "➕ Create Advertisement",
        "ads": "📢 My Advertisements",
        "campaigns": "🗓 Campaign Manager",
        "groups": "👥 Groups & Channels",
        "analytics": "📊 Analytics",
        "subscription": "💎 Subscription",
        "settings": "⚙️ Settings",
        "support": "🆘 Help & Support",
        "language": "🌐 Language",
        "admin": "🛡 Admin Control",
        "home": "🏠 Dashboard",
    },
    "hi": {
        "create": "➕ विज्ञापन बनाएँ",
        "ads": "📢 मेरे विज्ञापन",
        "campaigns": "🗓 अभियान प्रबंधन",
        "groups": "👥 समूह और चैनल",
        "analytics": "📊 रिपोर्ट और आँकड़े",
        "subscription": "💎 सदस्यता",
        "settings": "⚙️ सेटिंग्स",
        "support": "🆘 सहायता",
        "language": "🌐 भाषा बदलें",
        "admin": "🛡 एडमिन नियंत्रण",
        "home": "🏠 डैशबोर्ड",
    },
}

def dashboard_keyboard(is_admin: bool = False, lang: str = "en") -> InlineKeyboardMarkup:
    t = TEXT.get(lang, TEXT["en"])
    rows = [
        [InlineKeyboardButton(t["create"], callback_data="ad:new")],
        [InlineKeyboardButton(t["ads"], callback_data="ad:list"),
         InlineKeyboardButton(t["campaigns"], callback_data="camp:list")],
        [InlineKeyboardButton(t["groups"], callback_data="chat:list"),
         InlineKeyboardButton(t["analytics"], callback_data="analytics")],
        [InlineKeyboardButton(t["subscription"], callback_data="plans"),
         InlineKeyboardButton(t["settings"], callback_data="settings")],
        [InlineKeyboardButton(t["language"], callback_data="language"),
         InlineKeyboardButton(t["support"], callback_data="support")],
    ]
    if is_admin:
        rows.append([InlineKeyboardButton(t["admin"], callback_data="admin:home")])
    return InlineKeyboardMarkup(rows)

def language_keyboard(lang: str = "en") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🇮🇳 हिंदी", callback_data="lang:hi"),
            InlineKeyboardButton("🇬🇧 English", callback_data="lang:en"),
        ],
        [InlineKeyboardButton(TEXT.get(lang, TEXT["en"])["home"], callback_data="home")]
    ])

def back_home(lang: str = "en") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(TEXT.get(lang, TEXT["en"])["home"], callback_data="home")]
    ])

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
