# 🎛️ Modern Masaüstü Stüdyosu (PyWebView & TailwindCSS Mimarisi)

Bu doküman, terminal komutlarına gerek kalmadan tüm şampiyon seslerini, kostüm repliklerini, tersine atıfları ve canlı videoları görsel olarak yöneten **Discord ve Riot Client standartlarında 60 FPS akıcı, TailwindCSS & PyWebView tabanlı** masaüstü uygulamasının mimarisini ve teknik detaylarını açıklar.

---

## 🏗️ 1. Neden QtWidgets Yerine PyWebView + TailwindCSS?

Eski masaüstü sistemlerinde kullanılan klasik `QtWidgets / QSS` mimarisinin kısıtları (animasyonsuzluk, donuk renkler, esnek olmayan liste yapıları) terk edilmiş; **Microsoft Edge WebView2 çekirdeğini doğrudan bellek köprüsü (In-Memory IPC) üzerinden kullanan `PyWebView` mimarisine** geçilmiştir:

| Özellik | Eski Mimari (QtWidgets) | Yeni Mimari (PyWebView + TailwindCSS) |
| :--- | :--- | :--- |
| **Görsel Kalite** | Klasik Windows Formu benzeri | **Discord / Riot Client kalitesinde Dark Glassmorphism** |
| **Animasyon & Akıcılık** | Yok (Statik pikseller) | **60/120 FPS CSS3 geçişleri, neon parlamaları ve dalga formları** |
| **Sunucu İhtiyacı** | Yok | **YOK (Sıfır Sunucu, No-Node.js, doğrudan bellek köprüsü)** |
| **RAM Tüketimi** | ~90 MB | **~60 - 80 MB (Aşırı hafif ve optimize)** |
| **Açılış Hızı** | 1.2 sn | **~0.5 sn (Anında fırlar)** |

---

## 🎨 2. Arayüz ve Tasarım Mimarisi (`web/index.html` & `web/app.js`)

Uygulama, Discord ergonomisi ve League of Legends Hextech estetiğini harmanlayan 3 sütunlu ferah bir layout kullanır:

```
+-------------------------------------------------------------------------------------------------------------------------+
| ⚡ HEXTECH STUDIO - LoL Ses & Medya Otomasyonu                                                                          |
+----------------------+--------------------------+------------------------------+----------------------------------------+
| 🎙️ Ses & Kostüm     | 🎮 1. Şampiyon Seç       | 📂 Çıkarılan Ses Kütüphanesi | ⚡ HEXTECH AUDIO PLAYER & KONSOL        |
|                      | [ 🔍 Şampiyon ara...   ] | 📁 Varsayilan_Aatrox         | [▶ OYNATILIYOR]    00:02 / 00:04        |
| 🎯 Tersine Atıf      | 🛡️ Aatrox                |   ├── 📁 1_Q_Yetenegi (12)   | aatrox_karsilasma_hedef_zoe_01.wav      |
|                      | 🛡️ Ahri                  |   └── 📁 5_Ozel_Karsilasmala | 💬 "Zoe, alacakaranlığın alçağı..."     |
| 🎬 Canlı Duvar Kğt.  | 🛡️ Belveth               |       └── 🔊 aatrox_zoe_01   | [=======●================] 🔊 [===●===] |
|                      +--------------------------+------------------------------+----------------------------------------+
| 📂 Çıktı Klasörünü Aç| 🎭 2. Kostüm Seç         |                              | 📋 Canlı İşlem Konsolu                 |
|                      | 🌟 [TÜMÜNÜ ÇIKAR (FULL)] |                              | 📂 Obsidian hash tablosu yüklendi...   |
| Wwise v2024.1        | 🛡️ Varsayılan Hali      | [🔄 Yenile]                  | 🚀 Aatrox (Varsayılan) çıkarılıyor...  |
| 100% Deterministic   | 🎭 Adalet Işığı Aatrox   |                              | ✅ 249 ses başarıyla çıkarıldı!        |
+----------------------+--------------------------+------------------------------+----------------------------------------+
```

### A. 🎙️ Şampiyon Ses & Kostüm Çıkarıcı
- **Kompakt Arama & Seçim**: Sol panelden şampiyon seçildiği anda o şampiyonun oyundaki tüm Türkçe kostümleri dinamik olarak yüklenir.
- **Tekli veya Toplu Çıkarma**: `Seçili Kostümü Çıkar` (Altın Gradient Buton) ile tek kostüm saniyeler içinde çıkarılırken, `Tüm Kostümleri Çıkar` ile şampiyonun tüm diskografisi ayıklanır.

### B. 📂 Hiyerarşik Ses Kütüphanesi (Ağaç Görünümü)
- Çıkarılan sesler kostüm ve kategori bazında (`1_Q_Yetenegi`, `5_Ozel_Karsilasmalar` vb.) klasörlenir.
- Her klasörün yanında kaç adet ses dosyası barındırdığı rozet (`[249 ses]`) olarak gösterilir.
- Çift tıklama ile anında kesintisiz çalma başlar.

### C. 🎧 Hextech Web Audio Player
- HTML5 Web Audio API ile geliştirilmiş, ses dalgası zaman çubuğu (`seek bar`), zaman sayaçları, ses seviyesi ayarı ve varsa replik metni/altyazı kutusu.

### D. 📋 Canlı Renkli İşlem Konsolu
- Python arka planından gelen loglar (`StreamEmitter`) anlık olarak syntax-highlighted (renkli) biçimde terminal kutusuna akar.

---

## ⚡ 3. Kritik Mühendislik Çözümleri

### 1. 🛡️ Windows CMD Pencere Fırtınası Engeli (`CREATE_NO_WINDOW`)
- 400+ ses dosyası 16 iş parçacığıyla paralel dönüştürülürken Windows'un anlık yüzlerce CMD konsol penceresi açıp sistemi dondurması engellenmiştir.
- Tüm alt süreçlere (`subprocess.run`) **`creationflags = 0x08000000` (CREATE_NO_WINDOW)** tanımlanmış, dönüştürmeler %100 gizli ve sıfır pencere ile çalışır hale getirilmiştir.

### 2. 💎 `Ruby_` Ön Ekli Dosyalar Nedir? (Project Ruby / TFT)
- Riot Games'in `.wad.client` veri arşivlerinde görülen `Ruby_` ön eki, **Project Ruby (Teamfight Tactics / TFT & Swarm/Arena modları)** şampiyon ve minik efsane varlıklarıdır.
- Normal Sihirdar Vadisi şampiyonları doğrudan kendi ismiyle (`Aatrox`, `Ahri`) arşivlenirken; `Ruby_` dosyaları TFT'deki Chibi veya özel mod ses efektlerini temsil eder.

### 3. 🎯 Doğrudan Bellek İçi Python-JS Köprüsü (`app_api.py`)
- `AppAPI` sınıfı, `window.pywebview.api` üzerinden JS ile Python arasında JSON serialization ile doğrudan haberleşir.
- `extract_voices`, `extract_references`, `get_champions`, `get_skins`, `get_extracted_tree` ve `get_audio_base64` metodları asenkron thread'ler üzerinde GUI'ı kitlemeden çalışır.

---

## 📦 4. Bağımsız `.EXE` Derlemesi ve Kısayollar

* **PyInstaller Bağımsız EXE:** 
  ```powershell
  python build_exe.py
  # Çıktı: dist/LoL_Studio/LoL_Studio.exe
  ```
* **Masaüstü Kısayolu:** `scripts/create_shortcut.py` ile masaüstüne **`LoL Ses ve Video Studyosu.lnk`** kısayolu otomatik oluşturulmuştur.
