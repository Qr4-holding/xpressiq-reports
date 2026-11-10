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
// Demo room: password, cookie-signing secret and the demo links live in the server environment only.
const crypto = require("crypto");
const DEMO_PASSWORD = process.env.DEMO_PASSWORD || "";
const DEMO_SECRET = process.env.DEMO_SECRET || crypto.randomBytes(32).toString("hex");
let DEMO_LINKS = {};   // {"product-slug": "https://..."} or {"product-slug": [["Button label","https://..."], ...]}
try { DEMO_LINKS = JSON.parse(process.env.DEMO_LINKS || "{}"); } catch (e) { console.error("DEMO_LINKS is not valid JSON"); }
const NOINDEX = !!process.env.NOINDEX;

fs.mkdirSync(DATA_DIR, { recursive: true });
const app = express();
app.disable("x-powered-by");
app.set("trust proxy", 1);
if (NOINDEX) app.use((req, res, next) => { res.setHeader("X-Robots-Tag", "noindex, nofollow"); next(); });
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
    report: clean(b.report, 200), product: clean(b.product, 200), interest: clean(b.interest, 200), ua: clean(req.get("user-agent"), 300),
  };
  fs.appendFileSync(path.join(DATA_DIR, "leads.jsonl"), JSON.stringify(rec) + "\n");
  const subject = kind === "enquiry" ? `[XpressIQ] ${rec.interest || "Demo request"}: ${rec.product || "a build"} from ${rec.name || email}` : kind === "commission" ? `[XpressIQ] Report enquiry from ${rec.name || email}` : `[XpressIQ] New subscriber: ${email}`;
  const text = Object.entries(rec).map(([k, v]) => `${k}: ${v}`).join("\n");
  try { await notify(subject, text); } catch (e) { console.error("notify failed", e.message); }
  res.json({ ok: true });
}

app.post("/api/subscribe", (req, res) => lead("subscribe", req, res));
app.post("/api/commission", (req, res) => lead("commission", req, res));
app.post("/api/enquiry", (req, res) => lead("enquiry", req, res));

// ---------- demo room (password protected) ----------
const PRIV = path.join(__dirname, "private");
const readPriv = (f) => { try { return fs.readFileSync(path.join(PRIV, f), "utf8"); } catch (e) { return ""; } };
const escH = (v) => String(v).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const demoToken = () => crypto.createHmac("sha256", DEMO_SECRET).update("demo:" + DEMO_PASSWORD).digest("hex");
const same = (a, b) => { const x = crypto.createHash("sha256").update(String(a)).digest(), y = crypto.createHash("sha256").update(String(b)).digest(); return crypto.timingSafeEqual(x, y); };
const cookie = (req, name) => { const m = (req.headers.cookie || "").split(/;\s*/).find((c) => c.startsWith(name + "=")); return m ? m.slice(name.length + 1) : ""; };
const authed = (req) => !!DEMO_PASSWORD && same(cookie(req, "xiq_demo"), demoToken());
const fails = new Map();   // ip -> {n, until}
const blocked = (ip) => { const f = fails.get(ip); if (!f) return false; if (Date.now() > f.until) { fails.delete(ip); return false; } return f.n >= 8; };
const priv = (res) => { res.setHeader("Cache-Control", "no-store"); res.setHeader("X-Robots-Tag", "noindex, nofollow"); return res; };
function demoButtons(slug) {
  let v = DEMO_LINKS[slug];
  if (typeof v === "string") v = [["Open the working demo", v]];
  const ok = (Array.isArray(v) ? v : []).filter((x) => Array.isArray(x) && /^https:\/\//.test(x[1] || ""));
  if (!ok.length) return '<span class="tag tag-soon" style="text-align:center">Demo being connected</span>';
  return ok.map(([label, url]) => `<a class="btn btn-lime" href="${escH(url)}" target="_blank" rel="noopener noreferrer">${escH(label)} <span class="arr" aria-hidden="true">→</span></a>`).join("");
}
const loginPage = (msg) => readPriv("login.html").replace("<!--ERR-->", escH(msg || ""));
app.get("/demos", (req, res) => {
  if (!DEMO_PASSWORD) return priv(res).send(loginPage("The demo room is not open yet. Request access and you will hear back."));
  if (!authed(req)) return priv(res).status(401).send(loginPage(""));
  priv(res).send(readPriv("demos.html").replace(/<!--DEMO:([a-z0-9-]+)-->/g, (m, slug) => demoButtons(slug)));
});
app.post("/demos/login", (req, res) => {
  const ip = req.ip || "x";
  if (!DEMO_PASSWORD) return res.redirect(303, "/demos");
  if (blocked(ip)) return priv(res).status(429).send(loginPage("Too many attempts. Please try again in 15 minutes."));
  if (!same(clean((req.body || {}).password, 200), DEMO_PASSWORD)) {
    const f = fails.get(ip) || { n: 0, until: 0 }; f.n += 1; f.until = Date.now() + 15 * 60 * 1000; fails.set(ip, f);
    return priv(res).status(401).send(loginPage("That password is not right. Please check it and try again."));
  }
  fails.delete(ip);
  res.setHeader("Set-Cookie", `xiq_demo=${demoToken()}; Path=/; HttpOnly; SameSite=Lax; Max-Age=${7 * 24 * 3600}${req.secure ? "; Secure" : ""}`);
  const next = clean((req.body || {}).next, 80).replace(/[^a-z0-9-]/g, "");
  res.redirect(303, "/demos" + (next ? "#" + next : ""));
});
app.get("/demos/logout", (req, res) => { res.setHeader("Set-Cookie", "xiq_demo=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0"); res.redirect(303, "/demos"); });
// never serve the private templates or the site's own source files
app.use((req, res, next) => (/^\/(private|node_modules|data)(\/|$)|\.(py|json|yml|md|conf)$|^\/server\.js$/i.test(req.path) ? res.status(404).sendFile(path.join(__dirname, "404.html")) : next()));

// static site with clean URLs (/gallery -> gallery.html, /reports/slug -> reports/slug.html)
const ROOT = path.join(__dirname);
app.use(express.static(ROOT, { extensions: ["html"], maxAge: "1h", setHeaders: (res, p) => {
  if (p.endsWith(".html")) res.setHeader("Cache-Control", "no-cache");
  else if (p.endsWith(".mp4") || p.endsWith(".jpg")) res.setHeader("Cache-Control", "public, max-age=604800");
} }));
app.use((req, res) => res.status(404).sendFile(path.join(ROOT, "404.html"), (err) => { if (err) res.status(404).send("Not found"); }));

app.listen(PORT, () => console.log(`xpressiq site on :${PORT}, leads -> ${DATA_DIR}, mail ${RESEND_API_KEY && CONTACT_TO ? "on" : "off (file only)"}, demo room ${DEMO_PASSWORD ? "locked with password" : "closed (no password set)"}`));
