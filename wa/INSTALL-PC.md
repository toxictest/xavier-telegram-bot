# 💻 WhatsApp Bot — PC pe 24/7 Setup (10 min, free)

Yeh package tumhare WhatsApp bot ko PC pe hamesha-on banata hai.

## Files kya hain (yehi sab zip me hain)
| File | Kaam |
|---|---|
| `WhatsAppBot.bat` | **Yehi double-click karo** — bot start (crash ho toh khud restart) |
| `wa-bot.js` | Bot ka code |
| `.env` | Tumhara Groq key + Owner ID (already set) |
| `session/` | **Tumhari linked device ka session — QR dobara scan NAHI karna** |
| `package.json` + `package-lock.json` | Dependencies ki list |

## Setup (10 min)

### Step 1: Node.js install karo (sirf pehli baar)
1. [nodejs.org](https://nodejs.org) kholo
2. **LTS** version download karo
3. Installer chalao — **saari settings default** (Next, Next, Install)
4. PC restart karo (zaroori)

### Step 2: Zip extract karo
1. `whatsapp-pc.zip` ko kisi jagah extract karo (e.g. `C:\XavierWA\`)
2. Folder me sab files + `session` folder hona chahiye

### Step 3: Bot chalao
1. **`WhatsAppBot.bat` double-click** karo
2. Pehli baar packages install honge (2-3 min) — phir turant
3. Session mil jayega toh **bina QR ke** hi CONNECT ho jayega
4. (Agar kabhi QR chahiye — wohi black window me print hoga, phone se scan karo)

### Step 4: PC ready rakhna
- Bot window **band mat karo**
- PC **sleep/hibernate mat karo** — Settings → Power & battery → Sleep: "Never" (ya bas PC ko on rakhna)
- Bas yahi — ab bot 24/7 jaagata rahega ✅

## Kya-kya automatically hota hai
- ✅ Crash ho toh **5 sec me khud restart**
- ✅ Boot ke baad bhi double-click karna hoga (ya PC me startup me daal sakte ho: Win+R → `shell:startup` → .bat ka shortcut wahan)
- ✅ Messages, AI replies, rules, /brief — sab wahi jaisa hai

## ⚠️ Important
1. **Ek hi time pe ek hi jagah chalu rakho** — PC pe chala toh sandbox wale bot ko band karwana hoga (agent se bolo "sandbox bot band kar do")
2. `session` folder kisi ko mat dikhao / share mat karo — isse tumhara WhatsApp control hota hai
3. Node.js install ke baad **naya** .bat window kholo (pehle wale me node path refresh nahi hota)
