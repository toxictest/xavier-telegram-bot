// WhatsApp Auto-Reply Bot (Baileys)
// Same rules.json + same Groq AI as Telegram bot
import {
  makeWASocket,
  fetchLatestBaileysVersion,
  useMultiFileAuthState,
  DisconnectReason,
} from '@whiskeysockets/baileys';
import QRCode from 'qrcode';
import fs from 'fs';
import http from 'http';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// ---------- Env (../.env se) ----------
function loadEnv(file) {
  try {
    for (const line of fs.readFileSync(file, 'utf8').split('\n')) {
      const m = line.match(/^\s*([A-Z0-9_]+)\s*=\s*(.*)$/);
      if (m && m[2] && !m[2].startsWith('#')) process.env[m[1]] = m[2];
    }
  } catch {}
}
loadEnv(path.join(__dirname, '..', '.env'));

const GROQ_KEY = process.env.GROQ_API_KEY || '';
const GROQ_MODEL = process.env.WA_MODEL || 'qwen/qwen3.8-27b';
const OWNER_ID = (process.env.OWNER_ID || '').replace(/@.*$/, '');
const SYSTEM_PROMPT =
  process.env.SYSTEM_PROMPT ||
  'Tu ek friendly personal assistant hai. Reply short, clear aur helpful rakh. User Hindi/Hinglish me likh sakta hai — usi language me reply karo.';
const RULES_FILE = path.join(__dirname, '..', 'rules.json');
const QR_FILE = path.join(__dirname, 'qr.png');
const SESSION_DIR = path.join(__dirname, 'session');
const WA_NUMBER = (process.env.WA_NUMBER || '').replace(/[^0-9]/g, '');
const PORT = parseInt(process.env.PORT || '10000', 10);
let WA_CONNECTED = false;

// ---------- Rules (shared with Telegram bot) ----------
function loadRules() {
  try {
    const d = JSON.parse(fs.readFileSync(RULES_FILE, 'utf8'));
    return Array.isArray(d) ? d : [];
  } catch {
    return [];
  }
}
function saveRules(rules) {
  fs.writeFileSync(RULES_FILE, JSON.stringify(rules, null, 2));
}
function ruleReply(text) {
  const t = (text || '').toLowerCase();
  for (const r of loadRules()) {
    if (!r.match || !r.reply) continue;
    let hit = false;
    try {
      hit = new RegExp(r.match, 'i').test(t);
    } catch {
      hit = t.includes(r.match.toLowerCase());
    }
    if (hit) return r.reply;
  }
  return null;
}

// ---------- AI (Groq, free) ----------
async function aiComplete(messages, maxTokens = 300, temperature = 0.6) {
  const res = await fetch('https://api.groq.com/openai/v1/chat/completions', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${GROQ_KEY}`,
    },
    body: JSON.stringify({ model: GROQ_MODEL, messages, max_tokens: maxTokens, temperature }),
  });
  if (!res.ok) throw new Error('Groq ' + res.status + ': ' + (await res.text()).slice(0, 200));
  const d = await res.json();
  return (d.choices?.[0]?.message?.content || '').trim();
}

const HIST = new Map();
const MAXH = 10;

async function getReply(chatId, text) {
  const r = ruleReply(text);
  if (r) return r;
  if (!GROQ_KEY) return '✅ Message mil gaya! (AI key set nahi hai)';
  const h = HIST.get(chatId) || [];
  h.push({ role: 'user', content: text });
  try {
    const out = await aiComplete([{ role: 'system', content: SYSTEM_PROMPT }, ...h.slice(-MAXH)], 300);
    h.push({ role: 'assistant', content: out });
    if (h.length > MAXH * 2) h.splice(0, h.length - MAXH * 2);
    HIST.set(chatId, h);
    return out || '🤖 (AI ne khali reply diya)';
  } catch (e) {
    return '⚠️ AI fail: ' + e.message;
  }
}

// ---------- CGL Morning Brief ----------
const NEWS_QUERIES = [
  ['current affairs today general knowledge', 6],
  ['SSC CGL exam notification result', 5],
  ['SSC CGL preparation syllabus update', 3],
  ['India government scheme policy news', 4],
];
const BRIEF_PROMPT =
  'Tum ek SSC CGL aspirant ka personal news editor ho. Neeche diye headlines ko padhke ek crisp "Morning Current Affairs Brief" Hinglish me banao. Format: 🌅 GOOD MORNING — CGL Morning Brief, phir 🎯 TOP 5 CURRENT AFFAIRS (one-liner + CGL ke liye kyun important), phir 📢 SSC/CGL LATEST (notification/exam date/result), phir 📌 QUICK GK (2-3 one-liners). Sources bracket me mention karo. Total ~250 words. Sirf brief likhna.';

function decodeXml(s) {
  return (s || '')
    .replace(/<!\[CDATA\[([\s\S]*?)\]\]>/g, '$1')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .trim();
}

async function fetchRss(query, count) {
  const url =
    'https://news.google.com/rss/search?' +
    new URLSearchParams({ q: query, hl: 'en-IN', gl: 'IN', ceid: 'IN:en' });
  const res = await fetch(url, { headers: { 'User-Agent': 'Mozilla/5.0 (xavier-wa-bot)' } });
  if (!res.ok) throw new Error('rss ' + res.status);
  const xml = await res.text();
  const items = [];
  const re = /<item>([\s\S]*?)<\/item>/g;
  let m;
  while ((m = re.exec(xml)) && items.length < count) {
    const block = m[1];
    const title = decodeXml((block.match(/<title>([\s\S]*?)<\/title>/) || [])[1]);
    const source = decodeXml((block.match(/<source[^>]*>([\s\S]*?)<\/source>/) || [])[1]);
    if (title) items.push({ title, source });
  }
  return items;
}

async function generateBrief() {
  const items = [];
  const seen = new Set();
  for (const [q, n] of NEWS_QUERIES) {
    try {
      for (const it of await fetchRss(q, n)) {
        const k = it.title.toLowerCase();
        if (!seen.has(k)) {
          seen.add(k);
          items.push(it);
        }
      }
    } catch {}
  }
  const top = items.slice(0, 20);
  if (!top.length) return '⚠️ Aaj ki news fetch nahi ho payi. Phir try karo.';
  const data = top.map((i) => `- ${i.title} [${i.source}]`).join('\n');
  return (
    (await aiComplete(
      [
        { role: 'system', content: BRIEF_PROMPT },
        { role: 'user', content: `Headlines:\n${data}\n\nAb brief likho.` },
      ],
      800,
      0.4
    )) || '⚠️ Brief generate nahi ho payi.'
  );
}

// ---------- Commands ----------
function isOwner(jid) {
  if (!OWNER_ID) return true;
  return jid.startsWith(OWNER_ID);
}

async function handleCommand(sock, jid, text) {
  const parts = text.split(/\s+/);
  const cmd = (parts[0] || '').toLowerCase();

  if (cmd === '/start') {
    return 'Hello! 👋 Main WhatsApp pe bhi tumhara auto-reply bot hoon.\n/start /id /brief /rules /setrule <kw> <reply> /delrule <kw>';
  }
  if (cmd === '/id') return `🆔 Ye number: ${jid}`;
  if (cmd === '/rules') {
    if (!isOwner(jid)) return '❌ Sirf owner.';
    const rules = loadRules();
    if (!rules.length) return 'Abhi koi rule nahi. /setrule se add karo.';
    return '📋 Rules:\n' + rules.map((r, i) => `${i + 1}. ${r.match} → ${r.reply}`).join('\n');
  }
  if (cmd === '/setrule') {
    if (!isOwner(jid)) return '❌ Sirf owner.';
    if (parts.length < 3) return 'Format: /setrule <keyword> <reply text>';
    const kw = parts[1];
    const reply = parts.slice(2).join(' ');
    const rules = loadRules().filter((r) => r.match !== kw);
    rules.push({ match: kw, reply });
    saveRules(rules);
    return `✅ Rule save: ${kw} → ${reply}\n(Telegram bot se bhi apply hogi)`;
  }
  if (cmd === '/delrule') {
    if (!isOwner(jid)) return '❌ Sirf owner.';
    if (parts.length < 2) return 'Format: /delrule <keyword>';
    const kw = parts[1];
    saveRules(loadRules().filter((r) => r.match !== kw));
    return `🗑️ Rule hatayi: ${kw}`;
  }
  if (cmd === '/brief') {
    if (!isOwner(jid)) return '❌ Sirf owner.';
    sock.sendMessage(jid, { text: '📰 Brief bana raha hoon... (30-60 sec)' });
    return await generateBrief();
  }
  return null;
}

// ---------- WhatsApp connection ----------
const { state, saveCreds } = await useMultiFileAuthState(SESSION_DIR);
const { version } = await fetchLatestBaileysVersion();
console.log('Baileys version:', version?.join('.'));

async function connect() {
  const sock = makeWASocket({ version, auth: state, printQRInTerminal: true });
  sock.ev.on('creds.update', saveCreds);

  // Pairing-code mode: number set ho toh QR ki jagah phone pe code-based request jaati hai
  if (!state.creds.registered && WA_NUMBER) {
    try {
      const code = await sock.requestPairingCode(WA_NUMBER);
      console.log('PAIRING CODE REQUESTED for ' + WA_NUMBER);
      console.log('PAIRING CODE: ' + code);
      console.log('Phone pe pairing request aayegi — usme yahi code dikhna chahiye — confirm karo');
    } catch (e) {
      console.error('pairing code request fail:', e.message);
    }
  }

  sock.ev.on('connection.update', (upd) => {
    const { connection, lastDisconnect, qr } = upd;
    if (qr) {
      QRCode.toFile(QR_FILE, qr, { width: 440, margin: 2 }).then(() =>
        console.log('QR READY:', QR_FILE)
      );
    }
    if (connection === 'open') {
      WA_CONNECTED = true;
      console.log('CONNECTED as', sock.user?.id);
      try { fs.unlinkSync(QR_FILE); } catch {}
    }
    if (connection === 'close') {
      WA_CONNECTED = false;
      const code = lastDisconnect?.error?.output?.statusCode;
      if (code === DisconnectReason.loggedOut) {
        console.log('LOGGED OUT — session reset. QR/pairing dobara karna hoga.');
        try {
          fs.rmSync(SESSION_DIR, { recursive: true, force: true });
          fs.mkdirSync(SESSION_DIR, { recursive: true });
        } catch {}
      }
      console.log('Connection close — 3 sec me reconnect...');
      setTimeout(connect, 3000);
    }
  });

  sock.ev.on('messages.upsert', async ({ messages }) => {
    for (const m of messages) {
      try {
        const jid = m.key.remoteJid;
        const rawText = m.message?.conversation || m.message?.extendedTextMessage?.text || '';
        console.log(
          '>>> MSG jid=' + jid +
          ' fromMe=' + m.key.fromMe +
          ' types=' + Object.keys(m.message || {}).join(',') +
          ' text="' + String(rawText).slice(0, 80) + '"'
        );
        if (!m.message || m.key.fromMe) continue;
        if (!jid || jid === 'status@broadcast' || jid === 'broadcast') continue;

        let text = m.message.conversation || m.message.extendedTextMessage?.text || '';
        if (!text || !text.trim()) continue;
        text = text.trim();

        // Group: sirf mention ya reply-to-bot
        if (jid.includes('@g.us')) {
          const ext = m.message.extendedTextMessage || {};
          const mentioned = ext.mentionedJid || [];
          const replyToBot = ext.contextInfo?.participant === sock.user?.id;
          if (!mentioned.includes(sock.user?.id) && !replyToBot && !text.startsWith('/')) continue;
          text = text.replace(/@\d{5,}/g, '').trim() || text;
        }

        let out = null;
        if (text.startsWith('/')) out = await handleCommand(sock, jid, text);
        else out = await getReply(jid, text);
        if (out) {
          await sock.sendMessage(jid, { text: out.slice(0, 4000) });
          console.log('>>> REPLIED to ' + jid + ' ("' + String(out).slice(0, 60) + '...")');
        } else {
          console.log('>>> NO REPLY (filtered) for ' + jid);
        }
      } catch (e) {
        console.error('message error:', e.message);
      }
    }
  });
}

// ---------- HTTP server (host: health check + live QR page) ----------
const QR_PAGE = `<!DOCTYPE html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Xavier WhatsApp Bot</title>
<style>
body{font-family:system-ui,Arial;background:#0b141a;color:#e9edef;display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:100vh;margin:0}
img{width:min(82vw,360px);border-radius:12px;margin:14px 0;background:#fff}
#st{font-size:18px}
p{color:#8696a0;font-size:14px;text-align:center;padding:0 18px;line-height:1.5}
</style></head><body>
<h1> WhatsApp Bot</h1>
<div id="st">⏳ check ho raha...</div>
<img id="qr" src="/qr.png?t=0" onerror="this.style.opacity=.25">
<p>"CONNECTED" na dikhe toh: WhatsApp → Settings → <b>Linked Devices</b> → <b>Link a Device</b> → upar wala QR scan karo. QR khud refresh hota hai.</p>
<script>
let i=0;
setInterval(()=>{document.getElementById('qr').src='/qr.png?t='+(++i)},8000);
setInterval(async()=>{try{const s=await fetch('/status').then(r=>r.json());
document.getElementById('st').textContent=s.connected?'✅ CONNECTED — bot 24/7 live hai':'⏳ QR scan karo (upar)';
}catch(e){}},5000);
</script>
</body></html>`;

http
  .createServer((req, res) => {
    if (req.url.startsWith('/qr.png')) {
      fs.readFile(QR_FILE, (err, data) => {
        if (err) {
          res.writeHead(404, { 'Content-Type': 'text/plain' });
          res.end('QR abhi ready nahi');
          return;
        }
        res.writeHead(200, { 'Content-Type': 'image/png', 'Cache-Control': 'no-store' });
        res.end(data);
      });
    } else if (req.url.startsWith('/status')) {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ connected: WA_CONNECTED }));
    } else if (req.url.startsWith('/health')) {
      res.writeHead(200, { 'Content-Type': 'text/plain' });
      res.end('wa-bot alive');
    } else {
      res.writeHead(200, { 'Content-Type': 'text/html' });
      res.end(QR_PAGE);
    }
  })
  .listen(PORT, '0.0.0.0', () => console.log('HTTP server on :' + PORT));

connect();
console.log('WhatsApp bot starting... (QR bane pe terminal me "QR READY" aayega)');
