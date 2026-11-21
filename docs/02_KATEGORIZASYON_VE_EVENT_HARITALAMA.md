# 🎯 Kategorizasyon, Olay Haritalama ve Tersine Atıf Mimarisi

Bu doküman, Riot Games'in Wwise HIRC Event grafiğinden çıkarılan seslerin hangi oyun içi eylemde (Olay/Tetikleyici) çaldığının nasıl tespit edildiğini, dosya isimlendirme kurallarını ve **Hedef Şampiyon Tersine Atıf Dedektörü**'nün çalışma prensibini açıklar.

---

## 🏷️ 1. Olay ve Eylem Bazlı İsimlendirme Kuralları (`event_categorizer.py`)

Riot Games'in Wwise olayları (`Play_vo_PykeSkin45_Kill3DZed`, `Play_vo_Pyke_Move2D`, `Play_vo_Pyke_TurretDestroy3D` vb.) regex ve kural tabanlı motorumuz tarafından kristal netliğinde Türkçe dosya adlarına dönüştürülür:

### ⚔️ Hedef Şampiyon Etkileşimleri:
* `kill` / `firstblood` ➔ `{sampiyon}_katletme_hedef_{hedef}` *(Örn: `pyke_katletme_hedef_zed_01.wav`)*
* `firstencounter` / `encounter` ➔ `{sampiyon}_karsilasma_hedef_{hedef}` *(Örn: `pyke_karsilasma_hedef_lux_01.wav`)*
* `ally` ➔ `{sampiyon}_dost_karsilasma_hedef_{hedef}`
* `enemy` ➔ `{sampiyon}_dusman_karsilasma_hedef_{hedef}`
* `taunt` ➔ `{sampiyon}_kiskirtma_hedef_{hedef}` *(Örn: `pyke_kiskirtma_hedef_gangplank_01.wav`)*
* `joke` ➔ `{sampiyon}_saka_hedef_{hedef}` *(Örn: `pyke_saka_hedef_ezreal_01.wav`)*
* `spell` / `cast` / `hit` ➔ `{sampiyon}_yetenek_vurusu_hedef_{hedef}`

### 🎮 Genel Oyun İçi Olaylar:
* `intro` / `gamestart` / `matchstart` ➔ `{sampiyon}_oyun_basi_dogus_01.wav`
* `respawn` / `revive` ➔ `{sampiyon}_yeniden_canlanma_01.wav`
* `recall` ➔ `{sampiyon}_usse_donus_01.wav`
* `death` / `die` ➔ `{sampiyon}_olum_01.wav`
* `penta` ➔ `{sampiyon}_pentakill_01.wav`
* `firstblood` ➔ `{sampiyon}_ilk_kan_katletme_01.wav`
* `turret` / `tower` ➔ `{sampiyon}_kule_yikma_01.wav`
* `dragon` / `baron` ➔ `{sampiyon}_epik_canavar_kesme_01.wav`
* `item` / `shop` ➔ `{sampiyon}_esya_alimi_01.wav`
* `move` ➔ `{sampiyon}_hareket_yurume_01.wav`
* `attack` ➔ `{sampiyon}_normal_saldiri_01.wav`
* `spell_q` / `spell_w` / `spell_e` / `spell_r` ➔ `{sampiyon}_q/w/e/r_yetenek_01.wav`

---

## 🎯 2. Hedef Şampiyon Tersine Atıf Dedektörü (`extract_target_references.py`)

Garen veya herhangi bir hedef şampiyon seçildiğinde, sistem oyundaki tüm 170+ şampiyonun WAD arşivlerini 16 iş parçacığıyla tarar ve hedefe söylenen tüm replikleri çıkarır.

### 🌳 Hiyerarşik Klasörleme Yapısı:
```text
Garene_Yapilan_Tum_Ozel_Atiflar/
├── Varsayilan_Garene_Yapilan_Atiflar/
│   ├── Aatrox/
│   │   ├── Varsayilan_Hali/ (2 adet)
│   │   ├── Adalet_Işığı_Aatrox/ (2 adet)
│   │   ├── Kara_Ay_Aatrox/ (2 adet)
│   │   ├── Meka_Aatrox/ (2 adet)
│   │   └── Uzay_Serüveni_Aatrox/ (2 adet)
│   ├── Darius/
│   │   └── Potanın_Kralı_Darius/ (1 adet)
│   ├── Sylas/
│   │   ├── Varsayilan_Hali/ (7 adet)
│   │   ├── KOD_ADI_Sylas/ (4 adet)
│   │   ├── Kül_Katili_Sylas/ (4 adet)
│   │   └── Sonsuz_Karanlık_Sylas/ (1 adet)
│   └── Lux/, Poppy/, Camille/, Xin Zhao/... (35 Şampiyon Klasörü)
│
├── Yüce_Kral_Garene_Yapilan_Atiflar/
│   ├── Darius/
│   │   ├── Yüce_Kral_Darius/ (1 adet)
│   │   └── Kutlu_Yüce_Kral_Darius/ (13 adet)
│   ├── Yone/ ── Şafağın_Ruhu_Yone/ (2 adet)
│   └── Soraka/ ─ Şafağın_Ruhu_Soraka/ (2 adet)
│
├── Meka_Krallıkları_Garene_Yapilan_Atiflar/
├── Savaş_Akademisi_Garene_Yapilan_Atiflar/
└── Efsanebaz_Garene_Yapilan_Atiflar/
```

### ⚡ Mükerrer Ses Eleme (Audio MD5 Hash Deduplication):
Epik kostümler (1350 RP) şampiyonun varsayılan sesini paylaşır. Bir şampiyonun 6 kostümü aynı ses dosyasını içeriyorsa, ses verisinin MD5 hash'i taranarak o replik yalnızca 1 defa çıkarılır; klasörlerde gereksiz dosya kirliliği oluşması %100 engellenir.
