# -*- coding: utf-8 -*-
import json
import os

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
lor_db_path = os.path.join(root_dir, 'cache', 'lor_full_database.json')
web_db_path = os.path.join(root_dir, 'lol-matrix-web', 'public', 'data', 'lor_matrix_data.json')

with open(lor_db_path, 'r', encoding='utf-8') as f:
    db = json.load(f)

char_meta = db.get('char_meta', {})
updated_champs = 0

for cname, cmeta in char_meta.items():
    if not cmeta.get('is_champ'):
        continue
    codes = cmeta.get('codes', [])
    skins = cmeta.setdefault('skins', {})
    c_set = cmeta.get('set', 'Set1')

    # Seviye 1 (Temel)
    c0 = codes[0] if codes else cmeta.get('base_code', '')
    sk0 = skins.get('0') or skins.get(0) or {}
    sk0['skin_num'] = 0
    sk0['name'] = f"{cname} (Seviye 1)"
    sk0['card_code'] = c0
    sk0['is_base'] = True
    sk0['splash_url'] = f"https://cdn.runeterra.ar/assets/img/card/en_us/{c0}-full.webp"
    sk0['extra_urls'] = [
        f"https://dd.b.pvp.net/latest/{c_set.lower()}/en_us/img/cards/{c0}-full.png",
        f"https://cdn.runeterra.ar/assets/img/card/en_us/{c0}-full.webp"
    ]
    sk0['voice_type'] = 'base'
    sk0['voice_badge'] = '🃏 LOR SEVİYE 1'
    sk0['voice_tag'] = 'Seviye 1 Kartı'
    sk0['voice_desc'] = f"{cname} Seviye 1 kart çizimi ve dublajı."
    sk0['is_unique'] = True
    skins['0'] = sk0

    # Seviye 2, Seviye 3 vb.
    for idx, code in enumerate(codes[1:], start=1):
        s_key = str(idx)
        lvl_num = idx + 1
        name = f"{cname} (Seviye {lvl_num})" if lvl_num <= 3 else f"{cname} (Özel Form {lvl_num})"
        skins[s_key] = {
            'skin_num': idx,
            'name': name,
            'card_code': code,
            'is_base': False,
            'splash_url': f"https://cdn.runeterra.ar/assets/img/card/en_us/{code}-full.webp",
            'extra_urls': [
                f"https://dd.b.pvp.net/latest/{c_set.lower()}/en_us/img/cards/{code}-full.png",
                f"https://cdn.runeterra.ar/assets/img/card/en_us/{code}-full.webp"
            ],
            'voice_type': 'base',
            'voice_badge': f"🃏 LOR SEVİYE {lvl_num}",
            'voice_tag': f"Seviye {lvl_num} Kartı",
            'voice_desc': f"{cname} {name} kart çizimi ve dublajı.",
            'is_unique': True
        }
    updated_champs += 1

with open(lor_db_path, 'w', encoding='utf-8') as f:
    json.dump(db, f, ensure_ascii=False, indent=2)

if os.path.exists(web_db_path):
    with open(web_db_path, 'r', encoding='utf-8') as f:
        wdb = json.load(f)
    wdb['char_meta'] = char_meta
    with open(web_db_path, 'w', encoding='utf-8') as f:
        json.dump(wdb, f, ensure_ascii=False, indent=2)

print(f"Successfully updated {updated_champs} LoR champions with Level 1, 2, 3 card skins!")
