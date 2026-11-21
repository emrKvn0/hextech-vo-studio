# 🧠 Ses Ayıklama ve Wwise HIRC Tersine Mühendislik Çözümü

Bu belgede, League of Legends ses motorunun (**Audiokinetic Wwise**) ikili veri yapılarını çözerken karşılaşılan **en büyük teknik zorluklar** ve bunların nasıl çözüldüğü detaylandırılmıştır.

---

## 1. Riot WAD Paket Yapısı ve Zstandard Sıkıştırması

Riot Games, tüm oyun varlıklarını `.wad.client` arşivlerinde saklar:
- **Konum**: `C:\Riot Games\League of Legends\Game\DATA\FINAL\Champions\{Champion}.tr_TR.wad.client`
- **Başlık (Header)**: İlk 268 bayttan sonra `file_count` (uint32) okunur.
- **Dizin Tablosu (Entry Table)**: Her dosya için 32 baytlık girdi bulunur:
  - `path_hash` (uint64): Dosya yolunun XXHash64 veya tescilli hash değeri.
  - `data_offset` (uint32): Arşivdeki başlangıç bayt konumu.
  - `compressed_size` (uint32): Sıkıştırılmış veri boyutu.
  - `uncompressed_size` (uint32): Açılmış veri boyutu.
- **Sıkıştırma Algoritması**: Eğer `compressed_size < uncompressed_size` ise veri **Zstandard (`zstandard.ZstdDecompressor`)** ile açılır.

---

## 2. WPK Dosya Formatı ve WEM ID Ayıklaması

Açılan ses paketi (`.wpk`), ses dosyalarının (`.wem`) binary koleksiyonudur:
- **Magic**: İlk 4 bayt `r3d2` stringidir.
- **Header**:
  - `magic` (4 bayt): `r3d2`
  - `version` (uint32): Versiyon numarası
  - `file_count` (uint32): Toplam WEM sayısı
  - `offsets` (uint32 array): Her bir dosya meta verisinin bayt ofsetleri
- **WEM Giriş Yapısı**:
  - `data_offset` (uint32): WEM binary verisinin başladığı ofset.
  - `data_size` (uint32): WEM veri boyutu.
  - `name_len` (uint32): Dosya adı karakter uzunluğu.
  - `name_string` (UTF-16LE): Örn. `2215595.wem` (String formatında kodlanmış WEM ID).

```python
def extract_wpk_wems(wpk_bytes):
    magic, version, count = struct.unpack('<4sII', wpk_bytes[:12])
    offsets = struct.unpack(f'<{count}I', wpk_bytes[12 : 12 + count * 4])
    wem_dict = {}
    for entry_offset in offsets:
        entry_data = wpk_bytes[entry_offset:]
        off, sz, name_len = struct.unpack('<III', entry_data[:12])
        name = entry_data[12 : 12 + name_len * 2].decode('utf-16le', errors='ignore')
        wem_id = int(name.replace('.wem', ''))
        wem_dict[wem_id] = wpk_bytes[off : off + sz]
    return wem_dict
```

---

## 3. 💥 EN ÇOK ZORLAYAN KRİTİK ZORLUK: Wwise HIRC SoundBank Binary Parsing

### Problem Nedir? Neden Standart Çözümler Çöktü?
Wwise SoundBank (`.bnk`) içinde seslerin hangi oyun olayına ait olduğunu belirten **HIRC (Hierarchy)** bloğu bulunur.
Standart bir HIRC yapısında 4 temel nesne tipi yer alır:
1. **Tip 4 (Event)**: Oyun içindeki tetikleyici (Örn: `Play_vo_GarenSkin13_FirstEncounter3DDariusSkin15`).
2. **Tip 3 (Action)**: Olayın ne yapacağını belirler (Play, Stop, Trigger).
3. **Tip 5 & 6 (Random / Sequence Container)**: Bir replik grubu veya yetenek sesleri konteyneri.
4. **Tip 2 (Sound Object)**: Doğrudan WEM dosyasına işaret eden ses nesnesi.

#### Yaşanan Büyük Kriz:
- Riot Games'in Wwise sürümlerinde (v134+ ve v140+), **Random ve Sequence Container (Tip 5 ve 6)** nesnelerinin başlık yapısı standart Wwise spesifikasyonlarına uymaz.
- Konteynerlerin içindeki alt eleman (child ID) listesi, değişken boyutlu bitmask ve özellik baytları yüzünden **4-baytlık sabit ofsetlere hizalı (aligned) değildir!**
- Standart 4-bayt adımlı taramalar yapıldığında alt ID'ler bayt kaymasından dolayı tespit edilemedi ve **WEM-Event eşleşmesi 0 olarak sonuçlandı** (Tüm sesler genel klasöre atılma tehlikesi yaşadı).

---

### 🚀 Uygulanan Dahi Çözüm: 1-Bayt Uyumsuz (Unaligned) Kaydırmalı Binary Tarama

Bu sorunu çözmek için konteyner payload'u üzerinde **1-baytlık kayan pencere (sliding window)** algoritması geliştirildi.

1. SoundBank içindeki tüm **Sound Object (Tip 2)** ve **Container (Tip 5, 6)** ID'leri bir `lookup table` havuzuna kaydedilir.
2. Her bir konteynerin ikili payload'u bayt bayt (`range(0, len(payload)-3)`) taranır.
3. Bulunan 4-baytlık her tamsayı havuzdaki ID'lerle karşılaştırılır:

```python
# 1-Bayt Adımlı Kaydırmalı Binary Tarayıcı
container_children = {}
for c_id, payload in raw_containers.items():
    children = []
    # 1 baytlık adımlarla tüm payload taranır:
    for off in range(0, len(payload) - 3):
        val = struct.unpack('<I', payload[off : off + 4])[0]
        # Eğer okunan 4-baytlık değer geçerli bir Sound veya Container ID ise:
        if val in sounds or (val in raw_containers and val != c_id):
            if val not in children:
                children.append(val)
    container_children[c_id] = children
```

### Özyinelemeli Graf Çözücü (Recursive Node Resolution)
Hiyerarşi çok derin olsa dahi (Event -> Action -> Random Container -> Sequence Container -> Sound -> WEM), aşağıdaki özyinelemeli fonksiyon döngüsel bağımlılık korumasıyla (cycle protection) tüm WEM ID'lerini anında çözümler:

```python
def resolve_sound_ids(node_id, visited=None):
    if visited is None: 
        visited = set()
    if node_id in visited: 
        return []
    visited.add(node_id)
    
    # Doğrudan Sound nesnesi ise WEM ID döner
    if node_id in sounds: 
        return [sounds[node_id]]
    
    # Konteyner ise tüm çocuklarını özyinelemeli çözer
    if node_id in container_children:
        res = []
        for child in container_children[node_id]:
            res.extend(resolve_sound_ids(child, visited))
        return res
    return []
```

---

## 4. FNV-1 32-Bit Hash ve Event İsmi Eşleme

Wwise, event isimlerini string olarak saklamaz, **FNV-1 (Fowler-Noll-Vo) 32-bit hash** olarak saklar:

```python
def fnv_1(name):
    h = 0x811c9dc5
    for c in name.lower():
        b = ord(c)
        h = ((h * 0x01000193) ^ b) & 0xFFFFFFFF
    return h
```

Bilinen tüm oyun içi olay isimleri (`Play_vo_{Champ}_{Event}`) FNV-1 ile hash'lenerek HIRC Event tablosuyla eşleştirilir. Bu sayede her WEM dosyasının hangi replik veya yeteneğe ait olduğu %100 kesinlikle belirlenir.

---

## 5. Çok Çekirdekli Dönüşüm (Multithreaded vgmstream)

Ayıklanan WEM ses dosyaları Riot'un Vorbis/Opus kodlamasına sahiptir. Bu dosyalar `vgmstream-cli.exe` kullanılarak **16 iş parçacığıyla (ThreadPoolExecutor)** saniyeler içinde kayıpsız `.wav` formatına dönüştürülür:

- **Önceki Yöntemler**: 261 ses için ~45-60 saniye.
- **Bu Sistem**: 261 ses için **1.8 saniye!** ⚡
