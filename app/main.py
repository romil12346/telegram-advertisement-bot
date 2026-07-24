import logging
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler,
    ConversationHandler, filters
)
from .config import load_config
from .database import Database
from .scheduler import campaign_tick
from .handlers import (
    AD_NAME, AD_CONTENT, AD_BUTTONS, CAMP_INTERVAL, CAMP_CHATS,
    start, help_command, connect_chat, new_ad_start, new_ad_name, new_ad_content,
    new_ad_buttons, list_ads, view_ad, preview_ad, set_ad_status, duplicate_ad,
    delete_ad, new_campaign_start, campaign_interval, campaign_chat_selection,
    list_campaigns, toggle_campaign, list_chats, analytics, plans, admin_home,
    owner_command, support, settings, cancel, noop, error_handler,
)

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)

async def post_init(app: Application):
    db = app.bot_data["db"]
    await db.init()
    app.job_queue.run_repeating(campaign_tick, interval=30, first=5, name="campaign-tick")
    await app.bot.set_my_commands([
        ("start", "Open dashboard"),
        ("newad", "Create advertisement"),
        ("myads", "View advertisements"),
        ("groups", "Connected groups and channels"),
        ("analytics", "Delivery statistics"),
        ("plans", "Subscription plans"),
        ("help", "Help"),
        ("cancel", "Cancel current operation"),
    ])

def build_app() -> Application:
    cfg = load_config()
    db = Database(cfg.database_path)
    app = (
        Application.builder()
        .token(cfg.bot_token)
        .post_init(post_init)
        .concurrent_updates(False)
        .build()
    )
    app.bot_data["config"] = cfg
    app.bot_data["db"] = db

    ad_conv = ConversationHandler(
        entry_points=[
            CommandHandler("newad", new_ad_start),
            CallbackQueryHandler(new_ad_start, pattern=r"^ad:new$"),
        ],
        states={
            AD_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, new_ad_name)],
            AD_CONTENT: [MessageHandler(
                (filters.TEXT | filters.PHOTO | filters.VIDEO | filters.ANIMATION |
                 filters.Document.ALL | filters.AUDIO) & ~filters.COMMAND,
                new_ad_content,
            )],
            AD_BUTTONS: [MessageHandler(filters.TEXT & ~filters.COMMAND, new_ad_buttons)],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CallbackQueryHandler(cancel, pattern=r"^cancel$"),
        ],
        per_user=True,
        per_chat=True,
    )

    camp_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(new_campaign_start, pattern=r"^camp:new:\d+$")],
        states={
            CAMP_INTERVAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, campaign_interval)],
            CAMP_CHATS: [CallbackQueryHandler(campaign_chat_selection, pattern=r"^campchat:")],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CallbackQueryHandler(cancel, pattern=r"^cancel$"),
        ],
        per_user=True,
        per_chat=True,
    )

    app.add_handler(ad_conv)
    app.add_handler(camp_conv)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("connect", connect_chat))
    app.add_handler(CommandHandler("myads", list_ads))
    app.add_handler(CommandHandler("groups", list_chats))
    app.add_handler(CommandHandler("analytics", analytics))
    app.add_handler(CommandHandler("plans", plans))
    app.add_handler(CommandHandler("admin", admin_home))
    app.add_handler(CommandHandler(["addadmin", "removeadmin", "setplan", "broadcast"], owner_command))

    app.add_handler(CallbackQueryHandler(start, pattern=r"^home$"))
    app.add_handler(CallbackQueryHandler(list_ads, pattern=r"^ad:list$"))
    app.add_handler(CallbackQueryHandler(view_ad, pattern=r"^ad:view:\d+$"))
    app.add_handler(CallbackQueryHandler(preview_ad, pattern=r"^ad:preview:\d+$"))
    app.add_handler(CallbackQueryHandler(set_ad_status, pattern=r"^ad:(activate|pause):\d+$"))
    app.add_handler(CallbackQueryHandler(duplicate_ad, pattern=r"^ad:duplicate:\d+$"))
    app.add_handler(CallbackQueryHandler(delete_ad, pattern=r"^ad:delete:\d+$"))
    app.add_handler(CallbackQueryHandler(list_campaigns, pattern=r"^camp:list$"))
    app.add_handler(CallbackQueryHandler(toggle_campaign, pattern=r"^camp:toggle:\d+$"))
    app.add_handler(CallbackQueryHandler(list_chats, pattern=r"^chat:list$"))
    app.add_handler(CallbackQueryHandler(analytics, pattern=r"^analytics$"))
    app.add_handler(CallbackQueryHandler(plans, pattern=r"^plans$"))
    app.add_handler(CallbackQueryHandler(admin_home, pattern=r"^admin:home$"))
    app.add_handler(CallbackQueryHandler(settings, pattern=r"^settings$"))
    app.add_handler(CallbackQueryHandler(support, pattern=r"^support$"))
    app.add_handler(CallbackQueryHandler(noop, pattern=r"^noop$"))
    app.add_error_handler(error_handler)
    return app

def main():
    app = build_app()
    app.run_polling(allowed_updates=None, drop_pending_updates=False)

if __name__ == "__main__":
    main()
