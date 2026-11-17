"""Turn an issue dict into 1080x1350 JPEG slides, in one of three visual themes."""
import json
import math
from datetime import date
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup
from playwright.sync_api import sync_playwright

from . import icons
from .config import ASSETS, EDITIONS, MAX_CONTENT_SLIDES, TEMPLATES, TR_DAYS, TR_MONTHS

THEMES = ("gazete", "kart", "harita")
_MAP = None


class OverflowError_(RuntimeError):
    """A slide's text did not fit even at the smallest allowed size."""

    def __init__(self, slides):
        super().__init__(f"text overflow on slides {slides}")
        self.slides = slides


def samsun_map() -> dict:
    global _MAP
    if _MAP is None:
        _MAP = json.loads((ASSETS / "samsun_map.json").read_text(encoding="utf-8"))
    return _MAP


def map_svg(highlight=(), pins=(), cls="map", vb=None, target=None, label=None, zoom=None, context=True) -> Markup:
    """SVG of Samsun: neighbours as context, the 17 districts, optional highlighted districts and numbered pins.

    pins: list of (label, district). Pins in the same district are merged; nearby pins are pushed apart
    and get a leader line back to their district.
    """
    m = samsun_map()
    if highlight == "all":
        highlight = list(m["districts"])
    vb = vb or f'0 0 {m["width"]} {m["height"]}'
    if zoom == "auto" and target in m["districts"]:  # small districts get a closer frame
        zoom = min(2.4, max(1.0, (14000 / m["districts"][target]["area"]) ** 0.5))
        zoom = zoom if zoom > 1.05 else None
    if zoom and target in m["districts"]:  # frame the target district, keeping the base aspect ratio
        x0, y0, w0, h0 = (float(v) for v in vb.split())
        w, h = w0 / zoom, h0 / zoom
        t = m["districts"][target]
        x = min(max(t["cx"] - w / 2, x0), x0 + w0 - w)
        y = min(max(t["cy"] - h / 2, y0), y0 + h0 - h)
        vb = f"{x:.0f} {y:.0f} {w:.0f} {h:.0f}"

    parts = [f'<svg class="{cls}" viewBox="{vb}" preserveAspectRatio="xMidYMid meet">']
    if context:
        parts.append('<g class="ctx">' + "".join(f'<path d="{d}"/>' for d in m["context"]) + "</g>")
    parts.append('<g class="dist">')
    for name, v in m["districts"].items():
        on = " on" if name in highlight else ""
        parts.append(f'<path class="d{on}" d="{v["d"]}"/>')
    parts.append("</g>")
    # merge pins per district
    merged = {}
    for label, district in pins:
        if district in m["districts"]:
            merged.setdefault(district, []).append(label)
    nodes = []
    for district, labels in merged.items():
        v = m["districts"][district]
        nodes.append({"x": v["cx"], "y": v["cy"], "ox": v["cx"], "oy": v["cy"], "label": "·".join(labels)})
    min_d = 74.0
    for _ in range(80):  # simple repulsion so pins never overlap
        for i, a in enumerate(nodes):
            for b in nodes[i + 1:]:
                dx, dy = b["x"] - a["x"], b["y"] - a["y"]
                dist = math.hypot(dx, dy) or 0.01
                if dist < min_d:
                    push = (min_d - dist) / 2
                    ux, uy = dx / dist, dy / dist
                    a["x"] -= ux * push; a["y"] -= uy * push
                    b["x"] += ux * push; b["y"] += uy * push
    parts.append('<g class="pins">')
    for n in nodes:
        if math.hypot(n["x"] - n["ox"], n["y"] - n["oy"]) > 8:
            parts.append(f'<line class="lead" x1="{n["ox"]}" y1="{n["oy"]}" x2="{n["x"]:.1f}" y2="{n["y"]:.1f}"/>'
                         f'<circle class="dot" cx="{n["ox"]}" cy="{n["oy"]}" r="5"/>')
        w = 30 + 22 * len(n["label"])
        parts.append(f'<g class="pin" transform="translate({n["x"]:.1f} {n["y"]:.1f})">'
                     f'<rect x="{-w / 2:.1f}" y="-24" width="{w:.1f}" height="48" rx="24"/>'
                     f'<text y="9" text-anchor="middle">{n["label"]}</text></g>')
    parts.append("</g>")
    if target in m["districts"]:
        t = m["districts"][target]
        parts.append(f'<g class="target" transform="translate({t["cx"]} {t["cy"]})">'
                     '<circle class="r2" r="46"/><circle class="r1" r="22"/><circle class="c" r="7"/>'
                     '<path class="x" d="M-70 0H-30M30 0H70M0 -70V-30M0 30V70"/></g>')
        if label:
            ly = t["cy"] + 96 if t["cy"] < 260 else t["cy"] - 64
            parts.append(f'<text class="tlabel" x="{t["cx"]}" y="{ly}" text-anchor="middle">{label}</text>')
    parts.append("</svg>")
    return Markup("".join(parts))


def build_slides(issue: dict) -> list:
    stories = [dict(s) for s in issue["stories"]]
    briefs = issue.get("briefs") or []
    practical = issue.get("practical")
    room = MAX_CONTENT_SLIDES - (1 if briefs else 0) - (1 if practical else 0)
    stories = stories[:room]
    for i, st in enumerate(stories, start=1):
        st["n"] = i
        st["icon"] = Markup(icons.svg(icons.for_category(st["category"])))
        st["icon_name"] = icons.for_category(st["category"])
        st["body_paragraphs"] = [p.strip() for p in st.get("body", "").split("\n") if p.strip()]
        st["words"] = len((st.get("title", "") + " " + st.get("body", "") + " " + st.get("why", "")).split())
    for b in briefs:
        b["icon"] = Markup(icons.svg(icons.for_category(b["category"])))
    slides = [{"kind": "cover", "stories": stories}]
    slides.append({"kind": "lead", "story": stories[0]})
    slides += [{"kind": "story", "story": s} for s in stories[1:]]
    if briefs:
        srcs = []
        for b in briefs:
            for s in b.get("sources", []):
                if s not in srcs:
                    srcs.append(s)
        slides.append({"kind": "briefs", "briefs": briefs, "sources": srcs})
    if practical:
        slides.append({"kind": "practical"})
    slides.append({"kind": "outro"})
    for i, s in enumerate(slides, start=1):
        s["idx"] = i
    return slides


def render_html(issue: dict, theme: str, sample: bool = False, fontset: str = "libron") -> str:
    env = Environment(loader=FileSystemLoader(str(TEMPLATES)), autoescape=select_autoescape(["html", "j2"]))
    env.globals["icon"] = lambda name, stroke=1.8: Markup(icons.svg(name, stroke))
    env.globals["map_svg"] = map_svg
    tpl = env.get_template(f"{theme}.html.j2")
    d = date.fromisoformat(issue["date"])
    slides = build_slides(issue)
    words = sum(s["story"]["words"] for s in slides if s["kind"] in ("lead", "story"))
    words += sum(len(b["text"].split()) for b in issue.get("briefs") or [])
    stories = slides[0]["stories"]
    return tpl.render(
        assets=ASSETS.as_uri(),
        mark_svg=Markup((ASSETS / "bwa-mark.svg").read_text(encoding="utf-8")),
        edition=issue["edition"],
        ed=EDITIONS[issue["edition"]],
        day=d.day, month=TR_MONTHS[d.month - 1], year=d.year, weekday=TR_DAYS[d.weekday()],
        date_short=d.strftime("%d.%m.%Y"),
        issue_no=issue.get("issue_no", 1),
        weather=issue.get("weather"),
        practical=issue.get("practical"),
        scoreboard=issue.get("scoreboard"),
        slides=slides,
        total=len(slides),
        stories=stories,
        districts_with_news=sorted({s["district"] for s in stories if s.get("district") in samsun_map()["districts"]}),
        pins=[(f"{s['n']:02d}", s.get("district")) for s in stories],
        reading_min=max(1, math.ceil(words / 180)),
        map_credit=samsun_map()["credit"],
        sample=sample,
        fontset=fontset,
    )


def render(issue: dict, out_dir, theme: str = "klasik", sample: bool = False, strict: bool = True, fontset: str = "libron") -> list:
    """Write slides.html plus 01.jpg, 02.jpg… into out_dir and return the JPEG paths.

    Raises OverflowError_ if any slide still overflows after auto-shrinking.
    """
    out_dir = Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    html_path = out_dir / "slides.html"
    html_path.write_text(render_html(issue, theme, sample, fontset), encoding="utf-8")
    paths = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1080, "height": 1350}, device_scale_factor=1)
        page.goto(html_path.as_uri())
        page.evaluate("document.fonts.ready.then(() => true)")
        report = page.evaluate("window.__fit()")
        bad = [r["idx"] for r in report if r["overflow"]]
        if bad and strict:
            browser.close()
            raise OverflowError_(bad)
        if bad:
            print(f"[render] WARNING overflow on slides {bad}")
        for i, el in enumerate(page.locator("section.slide").all(), start=1):
            path = out_dir / f"{i:02d}.jpg"
            el.screenshot(path=str(path), type="jpeg", quality=92)
            paths.append(path)
        browser.close()
    return paths
