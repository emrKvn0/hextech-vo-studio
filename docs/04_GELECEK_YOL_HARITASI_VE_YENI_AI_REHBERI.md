# 🧭 Gelecek Yol Haritası ve Yeni AI Rehberi

Bu belge, bu projeyi devralacak **yeni yapay zeka modelleri (AI agents)** ve **yazılım geliştiriciler** için kapsamlı bir operasyonel kılavuz ve gelecek geliştirme planıdır.

---

## 🤖 Yeni AI Modelleri İçin Altın Kurallar (Quick Start)

1. **Her zaman Türkçe konuş**: Kullanıcı kuralı gereği yanıtlar ve iletişim daima Türkçe olmalıdır.
2. **Kendi terminal çıktılarını oku**: Command çıktılarını ayrı dosyaya yönlendirme (`> output.txt`), stdout/stderr üzerinden doğrudan oku.
3. **Local ile Prod ayrımı**: Proje depolarında local ve prod ortamları ayrı pushlanır.
4. **Whisper veya AI transkripsiyon modeli KULLANMA**: Ses isimlendirme ve kategorizasyonunda **asla AI transkripsiyonu kullanma**. Riot'un Wwise HIRC SoundBank Event isimleri zaten resmidir ve 2 saniyede %100 doğrulukla sınıflandırma yapar.
5. **Wwise Parser Mantığı**: Yeni bir şampiyon veya kostüm eklerken `scripts/godking_complete.py` içindeki **1-bayt unaligned tarama** algoritmasını referans al. Sabit ofset kullanma, Wwise konteynerleri dinamiktir.
6. **Gereksiz test script'i bırakma**: İşlem bittiğinde root dizinde geçici `.py` scriptleri temizle, kalıcı üretim kodlarını `scripts/` klasöründe tut.

---

## 🛠️ Temel Betiklerin Kullanımı

### 1. Şampiyonun Tüm Seslerini Çözümleme ve Kategorize Etme:
```bash
python scripts/godking_complete.py
```
- **Çıktı**: `Champions/Garen/Yüce_Kral_Garen/` altında tüm yetenek, atıf, emote ve efekt klasörleri.
- **Süre**: ~2 saniye.
- **Yöntem**: 100% Deterministik Wwise HIRC binary parsing.

### 2. Canlı Duvar Kağıtlarını ve Giriş Ekranlarını İndirme:
- 4K ve 1080p resmi canlı duvar kağıtları `C:\Users\emrKvn\Downloads\LoL Karakter Mp4leri\` klasörüne indirilir.

---

## 🗺️ Gelecek Yol Haritası (Roadmap)

### 📌 Aşama 1: 160+ Şampiyon İçin Otomatik Toplu Ayıklayıcı (Batch Extractor)
- [ ] `champions_metadata.json` dosyasındaki tüm WAD ve WPK hash'lerini otomatik indeksleyen dinamik tarayıcı.
- [ ] Tek komutla istenen şampiyon ve kostüm ID'sini parametre olarak alan genel CLI arayüzü:
  ```bash
  python scripts/extract_champion.py --champion Darius --skin 15 --lang tr_TR
  ```

### 📌 Aşama 2: Otomatik Video & Ses Birleştirme (FFmpeg Render Pipeline)
- [ ] Ayıklanan şampiyon repliklerini, ilgili şampiyonun 4K canlı duvar kağıdı üzerine bindiren otomatik video üretici.
- [ ] Ses seviyesi normalizasyonu (**EBU R128 loudness normalization**).
- [ ] Dinamik şeffaf overlay şablonu (`lol_overlay_template.png`) ile şampiyon çerçevesi yerleştirme.

### 📌 Aşama 3: Otomatik LoL Altyazı Şablonları (ASS Styling)
- [ ] Event verilerinden `.ass` / `.srt` altyazı dosyaları üretme.
- [ ] League of Legends orijinal fontlarıyla (Beaufort for LoL / Spiegel) şık altyazı animasyonları oluşturma.

### 📌 Aşama 4: Web UI / Obsidian Entegrasyonu
- [ ] Tüm replikleri, atıfları ve ses dosyalarını dinlenebilir web oynatıcısı veya Obsidian Markdown notları halinde kataloglama.
- [ ] Şampiyonlar arası etkileşim matrisi grafiği (Mermaid & D3.js).
