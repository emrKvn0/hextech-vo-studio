import os
import sys
import json
import urllib.request
import re
import threading
from datetime import datetime

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(ROOT_DIR, "all_lol_skins_database.json")
OUT_JS = os.path.join(ROOT_DIR, "web", "skins_dates.js")
SYNC_LOG_FILE = os.path.join(ROOT_DIR, ".last_skin_sync.json")

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

def fetch_json(url, timeout=20):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)

def get_local_skins():
    if os.path.exists(DB_PATH):
        try:
            with open(DB_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Yerel skin DB okuma hatası: {e}")
    return []

def save_local_skins(skins):
    with open(DB_PATH, 'w', encoding='utf-8') as f:
        json.dump(skins, f, ensure_ascii=False, indent=2)

    # skins_dates.js dosyasını da güncelle
    dates_map = {}
    for s in skins:
        sid = str(s.get('skin_id'))
        rdate = s.get('release_date') or ''
        if sid and rdate:
            dates_map[sid] = rdate

    with open(OUT_JS, 'w', encoding='utf-8') as f:
        f.write("window.LOL_SKINS_DATES = " + json.dumps(dates_map, ensure_ascii=False, indent=2) + ";\n")

def check_for_updates():
    """
    CDragon'dan son kostüm sayısını ve ID'lerini kontrol eder.
    Dönüş: (needs_update: bool, missing_ids: list, remote_total: int, local_total: int)
    """
    local_skins = get_local_skins()
    local_ids = {s['skin_id'] for s in local_skins if 'skin_id' in s}

    try:
        remote_skins_tr = fetch_json("https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/tr_tr/v1/skins.json", timeout=12)
        remote_ids = {int(k) for k in remote_skins_tr.keys() if k.isdigit() and int(k) > 0}
        
        missing = sorted(list(remote_ids - local_ids))
        needs_update = len(missing) > 0
        return needs_update, missing, len(remote_ids), len(local_ids)
    except Exception as e:
        print(f"⚠️ CDragon kontrolü sırasında hata: {e}")
        return False, [], 0, len(local_ids)

def sync_skins(log_callback=print):
    """
    Yeni kostümleri CDragon'dan çeker ve yerel veritabanını günceller.
    """
    local_skins = get_local_skins()
    local_ids = {s['skin_id'] for s in local_skins if 'skin_id' in s}

    log_callback("🌐 CDragon üzerinden güncel kostüm ve şampiyon verileri alınıyor...")
    try:
        cd_skins_tr = fetch_json("https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/tr_tr/v1/skins.json")
        cd_skins_en = fetch_json("https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/skins.json")
        cd_champs = fetch_json("https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/tr_tr/v1/champion-summary.json")
    except Exception as e:
        log_callback(f"❌ CDragon verisi indirilemedi: {e}")
        return {"status": "error", "message": str(e)}

    champ_meta = {c['id']: c for c in cd_champs if 'id' in c}
    remote_ids = {int(k) for k in cd_skins_tr.keys() if k.isdigit() and int(k) > 0}
    missing_ids = remote_ids - local_ids

    if not missing_ids:
        log_callback("✅ Kostüm veritabanı zaten %100 güncel!")
        return {"status": "success", "updated": 0, "total": len(local_skins)}

    log_callback(f"🧩 {len(missing_ids)} yeni kostüm tespit edildi, sisteme entegre ediliyor...")

    rarity_map = {
        'kNoRarity': 'Standart', 'kEpic': 'Epik (1350 RP)', 'kLegendary': 'Efsanevi (1820 RP)',
        'kMythic': 'İhtişamlı / Prestij', 'kUltimate': 'Ebedi (Ultimate)',
        'kExclusive': 'Özel / Sandık', 'kTranscendent': 'Ulu (Transcendent)', 'kExalted': 'Haşmetli'
    }

    rarity_cost_map = {
        'kEpic': 1350, 'kLegendary': 1820, 'kUltimate': 3250,
        'kMythic': 0, 'kExclusive': 0, 'kTranscendent': 0, 'kExalted': 0
    }

    added_count = 0
    for sid in sorted(list(missing_ids)):
        str_id = str(sid)
        tr_data = cd_skins_tr.get(str_id, {})
        en_data = cd_skins_en.get(str_id, {})
        if not tr_data:
            continue

        champ_id = sid // 1000
        skin_num = sid % 1000
        c_info = champ_meta.get(champ_id, {})

        c_name = c_info.get('name') or c_info.get('alias') or 'Şampiyon'
        c_alias = c_info.get('alias') or c_name

        tr_name = tr_data.get('name', '').strip()
        en_name = en_data.get('name', '').strip() or tr_name
        is_base = bool(tr_data.get('isBase', skin_num == 0))

        if is_base:
            tr_name = f"Varsayılan {c_name}"
            en_name = f"Default {c_alias}"

        raw_rarity = tr_data.get('rarity') or 'kNoRarity'
        rarity_tr = rarity_map.get(raw_rarity, 'Standart')
        cost_rp = rarity_cost_map.get(raw_rarity, 0)
        if raw_rarity == 'kNoRarity' and not is_base:
            cost_rp = 975

        # Tahmini çıkış tarihi (yeni kostümler için bugünün tarihi)
        release_date = datetime.now().strftime("%Y-%m-%d")

        splash_path = tr_data.get('splashPath') or ''
        splash_url = ""
        if splash_path:
            clean_splash = splash_path.replace('/lol-game-data/assets/', '').lower()
            splash_url = f"https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/{clean_splash}"

        skin_obj = {
            "skin_id": sid,
            "champion_id": champ_id,
            "champion_name": c_name,
            "champion_alias": c_alias,
            "skin_num": skin_num,
            "is_base": is_base,
            "name_tr": tr_name,
            "name_en": en_name,
            "rarity_raw": raw_rarity,
            "rarity_tr": rarity_tr,
            "cost_rp": cost_rp,
            "release_date": release_date,
            "has_new_voice_lines": raw_rarity in ('kLegendary', 'kUltimate', 'kTranscendent', 'kExalted'),
            "has_new_quotes": raw_rarity in ('kLegendary', 'kUltimate', 'kTranscendent', 'kExalted'),
            "is_legacy": False,
            "description_tr": tr_data.get('description', '') or '',
            "splash_url": splash_url
        }

        local_skins.append(skin_obj)
        added_count += 1

    local_skins.sort(key=lambda x: x['skin_id'])
    save_local_skins(local_skins)

    # Senkronizasyon kaydı oluştur
    try:
        with open(SYNC_LOG_FILE, 'w', encoding='utf-8') as f:
            json.dump({
                "last_sync": datetime.now().isoformat(),
                "added_count": added_count,
                "total_skins": len(local_skins)
            }, f, indent=2)
    except Exception:
        pass

    log_callback(f"💾 Veritabanı başarıyla güncellendi! Toplam {len(local_skins)} kostüm mevcut (+{added_count} yeni eklendi).")
    return {"status": "success", "updated": added_count, "total": len(local_skins)}

def trigger_background_sync(on_complete=None):
    def _worker():
        try:
            needs_update, missing, remote_tot, local_tot = check_for_updates()
            if needs_update:
                print(f"🔄 Arka planda yeni LoL kostümleri tespit edildi ({len(missing)} yeni). Güncelleniyor...")
                res = sync_skins(log_callback=print)
                if on_complete:
                    on_complete(res)
            else:
                print(f"✅ Kostüm veritabanı güncel ({local_tot} kostüm).")
        except Exception as e:
            print(f"⚠️ Arka plan kostüm senkronizasyon hatası: {e}")

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    return t

if __name__ == "__main__":
    if sys.platform == 'win32':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass
    res = sync_skins()
    print("Sonuç:", res)
