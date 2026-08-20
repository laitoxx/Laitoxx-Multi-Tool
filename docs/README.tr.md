# Laitoxx Multi-Tool 3.0.0-rc.1

[English](../README.md) | [Русский](README.ru.md) | [Українська](README.uk.md) | [Türkçe](README.tr.md)

<img src="../screenshot.png" alt="Laitoxx Multi-Tool arayüzü" width="100%"/>

> **Sürüm adayı:** 3.0.0-rc.1, bir sonraki büyük sürümün önizlemesidir.
> Mimari, yükleyici, tarama, grafik ve OSINT araçlarında kapsamlı değişiklikler
> içerir. 2.x sürümünden yükseltmeden önce önemli raporlarınızı ve ayarlarınızı
> yedekleyin.

Laitoxx; herkese açık teknik kanıtları toplamak, ilişkilendirmek ve dışa
aktarmak için geliştirilmiş masaüstü OSINT ve savunma güvenliği çalışma
ortamıdır. Odaklanmış araştırma araçlarını, yerel analizi, ilişki grafiklerini
ve genişletilebilir Lua eklenti sistemini PyQt6 arayüzünde bir araya getirir.

Laitoxx'u yalnızca sahibi olduğunuz veya incelemek için açık izniniz bulunan
sistemler ve veriler üzerinde kullanın. Proje eğitim, araştırma, olay müdahalesi
ve yasal güvenlik değerlendirmeleri için tasarlanmıştır. Geliştiriciler kötüye
kullanımdan sorumlu değildir.

## 3.0 sürümündeki yenilikler

- **Advanced Web Scanner:** DNS, kayıt, sertifika, yönlendirme, açık servis,
  tehdit istihbaratı, arşiv ve güvenlik açığı kaynaklarını tek bir kanıt grafiği
  ve zaman çizelgesinde ilişkilendirir. Varsayılan olarak pasif toplama yapar;
  sınırlandırılmış yerel doğrulama açıkça etkinleştirilir.
- **TONgue:** Telegram kimlikleri, TON adresleri, koleksiyonluk Gifts, NFT'ler
  ve herkese açık işlem kanıtlarından birleşik bir araştırma grafiği ile
  JSON/CSV raporları oluşturur.
- **Masscan çalışma alanı:** eski Nmap tabanlı port tarayıcısının yerine
  Masscan 1.3.2 keşfi, sınırlandırılmış banner toplama ve yerel servis parmak izi
  analizi getirir.
- **CogniPass entegrasyonu:** sabitlenmiş Zig parola üretim motorunu mevcut CPU
  için derler ve ayrı bir grafik arayüz üzerinden sunar.
- **Araştırma odaklı araçlar:** IOC çıkarma, Domain Intelligence,
  yapılandırılmış Web Crawler, steganografi çalışma alanı ve 86 modlu Text
  Cipher eklendi.
- **Yenilenen temel:** özellik odaklı `src` mimarisi, gecikmeli araç yükleme,
  merkezi ağ politikası, işletim sistemine özel çalışma verileri, daha güvenli
  Lua eklentileri, modüler GUI denetleyicileri ve ortak grafik/rapor bileşenleri.

3.0.0-rc.1 değişikliklerinin tamamı ve karşılaştırma temeli için
[CHANGELOG.md](../CHANGELOG.md) dosyasına bakın.

## Yetenekler

### OSINT ve araştırmalar

- Coğrafi konum, itibar, açık servis ve HTTP kanıtlarıyla IP istihbaratı.
- DNS, RDAP, HTTP, TLS, sertifika ve sınırlandırılmış alt alan adı keşfiyle
  Domain Intelligence.
- 500'den fazla sitelik katalogda Username OSINT; sağlayıcı sağlık takibi,
  kullanıcı adı üretimi, profil kanıtları, avatar işleme ve grafik dışa aktarma.
- E-posta doğrulama ve herkese açık veri zenginleştirme.
- Google dork oluşturucu, yerel veri tabanı araması, görsel arama ve adli görsel
  inceleme.
- Herkese açık konumlandırma verileriyle küresel Wi-Fi/MAC sorgulama.
- Kapsam denetimi, endpoint/form keşfi, raporlar ve grafik izdüşümüyle
  yapılandırılmış web sitesi taraması.
- IP, alan adı, URL, e-posta adresi, telefon numarası, hash, JWT ve kullanıcı adı
  için IOC çıkarma.
- Telegram, TON cüzdanları, Gifts, NFT'ler, sahiplik geçmişi, hareketler ve
  herkese açık kanıtlar için TONgue araştırmaları.

### Web ve ağ değerlendirmesi

- Kanıt kaynağı, güven durumları, kotalar, önbellek, zaman çizelgeleri ve ilişki
  grafikleriyle Advanced Web Scanner.
- Naabu, httpx, Nuclei ve mevcut bir WPScan kurulumu ile isteğe bağlı yerel
  doğrulama.
- Yerel banner ve servis parmak izi analiziyle Masscan port keşfi.
- HTTP Inspector, teknoloji parmak izi, pasif CMS denetimi ve JWT analizi.
- TLS, CORS, yönlendirme ve güvenlik başlığı kontrolleri.
- IPv4/IPv6 CIDR hesaplayıcı ve düzenli ifade test aracı.

### Yerel yardımcı araçlar

- Meta veri inceleme, gizlilik puanlama, temizleme ve dosya adli analizi.
- Steganografi kodlama, çıkarma ve inceleme; kapasite kontrolleri ile kimliği
  doğrulanmış/şifrelenmiş veri kapsayıcıları.
- Metin hashleme, hash türü belirleme ve rainbow table oluşturma.
- 86 yerel kodlama, klasik şifre, metin işlemi, hash, sayı/tarih/renk dönüşümü
  ve sembol dönüşümü içeren Text Cipher.
- Standart parola üretici ve ayrı CogniPass hedefli parola üreticisi.
- Düzenler, stiller, içe/dışa aktarma, analiz ve geri alınabilir düzenleme
  özellikli yerel ilişki grafiği editörü.

### Uygulama platformu

- Temalar, arka plan özelleştirme, komut paleti, görev denetimleri ve dört
  arayüz dili bulunan PyQt6 masaüstü arayüzü.
- Lua eklenti keşfi, yapılandırma, sözdizimi araçları, kısıtlı yürütme ortamı ve
  grafik/OSINT servisleri için host API'leri.
- Uygulama genelinde SOCKS5 yönlendirme. Proxy koruması etkin olduğunda,
  uyumlu araçların ayarlanan rotayı sessizce atlamaması için doğrudan DNS ve
  socket erişimi engellenir.
- Yapılandırılmış raporlar, yeniden kullanılabilir kanıt grafikleri, yerel
  önbellek, rate limit takibi, ortak iptal mekanizması ve kısmi sonuç yönetimi.

## Gereksinimler

- Desteklenen x86/x64 veya ARM64 platformunda Windows, Linux ya da macOS.
- Python **3.10 ile 3.13 arası**. PyQt ve bağımlılık yığınının bazı parçaları
  henüz uyumlu olmadığından Python 3.14 bu sürümde desteklenmez.
- Bağımlılık kurulumu ve çevrimiçi OSINT sağlayıcıları için internet bağlantısı.
- Git önerilir. Sabitlenmiş kaynak arşivi normal şekilde indirilemezse
  doğrulanabilir yedek yöntem olarak da kullanılır.
- Masscan kaynak derlemesi için:
  - Linux/FreeBSD: `make` ve GCC ya da Clang gibi bir C derleyicisi;
  - macOS: `make` ve Xcode Command Line Tools;
  - Windows: `mingw32-make` ile GCC veya Clang içeren MinGW ve tarama için
    Npcap uyumlu paket sürücüsü.
- Masscan'ı çalıştırmak için genellikle yönetici/root yetkisi veya uygun
  raw-packet capability gerekir. Kurulum bu yetkileri otomatik olarak vermez.

## Kurulum

### Git ile klonlama

```sh
git clone https://github.com/laitoxx/Laitoxx-Multi-Tool.git
cd Laitoxx-Multi-Tool
```

Alternatif olarak GitHub'da **Code → Download ZIP** seçeneğini kullanın, arşivi
çıkarın ve çıkarılan dizinde bir terminal açın.

### Linux ve macOS

```sh
chmod +x install.sh
./install.sh
python3 start.py
```

### Windows

`install.bat` dosyasını Command Prompt üzerinden veya çift tıklayarak çalıştırın,
ardından uygulamayı başlatın:

```cmd
install.bat
python start.py
```

Yükleyici `venv` oluşturur, Python gereksinimlerini kurar, CogniPass'i derler,
doğrulanmış bağımsız tarayıcı sürümlerini yükler ve sabitlenmiş Masscan
kaynağını mevcut işletim sistemi ile CPU için derler. Eksik derleyici,
desteklenmeyen platform, indirme/checksum hatası, engellenen dosya veya başarısız
bağımlılık açıkça bildirilir. Zorunlu bir bileşen grubu başarısız olduğunda
yükleyici kurulumu başarılı göstermez.

Bu sürümde aşağıdaki bileşenler sabitlenmiştir:

| Bileşen | Sürüm veya kaynak | Kurulum yöntemi |
| --- | --- | --- |
| CogniPass | commit `1062c39102a8868e2a48a7496047eb24497d67bd` | yerel optimize Zig derlemesi |
| Masscan | 1.3.2 | doğrulanmış resmi kaynak derlemesi |
| Nuclei | 3.11.0 | doğrulanmış bağımsız sürüm |
| httpx | 1.10.0 | doğrulanmış bağımsız sürüm |
| Naabu | 2.6.1 | doğrulanmış bağımsız sürüm |

Resmi CLI aracı Ruby ve yerel derleme bağımlılıkları gerektirdiğinden WPScan
isteğe bağlıdır ve otomatik indirilmez. `wpscan` zaten `PATH` içinde bulunuyorsa
Laitoxx bunu algılar; bulunmadığında diğer pasif ve aktif aşamalar çalışmaya
devam eder.

## Çalıştırma ve güncelleme

Projeyi her zaman `start.py` üzerinden başlatın. Bu dosya yerel sanal ortamın
varlığını doğrular, bağlantı kontrolünü çalıştırır ve GUI'yi doğru `src` içe
aktarma yolu ile başlatır.

```sh
python3 start.py   # Linux/macOS
python start.py    # Windows
```

Git ile kurulan kopyalar açılıştan önce yapılandırılmış upstream'i kontrol
edebilir. `.git` meta verisi bulunmayan ZIP/kaynak anlık görüntüleri güncelleme
kontrolünü sorunsuz biçimde atlar.

Yazılabilir veriler kaynak ağacının dışında saklanır:

- Linux: `${XDG_DATA_HOME:-~/.local/share}/laitoxx`
- macOS: `~/Library/Application Support/Laitoxx`
- Windows: `%LOCALAPPDATA%\Laitoxx`

Farklı bir veri dizini kullanmak için `LAITOXX_DATA_DIR` ayarlayın.

## Advanced Web Scanner yapılandırması

Advanced Web Scanner ilk taramada zorunlu sağlayıcı kurulum denetimini açar.
Temel zincir, herkese açık endpoint'lerin yanı sıra ücretsiz IPinfo Lite ve
AbuseIPDB kimlik bilgilerini kullanır. İsteğe bağlı sağlayıcılar ayrı ayrı
etkinleştirilebilir. Desteklenen ortam değişkenleri şunlardır:

```text
IPINFO_TOKEN, OTX_API_KEY, ABUSEIPDB_API_KEY, NVD_API_KEY,
SHODAN_API_KEY, VIRUSTOTAL_API_KEY, URLSCAN_API_KEY,
GREYNOISE_API_KEY, GITHUB_TOKEN, VULNCHECK_API_TOKEN,
WPSCAN_API_TOKEN, HACKERTARGET_API_KEY, WHOISJSON_API_KEY,
BOTOI_API_KEY, LEAKIX_API_KEY, CERTSPOTTER_API_TOKEN
```

Yerel araç yolları `LAITOXX_<TOOL>_PATH` ile değiştirilebilir. Sağlayıcı
kotaları, bekleme süreleri, önbellek durumu, kısmi hatalar ve kanıt zaman
damgaları raporlarda görünür kalır. Teknik ayrıntılar
[`advanced_web_scanner/README.md`](../src/laitoxx/features/osint/advanced_web_scanner/README.md)
dosyasında açıklanmıştır.

## Eklentiler

Laitoxx, `lua_plugins/` dizinindeki Lua eklentilerini destekler. 3.0 çalışma
zamanı, Lua'nın sürece sınırsız erişmesi yerine kısıtlı bir ortam ve açık host
servisleri sunar. Birlikte verilen şablon ve geliştirme kılavuzuyla başlayın:

- [Eklenti şablonu](../lua_plugins/_template.lua)
- [Eklenti Geliştirme Kılavuzu](pluginBuilding.tr.md)

2.x sürümünden geçiş yapan eklenti geliştiricileri, mevcut bir eklentiyi
3.0.0-rc.1 içinde yüklemeden önce host API değişikliklerini incelemelidir.

## Mimari ve doğrulama

Uygulama özellik odaklı bir paket düzeni kullanır:

- `laitoxx.app` - composition root, araç kataloğu ve eklenti çalışma zamanı;
- `laitoxx.core` - ayarlar, yerelleştirme, yollar, TLS ve ağ politikası;
- `laitoxx.features` - bağımsız OSINT, ağ, web-audit, crypto ve utility
  özellikleri;
- `laitoxx.interfaces.gui` - PyQt sunum katmanı ve denetleyiciler;
- `laitoxx.shared` - yeniden kullanılabilir grafik, yürütme ve rapor bileşenleri.

Araç işleyicileri içe aktarma yolları olarak tanımlanır ve yalnızca
seçildiklerinde yüklenir. Böylece isteğe bağlı bir özelliğin hatası ana
arayüzün başlatılmasını engellemez. Bağımlılık kuralları ve genişletme rehberi
[ARCHITECTURE.md](ARCHITECTURE.md) dosyasında bulunur.

Bakım denetimleri şunları içerir:

```sh
venv/bin/python scripts/verify_dependencies.py
venv/bin/python scripts/check_structure.py
venv/bin/python scripts/verify_architecture.py
```

Çekirdek, GUI, worker, sağlayıcı, metin dönüşümü, steganografi, Web OSINT ve
TONgue çalışma zamanı denetimleri `scripts/` dizininde bulunur.

## Sürüm adayı notları

- Bu bir ön sürümdür. Regresyon bildirirken işletim sistemi, Python sürümü,
  tam hata metni ve yeniden üretme adımlarını ekleyin.
- Aktif ağ doğrulaması mevcut tarama için açıkça onaylanana kadar kapalıdır.
  Yetkiniz olmadan üçüncü taraf altyapısını taramayın.
- Çevrimiçi sağlayıcı kapsamı kimlik bilgilerine, kotalara, kullanılabilirliğe
  ve hedef türüne bağlıdır. Kısmi sonuçlar beklenen bir durumdur ve kaynak
  durumlarıyla birlikte korunur.
- Raw/yerel araçlar ilgili rotayı garanti edemediğinden SOCKS proxy koruması
  etkin olduğunda yerel tarayıcılar bilinçli olarak devre dışı bırakılır.

## Bildirimler

Yeniden dağıtılabilir parmak izi verileri ve üçüncü taraf bileşenleri kendi
lisanslarını korur. Kaynak, sürüm ve tam lisans metinleri
[THIRD_PARTY_LICENSES.md](../THIRD_PARTY_LICENSES.md) dosyasında listelenmiştir.
