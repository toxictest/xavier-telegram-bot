"""
Telegram Auto-Reply Bot
- Har message ka reply (rules-based + optional AI)
- Groups me sirf mention/reply pe reply karta hai
- Owner commands: /rules /setrule /delrule /id
"""
import json
import logging
import os
import re
from pathlib import Path

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
)

logging.basicConfig(
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("tg-bot")

# ---------------- Config ----------------
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()      # FREE
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()  # FREE

# Provider: groq | gemini | openai — auto-detect, ya AI_PROVIDER se force karo
PROVIDER = os.getenv("AI_PROVIDER", "").strip().lower()
if not PROVIDER:
    if GROQ_API_KEY:
        PROVIDER = "groq"
    elif GEMINI_API_KEY:
        PROVIDER = "gemini"
    elif OPENAI_API_KEY:
        PROVIDER = "openai"

DEFAULT_MODEL = {
    "groq": "qwen/qwen3.8-27b",
    "gemini": "gemini-2.0-flash",
    "openai": "gpt-4o-mini",
}
MODEL = os.getenv("MODEL", "").strip() or DEFAULT_MODEL.get(PROVIDER, "gpt-4o-mini")
OWNER_ID = int(os.getenv("OWNER_ID", "0") or 0) or None  # None = sab allowed (test ke liye)
SYSTEM_PROMPT = os.getenv(
    "SYSTEM_PROMPT",
    "Tu ek friendly personal assistant hai. Reply short, clear aur helpful rakh. "
    "User Hindi/Hinglish me likh sakta hai — usi language me reply karo.",
)

BASE_DIR = Path(__file__).parent
RULES_FILE = BASE_DIR / "rules.json"
MAX_HIST = 10  # per-chat history length for AI

# AI client (optional) — groq/openai: OpenAI-compatible, gemini: REST
_client = None
_http = None
try:
    if PROVIDER in ("groq", "openai"):
        from openai import AsyncOpenAI
        _client = AsyncOpenAI(
            api_key=GROQ_API_KEY if PROVIDER == "groq" else OPENAI_API_KEY,
            base_url="https://api.groq.com/openai/v1" if PROVIDER == "groq" else None,
        )
    elif PROVIDER == "gemini":
        import httpx
        _http = httpx.AsyncClient(timeout=30)
except ImportError:
    pass

AI_READY = _client is not None or _http is not None
if AI_READY:
    log.info("AI provider: %s (model: %s)", PROVIDER, MODEL)
else:
    log.info("AI provider: koi nahi — rules-only mode")

MEM = {}  # chat_id -> message history


# ---------------- Rules engine ----------------
def load_rules():
    try:
        with open(RULES_FILE) as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def save_rules(rules):
    with open(RULES_FILE, "w") as f:
        json.dump(rules, f, ensure_ascii=False, indent=2)


def first_rule_reply(text):
    t = (text or "").lower()
    for rule in load_rules():
        pat = rule.get("match", "")
        reply = rule.get("reply", "")
        if not pat or not reply:
            continue
        try:
            if re.search(pat, t, re.IGNORECASE):
                return reply
        except re.error:
            if pat.lower() in t:
                return reply
    return None


def default_reply():
    if not AI_READY:
        return (
            "✅ Message mil gaya!\n\n"
            "AI replies abhi ON nahi hain. Smart replies ke liye "
            "GROQ_API_KEY (free) ya GEMINI_API_KEY (free) .env me daalo, "
            "ya /rules me apne keywords add karo."
        )
    return "🤖 Soch raha hoon... (AI reply nahi aaya)"


# ---------------- AI reply ----------------
async def ai_complete(messages, max_tokens=300, temperature=0.6):
    """Generic AI call — OpenAI-compatible (Groq/OpenAI) ya Gemini REST. messages = [{role, content}]"""
    if _client is not None:
        resp = await _client.chat.completions.create(
            model=MODEL,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return (resp.choices[0].message.content or "").strip()
    if _http is not None:
        system = next((m["content"] for m in messages if m["role"] == "system"), None)
        contents = [
            {"role": "user" if m["role"] == "user" else "model",
             "parts": [{"text": m["content"]}]}
            for m in messages if m["role"] != "system"
        ]
        payload = {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": temperature,
            },
        }
        if system:
            payload["system_instruction"] = {"parts": [{"text": system}]}
        r = await _http.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent",
            params={"key": GEMINI_API_KEY},
            json=payload,
        )
        r.raise_for_status()
        return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    return None


async def ai_reply(chat_id, text):
    hist = MEM.setdefault(chat_id, [])
    hist.append({"role": "user", "content": text})
    out = None
    try:
        out = await ai_complete(
            [{"role": "system", "content": SYSTEM_PROMPT}] + hist[-MAX_HIST:],
            max_tokens=300,
        )
    except Exception as e:
        log.exception("AI call failed")
        out = f"⚠️ AI reply fail ho gaya: {e}"
    if not out:
        out = default_reply()
    hist.append({"role": "assistant", "content": out})
    del hist[:-MAX_HIST * 2]
    return out


# ---------------- Helpers ----------------
def is_owner(update: Update) -> bool:
    if not OWNER_ID:
        return True
    return update.effective_user and update.effective_user.id == OWNER_ID


# ---------------- Handlers ----------------
async def cmd_start(update: Update, context):
    await update.message.reply_text(
        f"Hello {update.effective_user.first_name}! 👋\n\n"
        "Main tumhara auto-reply bot hoon.\n"
        "/help — commands dikhata hoon\n"
        "Koi bhi message bhejo, main reply karunga."
    )


async def cmd_help(update: Update, context):
    txt = (
        "📌 Commands:\n"
        "/start — intro\n"
        "/id — apna Telegram ID dekho (OWNER_ID ke liye)\n"
        "/brief — CGL morning brief abhi banao 📰\n"
        "/rules — saari rules dikhao\n"
        "/setrule <keyword> <reply> — nayi rule add karo\n"
        "/delrule <keyword> — rule hatao\n\n"
        "Group me mujhe mention karo ya mere message ka reply karo."
    )
    if not is_owner(update):
        txt = (
            "📌 Commands:\n/start /help /id\n\n"
            "Rules manage karne ke liye OWNER_ID set hona chahiye."
        )
    await update.message.reply_text(txt)


async def cmd_id(update: Update, context):
    u = update.effective_user
    await update.message.reply_text(f"🆔 Aapka user ID: {u.id}\nChat ID: {update.effective_chat.id}")


async def cmd_rules(update: Update, context):
    if not is_owner(update):
        await update.message.reply_text("❌ Sirf owner.")
        return
    rules = load_rules()
    if not rules:
        await update.message.reply_text("Abhi koi rule nahi hai. /setrule se add karo.")
        return
    lines = [f"{i+1}. {r.get('match')} → {r.get('reply')}" for i, r in enumerate(rules)]
    await update.message.reply_text("📋 Rules:\n" + "\n".join(lines))


async def cmd_setrule(update: Update, context):
    if not is_owner(update):
        await update.message.reply_text("❌ Sirf owner.")
        return
    if len(context.args) < 2:
        await update.message.reply_text("Format: /setrule <keyword> <reply text>")
        return
    keyword = context.args[0]
    reply = " ".join(context.args[1:])
    rules = [r for r in load_rules() if r.get("match") != keyword]
    rules.append({"match": keyword, "reply": reply})
    save_rules(rules)
    await update.message.reply_text(f"✅ Rule save: {keyword} → {reply}")


async def cmd_delrule(update: Update, context):
    if not is_owner(update):
        await update.message.reply_text("❌ Sirf owner.")
        return
    if not context.args:
        await update.message.reply_text("Format: /delrule <keyword>")
        return
    keyword = context.args[0]
    rules = [r for r in load_rules() if r.get("match") != keyword]
    save_rules(rules)
    await update.message.reply_text(f"🗑️ Rule hatayi: {keyword}")


async def cmd_brief(update: Update, context):
    if not is_owner(update):
        await update.message.reply_text("❌ Sirf owner.")
        return
    await update.message.reply_text("📰 Brief bana raha hoon... (30-60 sec)")
    try:
        from brief import generate_brief
        text = await generate_brief(ai_complete)
        await update.message.reply_text(text[:4000])
    except Exception as e:
        log.exception("brief fail")
        await update.message.reply_text(f"⚠️ Brief fail ho gaya: {e}")


async def on_message(update: Update, context):
    msg = update.message
    if not msg or not msg.text:
        return

    text = msg.text.strip()
    chat = msg.chat

    # Group me sirf mention / reply-to-bot pe reply
    if chat.type != "private":
        mentioned = False
        for e in msg.entities or []:
            if e.type == "mention" and e.user and e.user.id == context.bot.id:
                mentioned = True
        replied_to_bot = (
            msg.reply_to_message
            and msg.reply_to_message.from_user
            and msg.reply_to_message.from_user.id == context.bot.id
        )
        if not (mentioned or replied_to_bot or text.startswith("/")):
            return

    # 1) Rules
    reply = first_rule_reply(text)

    # 2) AI
    if reply is None and AI_READY:
        try:
            await chat.send_action(ChatAction.TYPING)
        except Exception:
            pass
        reply = await ai_reply(chat.id, text)

    # 3) Fallback
    if reply is None:
        reply = default_reply()

    await msg.reply_text(reply[:4000])


async def on_non_text(update: Update, context):
    await update.message.reply_text("📎 Main abhi sirf text messages handle karta hoon.")


# ---------------- App ----------------
def build_app() -> Application:
    if not BOT_TOKEN:
        raise SystemExit(
            "BOT_TOKEN missing hai. .env file banao ya environment me set karo (BotFather se token)."
        )
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("id", cmd_id))
    app.add_handler(CommandHandler("brief", cmd_brief))
    app.add_handler(CommandHandler("rules", cmd_rules))
    app.add_handler(CommandHandler("setrule", cmd_setrule))
    app.add_handler(CommandHandler("delrule", cmd_delrule))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))
    app.add_handler(MessageHandler(~filters.TEXT & ~filters.COMMAND, on_non_text))
    return app


def main():
    app = build_app()
    log.info("Bot starting (polling)...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
