import json

with open("all_lol_skins_database.json", "r", encoding="utf-8") as f:
    db = json.load(f)

recent_champs = ["Aurora", "Smolder", "Hwei", "Briar", "Naafiri", "Milio", "K'Sante", "Nilah", "Bel'Veth", "Renata Glasc", "Zeri", "Vex", "Akshan", "Gwen"]

recent_dates = {
    "Aurora": "2024-07-17",
    "Smolder": "2024-01-31",
    "Hwei": "2023-12-06",
    "Briar": "2023-09-13",
    "Naafiri": "2023-07-19",
    "Milio": "2023-03-22",
    "K'Sante": "2022-11-02",
    "Nilah": "2022-07-13",
    "Bel'Veth": "2022-06-09",
    "Renata Glasc": "2022-02-17",
    "Zeri": "2022-01-20",
    "Vex": "2021-09-23",
    "Akshan": "2021-07-22",
    "Gwen": "2021-04-15"
}

updated = 0
for s in db:
    cname = s.get("champion_name")
    if cname in recent_dates:
        if s.get("release_date") in ["2015-01-01", "2009-02-21", "2024-01-01"]:
            s["release_date"] = recent_dates[cname]
            updated += 1

with open("all_lol_skins_database.json", "w", encoding="utf-8") as f:
    json.dump(db, f, ensure_ascii=False, indent=2)

# Update web/skins_dates.js
date_map = {str(s['skin_id']): s['release_date'] for s in db if 'skin_id' in s}
with open('web/skins_dates.js', 'w', encoding='utf-8') as f:
    f.write("window.LOL_SKINS_DATES = " + json.dumps(date_map, ensure_ascii=False) + ";\n")

print(f"Updated {updated} recent champion release dates.")
