# Xavier Auto-Assistant System 🤖

Ek hi token/key system se 3 platforms ka kaam:

| Platform | Mode | Hosting | Status |
|---|---|---|---|
| **Telegram** (@Xavier_dadaBot) | Webhook | Render (free, 24/7) | ✅ Live |
| **WhatsApp** | Baileys (linked device) | Sandbox / PC (one-click) | ✅ Live |
| **CGL Morning Brief** | Google News RSS + AI | Render endpoint + cron-job.org | ✅ Ready |

## Features
- **AI replies** — Groq (FREE) `qwen/qwen3.8-27b`, Hinglish, 10-message memory
- **Keyword rules** — `rules.json` (dono platforms share karte hain), Telegram/WhatsApp se `/setrule` se manage
- **CGL Morning Brief** — subah 8 AM (cron-job.org → `/morning-brief` endpoint) + `/brief` command on demand
- **Owner lock** — `OWNER_ID` se sirf owner rules badal sakta hai
- **Group safety** — groups me sirf mention/reply pe reply

## Files
```
bot.py               # Core bot (rules + AI + commands) — Telegram
webhook_bot.py       # Webhook server — Render deploy ke liye
brief.py             # CGL morning brief engine (RSS + AI)
rules.json           # Shared keyword rules
requirements.txt     # Python deps
render.yaml          # Render settings (auto-deploy)
RENDER-GUIDE.md      # Render deploy guide
VM-GUIDE.md          # Free VM guide (future)

wa/
  wa-bot.js          # WhatsApp bot (Baileys) — same rules + AI
  WhatsAppBot.bat    # PC one-click launcher (auto-restart)
  INSTALL-PC.md      # PC setup guide (10 min)
  package.json       # Node deps
```

## Secrets (repo me Nahi hain)
`BOT_TOKEN`, `GROQ_API_KEY`, `OWNER_ID` → Render ke Environment Variables me
(sandbox me `tg-bot/.env`, PC me `wa/.env` — dono git-excluded)

## Useful endpoints (Render)
- `GET /health` — liveness (UptimeRobot ping yahan)
- `GET /morning-brief?token=<WEBHOOK_SECRET>` — daily brief trigger
- `POST /webhook` — Telegram updates (secret-protected)

## 24/7 stack
1. **Render** — Telegram bot + brief (webhook, free tier)
2. **UptimeRobot** — har 1 min `/health` ping (Render ko jaagaye)
3. **cron-job.org** — daily 8 AM `morning-brief` trigger (Asia/Kolkata)
4. **PC (optional)** — WhatsApp bot 24/7 (`wa/WhatsAppBot.bat`)
