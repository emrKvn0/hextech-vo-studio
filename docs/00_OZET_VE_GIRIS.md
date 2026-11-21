# 🎙️ League of Legends Ses & Medya Otomasyon Sistemi

Bu dokümantasyon, League of Legends'ın tescilli oyun paketlerinden (**WAD, WPK, BNK**) ses verilerini sıfır kayıpla ayıklayan, Wwise ses motorunun ikili grafiğini tersine mühendislikle çözen, sesleri doğrudan oyun içi olaylara (**Event**) ve şampiyon atıflarına göre kategorize eden, kostümleri akıllı ses türlerine göre sınıflandıran (Özgün Yeni Dublaj / Vokal Efektli / Standart), ilgili animasyonlu splash/video içeriklerini indiren ve tüm bunları modern bir **Masaüstü Kontrol Paneli (GUI)** ile yöneten sistemin teknik mimarisini açıklar.

> [!NOTE]
> **Önemli Not:** Bu sistemde temel ses sınıflandırması ve isimlendirmesi için harici yapay zeka yerine Riot Games'in ikili SoundBank dosyalarındaki resmi Event hiyerarşisi üzerinden %100 deterministik algoritmalar kullanılır (0.02 saniyede çözülür). İsteğe bağlı olarak videolara altyazı ve kelime kelime yanan karaoke animasyonu eklemek için yerleşik Faster-Whisper Türkçe Speech-to-Text motoru desteklenmektedir.

---

## 📂 Dokümantasyon İndeksi

1. **[01. Ses Ayıklama ve Wwise HIRC Çözümü](01_SES_AYIKLAMA_VE_WWISE_HIRC_COZUMU.md)**
   - *Riot WAD paketlerinin açılması (Zstandard sıkıştırması).*
   - *WPK başlığı ve UTF-16LE WEM ID ayıklaması.*
   - *Wwise HIRC SoundBank unaligned 1-byte binary taraması ve hiyerarşik çözücü.*
   - *vgmstream ile 16-thread çok çekirdekli WAV dönüşümü.*
2. **[02. Kategorizasyon, Event Haritalama ve Akıllı Ses Türleri](02_KATEGORIZASYON_VE_EVENT_HARITALAMA.md)**
   - *Resmi Wwise Event isimlerinden doğrudan oyun mekaniği bazlı (Q, W, E, R, Katletme, Karşılaşma, Kule Yıkma, Doğuş vb.) Türkçe isimlendirme.*
   - *Akıllı Ses Türü Sınıflandırması: 👑 Özgün Yeni Dublaj, 🎛️ Vokal Filtreli / Klon Dublaj, 🎮 Standart Ses.*
   - *2.146 Kostümün Resmi Türkçe Nadirlik Standartları (Destansı, Efsanevi, İhtişamlı, Ebedi).*
   - *Hedef Şampiyon Tersine Atıf Dedektörü (170+ şampiyonu tarama ve Şampiyon/Kostüm bazlı hiyerarşi).*
3. **[03. Canlı Duvar Kağıtları ve Video Otomasyonu](03_CANLI_DUVAR_KAGITLARI_VE_VIDEO_OTOMASYONU.md)**
   - *MotionBGS 4K / HD MP4 ayrıştırma formülü.*
   - *Resmi Riot Games giriş ekranlarının (Login Screens) otomatik indirilmesi.*
   - *YouTube 403 Forbidden throttling sorununu aşma (Android Client tekniği).*
4. **[04. Gelecek Yol Haritası ve Operasyonel Rehber](04_GELECEK_YOL_HARITASI_VE_YENI_AI_REHBERI.md)**
   - *Yeni bir geliştiricinin projeyi tek komutla veya GUI ile çalıştırma adımları.*
   - *Masaüstü kısayolları ve video kurgu pipeline planı.*
5. **[05. Modern Masaüstü Stüdyosu (PyWebView & TailwindCSS)](05_MASAUSTU_GUI_VE_OTOMASYON_STUDYOSU.md)**
   - *PyWebView + Yerleşik Python HTTP & Server-Sent Events (SSE) sunucu mimarisi.*
   - *Riot Client Tarzı 3 Sütunlu Düzen: Sol Tam Boy Şampiyon Listesi + Orta Yatay Kostüm Şeridi (Carousel) + Sağ Hextech Oynatıcı & Sıralı Çalma Kuyruğu.*
   - *Toplu Seçim & Otomatik Sıralı Çalma (Sequential Playlist Queue).*
   - *CREATE_NO_WINDOW bayrağı ile sıfır konsol penceresi ve arka plan sessiz dönüşümü.*
   - *Ruby_ (Project Ruby / TFT & Özel Modlar) analizi.*

---

## 🏗️ Proje Dizin Yapısı

```
lol-ses-veriler/
├── Champions/                           # İşlenmiş ve kategorize edilmiş şampiyon sesleri
│   ├── Garen/
│   │   ├── Garene_Yapilan_Tum_Ozel_Atiflar/ # Tersine atıf dedektörü arşivi
│   │   ├── Yüce_Kral_Garen/            # 261 replik (Özgün Yeni Dublaj)
│   │   ├── Düşmüşlerin_Kehaneti_Garen/ # 71 replik (Vokal Filtreli)
│   │   └── Varsayilan_Garen/           # 71 replik (Standart)
│   ├── Aatrox/
│   └── Ezreal/
├── web/                                 # Modern TailwindCSS & HTML5 Arayüz Dosyaları
│   ├── index.html                       # 3 Sütunlu Riot Client Yatay Kostüm Şeridi & Hextech UI
│   ├── app.js                           # Durum yönetimi, Playlist Queue, Sıralı Oynatma & SSE
│   └── skins_dates.js                   # Kronolojik kostüm çıkış tarihleri önbelleği
├── server_backend.py                    # Yerleşik Python HTTP & Server-Sent Events (SSE) REST sunucusu
├── main_gui.py                          # PyWebView masaüstü pencere başlatıcısı
├── build_exe.py                         # PyInstaller bağımsız .EXE derleme otomasyonu
├── scripts/                             # Çekirdek Python tersine mühendislik ve otomasyon betikleri
│   ├── lol_voice_extractor_expert.py    # Şampiyon & Kostüm ses çıkarıcı ve Wwise VO analiz motoru
│   ├── extract_target_references.py     # Tersine hedef atıf dedektörü
│   ├── event_categorizer.py             # Olay ve eylem bazlı isimlendirme kuralları
│   ├── metadata_manager.py              # Kostüm veritabanı, ses türleri & hash yöneticisi
│   ├── download_live_wallpapers.py      # 4K canlı duvar kağıtları indirici
│   ├── create_shortcut.py               # Masaüstü .EXE kısayol oluşturucu
│   └── export_all_skins.py              # 2.146 kostümün Türkçe veritabanı oluşturucusu
├── all_lol_skins_database.json          # 2.146 kostümün Türkçe ve nadirlik standart veritabanı
├── LoL_Studio_Baslat.bat                # Hızlı çift tıklamalık masaüstü başlatıcı
├── vgmstream/                           # Riot WEM -> WAV dönüştürücü motor (vgmstream-cli.exe)
└── docs/                                # Kapsamlı sistem dokümantasyonu
```�z masaüstü uygulaması
├── all_lol_skins_database.json          # 2.146 kostümün Türkçe veritabanı
├── main_gui.py                          # GUI başlatıcı
├── LoL_Studio_Baslat.bat                # Hızlı çift tıklamalık başlatıcı
├── vgmstream/                           # Riot WEM -> WAV dönüştürücü motor
└── docs/                                # Kapsamlı sistem dokümantasyonu
```
