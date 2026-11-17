"""Collect candidate Samsun news from Google News RSS (free, no key)."""
import re
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import feedparser
import requests

from .config import EDITIONS, TZ

UA = "Mozilla/5.0 (compatible; BugunSamsun/1.0)"
_WORD = re.compile(r"[0-9a-zçğıöşüâîû]+")


def _rss_url(query: str) -> str:
    return ("https://news.google.com/rss/search?q=" + quote(f"{query} when:1d")
            + "&hl=tr&gl=TR&ceid=TR:tr")


def _tokens(title: str) -> set:
    t = title.replace("İ", "i").replace("I", "ı").lower()
    return {w for w in _WORD.findall(t) if len(w) > 2}


def similar(a: str, b: str, threshold: float = 0.55) -> bool:
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return False
    return len(ta & tb) / min(len(ta), len(tb)) >= threshold


def _fetch(query: str) -> list:
    for attempt in range(3):
        try:
            r = requests.get(_rss_url(query), headers={"User-Agent": UA}, timeout=20)
            r.raise_for_status()
            return feedparser.parse(r.content).entries
        except Exception as exc:
            print(f"[collect] '{query}' attempt {attempt + 1} failed: {exc}")
            time.sleep(3 * (attempt + 1))
    return []


def collect(edition: str, since_hours: int = 26, recent_titles=(), limit: int = 70) -> list:
    """Return candidate stories: [{title, sources, published, links}], most-covered first.

    Same story from several outlets is merged (its source count is a useful importance signal).
    Titles similar to `recent_titles` (already published) are dropped.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=since_hours)
    merged = []
    for q in EDITIONS[edition]["queries"]:
        for e in _fetch(q):
            raw = e.get("title", "").strip()
            src = (e.get("source") or {}).get("title") or ""
            title = raw
            if src and raw.endswith(" - " + src):
                title = raw[: -len(src) - 3].strip()
            elif " - " in raw:
                title, src = raw.rsplit(" - ", 1)
            if not title:
                continue
            published = None
            if e.get("published_parsed"):
                published = datetime(*e.published_parsed[:6], tzinfo=timezone.utc)
                if published < cutoff:
                    continue
            if any(similar(title, t) for t in recent_titles):
                continue
            for item in merged:
                if similar(title, item["title"]):
                    if src and src not in item["sources"]:
                        item["sources"].append(src)
                    if published and (item["published"] is None or published > item["published"]):
                        item["published"] = published
                    break
            else:
                merged.append({"title": title, "sources": [src] if src else [], "published": published,
                               "link": e.get("link", "")})
    merged.sort(key=lambda i: (len(i["sources"]), i["published"] or cutoff), reverse=True)
    out = []
    for i in merged[:limit]:
        out.append({
            "title": i["title"],
            "sources": i["sources"],
            "published": i["published"].astimezone(TZ).strftime("%d.%m %H:%M") if i["published"] else "",
            "link": i["link"],
        })
    return out
