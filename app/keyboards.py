from telegram import InlineKeyboardButton, InlineKeyboardMarkup

TEXT = {
    "en": {
        "create": "鉃� Create Advertisement",
        "ads": "馃摙 My Advertisements",
        "campaigns": "馃棑 Campaign Manager",
        "groups": "馃懃 Groups & Channels",
        "analytics": "馃搳 Analytics",
        "subscription": "馃拵 Subscription",
        "settings": "鈿欙笍 Settings",
        "support": "馃啒 Help & Support",
        "language": "馃寪 Language",
        "admin": "馃洝 Admin Control",
        "home": "馃彔 Dashboard",
    },
    "hi": {
        "create": "鉃� 啶掂た啶溹啶炧ぞ啶え 啶え啶距啶�",
        "ads": "馃摙 啶啶班 啶掂た啶溹啶炧ぞ啶え",
        "campaigns": "馃棑 啶呧き啶苦く啶距え 啶啶班が啶傕ぇ啶�",
        "groups": "馃懃 啶膏ぎ啷傕す 啶斷ぐ 啶氞啶ㄠげ",
        "analytics": "馃搳 啶班た啶啶班啶� 啶斷ぐ 啶嗋啶曕ぁ啶监",
        "subscription": "馃拵 啶膏う啶膏啶い啶�",
        "settings": "鈿欙笍 啶膏啶熰た啶傕啷嵿じ",
        "support": "馃啒 啶膏す啶距く啶むぞ",
        "language": "馃寪 啶ぞ啶粪ぞ 啶う啶侧啶�",
        "admin": "馃洝 啶忇ぁ啶た啶� 啶ㄠた啶啶む啶班ぃ",
        "home": "馃彔 啶∴啶多が啷嬥ぐ啷嵿ぁ",
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
            InlineKeyboardButton("馃嚠馃嚦 啶灌た啶傕う啷€", callback_data="lang:hi"),
            InlineKeyboardButton("馃嚞馃嚙 English", callback_data="lang:en"),
        ],
        [InlineKeyboardButton(TEXT.get(lang, TEXT["en"])["home"], callback_data="home")]
    ])

def back_home(lang: str = "en") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(TEXT.get(lang, TEXT["en"])["home"], callback_data="home")]
    ])

def cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("鉂� Cancel", callback_data="cancel")]])

def ad_actions(ad_id: int, status: str) -> InlineKeyboardMarkup:
    toggle = ("鈻讹笍 Activate", f"ad:activate:{ad_id}") if status != "active" else ("鈴� Pause", f"ad:pause:{ad_id}")
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("馃憗 Preview", callback_data=f"ad:preview:{ad_id}"),
         InlineKeyboardButton("鉁忥笍 Edit", callback_data=f"ad:edit:{ad_id}")],
        [InlineKeyboardButton(toggle[0], callback_data=toggle[1]),
         InlineKeyboardButton("馃搮 Create Campaign", callback_data=f"camp:new:{ad_id}")],
        [InlineKeyboardButton("馃搫 Duplicate", callback_data=f"ad:duplicate:{ad_id}"),
         InlineKeyboardButton("馃棏 Delete", callback_data=f"ad:delete:{ad_id}")],
        [InlineKeyboardButton("猬咃笍 Back", callback_data="ad:list")],
    ])
