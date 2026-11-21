import os
import sys
import json
import re
import functools
import urllib.request

# Immediate unbuffered stdout with UTF-8
print = functools.partial(print, flush=True)

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

WORKSPACE = r"C:\Users\PC\Desktop\Yazılım\projects\active\lol-ses-veriler"
PBE_CACHE_DIR = os.path.join(WORKSPACE, "PBE_Cache")
os.makedirs(PBE_CACHE_DIR, exist_ok=True)

CD_PBE_BASE = "https://raw.communitydragon.org/pbe"

def get_champion_numeric_id(champ_name):
    """Dynamically resolves champion ID (e.g. Seraphine -> 147, Garen -> 86)."""
    champ_clean = champ_name.lower().replace("'", "").replace(" ", "").replace("_", "")
    
    # 1. Try champions_metadata.json
    meta_path = os.path.join(WORKSPACE, "champions_metadata.json")
    if os.path.exists(meta_path):
        try:
            with open(meta_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for item in data:
                    c_key = item.get('champion_name', '').lower().replace("'", "").replace(" ", "").replace("_", "")
                    c_alias = item.get('champion_alias', '').lower().replace("'", "").replace(" ", "").replace("_", "")
                    if c_key == champ_clean or c_alias == champ_clean:
                        return str(item.get('champion_id', '147'))
        except Exception:
            pass

    # 2. Try all_lol_skins_database.json
    skins_db_path = os.path.join(WORKSPACE, "all_lol_skins_database.json")
    if os.path.exists(skins_db_path):
        try:
            with open(skins_db_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for item in data:
                    c_key = item.get('champion_name', '').lower().replace("'", "").replace(" ", "").replace("_", "")
                    c_alias = item.get('champion_alias', '').lower().replace("'", "").replace(" ", "").replace("_", "")
                    if c_key == champ_clean or c_alias == champ_clean:
                        return str(item.get('champion_id', '147'))
        except Exception:
            pass

    return "147"

def fetch_pbe_audio_assets(champ_name, skin_num_or_id, target_folder_name=None, out_dir=None):
    """
    Downloads or streams PBE specific audio/SFX without requiring full 50GB PBE client installation.
    Returns dict containing status, downloaded count, and discovered Wwise event names.
    """
    folder_name = target_folder_name or f"PBE_Skin_{skin_num_or_id}"
    if not out_dir:
        out_dir = os.path.join(WORKSPACE, "Champions", champ_name, folder_name)

    secim_dir = os.path.join(out_dir, "0_Secim_ve_Yasaklama")
    sfx_dir = os.path.join(out_dir, "Ses_Efektleri")
    os.makedirs(secim_dir, exist_ok=True)
    os.makedirs(sfx_dir, exist_ok=True)

    champ_clean = champ_name.lower().replace("'", "").replace(" ", "").replace("_", "")
    champ_id = get_champion_numeric_id(champ_name)
    
    m = re.search(r'(\d+)', str(skin_num_or_id))
    skin_num = int(m.group(1)) if m else 0
    if skin_num > 1000:
        skin_num = skin_num % 1000

    print(f"☁️ [PBE Bulut] {champ_name} ({folder_name}) için 0 GB yer kaplayan PBE ses akışı başlatılıyor...")
    
    downloaded = 0
    
    # 1. PBE Choose & Ban Voice
    choose_url = f"{CD_PBE_BASE}/plugins/rcp-be-lol-game-data/global/tr_tr/v1/champion-choose-vo/{champ_id}.ogg"
    ban_url = f"{CD_PBE_BASE}/plugins/rcp-be-lol-game-data/global/tr_tr/v1/champion-ban-vo/{champ_id}.ogg"
    
    for name, url in [
        (f"{champ_clean}_pbe_secim_sesi.ogg", choose_url),
        (f"{champ_clean}_pbe_yasaklama_sesi.ogg", ban_url)
    ]:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            dst = os.path.join(secim_dir, name)
            with urllib.request.urlopen(req, timeout=10) as resp, open(dst, 'wb') as f:
                f.write(resp.read())
            downloaded += 1
            print(f"  ✅ [PBE CDN] {name} indirildi.")
        except Exception:
            pass

    # 2. PBE Champion SFX Audio
    sfx_url = f"{CD_PBE_BASE}/plugins/rcp-be-lol-game-data/global/default/v1/champion-sfx-audios/{champ_id}.ogg"
    try:
        req = urllib.request.Request(sfx_url, headers={'User-Agent': 'Mozilla/5.0'})
        dst = os.path.join(sfx_dir, f"{champ_clean}_pbe_genel_sfx.ogg")
        with urllib.request.urlopen(req, timeout=10) as resp, open(dst, 'wb') as f:
            f.write(resp.read())
        downloaded += 1
        print(f"  ✅ [PBE CDN] {champ_clean}_pbe_genel_sfx.ogg indirildi.")
    except Exception:
        pass

    # 3. Extract PBE Wwise Events Manifest for this skin
    discovered_events = []
    try:
        bin_url = f"{CD_PBE_BASE}/game/data/characters/{champ_clean}/skins/skin{skin_num:02d}.bin.json"
        req = urllib.request.Request(bin_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            bin_data = json.loads(resp.read().decode('utf-8'))
            banks = []
            for k, v in bin_data.items():
                if isinstance(v, dict) and 'skinAudioProperties' in v:
                    banks = v['skinAudioProperties'].get('bankUnits', [])
                    break
            if banks:
                manifest_path = os.path.join(out_dir, "pbe_wwise_events_manifest.json")
                with open(manifest_path, 'w', encoding='utf-8') as f:
                    json.dump(banks, f, ensure_ascii=False, indent=2)
                for b in banks:
                    for ev in b.get('events', []):
                        discovered_events.append(ev)
                print(f"  ✅ [PBE Wwise] {len(discovered_events)} adet resmi PBE Wwise Event haritası kaydedildi.")
    except Exception as e:
        pass
            
    return {
        "status": "success",
        "downloaded_files": downloaded,
        "events": discovered_events
    }

if __name__ == "__main__":
    fetch_pbe_audio_assets("Seraphine", "147069", "Kalp_Şarkısı_Seraphine")
