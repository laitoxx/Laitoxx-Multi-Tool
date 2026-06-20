# Laitoxx Multi-Tool V2.3.2

[English](../README.md) | [Русский](README.ru.md) | [Українська](README.uk.md) | [Türkçe](README.tr.md)

<img src="../screenshot.png" alt="Laitoxx banner" width="100%"/>

---

Laitoxx, modern ve kullanıcı dostu bir Grafik Kullanıcı Arayüzüne (GUI) sahip güçlü bir OSINT (Açık Kaynak İstihbaratı) ve siber güvenlik aracıdır. Eğitim ve araştırma amacıyla tasarlanmıştır.

⚠ **Feragatname**: Bu araç yalnızca eğitim amacıyla oluşturulmuştur. Geliştiriciler, bu yazılımın kötüye kullanımından sorumlu değildir.

### 🔌 Eklenti Geliştirme (Lua)
Laitoxx, Lua tabanlı bir eklenti sistemi aracılığıyla genişletilebilirliği destekler. 
Kılavuz: 👉 [Eklenti Geliştirme Kılavuzu (Türkçe)](pluginBuilding.tr.md)

### 🔹 Özellikler
* **Modern Arayüz (GUI)**
* **Lua Eklentileri ile Genişletilebilirlik**
* **Akıllı Palet Üreticili Gelismis Tema Editoru**
* **Özelleştirilebilir Temalar**
* **Grafik Düzenleyici (İlişki Görselleştirme)**
* **SOCKS5 Proxy Desteği**
* **Performans Modu**

#### OSINT Araçları:
* Küresel Wi-Fi ve MAC Takibi
* Gelişmiş Meta Veri Görüntüleyici ve Adli Bilişim
* Telefon numarası sorgulama
* IP izleme ve tarama (interaktif haritalarla)
* E-posta OSINT ve doğrulama
* Telegram OSINT
* Kullanıcı adı arama ve Nickname oluşturma (500+ site)
* Görsel Tabanlı Arama
* Google OSINT (Gelişmiş dorklar)
* Yerel Veritabanı araması
* Web-crawler (Web Tarayıcı)
* Web Sitesi Bilgileri (Whois vb.)

#### Web ve Ağ Araçları:
* Port tarayıcı (Nmap tabanlı)
* Nmap Tarayıcı
* Alt alan adı bulucu (Subdomain finder)
* CMS Dedektörü
* Teknoloji Tespiti (WAF, CDN vb.)
* Web güvenlik araçları (SSL, CORS, Open Redirect, HTTP inceleme, JWT analizatörü)
* CIDR Aralık Hesaplayıcı
* REGEX Test Aracı

#### Yardımcı Programlar:
* Hash Araçları (Metin Hashleme, Hash Tanımlayıcı, Rainbow Table)
* Metin Dönüştürücü (Kodlama/çözme: Leet, Morse, Base64, Hex, ROT-13 vb.)
* Parola Oluşturucu

### 🚀 Kurulum ve Kullanım

Laitoxx, tüm önemli işletim sistemleri için otomatik kurulum komut dosyaları (script) sunar. Aracı Git kullanarak veya bir ZIP arşivi indirerek indirebilirsiniz.

#### 🔽 Seçenek 1: Git ile (Önerilen)
1. **Depoyu klonlayın:**
   ```sh
   git clone https://github.com/Laitoxx/Laitoxx-Multi-Tool.git
   cd Laitoxx-Multi-Tool
   ```

#### 🔽 Seçenek 2: Git olmadan
1. Depoyu GitHub'dan bir ZIP dosyası olarak indirin (**Code** -> **Download ZIP**'e tıklayın).
2. ZIP arşivini çıkartın ve açılan klasörde (`Laitoxx-Multi-Tool-main`) bir terminal açın.

---

#### 🐧 Ubuntu/Debian (Linux)
Otomatik kurulum komut dosyasını çalıştırın:
```sh
chmod +x install.sh
./install.sh
```
*Daha sonra çalıştırmak için şunu kullanın: `python3 start.py`*

#### 🍎 MacOS
Otomatik kurulum komut dosyasını çalıştırın:
```sh
chmod +x install.sh
./install.sh
```
*Daha sonra çalıştırmak için şunu kullanın: `python3 start.py`*

#### 🪟 Windows
`install.bat` dosyasına çift tıklayın veya komut satırı (CMD) aracılığıyla çalıştırın:
```cmd
install.bat
```
*Daha sonra çalıştırmak için şunu kullanın: `python start.py`*

### ✨ Degisiklik Gunlugu (Changelog) v2.3.2
* **Tema Editoru Yeniden Tasarlandi**: Renk tema editoru tamamen yeniden yapildi. Artik akilli palet ureteci (tamamlayici, triadik ve analoglu semalar), goruntuden palet cikarma, canli onizleme paneli, renk korlugu simulasyonu (deuteranopi, protanopi, tritanopi), WCAG kontrast otomatik duzeltme, ekrandan renk damlaligi, renk kopyalama/yapistirma, tema tersine cevirme, global kose yuvarlakligi kaydirici ve favori ve arama ozellikleriyle tam tema kutuphanesi sunmaktadir.
* **Gunduz/Gece Otomatik Tema Zamanlama**: Ayarlara, belirli saatlerde gunduz ve gece temalari arasinda otomatik gecis yapan bir zamanlama sistemi eklendi.
* **Tema Olusturma Dugmesi Geri Getirildi**: Kenar cubugundaki "Renk Temasi Olustur" dugmesi eksikti ve geri getirildi.
* **Hata Duzeltme - Kullanici Adi Arama**: Profil sayfasinda beklenen meta veriler bulunmadiginda islenmeyen `NoneType` hatasina neden olan Telegram kullanici adi aramasindaki cokme duzeltildi.
* **Hata Duzeltme - Pencere Basliklari**: Gorev cubugunda terminal penceresinin "python" olarak goruntulenmesi dahil, uygulamadaki yanlis pencere basliklari duzeltildi.
* **Hata Duzeltme - Arayuz Metinleri**: Iletisim kutularinda ve arac panellerinde cok sayida tutarsiz etiket, ayirici ve aciklama duzeltildi.

### ✨ Degisiklik Gunlugu (Changelog) v2.3.1
* **Kuresel Wi-Fi Takibi**: Dunya genelindeki Wi-Fi yonlendiricilerini bulun. Sadece bir IP adresi veya tek bir MAC adresi aratarak tum bir yonlendirici mahallesinin kesin koordinatlarini ortaya cikarmak artik mumkun.
* **Akilli Interaktif Haritalar**: Haritalar artik bir hedefin fiziksel konumunu gorselleştirmek icin konutlari, kafeleri, parklari ve yakindaki Wi-Fi noktalarini otomatik olarak vurguluyor.
* **Gelismis Meta Veri Goruntuleyici**: Goruntülerden ve belgelerden gizli meta verileri (Exif, GPS, yazar bilgisi) cikarmak, analiz etmek ve guvenli bir sekilde silmek icin guclu bir arac eklendi.
* **Arayuz Gelistirmeleri**: Uygulamanin agir aramalar sirasinda hizli ve duyarli kalmasi icin sorunsuz yukleme animasyonlari ve arka plan islemleri eklendi.
* **Coklu Dil Destegi**: Ag OSINT pencereleri artik tamamen cevrildi ve Ingilizce, Rusca, Ukraynaca ve Turkce arasinda dinamik olarak gecis yapiyor.
* **Performans Iyilestirmeleri**: Daha istikrarli, guvenli ve hizli bir deneyim icin devasa dahili optimizasyonlar yapildi.
