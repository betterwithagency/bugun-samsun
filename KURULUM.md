# Bugün Samsun · Kurulum rehberi

Bu proje her gün üç bülteni kendiliğinden hazırlayıp @bugunsamsun hesabında paylaşır:

| Bülten | Hazırlık başlar | Yayın |
|---|---|---|
| Gündem | 07.07 | 08.00 |
| Ekonomi & İş | 11.37 | 12.30 |
| Spor | 18.07 | 19.00 |

### Bültenleri ne başlatır?
GitHub'ın kendi zamanlaması (cron) bu depoda saatlerce geç çalıştı: 18 Kasım'ın Spor tetikleyicisi gece 01.33'te
başladı ve ikinci bir Spor bülteni paylaştı. Bu yüzden bültenleri artık yalnızca **Zamanlayıcı** başlatır.
*Actions* sekmesinde bu iş akışının her zaman bir çalıştırması açık durur. Bu çalıştırma bir sonraki hazırlık
saatine kadar bekler, bülteni başlatır ve kendinden sonrakini başlatır. Uzun aralar (gece gibi) en fazla 5,5
saatlik ara adımlarla geçilir.

Aynı bülten iki kez paylaşılmasın diye üç kontrol var:
1. **Yayın penceresi:** Zamanlayıcının başlattığı bülten yalnızca yayın saatinden 3 saat önce ile 2 saat sonra
   arasında paylaşılır. Geç kalan bir tetikleyici hiçbir şey göndermez.
2. **Kayıt:** Aynı bülten son 14 saat içinde paylaşılmışsa (`data/state.json`) çalıştırma göndermeden kapanır.
3. **Hesap:** Göndermeden hemen önce Instagram hesabında son 14 saatte aynı bültenin paylaşılıp paylaşılmadığına bakılır.

- **Zamanlayıcı durursa** (*Actions → Zamanlayıcı* altında çalışan bir iş yoksa): *Run workflow* ile yeniden başlat;
  alanları boş bırakman yeterli.
- **Zamanlayıcıyı tamamen durdurmak için:** çalışan Zamanlayıcı işini *Cancel workflow run* ile iptal et.

Her çalıştırmada sırasıyla şunlar olur:
1. Google Haberler'den son 24 saatin Samsun haberleri toplanır.
2. Yapay zekâ (Gemini) haberleri seçer ve web'de kaynak sayfalarını okuyarak doğrular.
3. Bülten metni yazılır, uzunluklar kontrol edilir.
4. Görseller şablondan üretilir.
5. Yayın saatinde Instagram'a carousel olarak gönderilir.

Hepsi GitHub Actions'ta çalışır; senin bilgisayarının açık olması gerekmez.

Aşağıdaki adımları bir kez yapman yeterli. Toplam süre yaklaşık 30-45 dakika.

---

## 1. Instagram hesabı (tamamlandı)

- @bugunsamsun **İşletme** hesabı; kategori "News & media website" profilde görünüyor.
- **Isınma:** Otomasyonu başlatmadan önce birkaç gün hesabı normal kullan (elle 1-2 paylaşım, hikâye). Yeni hesapların hemen otomatik paylaşıma başlaması kısıtlamaya yol açabilir.

## 2. Instagram yayın anahtarı

Meta'da kurulu olanlar:
- **Uygulama:** "Bugun Samsun Yayinci"; bw/a işletme portföyüne bağlı, *API setup with Unified login* yöntemiyle.
- **İzinler:** Yalnızca `instagram_basic` ve `instagram_content_publish` istenir. `instagram_manage_messages` de görünür; Meta bunu zorunlu tutuyor.
- **Test kullanıcısı:** @bugunsamsun uygulamaya test kullanıcısı olarak eklendi ve daveti kabul edildi.
- **Hesap kimliği:** `17841475041510019`. GitHub'da `IG_USER_ID` değişkeni olarak kayıtlı.

Anahtarı yeniden üretmen gerekirse:
1. Uygulama panosunda *Kullanım durumları → Instagram API → API setup with Unified login → 2. Generate access tokens* bölümünü aç.
2. @bugunsamsun satırında **Generate token** de.
3. Çıkan anahtarı kopyala ve terminalde `gh secret set IG_ACCESS_TOKEN -R betterwithagency/bugun-samsun` komutuyla yapıştır.

Bu yöntemin anahtarı bir **sistem kullanıcısı anahtarıdır** ve süresi dolmaz; yenilemeye gerek yoktur. Eski tür Instagram girişi anahtarları da desteklenir; bunlar haftalık olarak kendiliğinden yenilenir.

## 3. Yapay zekâ anahtarı (Gemini)

Haberleri seçen, web'de doğrulayan ve yazan yapay zekâ varsayılan olarak **Google Gemini**. Araştırma için Google Arama ve sayfa okuma araçlarını kullanır.

1. [Google AI Studio](https://aistudio.google.com) → *Get API key* bölümünden bir anahtar oluştur. Faturalandırma tanımlı bir proje seç.
2. Anahtarı GitHub'da *Settings → Secrets and variables → Actions → New repository secret* ile `GEMINI_API_KEY` adıyla ekle. Anahtarı sohbete ya da başka bir yere yapıştırma.

**Model:** Varsayılan `gemini-4-argon` (Google'ın verimli Gemini 4 akıl yürütme modeli). Daha güçlü ama daha pahalı `gemini-4-carbon` için *Variables* sekmesinde `BULTEN_GEMINI_MODEL` değişkenini değiştir.

**Maliyet:** Google Arama ile beslenen yanıtlarda ayda 5.000 arama ücretsiz. Sonrası 1.000 arama başına 14 $ (Gemini 3 ve sonrası için). Bültenler ayda yaklaşık 1.000 arama yapar. Model kullanım ücretleri için Google AI Studio'daki fiyat sayfasına bak ve ilk hafta faturalandırma ekranından gerçek tutarı izle.

**Claude'a geçmek istersen:** `BULTEN_PROVIDER` değişkenini `claude` yap ve `ANTHROPIC_API_KEY` gizli değerini ekle. Model `BULTEN_MODEL` ile seçilir, varsayılanı `claude-opus-5-5`.

## 4. GitHub deposu

Depo hazır: **https://github.com/betterwithagency/bugun-samsun** (public).

- **Neden public:** Instagram görselleri bir web adresinden çekiyor. Görseller depodaki ayrı bir `media` dalından yayınlanıyor.
- **Gizli kalanlar:** Şifreler ve anahtarlar herkese açık değildir; GitHub Secrets'ta saklanır. Depoya kaydedilen Instagram anahtarı da şifrelidir.
- **Duraklatılmış teslim:** Depo `data/PAUSE` dosyasıyla duraklatılmış olarak geldi. Zamanlanmış çalıştırmalar sen hazır olana kadar hiçbir şey yapmadan biter.

*Settings → Secrets and variables → Actions → New repository secret* ile gizli değerler:

| Ad | Değer |
|---|---|
| `GEMINI_API_KEY` | 3. adımdaki Gemini anahtarı |
| `IG_ACCESS_TOKEN` | 2. adımdaki Instagram anahtarı |

Değişken (*Variables* sekmesi): `IG_USER_ID` = `17841475041510019` (eklendi).
| `TOKEN_KEY` (isteğe bağlı) | Yalnızca 60 günlük Instagram girişi anahtarı kullanılırsa gerekir; süresiz sistem kullanıcısı anahtarında gerekmez. Uzun, rastgele bir paroladır (en az 32 karakter) ve yenilenen anahtarı şifrelemek için kullanılır. Şu komutla değeri görmeden üretip ekleyebilirsin: `python3 -c "import secrets; print(secrets.token_urlsafe(32))" \| gh secret set TOKEN_KEY -R betterwithagency/bugun-samsun` |

İpucu: Gizli değerleri GitHub'ın *New secret* sayfasından eklemek en kolayı. Eklediğin anahtarların çalıştığını *Run workflow* ekranındaki **Bağlantı kontrolü** kutusuyla, hiçbir şey yayınlamadan deneyebilirsin.

## 5. Önce deneme, sonra canlı

1. **Kuru deneme** (duraklatma açıkken de çalışır):
   - Deponun *Actions* sekmesinde **Bugün Samsun → Run workflow** de.
   - Bülten olarak `gundem` seç, "Instagram'a gönder" kutusunu **boş bırak**.
   - İş bitince sayfanın altındaki `bulten-gundem-…` dosyasını indir. İçinde kareler, Instagram açıklaması (`caption.txt`) ve yapay zekânın araştırma notları (`dosya.md`) var.
2. **Canlıya geçiş:** Sonuç iyiyse depoda `data/PAUSE` dosyasını aç, çöp kutusu simgesiyle sil ve değişikliği kaydet.
3. **İlk gerçek paylaşım:** İstersen hemen bir tane göndermek için *Run workflow*'u "Instagram'a gönder" kutusu **işaretli** olarak çalıştır. Yoksa bir sonraki yayın saatini bekle; zamanlanmış çalıştırmalar artık kendiliğinden yayın yapar.

## Günlük kullanım

- **Duraklatmak için:** Depoda *Add file → Create new file* ile `data/PAUSE` adlı boş bir dosya oluştur ve kaydet. Yayınlar durur. Dosyayı silince devam eder.
- **Bir şey ters giderse:** GitHub başarısız çalıştırmalarda sana e-posta gönderir. Ayrıntılar *Actions* sekmesinde.
- **Haber az olduğunda:** Ekonomi ya da Spor'da o gün doğrulanmış en az 3 haber yoksa o bülten atlanır. Bu bir hata sayılmaz.
- **Arşiv:**
  - Yayınlanan her bültenin metni ve kaynakları `data/issues/` klasöründe tutulur.
  - Son 30 günün başlıkları `data/history.json` dosyasındadır; aynı haberin tekrar yayınlanmasını bu engeller.

## Yayın sorumluluğu

İçerik yapay zekâ tarafından yazılıyor ve insan onayı olmadan yayınlanıyor. Yayın kuralları `bulten/write.py` dosyasının başında. Bu kurallar yapay zekâya şunları söylüyor:
- Yalnızca kaynak sayfası okunarak doğrulanmış haberleri kullan.
- Suç ve kaza haberlerinde kişi adı verme.
- İntihar haberlerini dahil etme.
- Siyasi polemiğe girme.
- Kaynak metni kopyalama.

Yine de hesabın sorumluluğu sende. İlk iki hafta paylaşımları her gün kontrol etmeni öneririm.

## Teknik notlar

- **Yerelde deneme:**
  - `python -m bulten run --edition gundem` komutu kareleri `output/` klasörüne üretir, yayın yapmaz. `GEMINI_API_KEY` ortam değişkeni gerekir.
  - `--issue samples/gundem.json` ile yapay zekâ adımı atlanır; şablon testi için kullanılır. Aynı test GitHub'da *Run workflow* ekranındaki "Şablon testi" kutusuyla da çalışır.
- **Tasarım:**
  - Şablon `templates/klasik.html.j2`. Fontlar Libron (başlık) ve Lexend (metin), ikisi de SIL OFL 1.1 lisanslı.
  - Harita verisi © OpenStreetMap katkıcıları (ODbL), geoBoundaries üzerinden.
  - Hava ve deniz verisi Open-Meteo'dan gelir.
