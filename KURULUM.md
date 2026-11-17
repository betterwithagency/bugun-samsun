# Samsun Bülten · Kurulum rehberi

Bu proje her gün üç bülteni kendiliğinden hazırlayıp @samsun.bulten hesabında paylaşır:

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

## 1. Instagram hesabını hazırla

1. **Doğrulama:** Hesap şu an "doğrulama selfiesi" istiyor. Instagram uygulamasından selfie'yi gönder ve hesabın açılmasını bekle (genelde 1-2 gün).
2. **Profesyonel hesap:** Hesap açılınca *Ayarlar → Hesap türü ve araçlar → Profesyonel hesaba geç* yolunu izle. "İşletme" seç, kategori olarak "Medya/Haber şirketi" ya da benzerini seç.
3. **Isınma:** Otomasyonu başlatmadan önce birkaç gün hesabı normal kullan: profil fotoğrafı, biyografi, elle 1-2 paylaşım. Yeni hesapların hemen otomatik paylaşıma başlaması tekrar kısıtlamaya yol açabilir.

## 2. Instagram yayın anahtarını (access token) al

1. [developers.facebook.com](https://developers.facebook.com) adresine Facebook hesabınla gir, gerekiyorsa geliştirici hesabı oluştur.
2. *Uygulamalarım → Uygulama oluştur* yolunu izle. Kullanım alanı olarak **"Instagram'da mesajları ve içeriği yönet"** seç. Uygulamaya örneğin "Samsun Bülten Yayıncı" adını ver.
3. Uygulama panosunda **Instagram → Instagram girişi ile API kurulumu** bölümünü aç.
4. **"Erişim belirteçleri oluştur"** adımında *Hesap ekle* de ve @samsun.bulten ile giriş yap. İzinleri onayla; en az `instagram_business_basic` ve `instagram_business_content_publish` izinleri gerekli.
   - Hesap eklenemezse: *Uygulama rolleri → Roller → Instagram test kullanıcısı ekle* ile @samsun.bulten'i ekle. Ardından daveti Instagram'da kabul et (*Ayarlar → Web sitesi izinleri → Uygulamalar ve web siteleri → Test kullanıcısı davetleri*). Sonra bu adımı tekrarla.
5. Oluşan uzun bir metni kopyala. Bu senin **IG_ACCESS_TOKEN** değerin. Kimseyle paylaşma.

Bu anahtar 60 gün geçerli. Sistem onu her hafta kendiliğinden yeniler, yani normalde bir daha uğraşmazsın.

## 3. Anthropic API anahtarı al

1. [console.anthropic.com](https://console.anthropic.com) adresinde hesap aç ya da giriş yap.
2. *Billing* bölümünden kredi yükle. **Aylık harcama limiti** koymanı öneririm.
3. *API Keys → Create Key* ile bir anahtar oluştur. Bu senin **ANTHROPIC_API_KEY** değerin.

**Tahmini maliyet:** Varsayılan model Claude Opus 5.5. Her bülten web araması, sayfa okuma ve yazım dahil yaklaşık 1-2 $ tutar; günde 3 bültenle ayda yaklaşık 90-180 $.

**Daha ucuz seçenek:** GitHub'da *Settings → Secrets and variables → Actions → Variables* bölümünde `BULTEN_MODEL` değişkenini `claude-sonnet-5-5` yaparsan maliyet yaklaşık yarıya iner. İlk hafta Console'daki *Usage* ekranından gerçek tutarı izle.

## 4. GitHub deposu

Depo hazır: **https://github.com/betterwithagency/samsun-bulten** (public).

- **Neden public:** Instagram görselleri bir web adresinden çekiyor. Görseller depodaki ayrı bir `media` dalından yayınlanıyor.
- **Gizli kalanlar:** Şifreler ve anahtarlar herkese açık değildir; GitHub Secrets'ta saklanır. Depoya kaydedilen Instagram anahtarı da şifrelidir.
- **Duraklatılmış teslim:** Depo `data/PAUSE` dosyasıyla duraklatılmış olarak geldi. Zamanlanmış çalıştırmalar sen hazır olana kadar hiçbir şey yapmadan biter.

*Settings → Secrets and variables → Actions → New repository secret* ile üç gizli değer ekle:

| Ad | Değer |
|---|---|
| `ANTHROPIC_API_KEY` | 3. adımdaki anahtar |
| `IG_ACCESS_TOKEN` | 2. adımdaki Instagram anahtarı |
| `TOKEN_KEY` | Uzun, rastgele bir parola (en az 32 karakter). Yenilenen Instagram anahtarını şifrelemek için kullanılır. Şu komutla değeri görmeden üretip ekleyebilirsin: `python3 -c "import secrets; print(secrets.token_urlsafe(32))" \| gh secret set TOKEN_KEY -R betterwithagency/samsun-bulten` |

İpucu: `gh secret set ANTHROPIC_API_KEY -R betterwithagency/samsun-bulten` komutu değeri gizli olarak sorar. Anahtarı terminale yapıştırırsın; başka hiçbir yerde görünmez.

## 5. Önce deneme, sonra canlı

1. **Kuru deneme** (duraklatma açıkken de çalışır):
   - Deponun *Actions* sekmesinde **Samsun Bülten → Run workflow** de.
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
