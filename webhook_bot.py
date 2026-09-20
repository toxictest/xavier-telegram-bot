"""
Telegram Bot — WEBHOOK mode (Render free tier ke liye)

Kya hota hai:
- GET  /        → "alive" (Render health check / UptimeRobot ping)
- GET  /health  → same (ping endpoint)
- POST /webhook → Telegram yahan messages bhejta hai

Deploy (Render):  start command = python webhook_bot.py
Secret token se sirf Telegram hi messages bhej sakta hai (security).
"""
import asyncio
import logging
import os
import signal

from aiohttp import web
from telegram import Update

from bot import build_app, log

PORT = int(os.getenv("PORT", "10000"))
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "xavier-tg-webhook-2026")
HOST = os.getenv("RENDER_EXTERNAL_HOSTNAME", "").strip()  # Render ye auto-set karta hai


async def make_tg_app():
    tg_app = build_app()
    await tg_app.initialize()
    await tg_app.start()
    return tg_app


async def main():
    tg_app = await make_tg_app()

    async def health(request):
        return web.Response(text="tg-bot alive")

    async def webhook(request):
        # Sirf Telegram hi yahan bhej sakta hai (secret token match hona chahiye)
        token = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if token != WEBHOOK_SECRET:
            log.warning("Webhook reject: galat secret token")
            return web.Response(status=403, text="forbidden")
        try:
            data = await request.json()
            update = Update.de_json(data, tg_app.bot)
            await tg_app.process_update(update)
        except Exception:
            log.exception("Webhook update process karte waqt error")
            return web.Response(status=500, text="error")
        return web.Response(text="ok")

    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/health", health)
    app.router.add_post("/webhook", webhook)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    log.info("Webhook server listening on :%s", PORT)

    # Render pe: Telegram ko batado ki updates yahan bhejne hain
    if HOST:
        url = f"https://{HOST}/webhook"
        await tg_app.bot.set_webhook(
            url=url,
            secret_token=WEBHOOK_SECRET,
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES,
        )
        log.info("Webhook set ho gaya: %s", url)
    else:
        log.info("RENDER_EXTERNAL_HOSTNAME nahi mila — setWebhook skip (local test mode)")

    # Chale rakho jab tak Render SIGTERM na bheje
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError:
            pass
    await stop.wait()

    log.info("Shutting down gracefully...")
    await tg_app.stop()
    await tg_app.shutdown()
    await runner.cleanup()
    log.info("Bye.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
