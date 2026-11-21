import urllib.request
import json
import re
import sys

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

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

print(f"Total skins fetched: TR={len(skins_tr)}, EN={len(skins_en)}")

# Map English names to Turkish skin IDs
en_to_id = {}
id_to_en = {}
for sid_str, s in skins_en.items():
    en_name = s.get('name', '').strip()
    if en_name:
        en_to_id[en_name.lower()] = int(sid_str)
        id_to_en[int(sid_str)] = en_name

# Now let's see which skins match our known Mobafire 2024-2026 accurate dates
accurate_dates_by_id = {
    # 2026
    en_to_id.get("mvp t1 miss fortune"): "2026-07-15",
    en_to_id.get("spaghetti alla vel'koz"): "2026-05-28",
    en_to_id.get("eternal aspect leona"): "2026-05-28",
    en_to_id.get("eternal aspect diana"): "2026-05-28",
    en_to_id.get("demoncursed vayne"): "2026-04-29",
    en_to_id.get("petals of spring lillia"): "2026-02-19",
    en_to_id.get("aegis frame galio"): "2026-01-22",
    3040: "2026-01-22", # Koruma Ünitesi Galio

    # 2025
    en_to_id.get("winter wonder zeri"): "2025-12-03",
    en_to_id.get("mecha kingdoms darius"): "2025-11-05",
    en_to_id.get("spirit blossom springs ahri"): "2025-07-30",
    en_to_id.get("spirit blossom springs teemo"): "2025-07-30",
    en_to_id.get("spirit blossom springs sett"): "2025-07-30",
    en_to_id.get("spirit blossom karma"): "2025-06-25",
    en_to_id.get("spirit blossom ashe"): "2025-04-30",
    en_to_id.get("spirit blossom irelia"): "2025-04-30",
    en_to_id.get("cat-in-the-box shaco"): "2025-04-02",
    en_to_id.get("battle academia xayah"): "2025-03-19",
    en_to_id.get("battle academia rakan"): "2025-03-19",
    en_to_id.get("mythmaker jhin"): "2025-01-23",

    # 2024
    en_to_id.get("arcane savior viktor"): "2024-12-11",
    en_to_id.get("arcane brawler vi"): "2024-11-20",
    en_to_id.get("arcane survivor jayce"): "2024-11-20",
    en_to_id.get("chosen of the wolf ambessa"): "2024-11-06",
    en_to_id.get("dark star sylas"): "2024-10-23",
    en_to_id.get("fright night veigar"): "2024-09-25",
    en_to_id.get("primordian aatrox"): "2024-07-31",
    en_to_id.get("battle dove seraphine"): "2024-07-17",
    en_to_id.get("empyrean varus"): "2024-05-01",
    en_to_id.get("high noon yone"): "2024-03-20",
    en_to_id.get("porcelain protector aurelion sol"): "2024-02-22",
    en_to_id.get("heavenscale lee sin"): "2024-02-07"
}

# Remove None keys
accurate_dates_by_id = {k: v for k, v in accurate_dates_by_id.items() if k is not None}

print(f"Mapped {len(accurate_dates_by_id)} accurate dates by exact Skin ID:")
for sid, dt in accurate_dates_by_id.items():
    tr_name = skins_tr.get(str(sid), {}).get('name', 'Bilinmeyen')
    en_name = id_to_en.get(sid, 'Unknown')
    print(f"  ID {sid}: {dt} -> TR: '{tr_name}' (EN: '{en_name}')")
