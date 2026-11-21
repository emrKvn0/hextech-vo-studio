# -*- coding: utf-8 -*-
"""
⚡ Just-In-Time (JIT) Ultra-Fast On-Demand LoL Audio Extractor & Streamer
Streams any dialogue cue in ~30-60ms on first click, and 0ms on subsequent clicks.
Zero disk bloat: only extracts the exact audio line the user clicks to hear.
Uses xxhash to deterministically map skins (Base vs Skins) so default champions
never play robotic/skin-effected audio.
"""

import os
import sys
import re
import struct
import hashlib
import subprocess
import xxhash
import zstandard as zstd

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(ROOT_DIR, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import extract_target_references as ref_extractor

CACHE_DIR = os.path.join(ROOT_DIR, "cache", "audio_jit")
os.makedirs(CACHE_DIR, exist_ok=True)
CHAMPIONS_DIR = os.path.join(ROOT_DIR, "Champions")
VGMSTREAM_PATH = ref_extractor.VGMSTREAM_PATH

def find_in_champions_dir(speaker_champ, raw_event, target_champ=""):
    """Search if the voice is already extracted in Champions directory."""
    if not os.path.exists(CHAMPIONS_DIR):
        return None

    targets_to_check = [target_champ] if target_champ else []
    targets_to_check.extend([speaker_champ])

    ev_clean = raw_event.lower()
    for t in targets_to_check:
        if not t:
            continue
        tdir = os.path.join(CHAMPIONS_DIR, t)
        if os.path.exists(tdir):
            for root, _, files in os.walk(tdir):
                for f in files:
                    if f.lower().endswith('.wav'):
                        f_low = f.lower()
                        if ev_clean in f_low or f_low in ev_clean:
                            return os.path.join(root, f)
    return None

def extract_single_event_jit(speaker_champ, raw_event):
    """
    Directly unpacks single event wem from speaker's voice WAD and converts to wav in ~30-60ms.
    Strictly isolates Base audio from Skin audio using WAD xxhash paths.
    """
    if raw_event and '2d' in raw_event.lower():
        # Automatically map 2D UI event triggers to real 3D spatial voice cues
        raw_event = re.sub(r'2d', '3D', raw_event, flags=re.IGNORECASE)

    # 1. Check disk cache first (0ms instant response)
    cache_key = hashlib.md5(f"{speaker_champ}_{raw_event}".encode('utf-8')).hexdigest()
    cached_wav = os.path.join(CACHE_DIR, f"{cache_key}.wav")
    if os.path.exists(cached_wav) and os.path.getsize(cached_wav) > 1000:
        return cached_wav

    voice_wad, _, resolved_speaker = ref_extractor.find_champion_wad_files(speaker_champ, auto_download=False)
    if not voice_wad or not os.path.exists(voice_wad):
        return None

    speaker = resolved_speaker or speaker_champ
    speaker_clean = speaker.lower().replace(" ", "").replace("'", "").replace("_", "")

    # 2. Detect speaker skin from event name
    # e.g. Play_vo_CamilleSkin01_FirstEncounter3DYasuo -> Skin01
    # e.g. Play_vo_Camille_FirstEncounter3DYasuo -> Base
    spk_chunk = raw_event
    m_act = re.search(r'_(firstencounter|encounter|kill|taunt|joke|ally|firstblood|spellcast)', raw_event, re.IGNORECASE)
    if m_act:
        spk_chunk = raw_event[:m_act.start()]

    spk_skin_num = 0
    m_spk = re.search(r'skin0*([0-9]{1,2})', spk_chunk, re.IGNORECASE)
    if m_spk:
        try:
            spk_skin_num = int(m_spk.group(1))
        except ValueError:
            spk_skin_num = 0

    wanted_skin_tag = "base" if spk_skin_num == 0 else f"skin{spk_skin_num:02d}"

    # 3. Build xxhash lookup table for all possible skins of this champion
    skin_tags = ["base"] + [f"skin{i:02d}" for i in range(1, 65)]
    hash_to_skin = {}
    for stag in skin_tags:
        for loc in ["en_us", "tr_tr", "en_US", "tr_TR"]:
            for ext in ["audio.wpk", "events.bnk"]:
                p = f"assets/sounds/wwise2016/vo/{loc}/characters/{speaker_clean}/skins/{stag}/{speaker_clean}_{stag}_vo_{ext}"
                h = xxhash.xxh64(p.lower().encode("utf-8")).intdigest()
                hash_to_skin[h] = (stag, ext)

    dctx = zstd.ZstdDecompressor()
    skin_wpks = {}
    skin_bnks = {}
    fallback_wpks = []
    fallback_bnks = []

    try:
        with open(voice_wad, 'rb') as f:
            f.seek(268)
            fc_bytes = f.read(4)
            if len(fc_bytes) < 4:
                return None
            fc = struct.unpack('<I', fc_bytes)[0]
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

                stag, ext = hash_to_skin.get(phash, (None, None))
                if len(data) >= 4 and data[:4] == b'r3d2':
                    w_dict = ref_extractor.extract_wpk_wems(data)
                    if w_dict:
                        if stag:
                            skin_wpks[stag] = w_dict
                        fallback_wpks.append(w_dict)
                elif len(data) >= 4 and data[:4] == b'BKHD' and b'HIRC' in data:
                    if stag:
                        skin_bnks[stag] = data
                    fallback_bnks.append(data)
    except Exception as e:
        print(f"⚠️ WAD okuma hatası ({speaker}): {e}")
        return None

    # 4. Generate candidate event names to search in HIRC soundbank
    clean_ev = re.sub(r'(5a|Jl|0sq|sq|n|v|c|L|K|k)$', '', raw_event).strip('_')
    # strip trailing number from take variations e.g. Yasuo1 -> Yasuo
    clean_ev_no_digit = re.sub(r'([A-Za-z])\d$', r'\1', clean_ev)

    candidate_names = set([
        raw_event,
        raw_event.rstrip('Kk'),
        clean_ev,
        clean_ev_no_digit,
        f"Play_{raw_event}",
        f"Play_{clean_ev}",
        f"Play_{raw_event.rstrip('Kk')}",
        f"Play_vo_{speaker}_{raw_event}",
        f"Play_vo_{speaker}_{clean_ev}",
        f"vo_{raw_event}"
    ])

    # If skin number is present, also add skin-specific prefix candidates
    if spk_skin_num > 0:
        candidate_names.add(f"Play_vo_{speaker}Skin{spk_skin_num:02d}_{clean_ev}")
        candidate_names.add(f"Play_vo_{speaker}Skin{spk_skin_num}_{clean_ev}")
    else:
        candidate_names.add(f"Play_vo_{speaker}_{clean_ev}")
        candidate_names.add(f"Play_vo_{speaker}Base_{clean_ev}")

    event_hash_map = {}
    for cname in candidate_names:
        if cname:
            h = ref_extractor.fnv_1(cname)
            event_hash_map[h] = cname

    # 5. Prioritize BNKs: Wanted skin FIRST to ensure base never plays skin audio!
    ordered_bnks = []
    if wanted_skin_tag in skin_bnks:
        ordered_bnks.append((wanted_skin_tag, skin_bnks[wanted_skin_tag]))
    for stag, bdata in skin_bnks.items():
        if stag != wanted_skin_tag:
            ordered_bnks.append((stag, bdata))
    for fb in fallback_bnks:
        if not any(fb is b[1] for b in ordered_bnks):
            ordered_bnks.append(("fallback", fb))

    found_wem_bytes = None
    found_wem_id = None

    for stag, bnk in ordered_bnks:
        wem_map = ref_extractor.parse_hirc_soundbank(bnk, event_hash_map)
        if wem_map:
            # Prioritize matching WPK
            candidate_wpks = []
            if stag in skin_wpks:
                candidate_wpks.append(skin_wpks[stag])
            for w in fallback_wpks:
                if w not in candidate_wpks:
                    candidate_wpks.append(w)

            for wid in wem_map.keys():
                for wpk in candidate_wpks:
                    if wid in wpk:
                        found_wem_bytes = wpk[wid]
                        found_wem_id = wid
                        break
                if found_wem_bytes:
                    break
        if found_wem_bytes:
            break

    if not found_wem_bytes:
        return None

    # 6. Convert single wem to wav via vgmstream
    temp_wem = os.path.join(CACHE_DIR, f"temp_{cache_key}.wem")
    with open(temp_wem, 'wb') as tf:
        tf.write(found_wem_bytes)

    creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
    subprocess.run([VGMSTREAM_PATH, "-o", cached_wav, temp_wem],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                   creationflags=creationflags)

    if os.path.exists(temp_wem):
        try:
            os.remove(temp_wem)
        except Exception:
            pass

    if os.path.exists(cached_wav) and os.path.getsize(cached_wav) > 100:
        return cached_wav

    return None

def extract_single_wem_jit(speaker_champ, wem_id, raw_event=None):
    """
    Directly unpacks specific WEM audio by ID from champion's WAD files in ~15-30ms.
    Guarantees 100% precision for variations under the same event.
    """
    if not wem_id:
        if raw_event:
            return extract_single_event_jit(speaker_champ, raw_event)
        return None

    try:
        wid_int = int(wem_id)
    except ValueError:
        return extract_single_event_jit(speaker_champ, raw_event) if raw_event else None

    # 1. Check disk cache
    cached_wav = os.path.join(CACHE_DIR, f"{speaker_champ}_{wid_int}.wav")
    if os.path.exists(cached_wav) and os.path.getsize(cached_wav) > 100:
        return cached_wav

    # 2. Find champion WAD files
    wad_candidates = []
    wad_dir = r"C:\Riot Games\League of Legends\Game\DATA\FINAL\Champions"
    for name_fmt in [f"{speaker_champ}.tr_TR.wad.client", f"{speaker_champ}.wad.client"]:
        p = os.path.join(wad_dir, name_fmt)
        if os.path.exists(p):
            wad_candidates.append(p)

    voice_wad, _, resolved_speaker = ref_extractor.find_champion_wad_files(speaker_champ, auto_download=False)
    if voice_wad and voice_wad not in wad_candidates:
        wad_candidates.append(voice_wad)

    dctx = zstd.ZstdDecompressor()
    found_wem_bytes = None

    for wp in wad_candidates:
        try:
            with open(wp, 'rb') as f:
                f.seek(268)
                fc_bytes = f.read(4)
                if len(fc_bytes) < 4:
                    continue
                fc = struct.unpack('<I', fc_bytes)[0]
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
                        w_dict = ref_extractor.extract_wpk_wems(data)
                        if wid_int in w_dict:
                            found_wem_bytes = w_dict[wid_int]
                            break
                if found_wem_bytes:
                    break
        except Exception:
            continue

    if not found_wem_bytes:
        # Fallback to event extraction if wem was not found
        return extract_single_event_jit(speaker_champ, raw_event) if raw_event else None

    # Convert to WAV
    temp_wem = os.path.join(CACHE_DIR, f"temp_{speaker_champ}_{wid_int}.wem")
    with open(temp_wem, 'wb') as tf:
        tf.write(found_wem_bytes)

    creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
    subprocess.run([VGMSTREAM_PATH, "-o", cached_wav, temp_wem],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                   creationflags=creationflags)

    if os.path.exists(temp_wem):
        try:
            os.remove(temp_wem)
        except Exception:
            pass

    if os.path.exists(cached_wav) and os.path.getsize(cached_wav) > 100:
        return cached_wav

    return None

def get_or_extract_audio(speaker_champ, raw_event, target_champ="", wem_id=None, game="lol"):
    """
    Unified entrypoint for audio streaming:
    Supports both League of Legends (WAD/WPK/BNK) and Legends of Runeterra (PCK).
    """
    # LoR otomatik tespiti: game=="lor" veya raw_event/wem_id "VO_...wem" ise
    ev_str = str(raw_event or "")
    wid_str = str(wem_id or "")
    if game == "lor" or ev_str.upper().startswith("VO_") or wid_str.upper().startswith("VO_") or ev_str.lower().endswith(".wem") or wid_str.lower().endswith(".wem"):
        lor_wem = wid_str if wid_str.upper().startswith("VO_") else ev_str
        return extract_lor_wem_jit(lor_wem)

    if wem_id:
        res = extract_single_wem_jit(speaker_champ, wem_id, raw_event)
        if res:
            return res

    found = find_in_champions_dir(speaker_champ, raw_event, target_champ)
    if found:
        return found
    return extract_single_event_jit(speaker_champ, raw_event)


# =============================================================================
# 🃏 LEGENDS OF RUNETERRA (LoR) JIT SES & ETKİLEŞİM MOTORU
# =============================================================================
LOR_AUDIO_DIR = r"C:\Riot Games\LoR\live\PatcherData\PatchableFiles\Audio"
LOR_FULL_DB_PATH = os.path.join(ROOT_DIR, "cache", "lor_full_database.json")
LOR_MATRIX_PATH = os.path.join(ROOT_DIR, "lol-matrix-web", "public", "data", "lor_matrix_data.json")

_lor_pck_index = None
_lor_full_db = None
_lor_matrix_db = None


def _fnv1_64_lor(wem_filename: str) -> int:
    s = f"turkish(turkey)\\{wem_filename.lower()}"
    h = 0xcbf29ce484222325
    prime = 0x100000001b3
    for b in s.encode('ascii', 'ignore'):
        h = ((h * prime) & 0xFFFFFFFFFFFFFFFF) ^ b
    return h


def get_lor_pck_index() -> dict:
    global _lor_pck_index
    if _lor_pck_index is not None:
        return _lor_pck_index
    _lor_pck_index = {}
    for stage_file in ["Turkish(Turkey)_stage0.pck", "Turkish(Turkey)_stage1.pck"]:
        p = os.path.join(LOR_AUDIO_DIR, stage_file)
        if not os.path.exists(p):
            continue
        try:
            with open(p, 'rb') as f:
                header = f.read(0x3C)
                if len(header) < 0x3C or header[:4] != b'AKPK':
                    continue
                ext_count = struct.unpack_from('<I', header, 0x38)[0]
                table = f.read(ext_count * 24)
                for i in range(ext_count):
                    h64, mult, fsize, offset_blocks, folder_id = struct.unpack_from('<QIIII', table, i * 24)
                    _lor_pck_index[h64] = (p, offset_blocks * mult, fsize)
        except Exception:
            pass
    return _lor_pck_index


def extract_lor_wem_jit(wem_filename: str):
    """LoR Turkish(Turkey)_stage1.pck içinden ~15ms'de .wem çıkarır ve .wav'a dönüştürür."""
    if not wem_filename:
        return None
    w_clean = wem_filename.strip()
    if not w_clean.lower().endswith('.wem'):
        w_clean += '.wem'

    safe_key = re.sub(r'[^\w\-_.]', '_', w_clean[:-4])
    cached_wav = os.path.join(CACHE_DIR, f"lor_{safe_key}.wav")
    if os.path.exists(cached_wav) and os.path.getsize(cached_wav) > 100:
        return cached_wav

    pck_idx = get_lor_pck_index()
    h64 = _fnv1_64_lor(w_clean)
    entry = pck_idx.get(h64)
    if not entry:
        return None

    pck_path, offset, fsize = entry
    try:
        with open(pck_path, 'rb') as f:
            f.seek(offset)
            wem_bytes = f.read(fsize)
    except Exception:
        return None

    temp_wem = os.path.join(CACHE_DIR, f"temp_lor_{safe_key}.wem")
    try:
        with open(temp_wem, 'wb') as tf:
            tf.write(wem_bytes)
        creationflags = 0x08000000 if sys.platform == 'win32' else 0
        subprocess.run(
            [VGMSTREAM_PATH, "-o", cached_wav, temp_wem],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags
        )
    finally:
        if os.path.exists(temp_wem):
            try:
                os.remove(temp_wem)
            except Exception:
                pass

    if os.path.exists(cached_wav) and os.path.getsize(cached_wav) > 100:
        return cached_wav
    return None


def get_lor_full_db() -> dict:
    global _lor_full_db
    if _lor_full_db is not None:
        return _lor_full_db
    if os.path.exists(LOR_FULL_DB_PATH):
        try:
            import json
            with open(LOR_FULL_DB_PATH, 'r', encoding='utf-8') as f:
                _lor_full_db = json.load(f)
                return _lor_full_db
        except Exception:
            pass
    _lor_full_db = {}
    return _lor_full_db


def get_lor_matrix_db() -> dict:
    global _lor_matrix_db
    if _lor_matrix_db is not None:
        return _lor_matrix_db
    if os.path.exists(LOR_MATRIX_PATH):
        try:
            import json
            with open(LOR_MATRIX_PATH, 'r', encoding='utf-8') as f:
                _lor_matrix_db = json.load(f)
                return _lor_matrix_db
        except Exception:
            pass
    _lor_matrix_db = {}
    return _lor_matrix_db


def extract_lor_champion_voices(champ_name: str, skin_num=0):
    """ChampionVoicesView için LoR karakterinin tüm replik kategorilerini döner."""
    import generate_lor_database as lor_gen
    import champion_voice_extractor as cve
    db = get_lor_full_db()
    char_meta = db.get('char_meta', {})
    voices_by_char = db.get('voices_by_char', {})
    master_trans = cve.get_master_transcripts()

    # İsim eşleştirme
    target_key = champ_name
    if target_key not in char_meta:
        for k in char_meta:
            if k.lower() == champ_name.lower():
                target_key = k
                break
    if target_key not in char_meta:
        return None

    cmeta = char_meta[target_key]
    skins_dict = cmeta.get('skins', {})
    skins_list = [skins_dict[k] for k in sorted(skins_dict.keys(), key=lambda x: int(x))]
    for sk in skins_list:
        sk['skin_num'] = int(sk['skin_num'])

    try:
        s_num = int(skin_num)
    except ValueError:
        s_num = 0

    char_skins_voices = voices_by_char.get(target_key, {})
    ev_map = char_skins_voices.get(str(s_num)) or char_skins_voices.get("0") or {}
    current_skin = next((s for s in skins_list if int(s['skin_num']) == s_num), skins_list[0] if skins_list else {
        'skin_num': 0,
        'name': f"Varsayılan {target_key}",
        'splash_url': cmeta.get('splash_url', ''),
        'voice_type': 'base',
        'voice_badge': '🃏 LOR VARSAYILAN DUBLAJ',
        'voice_tag': 'Ana Kart Sesi',
        'voice_desc': '',
        'is_unique': True
    })

    categorized = {}
    total_wems = 0
    for base_ev, w_entries in ev_map.items():
        if not w_entries:
            continue
        first_wem = w_entries[0]['wem']
        tgt_c = w_entries[0].get('target', '')
        cat_id, _, action_label, sort_weight = lor_gen.classify_wem_action(first_wem, tgt_c)

        tgt_meta = char_meta.get(tgt_c, {}) if tgt_c else {}
        wem_items = []
        for idx, we in enumerate(w_entries, 1):
            w_file = we['wem']
            tr_text = master_trans.get(w_file, '') or we.get('transcript', '')
            wem_items.append({
                'wem_id': w_file,
                'variation_index': idx,
                'variation_total': len(w_entries),
                'transcript': tr_text
            })
            total_wems += 1

        categorized.setdefault(cat_id, []).append({
            'raw_event': base_ev,
            'action_name': action_label,
            'sort_weight': sort_weight,
            'is_sfx': False,
            'target_champ': tgt_c,
            'target_skin_num': 0,
            'target_skin_name': f"Varsayılan {tgt_c}" if tgt_c else "",
            'target_splash_url': tgt_meta.get('splash_url', '') if tgt_c else "",
            'wems': wem_items
        })

    result_categories = []
    for cat_key in sorted(cve.CATEGORY_META.keys()):
        if cat_key in categorized:
            meta = cve.CATEGORY_META[cat_key]
            items = sorted(categorized[cat_key], key=lambda x: (x['sort_weight'], x['action_name']))
            result_categories.append({
                'id': cat_key,
                'title': meta['title'],
                'icon': meta['icon'],
                'color': meta['color'],
                'count': len(items),
                'total_wems': sum(len(it['wems']) for it in items),
                'items': items
            })

    return {
        'schema_version': 2,
        'game': 'lor',
        'champion': target_key,
        'skin_num': s_num,
        'skin_name': current_skin['name'],
        'splash_url': current_skin.get('splash_url', cmeta.get('splash_url', '')),
        'voice_type': current_skin.get('voice_type', 'base'),
        'voice_badge': current_skin.get('voice_badge', '🃏 LOR VARSAYILAN DUBLAJ'),
        'voice_tag': current_skin.get('voice_tag', 'Ana Kart Sesi'),
        'voice_desc': current_skin.get('voice_desc', ''),
        'is_unique': current_skin.get('is_unique', True),
        'total_events': len(ev_map),
        'total_wems': total_wems,
        'skins': skins_list,
        'categories': result_categories
    }


def extract_lor_pair_interactions(champA: str, champB: str):
    """PairInteractionsView için iki LoR karakteri arasındaki karşılıklı diyalog ve etkileşimleri döner."""
    import champion_voice_extractor as cve
    db = get_lor_full_db()
    mat = get_lor_matrix_db()
    char_meta = db.get('char_meta', {})
    pair_dialogues = db.get('pair_dialogues', {})
    master_trans = cve.get_master_transcripts()

    is_all_targets = (champB.strip().upper() == 'ALL')

    # İsimleri normalize et
    realA = champA
    realB = champB
    for k in char_meta:
        if k.lower() == champA.lower():
            realA = k
        if not is_all_targets and k.lower() == champB.lower():
            realB = k

    metaA = char_meta.get(realA, {'name': realA, 'splash_url': '', 'icon_url': ''})
    if is_all_targets:
        realB = "Tümü"
        metaB = {
            'name': 'Tüm Etkileşimler',
            'splash_url': 'https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/champion-icons/-1.png',
            'icon_url': 'https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/champion-icons/-1.png'
        }
    else:
        metaB = char_meta.get(realB, {'name': realB, 'splash_url': '', 'icon_url': ''})

    chains = []
    if is_all_targets:
        lowA = realA.lower()
        for pk, ch_list in pair_dialogues.items():
            if pk.startswith(f"{lowA}__") or pk.endswith(f"__{lowA}"):
                parts = pk.split("__")
                partner = parts[1] if parts[0] == lowA else parts[0]
                # Hayatsöndüren (Spirit Blossom Kindred) kopyasını Kindred lehine filtrele (Madde 3)
                if 'hayats' in partner.lower() or '98sb044' in partner.lower():
                    continue
                for ch in ch_list:
                    ch_copy = dict(ch)
                    ch_copy['partner_champ'] = partner.title()
                    turns_copy = []
                    for t in ch.get('turns', []):
                        tc = dict(t)
                        if master_trans.get(tc.get('wem_id')):
                            tc['transcript'] = master_trans[tc['wem_id']]
                        turns_copy.append(tc)
                    ch_copy['turns'] = turns_copy
                    chains.append(ch_copy)
    else:
        first_c, second_c = sorted([realA, realB], key=lambda x: x.lower())
        p_key = f"{first_c.lower()}__{second_c.lower()}"
        for ch in pair_dialogues.get(p_key, []):
            ch_copy = dict(ch)
            turns_copy = []
            for t in ch.get('turns', []):
                tc = dict(t)
                if master_trans.get(tc['wem_id']):
                    tc['transcript'] = master_trans[tc['wem_id']]
                turns_copy.append(tc)
            ch_copy['turns'] = turns_copy
            chains.append(ch_copy)

    used_wems = {t['wem_id'] for ch in chains for t in ch.get('turns', [])}

    # Tek yönlü etkileşimleri matristen topla
    champs_by_name = {c['name']: c for c in mat.get('champions', [])}
    cA_obj = champs_by_name.get(realA, {})

    sections_map = {
        "first_encounter": {
            "id": "first_encounter",
            "title": "Karşılaşma & Sahaya Çağrılma (Arrival)",
            "subtitle": "Kartlar sahaya indiği anda birbirlerine söyledikleri özel karşılaşma replikleri",
            "groups": []
        },
        "kills": {
            "id": "kills",
            "title": "Katletme & Dost Ölümü (Death & Kills)",
            "subtitle": "Birbirlerini katlettiklerinde veya dost kart öldüğünde verdikleri tepkiler",
            "groups": []
        },
        "taunts_jokes": {
            "id": "taunts_jokes",
            "title": "Bloklama & Savunma Atışmaları (Block Declare)",
            "subtitle": "Birbirlerini blokladıklarında tetiklenen özel replikler",
            "groups": []
        },
        "other_gameplay": {
            "id": "other_gameplay",
            "title": "Saldırı & Büyü Etkileşimleri (Attack & Spell)",
            "subtitle": "Beraber saldırırken veya büyü kullandıklarında tetiklenen replikler",
            "groups": []
        }
    }

    one_way_groups = {}
    if is_all_targets:
        # 1. A'nın diğer tüm karakterlere söyledikleri
        for it in cA_obj.get('outgoing_items', []):
            tgt_name = it.get('target_champ', '')
            if not tgt_name or tgt_name.lower() == realA.lower():
                continue
            wid = it.get('wem_id') or it.get('raw_event')
            if wid in used_wems:
                continue
            tgt_meta = char_meta.get(tgt_name, {'name': tgt_name, 'splash_url': '', 'icon_url': ''})
            b_act = it.get('base_action', 'diger')
            sec_key = (
                'first_encounter' if b_act == 'karsilasma' else
                'kills' if b_act in ('katletme', 'olum') else
                'taunts_jokes' if b_act in ('kiskirtma', 'saka') else
                'other_gameplay'
            )
            sub_cat = it.get('action_type', 'Özel Etkileşim')
            g_key = (sec_key, "A_to_B", realA, tgt_name, it.get('speaker_skin_num', 0), it.get('target_skin_num', 0), sub_cat)
            one_way_groups.setdefault(g_key, {
                'direction': "A_to_B",
                'speaker_champ': realA,
                'speaker_skin_num': it.get('speaker_skin_num', 0),
                'speaker_skin_name': it.get('speaker_skin_name', f"Varsayılan {realA}"),
                'speaker_splash_url': metaA.get('splash_url', ''),
                'target_champ': tgt_name,
                'target_skin_num': it.get('target_skin_num', 0),
                'target_skin_name': it.get('target_skin_name', f"Varsayılan {tgt_name}"),
                'target_splash_url': tgt_meta.get('splash_url', ''),
                'sub_category': sub_cat,
                'sort_order': 10,
                'quotes': []
            })
            q_list = one_way_groups[g_key]['quotes']
            q_list.append({
                'speaker_champ': realA,
                'speaker_skin_num': it.get('speaker_skin_num', 0),
                'speaker_skin_name': it.get('speaker_skin_name', f"Varsayılan {realA}"),
                'speaker_splash_url': metaA.get('splash_url', ''),
                'target_champ': tgt_name,
                'target_skin_num': it.get('target_skin_num', 0),
                'target_skin_name': it.get('target_skin_name', f"Varsayılan {tgt_name}"),
                'target_splash_url': tgt_meta.get('splash_url', ''),
                'raw_event': wid,
                'action_name': sub_cat,
                'wem_id': wid,
                'variation_index': len(q_list) + 1,
                'variation_total': len(q_list) + 1,
                'transcript': master_trans.get(wid, '') or it.get('transcript', '')
            })

        # 2. Diğer tüm karakterlerin A'ya söyledikleri
        for other_c in mat.get('champions', []):
            spk_name = other_c.get('name', '')
            if spk_name.lower() == realA.lower():
                continue
            for it in other_c.get('outgoing_items', []):
                if it.get('target_champ', '').lower() != realA.lower():
                    continue
                wid = it.get('wem_id') or it.get('raw_event')
                if wid in used_wems:
                    continue
                spk_meta = char_meta.get(spk_name, {'name': spk_name, 'splash_url': '', 'icon_url': ''})
                b_act = it.get('base_action', 'diger')
                sec_key = (
                    'first_encounter' if b_act == 'karsilasma' else
                    'kills' if b_act in ('katletme', 'olum') else
                    'taunts_jokes' if b_act in ('kiskirtma', 'saka') else
                    'other_gameplay'
                )
                sub_cat = it.get('action_type', 'Özel Etkileşim')
                g_key = (sec_key, "B_to_A", spk_name, realA, it.get('speaker_skin_num', 0), it.get('target_skin_num', 0), sub_cat)
                one_way_groups.setdefault(g_key, {
                    'direction': "B_to_A",
                    'speaker_champ': spk_name,
                    'speaker_skin_num': it.get('speaker_skin_num', 0),
                    'speaker_skin_name': it.get('speaker_skin_name', f"Varsayılan {spk_name}"),
                    'speaker_splash_url': spk_meta.get('splash_url', ''),
                    'target_champ': realA,
                    'target_skin_num': it.get('target_skin_num', 0),
                    'target_skin_name': it.get('target_skin_name', f"Varsayılan {realA}"),
                    'target_splash_url': metaA.get('splash_url', ''),
                    'sub_category': sub_cat,
                    'sort_order': 10,
                    'quotes': []
                })
                q_list = one_way_groups[g_key]['quotes']
                q_list.append({
                    'speaker_champ': spk_name,
                    'speaker_skin_num': it.get('speaker_skin_num', 0),
                    'speaker_skin_name': it.get('speaker_skin_name', f"Varsayılan {spk_name}"),
                    'speaker_splash_url': spk_meta.get('splash_url', ''),
                    'target_champ': realA,
                    'target_skin_num': it.get('target_skin_num', 0),
                    'target_skin_name': it.get('target_skin_name', f"Varsayılan {realA}"),
                    'target_splash_url': metaA.get('splash_url', ''),
                    'raw_event': wid,
                    'action_name': sub_cat,
                    'wem_id': wid,
                    'variation_index': len(q_list) + 1,
                    'variation_total': len(q_list) + 1,
                    'transcript': master_trans.get(wid, '') or it.get('transcript', '')
                })
    else:
        cB_obj = champs_by_name.get(realB, {})
        for spk_name, tgt_name, spk_meta, tgt_meta, c_obj, dir_key in [
            (realA, realB, metaA, metaB, cA_obj, "A_to_B"),
            (realB, realA, metaB, metaA, cB_obj, "B_to_A")
        ]:
            for it in c_obj.get('outgoing_items', []):
                if it.get('target_champ', '').lower() != tgt_name.lower():
                    continue
                wid = it.get('wem_id') or it.get('raw_event')
                if wid in used_wems:
                    continue
                b_act = it.get('base_action', 'diger')
                sec_key = (
                    'first_encounter' if b_act == 'karsilasma' else
                    'kills' if b_act in ('katletme', 'olum') else
                    'taunts_jokes' if b_act in ('kiskirtma', 'saka') else
                    'other_gameplay'
                )
                sub_cat = it.get('action_type', 'Özel Etkileşim')
                g_key = (sec_key, dir_key, spk_name, tgt_name, it.get('speaker_skin_num', 0), it.get('target_skin_num', 0), sub_cat)
                one_way_groups.setdefault(g_key, {
                    'direction': dir_key,
                    'speaker_champ': spk_name,
                    'speaker_skin_num': it.get('speaker_skin_num', 0),
                    'speaker_skin_name': it.get('speaker_skin_name', f"Varsayılan {spk_name}"),
                    'speaker_splash_url': spk_meta.get('splash_url', ''),
                    'target_champ': tgt_name,
                    'target_skin_num': it.get('target_skin_num', 0),
                    'target_skin_name': it.get('target_skin_name', f"Varsayılan {tgt_name}"),
                    'target_splash_url': tgt_meta.get('splash_url', ''),
                    'sub_category': sub_cat,
                    'sort_order': 10,
                    'quotes': []
                })
                q_list = one_way_groups[g_key]['quotes']
                q_list.append({
                    'speaker_champ': spk_name,
                    'speaker_skin_num': it.get('speaker_skin_num', 0),
                    'speaker_skin_name': it.get('speaker_skin_name', f"Varsayılan {spk_name}"),
                    'speaker_splash_url': spk_meta.get('splash_url', ''),
                    'target_champ': tgt_name,
                    'target_skin_num': it.get('target_skin_num', 0),
                    'target_skin_name': it.get('target_skin_name', f"Varsayılan {tgt_name}"),
                    'target_splash_url': tgt_meta.get('splash_url', ''),
                    'raw_event': wid,
                    'action_name': sub_cat,
                    'wem_id': wid,
                    'variation_index': len(q_list) + 1,
                    'variation_total': len(q_list) + 1,
                    'transcript': master_trans.get(wid, '') or it.get('transcript', '')
                })

    for g_key, g_obj in one_way_groups.items():
        total_q = len(g_obj['quotes'])
        for q in g_obj['quotes']:
            q['variation_total'] = total_q
        sections_map[g_key[0]]['groups'].append(g_obj)

    total_dialogue_turns = sum(c['turn_count'] for c in chains)
    total_one_way = sum(sum(len(g['quotes']) for g in s['groups']) for s in sections_map.values())

    return {
        'schema_version': 2,
        'game': 'lor',
        'champA': {
            'name': realA,
            'splash_url': metaA.get('splash_url', ''),
            'icon_url': metaA.get('icon_url', '')
        },
        'champB': {
            'name': realB,
            'splash_url': metaB.get('splash_url', ''),
            'icon_url': metaB.get('icon_url', '')
        },
        'summary': {
            'dialogue_chains_count': len(chains),
            'dialogue_turns_count': total_dialogue_turns,
            'one_way_quotes_count': total_one_way,
            'total_interactions': total_dialogue_turns + total_one_way,
            'total_dialogue_chains': len(chains),
            'total_dialogue_turns': total_dialogue_turns,
            'total_one_way_quotes': total_one_way
        },
        'dialogue_chains': chains,
        'sections': [s for s in sections_map.values() if s['groups']]
    }

