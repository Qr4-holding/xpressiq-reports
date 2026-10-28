#!/usr/bin/env python3
"""XpressIQ Fast Movers First — intro/outro wrapper.

Usage:
  python3 wrap.py render-cards --config config.json --out build/
  python3 wrap.py wrap --config config.json --video in.mp4 --out out.mp4 \
        [--title-vo title.mp3]

Renders a branded intro (logo + strapline + report title) and outro (logo,
contact email, copyright, one-line CTA) as PNG frame sequences with Pillow,
turns them into clips with ffmpeg, lays the voiceover under them, and
concatenates intro + source video + outro. Works for 16:9 and 9:16 — the
source video's size decides the card size.
"""
import argparse, json, math, pathlib, subprocess, sys, tempfile

from PIL import Image, ImageDraw, ImageFont

HERE = pathlib.Path(__file__).parent

# ---------- helpers ----------
def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode != 0:
        print(r.stderr[-4000:], file=sys.stderr); raise SystemExit(f"command failed: {cmd[0]}")
    return r.stdout

def probe(path):
    out = run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
               "stream=width,height,r_frame_rate:format=duration", "-of", "json", str(path)])
    j = json.loads(out); s = j["streams"][0]
    num, den = s["r_frame_rate"].split("/"); fps = float(num) / float(den)
    return int(s["width"]), int(s["height"]), fps, float(j["format"]["duration"])

def audio_len(path):
    return float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)]).strip())

def font(cfg, key, size):
    return ImageFont.truetype(cfg["fonts"][key], size)

def ease(t):  # smoothstep
    t = max(0.0, min(1.0, t)); return t * t * (3 - 2 * t)

def hexrgb(h):
    h = h.lstrip("#"); return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def wrap_text(draw, text, fnt, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=fnt) <= max_w: cur = t
        else: lines.append(cur); cur = w
    if cur: lines.append(cur)
    return lines

def draw_logo(draw, cfg, x, y, size, color_ink, color_accent, dot=True):
    f = font(cfg, "display", size)
    draw.text((x, y), "Xpress", font=f, fill=color_ink)
    wx = draw.textlength("Xpress", font=f)
    draw.text((x + wx, y), "IQ", font=f, fill=color_accent)
    if dot:
        wq = draw.textlength("IQ", font=f); r = size * 0.11
        cx = x + wx + wq + size * 0.22; cy = y + size * 0.62
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=hexrgb(cfg["colors"]["lime"]))
    return draw.textlength("XpressIQ", font=f)

# ---------- cards ----------
def draw_intro_card(cfg, W, H, title, play=False):
    """One fully drawn intro card: used for every intro frame and, with play=True, as the poster."""
    C = cfg["colors"]; bg = hexrgb(C["dark"]); ink = (255, 255, 255); lime = hexrgb(C["lime"])
    portrait = H > W
    S = W / 1280 if not portrait else W / 720
    logo_size = int((120 if not portrait else 84) * S)
    im = Image.new("RGB", (W, H), bg); d = ImageDraw.Draw(im)
    rule_y = int(H * (0.37 if not portrait else 0.33))
    d.rectangle((int(W * 0.08), rule_y, int(W * 0.92), rule_y + max(2, int(3 * S))), fill=lime)
    draw_logo(d, cfg, int(W * 0.08), rule_y - int(logo_size * 1.25), logo_size, ink, lime)
    f = font(cfg, "display", int((28 if not portrait else 24) * S))
    d.text((int(W * 0.08), rule_y + int(26 * S)), cfg["strapline"], font=f, fill=lime)
    if title:
        f = font(cfg, "display", int((56 if not portrait else 44) * S))
        lines = wrap_text(d, title, f, int(W * 0.84))
        yy = rule_y + int((90 if not portrait else 84) * S); lh = int(f.size * 1.12)
        for ln in lines:
            d.text((int(W * 0.08), yy), ln, font=f, fill=ink); yy += lh
        fe = font(cfg, "display", int((18 if not portrait else 16) * S))
        d.text((int(W * 0.08), yy + int(18 * S)), cfg["series_label"].upper(), font=fe, fill=(159, 181, 173))
    if play:
        # lime play button, bottom-right, with a soft shadow: the cover thumb reads as a video at a glance
        r = int((54 if not portrait else 46) * S)
        cx = (W - int(W * 0.08) - r) if not portrait else (int(W * 0.08) + r); cy = H - int(H * (0.10 if not portrait else 0.08)) - r
        sh = Image.new("RGBA", (W, H), (0, 0, 0, 0)); sd = ImageDraw.Draw(sh)
        sd.ellipse((cx - r, cy - r + int(6 * S), cx + r, cy + r + int(6 * S)), fill=(0, 0, 0, 90))
        from PIL import ImageFilter
        sh = sh.filter(ImageFilter.GaussianBlur(int(10 * S)))
        im.paste(sh, (0, 0), sh); d = ImageDraw.Draw(im)
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=lime)
        t = r * 0.52
        d.polygon([(cx - t * 0.7, cy - t), (cx - t * 0.7, cy + t), (cx + t * 0.95, cy)], fill=bg)
    return im

def render_intro_frames(cfg, W, H, fps, dur, title, outdir):
    """Silent motion intro. Frame 0 is the complete card (so it doubles as the thumbnail);
    the lime rule then re-sweeps left to right, the dot pops, and the card fades to the video."""
    C = cfg["colors"]; bg = hexrgb(C["dark"]); lime = hexrgb(C["lime"])
    portrait = H > W
    S = W / 1280 if not portrait else W / 720
    logo_size = int((120 if not portrait else 84) * S)
    rule_y = int(H * (0.37 if not portrait else 0.33)); rh = max(2, int(3 * S))
    x0, x1 = int(W * 0.08), int(W * 0.92)
    card = draw_intro_card(cfg, W, H, title)
    # dot position (mirrors draw_logo)
    fL = font(cfg, "display", logo_size); d0 = ImageDraw.Draw(card)
    wx = d0.textlength("Xpress", font=fL) + d0.textlength("IQ", font=fL)
    r = logo_size * 0.11; cx = x0 + wx + logo_size * 0.22; cy = (rule_y - int(logo_size * 1.25)) + logo_size * 0.62
    dark = Image.new("RGB", (W, H), bg)
    n = int(dur * fps)
    sweep_start, sweep_len = 0.15, 0.7
    for i in range(n):
        t = i / fps
        im = card.copy(); d = ImageDraw.Draw(im)
        if sweep_start <= t < sweep_start + sweep_len + 0.05:
            # wipe the rule and redraw it growing, with a bright head
            a = ease((t - sweep_start) / sweep_len)
            d.rectangle((x0, rule_y, x1, rule_y + rh), fill=bg)
            xe = int(x0 + (x1 - x0) * a)
            d.rectangle((x0, rule_y, xe, rule_y + rh), fill=lime)
            d.rectangle((max(x0, xe - int(28 * S)), rule_y - rh, xe, rule_y + 2 * rh), fill=(234, 255, 180))
        # dot pop: shrinks then overshoots back
        if 0.3 <= t < 1.3:
            u = (t - 0.3) / 1.0; k = ease(u); scale = 0.2 + 1.0 * k + 0.25 * math.sin(math.pi * u) * (1 - k)
            rr = r * scale
            d.ellipse((cx - r * 1.3, cy - r * 1.3, cx + r * 1.3, cy + r * 1.3), fill=bg)
            d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=lime)
        fo = ease((dur - t) / 0.35)
        if fo < 1: im = Image.blend(dark, im, fo)
        im.save(outdir / f"i{i:05d}.png")
    return n

def render_outro_frames(cfg, W, H, fps, dur, outdir):
    C = cfg["colors"]; bg = hexrgb(C["dark"]); ink = (255, 255, 255); lime = hexrgb(C["lime"])
    portrait = H > W
    S = W / 1280 if not portrait else W / 720
    logo_size = int((132 if not portrait else 92) * S)
    n = int(dur * fps)
    for i in range(n):
        t = i / fps
        im = Image.new("RGB", (W, H), bg); d = ImageDraw.Draw(im)
        fi = ease(t / 0.6)
        tmp = Image.new("RGBA", (W, H), (0, 0, 0, 0)); td = ImageDraw.Draw(tmp)
        # centred logo
        f = font(cfg, "display", logo_size); lw = td.textlength("XpressIQ", font=f) + logo_size * 0.4
        lx = int((W - lw) / 2); ly = int(H * (0.30 if not portrait else 0.34))
        draw_logo(td, cfg, lx, ly, logo_size, ink + (int(255 * fi),), lime + (int(255 * fi),))
        fs = font(cfg, "display", int((26 if not portrait else 22) * S))
        s = cfg["strapline"]; sw = td.textlength(s, font=fs)
        td.text(((W - sw) / 2, ly + int(logo_size * 1.25)), s, font=fs, fill=lime + (int(255 * fi),))
        # CTA line
        ca = ease((t - 0.8) / 0.6)
        if ca > 0:
            fc = font(cfg, "body", int((30 if not portrait else 26) * S))
            lines = wrap_text(td, cfg["outro_cta"], fc, int(W * 0.8))
            yy = ly + int(logo_size * 1.25) + int((80 if not portrait else 74) * S)
            for ln in lines:
                w = td.textlength(ln, font=fc); td.text(((W - w) / 2, yy), ln, font=fc, fill=(227, 236, 232, int(255 * ca))); yy += int(fc.size * 1.3)
            fe = font(cfg, "display", int((34 if not portrait else 28) * S))
            e = cfg["contact_email"]; ew = td.textlength(e, font=fe)
            td.text(((W - ew) / 2, yy + int(14 * S)), e, font=fe, fill=ink + (int(255 * ca),))
        # footer: copyright
        fa = ease((t - 1.2) / 0.6)
        if fa > 0:
            ff = font(cfg, "body", int((18 if not portrait else 15) * S))
            c = cfg["copyright"]; cw = td.textlength(c, font=ff)
            td.text(((W - cw) / 2, H - int((70 if not portrait else 90) * S)), c, font=ff, fill=(127, 150, 144, int(255 * fa)))
        im.paste(tmp, (0, 0), tmp)
        fo = ease((dur - t) / 0.7)
        if fo < 1:
            im = Image.blend(Image.new("RGB", (W, H), bg), im, fo)
        im.save(outdir / f"o{i:05d}.png")
    return n

def frames_to_clip(frames_glob, fps, W, H, audio_tracks, dur, out):
    """audio_tracks: list of (path, start_seconds). Mixes them under the clip."""
    cmd = ["ffmpeg", "-y", "-v", "error", "-framerate", str(fps), "-i", frames_glob]
    for p, _ in audio_tracks: cmd += ["-i", str(p)]
    if audio_tracks:
        parts = []; names = []
        for k, (_, st) in enumerate(audio_tracks):
            parts.append(f"[{k+1}:a]aformat=sample_rates=44100:channel_layouts=stereo,adelay={int(st*1000)}|{int(st*1000)}[a{k}]"); names.append(f"[a{k}]")
        parts.append("".join(names) + f"amix=inputs={len(names)}:normalize=0,apad[aout]")
        cmd += ["-filter_complex", ";".join(parts), "-map", "0:v", "-map", "[aout]"]
    else:
        cmd += ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-map", "0:v", "-map", "1:a"]
    cmd += ["-t", f"{dur:.3f}", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-profile:v", "high", "-crf", "18",
            "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-ac", "2", "-s", f"{W}x{H}", str(out)]
    run(cmd)

def detect_end_card(src, dur, window=8.0, step=0.25):
    """Find where a flat end card (e.g. NotebookLM's) begins in the last `window` seconds.
    Returns seconds-from-end to cut, or None if no flat run is found."""
    import io
    try:
        import numpy as np
    except ImportError:
        return None
    samples = []
    t = max(0.0, dur - window)
    while t < dur - 0.1:
        r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.2f}", "-i", str(src), "-frames:v", "1",
                            "-vf", "scale=64:-1", "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True)
        if r.stdout:
            a = np.asarray(Image.open(io.BytesIO(r.stdout)).convert("L"), dtype=float)
            samples.append((t, float(a.std())))
        t += step
    # the end card: a sharp drop to a flat frame (std < 2) after busy content (std > 8)
    for k in range(1, len(samples)):
        if samples[k][1] < 2.0 and samples[k-1][1] > 8.0:
            return dur - samples[k][0]
    return None

def normalise(src, W, H, fps, out, trim_end=0.0):
    """Re-encode the source so concat is lossless-safe (same codec params, stereo 44.1k).
    trim_end: seconds to drop from the end (the NotebookLM end card)."""
    _, _, _, dur = probe(src)
    run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-t", f"{max(1.0, dur - trim_end):.3f}", "-vf", f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,fps={fps}",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-profile:v", "high", "-crf", "18", "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-ac", "2", str(out)])

def concat(parts, out):
    lst = out.parent / (out.stem + "_concat.txt")
    lst.write_text("".join(f"file '{p.resolve()}'\n" for p in parts))
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", "-movflags", "+faststart", str(out)])
    lst.unlink()

# ---------- commands ----------
def cmd_wrap(a):
    cfg = json.loads(pathlib.Path(a.config).read_text())
    W, H, fps, _ = probe(a.video); fps = 30 if fps > 29 else 24 if fps < 26 else 25
    work = pathlib.Path(tempfile.mkdtemp(prefix="xiqwrap_"))
    # --- intro timing: brand VO at 0.3s, title VO after it
    outro_vo = HERE / cfg["voice"]["outro_file"]
    intro_dur = cfg["intro"]["seconds"]
    n = render_intro_frames(cfg, W, H, fps, intro_dur, a.title or "", work)
    frames_to_clip(str(work / "i%05d.png"), fps, W, H, [], intro_dur, work / "intro.mp4")
    # --- outro
    outro_dur = max(cfg["outro"]["min_seconds"], 0.6 + audio_len(outro_vo) + 1.2)
    render_outro_frames(cfg, W, H, fps, outro_dur, work)
    frames_to_clip(str(work / "o%05d.png"), fps, W, H, [(outro_vo, 0.6)], outro_dur, work / "outro.mp4")
    # --- body + concat
    _, _, _, src_dur = probe(a.video)
    trim = a.trim_end
    if trim is None:
        found = detect_end_card(a.video, src_dur)
        trim = (found + cfg["body"].get("cut_before_card_seconds", 0.15)) if found else cfg["body"].get("trim_end_seconds", 0.0)
    normalise(a.video, W, H, fps, work / "body.mp4", trim_end=trim)
    out = pathlib.Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    concat([work / "intro.mp4", work / "body.mp4", work / "outro.mp4"], work / "joined.mp4")
    # poster = the intro card; embed it as cover art so players and galleries show it
    poster = out.with_suffix(".jpg")
    draw_intro_card(cfg, W, H, a.title or "", play=True).save(poster, quality=90, optimize=True)
    run(["ffmpeg", "-y", "-v", "error", "-i", str(work / "joined.mp4"), "-i", str(poster), "-map", "0", "-map", "1",
         "-c", "copy", "-disposition:v:1", "attached_pic", "-movflags", "+faststart", str(out)])
    print(f"wrote {out} + {poster.name}  ({W}x{H} @ {fps}fps; intro {intro_dur:.1f}s, body trimmed {trim:.2f}s, outro {outro_dur:.1f}s)")

def cmd_cards(a):
    """Render stand-alone intro/outro clips (no body) for review."""
    cfg = json.loads(pathlib.Path(a.config).read_text())
    for (W, H) in [(1280, 720), (720, 1280)]:
        work = pathlib.Path(tempfile.mkdtemp(prefix="xiqcards_")); fps = 30
        outro_vo = HERE / cfg["voice"]["outro_file"]
        idur = cfg["intro"]["seconds"]
        render_intro_frames(cfg, W, H, fps, idur, a.title or "", work)
        tag = "16x9" if W > H else "9x16"
        outd = pathlib.Path(a.out); outd.mkdir(parents=True, exist_ok=True)
        frames_to_clip(str(work / "i%05d.png"), fps, W, H, [], idur, outd / f"intro-{tag}.mp4")
        odur = max(cfg["outro"]["min_seconds"], 0.6 + audio_len(outro_vo) + 1.2)
        render_outro_frames(cfg, W, H, fps, odur, work)
        frames_to_clip(str(work / "o%05d.png"), fps, W, H, [(outro_vo, 0.6)], odur, outd / f"outro-{tag}.mp4")
        print("wrote", outd / f"intro-{tag}.mp4", outd / f"outro-{tag}.mp4")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
    w = sub.add_parser("wrap"); w.add_argument("--config", required=True); w.add_argument("--video", required=True); w.add_argument("--out", required=True)
    w.add_argument("--title", default=""); w.add_argument("--title-vo", default=None, help="ignored: the intro is silent")
    w.add_argument("--trim-end", type=float, default=None, help="seconds to cut from the source end (default: auto-detect the end card)"); w.set_defaults(fn=cmd_wrap)
    c = sub.add_parser("render-cards"); c.add_argument("--config", required=True); c.add_argument("--out", required=True)
    c.add_argument("--title", default=""); c.add_argument("--title-vo", default=None); c.set_defaults(fn=cmd_cards)
    a = ap.parse_args(); a.fn(a)
