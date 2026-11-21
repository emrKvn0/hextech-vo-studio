# 🎬 Canlı Duvar Kağıtları ve Video Otomasyonu

Bu belgede, atıfta bulunulan şampiyonların 4K ve Full HD canlı animasyonlu duvar kağıtlarının (**MP4**) indirilmesi, kaynak çözümlemesi ve karşılaşılan engellerin aşılması anlatılmaktadır.

---

## 1. Hedef Dizin ve Standart İsimlendirme

Tüm videolar kullanıcının yerel indirme klasörüne kaydedilir:
- **Konum**: `C:\Users\emrKvn\Downloads\LoL Karakter Mp4leri\`
- **İsimlendirme Formatı**: `{Sira}_{Sampiyon}_{Kostum}_{Cozunurluk}.mp4`

---

## 2. MotionBGS 4K Doğrudan Medya Ayrıştırma Formülü

MotionBGS platformunda canlı duvar kağıdı sayfaları incelendiğinde doğrudan indirme URL'sinin sabit bir matematiksel kurala bağlı olduğu keşfedilmiştir:

- **Sayfa URL'si**: `https://motionbgs.com/{SLUG}`
- **Sayfa İçerisindeki Görsel**: `/media/{ID}/{SLUG}.jpg`
- **4K MP4 İndirme URL'si**: `https://motionbgs.com/media/{ID}/{SLUG}.3840x2160.mp4`
- **1080p MP4 İndirme URL'si**: `https://motionbgs.com/media/{ID}/{SLUG}.1920x1080.mp4`

### Örnek Doğrulama:
- **Yüce Kral Darius**: `https://motionbgs.com/media/5218/god-king-darius.3840x2160.mp4` (23.5 MB, 3840x2160)
- **Kan Ayı Diana**: `https://motionbgs.com/media/5214/blood-moon-diana.3840x2160.mp4` (14.6 MB, 3840x2160)
- **Tanrı Yumruk Lee Sin**: `https://motionbgs.com/media/5222/god-fist-lee-sin.3840x2160.mp4` (35.3 MB, 3840x2160)
- **Silah Tanrıçası Miss Fortune**: `https://motionbgs.com/media/5219/gun-goddess-miss-fortune.3840x2160.mp4` (28.0 MB, 3840x2160)
- **Gecegetiren Yasuo (Eski 2017)**: `https://motionbgs.com/media/4265/nightbringer-yasuo.1920x1080.mp4` (13.1 MB, 1920x1080)

---

## 3. DesktopHut Canlı Duvar Kağıdı ve Doğrudan MP4 Ayrıştırma

DesktopHut (`https://www.desktophut.com`) platformundan canlı arama ve video çekme formülü:
- **Arama URL'si**: `https://www.desktophut.com/search/{QUERY}`
- **Sayfa Slug URL'si**: `https://www.desktophut.com/{SLUG}`
- **Görsel / Poster**: `https://www.desktophut.com/images/thumb_{TIMESTAMP}_{ID}.jpg`
- **Doğrudan MP4 İndirme**: `https://desktophut.com/files/{TIMESTAMP}-{TIMESTAMP}-{slug}.mp4`

---

## 4. 🛡️ YouTube 403 Forbidden Engeli ve Android Client Çözümü

Orijinal şampiyon splash art'larının (Katarina, Elise, Evelynn, Fiora, Jax vb.) resmi Riot Games giriş ekranları (`Login Screens`) `yt-dlp` ile indirilirken YouTube'un yeni SABR video akış kısıtlaması nedeniyle `HTTP Error 403: Forbidden` hatası alındı.

### 💡 Çözüm:
`yt-dlp`'ye `--extractor-args "youtube:player_client=android"` argümanı eklenerek isteklerin mobil Android istemcisi üzerinden yapılması sağlandı. Bu sayede 403 engeli %100 aşıldı:

```python
cmd = [
    "yt-dlp",
    "--no-warnings",
    "--extractor-args", "youtube:player_client=android",
    "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
    "--merge-output-format", "mp4",
    "-o", target_path,
    f"ytsearch1:{query}"
]
```

---

## 5. Çoklu Kaynak Birleşik Arama ve İndirme Mimarisi (`scripts/wallpaper_engine.py`)

1. **Paralel Tarama (`ThreadPoolExecutor`)**:
   - `search_desktophut()`
   - `search_motionbgs()`
   - `search_youtube_wallpapers()`
2. **REST API Entegrasyonu**:
   - `GET /api/wallpapers/search?q={query}&source={all|desktophut|motionbgs|youtube}&resolution={all|4k|1080p}`
   - `POST /api/wallpapers/download` (Arka planda stream & yt-dlp indirme)
   - `GET /api/wallpapers/status` (Canlı indirme yüzdesi ve hız takibi)
   - `GET /api/wallpapers/downloaded` (Yerel indirilmiş duvar kağıtları galerisi)
   - `POST /api/wallpapers/open-folder` (İndirilenler klasörünü açma)
3. **Web GUI Özellikleri**:
   - Dahili Modal Video Oynatıcı (DesktopHut MP4, MotionBGS ve YouTube iframe önizleme).
   - Canlı indirme ilerleme çubuğu.
   - Popüler şampiyon filtreleri ve tek tıkla arama.
