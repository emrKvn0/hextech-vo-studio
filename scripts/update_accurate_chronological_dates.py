import json
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

with open(db_path, "r", encoding="utf-8") as f:
    skins_db = json.load(f)

# Comprehensive list of recent & accurate skin dates
MOBAFIRE_ACCURATE_DATES = {
    # 2026
    "MVP T1 Miss Fortune": "2026-07-15",
    "Spaghetti alla Vel'Koz": "2026-05-28",
    "Spagetti Vel'Koz": "2026-05-28",
    "Sonsuzluğun Sureti Leona": "2026-05-28",
    "Eternal Aspect Leona": "2026-05-28",
    "Sonsuzluğun Sureti Diana": "2026-05-28",
    "Eternal Aspect Diana": "2026-05-28",
    "İblisin Laneti Vayne": "2026-04-29",
    "Demoncursed Vayne": "2026-04-29",
    "İlkbahar Yaprakları Lillia": "2026-02-19",
    "Petals of Spring Lillia": "2026-02-19",
    "Kalkan Zırhlı Galio": "2026-01-22",
    "Aegis Frame Galio": "2026-01-22",

    # 2025
    "Kış Mucizesi Zeri": "2025-12-03",
    "Winter Wonder Zeri": "2025-12-03",
    "Meka Krallıkları Darius": "2025-11-05",
    "Mecha Kingdoms Darius": "2025-11-05",
    "Ruh Çiçeği Kaplıcası Ahri": "2025-07-30",
    "Spirit Blossom Springs Ahri": "2025-07-30",
    "Ruh Çiçeği Kaplıcası Teemo": "2025-07-30",
    "Ruh Çiçeği Kaplıcası Yasuo": "2025-07-30",
    "Ruh Çiçeği Karma": "2025-06-25",
    "Spirit Blossom Karma": "2025-06-25",
    "Ruh Çiçeği Ashe": "2025-04-30",
    "Spirit Blossom Ashe": "2025-04-30",
    "Ruh Çiçeği Irelia": "2025-04-30",
    "Spirit Blossom Irelia": "2025-04-30",
    "Kedi Kutusu Shaco": "2025-04-02",
    "Cat-in-the-Box Shaco": "2025-04-02",
    "Savaş Akademisi Xayah": "2025-03-19",
    "Battle Academia Xayah": "2025-03-19",
    "Savaş Akademisi Rakan": "2025-03-19",
    "Battle Academia Rakan": "2025-03-19",
    "Efsanebaz Jhin": "2025-01-23",
    "Mythmaker Jhin": "2025-01-23",

    # 2024
    "Arcane: Kurtarıcı Viktor": "2024-12-11",
    "Arcane Savior Viktor": "2024-12-11",
    "Arcane: Dövüşçü Vi": "2024-11-20",
    "Arcane Brawler Vi": "2024-11-20",
    "Arcane: Felaketzede Jayce": "2024-11-20",
    "Arcane Survivor Jayce": "2024-11-20",
    "Arcane: Shimmer Warwick": "2024-11-20",
    "Kurt'un Seçilmişi Ambessa": "2024-11-06",
    "Chosen of the Wolf Ambessa": "2024-11-06",
    "Sonsuz Karanlık Sylas": "2024-10-23",
    "Dark Star Sylas": "2024-10-23",
    "Korkunç Gece Veigar": "2024-09-25",
    "Fright Night Veigar": "2024-09-25",
    "Primordia'lı Aatrox": "2024-07-31",
    "Primordian Aatrox": "2024-07-31",
    "Savaş Güvercini Seraphine": "2024-07-17",
    "Battle Dove Seraphine": "2024-07-17",
    "Arş Hükümdarı Varus": "2024-05-01",
    "Empyrean Varus": "2024-05-01",
    "Vahşi Batılı Yone": "2024-03-20",
    "High Noon Yone": "2024-03-20",
    "Porselen Muhafız Aurelion Sol": "2024-02-22",
    "Porcelain Protector Aurelion Sol": "2024-02-22",
    "Göklerin Efendisi Lee Sin": "2024-02-07",
    "Heavenscale Lee Sin": "2024-02-07"
}

# Update database
updated_count = 0
for s in skins_db:
    name_tr = s.get("name_tr", "")
    for k, v in MOBAFIRE_ACCURATE_DATES.items():
        if k.lower() in name_tr.lower() or name_tr.lower() in k.lower():
            s["release_date"] = v
            updated_count += 1
            break

# Save updated JSON
with open(db_path, "w", encoding="utf-8") as f:
    json.dump(skins_db, f, ensure_ascii=False, indent=2)

# Build date map for JS
date_map = {}
for s in skins_db:
    sid = s.get("skin_id") or (s.get("champion_id", 0) * 1000 + s.get("skin_num", 0))
    d = s.get("release_date")
    if d and d not in ["Bilinmiyor", "0000-00-00", "None"]:
        date_map[str(sid)] = d

js_content = "window.LOL_SKINS_DATES = " + json.dumps(date_map, ensure_ascii=False) + ";\n"
with open(out_js, "w", encoding="utf-8") as f:
    f.write(js_content)

print(f"Top {len(date_map)} skin release date written to skins_dates.js")
print(f"Updated {updated_count} specific skins from accurate chronological list.")
