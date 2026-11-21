# 🗺️ League of Legends Ses & Video Otomasyon Yol Haritası (ROADMAP)

Bu proje, League of Legends tescilli oyun arşivlerinden (**WAD / WPK / BNK**) ses ve replik verilerini ayıklayan, Wwise ikili hiyerarşisini çözen, sesleri oyun içi olaylara ve atıflara göre kategorize eden ve ilgili animasyonlu medya varlıklarını indiren tam kapsamlı bir otomasyon sistemidir.

> [!NOTE]
> Bu sistemde **hiçbir yapay zeka/transkripsiyon modeli (Whisper vb.) kullanılmamıştır**. Tüm sesler Riot'un resmi Wwise Event grafiği üzerinden 2 saniyede %100 deterministik olarak çözülür.

Tüm teknik mimari, tersine mühendislik çözümleri ve yol haritası [`docs/`](docs/) klasöründe modüler olarak belgelenmiştir:

---

## 📚 Dokümantasyon Dosyaları

- 📖 **[docs/00_OZET_VE_GIRIS.md](docs/00_OZET_VE_GIRIS.md)**: Proje Özeti, Klasör Yapısı ve Temel Mimarisi.
- ⚙️ **[docs/01_SES_AYIKLAMA_VE_WWISE_HIRC_COZUMU.md](docs/01_SES_AYIKLAMA_VE_WWISE_HIRC_COZUMU.md)**: Wwise HIRC SoundBank 1-Bayt Unaligned Tarayıcısı, WPK Parsing ve vgmstream çok çekirdekli dönüşüm.
- 🏷️ **[docs/02_KATEGORIZASYON_VE_EVENT_HARITALAMA.md](docs/02_KATEGORIZASYON_VE_EVENT_HARITALAMA.md)**: 11 Standart Kategori, Yüce Kral Garen'in 17 Özel Atıf Hiyerarşisi ve Doğrudan Event Haritalama Motoru.
- 🎬 **[docs/03_CANLI_DUVAR_KAGITLARI_VE_VIDEO_OTOMASYONU.md](docs/03_CANLI_DUVAR_KAGITLARI_VE_VIDEO_OTOMASYONU.md)**: MotionBGS 4K ayrıştırma, Resmi Login Screen indirme ve YouTube 403 engeli çözümü.
- 🧭 **[docs/04_GELECEK_YOL_HARITASI_VE_YENI_AI_REHBERI.md](docs/04_GELECEK_YOL_HARITASI_VE_YENI_AI_REHBERI.md)**: Gelecek AI modelleri için hızlı başlangıç rehberi ve 160+ şampiyon genişletme planı.

---

## ⚡ Hızlı Çalıştırma

```bash
# Yüce Kral Garen seslerini 2 saniyede ayıkla ve klasörle:
python scripts/godking_complete.py
```
