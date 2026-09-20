"""
CGL Morning Brief
Google News RSS (India) se headlines nikaalta hai, AI se exam-oriented brief banata hai.
"""
import logging
import urllib.parse
import xml.etree.ElementTree as ET

import httpx

log = logging.getLogger("tg-bot.brief")

NEWS_QUERIES = [
    ("current affairs today general knowledge", 6),
    ("SSC CGL exam notification result", 5),
    ("SSC CGL preparation syllabus update", 3),
    ("India government scheme policy news", 4),
]

SYSTEM_BRIEF_PROMPT = (
    "Tum ek SSC CGL aspirant ka personal news editor ho. Neeche diye headlines ko padhke "
    "ek crisp 'Morning Current Affairs Brief' Hinglish me banao.\n\n"
    "Format exactly yeh rakho:\n"
    "🌅 GOOD MORNING — CGL Morning Brief\n\n"
    "🎯 TOP 5 CURRENT AFFAIRS — har item: one-liner + (CGL ke liye kyun important)\n\n"
    "📢 SSC/CGL LATEST — notification, exam date, result jaisi updates (ho toh)\n\n"
    "📌 QUICK GK — 2-3 one-liners\n\n"
    "Sources bracket me mention karo (jaise [Adda247], [TOI]). Total ~250 words. "
    "Sirf brief likhna, aur kuch nahi."
)


async def _fetch_rss(client, query, count):
    params = urllib.parse.urlencode(
        {"q": query, "hl": "en-IN", "gl": "IN", "ceid": "IN:en"}
    )
    r = await client.get(f"https://news.google.com/rss/search?{params}")
    r.raise_for_status()
    root = ET.fromstring(r.content)
    items = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        src = item.find("source")
        source = src.text.strip() if src is not None and src.text else ""
        if title:
            items.append({"title": title, "source": source, "link": link})
        if len(items) >= count:
            break
    return items


async def gather_headlines():
    seen, items = set(), []
    async with httpx.AsyncClient(
        timeout=20, headers={"User-Agent": "Mozilla/5.0 (xavier-tg-bot)"}
    ) as client:
        for query, count in NEWS_QUERIES:
            try:
                for it in await _fetch_rss(client, query, count):
                    key = it["title"].lower()
                    if key not in seen:
                        seen.add(key)
                        items.append(it)
            except Exception:
                log.exception("RSS fetch fail: %s", query)
    return items[:20]


async def generate_brief(ai_complete):
    """ai_complete = bot.ai_complete (system+user messages leke AI output deta hai)."""
    items = await gather_headlines()
    if not items:
        return "⚠️ Aaj ki news fetch nahi ho payi. Thodi der me /brief se phir try karo."
    data = "\n".join(f"- {it['title']} [{it['source']}]" for it in items)
    out = await ai_complete(
        [
            {"role": "system", "content": SYSTEM_BRIEF_PROMPT},
            {"role": "user", "content": f"Headlines:\n{data}\n\nAb brief likho."},
        ],
        max_tokens=800,
        temperature=0.4,
    )
    return out or "⚠️ Brief generate nahi ho payi (AI fail). Phir try karo."
