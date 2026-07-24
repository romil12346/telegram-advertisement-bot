# Professional Telegram Advertisement Bot

A Railway-ready Telegram advertising and announcement manager.

## Included

- Text/photo/video/animation/document advertisements
- Inline URL buttons
- Draft, preview, publish, pause, resume, duplicate and delete
- Multiple connected groups/channels
- Bot administrator and permission checks
- One-time and interval schedules
- Working-hour restrictions
- Maximum post count and expiry
- Automatic retry and delivery logs
- Optional deletion of the previous advertisement
- Campaign analytics and tracked links
- Owner/sub-admin role system
- Plans, trials, coupons, referrals and subscriptions
- Daily dashboard and audit logs
- SQLite persistence and restart recovery
- Telegram-only admin interface

## Railway deployment

1. Create a Telegram bot using BotFather.
2. Copy `.env.example` values into Railway Variables.
3. Set `BOT_TOKEN` and your numeric `OWNER_ID`.
4. Upload this project to GitHub.
5. Deploy the repository on Railway.
6. Add PostgreSQL later if you need very large scale; the included version uses persistent SQLite.

Important: attach a Railway Volume and set `DATABASE_PATH=/data/advertisement_bot.db`.

## Commands

- `/start` – dashboard
- `/newad` – create advertisement
- `/myads` – advertisements
- `/groups` – connected chats
- `/analytics` – delivery statistics
- `/plans` – subscription information
- `/admin` – owner/admin controls
- `/cancel` – cancel current operation
- `/help` – help

## Connect a group/channel

1. Add the bot.
2. Promote it as administrator with Post Messages and Delete Messages permissions.
3. Send `/connect` in the group/channel.
4. Open the bot privately and use **My Groups**.

## Safety

The bot posts only to chats where it is present and authorised. It does not scrape members, send unsolicited private messages, bypass Telegram limits, or conceal advertising.
