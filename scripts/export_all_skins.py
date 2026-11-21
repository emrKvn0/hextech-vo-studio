import os
import sys
import json
import urllib.request
from datetime import datetime

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

CD_SKINS_TR_URL = "https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/tr_tr/v1/skins.json"
CD_CHAMPS_TR_URL = "https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/tr_tr/v1/champion-summary.json"
MERAKI_CHAMPS_URL = "https://cdn.merakianalytics.com/riot/lol/resources/latest/en-US/champions.json"
OUTPUT_JSON_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "all_lol_skins_database.json")

RARITY_TR_MAP = {
    "kNoRarity": "Standart / Yaygın",
    "NoRarity": "Standart / Yaygın",
    "kEpic": "Destansı (1350 RP)",
    "Epic": "Destansı (1350 RP)",
    "kLegendary": "Efsanevi (1820 RP)",
    "Legendary": "Efsanevi (1820 RP)",
    "kMythic": "İhtişamlı / Prestij",
    "Mythic": "İhtişamlı / Prestij",
    "kUltimate": "Ebedi (3250 RP)",
    "Ultimate": "Ebedi (3250 RP)",
    "kTranscendent": "Ulu (Şöhretler Müzesi)",
    "Transcendent": "Ulu (Şöhretler Müzesi)",
    "kExalted": "Haşmetli (Mabed)",
    "Exalted": "Haşmetli (Mabed)",
    "kRare": "Nadir (975 RP)",
    "Rare": "Nadir (975 RP)",
    "kExclusive": "Özel / Etkinlik"
}

def fetch_json(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode('utf-8'))

def build_skins_database():
    print("🌐 1. Türkçe kostüm ve şampiyon verileri CommunityDragon üzerinden alınıyor...")
    cd_skins_raw = fetch_json(CD_SKINS_TR_URL)
    cd_champs_raw = fetch_json(CD_CHAMPS_TR_URL)

    champ_id_to_name = {}
    for c in cd_champs_raw:
        c_id = c.get('id')
        if c_id and c_id > 0:
            champ_id_to_name[c_id] = {
                'name': c.get('name', ''),
                'alias': c.get('alias', ''),
                'title': c.get('title', '')
            }

    print("🌐 2. Çıkış tarihleri, RP maliyetleri ve Dublaj (VO) verileri Meraki Analytics üzerinden alınıyor...")
    meraki_champs = {}
    try:
        meraki_champs = fetch_json(MERAKI_CHAMPS_URL)
    except Exception as e:
        print(f"⚠️ Meraki API uyarısı: {e}")

    meraki_skins_by_id = {}
    for c_alias, c_info in meraki_champs.items():
        for s in c_info.get('skins', []):
            s_id = s.get('id')
            if s_id:
                meraki_skins_by_id[s_id] = s

    print("🧩 3. Veriler birleştiriliyor ve hiyerarşik yapı oluşturuluyor...")
    all_skins = []

    for skin_id_str, cd_skin in cd_skins_raw.items():
        try:
            skin_id = int(skin_id_str)
        except ValueError:
            continue

        champ_id = skin_id // 1000
        skin_num = skin_id % 1000
        is_base = cd_skin.get('isBase', False) or skin_num == 0

        champ_meta = champ_id_to_name.get(champ_id, {'name': 'Bilinmeyen', 'alias': '', 'title': ''})
        champ_name = champ_meta['name']
        champ_alias = champ_meta['alias']

        meraki_info = meraki_skins_by_id.get(skin_id, {})

        # Rarity normalization
        raw_rarity = cd_skin.get('rarity') or meraki_info.get('rarity') or 'kNoRarity'
        rarity_tr = RARITY_TR_MAP.get(raw_rarity, raw_rarity)

        # Release date
        release_date = meraki_info.get('release') or "Bilinmiyor"
        cost = meraki_info.get('cost') or (1820 if 'Legendary' in raw_rarity else 1350 if 'Epic' in raw_rarity else 0)
        new_voice = meraki_info.get('newVoice', False) or 'Legendary' in raw_rarity or 'Ultimate' in raw_rarity or 'Transcendent' in raw_rarity
        new_quotes = meraki_info.get('newQuotes', False) or new_voice

        turkish_name = cd_skin.get('name') or meraki_info.get('name') or f"{champ_name} Kostümü"
        if is_base and (not turkish_name or turkish_name.lower() == champ_name.lower()):
            turkish_name = f"Varsayılan {champ_name}"

        skin_entry = {
            "skin_id": skin_id,
            "champion_id": champ_id,
            "champion_name": champ_name,
            "champion_alias": champ_alias,
            "skin_num": skin_num,
            "is_base": is_base,
            "name_tr": turkish_name,
            "rarity_raw": raw_rarity,
            "rarity_tr": rarity_tr,
            "cost_rp": cost,
            "release_date": release_date,
            "has_new_voice_lines": new_voice, # Yeni bağımsız replik / dublaj var mı?
            "has_new_quotes": new_quotes,
            "is_legacy": cd_skin.get('isLegacy', False),
            "description_tr": cd_skin.get('description') or meraki_info.get('lore') or "",
            "splash_url": f"https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/champion-splashes/{champ_id}/{skin_id}.jpg"
        }
        all_skins.append(skin_entry)

    # Sort by release date descending (newest first)
    def date_sort_key(item):
        d = item.get('release_date')
        if not d or d == "Bilinmiyor":
            return "1970-01-01"
        return d

    all_skins.sort(key=date_sort_key, reverse=True)

    print(f"💾 4. Toplam {len(all_skins):,} adet kostüm '{OUTPUT_JSON_PATH}' dosyasına kaydediliyor...")
    with open(OUTPUT_JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(all_skins, f, ensure_ascii=False, indent=2)

    print("✅ İşlem başarıyla tamamlandı!")
    return all_skins

if __name__ == "__main__":
    build_skins_database()
