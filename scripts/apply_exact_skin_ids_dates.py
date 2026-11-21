import urllib.request
import json
import re
import os
import sys

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
db_path = os.path.join(ROOT_DIR, "all_lol_skins_database.json")
out_js = os.path.join(ROOT_DIR, "web", "skins_dates.js")

headers = {'User-Agent': 'Mozilla/5.0'}

print("1. Fetching CDragon tr_TR skins.json...")
url_tr = "https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/tr_tr/v1/skins.json"
req_tr = urllib.request.Request(url_tr, headers=headers)
with urllib.request.urlopen(req_tr, timeout=20) as r:
    skins_tr = json.load(r)

print("2. Fetching CDragon en_US skins.json...")
url_en = "https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/skins.json"
req_en = urllib.request.Request(url_en, headers=headers)
with urllib.request.urlopen(req_en, timeout=20) as r:
    skins_en = json.load(r)

en_to_id = {}
for sid_str, s in skins_en.items():
    en_name = s.get('name', '').strip()
    if en_name:
        en_to_id[en_name.lower()] = int(sid_str)

with open(db_path, "r", encoding="utf-8") as f:
    db = json.load(f)

# Master official release dates table by exact Skin ID
OFFICIAL_DATES_BY_ID = {
    # 2026
    21069: "2026-07-15",   # MVP T1 Miss Fortune
    161029: "2026-05-28",  # Spagetti Vel'Koz (Spaghetti alla Vel'Koz)
    89064: "2026-05-28",   # Sonsuzluğun Sureti Leona (Eternal Aspect Leona)
    131076: "2026-05-28",  # Sonsuzluğun Sureti Diana (Eternal Aspect Diana)
    67067: "2026-04-29",   # İblisin Laneti Vayne (Demoncursed Vayne)
    876046: "2026-02-19",  # İlkbahar Yaprakları Lillia (Petals of Spring Lillia)
    3040: "2026-01-22",    # Koruma Ünitesi Galio (Aegis Frame Galio)

    # 2025
    221040: "2025-12-03",  # Kış Mucizesi Zeri (Winter Wonder Zeri)
    122067: "2025-11-05",  # Meka Krallıkları Darius (Mecha Kingdoms Darius)
    103088: "2025-07-30",  # Ruh Çiçeği Kaplıcası Ahri (Spirit Blossom Springs Ahri)
    17054: "2025-07-30",   # Ruh Çiçeği Kaplıcası Teemo (Spirit Blossom Springs Teemo)
    875067: "2025-07-30",  # Ruh Çiçeği Kaplıcası Sett (Spirit Blossom Springs Sett)
    43070: "2025-06-25",   # Ruh Çiçeği Karma (Spirit Blossom Karma)
    22076: "2025-04-30",   # Ruh Çiçeği Ashe (Spirit Blossom Ashe)
    39055: "2025-04-30",   # Ruh Çiçeği Irelia (Spirit Blossom Irelia)
    35064: "2025-04-02",   # Kedi Kutusu Shaco (Cat-in-the-Box Shaco)
    498057: "2025-03-19",  # Savaş Akademisi Xayah (Battle Academia Xayah)
    497047: "2025-03-19",  # Savaş Akademisi Rakan (Battle Academia Rakan)
    202047: "2025-01-23",  # Efsanebaz Jhin (Mythmaker Jhin)

    # 2024
    112024: "2024-12-11",  # Arcane: Kurtarıcı Viktor (Arcane Savior Viktor)
    254048: "2024-11-20",  # Arcane: Dövüşçü Vi (Arcane Brawler Vi)
    126035: "2024-11-20",  # Arcane: Felaketzede Jayce (Arcane Survivor Jayce)
    799001: "2024-11-06",  # Kurt'un Seçilmişi Ambessa (Chosen of the Wolf Ambessa)
    517046: "2024-10-23",  # Sonsuz Karanlık Sylas (Dark Star Sylas)
    45060: "2024-09-25",   # Dehşet Gecesi Veigar (Fright Night Veigar)
    266033: "2024-07-31",  # Primordia'lı Aatrox (Primordian Aatrox)
    147043: "2024-07-17",  # Savaş Güvercini Seraphine (Battle Dove Seraphine)
    110053: "2024-05-01",  # Arş Hükümdarı Varus (Empyrean Varus)
    777055: "2024-03-20",  # Vahşi Batılı Yone (High Noon Yone)
    136031: "2024-02-22",  # Porselen Muhafız Aurelion Sol (Porcelain Protector Aurelion Sol)
    64051: "2024-02-07"    # Semavipullu Lee Sin (Heavenscale Lee Sin)
}

# Auto-detect year from CDragon chromas for all other skins
chroma_year_count = 0
for sid_str, s in skins_tr.items():
    sid = int(sid_str)
    if sid in OFFICIAL_DATES_BY_ID:
        continue
    # Check chroma descriptions for "YYYY yılında"
    for ch in s.get('chromas', []):
        for desc_obj in ch.get('descriptions', []):
            desc_text = desc_obj.get('description', '')
            m = re.search(r'(\d{4})\s*yılında', desc_text)
            if m:
                year = m.group(1)
                OFFICIAL_DATES_BY_ID[sid] = f"{year}-06-01"
                chroma_year_count += 1
                break
        if sid in OFFICIAL_DATES_BY_ID:
            break

print(f"Chroma açıklamalarından tespit edilen ek tarih sayısı: {chroma_year_count}")

# Update database
db_map = {s.get('skin_id'): s for s in db if 'skin_id' in s}

for sid, rel_date in OFFICIAL_DATES_BY_ID.items():
    if sid in db_map:
        db_map[sid]['release_date'] = rel_date
    else:
        # Create skin entry if missing in db
        tr_info = skins_tr.get(str(sid), {})
        champ_id = sid // 1000
        skin_num = sid % 1000
        new_skin = {
            "skin_id": sid,
            "champion_id": champ_id,
            "skin_num": skin_num,
            "name_tr": tr_info.get('name', f"Kostüm {skin_num}"),
            "rarity_tr": "Efsanevi" if tr_info.get('rarity') == 'kLegendary' else "Epik",
            "release_date": rel_date
        }
        db.append(new_skin)
        db_map[sid] = new_skin

# Write updated JSON
with open(db_path, "w", encoding="utf-8") as f:
    json.dump(db, f, ensure_ascii=False, indent=2)

# Generate final skins_dates.js
date_map = {}
for s in db:
    sid = s.get("skin_id")
    if sid:
        date_map[str(sid)] = s.get("release_date", "2015-01-01")

# Also ensure all CDragon skins have entries
for sid_str in skins_tr.keys():
    if sid_str not in date_map:
        sid_int = int(sid_str)
        if sid_int in OFFICIAL_DATES_BY_ID:
            date_map[sid_str] = OFFICIAL_DATES_BY_ID[sid_int]
        elif sid_int % 1000 == 0:
            date_map[sid_str] = "2009-02-21"
        else:
            date_map[sid_str] = "2024-01-01"

js_content = "window.LOL_SKINS_DATES = " + json.dumps(date_map, ensure_ascii=False) + ";\n"
with open(out_js, "w", encoding="utf-8") as f:
    f.write(js_content)

print(f"✅ skins_dates.js güncellendi! Toplam: {len(date_map)} kostüm tarihi kaydedildi.")
print("Örnek test: Koruma Ünitesi Galio (3040) ->", date_map.get("3040"))
