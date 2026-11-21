import os
import sys
import re
import wave
import struct
import shutil
import subprocess
import functools
import concurrent.futures
import zstandard as zstd
from event_categorizer import parse_event_info
from metadata_manager import MetadataManager, sanitize_folder_name

# Immediate unbuffered stdout
print = functools.partial(print, flush=True)

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

def get_vgmstream_path():
    candidates = [
        os.path.join(getattr(sys, '_MEIPASS', ''), "vgmstream", "vgmstream-cli.exe"),
        os.path.join(os.path.dirname(sys.executable), "vgmstream", "vgmstream-cli.exe"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "vgmstream", "vgmstream-cli.exe"),
        os.path.join(os.getcwd(), "vgmstream", "vgmstream-cli.exe")
    ]
    for c in candidates:
        if c and os.path.exists(c):
            return c
    return "vgmstream-cli.exe"

def get_output_base():
    if getattr(sys, 'frozen', False):
        return os.path.join(os.path.dirname(sys.executable), "Champions")
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Champions")

def get_lol_champions_path():
    candidates = [
        r"C:\Riot Games\League of Legends\Game\DATA\FINAL\Champions",
        r"D:\Riot Games\League of Legends\Game\DATA\FINAL\Champions",
        r"E:\Riot Games\League of Legends\Game\DATA\FINAL\Champions",
        r"C:\Program Files\Riot Games\League of Legends\Game\DATA\FINAL\Champions",
        r"C:\Program Files (x86)\Riot Games\League of Legends\Game\DATA\FINAL\Champions",
        r"C:\League of Legends\Game\DATA\FINAL\Champions",
        r"D:\League of Legends\Game\DATA\FINAL\Champions",
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return candidates[0]

HASHES_PATH = r"C:\Users\emrKvn\Downloads\Obsidian_5.1.8\hashes\hashes.game.txt"
LOL_CHAMPIONS_PATH = get_lol_champions_path()
VGMSTREAM_PATH = get_vgmstream_path()
OUTPUT_BASE = get_output_base()

import threading

_download_lock = threading.Lock()

def ensure_champion_tr_wad(champ_name):
    """
    Kullanıcının oyunu İngilizce (en_US) olsa bile, Riot CDN üzerinden sadece istenen
    şampiyonun Türkçe WAD dosyasını (~7-15 MB) güvenli ve sıralı biçimde indirip Türkçe ses sağlar.
    """
    manifest_downloader = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools", "ManifestDownloader.exe")
    if not os.path.exists(manifest_downloader):
        return None
    
    out_dir = LOL_CHAMPIONS_PATH if os.path.exists(LOL_CHAMPIONS_PATH) else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Downloaded_TR_WADs")
    os.makedirs(out_dir, exist_ok=True)
    target_file = f"{champ_name}.tr_TR.wad.client"
    expected_path = os.path.join(out_dir, target_file)

    # 1. Zaten indirilmiş veya diskte mevcutsa tekrar indirme
    if os.path.exists(expected_path) and os.path.getsize(expected_path) > 100000:
        return expected_path
        
    alt_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Downloaded_TR_WADs", target_file)
    if os.path.exists(alt_path) and os.path.getsize(alt_path) > 100000:
        return alt_path

    # 2. Aynı anda birden fazla indirme fırtınasını önlemek için Lock
    with _download_lock:
        # Kilit alındıktan sonra tekrar kontrol (double-checked locking)
        if os.path.exists(expected_path) and os.path.getsize(expected_path) > 100000:
            return expected_path
        if os.path.exists(alt_path) and os.path.getsize(alt_path) > 100000:
            return alt_path

        proc = None
        try:
            manifest_url = "https://lol.secure.dyn.riotcdn.net/channels/public/releases/3FDBAF8A23FAE03E.manifest"
            print(f"☁️ [Riot Bulut CDN] '{champ_name}' için sadece 7-15 MB Türkçe ses paketi indiriliyor...")
            
            output_target = out_dir if out_dir != LOL_CHAMPIONS_PATH else os.path.dirname(os.path.dirname(os.path.dirname(out_dir)))
            cmd = [
                manifest_downloader,
                manifest_url,
                "-f", target_file,
                "-o", output_target,
                "-t", "4"
            ]
            cflags = 0x08000000 if sys.platform == 'win32' else 0
            
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=cflags
            )
            try:
                proc.communicate(timeout=90)
            except subprocess.TimeoutExpired:
                print(f"  ⚠️ [Riot CDN] '{champ_name}' indirme zaman aşımına uğradı (90s). İşlem sonlandırılıyor...")
                proc.kill()
                proc.communicate()
                if sys.platform == 'win32':
                    subprocess.run(f"taskkill /F /PID {proc.pid} /T", shell=True, capture_output=True)
                return None
            
            if os.path.exists(expected_path) and os.path.getsize(expected_path) > 100000:
                print(f"  ✅ [Riot CDN] '{champ_name}' Türkçe ses paketi başarıyla hazırlandı.")
                return expected_path
        except Exception as e:
            print(f"  ⚠️ Bulut WAD indirme hatası: {e}")
            if proc:
                try:
                    proc.kill()
                except Exception:
                    pass
        return None

def find_champion_wad_files(champ_name, auto_download=True):
    """
    Şampiyon için dil/ses WAD dosyasını ve ana WAD dosyasını dinamik olarak bulur.
    Öncelik: .tr_TR.wad.client -> (auto_download ise Riot CDN İndirme) -> .{any_locale}.wad.client -> .wad.client
    """
    c_clean = champ_name.lower().replace(" ", "").replace("'", "").replace("_", "")
    if not os.path.exists(LOL_CHAMPIONS_PATH):
        return None, None, champ_name

    matched_files = []
    actual_champ_name = champ_name
    for f in os.listdir(LOL_CHAMPIONS_PATH):
        if not f.endswith('.wad.client'):
            continue
        base = f.replace('.wad.client', '')
        c_part = base.split('.')[0]
        if c_part.lower().replace(" ", "").replace("'", "").replace("_", "") == c_clean:
            matched_files.append(f)
            actual_champ_name = c_part

    # 1. Dil/ses WAD dosyası ara (tr_TR öncelikli)
    voice_wad_file = None
    for f in matched_files:
        if '.tr_tr.wad.client' in f.lower():
            voice_wad_file = f
            break
            
    # 2. Eğer yerel diskte tr_TR yoksa ve auto_download True ise, Riot CDN üzerinden kontrollü indir
    if not voice_wad_file and auto_download:
        downloaded = ensure_champion_tr_wad(actual_champ_name)
        if downloaded and os.path.exists(downloaded):
            voice_wad_file = os.path.basename(downloaded)

    # 3. Hala yoksa mevcut herhangi bir dil dosyasını al (en_US vs)
    if not voice_wad_file:
        for f in matched_files:
            parts = f.split('.')
            if len(parts) >= 4 and parts[-2] == 'wad' and parts[-1] == 'client':
                voice_wad_file = f
                break

    # 4. Ana WAD dosyası ara
    main_wad_file = None
    for f in matched_files:
        if f == f"{actual_champ_name}.wad.client" or f.lower() == f"{c_clean}.wad.client":
            main_wad_file = f
            break

    if not voice_wad_file and main_wad_file:
        voice_wad_file = main_wad_file
    if not main_wad_file and voice_wad_file:
        main_wad_file = voice_wad_file

    voice_path = os.path.join(LOL_CHAMPIONS_PATH, voice_wad_file) if voice_wad_file else None
    main_path = os.path.join(LOL_CHAMPIONS_PATH, main_wad_file) if main_wad_file else None

    return voice_path, main_path, actual_champ_name

def fnv_1(name):
    h = 0x811c9dc5
    for c in name.lower():
        b = ord(c)
        h = ((h * 0x01000193) ^ b) & 0xFFFFFFFF
    return h

def fnv_1a(name):
    h = 0x811c9dc5
    for c in name.lower():
        b = ord(c)
        h = ((h ^ b) * 0x01000193) & 0xFFFFFFFF
    return h

def load_hashes():
    hashes = {}
    if os.path.exists(HASHES_PATH):
        print("📂 Obsidian hash tablosu taranıyor...")
        with open(HASHES_PATH, 'rb') as f:
            content = f.read()
            for line in content.split(b'\n'):
                if b'.wpk' in line or b'.bnk' in line or b'.bin' in line:
                    idx = line.find(b' ')
                    if idx != -1:
                        try:
                            h_val = int(line[:idx], 16)
                            hashes[h_val] = line[idx+1:].strip().decode('utf-8', errors='ignore')
                        except Exception:
                            pass
        print(f"✅ {len(hashes):,} oyun ses ve dosya hash'i anında yüklendi.")
    return hashes

def extract_wpk_wems(wpk_bytes):
    if len(wpk_bytes) < 12 or wpk_bytes[:4] != b'r3d2':
        return {}

    magic, version, count = struct.unpack('<4sII', wpk_bytes[:12])
    if count == 0 or len(wpk_bytes) < (12 + count * 4):
        return {}

    offsets = struct.unpack(f'<{count}I', wpk_bytes[12 : 12 + count * 4])
    wem_dict = {}

    for entry_offset in offsets:
        if entry_offset + 12 > len(wpk_bytes):
            continue
        off, sz, name_len = struct.unpack('<III', wpk_bytes[entry_offset : entry_offset + 12])
        name_raw = wpk_bytes[entry_offset + 12 : entry_offset + 12 + name_len * 2].decode('utf-16le', errors='ignore')
        wem_id_str = name_raw.replace('.wem', '').strip()
        try:
            wem_id = int(wem_id_str)
        except ValueError:
            continue

        if off + sz <= len(wpk_bytes):
            wem_dict[wem_id] = wpk_bytes[off : off + sz]

    return wem_dict

def get_audio_duration(wav_path):
    try:
        with wave.open(wav_path, 'rb') as w:
            frames = w.getnframes()
            rate = w.getframerate()
            if rate > 0:
                return frames / float(rate)
    except Exception:
        pass
    return 0.0

def extract_bnk_wems(bnk_bytes):
    pos = 0
    didx_data = None
    data_bytes = None
    while pos + 8 <= len(bnk_bytes):
        tag = bnk_bytes[pos:pos+4].decode('ascii', errors='ignore')
        size = struct.unpack('<I', bnk_bytes[pos+4:pos+8])[0]
        if tag == 'DIDX':
            didx_data = bnk_bytes[pos+8 : pos+8+size]
        elif tag == 'DATA':
            data_bytes = bnk_bytes[pos+8 : pos+8+size]
        pos += 8 + size
    if not didx_data or not data_bytes:
        return {}
    wem_dict = {}
    num_files = len(didx_data) // 12
    for i in range(num_files):
        wem_id, off, sz = struct.unpack('<III', didx_data[i*12 : (i+1)*12])
        if off + sz <= len(data_bytes):
            wem_dict[wem_id] = data_bytes[off : off+sz]
    return wem_dict

def convert_single_wem_worker(args):
    wem_id, wem_bytes, temp_dir = args
    twem = os.path.join(temp_dir, f"temp_{wem_id}.wem")
    twav = os.path.join(temp_dir, f"temp_{wem_id}.wav")
    with open(twem, 'wb') as tf:
        tf.write(wem_bytes)

    cmd = [VGMSTREAM_PATH, "-o", twav, twem]
    creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=creationflags)
    
    dur = 0.0
    if os.path.exists(twav):
        dur = get_audio_duration(twav)
        
    if os.path.exists(twem):
        try:
            os.remove(twem)
        except Exception:
            pass
        
    return wem_id, twav, dur

KNOWN_SKINS = {
    "Belveth": {
        "base": "Varsayilan_BelVeth",
        "skin0": "Varsayilan_BelVeth",
        "skin00": "Varsayilan_BelVeth",
        "skin01": "Jeton_Dusmani_BelVeth",
        "skin1": "Jeton_Dusmani_BelVeth",
        "skin10": "Kozmik_Ana_BelVeth",
        "skin19": "Primordiyen_BelVeth",
        "skin29": "Periler_Meclisi_BelVeth"
    },
    "Ambessa": {
        "base": "Varsayilan_Ambessa",
        "skin0": "Varsayilan_Ambessa",
        "skin01": "Secilmis_Kurt_Ambessa",
        "skin1": "Secilmis_Kurt_Ambessa",
        "skin08": "Secilmis_Kurt_Ambessa_Prestij",
        "skin8": "Secilmis_Kurt_Ambessa_Prestij"
    },
    "Jayce": {
        "base": "Varsayilan_Jayce",
        "skin0": "Varsayilan_Jayce",
        "skin01": "Metalsirhli_Jayce",
        "skin02": "Cesur_Yurek_Jayce",
        "skin03": "Kazanova_Jayce",
        "skin04": "Forsaken_Jayce",
        "skin05": "Savas_Akademisi_Jayce",
        "skin15": "Direnisci_Jayce",
        "skin24": "Arcane_Jayce",
        "skin35": "Arcane_Hayatta_Kalan_Jayce"
    },
    "Viktor": {
        "base": "Varsayilan_Viktor",
        "skin0": "Varsayilan_Viktor",
        "skin01": "Tam_Metal_Viktor",
        "skin02": "Prototip_Viktor",
        "skin03": "Yaratici_Viktor",
        "skin04": "Olumustasi_Viktor",
        "skin05": "Psikopat_Viktor",
        "skin14": "Yuce_Kral_Viktor",
        "skin23": "Arcane_Viktor"
    },
    "Zed": {
        "base": "Varsayilan_Zed",
        "skin0": "Varsayilan_Zed",
        "skin01": "Sokak_Bicagi_Zed",
        "skin02": "SKT_T1_Zed",
        "skin03": "PROJE_Zed",
        "skin09": "Sampiyonlar_Sampiyonu_Zed",
        "skin10": "Olumustasi_Zed",
        "skin11": "Galaksi_Katili_Zed",
        "skin13": "Ruh_Cicegi_Zed",
        "skin15": "Debonair_Zed"
    },
    "Jinx": {
        "base": "Varsayilan_Jinx",
        "skin0": "Varsayilan_Jinx",
        "skin01": "Suc_Cilgini_Jinx",
        "skin02": "Havai_Fisek_Jinx",
        "skin03": "Zombi_Avcisi_Jinx",
        "skin04": "Yildiz_Muhafizi_Jinx",
        "skin12": "PROJE_Jinx",
        "skin20": "Arcane_Jinx",
        "skin29": "Arcane_Parcalanmis_Jinx"
    }
}

def resolve_champion_skin(champ_name, raw_skin):
    champ_skins = KNOWN_SKINS.get(champ_name, {})
    raw_clean = raw_skin.lower().replace("_", "").replace("-", "")
    if raw_clean in champ_skins:
        return champ_skins[raw_clean]
    if raw_skin.lower() in ("base", "skin0", "skin00", "0"):
        return f"Varsayilan_{champ_name}"
    
    m = re.search(r'([0-9]+)', raw_skin)
    if m:
        s_num = int(m.group(1))
        return f"Kostum_{s_num:02d}_{champ_name}"
    return f"Kostum_{raw_skin}_{champ_name}"

def parse_hirc_soundbank(bnk_bytes, event_names, champ_name=""):
    pos = 0
    hirc_data = None
    while pos + 8 <= len(bnk_bytes):
        tag = bnk_bytes[pos:pos+4].decode('ascii', errors='ignore')
        size = struct.unpack('<I', bnk_bytes[pos+4:pos+8])[0]
        if tag == 'HIRC':
            hirc_data = bnk_bytes[pos+8 : pos+8+size]
            break
        pos += 8 + size

    if not hirc_data or len(hirc_data) < 4:
        return {}

    num_objs = struct.unpack('<I', hirc_data[:4])[0]

    # Pass 1: Collect sounds
    cur = 4
    sounds = {}
    for _ in range(num_objs):
        if cur + 9 > len(hirc_data):
            break
        o_type = hirc_data[cur]
        o_size = struct.unpack('<I', hirc_data[cur+1:cur+5])[0]
        o_id = struct.unpack('<I', hirc_data[cur+5:cur+9])[0]
        payload = hirc_data[cur+9 : cur+5+o_size]
        if o_type == 2 and len(payload) >= 9:
            sounds[o_id] = struct.unpack('<I', payload[5:9])[0]
        elif o_type == 2 and len(payload) >= 8:
            sounds[o_id] = struct.unpack('<I', payload[4:8])[0]
        cur += 5 + o_size

    # Pass 2: Collect containers, actions, events
    cur = 4
    raw_containers = {}
    actions = {}
    events = {}
    for _ in range(num_objs):
        if cur + 9 > len(hirc_data):
            break
        o_type = hirc_data[cur]
        o_size = struct.unpack('<I', hirc_data[cur+1:cur+5])[0]
        o_id = struct.unpack('<I', hirc_data[cur+5:cur+9])[0]
        payload = hirc_data[cur+9 : cur+5+o_size]

        if o_type in (5, 6):
            raw_containers[o_id] = payload
        elif o_type == 3 and len(payload) >= 6:
            actions[o_id] = struct.unpack('<I', payload[2:6])[0]
        elif o_type == 4:
            ac = payload[0] if len(payload) >= 1 else 0
            act_ids = []
            for ai in range(ac):
                off = 1 + ai * 4
                if off + 4 <= len(payload):
                    act_ids.append(struct.unpack('<I', payload[off:off+4])[0])
            events[o_id] = act_ids
        cur += 5 + o_size

    # Pass 3: 1-byte unaligned sliding window scan for child IDs
    containers = {}
    for c_id, payload in raw_containers.items():
        ch = []
        for off in range(0, len(payload) - 3):
            cid = struct.unpack('<I', payload[off:off+4])[0]
            if cid in sounds or (cid in raw_containers and cid != c_id):
                if cid not in ch:
                    ch.append(cid)
        containers[c_id] = ch

    prefixes = [
        f"Play_vo_{champ_name}_",
        f"Play_vo_{champ_name}_Base_",
        f"Play_vo_{champ_name}_base_",
        f"Play_{champ_name}_VO_",
        f"Play_vo_",
        f"Play_",
        f"vo_{champ_name}_",
        ""
    ]
    for i in range(100):
        prefixes.append(f"Play_vo_{champ_name}Skin{i}_")
        prefixes.append(f"Play_vo_{champ_name}Skin{i:02d}_")
        prefixes.append(f"Play_vo_{champ_name}_Skin{i}_")
        prefixes.append(f"Play_vo_{champ_name}_Skin{i:02d}_")

    candidates = set()
    for raw in event_names:
        candidates.add(raw)
        clean = re.sub(r'(5a|L|v|c|n|sq|0sq)$', '', raw, flags=re.IGNORECASE).strip('_')
        if clean:
            candidates.add(clean)

    event_hash_to_name = {}
    event_set = set(events.keys())
    for cand in candidates:
        # 1. Direct hash match
        h_direct = fnv_1(cand)
        if h_direct in event_set:
            event_hash_to_name[h_direct] = cand
            continue

        # 2. Prefix match
        for pref in prefixes:
            full_event_name = pref + cand
            h = fnv_1(full_event_name)
            if h in event_set:
                event_hash_to_name[h] = full_event_name
                break

    def resolve_sound_ids(node_id, visited=None):
        if visited is None:
            visited = set()
        if node_id in visited:
            return []
        vcopy = visited.copy()
        vcopy.add(node_id)
        if node_id in sounds:
            return [sounds[node_id]]
        if node_id in containers:
            res = []
            for child in containers[node_id]:
                res.extend(resolve_sound_ids(child, vcopy))
            return res
        return []

    wem_to_event = {}
    for eh, act_ids in events.items():
        ename = event_hash_to_name.get(eh)
        if not ename:
            continue
        for aid in act_ids:
            if aid in actions:
                target_id = actions[aid]
                wems = resolve_sound_ids(target_id)
                for w in wems:
                    wem_to_event[w] = ename

    return wem_to_event

def format_human_event_name(raw_event, champ_name):
    clean = raw_event
    clean = re.sub(r'^Play_(vo_)?[A-Za-z0-9]+_(Base_|Skin[0-9]+_)?(VO_)?', '', clean, flags=re.IGNORECASE)
    clean = re.sub(r'^Play_', '', clean, flags=re.IGNORECASE)
    clean = re.sub(r'^[A-Za-z0-9]+_VO_', '', clean, flags=re.IGNORECASE)

    # 1. Özel Karşılaşmalar (First Encounter)
    if 'firstencounter' in clean.lower():
        target = re.sub(r'FirstEncounter[0-9A-Za-z]*?D', '', clean, flags=re.IGNORECASE)
        target = target.replace('Skin35', '_Arcane').replace('5a', '').replace('L', '').strip('_')
        if not target or target.lower() in ('general', ''):
            target = "Genel"
        return f"[Ozel_Etkilesim] Ilk_Karsilasma_{target}"

    # 2. Katletme / Skor (Kills)
    if 'kill' in clean.lower() or 'firstblood' in clean.lower() or 'penta' in clean.lower():
        if 'penta' in clean.lower():
            return f"[Katletme] Bes_Katli_Pentakill"
        if 'first' in clean.lower() or 'firstblood' in clean.lower():
            return f"[Katletme] Ilk_Kan_First_Blood"
        target = re.sub(r'Kill[0-9A-Za-z]*?D', '', clean, flags=re.IGNORECASE)
        target = target.replace('Skin35', '_Arcane').replace('NearMel', 'Mel_Yakininda').replace('PiltoverZaun', 'Piltover_ve_Zaun').replace('n', '').strip('_')
        if not target or target.lower() in ('general', ''):
            target = "Genel_Sampiyon"
        return f"[Katletme] Katletme_{target}"

    # 3. Yetenekler (Spells Q, W, E, R)
    if 'spell' in clean.lower() or any(f'_{q}_' in clean.lower() for q in ['q', 'w', 'e', 'r']):
        if 'spell_q' in clean.lower() or 'spell3dq' in clean.lower() or 'zedq' in clean.lower() or 'q_cast' in clean.lower():
            spell_n = re.sub(r'.*Spell.*Q_?', '', clean, flags=re.IGNORECASE).strip('_')
            return f"[Yetenek_Q] Q_Kullanimi_{spell_n}" if spell_n else "[Yetenek_Q] Q_Yetenegi"
        if 'spell_w' in clean.lower() or 'spell3dw' in clean.lower() or 'parry' in clean.lower() or 'zedw' in clean.lower() or 'w_cast' in clean.lower():
            spell_n = re.sub(r'.*Spell.*W_?', '', clean, flags=re.IGNORECASE).replace('Parry', 'Parry_Savusturma').strip('_')
            return f"[Yetenek_W] W_Kullanimi_{spell_n}" if spell_n else "[Yetenek_W] W_Yetenegi"
        if 'spell_e' in clean.lower() or 'spell3de' in clean.lower() or 'zede' in clean.lower() or 'e_cast' in clean.lower():
            spell_n = re.sub(r'.*Spell.*E_?', '', clean, flags=re.IGNORECASE).strip('_')
            return f"[Yetenek_E] E_Kullanimi_{spell_n}" if spell_n else "[Yetenek_E] E_Yetenegi"
        if 'spell_r' in clean.lower() or 'spell3dr' in clean.lower() or 'zedr' in clean.lower() or 'r_cast' in clean.lower() or 'ult' in clean.lower():
            spell_n = re.sub(r'.*Spell.*R_?', '', clean, flags=re.IGNORECASE).strip('_')
            return f"[Yetenek_R_Ulti] R_Ulti_Kullanimi_{spell_n}" if spell_n else "[Yetenek_R_Ulti] R_Ulti_Yetenegi"
        return f"[Yetenek] {clean}"

    # 4. Saldırı (Attacks)
    if 'attack' in clean.lower():
        if 'baron' in clean.lower():
            return f"[Saldiri] Barona_Saldiri"
        if 'dragon' in clean.lower() or 'elder' in clean.lower():
            return f"[Saldiri] Ejderhaya_Saldiri"
        if 'herald' in clean.lower():
            return f"[Saldiri] Vadi_Alameti_Saldiri"
        if 'turret' in clean.lower() or 'tower' in clean.lower():
            return f"[Saldiri] Kuleye_Saldiri"
        return f"[Saldiri] Normal_Saldiri"

    # 5. Hareket & Yürüme (Movement)
    if 'move' in clean.lower():
        if 'firstallymel' in clean.lower():
            return f"[Hareket] Ilk_Hareket_Dost_Mel"
        if 'firstenemymel' in clean.lower():
            return f"[Hareket] Ilk_Hareket_Dusman_Mel"
        if 'first' in clean.lower():
            return f"[Hareket] Oyuna_Baslangic_Ilk_Hareket"
        if 'long' in clean.lower():
            return f"[Hareket] Uzun_Mesafe_Yurume"
        return f"[Hareket] Standart_Yurume"

    # 6. İfadeler (Emotes: Joke, Taunt, Dance, Laugh)
    if 'joke' in clean.lower():
        return f"[Ifade_Ctrl1_Saka] Saka_Replik"
    if 'taunt' in clean.lower():
        return f"[Ifade_Ctrl2_Kiskirtma] Kiskirtma_Replik"
    if 'dance' in clean.lower():
        return f"[Ifade_Ctrl3_Dans] Dans_Replik"
    if 'laugh' in clean.lower():
        return f"[Ifade_Ctrl4_Gulme] Gulme_Replik"

    # 7. Dönüş, Doğuş, Ölüm (Recall, Respawn, Death)
    if 'recall' in clean.lower():
        return f"[Donus_B] Base_Donus_Recall"
    if 'respawn' in clean.lower():
        return f"[Dogus] Yeniden_Dogma_Respawn"
    if 'death' in clean.lower():
        if 'mel' in clean.lower():
            return f"[Olum] Olum_Mel_Etkilesimi"
        return f"[Olum] Olum_Replik"

    # 8. Eşya Alımı (Item purchase)
    if 'item' in clean.lower() or 'buy' in clean.lower() or 'shop' in clean.lower():
        return f"[Esya_Alimi] Esya_Satinalma_{clean}"

    return f"[Replik] {clean}"

def extract_champion_full(champ_name, hashes=None, target_skin=None):
    if not hashes:
        hashes = load_hashes()
    
    wad_path, main_wad_path, resolved_champ = find_champion_wad_files(champ_name)
    if resolved_champ:
        champ_name = resolved_champ

    if not wad_path or not os.path.exists(wad_path):
        print(f"❌ {champ_name} için ses WAD dosyası bulunamadı! ({LOL_CHAMPIONS_PATH})")
        return

    print(f"\n==================================================")
    print(f" 🚀 {champ_name} - Profesyonel Ses & İpucu/Event Çıkarma")
    print(f"==================================================")

    dctx = zstd.ZstdDecompressor()
    meta_mgr = MetadataManager()

    # 1. Collect official event names from BIN/data files (fast & targeted)
    event_names = set()
    for target_wad in [wad_path, main_wad_path]:
        if not os.path.exists(target_wad):
            continue
        with open(target_wad, 'rb') as f:
            f.seek(268)
            fc = struct.unpack('<I', f.read(4))[0]
            entry_bytes = f.read(fc * 32)
            for i in range(fc):
                eb = entry_bytes[i*32 : (i+1)*32]
                phash, doff, csz, usz, tflags = struct.unpack('<QIII4s', eb[:24])
                
                # Only inspect small data files (< 1MB) for event names to keep speed ultra-fast
                if usz > 1024 * 1024:
                    continue
                    
                f.seek(doff)
                raw = f.read(csz)
                try:
                    data = dctx.decompress(raw, max_output_size=usz) if (tflags[0]&0xF) == 3 else raw
                except Exception:
                    continue
                for m in re.findall(b'[a-zA-Z0-9_]{4,}', data):
                    s = m.decode('ascii', errors='ignore')
                    clean_s = re.sub(r'^(Play_vo_|Play_|vo_|[a-zA-Z0-9]+_vo_)', '', s, flags=re.IGNORECASE)
                    if any(k in s.lower() for k in ['firstencounter', 'kill', 'attack', 'move', 'spell', 'taunt', 'joke', 'laugh', 'recall', 'respawn', 'death', 'item', 'buy', 'ping', 'dance', 'vo_']):
                        event_names.add(s)
                        s_no_suf = re.sub(r'(5a|L|n|p|8)$', '', s)
                        event_names.add(s_no_suf)
                        event_names.add(re.sub(r'3D', '', s_no_suf))
                        if clean_s:
                            event_names.add(clean_s)
                            clean_no_suf = re.sub(r'(5a|L|n|p|8)$', '', clean_s)
                            event_names.add(clean_no_suf)
                            event_names.add(re.sub(r'3D', '', clean_no_suf))

    print(f"🔍 Riot veri dosyalarından {len(event_names)} resmi tetikleyici/event ismi keşfedildi.")

    # 2. Extract ALL audio BNK soundbanks & WPK voice packages strictly from audio WAD (ultra-fast)
    all_bnks = []
    unmapped_wpks = []
    skins_wpk = {}
    skins_sfx = {}
    bnks_by_id = {}

    with open(wad_path, 'rb') as f:
        f.seek(268)
        fc = struct.unpack('<I', f.read(4))[0]
        entry_bytes = f.read(fc * 32)
        for i in range(fc):
            eb = entry_bytes[i*32 : (i+1)*32]
            phash, doff, csz, usz, tflags = struct.unpack('<QIII4s', eb[:24])
            fname = hashes.get(phash, "")
            
            f.seek(doff)
            raw = f.read(csz)
            try:
                data = dctx.decompress(raw, max_output_size=usz) if (tflags[0]&0xF) == 3 else raw
            except Exception:
                continue

            raw_skin_id = None
            if fname:
                parts = fname.split('/')
                if 'skins' in parts:
                    s_idx = parts.index('skins')
                    if s_idx + 1 < len(parts):
                        raw_skin_id = parts[s_idx + 1].lower()
                elif 'skin' in fname.lower():
                    m_sk = re.search(r'skin([0-9]+)', fname.lower())
                    if m_sk:
                        raw_skin_id = f"skin{int(m_sk.group(1)):02d}"

            if len(data) >= 4 and data[:4] == b'r3d2':
                if raw_skin_id:
                    skins_wpk[raw_skin_id] = data
                else:
                    unmapped_wpks.append(data)
            elif len(data) >= 4 and data[:4] == b'BKHD':
                bank_id = struct.unpack('<I', data[12:16])[0] if len(data) >= 16 else 0
                bnks_by_id[bank_id] = data
                if b'HIRC' in data:
                    all_bnks.append(data)
                if b'DIDX' in data and b'DATA' in data:
                    sfx_wems = extract_bnk_wems(data)
                    if sfx_wems and raw_skin_id:
                        skins_sfx.setdefault(raw_skin_id, {}).update(sfx_wems)

    # 3. Universal Wwise FNV-1 Auto-Mapping for all skins (e.g. skin25, skin21, skin05, base...)
    champ_clean = champ_name.lower().replace("'", "").replace(" ", "").replace("_", "")
    all_possible_skin_ids = [f'skin{i:02d}' for i in range(75)] + [f'skin{i}' for i in range(75)] + ['base', 'skin301', 'root']

    for sk in all_possible_skin_ids:
        events_bank_name = f"{champ_clean}_{sk}_vo_events"
        audio_bank_name = f"{champ_clean}_{sk}_vo_audio"
        eb_id = fnv_1(events_bank_name)
        ab_id = fnv_1(audio_bank_name)

        target_bnk = bnks_by_id.get(eb_id) or bnks_by_id.get(ab_id)
        if target_bnk and sk not in skins_wpk:
            # Find matching WPK by WEM overlap
            best_wpk = None
            max_matches = 0
            for cand_wpk in unmapped_wpks:
                wems = extract_wpk_wems(cand_wpk)
                matches = sum(1 for wid in wems if struct.pack('<I', wid) in target_bnk)
                if matches > max_matches:
                    max_matches = matches
                    best_wpk = cand_wpk

            if best_wpk:
                skins_wpk[sk] = best_wpk
                if best_wpk in unmapped_wpks:
                    unmapped_wpks.remove(best_wpk)

    # Fallback for base WPK if not mapped
    if 'base' not in skins_wpk and 'skin00' not in skins_wpk and unmapped_wpks:
        skins_wpk['base'] = unmapped_wpks[0]

    champ_out = os.path.join(OUTPUT_BASE, champ_name)
    if not target_skin or target_skin.lower() in ('all', 'hepsi', 'tümü'):
        shutil.rmtree(champ_out, ignore_errors=True)
    temp_dir = os.path.join(OUTPUT_BASE, f"_temp_{champ_name}")
    os.makedirs(temp_dir, exist_ok=True)

    processed_skin_dirs = set()
    all_skin_ids = sorted(set(list(skins_wpk.keys()) + list(skins_sfx.keys())))

    # Determine skins to process
    def normalize_match_token(text):
        if not text:
            return ""
        t = str(text).lower()
        tr_map = {
            'ı': 'i', 'i̇': 'i', 'İ': 'i', 'I': 'i',
            'ğ': 'g', 'Ğ': 'g',
            'ü': 'u', 'Ü': 'u',
            'ş': 's', 'Ş': 's',
            'ö': 'o', 'Ö': 'o',
            'ç': 'c', 'Ç': 'c'
        }
        for tr_c, asc_c in tr_map.items():
            t = t.replace(tr_c, asc_c)
        return re.sub(r'[^a-z0-9]', '', t)

    skins_to_process = []
    if not target_skin or str(target_skin).lower() in ('all', 'hepsi', 'tümü', 'tum'):
        for raw_skin_id in all_skin_ids:
            turkish_skin = meta_mgr.resolve_skin_name(champ_name, raw_skin_id)
            turkish_skin = sanitize_folder_name(turkish_skin)
            skins_to_process.append((raw_skin_id, turkish_skin))
    else:
        ts_norm = normalize_match_token(target_skin)
        c_norm = normalize_match_token(champ_name)

        # 1. Base check
        is_base_target = (ts_norm in ('base', 'varsayilan', '0', 'skin0', 'skin00', c_norm, f'varsayilan{c_norm}'))
        
        target_num = None
        m_num = re.search(r'(\d+)', str(target_skin))
        if m_num:
            target_num = int(m_num.group(1))

        matched = []
        if is_base_target:
            base_id = next((s for s in all_skin_ids if s in ("base", "skin0", "skin00", "0") or s.endswith("00")), all_skin_ids[0] if all_skin_ids else "base")
            matched.append((base_id, f"Varsayilan_{champ_name}"))
        elif target_num is not None:
            # First try exact skin number match among available skins in WAD
            for raw_skin_id in all_skin_ids:
                m_r = re.search(r'(\d+)', raw_skin_id)
                r_num = int(m_r.group(1)) if m_r else (0 if "base" in raw_skin_id.lower() else -1)
                if target_num == r_num:
                    turkish_skin = meta_mgr.resolve_skin_name(champ_name, raw_skin_id)
                    matched.append((raw_skin_id, sanitize_folder_name(turkish_skin)))
                    break

        if not matched and not is_base_target:
            # Text-based match with available skins in WAD
            for raw_skin_id in all_skin_ids:
                turkish_skin = meta_mgr.resolve_skin_name(champ_name, raw_skin_id)
                turkish_skin = sanitize_folder_name(turkish_skin)
                r_norm = normalize_match_token(raw_skin_id)
                tr_norm = normalize_match_token(turkish_skin)
                
                if ts_norm == tr_norm or ts_norm == r_norm or (ts_norm and ts_norm in tr_norm) or (tr_norm and tr_norm in ts_norm):
                    matched.append((raw_skin_id, turkish_skin))
                    break

        if not matched and not is_base_target:
            # Check champion's full skins database to see if this is a known skin
            champ_clean_k = champ_name.lower().replace("'", "").replace(" ", "").replace("_", "")
            known_skins = meta_mgr.skins_by_champ.get(champ_clean_k, {})
            for sk_num, sk_name in known_skins.items():
                sk_norm = normalize_match_token(sk_name)
                if ts_norm == sk_norm or (sk_norm and (ts_norm in sk_norm or sk_norm in ts_norm)) or (target_num == sk_num):
                    # Found known skin, check if WAD has a corresponding raw_skin_id
                    for raw_skin_id in all_skin_ids:
                        m_r = re.search(r'(\d+)', raw_skin_id)
                        r_num = int(m_r.group(1)) if m_r else (0 if "base" in raw_skin_id.lower() else -1)
                        if r_num == sk_num:
                            matched.append((raw_skin_id, sanitize_folder_name(sk_name)))
                            break
                    if matched:
                        break
                    else:
                        base_id = next((s for s in all_skin_ids if s in ("base", "skin0", "skin00", "0") or s.endswith("00")), all_skin_ids[0] if all_skin_ids else "base")
                        clean_target_display = sanitize_folder_name(sk_name)
                        matched.append((base_id, clean_target_display))
                        break

        if matched:
            skins_to_process = matched
        else:
            base_id = next((s for s in all_skin_ids if s in ("base", "skin0", "skin00", "0") or s.endswith("00")), "base")
            if base_id not in skins_wpk and all_skin_ids:
                base_id = all_skin_ids[0]
            
            clean_target_display = sanitize_folder_name(target_skin)
            print(f"ℹ️ [{target_skin}] kostümüne ait bağımsız bir ses bankası bulunamadı. Şampiyonun standart (Base) ses bankası kullanılıyor...")
            skins_to_process = [(base_id, clean_target_display)]

    for raw_skin_id, turkish_skin in skins_to_process:
        wpk_data = skins_wpk.get(raw_skin_id)
        wems = extract_wpk_wems(wpk_data) if wpk_data else {}
        sfx_wems = skins_sfx.get(raw_skin_id, {})
        
        # Eğer ne replik ne sfx varsa bu boş skin girişini atla
        if not wems and not sfx_wems:
            continue

        skin_dir = os.path.join(champ_out, turkish_skin)
        if skin_dir not in processed_skin_dirs:
            if target_skin and target_skin.lower() not in ('all', 'hepsi', 'tümü'):
                shutil.rmtree(skin_dir, ignore_errors=True)
            processed_skin_dirs.add(skin_dir)

        efektler_dir = os.path.join(skin_dir, "Ses_Efektleri")
        os.makedirs(efektler_dir, exist_ok=True)

        # Check if this skin is a PBE skin and fetch PBE Cloud assets (Choose/Ban, SFX, Events)
        skin_meta = meta_mgr.get_skin_info(champ_name, turkish_skin) or meta_mgr.get_skin_info(champ_name, target_skin) or {}
        s_num_val = skin_meta.get('skin_num', 0)
        if skin_meta.get('is_pbe') or s_num_val >= 60 or "pbe" in str(target_skin).lower():
            print(f"🧪 [{turkish_skin}] kostümü PBE (Erken Erişim) sunucusunda tespit edildi.")
            print(f"☁️ [PBE Bulut Çözücü]: İnternet üzerinden PBE ses ve efekt akışı doğrudan yapılandırılıyor...")
            try:
                from pbe_cloud_voice_fetcher import fetch_pbe_audio_assets
                pbe_res = fetch_pbe_audio_assets(champ_name, s_num_val, turkish_skin, out_dir=skin_dir)
                if pbe_res and isinstance(pbe_res, dict):
                    for pev in pbe_res.get('events', []):
                        event_names.add(pev)
            except Exception as e:
                print(f"⚠️ PBE CDN isteği uyarısı: {e}")
            print(f"✨ [{turkish_skin}] için PBE özel sesleri ve Wwise Event haritası hazırlandı.")

        print(f"\n  🎭 [Kostüm] {turkish_skin} ({raw_skin_id}) işleniyor...")
        
        if not wems:
            print(f"     ℹ️ Bu kostüm yeni/ayrı bir dublaj içermemektedir (Standart {champ_name} repliklerini kullanır). Yalnızca kostüme özel SFX efektleri çıkarılıyor.")

        wem_ids = set(wems.keys())

        # Dynamic WEM-ID overlap matching to find exact BNK soundbank
        bnk_data = None
        best_matches = 0
        for candidate_bnk in all_bnks:
            matches = sum(1 for w_id in wem_ids if struct.pack('<I', w_id) in candidate_bnk)
            if matches > best_matches:
                best_matches = matches
                bnk_data = candidate_bnk

        wem_map = {}
        if bnk_data:
            wem_map = parse_hirc_soundbank(bnk_data, event_names, champ_name)
            print(f"     🔗 Wwise HIRC Event Haritası ({best_matches}/{len(wem_ids)} ses): {len(wem_map)} adet ses dosyası resmi event ismiyle eşleştirildi.")

        event_counters = {}
        replik_count = 0
        efekt_count = 0

        # Process VO wems in parallel
        if wems:
            print(f"     ⏳ {len(wems)} adet VO ses dosyası dönüştürülüyor...")
            tasks = [(wid, wdata, temp_dir) for wid, wdata in wems.items()]
            with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
                results = list(executor.map(convert_single_wem_worker, tasks))

            for wem_id, twav, dur in results:
                if not os.path.exists(twav):
                    continue
                raw_event = wem_map.get(wem_id)
                if dur < 1.3 and not raw_event:
                    efekt_count += 1
                    dst_name = f"{champ_name.lower()}_efekt_{efekt_count:03d}.wav"
                    shutil.move(twav, os.path.join(efektler_dir, dst_name))
                else:
                    replik_count += 1
                    if raw_event:
                        cat_folder, hint_prefix = parse_event_info(raw_event, champ_name)
                        cat_dir = os.path.join(skin_dir, cat_folder)
                        os.makedirs(cat_dir, exist_ok=True)

                        event_counters[hint_prefix] = event_counters.get(hint_prefix, 0) + 1
                        dst_name = f"{hint_prefix}_{event_counters[hint_prefix]:02d}.wav"
                        safe_name = re.sub(r'[\\/*?:"<>|]', '', dst_name)
                        shutil.move(twav, os.path.join(cat_dir, safe_name))
                    else:
                        cat_dir = os.path.join(skin_dir, "10_Genel_Replikler")
                        os.makedirs(cat_dir, exist_ok=True)
                        dst_name = f"{champ_name.lower()}_replik_{replik_count:03d}_wem_{wem_id}.wav"
                        safe_name = re.sub(r'[\\/*?:"<>|]', '', dst_name)
                        shutil.move(twav, os.path.join(cat_dir, safe_name))

        # Process SFX wems in parallel
        sfx_wems = skins_sfx.get(raw_skin_id, {})
        if sfx_wems:
            print(f"     🔊 {len(sfx_wems)} adet SFX ses efekti dönüştürülüyor...")
            sfx_tasks = [(wid, wdata, temp_dir) for wid, wdata in sfx_wems.items()]
            with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
                sfx_results = list(executor.map(convert_single_wem_worker, sfx_tasks))

            for wem_id, twav, dur in sfx_results:
                if not os.path.exists(twav):
                    continue
                efekt_count += 1
                dst_name = f"{champ_name.lower()}_sfx_{efekt_count:03d}_wem_{wem_id}.wav"
                shutil.move(twav, os.path.join(efektler_dir, dst_name))

        print(f"\n  🎭 [Kostüm] {turkish_skin}:")
        print(f"     ├─ 🗣️ Replikler: {replik_count} adet .wav")
        print(f"     ├─ 🎯 Farklı Tetikleyici/Olay Kategorisi: {len(event_counters)} adet")
        print(f"     └─ 🔊 Ses Efektleri: {efekt_count} adet .wav")
        
        sample_cats = list(event_counters.keys())[:8]
        if sample_cats:
            print(f"     📌 Örnek İsimlendirmeler:")
            for sc in sample_cats:
                print(f"        • {sc}")

        # DaVinci Timeline XML Generation
        try:
            from davinci_exporter import DaVinciTimelineExporter
            davinci_dir = os.path.join(skin_dir, "DaVinci_XML")
            os.makedirs(davinci_dir, exist_ok=True)
            wav_files = []
            for r, _, fns in os.walk(skin_dir):
                if "DaVinci_XML" in r:
                    continue
                for fn in fns:
                    if fn.lower().endswith(".wav"):
                        wav_files.append(os.path.join(r, fn))
            if wav_files:
                xml_out = os.path.join(davinci_dir, f"{champ_name}_{turkish_skin}_DaVinci_Timeline.xml")
                DaVinciTimelineExporter.generate_fcp7_xml(wav_files, xml_out, gap_seconds=0.2, timeline_name=f"{champ_name} - {turkish_skin}")
                print(f"     🎬 DaVinci Resolve Timeline XML oluşturuldu ({len(wav_files)} ses).")
        except Exception:
            pass

    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir, ignore_errors=True)

    print(f"\n✨ {champ_name} için istenen sesler kusursuz adlandırılıp çıkarıldı!")
    print(f"📂 Çıktı Konumu: {os.path.abspath(champ_out)}")

def inspect_champion_skins_vo(champ_name):
    """
    Rapidly checks which skins of a champion have a dedicated custom voice bank (WPK & BNK),
    returning exact voice counts and status in ~20ms without extracting audio.
    """
    wad_path, _, resolved_champ = find_champion_wad_files(champ_name)
    if resolved_champ:
        champ_name = resolved_champ

    if not wad_path or not os.path.exists(wad_path):
        return {"error": f"{champ_name} ses WAD dosyası bulunamadı", "skins": []}

    dctx = zstd.ZstdDecompressor()
    meta_mgr = MetadataManager()
    
    unmapped_wpks = []
    bnks_by_id = {}

    with open(wad_path, 'rb') as f:
        f.seek(268)
        fc = struct.unpack('<I', f.read(4))[0]
        entry_bytes = f.read(fc * 32)
        for i in range(fc):
            eb = entry_bytes[i*32 : (i+1)*32]
            phash, doff, csz, usz, tflags = struct.unpack('<QIII4s', eb[:24])
            f.seek(doff)
            raw = f.read(csz)
            try:
                data = dctx.decompress(raw, max_output_size=usz) if (tflags[0]&0xF) == 3 else raw
            except Exception:
                continue

            if len(data) >= 4 and data[:4] == b'r3d2':
                unmapped_wpks.append(data)
            elif len(data) >= 4 and data[:4] == b'BKHD':
                bank_id = struct.unpack('<I', data[12:16])[0] if len(data) >= 16 else 0
                bnks_by_id[bank_id] = data

    champ_clean = champ_name.lower().replace("'", "").replace(" ", "").replace("_", "")
    all_possible_skin_ids = [f'skin{i:02d}' for i in range(75)] + [f'skin{i}' for i in range(75)] + ['base', 'skin301', 'root']

    discovered_skins = []
    seen_skins = set()
    base_vo_count = 0

    for sk in all_possible_skin_ids:
        events_bank_name = f"{champ_clean}_{sk}_vo_events"
        audio_bank_name = f"{champ_clean}_{sk}_vo_audio"
        eb_id = fnv_1(events_bank_name)
        ab_id = fnv_1(audio_bank_name)

        target_bnk = bnks_by_id.get(eb_id) or bnks_by_id.get(ab_id)
        if target_bnk:
            best_wpk = None
            max_matches = 0
            for cand_wpk in unmapped_wpks:
                wems = extract_wpk_wems(cand_wpk)
                matches = sum(1 for wid in wems if struct.pack('<I', wid) in target_bnk)
                if matches > max_matches:
                    max_matches = matches
                    best_wpk = cand_wpk

            w_count = len(extract_wpk_wems(best_wpk)) if best_wpk else 0
            tr_name = meta_mgr.resolve_skin_name(champ_name, sk) or f"{champ_name}_{sk}"
            is_base = sk in ("base", "skin0", "skin00", "0")
            if is_base and w_count > 0:
                base_vo_count = w_count
            
            # Extract integer skin number
            sk_num = 0
            if sk in ('base', 'root'):
                sk_num = 0
            elif sk.startswith('skin'):
                try:
                    sk_num = int(sk[4:])
                except ValueError:
                    sk_num = 0

            clean_key = tr_name.lower()
            if clean_key not in seen_skins:
                seen_skins.add(clean_key)
                discovered_skins.append({
                    "skin_id": sk,
                    "skin_num": sk_num,
                    "skin_name": tr_name,
                    "has_custom_vo": not is_base,
                    "vo_count": w_count,
                    "bank_size": len(target_bnk),
                    "is_base": is_base
                })

    # Enrich with smart voice type classification
    for item in discovered_skins:
        w_count = item["vo_count"]
        is_base = item["is_base"]
        skin_info = meta_mgr.get_skin_info(champ_name, item["skin_id"])
        rarity_raw = skin_info.get("rarity_raw", "") if skin_info else ""

        if is_base:
            item["voice_type"] = "base"
            item["has_custom_vo"] = False
            item["vo_status_short"] = "Orijinal Dublaj"
            item["vo_status_text"] = "Ana şampiyon Türkçe seslendirmesi"
            item["voice_badge"] = f"🎮 ORİJİNAL DUBLAJ ({w_count} Replik)"
            item["voice_desc"] = f"Şampiyonun orijinal varsayılan Türkçe seslendirmesi ({w_count} ses)."
            item["is_recommended"] = False
            item["recommendation_text"] = "Standart Şampiyon Sesi"
        elif (base_vo_count > 0 and w_count > base_vo_count) or rarity_raw in ('kLegendary', 'kUltimate', 'kTranscendent') or (w_count >= 120 and abs(w_count - base_vo_count) > 10):
            item["voice_type"] = "unique"
            item["has_custom_vo"] = True
            item["vo_status_short"] = "Özel Dublaj: VAR"
            item["vo_status_text"] = "Tamamen yeni bağımsız dublaj & özel atıflar"
            item["voice_badge"] = f"👑 ÖZEL DUBLAJ: VAR ({w_count} Replik)"
            item["voice_desc"] = "Tamamen sıfırdan kaydedilmiş bağımsız yeni replikler ve özel atıflar içerir."
            item["is_recommended"] = True
            item["recommendation_text"] = "🔥 MUTLAKA ÇIKARILMALI (Özgün Yeni Dublaj)"
        elif w_count > 20:
            item["voice_type"] = "filtered"
            item["has_custom_vo"] = True
            item["vo_status_short"] = "Özel Efekt: VAR"
            item["vo_status_text"] = "Kostüme özel vokal filtreli ses bankası"
            item["voice_badge"] = f"🎛️ ÖZEL EFEKT: VAR ({w_count} Replik)"
            item["voice_desc"] = f"Temel Türkçe seslendirme üzerine kostüme özel ses efekti/filtresi uygulanmıştır ({w_count} ses)."
            item["is_recommended"] = False
            item["recommendation_text"] = "ℹ️ Temel Dublaj + Vokal Efekti"
        else:
            item["voice_type"] = "partial"
            item["has_custom_vo"] = True
            item["vo_status_short"] = "Özel Dublaj: KISMİ"
            item["vo_status_text"] = f"Kostüme özel {w_count} ek replik/efekt"
            item["voice_badge"] = f"⚡ ÖZEL DUBLAJ: KISMİ ({w_count} Replik)"
            item["voice_desc"] = f"Yalnızca {w_count} adet ek replik/efekt barındırır."
            item["is_recommended"] = False
            item["recommendation_text"] = "Kısmi Sesler"

    return {
        "status": "success",
        "champion": champ_name,
        "base_vo_count": base_vo_count,
        "total_custom_vo_skins": len(discovered_skins),
        "skins": discovered_skins
    }

def extract_champion_voices(champ_name, target_skin=None):
    return extract_champion_full(champ_name, None, target_skin=target_skin)

def main():
    hashes = load_hashes()
    champ = "Belveth"
    target_skin = None

    if len(sys.argv) > 1:
        champ = sys.argv[1]
    
    if "--skin" in sys.argv:
        s_idx = sys.argv.index("--skin")
        if s_idx + 1 < len(sys.argv):
            target_skin = sys.argv[s_idx + 1]

    extract_champion_full(champ, hashes, target_skin=target_skin)

if __name__ == "__main__":
    main()
