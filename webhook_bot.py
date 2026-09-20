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
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx
from aiohttp import web
from telegram import Update

from bot import build_app, log, OWNER_ID, ai_complete

PORT = int(os.getenv("PORT", "10000"))
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "xavier-tg-webhook-2026")
HOST = os.getenv("RENDER_EXTERNAL_HOSTNAME", "").strip()  # Render ye auto-set karta hai
SOCIAL_BOT_URL = os.getenv("SOCIAL_BOT_URL", "").strip()
TASK_SECRET = os.getenv("TASK_SECRET", "xavier-sm-task-2026")
IST = ZoneInfo("Asia/Kolkata")


async def social_task(name, extra=None):
    if not SOCIAL_BOT_URL:
        return
    params = {"name": name, "token": TASK_SECRET}
    if extra:
        params.update(extra)
    try:
        async with httpx.AsyncClient(timeout=300) as c:
            r = await c.get(f"{SOCIAL_BOT_URL}/task", params=params)
            log.info("social task %s -> %s %s", name, r.status_code, r.text[:80])
    except Exception:
        log.exception("social task fail: %s", name)


async def scheduler_loop(tg_app):
    """Daily brief (8 AM IST) + social media tasks yahan se trigger hote hain."""
    await asyncio.sleep(20)
    last = {}
    while True:
        try:
            now = datetime.now(IST)
            day = now.strftime("%Y-%m-%d")
            if now.hour == 8 and now.minute < 45 and last.get("brief") != day:
                last["brief"] = day
                try:
                    from brief import generate_brief
                    text = await generate_brief(ai_complete)
                    await tg_app.bot.send_message(chat_id=OWNER_ID, text=text[:4000])
                    log.info("daily 8AM brief sent")
                except Exception:
                    log.exception("daily brief fail")
                await social_task("morning")
            elif now.hour == 18 and now.minute < 45 and last.get("evening") != day:
                last["evening"] = day
                await social_task("evening")
            elif now.weekday() == 6 and now.hour == 12 and now.minute < 45 and last.get(
                "poll"
            ) != day:
                # Sunday noon: engagement poll (YT pe real poll, IG/FB pe comment-vote)
                last["poll"] = day
                await social_task(
                    "poll", {"topic": "CGL preparation me abhi kaunsa topic sabse zaroori hai?"}
                )
            elif 7 <= now.hour < 23 and now.minute % 30 == 0 and last.get(
                "comments"
            ) != f"{day}-{now.hour}-{now.minute // 30}":
                last["comments"] = f"{day}-{now.hour}-{now.minute // 30}"
                await social_task("comments")
        except Exception:
            log.exception("scheduler error")
        await asyncio.sleep(30)


async def video_forward(tg_app, msg):
    """User ne video bheji → social bot /upload → YouTube pe auto-upload."""
    fpath = f"/tmp/sm-up-{int(time.time())}.mp4"
    try:
        await tg_app.bot.send_message(
            chat_id=OWNER_ID, text="🎥 Video mil gayi! YouTube pe upload kar raha hoon (1-3 min)..."
        )
        vf = await tg_app.bot.get_file(msg.video.file_id)
        await vf.download_to_drive(custom_path=fpath)
        title = (msg.video.file_name or "Xavier video")[:100]
        for ext in (".mp4", ".mov", ".avi", ".mkv"):
            if title.lower().endswith(ext):
                title = title[: -len(ext)]
        async with httpx.AsyncClient(timeout=None) as c:
            with open(fpath, "rb") as f:
                r = await c.post(
                    f"{SOCIAL_BOT_URL}/upload",
                    params={"token": TASK_SECRET},
                    files={"file": (os.path.basename(fpath), f, msg.video.mime_type or "video/mp4")},
                )
            if r.status_code != 200:
                await tg_app.bot.send_message(
                    chat_id=OWNER_ID, text=f"⚠️ Video upload fail: {r.text[:200]}"
                )
                return
            data = r.json()
            r2 = await c.get(
                f"{SOCIAL_BOT_URL}/task",
                params={
                    "name": "video",
                    "file": data["file"],
                    "title": title,
                    "token": TASK_SECRET,
                },
            )
            await tg_app.bot.send_message(
                chat_id=OWNER_ID, text=f"📺 YouTube video status: {r2.text[:300]}"
            )
    except Exception:
        log.exception("video forward fail")
    finally:
        try:
            os.remove(fpath)
        except Exception:
            pass


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
            # Video bheji ho toh YouTube pe auto-upload (background me)
            if update.message and update.message.video and SOCIAL_BOT_URL:
                asyncio.create_task(video_forward(tg_app, update.message))
            await tg_app.process_update(update)
        except Exception:
            log.exception("Webhook update process karte waqt error")
            return web.Response(status=500, text="error")
        return web.Response(text="ok")

    async def morning_brief(request):
        # cron-job.org yahan daily hit karta hai (token check)
        if request.query.get("token") != WEBHOOK_SECRET:
            return web.Response(status=403, text="forbidden")
        try:
            from brief import generate_brief
            text = await generate_brief(ai_complete)
            if OWNER_ID:
                await tg_app.bot.send_message(chat_id=OWNER_ID, text=text[:4000])
                return web.Response(text="brief sent to owner")
            return web.Response(text=text[:200])
        except Exception as e:
            log.exception("morning brief fail")
            return web.Response(text=f"error: {e}", status=500)

    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/health", health)
    app.router.add_get("/morning-brief", morning_brief)
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
    if SOCIAL_BOT_URL:
        loop.create_task(scheduler_loop(tg_app))
        log.info("Scheduler active (8AM brief + social tasks)")
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
