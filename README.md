# 🎮 Hextech VO Studio — LoL Ses, Replik & Medya Stüdyosu

Bu proje, League of Legends şampiyonlarının yerel oyun ses dosyalarını (`WAD`/`WPK`/`BNK`), replik metinlerini (League Wiki & SkinSpotlights CC), AI ses algılama (`faster-whisper`) ve kurgu araçlarını (DaVinci Resolve FCPXML vb.) birleştiren modüler bir stüdyo sistemidir.

---

## 🛠️ Kurulum ve Tam Performans Gereksinimleri

Repoyu klonladıktan sonra geliştirici ortamıyla birebir aynı sonuç ve performansı alabilmek için aşağıdaki adımları uygulayın:

### 1. Python Bağımlılıkları (Python 3.10+)
```bash
pip install -r requirements.txt
```

### 2. AI Replik Dedektörü (`faster-whisper` & CUDA)
Video/ses içindeki replikleri otomatik tespit ve deşifre etmek için `faster-whisper` kullanılır (`turbo` modeli):
```bash
pip install faster-whisper
```
- **GPU (Önerilen):** NVIDIA GPU ve CUDA kuruluysa sistem otomatik olarak `float16` hassasiyetinde donanım hızlandırmayı seçer.
- **CPU:** CUDA bulunamazsa otomatik olarak `int8` moduna düşer. İlk çalıştırmada `turbo` modeli HuggingFace üzerinden otomatik indirilir.

### 3. Harici Araçlar (`vgmstream` & `ffmpeg`)
- **`vgmstream-cli.exe`:** `.wem` ses dosyalarını `.wav`/`.ogg` formatına çevirmek için gereklidir. Resmi [vgmstream](https://github.com/vgmstream/vgmstream/releases) sürümünü indirip proje kökündeki `vgmstream/` klasörünün içine (`vgmstream/vgmstream-cli.exe`) yerleştirin.
- **`ffmpeg`:** Ses/video işleme ve kesit alma işlemleri için sistem `PATH`'inizde kurulu olmalıdır.

### 4. Başlatma
- **Masaüstü Stüdyosu (PyWebView):** `python main_gui.py` veya `launchers/LoL_Studio_Baslat.bat`
- **LoL Matrix Web (React + Vite, Node.js 18+):**
  ```bash
  cd lol-matrix-web
  npm install
  npm run dev
  ```
  *(veya ses sunucusuyla birlikte `launchers/LoL_Matrix_Web_Baslat.bat`)*
- **LoLdle TR Sunucusu:** `python loldle_server.py` veya `launchers/LoLdle_Baslat.bat`

---

## 🚀 CLI Kullanımı (`vo_pipeline.py`)

Tek bir komutla şampiyon replik metinlerini wiki'den çekebilir, Türkçeye çevirebilir ve yerel ses dosyalarıyla eşleştirebilirsiniz:

```bash
# Sett Classic replikleri
python vo_pipeline.py --champion Sett --skin "Classic"

# Sett Radiant Serpent replikleri
python vo_pipeline.py --champion Sett --skin "Radiant Serpent"

# Diana Eternal Aspect replikleri
python vo_pipeline.py --champion Diana --skin "Eternal Aspect Diana"

# Aatrox Primordian replikleri (yerel ses eşleştirmeli)
python vo_pipeline.py --champion Aatrox --skin "Primordian Aatrox"

# Şampiyonun mevcut wiki sekmelerini listeleme
python vo_pipeline.py --champion Sett --check-tabs
```

---

## 🌐 REST API Uç Noktaları

Backend sunucusu (`server_backend.py`) üzerinden şu endpoint'ler kullanılabilir:

- `GET /api/quotes?champion=Sett&skin=Classic`: Şampiyonun kaydedilmiş replik listesini döner.
- `GET /api/quotes/tabs?champion=Sett`: Şampiyonun wiki'deki sekme ve bölüm isimlerini döner.
- `POST /api/quotes/sync`: İlgili şampiyon ve kostüm için arka planda çekme ve eşleştirme hattını çalıştırır.

---

## ⚖️ Hukuki Bildirim & Lisans (Legal Notice & Licensing)

1. **Riot Games Legal Jibber Jabber Bildirimi:**
   - *Hextech VO Studio* isn't endorsed by Riot Games and doesn't reflect the views or opinions of Riot Games or anyone officially involved in producing or managing Riot Games properties. Riot Games, and all associated properties are trademarks or registered trademarks of Riot Games, Inc.
   - Bu repo içerisinde telif hakkına sahip oyun içi ses dosyaları (`.wem`, `.wav`, `.ogg`) barındırılmaz ve dağıtılmaz; araç yalnızca kullanıcının kendi bilgisayarındaki kurulu dosyaları işlemesine yardımcı olur.

2. **League of Legends Wiki Alıntıları (`CC BY-SA 4.0`):**
   - `data/wiki_quotes/` altındaki replik metinleri ve tetikleyici başlıkları **Creative Commons Attribution-ShareAlike 4.0 (CC BY-SA 4.0)** lisansına tabidir.
   - Veri kaynağı: [https://wiki.leagueoflegends.com/](https://wiki.leagueoflegends.com/)

3. **YouTube SkinSpotlights Altyazıları (CC):**
   - SkinSpotlights kanalından çekilen altyazılar yalnızca wiki'de replik bulunmadığı durumlarda yedek referans olarak kullanılır. Altyazı telifleri ilgili içerik üreticisine aittir; ticari olarak kullanılamaz.

4. **Kaynak Kod Lisansı:**
   - Yukarıdaki üçüncü taraf veri setleri hariç olmak üzere, bu depodaki özgün yazılım kaynak kodları **MIT Lisansı** ile sunulmaktadır.
