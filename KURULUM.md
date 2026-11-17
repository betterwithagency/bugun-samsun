# Bugün Samsun · Kurulum rehberi

Bu proje her gün üç bülteni kendiliğinden hazırlayıp @bugunsamsun hesabında paylaşır:

| Bülten | Hazırlık başlar | Yayın |
|---|---|---|
| Gündem | 07.07 | 08.00 |
| Ekonomi & İş | 11.37 | 12.30 |
| Spor | 18.07 | 19.00 |

Her çalıştırmada sırasıyla şunlar olur:
1. Google Haberler'den son 24 saatin Samsun haberleri toplanır.
2. Claude haberleri seçer ve web'de kaynak sayfalarını okuyarak doğrular.
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

## 3. Anthropic API anahtarı al

1. [console.anthropic.com](https://console.anthropic.com) adresinde hesap aç ya da giriş yap.
2. *Billing* bölümünden kredi yükle. **Aylık harcama limiti** koymanı öneririm.
3. *API Keys → Create Key* ile bir anahtar oluştur. Bu senin **ANTHROPIC_API_KEY** değerin.

**Tahmini maliyet:** Varsayılan model Claude Opus 5.5. Her bülten web araması, sayfa okuma ve yazım dahil yaklaşık 1-2 $ tutar; günde 3 bültenle ayda yaklaşık 90-180 $.

**Daha ucuz seçenek:** GitHub'da *Settings → Secrets and variables → Actions → Variables* bölümünde `BULTEN_MODEL` değişkenini `claude-sonnet-5-5` yaparsan maliyet yaklaşık yarıya iner. İlk hafta Console'daki *Usage* ekranından gerçek tutarı izle.

## 4. GitHub deposu

Depo hazır: **https://github.com/betterwithagency/bugun-samsun** (public).

- **Neden public:** Instagram görselleri bir web adresinden çekiyor. Görseller depodaki ayrı bir `media` dalından yayınlanıyor.
- **Gizli kalanlar:** Şifreler ve anahtarlar herkese açık değildir; GitHub Secrets'ta saklanır. Depoya kaydedilen Instagram anahtarı da şifrelidir.
- **Duraklatılmış teslim:** Depo `data/PAUSE` dosyasıyla duraklatılmış olarak geldi. Zamanlanmış çalıştırmalar sen hazır olana kadar hiçbir şey yapmadan biter.

*Settings → Secrets and variables → Actions → New repository secret* ile gizli değerler:

| Ad | Değer |
|---|---|
| `ANTHROPIC_API_KEY` | 3. adımdaki anahtar |
| `IG_ACCESS_TOKEN` | 2. adımdaki Instagram anahtarı |

Değişken (*Variables* sekmesi): `IG_USER_ID` = `17841475041510019` (eklendi).
| `TOKEN_KEY` (isteğe bağlı) | Yalnızca 60 günlük Instagram girişi anahtarı kullanılırsa gerekir; süresiz sistem kullanıcısı anahtarında gerekmez. Uzun, rastgele bir paroladır (en az 32 karakter) ve yenilenen anahtarı şifrelemek için kullanılır. Şu komutla değeri görmeden üretip ekleyebilirsin: `python3 -c "import secrets; print(secrets.token_urlsafe(32))" \| gh secret set TOKEN_KEY -R betterwithagency/bugun-samsun` |

İpucu: `gh secret set ANTHROPIC_API_KEY -R betterwithagency/bugun-samsun` komutu değeri gizli olarak sorar. Anahtarı terminale yapıştırırsın; başka hiçbir yerde görünmez.

## 5. Önce deneme, sonra canlı

1. **Kuru deneme** (duraklatma açıkken de çalışır):
   - Deponun *Actions* sekmesinde **Bugün Samsun → Run workflow** de.
   - Bülten olarak `gundem` seç, "Instagram'a gönder" kutusunu **boş bırak**.
   - İş bitince sayfanın altındaki `bulten-gundem-…` dosyasını indir. İçinde kareler, Instagram açıklaması (`caption.txt`) ve Claude'un araştırma notları (`dosya.md`) var.
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

İçerik yapay zekâ tarafından yazılıyor ve insan onayı olmadan yayınlanıyor. Yayın kuralları `bulten/write.py` dosyasının başında. Bu kurallar Claude'a şunları söylüyor:
- Yalnızca kaynak sayfası okunarak doğrulanmış haberleri kullan.
- Suç ve kaza haberlerinde kişi adı verme.
- İntihar haberlerini dahil etme.
- Siyasi polemiğe girme.
- Kaynak metni kopyalama.

Yine de hesabın sorumluluğu sende. İlk iki hafta paylaşımları her gün kontrol etmeni öneririm.

## Teknik notlar

- **Yerelde deneme:**
  - `python -m bulten run --edition gundem` komutu kareleri `output/` klasörüne üretir, yayın yapmaz. `ANTHROPIC_API_KEY` ortam değişkeni gerekir.
  - `--issue samples/gundem.json` ile yapay zekâ adımı atlanır; şablon testi için kullanılır. Aynı test GitHub'da *Run workflow* ekranındaki "Şablon testi" kutusuyla da çalışır.
- **Tasarım:**
  - Şablon `templates/klasik.html.j2`. Fontlar Libron (başlık) ve Lexend (metin), ikisi de SIL OFL 1.1 lisanslı.
  - Harita verisi © OpenStreetMap katkıcıları (ODbL), geoBoundaries üzerinden.
  - Hava ve deniz verisi Open-Meteo'dan gelir.
