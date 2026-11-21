import json
import sys

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

with open('all_lol_skins_database.json', 'r', encoding='utf-8') as f:
    skins = json.load(f)

# Sadece bağımsız yeni seslendirmeye (VO) sahip veya Efsanevi/Aşkın kostümler
legendary_and_vo = [
    s for s in skins
    if not s['is_base'] and (
        s['has_new_voice_lines'] or 
        'Legendary' in s['rarity_raw'] or 
        'Transcendent' in s['rarity_raw'] or 
        'Ultimate' in s['rarity_raw']
    )
]

print(f"Toplam Özel Replikli / Efsanevi Kostüm: {len(legendary_and_vo)}")
print("\n" + "="*80)
print(" 🚀 YOUTUBE / TIKTOK İZLENME VE BULUNABİLİRLİK POTANSİYELİ EN YÜKSEK KOSTÜMLER")
print("="*80)

for idx, s in enumerate(legendary_and_vo[:25], 1):
    champ = s['champion_name']
    name = s['name_tr']
    r_date = s['release_date']
    rarity = s['rarity_tr']
    print(f"{idx:02d}. [{r_date}] {name} ({champ}) -> {rarity}")
