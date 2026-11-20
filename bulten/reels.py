"""Daily Reels: a ~20 s vertical video of the day's top 3 Gündem stories, posted at 17.30.

No AI step: the stories come from the Gündem bulletin already published this morning
(data/issues/<date>-gundem.json). The HTML template is stepped frame by frame (Web Animations API),
screenshotted with Playwright and piped into ffmpeg (H.264 + silent AAC, what Instagram expects).

By default the Reels goes out as a trial reel: Instagram shows it to non-followers first, so followers'
feeds still get three posts a day. If the account cannot post trial reels yet, it is posted as a normal Reels.
"""
import json
import os
import re
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from playwright.sync_api import sync_playwright

from .config import ASSETS, DATA, OUTPUT, TEMPLATES, TR_DAYS, TR_MONTHS, TZ
from .pipeline import MIN_GAP, PAUSE, STATE, WINDOW, Skip, _load, _save, _tr_lower
from .render import map_svg, samsun_map

PUBLISH_AT = "17:30"
FPS = 30
STORIES = 3
COVER, PER_STORY, CTA = 2.8, 4.8, 3.8  # seconds
MARKER = "#samsunhaberleri"  # only Reels captions carry it (duplicate check); never used by the bulletins
TRIAL = (os.environ.get("BULTEN_REELS_TRIAL") or "1") != "0"
CROP = "-10 58 970 540"


def _ffmpeg() -> str:
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    import imageio_ffmpeg  # bundled static build with libx264 (GitHub runners have no ffmpeg of their own)
    return imageio_ffmpeg.get_ffmpeg_exe()


def build(issue: dict) -> dict:
    """Template context: timings and per-story content."""
    districts = samsun_map()["districts"]
    stories = issue["stories"][:STORIES]
    scenes = []
    for i, st in enumerate(stories):
        d = st.get("district") or "Samsun"
        local = d in districts
        stat = st.get("stat") or None
        if stat and not (stat.get("value") or "").strip():
            stat = None
        scenes.append({
            "n": i + 1,
            "at": round(COVER + i * PER_STORY, 2),
            "len": PER_STORY,
            "category": st.get("category") or "Gündem",
            "title": st["short_title"],
            "stat": stat,
            "why": st.get("why", ""),
            "place": d if local else "Samsun geneli",
            "location": st.get("location", "") if st.get("location", "") not in (d, "Samsun") else "",
            "map": map_svg(highlight=[d], vb=CROP, target=d, context=False, zoom="auto") if local
            else map_svg(vb=CROP, context=False, cls="map all"),
        })
    pins = [(str(s["n"]), stories[k].get("district")) for k, s in enumerate(scenes)
            if stories[k].get("district") in districts]
    cta_at = round(COVER + len(scenes) * PER_STORY, 2)
    day = datetime.fromisoformat(issue["date"]).date()
    return {
        "assets": ASSETS.as_uri(),
        "date_label": f"{day.day} {TR_MONTHS[day.month - 1]} · {TR_DAYS[day.weekday()]}",
        "stories": stories,
        "scenes": scenes,
        "cover_map": map_svg(highlight=[d for _, d in pins], pins=pins, vb=CROP, context=False),
        "cta_at": cta_at,
        "duration": round(cta_at + CTA, 2),
        "seconds": int(round(cta_at + CTA)),
    }


def render_video(issue: dict, out_dir: Path) -> dict:
    """Write reels.html, reels.mp4 and kapak.jpg into out_dir. Returns paths and timing."""
    ctx = build(issue)
    env = Environment(loader=FileSystemLoader(TEMPLATES), autoescape=select_autoescape(["html", "j2"]))
    html = env.get_template("reels.html.j2").render(**ctx)
    out_dir.mkdir(parents=True, exist_ok=True)
    html_path = out_dir / "reels.html"
    html_path.write_text(html, encoding="utf-8")
    video = out_dir / "reels.mp4"
    cover = out_dir / "kapak.jpg"
    frames = round(ctx["duration"] * FPS)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1080, "height": 1920}, device_scale_factor=1)
        page.goto(html_path.as_uri())
        page.evaluate("document.fonts.ready.then(() => true)")
        bad = page.evaluate("window.__fit()")
        if bad:
            print(f"[reels] {bad} text block(s) still too big at the smallest size")
        page.evaluate("ms => seek(ms)", 1800)
        page.screenshot(path=str(cover), type="jpeg", quality=92)
        ff = subprocess.Popen(
            [_ffmpeg(), "-y", "-loglevel", "error",
             "-f", "image2pipe", "-framerate", str(FPS), "-c:v", "png", "-i", "-",
             "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-map", "0:v", "-map", "1:a", "-shortest",
             "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p",
             "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv",
             "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-profile:v", "high",
             "-r", str(FPS), "-g", str(FPS * 2),
             "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-movflags", "+faststart", str(video)],
            stdin=subprocess.PIPE)
        try:
            for i in range(frames):
                page.evaluate("ms => seek(ms)", i * 1000 / FPS)
                ff.stdin.write(page.screenshot(type="png"))
        finally:
            ff.stdin.close()
            code = ff.wait()
            browser.close()
    if code != 0 or not video.exists():
        raise RuntimeError(f"ffmpeg failed (exit {code})")
    return {"video": video, "cover": cover, "duration": ctx["duration"]}


def caption(issue: dict) -> str:
    stories = issue["stories"][:STORIES]
    lines = [f"Samsun'da bugün: günün {len(stories)} haberi.", ""]
    lines += [f"{n:02d} · {st['short_title']}" for n, st in enumerate(stories, start=1)]
    total = len(issue["stories"]) + len(issue.get("briefs", []))
    lines += ["", f"Gündem bülteninin tamamı profilde: {total} haber, kaynaklarıyla."]
    sources = []
    for st in stories:
        for s in st["sources"]:
            if s not in sources:
                sources.append(s)
    if sources:
        lines += ["Kaynaklar: " + ", ".join(sources)]
    lines += ["", "Her gün 08.00 Gündem · 12.30 Ekonomi & İş · 19.00 Spor.", "Harita: © OpenStreetMap katkıcıları"]
    tags = ["#samsun", MARKER]
    for st in stories:
        d = st.get("district", "Samsun")
        tag = "#" + re.sub(r"\s+", "", _tr_lower(d))
        if d != "Samsun" and tag not in tags:
            tags.append(tag)
    lines += ["", " ".join(tags[:5])]
    return "\n".join(lines)[:2200]


def run(publish: bool = False, wait: bool = False, force: bool = False, issue_file: str | None = None) -> dict:
    now = datetime.now(TZ)
    today = now.date()
    state = _load(STATE, {"issue_no": {}, "last": {}})
    if PAUSE.exists() and publish:
        raise Skip("data/PAUSE var: yayın duraklatıldı")
    hh, mm = map(int, PUBLISH_AT.split(":"))
    target = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
    if publish and wait and not target - WINDOW[0] <= now <= target + WINDOW[1]:
        raise Skip(f"reels yayın penceresinin dışında ({now:%H:%M}, yayın {PUBLISH_AT})")
    last_at = state.get("last_at", {}).get("reels")
    if publish and not force and last_at and now - datetime.fromisoformat(last_at) < MIN_GAP:
        raise Skip(f"reels {last_at[:16].replace('T', ' ')} tarihinde zaten yayınlandı")

    source = Path(issue_file) if issue_file else DATA / "issues" / f"{today.isoformat()}-gundem.json"
    if not source.exists():
        raise Skip(f"bugünün Gündem bülteni yok ({source.name}); Reels bugün atlanıyor")
    issue = json.loads(source.read_text(encoding="utf-8"))
    if len(issue.get("stories", [])) < 2:
        raise Skip("Reels için yeterli haber yok")

    folder = f"{today.isoformat()}-reels"
    out_dir = OUTPUT / folder
    made = render_video(issue, out_dir)
    text = caption(issue)
    (out_dir / "caption.txt").write_text(text, encoding="utf-8")
    print(f"[reels] rendered {made['duration']}s → {made['video']} ({made['video'].stat().st_size / 1e6:.1f} MB)")
    result = {"edition": "reels", "video": str(made["video"]), "caption": text, "published": False}
    if not publish:
        return result

    from . import instagram, tokens
    if wait:
        delay = (target - datetime.now(TZ)).total_seconds()
        if 0 < delay < 3 * 3600:
            print(f"[reels] waiting {int(delay)}s until {PUBLISH_AT}")
            time.sleep(delay)
    token = tokens.get_token()
    user = instagram.account(token)
    if not force:
        try:
            done = instagram.posted_since(token, user["user_id"], MARKER, datetime.now(TZ) - MIN_GAP)
        except instagram.InstagramError as exc:
            print(f"[reels] could not list recent posts, relying on state.json: {exc}")
            done = ""
        if done:
            raise Skip(f"reels son {MIN_GAP.seconds // 3600} saatte zaten paylaşılmış: {done}")
    post = None
    if TRIAL:
        try:
            post = instagram.publish_reel(token, user["user_id"], made["video"], text, trial=True, thumb_offset_ms=1800)
        except instagram.InstagramError as exc:
            print(f"[reels] trial reel not accepted, posting a normal Reels instead: {exc}")
    if post is None:
        post = instagram.publish_reel(token, user["user_id"], made["video"], text, trial=False, thumb_offset_ms=1800)
    print(f"[reels] published to @{user.get('username')}: {post.get('permalink') or post['id']}"
          f"{' (deneme Reels)' if post.get('trial') else ''}")

    _save(DATA / "reels" / f"{today.isoformat()}.json",
          {"date": today.isoformat(), "source": source.name, "trial": post.get("trial", False),
           "id": post["id"], "permalink": post.get("permalink", ""),
           "stories": [st["short_title"] for st in issue["stories"][:STORIES]]})
    state = _load(STATE, state)
    state.setdefault("last", {})["reels"] = today.isoformat()
    state.setdefault("last_at", {})["reels"] = datetime.now(TZ).isoformat(timespec="minutes")
    _save(STATE, state)
    result.update(published=True, permalink=post.get("permalink", ""), media_id=post["id"], trial=post.get("trial", False))
    return result
