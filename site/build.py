#!/usr/bin/env python3
"""Build the XpressIQ Fast Movers First site from reports.json + reports/*.md.
Usage: python3 build.py   (run inside the site folder)
Outputs: index.html, gallery.html, commission.html, reports/<slug>.html
"""
import json, re, html, pathlib, datetime
import markdown

ROOT = pathlib.Path(__file__).parent
MANIFEST = json.loads((ROOT / "reports.json").read_text())
REPORTS = MANIFEST["reports"]            # newest first
SITE = MANIFEST["site"]

def esc(s): return html.escape(s, quote=True)

BASE_URL = MANIFEST["site"].get("base_url", "https://www.xpressiq.co.uk")

def v(path):
    """Append a short content hash so browsers fetch new videos/posters after a re-wrap."""
    import hashlib
    f = ROOT / path
    if not f.exists(): return path
    h = hashlib.md5(f.read_bytes()).hexdigest()[:8]
    return f"{path}?v={h}"

def head(title, desc, depth=0, url="", image="", video=""):
    base = "../" * depth
    og = f'<meta property="og:type" content="website"><meta property="og:site_name" content="XpressIQ"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}">'
    if url: og += f'<meta property="og:url" content="{esc(url)}"><link rel="canonical" href="{esc(url)}">'
    if image: og += (f'<meta property="og:image" content="{esc(image)}"><meta property="og:image:secure_url" content="{esc(image)}">'
                     f'<meta property="og:image:type" content="image/jpeg"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">'
                     f'<meta property="og:image:alt" content="{esc(title)}"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{esc(title)}"><meta name="twitter:description" content="{esc(desc)}"><meta name="twitter:image" content="{esc(image)}">')
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">{og}<meta name="viewport" content="width=device-width,initial-scale=1">
<script>document.documentElement.className+=" js"</script><title>{esc(title)}</title><meta name="description" content="{esc(desc)}">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@500;700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{base}{v('assets/site.css')}"></head><body>"""

def nav(active, depth=0):
    b = "../" * depth
    def a(href, label, key):
        on = ' class="on"' if key == active else ""
        return f'<a href="{b}{href}"{on}>{label}</a>'
    return f"""<header class="nav"><div class="wrap">
<a class="logo" href="{b}index.html"><span class="h">Xpress<i>IQ</i><b></b></span><small>Fast Movers First</small></a>
<nav class="navlinks" aria-label="Main navigation">{a('index.html#builds','Builds','builds')}{a('index.html#reports','Reports','reports')}{a('gallery.html','Shorts','gallery')}{a('commission.html','Commission a report','commission')}<a class="lockl{' on' if active=='demos' else ''}" href="{b}demos"><svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" style="width:13px;height:13px"><path d="M17 9V7A5 5 0 0 0 7 7v2H6a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-9a2 2 0 0 0-2-2zm-8 0V7a3 3 0 0 1 6 0v2z"/></svg>Demo room</a></nav>
<a class="btn btn-dark navcta" href="{b}index.html#subscribe">Get the weekly report</a>
</div></header>"""

def footer(depth=0):
    b = "../" * depth
    y = datetime.date.today().year
    return f"""<footer class="footer"><div class="wrap">
<div><a class="logo" href="{b}index.html"><span class="h">Xpress<i style="color:#bdf453">IQ</i></span><small>Fast Movers First</small></a><p style="margin:8px 0 0">Intelligence delivered before you knew you needed it.</p></div>
<div style="display:flex;gap:24px;flex-wrap:wrap"><a href="{b}index.html#builds">Builds</a><a href="{b}index.html#reports">Reports</a><a href="{b}gallery.html">Shorts</a><a href="{b}demos">Demo room</a><a href="{b}commission.html">Commission a report</a><a href="{b}commission.html#contact">Contact</a></div>
<p style="margin:0;color:#7f9690">© {y} {SITE['company']} · <a href="{b}privacy.html">Privacy</a></p>
</div></footer>
<script>
document.querySelectorAll('.thumb').forEach(t=>{{const v=t.querySelector('video');if(!v)return;t.addEventListener('click',e=>{{if(e.target.closest('.rail'))return;if(t.classList.contains('playing'))return;t.classList.add('playing');v.controls=true;v.play();}});v.addEventListener('ended',()=>{{t.classList.remove('playing');v.controls=false;}});
const b=t.querySelector('.ri-share');if(!b)return;const lab=b.querySelector('span');let ready=null,busy=false;
const fname=()=> (b.dataset.text||'XpressIQ').replace(/[^a-z0-9]+/gi,'-').replace(/^-|-$/g,'').slice(0,60)+'.mp4';
const linkShare=async()=>{{const url=b.dataset.url,text=b.dataset.text;if(navigator.share){{try{{await navigator.share({{title:text,text:text,url:url}});}}catch(e){{}}return;}}try{{await navigator.clipboard.writeText(url);lab.textContent='Copied';setTimeout(()=>lab.textContent='Share',1500);}}catch(e){{prompt('Copy this link',url);}}}};
const fileShare=async f=>{{await navigator.share({{files:[f],title:b.dataset.text,text:b.dataset.text}});}};
b.addEventListener('click',async e=>{{e.stopPropagation();const fu=b.dataset.file;
 if(!fu||!navigator.canShare||!navigator.canShare({{files:[new File([new Blob()],'x.mp4',{{type:'video/mp4'}})]}})){{return linkShare();}}
 if(ready){{try{{await fileShare(ready);}}catch(err){{if(err.name!=='AbortError')linkShare();}}lab.textContent='Share';return;}}
 if(busy)return;busy=true;lab.textContent='Preparing';
 try{{const r=await fetch(fu);const blob=await r.blob();ready=new File([blob],fname(),{{type:'video/mp4'}});busy=false;
   try{{await fileShare(ready);lab.textContent='Share';}}catch(err){{if(err.name==='NotAllowedError'){{lab.textContent='Tap to send';}}else if(err.name==='AbortError'){{lab.textContent='Share';}}else{{lab.textContent='Share';linkShare();}}}}
 }}catch(err){{busy=false;lab.textContent='Share';linkShare();}}
}});}});
document.querySelectorAll('form[data-api]').forEach(f=>{{f.addEventListener('submit',async e=>{{e.preventDefault();const btn=f.querySelector('button[type=submit]');const msg=f.querySelector('.formmsg');const data=Object.fromEntries(new FormData(f).entries());btn.disabled=true;try{{const r=await fetch(f.dataset.api,{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify(data)}});const j=await r.json();if(j.ok){{f.querySelectorAll('input,textarea,select').forEach(i=>i.disabled=true);btn.textContent=f.dataset.done||'Done';msg.textContent=f.dataset.thanks||'Thank you.';}}else{{msg.textContent=j.error||'Something went wrong. Please try again.';btn.disabled=false;}}}}catch(err){{msg.textContent='Could not send just now. Please try again in a moment.';btn.disabled=false;}}}});}});
(function(){{var els=document.querySelectorAll('.rv');if(!('IntersectionObserver' in window)){{els.forEach(function(e){{e.classList.add('in')}});return;}}
var io=new IntersectionObserver(function(es){{es.forEach(function(e){{if(e.isIntersecting){{e.target.classList.add('in');io.unobserve(e.target);}}}});}},{{rootMargin:'0px 0px -8% 0px',threshold:.08}});els.forEach(function(e){{io.observe(e)}});
setTimeout(function(){{els.forEach(function(e){{var r=e.getBoundingClientRect();if(r.top<innerHeight)e.classList.add('in')}})}},1200);
if(matchMedia('(hover:hover) and (prefers-reduced-motion:no-preference)').matches)document.querySelectorAll('.pcard').forEach(function(c){{c.addEventListener('pointermove',function(ev){{var r=c.getBoundingClientRect(),x=(ev.clientX-r.left)/r.width-.5,y=(ev.clientY-r.top)/r.height-.5;c.style.transform='translateY(-6px) perspective(900px) rotateX('+(-y*3).toFixed(2)+'deg) rotateY('+(x*3).toFixed(2)+'deg)';}});c.addEventListener('pointerleave',function(){{c.style.transform='';}});}});
}})();
</script></body></html>"""

def optin(depth=0, report_slug="", compact=False):
    """Email opt-in form posting to /api/subscribe. Used on the home page and inside every report."""
    hid = f'<input type="hidden" name="report" value="{esc(report_slug)}">' if report_slug else ""
    head_h = '<h2 class="h" style="font-size:40px">Fast movers first.<br>Everyone else, later.</h2>' if not compact else '<h3 class="h" style="font-size:24px;margin:0">Get the next report before it is obvious.</h3>'
    para = "One email a week with the report, both videos and the sources. No digest, no filler. Unsubscribe in one click." if not compact else "One email a week: the report, both videos, the sources. Unsubscribe in one click."
    return f"""<div class="panel-dark optin{' compact' if compact else ''}"><div class="eyebrow">Get the weekly report</div>{head_h}<p>{para}</p>
<form data-api="/api/subscribe" data-done="Subscribed" data-thanks="You're on the list. The next report comes to your inbox." method="post" style="display:flex;gap:10px;flex-wrap:wrap;margin-top:8px">{hid}<input type="text" name="website" tabindex="-1" autocomplete="off" style="position:absolute;left:-9999px" aria-hidden="true"><label for="email-{report_slug or 'home'}" style="position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)">Email address</label><input id="email-{report_slug or 'home'}" name="email" type="email" placeholder="you@company.co.uk" required style="flex:1 1 220px;min-height:48px;padding:0 16px;border-radius:6px;border:1px solid #4e6b67;background:#0b1f22;color:#fff"><button type="submit" class="btn btn-lime">Send me the report</button><p class="formmsg" role="status" style="flex-basis:100%;margin:0;font-size:14px;color:#bdf453"></p></form>
<p style="font-size:12px;color:#8fa8a0">For founders, owners, investors and advisers who move on opportunity.</p></div>"""

def _ic(d): return f'<svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" style="width:20px;height:20px"><path d="{d}"/></svg>'
ICONS = {
 "share": _ic("M18 16a3 3 0 0 0-2.4 1.2l-7-4.1a3 3 0 0 0 0-2.2l7-4.1A3 3 0 1 0 15 5c0 .3 0 .6.1.9l-7 4.1a3 3 0 1 0 0 4l7 4.1A3 3 0 1 0 18 16"),
 "wa": _ic("M17.5 14.4c-.3-.1-1.8-.9-2-1-.3-.1-.5-.1-.7.1-.2.3-.8 1-1 1.2-.2.2-.4.2-.7.1-.3-.1-1.3-.5-2.4-1.5-.9-.8-1.5-1.8-1.7-2.1-.2-.3 0-.5.1-.6l.5-.6.3-.5c.1-.2 0-.4 0-.5L9 6.7c-.2-.6-.5-.5-.7-.5h-.6c-.2 0-.5.1-.8.4-.3.3-1 1-1 2.5s1.1 2.9 1.2 3.1c.1.2 2.1 3.2 5.1 4.5.7.3 1.3.5 1.7.6.7.2 1.4.2 1.9.1.6-.1 1.8-.7 2-1.4.2-.7.2-1.3.2-1.4-.1-.2-.3-.3-.5-.2M12 2a10 10 0 0 0-8.6 15.1L2 22l5-1.3A10 10 0 1 0 12 2m0 18.2a8.2 8.2 0 0 1-4.2-1.1l-.3-.2-3 .8.8-2.9-.2-.3A8.2 8.2 0 1 1 12 20.2"),
 "li": _ic("M20.4 2H3.6A1.6 1.6 0 0 0 2 3.6v16.8A1.6 1.6 0 0 0 3.6 22h16.8a1.6 1.6 0 0 0 1.6-1.6V3.6A1.6 1.6 0 0 0 20.4 2M8 19H5V9.5h3M6.5 8.2a1.7 1.7 0 1 1 0-3.5 1.7 1.7 0 0 1 0 3.5M19 19h-3v-4.6c0-1.1 0-2.5-1.5-2.5s-1.8 1.2-1.8 2.4V19h-3V9.5h2.9v1.3h.1a3.1 3.1 0 0 1 2.8-1.5c3 0 3.5 2 3.5 4.5"),
 "x": _ic("M17.5 3h3.1l-6.8 7.7L21.8 21h-6.2l-4.9-6.4L5.1 21H2l7.3-8.3L1.7 3h6.4l4.4 5.8M16.4 19.2h1.7L7 4.7H5.1"),
 "em": _ic("M3 5h18a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1m9 7.3L20 7H4m0 11h16V8.8l-8 5.5-8-5.5"),
 "ln": _ic("M10.6 13.4a1 1 0 0 1 0-1.4l3.4-3.4a3 3 0 0 1 4.2 4.2l-1.5 1.5-1.4-1.4 1.5-1.5a1 1 0 0 0-1.4-1.4l-3.4 3.4a1 1 0 0 0 1.4 1.4l.7-.7 1.4 1.4-.7.7a3 3 0 0 1-4.2-4.2m2.8-2.8a1 1 0 0 1 0 1.4L10 15.4a3 3 0 0 1-4.2-4.2l1.5-1.5 1.4 1.4-1.5 1.5a1 1 0 0 0 1.4 1.4l3.4-3.4"),
}

def share_img(vid):
    """1200x630 preview card if present, else the poster."""
    p = vid["poster"].replace(".jpg", "-share.jpg")
    return p if (ROOT / p).exists() else vid["poster"]

def stamp(url, vid):
    """Fresh query stamp per preview image so WhatsApp/LinkedIn build a new preview instead of a cached blank one."""
    import hashlib
    f = ROOT / share_img(vid)
    h = hashlib.md5(f.read_bytes()).hexdigest()[:6] if f.exists() else "1"
    return f"{url}?s={h}"

def share_overlay(url, text, file_url=""):
    """YouTube-style action rail down the right edge of a video: Share (system share sheet, or copy link),
    WhatsApp, X, LinkedIn. Always visible, including during playback."""
    import urllib.parse as u
    q = u.quote(url, safe=""); t = u.quote(text, safe="")
    def item(tag, inner, cls="", attrs=""):
        return f'<{tag} class="ri {cls}" {attrs}>{inner}</{tag}>'
    return ('<div class="rail" role="group" aria-label="Share this video">'
            + item("button", f'{ICONS["share"]}<span>Share</span>', "ri-share", f'type="button" data-url="{esc(url)}" data-text="{esc(text)}" data-file="{esc(file_url)}" aria-label="Share"')
            + item("a", f'{ICONS["wa"]}<span>WhatsApp</span>', "", f'href="https://wa.me/?text={t}%20{q}" target="_blank" rel="noopener" aria-label="Share on WhatsApp"')
            + item("a", f'{ICONS["x"]}<span>X</span>', "", f'href="https://x.com/intent/post?url={q}&text={t}" target="_blank" rel="noopener" aria-label="Share on X"')
            + item("a", f'{ICONS["li"]}<span>LinkedIn</span>', "", f'href="https://www.linkedin.com/sharing/share-offsite/?url={q}" target="_blank" rel="noopener" aria-label="Share on LinkedIn"')
            + '</div>')

def share(url, text):
    """Share row: native share sheet on phones, then WhatsApp, LinkedIn, X, email, copy link."""
    import urllib.parse as u
    q = u.quote(url, safe=""); t = u.quote(text, safe="")
    ic = lambda d: f'<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="{d}"/></svg>'
    wa = ic("M17.5 14.4c-.3-.1-1.8-.9-2-1-.3-.1-.5-.1-.7.1-.2.3-.8 1-1 1.2-.2.2-.4.2-.7.1-.3-.1-1.3-.5-2.4-1.5-.9-.8-1.5-1.8-1.7-2.1-.2-.3 0-.5.1-.6l.5-.6.3-.5c.1-.2 0-.4 0-.5L9 6.7c-.2-.6-.5-.5-.7-.5h-.6c-.2 0-.5.1-.8.4-.3.3-1 1-1 2.5s1.1 2.9 1.2 3.1c.1.2 2.1 3.2 5.1 4.5.7.3 1.3.5 1.7.6.7.2 1.4.2 1.9.1.6-.1 1.8-.7 2-1.4.2-.7.2-1.3.2-1.4-.1-.2-.3-.3-.5-.2M12 2a10 10 0 0 0-8.6 15.1L2 22l5-1.3A10 10 0 1 0 12 2m0 18.2a8.2 8.2 0 0 1-4.2-1.1l-.3-.2-3 .8.8-2.9-.2-.3A8.2 8.2 0 1 1 12 20.2")
    li = ic("M20.4 2H3.6A1.6 1.6 0 0 0 2 3.6v16.8A1.6 1.6 0 0 0 3.6 22h16.8a1.6 1.6 0 0 0 1.6-1.6V3.6A1.6 1.6 0 0 0 20.4 2M8 19H5V9.5h3M6.5 8.2a1.7 1.7 0 1 1 0-3.5 1.7 1.7 0 0 1 0 3.5M19 19h-3v-4.6c0-1.1 0-2.5-1.5-2.5s-1.8 1.2-1.8 2.4V19h-3V9.5h2.9v1.3h.1a3.1 3.1 0 0 1 2.8-1.5c3 0 3.5 2 3.5 4.5")
    x = ic("M17.5 3h3.1l-6.8 7.7L21.8 21h-6.2l-4.9-6.4L5.1 21H2l7.3-8.3L1.7 3h6.4l4.4 5.8M16.4 19.2h1.7L7 4.7H5.1")
    em = ic("M3 5h18a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1m9 7.3L20 7H4m0 11h16V8.8l-8 5.5-8-5.5")
    ln = ic("M10.6 13.4a1 1 0 0 1 0-1.4l3.4-3.4a3 3 0 0 1 4.2 4.2l-1.5 1.5-1.4-1.4 1.5-1.5a1 1 0 0 0-1.4-1.4l-3.4 3.4a1 1 0 0 0 1.4 1.4l.7-.7 1.4 1.4-.7.7a3 3 0 0 1-4.2-4.2m2.8-2.8a1 1 0 0 1 0 1.4L10 15.4a3 3 0 0 1-4.2-4.2l1.5-1.5 1.4 1.4-1.5 1.5a1 1 0 0 0 1.4 1.4l3.4-3.4")
    sh = ic("M18 16a3 3 0 0 0-2.4 1.2l-7-4.1a3 3 0 0 0 0-2.2l7-4.1A3 3 0 1 0 15 5c0 .3 0 .6.1.9l-7 4.1a3 3 0 1 0 0 4l7 4.1A3 3 0 1 0 18 16")
    return f"""<div class="share" data-url="{esc(url)}" data-text="{esc(text)}"><span class="eyebrow">Share</span>
<button type="button" class="sh sh-native" hidden>{sh}Share…</button>
<a class="sh" href="https://wa.me/?text={t}%20{q}" target="_blank" rel="noopener">{wa}WhatsApp</a>
<a class="sh" href="https://www.linkedin.com/sharing/share-offsite/?url={q}" target="_blank" rel="noopener">{li}LinkedIn</a>
<a class="sh" href="https://x.com/intent/post?url={q}&text={t}" target="_blank" rel="noopener">{x}X</a>
<a class="sh" href="mailto:?subject={t}&body={t}%0A%0A{q}">{em}Email</a>
<button type="button" class="sh sh-copy">{ln}Copy link</button></div>"""

PLAY = '<span class="play" aria-hidden="true"><svg width="26" height="26" viewBox="0 0 24 24" fill="#10282b"><path d="M7 4.5v15l13-7.5z"/></svg></span>'

def thumb(r, kind, depth=0, big_title=None):
    """kind: '16x9' or '9x16'. Returns a bare branded video thumb (with a share icon) or a placeholder."""
    b = "../" * depth
    vid = r["videos"].get(kind)
    share_url = f"{BASE_URL}/shorts/{r['slug']}" if kind == "9x16" else f"{BASE_URL}/reports/{r['slug']}"
    if vid: share_url = stamp(share_url, vid)
    ratio = "r169" if kind == "16x9" else "r916"
    brand = '<span class="brand" aria-hidden="true">Xpress<i>IQ</i></span>'
    if vid:
        return (f'<div class="thumb {ratio}" tabindex="0" role="button" aria-label="Play: {esc(vid["title"])}">'
                f'<video preload="metadata" playsinline poster="{b}{v(vid["poster"])}" src="{b}{v(vid["file"])}"></video>'
                f'{brand}{PLAY}<span class="dur">{vid["duration"]}</span>{share_overlay(share_url, vid["title"], (b + v(vid["file"])) if kind == "9x16" else "")}</div>')
    t = big_title or r["title"]
    return (f'<div class="thumb {ratio}" aria-label="{esc(t)} – video coming">'
            f'<div class="ph"><strong>{esc(t)}</strong><span>[VIDEO COMING]</span></div>{brand}{PLAY}</div>')

def tag_for(grade):
    return {"Traced":"tag-ok","Attributed":"tag-ok","Framework":"tag-hyp","Hypothesis":"tag-hyp","Not substantiated":"tag-fail","Illustrative":"tag-hyp"}.get(grade,"tag-hyp")

def report_card(r, depth=0):
    b = "../" * depth
    v = r["videos"].get("16x9")
    status = '<span class="tag tag-next">Latest</span>' if r is REPORTS[0] else (f'<span class="tag tag-soon">{esc(r["status"])}</span>' if r.get("status") else "")
    body = thumb(r, "16x9", depth)
    return f"""<article><a href="{b}reports/{r['slug']}.html" style="text-decoration:none;color:inherit">{body}</a>
<div class="meta"><span class="eyebrow">Report {r['number']:02d} · {esc(r['date_label'])}</span>{status}</div>
<h3 class="h" style="font-size:22px;font-weight:700;margin:10px 0 6px"><a href="{b}reports/{r['slug']}.html" style="text-decoration:none">{esc(r['title'])}</a></h3>
<p style="font-size:14px;line-height:1.55;color:#44585b;margin:0">{esc(r['summary'])}</p></article>"""

# ---------- products ----------
PRODUCTS = MANIFEST.get("products", [])
LOCK = '<svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" style="width:15px;height:15px"><path d="M17 9V7A5 5 0 0 0 7 7v2H6a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-9a2 2 0 0 0-2-2zm-8 0V7a3 3 0 0 1 6 0v2z"/></svg>'
ARR = '<span class="arr" aria-hidden="true">→</span>'

def pvideo(p, depth=0, i=0):
    """Explainer video slot for a product: the real video when one is set, else a branded placeholder poster."""
    b = "../" * depth
    vid = p.get("video")
    if vid:
        return (f'<div class="thumb r169" tabindex="0" role="button" aria-label="Play: {esc(vid.get("title", p["name"]))}">'
                f'<video preload="metadata" playsinline poster="{b}{v(vid["poster"])}" src="{b}{v(vid["file"])}"></video>'
                f'{PLAY}<span class="dur">{vid.get("duration","")}</span></div>')
    return (f'<div class="pposter" style="--hue:{p.get("hue",85)};--d:{i*0.7:.1f}s" role="img" aria-label="{esc(p["name"])}: explainer video coming soon">'
            f'<div class="pt"><span class="wm">Xpress<i>IQ</i></span><span class="chip">{esc(p["sector"])}</span></div>'
            f'<div><div class="nm">{esc(p["name"])}</div><div class="soon">Explainer video · coming soon</div></div>'
            f'<span class="pl" aria-hidden="true"><svg width="20" height="20" viewBox="0 0 24 24" fill="#10282b" style="width:20px;height:20px"><path d="M7 4.5v15l13-7.5z"/></svg></span></div>')

def product_card(p, i):
    cls = "pcard rv" + (" feature" if i == 0 else " tall" if i == 1 else "")
    return f"""<article class="{cls}" id="p-{p['slug']}" style="--d:{(i%3)*0.08:.2f}s">{pvideo(p, 0, i)}
<div class="pb"><div class="eyebrow">{esc(p['sector'])}</div><h3 class="h">{esc(p['name'])}</h3><p class="tl">{esc(p['tagline'])}</p><p class="ds">{esc(p['desc'])}</p>
<div class="pf"><a class="demo" href="demos#{p['slug']}">{LOCK}Open the demo</a><a class="more" href="products/{p['slug']}.html">What it does →</a></div></div></article>"""

def enquiry(product="", depth=0, uid="enq"):
    """Ask for demo access, a subscription or a white-label conversation. Posts to /api/enquiry."""
    opts = "".join(f'<option{" selected" if p["name"]==product else ""}>{esc(p["name"])}</option>' for p in PRODUCTS)
    return f"""<form data-api="/api/enquiry" data-done="Sent" data-thanks="Received. You will hear back within two working days." method="post" style="display:flex;flex-direction:column;gap:12px">
<input type="text" name="website" tabindex="-1" autocomplete="off" style="position:absolute;left:-9999px" aria-hidden="true">
<div class="field"><label for="{uid}-n">Your name</label><input id="{uid}-n" name="name" required></div>
<div class="field"><label for="{uid}-e">Email address</label><input id="{uid}-e" name="email" type="email" required></div>
<div class="field"><label for="{uid}-p">Which build</label><select id="{uid}-p" name="product">{opts}<option>More than one</option></select></div>
<div class="field"><label for="{uid}-i">What you would like</label><select id="{uid}-i" name="interest"><option>Access to the working demo</option><option>A subscription</option><option>A white-label version</option><option>Something else</option></select></div>
<button type="submit" class="btn btn-lime">Send request</button><p class="formmsg" role="status" style="font-size:14px;color:#bdf453;margin:0"></p></form>"""

def build_product(i, p):
    url = f"{BASE_URL}/products/{p['slug']}"
    does = "".join(f"<li>{esc(x)}</li>" for x in p["does"])
    nxt = PRODUCTS[(i+1) % len(PRODUCTS)]
    out = head(f"{p['name']} — {p['tagline']} | XpressIQ", p["desc"], depth=1, url=url)
    out += nav("builds", depth=1)
    out += f"""<main><section class="section wrap"><div class="phero">
<div><div class="eyebrow"><span class="dot"></span>XpressIQ build · {esc(p['sector'])}</div>
<h1 class="h">{esc(p['name'])}</h1><p class="h" style="font-size:24px;font-weight:700;color:#3f6a1a;letter-spacing:-.02em;margin:0 0 16px">{esc(p['tagline'])}</p>
<p style="font-size:18px;line-height:1.65;color:#44585b;margin:0 0 22px">{esc(p['desc'])}</p>
<div class="chips" style="margin-bottom:24px"><span class="chip">Working demo</span><span class="chip">Subscription</span><span class="chip">White-label</span></div>
<div style="display:flex;gap:12px;flex-wrap:wrap"><a class="btn btn-dark" href="../demos#{p['slug']}">{LOCK}Open the working demo</a><a class="btn btn-line" href="#access">Request access</a></div></div>
<div class="rv">{pvideo(p, 1)}</div></div></section>
<section class="section wash"><div class="wrap grid2">
<div class="rv"><div class="eyebrow">What it does</div><h2 class="h" style="font-size:38px;margin:12px 0 22px">In plain terms.</h2><ul class="does">{does}</ul></div>
<div class="rv" style="--d:.1s"><div class="eyebrow">Who it is for</div><h2 class="h" style="font-size:38px;margin:12px 0 22px">Built for.</h2>
<div class="card"><p style="font-size:17px;color:#2b3b3e">{esc(p['for'])}</p></div>
<div class="card" style="margin-top:14px"><div class="eyebrow">How you can have it</div><p style="font-size:16px;color:#2b3b3e"><strong>Subscription</strong>: use it as it is, under its own name.</p><p style="font-size:16px;color:#2b3b3e"><strong>White-label</strong>: the same build under your brand, for your own customers.</p></div></div>
</div></section>
<section class="section wrap" id="access"><div class="grid2" style="align-items:start">
<div class="rv"><div class="eyebrow"><span class="dot"></span>See it working</div><h2 class="h" style="font-size:44px;margin:12px 0 16px">The demo is real.<br>The door is locked.</h2>
<p style="font-size:17px;line-height:1.65;color:#44585b;max-width:480px">The working demo of {esc(p['name'])} sits in the XpressIQ demo room, behind a password. Ask for access and you can try it yourself, in your own time.</p>
<p style="margin-top:22px"><a href="{nxt['slug']}.html" style="font-weight:700;text-decoration:none;border-bottom:2px solid #9fb59f">Next build: {esc(nxt['name'])} →</a></p></div>
<div class="glowb lockbox rv" style="--d:.1s"><div class="eyebrow" style="color:#bdf453">Request access</div>{enquiry(p['name'], 1, 'pe')}</div>
</div></section></main>"""
    out += footer(depth=1)
    (ROOT / "products").mkdir(exist_ok=True)
    (ROOT / "products" / f"{p['slug']}.html").write_text(out)

def build_private():
    """Pages only the server may send (password-protected demo room). The server fills in the demo links."""
    d = ROOT / "private"; d.mkdir(exist_ok=True)
    rows = "".join(f"""<div class="glowb drow rv" id="{p['slug']}" style="--d:{i*0.05:.2f}s"><div><div class="eyebrow">{esc(p['sector'])}</div><h3 class="h">{esc(p['name'])}</h3><p>{esc(p['desc'])}</p></div><div class="dl"><!--DEMO:{p['slug']}--></div></div>""" for i, p in enumerate(PRODUCTS))
    out = head("Demo room — XpressIQ", "Working demos of XpressIQ builds.") + nav("demos")
    out += f"""<main class="room"><section class="section wrap"><div class="sec-head"><div><div class="eyebrow"><span class="dot"></span>Demo room · private</div><h1 class="h" style="font-size:52px;margin-top:14px">The working demos.</h1></div><p>Each button opens the live demo in a new tab. Please do not pass this page on. <a href="/demos/logout" style="color:#bdf453">Lock the room</a></p></div>{rows}</section></main>"""
    out += footer()
    (d / "demos.html").write_text(out.replace('href="index.html', 'href="/index.html').replace('href="gallery.html', 'href="/gallery.html').replace('href="commission.html', 'href="/commission.html').replace('href="privacy.html', 'href="/privacy.html').replace('href="assets/', 'href="/assets/').replace('href="demos"', 'href="/demos"'))
    out = head("Demo room — XpressIQ", "The XpressIQ demo room is private.") + nav("demos")
    out += f"""<main class="room"><section class="section wrap"><div class="grid2" style="align-items:start">
<div class="glowb lockbox"><div class="eyebrow">Demo room · private</div><h1 class="h" style="font-size:40px">Enter the password.</h1><p>The working demos are behind this door. If you have been sent a password, enter it here.</p>
<form method="post" action="/demos/login" style="display:flex;flex-direction:column;gap:12px"><input type="hidden" name="next" id="next"><div class="field"><label for="pw">Password</label><input id="pw" name="password" type="password" required autocomplete="current-password" autofocus></div><p class="err" role="alert"><!--ERR--></p><button class="btn btn-lime" type="submit">Open the demo room</button></form></div>
<div class="glowb lockbox"><div class="eyebrow">No password yet?</div><h2 class="h" style="font-size:28px">Request access.</h2><p>Say which build you want to see. A password comes back by email.</p>{enquiry("", 0, 'le')}</div>
</div></section></main><script>document.getElementById('next').value=location.hash.slice(1);</script>"""
    out += footer()
    (d / "login.html").write_text(out.replace('href="index.html', 'href="/index.html').replace('href="gallery.html', 'href="/gallery.html').replace('href="commission.html', 'href="/commission.html').replace('href="privacy.html', 'href="/privacy.html').replace('href="assets/', 'href="/assets/').replace('href="demos"', 'href="/demos"'))

# ---------- index ----------
def build_index():
    L = REPORTS[0]
    others = "".join(report_card(r) for r in REPORTS)
    cards = "".join(product_card(p, i) for i, p in enumerate(PRODUCTS))
    rows = "".join(f'<a class="row" href="#p-{p["slug"]}" style="--d:{i*2}s"><span class="n">{i+1:02d}</span><span class="nm">{esc(p["name"])}</span><span class="sc">{esc(p["sector"])}</span></a>' for i, p in enumerate(PRODUCTS))
    mq = "".join(f"<span>{esc(x)}</span>" for x in ["Fast Movers First", "Spotted early", "Demand tested", "Built and working"] + [p["name"] for p in PRODUCTS])
    def words(text, start=0):
        return " ".join(f'<span class="w"><span style="--d:{(start+k)*0.07:.2f}s">{w}</span></span>' for k, w in enumerate(text.split()))
    out = head("XpressIQ — Fast Movers First. Ideas spotted early, tested and built.", "XpressIQ finds opportunities before they are obvious, tests the demand and builds the ones that stand up. Weekly Fast Movers First reports and working demos of every build.", url=BASE_URL + "/", image=(f"{BASE_URL}/{share_img(L['videos']['16x9'])}" if L['videos'].get('16x9') else ""))
    out += nav("home")
    out += f"""<main>
<section class="hero2" id="top"><span class="blob b1"></span><span class="blob b2"></span><div class="wrap">
<div>
<div class="eyebrow"><span class="dot"></span>Fast Movers First</div>
<h1 class="h">{words("Spotted early.")}<br>{words("Tested.", 2)} <i>{words("Built.", 3)}</i></h1>
<p class="lead">XpressIQ finds opportunities before they are obvious, tests whether the demand is real, and builds the ones that stand up. The reports and the working builds are all here.</p>
<div class="acts"><a class="btn btn-lime" href="#builds">See the builds {ARR}</a><a class="btn btn-ghost" href="#reports">Read the reports</a></div>
<div class="facts"><div><div class="h">{len(PRODUCTS)}</div><small>Working builds</small></div><div><div class="h">Weekly</div><small>Fast Movers First report</small></div><div><div class="h">2 ways</div><small>Subscription or white-label</small></div></div>
</div>
<div class="glowb board" aria-label="XpressIQ builds"><div class="bh"><span>The builds</span><span class="live"><b></b>Working demos</span></div>{rows}</div>
</div></section>
<div class="marq" aria-hidden="true"><div class="track">{mq}{mq}</div></div>

<section class="section wrap" id="builds">
<div class="sec-head rv"><div><div class="eyebrow"><span class="dot"></span>The builds</div><h2 class="h">Ideas that got built.</h2></div><p>Each one started as an opportunity worth testing. Each one now works. Watch what it does, then open the demo and try it.</p></div>
<div class="pgrid">{cards}
<article class="pcard cta rv" style="--d:.16s"><div><div class="eyebrow" style="color:#bdf453">Subscription or white-label</div><h3 class="h" style="margin-top:12px">Want one of these under your own name?</h3></div><p>Every build here can be used as it is, or rebranded as yours for your own customers.</p><a class="btn btn-lime" href="#ways">How it works {ARR}</a></article>
</div></section>

<section class="section dark-sec" id="ways"><div class="wrap">
<div class="sec-head rv"><div><div class="eyebrow">Three ways in</div><h2 class="h">Use it. Brand it.<br>Or bring your own question.</h2></div><p>Start with the demo. If it fits, there is a way to have it that suits how you work.</p></div>
<div class="ways">
<div class="glowb way rv"><span class="n">01</span><h3 class="h">Subscribe</h3><p>Use a build as it stands, under its own name, for a regular fee. Nothing to set up on your side.</p><a href="demos">Open the demo room →</a></div>
<div class="glowb way rv" style="--d:.1s"><span class="n">02</span><h3 class="h">White-label</h3><p>The same working build carrying your brand, offered to your own customers as yours.</p><a href="demos">Request a white-label demo →</a></div>
<div class="glowb way rv" style="--d:.2s"><span class="n">03</span><h3 class="h">Commission a report</h3><p>Have a market or an idea of your own? Get a Fast Movers First report on whether it stands up.</p><a href="commission.html">Start a report enquiry →</a></div>
</div></div></section>

<section class="section wrap" id="reports">
<div class="sec-head rv"><div><div class="eyebrow"><span class="dot"></span>Fast Movers First reports</div><h2 class="h">Find out before<br>it's obvious.</h2></div><p>One report a week on what is changing in UK business, with the evidence graded and the next move named. Every build above began as a question like these.</p></div>
<div class="featrep rv" id="latest"><div>{thumb(L,'16x9')}</div>
<div><div class="meta" style="margin-top:0;justify-content:flex-start"><span class="tag tag-next">Latest</span><span class="eyebrow">Report {L['number']:02d} · {esc(L['date_label'])}</span></div>
<h3 class="h" style="font-size:34px;margin:14px 0 12px">{esc(L['title'])}</h3><p style="color:#53666a;line-height:1.65;font-size:16px;margin:0 0 18px">{esc(L['summary'])}</p>
<a class="btn btn-dark" href="reports/{L['slug']}.html">Read the full report {ARR}</a></div></div>
<div class="grid3">{others}</div>
</section>

<section class="cta" id="subscribe"><div class="wrap cta-grid">
<div class="rv">{optin()}</div>
<div class="panel-light rv" style="--d:.1s"><div class="eyebrow">Your own question</div><h2 class="h" style="font-size:32px">Commission a Fast Movers First report.</h2><p>A market, a sector or an idea you cannot stop thinking about, researched, graded and ended with the next move. Delivered as a written report and two videos.</p><a href="commission.html" class="btn btn-dark" style="align-self:flex-start;margin-top:auto">Start a report enquiry</a></div>
</div></section>
</main>"""
    out += footer()
    (ROOT / "index.html").write_text(out)

# ---------- gallery ----------
def build_gallery():
    items = []
    for r in REPORTS:
        v = r["videos"].get("9x16")
        items.append(f"""<article>{thumb(r,'9x16')}
<div class="meta"><span class="eyebrow">Report {r['number']:02d} · {esc(r['date_label'])}</span>{'<span class="tag tag-next">Ready</span>' if v else '<span class="tag tag-soon">Coming soon</span>'}</div>
<h3 class="h">{esc(v['title'] if v else r['title'])}</h3><p>{esc(r['summary'])}</p>
<div style="display:flex;gap:18px;flex-wrap:wrap;align-items:center"><a class="link" href="reports/{r['slug']}.html">Read the full report →</a>{('<a class="link" href="shorts/' + r['slug'] + '.html">Open the short →</a>') if v else ''}</div>
</article>""")
    out = head("XpressIQ Shorts — the report in a minute or two", "Portrait video summaries of every Fast Movers First report.")
    out += nav("gallery")
    out += f"""<main><section class="section wrap"><div class="sec-head"><div><div class="eyebrow"><span class="dot"></span>Shorts</div><h2 class="h">The report, in a minute or two.</h2></div><p>Portrait summaries of each Fast Movers First report, for the people who move before they have read the full thing. Each one links to its report and sources.</p></div>
<div class="gallery">{''.join(items)}</div></section></main>"""
    out += footer()
    (ROOT / "gallery.html").write_text(out)

# ---------- commission ----------
def build_commission():
    out = head("Commission a Fast Movers First report — XpressIQ", "Put your own market, sector or idea through the XpressIQ method: researched, traced, graded, ended with the next move.")
    out += nav("commission")
    out += f"""<main><section class="section wrap"><div class="grid2">
<div><div class="eyebrow"><span class="dot"></span>Commission a report</div><h1 class="h" style="font-size:52px;margin:14px 0 18px">Your question.<br>Same method.</h1>
<p style="font-size:18px;line-height:1.65;color:#44585b;max-width:520px">Every Fast Movers First report follows one process. Commissioned reports follow it too: your market, sector or idea is researched across sources, written up as a single source of truth with every claim traced and graded, then delivered as a written report with a full video briefing and a short.</p>
<div class="grid3" style="margin-top:28px;gap:12px">
<div class="card"><div class="eyebrow">01</div><h3 class="h" style="font-size:18px">The question</h3><p>A market, a sector, a competitor, a regulation or an idea you cannot stop thinking about.</p></div>
<div class="card"><div class="eyebrow">02</div><h3 class="h" style="font-size:18px">The decision</h3><p>What you need to decide once you have the answer. The report is built to support that decision.</p></div>
<div class="card"><div class="eyebrow">03</div><h3 class="h" style="font-size:18px">The timeframe</h3><p>When you need it. Most reports turn around inside a week.</p></div>
</div>
<p style="font-size:14px;color:#5d7073;margin-top:24px">Pricing is agreed per report once the scope is clear. Commissioned reports are private to you unless you choose to publish them.</p>
</div>
<div class="panel-light"><div class="eyebrow">Start a report enquiry</div>
<form data-api="/api/commission" data-done="Sent" data-thanks="Received. You will hear back within two working days." method="post" style="display:flex;flex-direction:column;gap:14px" id="contact">
<input type="text" name="website" tabindex="-1" autocomplete="off" style="position:absolute;left:-9999px" aria-hidden="true">
<div class="field"><label for="name">Your name</label><input id="name" name="name" required></div>
<div class="field"><label for="org">Company or organisation</label><input id="org" name="company"></div>
<div class="field"><label for="from">Email address</label><input id="from" name="email" type="email" required></div>
<div class="field"><label for="q">The idea, market or question</label><textarea id="q" name="question" required></textarea></div>
<div class="field"><label for="d">What you need to decide</label><textarea id="d" name="decision"></textarea></div>
<div class="field"><label for="t">Preferred timeframe</label><select id="t" name="timeframe"><option>Within a week</option><option>Within two weeks</option><option>Within a month</option><option>No fixed date</option></select></div>
<button type="submit" class="btn btn-dark">Send enquiry</button>
<p class="formmsg" role="status" style="font-size:14px;color:#3f6a1a;margin:0"></p>
<p style="font-size:13px;color:#5d7073;margin:0">Replies come from XpressIQ within two working days. Nothing you send is shared.</p>
</form></div>
</div></section></main>"""
    out += footer()
    (ROOT / "commission.html").write_text(out)

# ---------- report pages ----------
def md_to_html(text):
    # strip ?utm_source tracking, leave links
    text = re.sub(r"\?utm_source=chatgpt\.com", "", text)
    h = markdown.markdown(text, extensions=["tables", "sane_lists"])
    h = h.replace("<table>", '<div class="tablewrap"><table>').replace("</table>", "</table></div>")
    # drop the document's own H1 (page supplies it)
    h = re.sub(r"<h1>.*?</h1>\s*", "", h, count=1, flags=re.S)
    return h

def build_report(i, r):
    prev_r = REPORTS[i+1] if i+1 < len(REPORTS) else None
    next_r = REPORTS[i-1] if i-1 >= 0 else None
    body = md_to_html((ROOT / "reports" / f"{r['slug']}.md").read_text()) if (ROOT / "reports" / f"{r['slug']}.md").exists() else f'<p class="srcnote">Written report to follow. The videos above carry this week\'s findings.</p>'
    # opt-in after the first main section; members gate when access != free
    parts = re.split(r'(?=<h2>)', body)
    if r.get("access", "free") != "free" and len(parts) > 2:
        teaser = "".join(parts[:2])
        body = teaser + f"""<div class="gate"><div class="eyebrow">Members' report</div><h3 class="h" style="font-size:26px;margin:10px 0 8px">The rest of this report is for XpressIQ members.</h3><p>{esc(SITE.get('members_copy','Members get every Fast Movers First report in full, with the evidence grades and sources, the week it is published.'))}</p><a class="btn btn-lime" href="{SITE.get('members_url','../commission.html')}">Become a member</a></div>"""
    elif len(parts) > 2:
        body = "".join(parts[:2]) + optin(1, r['slug'], compact=True) + "".join(parts[2:])
    grades = "".join(f'<div class="grade" style="border-color:#dce4dc"><span class="tag {tag_for(g["grade"])}">{esc(g["grade"])}</span><div><strong style="font-family:Manrope,sans-serif;font-size:16px;font-weight:700;display:block;margin-bottom:4px">{esc(g["claim"])}</strong><span style="color:#53666a;font-size:14px;line-height:1.5">{esc(g["note"])}</span></div></div>' for g in r.get("grades",[]))
    pager = f'<div class="pager"><span>{("<a href=\"" + prev_r["slug"] + ".html\">← Previous: " + esc(prev_r["title"]) + "</a>") if prev_r else ""}</span><span>{("<a href=\"" + next_r["slug"] + ".html\">Next: " + esc(next_r["title"]) + " →</a>") if next_r else "<a href=\"../index.html#subscribe\">Get next week's report →</a>"}</span></div>'
    url = f"{BASE_URL}/reports/{r['slug']}"
    v16 = r["videos"].get("16x9")
    out = head(f"{r['title']} — XpressIQ Fast Movers First report {r['number']:02d}", r["summary"], depth=1, url=url, image=(f"{BASE_URL}/{share_img(v16)}" if v16 else ""))
    out += nav("reports", depth=1)
    out += f"""<main><section class="section wrap"><article class="report">
<div class="eyebrow"><span class="dot"></span>Fast Movers First · Report {r['number']:02d} · {esc(r['date_label'])}</div>
<h1 class="h">{esc(r['title'])}</h1>
<p class="byline">{esc(r['standfirst'])}</p>
<div style="margin:36px 0 44px">{thumb(r,'16x9',1)}<div class="meta"><span class="eyebrow">Full briefing · {r['videos'].get('16x9',{}).get('duration','coming')}</span><a href="../gallery.html" style="font-size:14px;font-weight:700;text-decoration:none;border-bottom:2px solid #9fb59f">The short version is in Shorts →</a></div></div>
{('<div class="eyebrow" style="margin-bottom:6px">Evidence grades</div><div class="grades" style="border-color:#dce4dc">' + grades + '</div>') if grades else ''}
{('<blockquote><p><strong>The next move. </strong>' + esc(r['next_move']) + '</p></blockquote>') if r.get('next_move') else ''}
{body}
{optin(1, r['slug'])}
{pager}
</article></section></main>"""
    out += footer(depth=1)
    (ROOT / "reports" / f"{r['slug']}.html").write_text(out)

def build_short(r):
    vid = r["videos"].get("9x16")
    if not vid: return
    url = f"{BASE_URL}/shorts/{r['slug']}"
    out = head(f"{vid['title']} — XpressIQ short", r["summary"], depth=1, url=url, image=f"{BASE_URL}/{share_img(vid)}")
    out += nav("gallery", depth=1)
    out += f"""<main><section class="section wrap"><div class="grid2" style="align-items:start;max-width:980px;margin:0 auto">
<div style="max-width:420px;margin:0 auto;width:100%">{thumb(r,'9x16',1)}</div>
<div><div class="eyebrow"><span class="dot"></span>Fast Movers First · Report {r['number']:02d} · {esc(r['date_label'])} · {vid['duration']}</div>
<h1 class="h" style="font-size:40px;margin:14px 0 14px">{esc(vid['title'])}</h1>
<p style="font-size:17px;line-height:1.65;color:#44585b">{esc(r['summary'])}</p>
<a class="btn btn-dark" href="../reports/{r['slug']}.html" style="margin-top:8px">Read the full report and sources</a>
<div style="margin-top:36px">{optin(1, r['slug'], compact=True)}</div>
</div></div></section></main>"""
    out += footer(depth=1)
    (ROOT / "shorts").mkdir(exist_ok=True)
    (ROOT / "shorts" / f"{r['slug']}.html").write_text(out)

def build_privacy():
    out = head("Privacy — XpressIQ", "How XpressIQ handles the information you give it.")
    out += nav("", 0)
    out += f"""<main><section class="section wrap"><article class="report"><h1 class="h" style="font-size:40px">Privacy</h1>
<p>XpressIQ ({SITE['company']}) collects an email address when you subscribe to the weekly report, and the details you choose to send when you enquire about a commissioned report. That information is used only to send you the report or reply to your enquiry. It is not sold or shared. You can unsubscribe from any email in one click, or ask for your details to be deleted by replying to any XpressIQ email or using the <a href="commission.html#contact">contact form</a>.</p>
<p>Videos on this site are hosted on this site. No advertising trackers are used.</p></article></section></main>"""
    out += footer()
    (ROOT / "privacy.html").write_text(out)

if __name__ == "__main__":
    build_index(); build_gallery(); build_commission(); build_privacy(); build_private()
    for i, p in enumerate(PRODUCTS): build_product(i, p)
    for i, r in enumerate(REPORTS): build_report(i, r); build_short(r)
    print("built:", [p.name for p in ROOT.glob("*.html")], [p.name for p in (ROOT/"reports").glob("*.html")])
