# 📱 Xavier Full Automation — Master Setup Guide

> Har cheez kaha milegi, kaise milegi — sab ek jagah. Phone pe padhne layak.

## ⚡ TL;DR — kya ready hai, kya karna hai

**Ready ✅ (tune kuch nahi karna):**
- Telegram bot `@Xavier_dadaBot` — 24/7 Render pe
- WhatsApp bot — 24/7 Render pe (QR scan ho chuka)
- 8 AM brief, 6 PM post, comment auto-replies, Sunday poll — sab auto (TG bot ke andar)
- Social media bot (Instagram + Facebook + YouTube) — code ready, tested, GitHub pe

**Karna hai (is order me, total ~1.5 ghanta):**

| # | Kaam | Time |
|---|---|---|
| 1 | Social bot Render pe deploy (Part 1) | 10 min |
| 2 | TG bot se connect karna (Part 2) | 2 min |
| 3 | Instagram connect (Part 3) | 20 min |
| 4 | Facebook connect (Part 4) | 5 min |
| 5 | YouTube connect (Part 5) | 15 min |
| 6 | Uptime monitors (Part 6) | 10 min |
| 7 | Test checklist (Part 7) | 10 min |

**Koi bhi platform baad me connect karna ho toh bhi sab chalega** — jo connected nahi, uska post Telegram pe "manual" mode me aayega.

---

## 🗺️ Cheat sheet — cheez kaha milegi

| Cheez | Kaha se | Ek baar / baar-baar |
|---|---|---|
| Groq API key | console.groq.com | Ek baar (pehle se hai ✅) |
| TG bot token | @BotFather | Ek baar (pehle se hai ✅) |
| Owner TG ID | `5573716572` | Fixed (pehle se hai ✅) |
| IG token + ID | developers.facebook.com | Ek baar (60 din baad renew) |
| FB Page token + ID | Wahi Meta app | Ek baar (Page token kabhi expire nahi) |
| YouTube 4 values | console.cloud.google.com + yt_auth.py | Ek baar |
| TASK_SECRET | `xavier-sm-task-2026` | Fixed |

---

## Part 1: Social bot ko Render pe deploy karo (10 min)

1. `render.com` pe login (GitHub se)
2. Upar **New +** → **Web Service**
3. Repo: **`toxictest/xavier-social-bot`** select karo, branch `main`
4. Region: **Frankfurt** (India ke liye best free option)
5. Plan: **Free** (build/start commands render.yaml se auto aayenge)
6. **Environment Variables** daalo:

| Variable | Value | Abhi zaroori? |
|---|---|---|
| `GROQ_API_KEY` | (Groq console wali key) | ✅ |
| `MODEL` | `qwen/qwen3.8-27b` | default hi hai |
| `TELEGRAM_BOT_TOKEN` | @Xavier_dadaBot ka token | ✅ |
| `OWNER_TG_ID` | `5573716572` | ✅ |
| `TASK_SECRET` | `xavier-sm-task-2026` | ✅ |
| `IG_USER_TOKEN` | (Part 3 se milega) | baad me |
| `IG_USER_ID` | (Part 3 se milega) | baad me |
| `IG_PAGE_NAME` | `@xavier` | baad me |
| `FB_PAGE_ID` | (Part 4 se milega) | baad me |
| `FB_PAGE_TOKEN` | (Part 4 se milega) | baad me |
| `YT_REFRESH_TOKEN` | (Part 5 se milega) | baad me |
| `YT_CLIENT_ID` | (Part 5 se milega) | baad me |
| `YT_CLIENT_SECRET` | (Part 5 se milega) | baad me |
| `YT_CHANNEL_ID` | (Part 5 se milega) | baad me |

7. **Create Web Service** → green "Online" aane do (2-3 min)
8. URL copy kar lo: `https://xavier-social-bot.onrender.com`

⚠️ Pehla request 30-60 sec le sakta hai (free service soti hai, jaagne me time lagta hai).

---

## Part 2: TG bot se connect karo (2 min)

1. Render → `xavier-telegram-bot` service → **Settings → Environment**
2. Nayi variable: `SOCIAL_BOT_URL` = `https://xavier-social-bot.onrender.com`
3. Save → auto-redeploy hoga
4. **Bas.** Scheduler code me pehle se hai: 8 AM brief+post, 6 PM post, Sunday 12 PM poll, har 30 min comment replies (7 AM–11 PM)

---

## Part 3: Instagram connect (20 min)

**Pehle:** IG account **Business** hona chahiye
- Phone: Instagram → Profile → ⋮ → **Account type and tools** → **Switch to professional account** → Business

**Steps:**
1. `developers.facebook.com` pe login — **wahi Facebook account** jis se IG connected hai
2. **My Apps** → **Create App** → type: **Business** → name kuch bhi (e.g. "XavierSocial")
3. App dashboard → left menu → **Instagram**
4. **"Generate a token"** section → **As a Business Account** chuno → apna IG business account select karo → ye 3 permissions tick karo:
   - `instagram_business_basic`
   - `instagram_business_content_publish`
   - `instagram_business_manage_comments`
   → **Generate token**
5. Token ko long-lived banao (ek baar, browser me ye URL kholo):
   ```
   https://graph.facebook.com/v19.0/oauth/access_token?grant_type=fb_exchange_token&client_id=<APP_ID>&client_secret=<APP_SECRET>&fb_exchange_token=<STEP-4-WALA-TOKEN>
   ```
   APP_ID + APP_SECRET: app dashboard → **Settings → Basic**
   → response me `access_token` = **IG_USER_TOKEN**
   (Long-lived token 60 din ka hota hai, lekin roz use hone se khud renew hota rehta hai)
6. **IG_USER_ID** nikalo — browser me kholo:
   ```
   https://graph.facebook.com/v19.0/me?access_token=<IG_USER_TOKEN>
   ```
   → `"id": "1784xxxxxxxxxxxxx"` → yehi **IG_USER_ID** hai
7. **Test user add karo** (development mode me zaroori):
   App dashboard → Instagram section → **Manage / Add test users** → apna IG username → add
8. Render env me `IG_USER_TOKEN` + `IG_USER_ID` + `IG_PAGE_NAME` daalo → save
9. **Test:** browser me kholo:
   ```
   https://xavier-social-bot.onrender.com/task?name=morning&token=xavier-sm-task-2026
   ```
   → 1-2 min me tumhare Telegram pe post aayegi "✅ Instagram" ke saath

**Token expire/error ho toh:** step 4-6 dobara (2 min ka kaam).

---

## Part 4: Facebook Page connect (5 min)

1. Ek **Facebook Page** chahiye (personal profile nahi) — `facebook.com/pages/create`
2. Wahi Meta app (Part 3 wala): **Business Settings → Pages → Add Page** → apni page
3. Graph Explorer (`developers.facebook.com/tools/explorer`) me permissions add karo:
   `pages_show_list`, `pages_read_engagement`, `pages_manage_posts` → token generate
4. **Page token + ID** — browser me kholo:
   ```
   https://graph.facebook.com/v19.0/me/accounts?access_token=<LONG-LIVED-USER-TOKEN>
   ```
   → apni page ka `"id"` = **FB_PAGE_ID** aur `"access_token"` = **FB_PAGE_TOKEN**
   (Page token kabhi expire nahi hota ✅)
5. App me page ko **test user** add karo
6. Render env daalo → save

---

## Part 5: YouTube connect (15 min)

1. `console.cloud.google.com` → **wahi Google account** jiska YouTube channel hai
2. Upar project banao/select karo
3. **APIs & Services → Library** → search "YouTube Data API v3" → **Enable**
4. **OAuth consent screen** → User Type: **External** → naam daalo →
   **Test users** me apna Google email add karo → Save
   (App "Testing" mode me rahegi — apne account ke liye bilkul theek hai)
5. **Credentials → Create Credentials → OAuth client ID → Desktop app** → JSON download karo
   → usme `client_id` = **YT_CLIENT_ID**, `client_secret` = **YT_CLIENT_SECRET**
6. **Apne PC pe** (phone pe nahi):
   ```bash
   pip install requests
   python3 yt_auth.py
   ```
   (file `yt_auth.py` — repo `toxictest/xavier-social-bot` me hai; GitHub se download karo ya main bhej doon)
   → client ID/secret daalo → Google login page khulega → consent do
   → terminal me 4 lines print hongi:
   ```
   YT_REFRESH_TOKEN=...
   YT_CLIENT_ID=...
   YT_CLIENT_SECRET=...
   YT_CHANNEL_ID=...
   ```
7. Chaaron ko Render env me daalo → save
8. **Test:** @Xavier_dadaBot ko 5MB ki choti video bhejo → 2-3 min me YouTube pe upload + link Telegram pe

**Note:** free quota ≈ 6 video uploads/day + polls/community posts unlimited (10,000 units/day). Roz ka 1 video + poll = aaram se.

---

## Part 6: Uptime monitoring (10 min) — 24/7 ka bima

1. `uptimerobot.com` → free signup (email/Google)
2. **Add New Monitor** → type: **HTTP(S)**
3. Monitor 1: URL = `https://xavier-telegram-bot.onrender.com/health` → interval **5 min** (free me fixed) → alerts: email (+ WhatsApp optional)
4. Monitor 2: URL = `https://xavier-whatsapp-bot.onrender.com/health` → same
5. **Social bot ka monitor MAT banao** ⚠️ — wo 95% time sota hai (pool bachane ke liye). Monitor se wo 24/7 jaagta toh Render hours kha jaate.

---

## Part 7: Test checklist

- [ ] `https://xavier-social-bot.onrender.com/health` → "sm-bot alive"
- [ ] WA bot ko "hi" bhejo → 30 sec me reply
- [ ] Browser: `/task?name=morning&token=xavier-sm-task-2026` → TG pe post aaye
- [ ] IG connected hai toh post me "✅ Instagram" dikhe
- [ ] YT connected hai toh 5MB video bhejo → YouTube pe dikhe
- [ ] Manual poll: `/task?name=poll&topic=Best%20subject%3F&token=xavier-sm-task-2026`
- [ ] Sunday 12 PM ko auto poll aana chahiye

---

## Part 8: Monthly routine (1st tarikh, 2 min)

1. Render → **Billing → Usage** dekho: 750 hours me se kitne gaye
2. **Math:** TG 24/7 ≈ 730h + WA 24/7 ≈ 730h = **1460h > 750h pool**
   → Pool ~day 15-16 pe khatam hoga → Render free services ko next month tak pause kar dega (phir auto on)
3. **Permanent fix (jab pool tight ho):** WhatsApp bot **Koyeb** pe shift karo
   - Koyeb free: 1 service, 512MB, normally bina credit card ke, apna alag free pool
   - Phir Render me sirf TG (730h) + social bot (~10h) ≈ 740h → 750 me fit ✅
   - Bas bol do **"WA Koyeb pe shift karo"** — main files ready kar dunga

---

## 🆘 Common problems

| Problem | Solution |
|---|---|
| Pehla request 30-60 sec le raha | Normal (cold start). Dusra request fast aayega |
| WA bot redeploy ke baad nahi reply | `https://xavier-whatsapp-bot.onrender.com/` kholo → naya QR scan karo (Render ki disk har deploy pe reset hoti hai) |
| IG post me error (100/200) | Test user dobara add karo (Part 3 step 7) |
| YT: "accessNotConfigured" | YouTube Data API v3 enable nahi kiya (Part 5 step 3) |
| YT: "Invalid OAuth client" | Desktop app type hi chahiye, Web nahi (Part 5 step 5) |
| TG se post aayi lekin "manual" | Us platform ka token env me nahi/ghalta — check karo |
| Sunday poll nahi aaya | SOCIAL_BOT_URL env set hai? (Part 2) |

---

## 🔗 Sab kuch kaha hai

| Cheez | Location |
|---|---|
| TG bot code | github.com/toxictest/xavier-telegram-bot |
| Social bot code | github.com/toxictest/xavier-social-bot |
| Social bot setup details | repo ke andar `SM-SETUP.md` |
| YT auth script | repo ke andar `yt_auth.py` |
| Live TG bot | xavier-telegram-bot.onrender.com |
| Live WA bot | xavier-whatsapp-bot.onrender.com |
