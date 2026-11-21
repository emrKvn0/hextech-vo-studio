import os
import sys
import re
import wave
import struct
import shutil
import hashlib
import subprocess
import functools
import concurrent.futures
import zstandard as zstd
from metadata_manager import MetadataManager

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

import lol_voice_extractor_expert as voice_extractor

HASHES_PATH = r"C:\Users\emrKvn\Downloads\Obsidian_5.1.8\hashes\hashes.game.txt"
LOL_CHAMPIONS_PATH = voice_extractor.LOL_CHAMPIONS_PATH
find_champion_wad_files = voice_extractor.find_champion_wad_files
VGMSTREAM_PATH = get_vgmstream_path()
OUTPUT_BASE = get_output_base()

def fnv_1(name):
    h = 0x811c9dc5
    for c in name.lower():
        b = ord(c)
        h = ((h * 0x01000193) ^ b) & 0xFFFFFFFF
    return h

def load_hashes():
    hashes = {}
    if os.path.exists(HASHES_PATH):
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
        try:
            wem_id = int(name_raw.replace('.wem', '').strip())
            if off + sz <= len(wpk_bytes):
                wem_dict[wem_id] = wpk_bytes[off : off + sz]
        except ValueError:
            continue

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

def parse_hirc_soundbank(bnk_bytes, target_events_map):
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
    cur = 4
    sounds = {}
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

        if o_type == 2 and len(payload) >= 9:
            sounds[o_id] = struct.unpack('<I', payload[5:9])[0]
        elif o_type == 2 and len(payload) >= 8:
            sounds[o_id] = struct.unpack('<I', payload[4:8])[0]
        elif o_type in (5, 6):
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

    # Unaligned 1-byte sliding window container scan
    containers = {}
    for c_id, payload in raw_containers.items():
        ch = []
        for off in range(0, len(payload) - 3):
            cid = struct.unpack('<I', payload[off:off+4])[0]
            if cid in sounds or (cid in raw_containers and cid != c_id):
                if cid not in ch:
                    ch.append(cid)
        containers[c_id] = ch

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
        if eh in target_events_map:
            ename = target_events_map[eh]
            for aid in act_ids:
                if aid in actions:
                    tid = actions[aid]
                    wems = resolve_sound_ids(tid)
                    for w in wems:
                        wem_to_event[w] = ename

    return wem_to_event

def resolve_target_interaction_paths(speaker_champ, speaker_skin_raw, target_champ, raw_event, meta_mgr):
    ev_lower = raw_event.lower()
    target_lower = target_champ.lower()

    # 1. Hedef Şampiyonun Hangi Haline Yapıldı? (Target Skin)
    m_target_skin = re.search(re.escape(target_lower) + r'skin(\d+)', ev_lower)
    target_skin_folder = f"Varsayilan_{target_champ}e_Yapilan_Atiflar"

    if m_target_skin:
        s_num = int(m_target_skin.group(1))
        target_skin_name = meta_mgr.resolve_skin_name(target_champ, f"skin{s_num:02d}")
        target_skin_folder = f"{target_skin_name}e_Yapilan_Atiflar"

    # 2. Söyleyen Şampiyon Klasörü
    speaker_champ_folder = speaker_champ.capitalize()

    # 3. Söyleyen Şampiyonun Hangi Hali?
    spk_skin = speaker_skin_raw
    m_spk_ev = re.search(re.escape(speaker_champ.lower()) + r'skin(\d+)', ev_lower)
    if m_spk_ev:
        spk_skin = f"skin{int(m_spk_ev.group(1)):02d}"

    speaker_skin_tr = meta_mgr.resolve_skin_name(speaker_champ, spk_skin)
    is_base = spk_skin.lower() in ('base', 'skin0', 'skin00', '0', '') or 'varsayilan' in speaker_skin_tr.lower()
    speaker_skin_subfolder = "Varsayilan_Hali" if is_base else speaker_skin_tr

    # 4. Eylem Tipi (Action Type)
    action_type = "karsilasma"
    if 'kill' in ev_lower or 'firstblood' in ev_lower:
        action_type = "katletme"
    elif 'taunt' in ev_lower:
        action_type = "kiskirtma"
    elif 'joke' in ev_lower:
        action_type = "saka"
    elif 'ally' in ev_lower:
        action_type = "dost_karsilasma"
    elif 'enemy' in ev_lower:
        action_type = "dusman_karsilasma"
    elif 'spell' in ev_lower or 'cast' in ev_lower or 'hit' in ev_lower:
        action_type = "yetenek_etkilesimi"

    speaker_clean = speaker_champ.lower()
    prefix = f"{speaker_clean}_{action_type}"
    return target_skin_folder, speaker_champ_folder, speaker_skin_subfolder, prefix

def scan_single_champion_wad(args):
    speaker_champ, target_champ_lower = args
    voice_wad_path, main_wad_path, resolved_speaker = find_champion_wad_files(speaker_champ, auto_download=False)
    
    scan_wad = main_wad_path if (main_wad_path and os.path.exists(main_wad_path)) else voice_wad_path
    if not scan_wad or not os.path.exists(scan_wad):
        return speaker_champ, set()

    found_events = set()
    dctx = zstd.ZstdDecompressor()

    with open(scan_wad, 'rb') as f:
        f.seek(268)
        fc = struct.unpack('<I', f.read(4))[0]
        entry_bytes = f.read(fc * 32)
        for i in range(fc):
            eb = entry_bytes[i*32 : (i+1)*32]
            phash, doff, csz, usz, tflags = struct.unpack('<QIII4s', eb[:24])
            
            if (tflags[0]&0xF) == 3 or csz > 50:
                f.seek(doff)
                raw = f.read(csz)
                try:
                    data = dctx.decompress(raw, max_output_size=usz) if (tflags[0]&0xF) == 3 else raw
                    if target_champ_lower.encode('ascii') in data.lower():
                        for m in re.findall(b'[a-zA-Z0-9_]{5,}', data):
                            s = m.decode('ascii', errors='ignore')
                            if target_champ_lower in s.lower() and any(k in s.lower() for k in ['encounter', 'kill', 'taunt', 'joke', 'move', 'vo_', 'hit', 'cast', 'attack', 'spell']):
                                found_events.add(s)
                                s_clean = re.sub(r'^(Play_)?(vo_)?[A-Za-z0-9]+_(Base_|Skin[0-9]+_)?(VO_)?', '', s, flags=re.IGNORECASE)
                                s_clean = re.sub(r'^(Play_vo_|Play_|vo_)', '', s_clean, flags=re.IGNORECASE)
                                if s_clean:
                                    found_events.add(s_clean)
                except Exception:
                    continue

    return resolved_speaker or speaker_champ, found_events

def extract_all_interactions_for_champion(target_champion, target_skin=None, speaker_base_only=False, gap_seconds=0.8):
    target_champ_clean = target_champion.capitalize()
    target_champ_lower = target_champion.lower()
    dctx = zstd.ZstdDecompressor()
    hashes = load_hashes()
    meta_mgr = MetadataManager()

    skin_filter_desc = f" ({target_skin})" if (target_skin and target_skin.upper() != 'ALL') else " (Tüm Kostümler)"
    spk_filter_desc = " [Sadece Varsayılan Karakterler]" if speaker_base_only else " [Tüm Kostümler]"
    print(f"\n================================================================================")
    print(f" 🎯 HEDEF ŞAMPİYON ATIF DEDEKTÖRÜ (GELİŞMİŞ HİYERARŞİ): [{target_champ_clean.upper()}]{skin_filter_desc}{spk_filter_desc}")
    print(f"================================================================================")
    print(f"⚡ 16 İş parçacığı ile tüm LoL şampiyon ses bankaları taranıyor...\n")

    all_champs = []
    seen = set()
    if os.path.exists(LOL_CHAMPIONS_PATH):
        for f in os.listdir(LOL_CHAMPIONS_PATH):
            if f.endswith('.wad.client'):
                base = f.replace('.wad.client', '')
                ch = base.split('.')[0]
                if ch and ch.lower() != target_champ_lower and ch not in seen:
                    seen.add(ch)
                    all_champs.append(ch)

    # 1. Aşama: Çok çekirdekli paralel tarama
    scan_tasks = [(ch, target_champ_lower) for ch in all_champs]
    speakers_data = {}
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
        scan_results = list(executor.map(scan_single_champion_wad, scan_tasks))

    for speaker_champ, ev_set in scan_results:
        if ev_set:
            speakers_data[speaker_champ] = ev_set

    total_referencing_champs = len(speakers_data)
    total_events = sum(len(evs) for evs in speakers_data.values())
    print(f"✅ Tarama tamamlandı! {total_referencing_champs} farklı şampiyonda {total_events} adet potansiyel {target_champ_clean} atıfı tespit edildi!")

    out_base = os.path.join(OUTPUT_BASE, target_champ_clean, f"{target_champ_clean}e_Yapilan_Tum_Ozel_Atiflar")
    if target_skin and target_skin.upper() != 'ALL':
        norm_ts = target_skin.lower().replace('_', '').replace(' ', '')
        if os.path.exists(out_base):
            for d in os.listdir(out_base):
                clean_d = d.lower().replace('_', '').replace(' ', '')
                if norm_ts in clean_d or clean_d in norm_ts:
                    shutil.rmtree(os.path.join(out_base, d), ignore_errors=True)
    else:
        shutil.rmtree(out_base, ignore_errors=True)

    temp_dir = os.path.join(OUTPUT_BASE, f"_temp_target_{target_champ_clean}")
    os.makedirs(temp_dir, exist_ok=True)

    extracted_total_voices = 0
    categories_summary = {}

    # Normalize target_skin filter
    norm_filter = None
    if target_skin and target_skin.upper() != 'ALL':
        norm_filter = target_skin.lower().replace('_', '').replace(' ', '').replace("'", "")

    # 2. Aşama: Her bir şampiyonun tüm kostüm WAD seslerini çıkarma
    for speaker_champ, event_strings in sorted(speakers_data.items()):
        voice_wad_path, _, resolved_speaker = find_champion_wad_files(speaker_champ, auto_download=True)
        if not voice_wad_path or not os.path.exists(voice_wad_path):
            continue
        speaker_champ = resolved_speaker or speaker_champ

        prefixes = [
            "",
            f"Play_vo_{speaker_champ}_",
            f"Play_vo_{speaker_champ}Base_",
            f"Play_vo_{speaker_champ}_Base_",
            f"Play_{speaker_champ}_VO_",
            f"Play_vo_",
            f"Play_",
            f"vo_{speaker_champ}_",
        ]
        for i in range(100):
            prefixes.append(f"Play_vo_{speaker_champ}Skin{i}_")
            prefixes.append(f"Play_vo_{speaker_champ}Skin{i:02d}_")
            prefixes.append(f"Play_vo_{speaker_champ}_Skin{i}_")
            prefixes.append(f"Play_vo_{speaker_champ}_Skin{i:02d}_")

        event_hash_map = {}
        for ev in event_strings:
            clean = re.sub(r'(5a|L|v|c|n|sq|0sq)$', '', ev, flags=re.IGNORECASE).strip('_')
            for cand in [ev, clean]:
                if not cand: continue
                for p in prefixes:
                    fn = p + cand
                    h = fnv_1(fn)
                    event_hash_map[h] = fn

        speaker_wpks = [] # list of (raw_skin, wem_dict)
        speaker_bnks = []
        with open(voice_wad_path, 'rb') as f:
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

                raw_skin = "base"
                parts = fname.split('/')
                if 'skins' in parts:
                    s_idx = parts.index('skins')
                    if s_idx + 1 < len(parts):
                        raw_skin = parts[s_idx + 1].lower()
                elif 'skin' in fname.lower():
                    m_sk = re.search(r'skin(\d+)', fname.lower())
                    if m_sk:
                        raw_skin = f"skin{int(m_sk.group(1)):02d}"

                if len(data) >= 4 and data[:4] == b'r3d2':
                    w_dict = extract_wpk_wems(data)
                    if w_dict:
                        speaker_wpks.append((raw_skin, w_dict))
                elif len(data) >= 4 and data[:4] == b'BKHD' and b'HIRC' in data:
                    speaker_bnks.append(data)

        speaker_matched_wems = {}
        speaker_audio_hashes = set()

        for bnk in speaker_bnks:
            wem_map = parse_hirc_soundbank(bnk, event_hash_map)
            for wid, ev_name in wem_map.items():
                for raw_skin, wems in speaker_wpks:
                    if wid in wems:
                        w_bytes = wems[wid]
                        audio_md5 = hashlib.md5(w_bytes).hexdigest()
                        if audio_md5 in speaker_audio_hashes:
                            continue
                        speaker_audio_hashes.add(audio_md5)
                        speaker_matched_wems[wid] = (w_bytes, ev_name, raw_skin)

        if not speaker_matched_wems:
            continue

        tasks = [(wid, wdata[0], temp_dir) for wid, wdata in speaker_matched_wems.items()]
        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
            conv_results = list(executor.map(convert_single_wem_worker, tasks))

        for wid, twav, dur in conv_results:
            if not os.path.exists(twav):
                continue
            
            if dur < 0.3:
                try:
                    os.remove(twav)
                except Exception:
                    pass
                continue

            wbytes, raw_ev, raw_skin = speaker_matched_wems[wid]
            
            target_subfolder, speaker_champ_folder, speaker_skin_subfolder, prefix = resolve_target_interaction_paths(
                speaker_champ, raw_skin, target_champ_clean, raw_ev, meta_mgr
            )

            # Apply target_skin filter if requested
            if norm_filter:
                clean_target_sub = target_subfolder.lower().replace('_', '').replace(' ', '')
                if norm_filter not in clean_target_sub and clean_target_sub not in norm_filter:
                    try:
                        os.remove(twav)
                    except Exception:
                        pass
                    continue
            
            # Apply speaker_base_only filter if requested (Sadece Varsayılan Kostümlü Karakterler)
            if speaker_base_only and speaker_skin_subfolder != "Varsayilan_Hali":
                try:
                    os.remove(twav)
                except Exception:
                    pass
                continue
            
            # Hiyerarşik veya Düz (Flat) Klasör Yolu:
            if speaker_base_only:
                # Kullanıcının CTRL+A ile kolayca seçebilmesi için tek klasör altında düz dizilim
                target_dir = os.path.join(out_base, target_subfolder)
                os.makedirs(target_dir, exist_ok=True)
                cat_key = prefix
                categories_summary[cat_key] = categories_summary.get(cat_key, 0) + 1
                idx_num = categories_summary[cat_key]
                dst_name = f"{prefix}_{idx_num:02d}.wav"
            else:
                # Kostümlü varyantlar için hiyerarşik yapı
                target_dir = os.path.join(out_base, target_subfolder, speaker_champ_folder, speaker_skin_subfolder)
                os.makedirs(target_dir, exist_ok=True)
                cat_key = f"{target_subfolder} / {speaker_champ_folder} / {speaker_skin_subfolder}"
                categories_summary[cat_key] = categories_summary.get(cat_key, 0) + 1
                idx_num = categories_summary[cat_key]
                dst_name = f"{prefix}_{idx_num:02d}.wav"
            safe_name = re.sub(r'[\\/*?:"<>|]', '', dst_name)
            shutil.move(twav, os.path.join(target_dir, safe_name))
            extracted_total_voices += 1

    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir, ignore_errors=True)

    # Automatically Generate DaVinci Resolve Master Timeline XML & SRT Subtitles
    try:
        from davinci_exporter import DaVinciTimelineExporter
        all_ref_wavs = []
        for root, _, files in os.walk(out_base):
            for f in sorted(files):
                if f.lower().endswith('.wav'):
                    all_ref_wavs.append(os.path.join(root, f))

        if all_ref_wavs:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            kurgu_dir = os.path.join(out_base, "Kurgu_Ciktilari", f"{timestamp}_{gap_seconds}s_Gap")
            os.makedirs(kurgu_dir, exist_ok=True)

            xml_filename = f"02_Dramatik_Kurgu_{gap_seconds}s_Gap.xml"
            xml_out_path = os.path.join(kurgu_dir, xml_filename)
            t_name = f"{target_champ_clean} Tüm Özel Atıflar (Dramatik Kurgu) - {len(all_ref_wavs)} Ses"

            DaVinciTimelineExporter.generate_fcp7_xml(
                audio_files=all_ref_wavs,
                output_path=xml_out_path,
                gap_seconds=gap_seconds,
                timeline_name=t_name,
                fps=60,
                smart_sort=True,
                exclude_sfx=False,
                target_champion=target_champ_clean,
                generate_srt=True,
                fade_in_seconds=0.5,
                fade_out_seconds=0.3
            )
            print(f" 🎬 DaVinci Resolve Kurgu Klasörü Hazırlandı:")
            print(f"    📂 Klasör: {kurgu_dir}")
            print(f"    ├─ 📁 01_Dramatik_Kurgu_{gap_seconds}s_Gap.fcpxml (DaVinci Resolve Native FCPXML)")
            print(f"    ├─ 📁 02_Dramatik_Kurgu_{gap_seconds}s_Gap.xml (Final Cut Pro 7 XML)")
            print(f"    ├─ 📝 03_Dramatik_Kurgu_{gap_seconds}s_Gap.srt (Faster-Whisper Senkron Türkçe Altyazı)")
            print(f"    ├─ 📁 04_Dramatik_Kurgu_{gap_seconds}s_Gap_Sadece_Metinler.fcpxml (Sadece Text+ Klipleri)")
            print(f"    └─ ⚙️ 05_Dramatik_Kurgu_{gap_seconds}s_Gap_Daktilo_TextPlus.setting (Fusion Daktilo Makrosu)")
    except Exception as e:
        print(f" ⚠️ DaVinci Timeline XML / SRT oluşturulurken hata: {e}")

    print(f"\n================================================================================")
    print(f" ✨ {target_champ_clean.upper()} İÇİN TÜM ATIFLAR 'VARSAYILAN HALİ' VE 'KOSTÜMLERİ' İLE AYRILDI!")
    print(f" 📂 Ana Klasör: Champions/{target_champ_clean}/{target_champ_clean}e_Yapilan_Tum_Ozel_Atiflar")
    print(f" 🗣️ Toplam Ayıklanan Yalın Atıf Repliği: {extracted_total_voices} adet .wav")
    print(f"================================================================================")
    for cat_name, count in sorted(categories_summary.items())[:25]:
        print(f"   ├─ 📁 {cat_name}: {count} adet .wav")
    if len(categories_summary) > 25:
        print(f"   └─ ... ve {len(categories_summary) - 25} farklı kostüm/şampiyon alt kategorisi daha!")
    print()


def main():
    target = "Ahri"
    target_skin = "Varsayilan_Ahri"
    speaker_base_only = False
    gap_seconds = 0.8
    
    if len(sys.argv) > 1:
        target = sys.argv[1]
    if len(sys.argv) > 2:
        target_skin = sys.argv[2]
        
    for idx, arg in enumerate(sys.argv):
        if arg.lower() in ('--base-only', '--speakers-base-only', 'base_only', 'baseonly', '--varsayilan-only'):
            speaker_base_only = True
        elif arg.lower() == '--gap' and idx + 1 < len(sys.argv):
            try:
                gap_seconds = float(sys.argv[idx + 1])
            except ValueError:
                pass
            
    extract_all_interactions_for_champion(target, target_skin, speaker_base_only=speaker_base_only, gap_seconds=gap_seconds)

if __name__ == "__main__":
    main()

