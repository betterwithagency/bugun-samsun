# Bugün Samsun

@bugunsamsun Instagram hesabı için otomatik haber bülteni: her gün 08.00 Gündem, 12.30 Ekonomi & İş, 19.00 Spor.

- Kurulum ve günlük kullanım: [KURULUM.md](KURULUM.md)
- Akış: `bulten/pipeline.py` (topla → araştır → yaz → kontrol → çiz → yayınla)
- Yayın kuralları ve yazım talimatları: `bulten/write.py` (yapay zekâ: `ai_gemini.py`, isteğe bağlı `ai_claude.py`)
- Tasarım: `templates/klasik.html.j2`
- Zamanlama: `.github/workflows/bulten.yml`
