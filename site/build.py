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
    st = f.stat(); h = hashlib.md5(f"{st.st_size}-{int(st.st_mtime)}".encode()).hexdigest()[:8]
    return f"{path}?v={h}"

def head(title, desc, depth=0, url="", image="", video=""):
    base = "../" * depth
    og = f'<meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}"><meta property="og:site_name" content="XpressIQ"><meta property="og:type" content="{'video.other' if video else 'website'}">'
    if url: og += f'<meta property="og:url" content="{esc(url)}">'
    if image: og += f'<meta property="og:image" content="{esc(image)}"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:image" content="{esc(image)}">'
    if video: og += f'<meta property="og:video" content="{esc(video)}"><meta property="og:video:type" content="video/mp4">'
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title><meta name="description" content="{esc(desc)}">{og}
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@500;700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{base}assets/site.css"></head><body>"""

def nav(active, depth=0):
    b = "../" * depth
    def a(href, label, key):
        on = ' class="on"' if key == active else ""
        return f'<a href="{b}{href}"{on}>{label}</a>'
    return f"""<header class="nav"><div class="wrap">
<a class="logo" href="{b}index.html"><span class="h">Xpress<i>IQ</i><b></b></span><small>Fast Movers First</small></a>
<nav class="navlinks" aria-label="Main navigation">{a('index.html#latest','Latest report','home')}{a('index.html#reports','All reports','reports')}{a('gallery.html','Shorts','gallery')}{a('commission.html','Commission a report','commission')}</nav>
<a class="btn btn-dark navcta" href="{b}index.html#subscribe">Get the weekly report</a>
</div></header>"""

def footer(depth=0):
    b = "../" * depth
    y = datetime.date.today().year
    return f"""<footer class="footer"><div class="wrap">
<div><a class="logo" href="{b}index.html"><span class="h">Xpress<i style="color:#bdf453">IQ</i></span><small>Fast Movers First</small></a><p style="margin:8px 0 0">Intelligence delivered before you knew you needed it.</p></div>
<div style="display:flex;gap:24px;flex-wrap:wrap"><a href="{b}index.html#latest">Latest</a><a href="{b}gallery.html">Shorts</a><a href="{b}commission.html">Commission a report</a><a href="{b}commission.html#contact">Contact</a></div>
<p style="margin:0;color:#7f9690">© {y} {SITE['company']} · <a href="{b}privacy.html">Privacy</a></p>
</div></footer>
<script>
document.querySelectorAll('.thumb').forEach(t=>{{const v=t.querySelector('video');if(!v)return;t.addEventListener('click',e=>{{if(e.target.closest('.rail'))return;if(t.classList.contains('playing'))return;t.classList.add('playing');v.controls=true;v.play();}});v.addEventListener('ended',()=>{{t.classList.remove('playing');v.controls=false;}});
const b=t.querySelector('.ri-share');if(!b)return;b.addEventListener('click',async e=>{{e.stopPropagation();const url=b.dataset.url,text=b.dataset.text;if(navigator.share){{try{{await navigator.share({{title:text,text:text,url:url}});return;}}catch(err){{if(err&&err.name==='AbortError')return;}}}}try{{await navigator.clipboard.writeText(url);const l=b.querySelector('span');l.textContent='Copied';setTimeout(()=>l.textContent='Share',1500);}}catch(err){{prompt('Copy this link',url);}}}});}});
document.querySelectorAll('form[data-api]').forEach(f=>{{f.addEventListener('submit',async e=>{{e.preventDefault();const btn=f.querySelector('button[type=submit]');const msg=f.querySelector('.formmsg');const data=Object.fromEntries(new FormData(f).entries());btn.disabled=true;try{{const r=await fetch(f.dataset.api,{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify(data)}});const j=await r.json();if(j.ok){{f.querySelectorAll('input,textarea,select').forEach(i=>i.disabled=true);btn.textContent=f.dataset.done||'Done';msg.textContent=f.dataset.thanks||'Thank you.';}}else{{msg.textContent=j.error||'Something went wrong. Please try again.';btn.disabled=false;}}}}catch(err){{msg.textContent='Could not send just now. Please try again in a moment.';btn.disabled=false;}}}});}});
</script></body></html>"""

def optin(depth=0, report_slug="", compact=False):
    """Email opt-in form posting to /api/subscribe. Used on the home page and inside every report."""
    hid = f'<input type="hidden" name="report" value="{esc(report_slug)}">' if report_slug else ""
    head_h = '<h2 class="h" style="font-size:40px">Fast movers first.<br>Everyone else, later.</h2>' if not compact else '<h3 class="h" style="font-size:24px;margin:0">Get the next report before it is obvious.</h3>'
    para = "One email a week with the report, both videos and the sources. No digest, no filler. Unsubscribe in one click." if not compact else "One email a week: the report, both videos, the sources. Unsubscribe in one click."
    return f"""<div class="panel-dark optin{' compact' if compact else ''}"><div class="eyebrow">Get the weekly report</div>{head_h}<p>{para}</p>
<form data-api="/api/subscribe" data-done="Subscribed" data-thanks="You're on the list. The next report comes to your inbox." method="post" style="display:flex;gap:10px;flex-wrap:wrap;margin-top:8px">{hid}<input type="text" name="website" tabindex="-1" autocomplete="off" style="position:absolute;left:-9999px" aria-hidden="true"><label for="email-{report_slug or 'home'}" style="position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)">Email address</label><input id="email-{report_slug or 'home'}" name="email" type="email" placeholder="you@company.co.uk" required style="flex:1 1 220px;min-height:48px;padding:0 16px;border-radius:6px;border:1px solid #4e6b67;background:#0b1f22;color:#fff"><button type="submit" class="btn btn-lime">Send me the report</button><p class="formmsg" role="status" style="flex-basis:100%;margin:0;font-size:14px;color:#bdf453"></p></form>
<p style="font-size:12px;color:#8fa8a0">For founders, owners, investors and advisers who move on opportunity.</p></div>"""

def _ic(d): return f'<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="{d}"/></svg>'
ICONS = {
 "share": _ic("M18 16a3 3 0 0 0-2.4 1.2l-7-4.1a3 3 0 0 0 0-2.2l7-4.1A3 3 0 1 0 15 5c0 .3 0 .6.1.9l-7 4.1a3 3 0 1 0 0 4l7 4.1A3 3 0 1 0 18 16"),
 "wa": _ic("M17.5 14.4c-.3-.1-1.8-.9-2-1-.3-.1-.5-.1-.7.1-.2.3-.8 1-1 1.2-.2.2-.4.2-.7.1-.3-.1-1.3-.5-2.4-1.5-.9-.8-1.5-1.8-1.7-2.1-.2-.3 0-.5.1-.6l.5-.6.3-.5c.1-.2 0-.4 0-.5L9 6.7c-.2-.6-.5-.5-.7-.5h-.6c-.2 0-.5.1-.8.4-.3.3-1 1-1 2.5s1.1 2.9 1.2 3.1c.1.2 2.1 3.2 5.1 4.5.7.3 1.3.5 1.7.6.7.2 1.4.2 1.9.1.6-.1 1.8-.7 2-1.4.2-.7.2-1.3.2-1.4-.1-.2-.3-.3-.5-.2M12 2a10 10 0 0 0-8.6 15.1L2 22l5-1.3A10 10 0 1 0 12 2m0 18.2a8.2 8.2 0 0 1-4.2-1.1l-.3-.2-3 .8.8-2.9-.2-.3A8.2 8.2 0 1 1 12 20.2"),
 "li": _ic("M20.4 2H3.6A1.6 1.6 0 0 0 2 3.6v16.8A1.6 1.6 0 0 0 3.6 22h16.8a1.6 1.6 0 0 0 1.6-1.6V3.6A1.6 1.6 0 0 0 20.4 2M8 19H5V9.5h3M6.5 8.2a1.7 1.7 0 1 1 0-3.5 1.7 1.7 0 0 1 0 3.5M19 19h-3v-4.6c0-1.1 0-2.5-1.5-2.5s-1.8 1.2-1.8 2.4V19h-3V9.5h2.9v1.3h.1a3.1 3.1 0 0 1 2.8-1.5c3 0 3.5 2 3.5 4.5"),
 "x": _ic("M17.5 3h3.1l-6.8 7.7L21.8 21h-6.2l-4.9-6.4L5.1 21H2l7.3-8.3L1.7 3h6.4l4.4 5.8M16.4 19.2h1.7L7 4.7H5.1"),
 "em": _ic("M3 5h18a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1m9 7.3L20 7H4m0 11h16V8.8l-8 5.5-8-5.5"),
 "ln": _ic("M10.6 13.4a1 1 0 0 1 0-1.4l3.4-3.4a3 3 0 0 1 4.2 4.2l-1.5 1.5-1.4-1.4 1.5-1.5a1 1 0 0 0-1.4-1.4l-3.4 3.4a1 1 0 0 0 1.4 1.4l.7-.7 1.4 1.4-.7.7a3 3 0 0 1-4.2-4.2m2.8-2.8a1 1 0 0 1 0 1.4L10 15.4a3 3 0 0 1-4.2-4.2l1.5-1.5 1.4 1.4-1.5 1.5a1 1 0 0 0 1.4 1.4l3.4-3.4"),
}

def share_overlay(url, text):
    """YouTube-style action rail down the right edge of a video: Share (system share sheet, or copy link),
    WhatsApp, X, LinkedIn. Always visible, including during playback."""
    import urllib.parse as u
    q = u.quote(url, safe=""); t = u.quote(text, safe="")
    def item(tag, inner, cls="", attrs=""):
        return f'<{tag} class="ri {cls}" {attrs}>{inner}</{tag}>'
    return ('<div class="rail" role="group" aria-label="Share this video">'
            + item("button", f'{ICONS["share"]}<span>Share</span>', "ri-share", f'type="button" data-url="{esc(url)}" data-text="{esc(text)}" aria-label="Share"')
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
    ratio = "r169" if kind == "16x9" else "r916"
    brand = '<span class="brand" aria-hidden="true">Xpress<i>IQ</i></span>'
    if vid:
        return (f'<div class="thumb {ratio}" tabindex="0" role="button" aria-label="Play: {esc(vid["title"])}">'
                f'<video preload="metadata" playsinline poster="{b}{v(vid["poster"])}" src="{b}{v(vid["file"])}"></video>'
                f'{brand}{PLAY}<span class="dur">{vid["duration"]}</span>{share_overlay(share_url, vid["title"])}</div>')
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

# ---------- index ----------
def build_index():
    L = REPORTS[0]
    grades = "".join(f'<div class="grade"><span class="tag {tag_for(g["grade"])}">{esc(g["grade"])}</span><div><strong>{esc(g["claim"])}</strong><span>{esc(g["note"])}</span></div></div>' for g in L["grades"])
    others = "".join(report_card(r) for r in REPORTS)
    radar = "".join(f'<div style="display:flex;justify-content:space-between;gap:16px;padding:17px 0;border-bottom:1px solid #d3dfd2;align-items:center"><div style="display:flex;gap:16px;align-items:baseline"><span style="color:#80a850;font-size:12px;font-weight:700;font-family:Manrope,sans-serif">{i+1:02d}</span><strong style="font-size:16px">{esc(x)}</strong></div><span class="tag tag-hyp">Hypothesis</span></div>' for i,x in enumerate(MANIFEST["radar"]))
    half = (len(MANIFEST["radar"])+1)//2
    radar_items = [f'<div style="display:flex;justify-content:space-between;gap:16px;padding:17px 0;border-bottom:1px solid #d3dfd2;align-items:center"><div style="display:flex;gap:16px;align-items:baseline"><span style="color:#80a850;font-size:12px;font-weight:700;font-family:Manrope,sans-serif">{i+1:02d}</span><strong style="font-size:16px">{esc(x)}</strong></div><span class="tag tag-hyp">Hypothesis</span></div>' for i,x in enumerate(MANIFEST["radar"])]
    radar_html = f'<div class="grid2" style="gap:0 48px"><div style="border-top:1px solid #d3dfd2">{"".join(radar_items[:half])}</div><div style="border-top:1px solid #d3dfd2">{"".join(radar_items[half:])}</div></div>'
    nx = MANIFEST["next"]
    out = head(f"XpressIQ — Fast Movers First. {L['title']}", "Weekly intelligence reports for people who move on opportunity. Every claim traced, every finding graded, every report ends with a next move.", url=BASE_URL + "/", image=(f"{BASE_URL}/{L['videos']['16x9']['poster']}" if L['videos'].get('16x9') else ""))
    out += nav("home")
    out += f"""<main>
<section class="wrap hero" id="top">
<div>
<div class="eyebrow"><span class="dot"></span>Fast intel. One report, two videos. Every week.</div>
<h1 class="h">Find out before<br>it's <i>obvious.</i></h1>
<p class="lead">Intelligence delivered before you knew you needed it.<span class="copy-lead"> By the time an opportunity is in the trade press, the fast movers have already moved. XpressIQ traces what is changing in UK business, grades the evidence and names the next move worth testing.</span></p>
<div class="stats copy-lead"><div><div class="h">1 report</div><div>Every week</div></div><div><div class="h">2 videos</div><div>Full briefing and a short</div></div><div><div class="h">3 grades</div><div>Traced · Framework · Not substantiated</div></div></div>
</div>
<div id="latest">
{thumb(L,'16x9')}
<div class="meta"><span class="eyebrow">Report {L['number']:02d} · {esc(L['date_label'])}</span><span class="tag tag-next">Latest</span></div>
<h2 class="h" style="font-size:22px;font-weight:700;margin:10px 0 6px;line-height:1.25">{esc(L['title'])}</h2>
<p style="color:#53666a;line-height:1.6;font-size:14px;margin:0">{esc(L['summary'])}</p>
<a href="reports/{L['slug']}.html" style="display:inline-block;color:#3f6a1a;font-size:14px;font-weight:700;margin-top:12px;text-decoration:none">Read the full report →</a>
<div class="after"><p class="lead" style="margin-top:24px">By the time an opportunity is in the trade press, the fast movers have already moved. XpressIQ traces what is changing in UK business, grades the evidence and names the next move worth testing.</p>
<div class="stats"><div><div class="h">1 report</div><div>Every week</div></div><div><div class="h">2 videos</div><div>Full and short</div></div><div><div class="h">Traced</div><div>Every claim</div></div></div></div>
</div>
</section>
<div class="ticker"><div class="wrap"><span>FAST MOVERS FIRST</span><span>EVERY CLAIM TRACED TO ITS SOURCE</span><span>EVERY FINDING GRADED</span><span>EVERY REPORT ENDS WITH A NEXT MOVE</span></div></div>

<section class="section dark-sec" id="this-week"><div class="wrap">
<div class="sec-head"><div><div class="eyebrow">Report {L['number']:02d} · what the evidence supports</div><h2 class="h">{esc(L['title'])}</h2></div><p>{esc(L['standfirst'])}</p></div>
<div class="grid2">
<div class="short">{thumb(L,'9x16')}<div class="meta"><span class="eyebrow" style="color:#9fb5ad">The short · {L['videos'].get('9x16',{}).get('duration','')}</span><p style="color:#c0d0c9;line-height:1.7;font-size:16px;margin:0">{esc(L['summary'])}</p><a class="btn btn-lime" href="reports/{L['slug']}.html">Read the full report</a></div></div>
<div><div class="eyebrow" style="color:#9fb5ad;margin-bottom:6px">Evidence grades</div><div class="grades">{grades}</div>
<div class="nextmove"><div class="eyebrow">The next move</div><p>{esc(L['next_move'])}</p><a href="commission.html" class="btn btn-lime" style="margin-top:18px">Discuss this with XpressIQ</a></div></div>
</div></div></section>

<section class="section wrap" id="reports">
<div class="sec-head"><div><div class="eyebrow"><span class="dot"></span>Fast Movers First reports</div><h2 class="h">One report a week.<br>The archive builds itself.</h2></div><p>Every report stays available with its sources, its evidence grades and both videos, so you can check how a call has aged.</p></div>
<div class="grid3">{others}</div>
</section>





<section class="cta" id="subscribe"><div class="wrap cta-grid">
{optin()}
<div class="panel-light"><div class="eyebrow">Need the method on your own question?</div><h2 class="h" style="font-size:32px">Commission a Fast Movers First report.</h2><p>A market, a sector or an idea you cannot stop thinking about, put through the same process: researched, traced, graded and ended with the next move. Delivered as a written report and two videos.</p><a href="commission.html" class="btn btn-dark" style="align-self:flex-start;margin-top:auto">Start a report enquiry</a></div>
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
    out = head(f"{r['title']} — XpressIQ Fast Movers First report {r['number']:02d}", r["summary"], depth=1, url=url, image=(f"{BASE_URL}/{v16['poster']}" if v16 else ""), video=(f"{BASE_URL}/{v16['file']}" if v16 else ""))
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
    out = head(f"{vid['title']} — XpressIQ short", r["summary"], depth=1, url=url, image=f"{BASE_URL}/{vid['poster']}", video=f"{BASE_URL}/{vid['file']}")
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
    build_index(); build_gallery(); build_commission(); build_privacy()
    for i, r in enumerate(REPORTS): build_report(i, r); build_short(r)
    print("built:", [p.name for p in ROOT.glob("*.html")], [p.name for p in (ROOT/"reports").glob("*.html")])
