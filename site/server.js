// XpressIQ reports site: static files + two form endpoints.
// Leads are appended to DATA_DIR/leads.jsonl and, when RESEND_API_KEY is set, emailed to CONTACT_TO.
// The destination address is never sent to the browser.
const express = require("express");
const fs = require("fs");
const path = require("path");

const PORT = process.env.PORT || 3000;
const DATA_DIR = process.env.DATA_DIR || path.join(__dirname, "data");
const CONTACT_TO = process.env.CONTACT_TO || "";          // e.g. contact@xpressiq.co.uk (server env only)
const MAIL_FROM = process.env.MAIL_FROM || "XpressIQ <reports@xpressiq.co.uk>";
const RESEND_API_KEY = process.env.RESEND_API_KEY || "";

fs.mkdirSync(DATA_DIR, { recursive: true });
const app = express();
app.disable("x-powered-by");
app.use(express.json({ limit: "32kb" }));
app.use(express.urlencoded({ extended: false, limit: "32kb" }));

const clean = (v, n = 2000) => (typeof v === "string" ? v.trim().slice(0, n) : "");
const isEmail = (e) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(e);

async function notify(subject, text) {
  if (!RESEND_API_KEY || !CONTACT_TO) return false;
  const r = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: { Authorization: `Bearer ${RESEND_API_KEY}`, "Content-Type": "application/json" },
    body: JSON.stringify({ from: MAIL_FROM, to: [CONTACT_TO], subject, text }),
  });
  return r.ok;
}

async function lead(kind, req, res) {
  const b = req.body || {};
  const email = clean(b.email, 200);
  if (!isEmail(email)) return res.status(400).json({ ok: false, error: "A valid email address is needed." });
  if (clean(b.website)) return res.json({ ok: true }); // honeypot filled: pretend success
  const rec = {
    kind, at: new Date().toISOString(), email,
    name: clean(b.name, 200), company: clean(b.company, 200),
    question: clean(b.question), decision: clean(b.decision), timeframe: clean(b.timeframe, 100),
    report: clean(b.report, 200), ua: clean(req.get("user-agent"), 300),
  };
  fs.appendFileSync(path.join(DATA_DIR, "leads.jsonl"), JSON.stringify(rec) + "\n");
  const subject = kind === "commission" ? `[XpressIQ] Report enquiry from ${rec.name || email}` : `[XpressIQ] New subscriber: ${email}`;
  const text = Object.entries(rec).map(([k, v]) => `${k}: ${v}`).join("\n");
  try { await notify(subject, text); } catch (e) { console.error("notify failed", e.message); }
  res.json({ ok: true });
}

app.post("/api/subscribe", (req, res) => lead("subscribe", req, res));
app.post("/api/commission", (req, res) => lead("commission", req, res));

// static site with clean URLs (/gallery -> gallery.html, /reports/slug -> reports/slug.html)
const ROOT = path.join(__dirname);
app.use(express.static(ROOT, { extensions: ["html"], maxAge: "1h", setHeaders: (res, p) => { if (p.endsWith(".mp4")) res.setHeader("Cache-Control", "public, max-age=604800"); } }));
app.use((req, res) => res.status(404).sendFile(path.join(ROOT, "404.html"), (err) => { if (err) res.status(404).send("Not found"); }));

app.listen(PORT, () => console.log(`xpressiq site on :${PORT}, leads -> ${DATA_DIR}, mail ${RESEND_API_KEY && CONTACT_TO ? "on" : "off (file only)"}`));
