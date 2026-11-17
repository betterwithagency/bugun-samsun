"""Shared settings for Bugün Samsun."""
import os
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
TEMPLATES = ROOT / "templates"
OUTPUT = ROOT / "output"
DATA = ROOT / "data"

TZ = ZoneInfo("Europe/Istanbul")
HANDLE = "@bugunsamsun"

# Visual design
THEME = os.environ.get("BULTEN_THEME") or "klasik"
FONTSET = os.environ.get("BULTEN_FONTSET") or "libron"

# AI provider for research and writing: "gemini" (default) or "claude"
PROVIDER = (os.environ.get("BULTEN_PROVIDER") or "gemini").strip().lower()
GEMINI_MODEL = os.environ.get("BULTEN_GEMINI_MODEL") or "gemini-4-argon"
MODEL = os.environ.get("BULTEN_MODEL") or "claude-opus-5-5"  # used when PROVIDER == "claude"

# Instagram: carousels hold up to 20 items via the API; we keep posts short on purpose.
MAX_SLIDES = 10
MAX_CONTENT_SLIDES = MAX_SLIDES - 2

SAMSUN_DISTRICTS = ["Alaçam", "Asarcık", "Atakum", "Ayvacık", "Bafra", "Canik", "Çarşamba", "Havza", "İlkadım",
                    "Kavak", "Ladik", "19 Mayıs", "Salıpazarı", "Tekkeköy", "Terme", "Vezirköprü", "Yakakent"]

EDITIONS = {
    "gundem": {
        "label": "Gündem",
        "title_html": "Günün<br><em>özeti</em>",
        "publish_at": "08:00",
        "schedule": "Ekonomi 12.30 · Spor 19.00",
        "next": "Yarın sabah 08.00'de yeni bültenle buradayız.",
        "min_stories": 3,
        "max_stories": 6,
        "max_briefs": 4,
        "practical": True,
        "queries": [
            "Samsun",
            "Atakum OR İlkadım OR Canik OR Tekkeköy",
            "Bafra OR Terme OR Vezirköprü OR Havza OR \"Çarşamba Samsun\"",
            "Alaçam OR Ladik OR Yakakent OR Salıpazarı OR Asarcık OR \"19 Mayıs ilçesi\" OR \"Kavak Samsun\" OR \"Ayvacık Samsun\"",
        ],
        "focus": "Samsun'daki günlük yaşamı etkileyen gelişmeler: belediye kararları, ulaşım, altyapı, sağlık, eğitim, "
                 "hava ve afet, kültür-sanat, çevre. Ekonomi ve spor haberlerini ancak çok büyük bir gelişmeyse seç; "
                 "onların kendi bültenleri var.",
    },
    "ekonomi": {
        "label": "Ekonomi & İş",
        "title_html": "Ekonomi<br><em>&amp; İş Dünyası</em>",
        "publish_at": "12:30",
        "schedule": "Spor bülteni 19.00'da",
        "next": "Ekonomi bülteni yarın 12.30'da.",
        "min_stories": 3,
        "max_stories": 5,
        "max_briefs": 4,
        "practical": False,
        "queries": [
            "Samsun ekonomi OR yatırım OR ihracat OR fabrika OR OSB",
            "Samsun TSO OR \"Ticaret Borsası\" OR OKA OR liman OR istihdam",
            "Samsun fındık OR tarım OR esnaf OR konut OR turizm",
        ],
        "focus": "Samsun'un ekonomisi ve iş dünyası: yatırımlar, sanayi ve OSB'ler, liman ve lojistik, ihracat, "
                 "tarım ve ürün fiyatları, istihdam, esnaf ve ticaret, oda ve borsa açıklamaları, kalkınma destekleri.",
    },
    "spor": {
        "label": "Spor",
        "title_html": "Samsun<br><em>Spor</em>",
        "publish_at": "19:00",
        "schedule": "Yarın sabah 08.00'de Gündem",
        "next": "Spor bülteni yarın 19.00'da.",
        "min_stories": 3,
        "max_stories": 5,
        "max_briefs": 4,
        "practical": False,
        "queries": [
            "Samsunspor",
            "Samsun spor OR basketbol OR voleybol OR güreş OR atletizm OR hentbol",
        ],
        "focus": "Samsun sporu: önce Samsunspor (maç sonuçları, kadro, transfer, teknik heyet açıklamaları), "
                 "sonra Samsun'un diğer kulüpleri ve sporcuları, amatör lig ve okul sporları.",
    },
}

TR_MONTHS = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz",
             "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
TR_DAYS = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]


def date_long(d) -> str:
    return f"{d.day} {TR_MONTHS[d.month - 1]} {d.year}, {TR_DAYS[d.weekday()]}"
