"""Claude does the journalism: research (web search + fetch) then writing to a strict JSON schema."""
import json

import anthropic

from .config import EDITIONS, MODEL, SAMSUN_DISTRICTS
from .icons import CATEGORIES

FALLBACK_BETA = "server-side-fallback-2026-07-01"

EDITORIAL_RULES = """Sen "Bugün Samsun" adlı Instagram haber bülteninin editörüsün. Bülten her gün otomatik yayınlanıyor ve yayından önce hiçbir insan kontrol etmiyor. Bu yüzden doğruluk, hızdan ve ilginçlikten her zaman önemlidir.

Doğruluk
- Bir haberi ancak güvenilir bir kaynağın sayfasını kendin okuyup doğruladıysan kullan: resmi kurumlar (valilik, belediyeler, bakanlıklar, odalar, kulüpler), haber ajansları (AA, İHA, DHA) ya da köklü ulusal/yerel yayınlar. Yalnızca başlıktan haber yazma.
- Sayıları, isimleri, unvanları, tarihleri kaynakta nasılsa öyle aktar. Kaynakta olmayan hiçbir ayrıntıyı ekleme, tahmin yürütme.
- Kaynaklar çelişiyorsa ya da olay hâlâ belirsizse haberi seçme.
- Haber son 24 saat içinde gerçekleşmiş ya da duyurulmuş olmalı ve doğrudan Samsun'u (il ya da ilçeleri) ilgilendirmeli.

Hassas içerik
- Suç, kaza ve yangın haberlerinde şüpheli, mağdur ya da yaralıların adını, soyadını, baş harflerini yazma; çocukların kimliğini ima eden hiçbir bilgi verme.
- Masumiyet karinesine uy: yalnızca resmi işlemleri aktar (gözaltına alındı, tutuklandı). "Cani", "vahşet", "katil" gibi yargılayan ya da sansasyonel ifadeler kullanma.
- İntihar ve intihar girişimi haberlerini seçme. Grafik ya da kanlı ayrıntı verme.
- Bir bültende en fazla bir asayiş haberi olsun; gündemi asayişe boğma.

Tarafsızlık ve üslup
- Siyasi polemik ve kavga haberlerini seçme. Kamu yararı taşıyan siyasi bir gelişmeyi seçersen yalnızca olguları, tarafları dengeli aktar; yorum yapma.
- Sade, net, Türkçe imla kurallarına uygun yaz. Tık tuzağı, ünlem, abartı yok.
- Kaynak metni kopyalama; kendi cümlelerinle özetle. Doğrudan alıntı gerekiyorsa en fazla bir kısa cümle, tırnak içinde.

Seçim önceliği
- Önce Samsunluların günlük hayatını etkileyen ve kamu yararı taşıyan haberler; sonra ekonomi, kültür ve insan hikâyeleri.
- Birçok kaynakta geçen haber genellikle daha önemlidir ama tek ölçüt bu değildir.
- Daha önce yayınladığımız bir konuyu yeni ve önemli bir gelişme yoksa tekrar seçme."""


def _client() -> anthropic.Anthropic:
    return anthropic.Anthropic(max_retries=4)


def _text(msg) -> str:
    return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()


def _check_stop(msg, step: str):
    if msg.stop_reason == "refusal":
        raise RuntimeError(f"{step}: model declined the request ({getattr(msg, 'stop_details', None)})")
    if msg.stop_reason == "max_tokens":
        raise RuntimeError(f"{step}: output hit max_tokens")


def research(edition: str, date_label: str, candidates: list, recent_titles: list) -> str:
    """Pick and verify stories with web search/fetch. Returns a plain-text dossier."""
    ed = EDITIONS[edition]
    cand_lines = "\n".join(
        f"{i + 1}. {c['title']} | kaynaklar: {', '.join(c['sources'][:6]) or '-'} | {c['published']}"
        for i, c in enumerate(candidates))
    recent = "\n".join(f"- {t}" for t in recent_titles) or "- (yok)"
    extras = []
    if ed["practical"]:
        extras.append("Ayrıca bugün Samsun'da planlı elektrik (YEDAŞ) ya da su (SASKİ) kesintisi olup olmadığını ara. "
                      "Yalnızca bugünün tarihini taşıyan resmi bir duyuru ya da bunu aktaran haber bulursan, "
                      "etkilenen ilçe/mahalleleri ve saatleri not et. Bulamazsan 'kesinti bilgisi yok' yaz.")
    if edition == "spor":
        extras.append("Samsunspor son 24 saatte resmi bir maç oynadıysa sonucu (rakip, skor, organizasyon ve hafta) "
                      "kulübün ya da güvenilir bir spor kaynağının sayfasından doğrula.")
    prompt = f"""Bugün {date_label}. "{ed['label']}" bültenini hazırlıyoruz.

Bu bültenin odağı: {ed['focus']}

Aşağıda son 24 saatte Google Haberler'de çıkan aday başlıklar var (kaç kaynakta geçtiği ve saatiyle). Bunlar yalnızca ipucu; web aramasıyla başka önemli Samsun haberleri de bulabilirsin.

<adaylar>
{cand_lines}
</adaylar>

<daha_once_yayinlananlar>
{recent}
</daha_once_yayinlananlar>

Görev:
1. Bülten için en önemli {ed['max_stories']} habere kadar seç (en az {ed['min_stories']}). Birincisi manşet olacak: en önemli ve en çok kişiyi ilgilendiren haber.
2. Ayrıca tek cümleyle verilebilecek {ed['max_briefs']} kısa habere kadar seç.
3. Her haberi web araması ve sayfa okumasıyla doğrula. Doğrulayamadığını bırak.
{chr(10).join('4. ' + e for e in extras)}

Çıktın, yazara verilecek bir dosya olsun (düz metin). Her haber için şunları yaz:
- Konu (kısa)
- İlçe: şu listeden biri ya da il geneli için "Samsun": {', '.join(SAMSUN_DISTRICTS)}
- Doğrulanmış olgular: kim, ne, nerede, ne zaman, varsa önemli sayılar (madde madde)
- Okur için neden önemli (kaynaklara dayanarak, spekülasyonsuz)
- Kaynak adları ve okuduğun sayfaların adresleri
Kısa haberler için tek satırlık olgu, ilçe ve kaynak yeterli."""

    client = _client()
    tools = [
        {"type": "web_search_20260209", "name": "web_search", "max_uses": 12,
         "user_location": {"type": "approximate", "city": "Samsun", "country": "TR", "timezone": "Europe/Istanbul"}},
        {"type": "web_fetch_20260209", "name": "web_fetch", "max_uses": 15},
    ]
    messages = [{"role": "user", "content": prompt}]
    responses = []
    for _ in range(8):  # server tools may pause a long turn; resume by appending the assistant content
        with client.beta.messages.stream(
            model=MODEL,
            max_tokens=64000,
            betas=[FALLBACK_BETA],
            fallbacks="default",
            cache_control={"type": "ephemeral"},
            system=EDITORIAL_RULES,
            messages=messages,
            tools=tools,
            output_config={"effort": "high"},
        ) as stream:
            msg = stream.get_final_message()
        responses.append(msg)
        if msg.stop_reason == "pause_turn":
            # consecutive assistant messages are merged into one turn by the API
            messages.append({"role": "assistant", "content": msg.content})
            continue
        _check_stop(msg, "research")
        dossier = _text(msg) or "\n".join(_text(m) for m in responses)
        if not dossier:
            raise RuntimeError("research: empty dossier")
        return dossier
    raise RuntimeError("research: too many pause_turn continuations")


def _schema(edition: str) -> dict:
    s = {"type": "string"}
    story = {
        "type": "object",
        "properties": {
            "category": {"type": "string", "enum": CATEGORIES},
            "district": {"type": "string", "enum": SAMSUN_DISTRICTS + ["Samsun"]},
            "location": s, "title": s, "short_title": s,
            "stat": {"type": "object", "properties": {"value": s, "label": s},
                     "required": ["value", "label"], "additionalProperties": False},
            "body": s, "why": s,
            "sources": {"type": "array", "items": s},
        },
        "required": ["category", "district", "location", "title", "short_title", "stat", "body", "why", "sources"],
        "additionalProperties": False,
    }
    brief = {
        "type": "object",
        "properties": {"category": {"type": "string", "enum": CATEGORIES},
                       "district": {"type": "string", "enum": SAMSUN_DISTRICTS + ["Samsun"]},
                       "text": s, "sources": {"type": "array", "items": s}},
        "required": ["category", "district", "text", "sources"], "additionalProperties": False,
    }
    outage = {
        "type": "object",
        "properties": {"kind": {"type": "string", "enum": ["bolt", "droplet"]}, "title": s, "text": s, "source": s},
        "required": ["kind", "title", "text", "source"], "additionalProperties": False,
    }
    score = {
        "type": "object",
        "properties": {"present": {"type": "boolean"}, "competition": s, "home": s, "away": s,
                       "home_score": {"type": "integer"}, "away_score": {"type": "integer"}},
        "required": ["present", "competition", "home", "away", "home_score", "away_score"],
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {"stories": {"type": "array", "items": story}, "briefs": {"type": "array", "items": brief},
                       "outages": {"type": "array", "items": outage}, "scoreboard": score, "hook": s},
        "required": ["stories", "briefs", "outages", "scoreboard", "hook"],
        "additionalProperties": False,
    }


LIMITS = {"title": 70, "short_title": 46, "location": 30, "body": 340, "why": 130,
          "stat.value": 12, "stat.label": 42, "brief": 115, "hook": 180}

WRITING_RULES = f"""Yazım kuralları (görsel şablona sığması için sınırlar kesindir):
- title: haber başlığı, en fazla {LIMITS['title']} karakter, nokta yok, cümle düzeninde (yalnızca ilk harf ve özel adlar büyük). 20 karakterden uzun tek kelimelerden kaçın.
- short_title: kapaktaki liste için kısa başlık, en fazla {LIMITS['short_title']} karakter.
- location: yer adı, en fazla {LIMITS['location']} karakter (ör. "Atakum sahili", "Bafra Karma OSB").
- district: haberin geçtiği ilçe; il genelini ilgilendiriyorsa "Samsun".
- category: verilen listeden en uygunu.
- body: iki kısa paragraf, aralarında tek satır sonu (\\n), toplam en fazla {LIMITS['body']} karakter. Yalnızca dosyadaki doğrulanmış olgular.
- why: "Neden önemli" satırı, okura somut etkisi, tek cümle, en fazla {LIMITS['why']} karakter. Her haberde zorunlu.
- stat: haberde gerçekten öne çıkan bir sayı varsa value (en fazla {LIMITS['stat.value']} karakter, ör. "%85", "250", "50 milyon TL") ve label (en fazla {LIMITS['stat.label']} karakter); yoksa ikisi de boş metin "".
- sources: yayın ya da kurum adları (adres değil), ör. ["AA", "Samsun Büyükşehir Belediyesi"].
- briefs: her biri tek cümle, en fazla {LIMITS['brief']} karakter.
- outages: yalnızca dosyada bugüne ait doğrulanmış kesinti varsa; kind elektrik için "bolt", su için "droplet".
- scoreboard: yalnızca spor bülteninde, Samsunspor son 24 saatte resmi maç oynadıysa present=true; yoksa present=false ve diğer alanlar boş/0.
- hook: Instagram açıklamasının ilk cümlesi, günün öne çıkanını merak uyandırarak ama abartmadan anlatır, en fazla {LIMITS['hook']} karakter, emoji yok.
- Sayılar Türkçe yazımla: "%85", "12.30", "1,5 milyon". Türkçe karakterleri doğru kullan."""


def write(edition: str, date_label: str, dossier: str, fix_note: str = "", previous: dict | None = None) -> dict:
    """Turn the dossier into the issue JSON. With fix_note/previous it rewrites only what's flagged."""
    ed = EDITIONS[edition]
    if previous is None:
        task = (f"Bugün {date_label}. Aşağıdaki doğrulanmış dosyadan \"{ed['label']}\" bültenini yaz. "
                f"stories listesinde en fazla {ed['max_stories']} haber olsun, ilki manşet. "
                f"briefs en fazla {ed['max_briefs']} tane. Dosyada olmayan hiçbir bilgiyi ekleme.\n\n"
                f"<dosya>\n{dossier}\n</dosya>")
    else:
        task = (f"Aşağıdaki bülten JSON'unda şu sorunlar var:\n{fix_note}\n\n"
                f"Yalnızca bu sorunları düzelt; içeriği ve olguları değiştirme. Dosya referans için aşağıda.\n\n"
                f"<bulten>\n{json.dumps(previous, ensure_ascii=False)}\n</bulten>\n\n<dosya>\n{dossier}\n</dosya>")
    client = _client()
    with client.beta.messages.stream(
        model=MODEL,
        max_tokens=32000,
        betas=[FALLBACK_BETA],
        fallbacks="default",
        system=EDITORIAL_RULES + "\n\n" + WRITING_RULES,
        messages=[{"role": "user", "content": task}],
        output_config={"effort": "high", "format": {"type": "json_schema", "schema": _schema(edition)}},
    ) as stream:
        msg = stream.get_final_message()
    _check_stop(msg, "write")
    return json.loads(_text(msg))


def problems(issue: dict) -> list:
    """Length/shape problems the writer must fix (rendering would otherwise shrink or overflow)."""
    out = []
    for i, st in enumerate(issue["stories"], start=1):
        for key in ("title", "short_title", "location", "body", "why"):
            if len(st[key]) > LIMITS[key]:
                out.append(f"stories[{i}].{key} {len(st[key])} karakter, en fazla {LIMITS[key]} olmalı")
        if not st["why"].strip():
            out.append(f"stories[{i}].why boş; zorunlu")
        if not st["sources"]:
            out.append(f"stories[{i}].sources boş; en az bir kaynak adı gerekli")
        if len(st["stat"]["value"]) > LIMITS["stat.value"]:
            out.append(f"stories[{i}].stat.value çok uzun (en fazla {LIMITS['stat.value']})")
        if len(st["stat"]["label"]) > LIMITS["stat.label"]:
            out.append(f"stories[{i}].stat.label çok uzun (en fazla {LIMITS['stat.label']})")
        if st["body"].count("\n") > 1:
            out.append(f"stories[{i}].body en fazla iki paragraf olmalı")
    for i, b in enumerate(issue["briefs"], start=1):
        if len(b["text"]) > LIMITS["brief"]:
            out.append(f"briefs[{i}].text {len(b['text'])} karakter, en fazla {LIMITS['brief']} olmalı")
    if len(issue["hook"]) > LIMITS["hook"]:
        out.append(f"hook {len(issue['hook'])} karakter, en fazla {LIMITS['hook']} olmalı")
    return out
