# -*- coding: utf-8 -*-
"""
⚡ League of Legends - Global Matrix & Reference Database Generator (v5 Zero-Audio Meta-Architecture)
Features:
- 100% Deterministic WAD & Wwise Event extraction across all 170+ champions.
- ZERO physical audio files generated or required (Zero-Audio Footprint, pure lightweight JSON metadata).
- Precise Skin vs Base classification (B->B, S->B, B->S, S->S).
- Complete recovery of previously filtered interactions (e.g. Jhin -> Yasuo, Camille skins -> Yasuo).
- Full retention of all interaction events even when transcript is missing ([Metin Yok - Sadece Etkileşim Kaydı]).
- Enriched with known Turkish transcripts where available.
"""

import os
import sys
import re
import json
import time
import struct
import concurrent.futures
import zstandard as zstd

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)
import extract_target_references as ref_ext

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKINS_DB_PATH = os.path.join(ROOT_DIR, "all_lol_skins_database.json")
WAD_DIR = r"C:\Riot Games\League of Legends\Game\DATA\FINAL\Champions"
OUTPUT_JSON_PATH = os.path.join(ROOT_DIR, "lol_matrix_data.json")
VITE_PUBLIC_JSON = os.path.join(ROOT_DIR, "lol-matrix-web", "public", "data", "lol_matrix_data.json")
CHAMPIONS_DIR = os.path.join(ROOT_DIR, "Champions")
MASTER_TRANSCRIPTS_PATH = os.path.join(ROOT_DIR, "cache", "master_transcripts.json")

def load_skins_and_metadata():
    if not os.path.exists(SKINS_DB_PATH):
        raise FileNotFoundError(f"Skins database not found: {SKINS_DB_PATH}")

    with open(SKINS_DB_PATH, 'r', encoding='utf-8') as f:
        skins_data = json.load(f)

    champ_canonical = {}
    champ_ids = {}
    champ_skins = {}

    for s in skins_data:
        c_name = s.get('champion_name') or s.get('champion_alias')
        c_alias = s.get('champion_alias') or c_name
        c_id = s.get('champion_id')
        s_num = s.get('skin_num', 0)
        s_name_tr = s.get('name_tr') or f"{c_name} Kostüm {s_num}"

        if not c_name:
            continue

        for key in [c_name.lower(), c_alias.lower()]:
            champ_canonical[key] = c_name
            if c_id:
                if key not in champ_ids or (c_id < 1000 and champ_ids[key] >= 1000):
                    champ_ids[key] = c_id
            if key not in champ_skins:
                champ_skins[key] = {}
            champ_skins[key][s_num] = s_name_tr

    return champ_canonical, champ_ids, champ_skins

def load_known_transcripts():
    known_texts = {}
    # 1. Master verified transcripts
    if os.path.exists(MASTER_TRANSCRIPTS_PATH):
        try:
            with open(MASTER_TRANSCRIPTS_PATH, 'r', encoding='utf-8') as mf:
                m_data = json.load(mf)
                for k, v in m_data.items():
                    if v and isinstance(v, str):
                        known_texts[k.lower()] = v.strip()
        except Exception:
            pass

    # 2. Champions cache
    if os.path.exists(CHAMPIONS_DIR):
        for root, dirs, files in os.walk(CHAMPIONS_DIR):
            for f in files:
                if f == '.ai_voice_cache.json' or f.endswith('_voice_quotes.json'):
                    p = os.path.join(root, f)
                    try:
                        with open(p, 'r', encoding='utf-8') as jf:
                            d = json.load(jf)
                            if isinstance(d, dict):
                                for k, v in d.items():
                                    if isinstance(v, dict) and v.get('text'):
                                        txt = v['text'].strip()
                                        clean_k = os.path.basename(k).lower().replace('.wav', '').replace('.wem', '')
                                        known_texts[clean_k] = txt
                                        if v.get('event_name'):
                                            known_texts[v['event_name'].lower()] = txt
                    except Exception:
                        pass
    return known_texts

def get_champ_icon(canonical_name, champ_ids):
    c_low = canonical_name.lower()
    cid = champ_ids.get(c_low)
    if cid:
        return f"https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/champion-icons/{cid}.png"
    return f"https://ddragon.leagueoflegends.com/cdn/14.20.1/img/champion/{canonical_name}.png"

def build_target_dictionary(champ_canonical):
    unique_targets = {}
    for key, cname in champ_canonical.items():
        k_clean = key.lower().replace(' ', '').replace("'", "").replace("_", "")
        if len(k_clean) >= 2 and k_clean not in ['the', 'and', 'all', 'out', 'for', 'skin', 'base', 'general', 'cosmic', 'penta']:
            unique_targets[k_clean] = cname

    custom_aliases = {
        'monkeyking': 'Wukong',
        'drmundo': 'Dr. Mundo',
        'mundo': 'Dr. Mundo',
        'masteryi': 'Master Yi',
        'twistedfate': 'Twisted Fate',
        'missfortune': 'Miss Fortune',
        'tahmkench': 'Tahm Kench',
        'xinzhao': 'Xin Zhao',
        'jarvaniv': 'Jarvan IV',
        'jarvan': 'Jarvan IV',
        'aurelionsol': 'Aurelion Sol',
        'kogmaw': "Kog'Maw",
        'chogath': "Cho'Gath",
        'khazix': "Kha'Zix",
        'kaisa': "Kai'Sa",
        'ksante': "K'Sante",
        'belveth': "Bel'Veth",
        'reksai': "Rek'Sai",
        'velkoz': "Vel'Koz",
        'leblanc': "LeBlanc"
    }
    for k, v in custom_aliases.items():
        unique_targets[k] = v

    return sorted(unique_targets.items(), key=lambda x: len(x[0]), reverse=True)

def parse_event(ev_str, speaker_canonical, champ_skins, all_target_keys, known_transcripts):
    ev_lower = ev_str.lower()

    action_match = re.search(r'(firstencounter|encounter|kill|firstblood|slay|tauntresponse|taunt|jokeresponse|joke|allyencounter|ally|spellcast|spell|attack|assist|hit|steal|ult)', ev_lower)
    if not action_match:
        return None

    act_raw = action_match.group(1)
    if act_raw in ['kill', 'firstblood', 'slay']:
        action = 'katletme'
    elif 'taunt' in act_raw:
        action = 'kiskirtma'
    elif 'joke' in act_raw:
        action = 'saka'
    elif 'ally' in act_raw:
        action = 'dost_karsilasma'
    elif act_raw in ['spell', 'spellcast', 'attack', 'assist', 'hit', 'steal', 'ult']:
        action = 'yetenek_etkilesimi'
    else:
        action = 'karsilasma'

    # 1. Speaker skin extraction
    spk_chunk = ev_str[:action_match.start()]
    spk_skin_num = 0
    m_spk_skin = re.search(r'skin0*([0-9]{1,2})', spk_chunk, re.IGNORECASE)
    if m_spk_skin:
        try:
            spk_skin_num = int(m_spk_skin.group(1))
        except ValueError:
            spk_skin_num = 0

    # 2. Target info after action
    after_action = ev_lower[action_match.end():]
    after_clean = re.sub(r'^(?:3d|2d|firstally|ally|_)+', '', after_action)
    after_clean_no_under = after_clean.replace('_', '')

    # Filter out generic ambient cues that are NOT champion interactions
    if re.match(r'^(?:general|minion|turret|tower|dragon|baron|herald|monster|shop|item|respawn|recall)', after_clean_no_under):
        return None

    found_target_canonical = None
    target_skin_num = 0
    spk_clean = speaker_canonical.lower().replace(' ', '').replace("'", "")

    for tgt_key, tgt_canonical in all_target_keys:
        if tgt_key == spk_clean:
            # Skip self-targeted interactions
            continue

        if after_clean_no_under.startswith(tgt_key):
            remainder = after_clean_no_under[len(tgt_key):]
            if len(tgt_key) <= 3 and remainder and not remainder.startswith('skin') and not remainder.isdigit() and remainder not in ['k', 'end', 'start']:
                continue

            found_target_canonical = tgt_canonical
            m_ts = re.search(r'skin0*([0-9]{1,2})', remainder)
            if m_ts:
                try:
                    target_skin_num = int(m_ts.group(1))
                except ValueError:
                    target_skin_num = 0
            break

    if not found_target_canonical:
        return None

    # Resolve Turkish Display Names
    spk_low = speaker_canonical.lower()
    tgt_low = found_target_canonical.lower()

    spk_skin_name = champ_skins.get(spk_low, {}).get(spk_skin_num)
    if not spk_skin_name:
        spk_skin_name = f"Varsayılan {speaker_canonical}" if spk_skin_num == 0 else f"{speaker_canonical} (Kostüm {spk_skin_num})"

    tgt_skin_name = champ_skins.get(tgt_low, {}).get(target_skin_num)
    if not tgt_skin_name:
        tgt_skin_name = f"Varsayılan {found_target_canonical}" if target_skin_num == 0 else f"{found_target_canonical} (Kostüm {target_skin_num})"

    spk_is_base = (spk_skin_num == 0)
    tgt_is_base = (target_skin_num == 0)

    if spk_is_base and tgt_is_base:
        matrix_type = "base_to_base"
    elif not spk_is_base and tgt_is_base:
        matrix_type = "skin_to_base"
    elif spk_is_base and not tgt_is_base:
        matrix_type = "base_to_skin"
    else:
        matrix_type = "skin_to_skin"

    # Reference ID (Virtual Lightweight Pointer - No audio file needed)
    ref_id = f"{speaker_canonical}_{ev_str}"

    # Lookup transcript if available
    transcript = known_transcripts.get(ev_lower, '')
    if not transcript:
        # Try finding transcript with speaker / action prefix
        for k, txt in known_transcripts.items():
            if spk_low in k and tgt_low in k and action in k:
                transcript = txt
                break

    return {
        "speaker_champ": speaker_canonical,
        "speaker_skin_num": spk_skin_num,
        "speaker_skin_name": spk_skin_name,
        "speaker_is_base": spk_is_base,
        "target_champ": found_target_canonical,
        "target_skin_num": target_skin_num,
        "target_skin_name": tgt_skin_name,
        "target_is_base": tgt_is_base,
        "matrix_type": matrix_type,
        "action_type": action,
        "raw_event": ev_str,
        "ref_id": ref_id,
        "transcript": transcript
    }

def scan_champion_wad(speaker_file_name, champ_canonical, champ_skins, all_target_keys, known_transcripts):
    speaker_raw = speaker_file_name.replace('.wad.client', '')
    speaker_canonical = champ_canonical.get(speaker_raw.lower(), speaker_raw.capitalize())

    # Check both default and tr_TR WAD files to extract complete BNKs and voice events
    wad_candidates = []
    wad_p1 = os.path.join(WAD_DIR, speaker_file_name)
    if os.path.exists(wad_p1):
        wad_candidates.append(wad_p1)
    
    tr_name = f"{speaker_raw}.tr_TR.wad.client"
    wad_p2 = os.path.join(WAD_DIR, tr_name)
    if os.path.exists(wad_p2) and wad_p2 != wad_p1:
        wad_candidates.append(wad_p2)

    if not wad_candidates:
        return []

    dctx = zstd.ZstdDecompressor()
    events = set()
    bnks = []
    wpk_wems = set()

    for wp in wad_candidates:
        is_audio_wad = wp.endswith('.tr_TR.wad.client')
        try:
            with open(wp, 'rb') as f:
                f.seek(268)
                fc_bytes = f.read(4)
                if len(fc_bytes) < 4:
                    continue
                fc = struct.unpack('<I', fc_bytes)[0]
                entries = f.read(fc * 32)
                for i in range(fc):
                    eb = entries[i*32 : (i+1)*32]
                    phash, doff, csz, usz, tflags = struct.unpack('<QIII4s', eb[:24])
                    if csz <= 0:
                        continue
                    # Skip massive meshes/textures in base WAD (> 1.2 MB)
                    if not is_audio_wad and usz > 1200000:
                        continue
                    f.seek(doff)
                    raw = f.read(csz)
                    try:
                        data = dctx.decompress(raw, max_output_size=usz) if (tflags[0]&0xF) == 3 else raw
                        if is_audio_wad and len(data) >= 4 and data[:4] == b'BKHD':
                            bnks.append(data)
                        elif is_audio_wad and len(data) >= 12 and data[:4] == b'r3d2':
                            magic, version, count = struct.unpack('<4sII', data[:12])
                            if 0 < count and len(data) >= (12 + count * 4):
                                offsets = struct.unpack(f'<{count}I', data[12 : 12 + count * 4])
                                for entry_offset in offsets:
                                    if entry_offset + 12 <= len(data):
                                        off, sz, name_len = struct.unpack('<III', data[entry_offset : entry_offset + 12])
                                        name_raw = data[entry_offset + 12 : entry_offset + 12 + name_len * 2].decode('utf-16le', errors='ignore')
                                        try:
                                            wid = int(name_raw.replace('.wem', '').strip())
                                            wpk_wems.add(wid)
                                        except ValueError:
                                            pass
                        elif len(data) >= 4 and (data[:4] == b'PROP' or data[:4] == b'BKHD'):
                            for m in re.findall(rb'(?:Play_vo_|vo_)[a-zA-Z0-9_]+', data):
                                events.add(m.decode('ascii', errors='ignore'))
                    except Exception:
                        pass
        except Exception as e:
            print(f"⚠️ Error reading {wp}: {e}")

    # First parse interaction events
    parsed_events = []
    for ev in events:
        p = parse_event(ev, speaker_canonical, champ_skins, all_target_keys, known_transcripts)
        if p:
            parsed_events.append((ev, p))

    if not parsed_events:
        return []

    # Map events to WEMs via HIRC Soundbanks
    target_map = {}
    for ev, p in parsed_events:
        target_map[ref_ext.fnv_1(ev)] = ev
        clean_ev = re.sub(r'(K|k)$', '', ev)
        if clean_ev != ev:
            target_map[ref_ext.fnv_1(clean_ev)] = ev

    event_to_wems = {}
    for b in bnks:
        w2e = ref_ext.parse_hirc_soundbank(b, target_map)
        for w, ev_name in w2e.items():
            if ev_name not in event_to_wems:
                event_to_wems[ev_name] = []
            if w not in event_to_wems[ev_name]:
                event_to_wems[ev_name].append(w)

    results = []
    seen = set()

    for ev, p in parsed_events:
        # If event is a 2D trigger and a 3D spatial voice event exists, skip 2D to prevent 404s!
        if '2d' in ev.lower():
            ev_3d = re.sub(r'2d', '3D', ev, flags=re.IGNORECASE)
            if any(other_ev == ev_3d for other_ev, _ in parsed_events):
                continue

        wems = event_to_wems.get(ev, [])
        if not wems:
            clean_ev = re.sub(r'(K|k)$', '', ev)
            wems = event_to_wems.get(clean_ev, [])

        # Filter WEMs to ONLY those that actually exist in physical WPK files!
        if wpk_wems and wems:
            valid_wems = [w for w in wems if w in wpk_wems]
            if valid_wems:
                wems = valid_wems
            else:
                # If resolved WEMs are not in WPK, don't invent ghost variations
                wems = [None]
        elif not wems:
            wems = [None]

        # Skip empty 2D events that have no WEM
        if not wems[0] and '2d' in ev.lower():
            continue

        total_vars = len(wems)
        for idx, wid in enumerate(wems):
            var_num = idx + 1
            k = (p['speaker_champ'], p['speaker_skin_num'], p['target_champ'], p['target_skin_num'], ev, wid)
            if k in seen:
                continue
            seen.add(k)

            # Look up transcript: 1. by WEM ID, 2. by event_wid, 3. by raw_event
            transcript = ""
            if wid:
                transcript = known_transcripts.get(str(wid), "")
                if not transcript:
                    transcript = known_transcripts.get(f"{ev}_{wid}".lower(), "")
            if not transcript:
                transcript = known_transcripts.get(ev.lower(), "")
            if not transcript and p.get('transcript'):
                transcript = p['transcript']

            # Action naming & variation tag
            base_act = p['action_type']
            if total_vars > 1:
                display_action = f"{base_act} #{var_num}"
                var_tag = f"Varyasyon {var_num}/{total_vars}"
            else:
                display_action = base_act
                var_tag = "Tekil Replik"

            ref_id = f"{speaker_canonical}_{ev}_{wid}" if wid else f"{speaker_canonical}_{ev}"

            item = dict(p)
            item['action_type'] = display_action
            item['base_action'] = base_act
            item['variation_index'] = var_num
            item['variation_total'] = total_vars
            item['variation_tag'] = var_tag
            item['wem_id'] = wid
            item['ref_id'] = ref_id
            item['transcript'] = transcript

            results.append(item)

    return results

def main():
    start_time = time.time()
    print("================================================================================")
    print("🚀 LEAGUE OF LEGENDS - GLOBAL ATIF VE ETKİLEŞİM VERİTABANI (v5 SIFIR-SES)")
    print("================================================================================")

    champ_canonical, champ_ids, champ_skins = load_skins_and_metadata()
    print(f"✅ Kostüm ve şampiyon veritabanı yüklendi: {len(champ_canonical)} isim anahtarı, {len(champ_skins)} şampiyon.")

    known_transcripts = load_known_transcripts()
    print(f"📖 Mevcut önbelleklerden {len(known_transcripts)} adet Türkçe replik metni indekslendi.")

    all_target_keys = build_target_dictionary(champ_canonical)

    if not os.path.exists(WAD_DIR):
        print(f"❌ LoL şampiyon dizini bulunamadı: {WAD_DIR}")
        return

    wad_files = [f for f in sorted(os.listdir(WAD_DIR)) if f.endswith('.wad.client') and '.' not in f.replace('.wad.client', '')]
    print(f"📦 Taranacak ana şampiyon WAD dosyası sayısı: {len(wad_files)}", flush=True)
    print(f"⚡ 16 İş parçacığı ile bellek içi WAD atıf taraması başlatılıyor...", flush=True)

    all_interactions = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
        futures = {executor.submit(scan_champion_wad, wf, champ_canonical, champ_skins, all_target_keys, known_transcripts): wf for wf in wad_files}
        completed_count = 0
        for f in concurrent.futures.as_completed(futures):
            res = f.result()
            all_interactions.extend(res)
            completed_count += 1
            if completed_count % 10 == 0 or completed_count == len(wad_files):
                print(f"  -> {completed_count}/{len(wad_files)} şampiyon WAD'ı tarandı... ({len(all_interactions)} ilişki bulundu)", flush=True)

    print(f"\n✨ WAD taraması tamamlandı! Toplam {len(all_interactions)} deterministik sözlü atıf tespit edildi.", flush=True)

    # Group by target and speaker
    by_target = {}
    by_speaker = {}
    vs_matrix = {}

    all_champs_set = set()
    for wf in wad_files:
        c_raw = wf.replace('.wad.client', '')
        c_can = champ_canonical.get(c_raw.lower(), c_raw.capitalize())
        all_champs_set.add(c_can)

    for item in all_interactions:
        tgt = item['target_champ']
        spk = item['speaker_champ']
        all_champs_set.add(tgt)
        all_champs_set.add(spk)

        by_target.setdefault(tgt, []).append(item)
        by_speaker.setdefault(spk, []).append(item)

        pair_key = tuple(sorted([spk, tgt]))
        if pair_key[0] not in vs_matrix:
            vs_matrix[pair_key[0]] = {}
        if pair_key[1] not in vs_matrix[pair_key[0]]:
            vs_matrix[pair_key[0]][pair_key[1]] = {"first_to_second": 0, "second_to_first": 0}

        if spk == pair_key[0]:
            vs_matrix[pair_key[0]][pair_key[1]]["first_to_second"] += 1
        else:
            vs_matrix[pair_key[0]][pair_key[1]]["second_to_first"] += 1

    # Sort incoming and outgoing items
    for t in by_target:
        by_target[t].sort(key=lambda x: (x['matrix_type'], x['speaker_champ'], x['raw_event']))
    for s in by_speaker:
        by_speaker[s].sort(key=lambda x: (x['matrix_type'], x['target_champ'], x['raw_event']))

    champions_data = []
    matrix_global_totals = {"base_to_base": 0, "skin_to_base": 0, "base_to_skin": 0, "skin_to_skin": 0}

    for c_name in sorted(list(all_champs_set)):
        incoming = by_target.get(c_name, [])
        outgoing = by_speaker.get(c_name, [])

        m_inc = {"base_to_base": 0, "skin_to_base": 0, "base_to_skin": 0, "skin_to_skin": 0}
        act_inc = {}
        spk_inc_map = {}
        for it in incoming:
            m_inc[it['matrix_type']] += 1
            matrix_global_totals[it['matrix_type']] += 1
            act_inc[it['action_type']] = act_inc.get(it['action_type'], 0) + 1
            spk_inc_map[it['speaker_champ']] = spk_inc_map.get(it['speaker_champ'], 0) + 1

        m_out = {"base_to_base": 0, "skin_to_base": 0, "base_to_skin": 0, "skin_to_skin": 0}
        act_out = {}
        tgt_out_map = {}
        for it in outgoing:
            m_out[it['matrix_type']] += 1
            act_out[it['action_type']] = act_out.get(it['action_type'], 0) + 1
            tgt_out_map[it['target_champ']] = tgt_out_map.get(it['target_champ'], 0) + 1

        top_speakers = [{"name": s, "count": c, "icon_url": get_champ_icon(s, champ_ids)} 
                        for s, c in sorted(spk_inc_map.items(), key=lambda x: x[1], reverse=True)]

        top_targets = [{"name": t, "count": c, "icon_url": get_champ_icon(t, champ_ids)} 
                       for t, c in sorted(tgt_out_map.items(), key=lambda x: x[1], reverse=True)]

        champions_data.append({
            "name": c_name,
            "id": champ_ids.get(c_name.lower(), 0),
            "icon_url": get_champ_icon(c_name, champ_ids),
            "total_incoming": len(incoming),
            "total_outgoing": len(outgoing),
            "unique_speakers_incoming": len(spk_inc_map),
            "unique_targets_outgoing": len(tgt_out_map),
            "matrix_incoming": m_inc,
            "matrix_outgoing": m_out,
            "actions_incoming": act_inc,
            "actions_outgoing": act_out,
            "top_speakers": top_speakers[:20],
            "top_targets": top_targets[:20],
            "incoming_items": incoming,
            "outgoing_items": outgoing
        })

    champions_data.sort(key=lambda x: x['total_incoming'], reverse=True)

    final_payload = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_champions": len(champions_data),
        "total_interactions": len(all_interactions),
        "global_matrix": matrix_global_totals,
        "champions": champions_data
    }

    print(f"💾 JSON dosyası diske yazılıyor: {OUTPUT_JSON_PATH}...")
    with open(OUTPUT_JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(final_payload, f, ensure_ascii=False, indent=2)

    if os.path.exists(os.path.dirname(VITE_PUBLIC_JSON)):
        print(f"📋 Vite public dizinine kopyalanıyor: {VITE_PUBLIC_JSON}...")
        with open(VITE_PUBLIC_JSON, 'w', encoding='utf-8') as f:
            json.dump(final_payload, f, ensure_ascii=False, indent=2)

    vite_dist_json = os.path.join(ROOT_DIR, "lol-matrix-web", "dist", "data", "lol_matrix_data.json")
    if os.path.exists(os.path.dirname(vite_dist_json)):
        with open(vite_dist_json, 'w', encoding='utf-8') as f:
            json.dump(final_payload, f, ensure_ascii=False, indent=2)

    file_size_mb = os.path.getsize(OUTPUT_JSON_PATH) / (1024 * 1024)
    print(f"🎉 BAŞARILI! Veritabanı oluşturuldu: {file_size_mb:.2f} MB ({len(champions_data)} şampiyon, {len(all_interactions)} eksiksiz atıf).")
    print(f"⏱️ Toplam geçen süre: {time.time() - start_time:.2f} saniye.")

if __name__ == '__main__':
    main()
