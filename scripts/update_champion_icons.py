# -*- coding: utf-8 -*-
"""
Resmi League of Legends PC güncel şampiyon ikonlarını CommunityDragon ve DataDragon üzerinden
tam eşleştirerek lol_matrix_data.json ve matrix veritabanına uygular.
Wild Rift / TFT (60000+ ID) hatalarını temizler, ASU/VGU güncel ikonlarını bağlar.
"""

import os
import sys
import json
import urllib.request

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSON_PATH = os.path.join(ROOT_DIR, "lol-matrix-web", "public", "data", "lol_matrix_data.json")

def main():
    print("🔄 CommunityDragon üzerinden en güncel resmi şampiyon haritası çekiliyor...")
    url = "https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/champion-summary.json"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            summary = json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        print(f"⚠️ İnternet hatası: {e}")
        return

    id_map = {}
    for item in summary:
        cid = item.get('id', -1)
        if 0 < cid < 1000:  # Resmi PC League of Legends şampiyonları
            name = item.get('name', '').strip()
            alias = item.get('alias', '').strip()
            if name:
                id_map[name.lower()] = cid
                id_map[name.lower().replace(" ", "").replace("'", "").replace(".", "")] = cid
            if alias:
                id_map[alias.lower()] = cid
                id_map[alias.lower().replace(" ", "").replace("'", "").replace(".", "")] = cid

    # Bilinen özel isimler ve Riot istisnaları
    overrides = {
        'wukong': 62, 'monkeyking': 62,
        'nunu': 20, 'nunu & willump': 20, 'nunu and willump': 20,
        'renata glasc': 888, 'renata': 888,
        'belveth': 897, "bel'veth": 897,
        'ksante': 899, "k'sante": 899,
        'kaisa': 145, "kai'sa": 145,
        'khazix': 121, "kha'zix": 121,
        'velkoz': 161, "vel'koz": 161,
        'chogath': 31, "cho'gath": 31,
        'kogmaw': 96, "kog'maw": 96,
        'reksai': 421, "rek'sai": 421,
        'drmundo': 36, "dr. mundo": 36, "dr mundo": 36,
        'jarvan iv': 59, 'jarvaniv': 59,
        'twisted fate': 4, 'twistedfate': 4,
        'miss fortune': 21, 'missfortune': 21,
        'master yi': 11, 'masteryi': 11,
        'xin zhao': 5, 'xinzhao': 5,
        'tahm kench': 223, 'tahmkench': 223,
        'aurelion sol': 136, 'aurelionsol': 136,
        'lee sin': 64, 'leesin': 64,
        'garen': 86,
        'ahri': 103,
        'teemo': 17,
        'jax': 24,
        'skarner': 72
    }
    for k, v in overrides.items():
        id_map[k] = v
        id_map[k.replace(" ", "").replace("'", "").replace(".", "")] = v

    if not os.path.exists(JSON_PATH):
        print(f"❌ Dosya bulunamadı: {JSON_PATH}")
        return

    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        db = json.load(f)

    updated_count = 0
    fixed_names = []

    for c in db.get('champions', []):
        cname = c.get('name', '')
        clow = cname.lower().replace("'", "").replace(" ", "").replace(".", "")
        correct_id = id_map.get(clow) or id_map.get(cname.lower())
        
        if correct_id:
            new_icon = f"https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/champion-icons/{correct_id}.png"
            old_icon = c.get('icon_url', '')
            if old_icon != new_icon or c.get('id') != correct_id:
                c['id'] = correct_id
                c['icon_url'] = new_icon
                updated_count += 1
                fixed_names.append((cname, correct_id))

        # Şampiyon içindeki top_speakers ve top_targets ikonlarını da güncelle
        for ts in c.get('top_speakers', []):
            sname = ts.get('name', '')
            slow = sname.lower().replace("'", "").replace(" ", "").replace(".", "")
            sid = id_map.get(slow) or id_map.get(sname.lower())
            if sid:
                ts['icon_url'] = f"https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/champion-icons/{sid}.png"

        for tt in c.get('top_targets', []):
            tname = tt.get('name', '')
            tlow = tname.lower().replace("'", "").replace(" ", "").replace(".", "")
            tid = id_map.get(tlow) or id_map.get(tname.lower())
            if tid:
                tt['icon_url'] = f"https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/champion-icons/{tid}.png"

    with open(JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False)

    print(f"✅ Toplam {updated_count} şampiyonun ikonu ve ID'si resmi güncel PC LoL ikonlarıyla yenilendi!")
    print(f"Örnek güncellenenler: {fixed_names[:10]}")

if __name__ == '__main__':
    main()
