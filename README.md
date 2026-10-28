# XpressIQ — weekly intelligence reports

One written report, one 16:9 briefing, one 9:16 short, every week.

- `site/` — the static website (xpressiq.co.uk). Edit `site/reports.json`, run `python3 site/build.py`, commit, push.
- `site/videos/` — the wrapped videos (branded intro + outro, end card trimmed, poster embedded). `site/thumbs/` — the branded posters.
- `skill/` — the `xpressiq-report-wrap` skill: `wrap.py`, `config.json`, the house voiceover in `vo/`, and `SKILL.md` describing the weekly process.
- `site/docker-compose.yml` — how the Hostinger VPS serves it (nginx behind the shared Caddy proxy; clones `main` on start).

Contact: Contact@XpressIQ.co.uk · © XpressIQ Limited
