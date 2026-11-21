import urllib.request
import json
import os

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
db_path = os.path.join(ROOT_DIR, "all_lol_skins_database.json")
out_js = os.path.join(ROOT_DIR, "web", "skins_dates.js")

with open(db_path, "r", encoding="utf-8") as f:
    db = json.load(f)

# Fetch latest Meraki or CDragon champions to get any missing skin dates
print("Checking CDragon live & pbe skin dates...")
headers = {'User-Agent': 'Mozilla/5.0'}

# Build a comprehensive dictionary
date_dict = {}
name_dict = {}

for s in db:
    sid = s.get("skin_id") or (s.get("champion_id", 0) * 1000 + s.get("skin_num", 0))
    d = s.get("release_date")
    if d and d not in ["Bilinmiyor", "0000-00-00", "None"]:
        date_dict[str(sid)] = d
    if s.get("name_tr"):
        name_dict[str(sid)] = s.get("name_tr")

print(f"Mevcut veritabanından alınan tarih sayısı: {len(date_dict)}")

# Also try CDragon skins.json
try:
    url = "https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/skins.json"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as resp:
        cd_skins = json.load(resp)
    
    added_from_cd = 0
    for sid_str, sdata in cd_skins.items():
        if sid_str not in date_dict:
            # Check if CD has release date
            rd = sdata.get("releaseDate")
            if rd and rd not in ["0000-00-00", ""]:
                date_dict[sid_str] = rd[:10]
                added_from_cd += 1
    print(f"CDragon'dan eklenen yeni tarihler: {added_from_cd}")
except Exception as e:
    print(f"CDragon fetch note: {e}")

# Save to web/skins_dates.js
js_content = "window.LOL_SKINS_DATES = " + json.dumps(date_dict, ensure_ascii=False) + ";\n"
with open(out_js, "w", encoding="utf-8") as f:
    f.write(js_content)

print(f"✅ Toplam {len(date_dict)} kostümün gerçek tarihi skins_dates.js içine yazıldı.")
