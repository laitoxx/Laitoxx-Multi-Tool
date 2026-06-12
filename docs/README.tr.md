# Laitoxx Multi-Tool V2.3.1

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

### ✨ Değişiklik Günlüğü (Changelog) v2.3.1
* **Küresel Wi-Fi Takibi**: Dünya çapındaki Wi-Fi yönlendiricilerini bulun. Sadece bir IP adresi veya tek bir MAC adresi aratarak tüm bir yönlendirici mahallesinin kesin koordinatlarını ortaya çıkarabilirsiniz.
* **Akıllı İnteraktif Haritalar**: Haritalar artık bir hedefin fiziksel konumunu görselleştirmeye yardımcı olmak için konutları, kafeleri, parkları ve yakındaki Wi-Fi noktalarını otomatik olarak vurguluyor.
* **Gelişmiş Meta Veri Görüntüleyici**: Görüntülerden ve belgelerden gizli meta verileri (Exif, GPS, yazar bilgisi) çıkarmak, analiz etmek ve güvenli bir şekilde silmek için güçlü bir araç eklendi.
* **Arayüz Geliştirmeleri**: Uygulamanın ağır aramalar sırasında hızlı ve duyarlı kalması için sorunsuz yükleme animasyonları ve arka plan işlemleri eklendi.
* **Çoklu Dil Desteği**: Ağ OSINT pencereleri artık tamamen çevrildi ve İngilizce, Rusça, Ukraynaca ve Türkçe arasında dinamik olarak geçiş yapıyor.
* **Performans İyileştirmeleri**: Daha istikrarlı, güvenli ve hızlı bir deneyim için devasa dahili optimizasyonlar yapıldı.
