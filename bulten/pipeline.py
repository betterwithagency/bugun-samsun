"""One bulletin, end to end: collect → research → write → check → render → wait → host → publish → record."""
import json
import re
import time
from datetime import datetime, timedelta
from pathlib import Path

from . import collect as collect_mod
from . import weather
from .config import DATA, EDITIONS, FONTSET, OUTPUT, THEME, TZ, TR_DAYS, TR_MONTHS
from .render import OverflowError_, build_slides, render

STATE = DATA / "state.json"
HISTORY = DATA / "history.json"
PAUSE = DATA / "PAUSE"
PHARMACY = "Nöbetçi eczaneleri e-Devlet'ten ya da Samsun Eczacı Odası'ndan öğrenebilirsin."

BASE_TAGS = {
    "gundem": ["#samsun", "#samsunhaber", "#samsungündem", "#bugunsamsun"],
    "ekonomi": ["#samsun", "#samsunekonomi", "#samsunişdünyası", "#bugunsamsun"],
    "spor": ["#samsun", "#samsunspor", "#samsunsporhaber", "#bugunsamsun"],
}


class Skip(Exception):
    """Nothing to publish today for this edition (not an error)."""


def _load(path: Path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def _save(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def _tr_lower(s: str) -> str:
    return s.replace("İ", "i").replace("I", "ı").lower()


def caption(issue: dict) -> str:
    ed = issue["edition"]
    lines = [issue["hook"].strip(), ""]
    for st in issue["stories"]:
        lines.append(f"{st['n']:02d} · {st['short_title']}")
    lines += ["", "Detaylar için kaydır →"]
    sources = []
    for item in issue["stories"] + issue.get("briefs", []):
        for s in item["sources"]:
            if s not in sources:
                sources.append(s)
    if sources:
        lines += ["", "Kaynaklar: " + ", ".join(sources)]
    lines += ["", "Her gün 08.00 Gündem · 12.30 Ekonomi & İş · 19.00 Spor. Haber ve önerilerin için DM."]
    lines += ["Harita: © OpenStreetMap katkıcıları"]
    tags = list(BASE_TAGS[ed])
    for st in issue["stories"]:
        d = st.get("district", "Samsun")
        if d != "Samsun":
            tag = "#" + re.sub(r"\s+", "", _tr_lower(d))
            if tag not in tags:
                tags.append(tag)
    lines += ["", " ".join(tags[:12])]
    return "\n".join(lines)[:2200]


def _trim(issue: dict, slide_ids: list):
    """Last resort when text still overflows: shorten the affected stories deterministically."""
    slides = build_slides(issue)
    for idx in slide_ids:
        s = slides[idx - 1]
        if s["kind"] in ("lead", "story"):
            st = issue["stories"][s["story"]["n"] - 1]
            st["body"] = st["body"].split("\n")[0]
        elif s["kind"] == "cover":
            for st in issue["stories"]:
                st["short_title"] = st["short_title"][:40].rsplit(" ", 1)[0]
        elif s["kind"] == "briefs":
            issue["briefs"] = issue["briefs"][:3]


def run(edition: str, publish: bool = False, wait: bool = False, force: bool = False,
        issue_file: str | None = None) -> dict:
    ed = EDITIONS[edition]
    now = datetime.now(TZ)
    today = now.date()
    date_label = f"{today.day} {TR_MONTHS[today.month - 1]} {today.year}, {TR_DAYS[today.weekday()]}"
    state = _load(STATE, {"issue_no": {}, "last": {}})
    history = _load(HISTORY, [])

    if PAUSE.exists() and publish:
        raise Skip("data/PAUSE var: yayın duraklatıldı")
    if publish and not force and state["last"].get(edition) == today.isoformat():
        raise Skip(f"{edition} bugün zaten yayınlandı")

    folder = f"{today.isoformat()}-{edition}"
    out_dir = OUTPUT / folder
    out_dir.mkdir(parents=True, exist_ok=True)

    if issue_file:  # test path: skip the AI steps
        issue = json.loads(Path(issue_file).read_text(encoding="utf-8"))
        issue.setdefault("hook", "Samsun'da bugün öne çıkanlar.")
        dossier = ""
    else:
        from . import write as w  # imported lazily so render-only runs don't need the SDK
        recent = [h["title"] for h in history if h["date"] >= (today - timedelta(days=3)).isoformat()]
        candidates = collect_mod.collect(edition, recent_titles=recent)
        print(f"[run] {len(candidates)} candidates")
        if len(candidates) < ed["min_stories"]:
            raise Skip(f"yeterli aday haber yok ({len(candidates)})")
        dossier = w.research(edition, date_label, candidates, recent)
        (out_dir / "dosya.md").write_text(dossier, encoding="utf-8")
        issue = w.write(edition, date_label, dossier)
        for attempt in range(2):
            issues = w.problems(issue)
            if not issues:
                break
            print(f"[run] fixing {len(issues)} problems: {issues}")
            issue = w.write(edition, date_label, dossier, fix_note="\n".join(issues), previous=issue)
        issue["edition"] = edition
        issue["stories"] = issue["stories"][: ed["max_stories"]]
        issue["briefs"] = issue["briefs"][: ed["max_briefs"]]
        if len(issue["stories"]) < ed["min_stories"]:
            raise Skip(f"doğrulanmış haber sayısı yetersiz ({len(issue['stories'])})")

    issue["edition"] = edition
    issue["date"] = today.isoformat()
    issue["issue_no"] = state["issue_no"].get(edition, 0) + 1
    for n, st in enumerate(issue["stories"], start=1):
        st["n"] = n
    issue.pop("practical", None)
    if ed["practical"]:
        issue["weather"] = weather.today()
        outages = issue.get("outages") or []
        if issue["weather"] or outages:  # without either, the guide slide would look empty: leave it out
            issue["practical"] = {"outages": outages, "pharmacy": PHARMACY}
    sb = issue.get("scoreboard") or {}
    issue["scoreboard"] = sb if sb.get("present") else None

    # render; if text overflows, ask the writer to shorten once, then trim deterministically
    paths = None
    for attempt in range(3):
        try:
            paths = render(issue, out_dir, theme=THEME, fontset=FONTSET, strict=attempt < 2)
            break
        except OverflowError_ as exc:
            print(f"[run] overflow on slides {exc.slides}")
            if attempt == 0 and not issue_file:
                from . import write as w
                note = (f"Görselde {exc.slides} numaralı slaytlardaki metin sığmadı. İlgili haberlerin body ve "
                        f"why alanlarını yaklaşık %25 kısalt; kapak (1) ise short_title alanlarını kısalt.")
                fixed = w.write(edition, date_label, dossier, fix_note=note, previous=issue)
                for k in ("stories", "briefs", "hook"):
                    issue[k] = fixed[k]
                for n, st in enumerate(issue["stories"], start=1):
                    st["n"] = n
            else:
                _trim(issue, exc.slides)
    text = caption(issue)
    (out_dir / "caption.txt").write_text(text, encoding="utf-8")
    if not issue_file:  # sample/test runs never touch the archive
        _save(DATA / "issues" / f"{folder}.json", {k: v for k, v in issue.items() if k != "weather"})
    print(f"[run] rendered {len(paths)} slides → {out_dir}")

    result = {"edition": edition, "slides": [str(p) for p in paths], "caption": text, "published": False}
    if not publish:
        return result

    from . import hosting, instagram, tokens
    if wait:
        hh, mm = map(int, ed["publish_at"].split(":"))
        target = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
        delay = (target - datetime.now(TZ)).total_seconds()
        if 0 < delay < 3 * 3600:
            print(f"[run] waiting {int(delay)}s until {ed['publish_at']}")
            time.sleep(delay)
    token = tokens.get_token()
    user = instagram.me(token)
    urls = hosting.host_images(paths, folder)
    post = instagram.publish_carousel(token, user["user_id"], urls, text)
    print(f"[run] published to @{user.get('username')}: {post.get('permalink') or post['id']}")

    state["issue_no"][edition] = issue["issue_no"]
    state["last"][edition] = today.isoformat()
    _save(STATE, state)
    for st in issue["stories"]:
        history.append({"date": today.isoformat(), "edition": edition, "title": st["title"],
                        "district": st.get("district"), "permalink": post.get("permalink", "")})
    cutoff = (today - timedelta(days=30)).isoformat()
    _save(HISTORY, [h for h in history if h["date"] >= cutoff])
    result.update(published=True, permalink=post.get("permalink", ""), media_id=post["id"])
    return result
