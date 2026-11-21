import os
import sys
import json
import threading

SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import extract_target_references as ref_extractor
from contextlib import redirect_stdout

def handle_references_get(handler, path, params, context):
    CHAMPIONS_OUTPUT_PATH = context['CHAMPIONS_OUTPUT_PATH']
    # 5. Get Reverse References Tree
    if path == '/api/references-tree':
        target = params.get('target', [''])[0]
        target_skin = params.get('skin', params.get('target_skin', ['']))[0]
        speaker_type = params.get('speaker_type', ['all'])[0].lower() # 'all', 'base_only', 'skins_only'

        if not target:
            handler.send_json([])
            return True

        target_dir = os.path.join(CHAMPIONS_OUTPUT_PATH, target, f"{target}e_Yapilan_Tum_Ozel_Atiflar")
        if not os.path.exists(target_dir):
            target_dir = os.path.join(CHAMPIONS_OUTPUT_PATH, f"Interactions_{target}")
            if not os.path.exists(target_dir):
                handler.send_json([])
                return True

        norm_skin = None
        if target_skin and target_skin.upper() != 'ALL':
            norm_skin = target_skin.lower().replace('_', '').replace(' ', '').replace("'", "")

        tree = []
        for cat_folder in sorted(os.listdir(target_dir)):
            if norm_skin:
                clean_cat = cat_folder.lower().replace('_', '').replace(' ', '')
                if norm_skin not in clean_cat and clean_cat not in norm_skin:
                    continue

            cat_path = os.path.join(target_dir, cat_folder)
            if not os.path.isdir(cat_path):
                continue

            speakers = []

            # 1. Doğrudan cat_path içinde yer alan .wav dosyalarını kontrol et (Düz / Flat Yapı)
            direct_wavs = [f for f in sorted(os.listdir(cat_path)) if f.lower().endswith('.wav')]
            if direct_wavs and speaker_type != 'skins_only':
                by_speaker = {}
                for fname in direct_wavs:
                    spk_name = fname.split('_')[0].capitalize()
                    if spk_name not in by_speaker:
                        by_speaker[spk_name] = []
                    by_speaker[spk_name].append({
                        "name": fname,
                        "path": os.path.join(cat_path, fname)
                    })
                for spk_name, files in sorted(by_speaker.items()):
                    speakers.append({
                        "speakerChampion": spk_name,
                        "skins": [{
                            "skinName": "Varsayilan_Hali",
                            "isBase": True,
                            "files": files
                        }]
                    })

            # 2. Alt klasörleri kontrol et (Hiyerarşik Yapı)
            for spk_folder in sorted(os.listdir(cat_path)):
                spk_path = os.path.join(cat_path, spk_folder)
                if not os.path.isdir(spk_path):
                    continue

                skins = []
                for sk_folder in sorted(os.listdir(spk_path)):
                    sk_path = os.path.join(spk_path, sk_folder)
                    if not os.path.isdir(sk_path):
                        continue

                    is_base = (sk_folder == "Varsayilan_Hali" or "varsayilan" in sk_folder.lower())

                    if speaker_type == 'base_only' and not is_base:
                        continue
                    if speaker_type == 'skins_only' and is_base:
                        continue

                    files = []
                    for fname in sorted(os.listdir(sk_path)):
                        if fname.lower().endswith('.wav'):
                            files.append({
                                "name": fname,
                                "path": os.path.join(sk_path, fname)
                            })

                    if files:
                        skins.append({
                            "skinName": sk_folder,
                            "isBase": is_base,
                            "files": files
                        })

                if skins:
                    speakers.append({
                        "speakerChampion": spk_folder,
                        "skins": skins
                    })

            if speakers:
                tree.append({
                    "category": cat_folder,
                    "speakers": speakers
                })

        handler.send_json(tree)
        return True

    # 6. Detailed Analytics for Reverse References (Matrix & Statistics)
    if path == '/api/references-analytics':
        target = params.get('target', [''])[0]
        ROOT_DIR = context.get('ROOT_DIR', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        # Helper: load skin metadata for icons
        skins_db_path = os.path.join(ROOT_DIR, "all_lol_skins_database.json")
        champ_id_map = {}
        champ_alias_map = {}
        if os.path.exists(skins_db_path):
            try:
                with open(skins_db_path, 'r', encoding='utf-8') as f:
                    skins_data = json.load(f)
                    for s in skins_data:
                        c_name = s.get('champion_name') or s.get('champion_alias')
                        c_id = s.get('champion_id')
                        c_alias = s.get('champion_alias')
                        if c_name and c_id:
                            champ_id_map[c_name.lower()] = c_id
                            champ_alias_map[c_name.lower()] = c_alias
            except Exception:
                pass

        def get_champ_icon(name):
            cid = champ_id_map.get(name.lower())
            if cid:
                return f"https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/champion-icons/{cid}.png"
            alias = champ_alias_map.get(name.lower(), name)
            return f"https://ddragon.leagueoflegends.com/cdn/14.20.1/img/champion/{alias}.png"

        # If no target specified, return summary stats for all champions
        if not target:
            champions_summary = []
            seen = set()
            LOL_CHAMPIONS_PATH = context.get('LOL_CHAMPIONS_PATH', '')
            wad_champs = []
            if os.path.exists(LOL_CHAMPIONS_PATH):
                for f in sorted(os.listdir(LOL_CHAMPIONS_PATH)):
                    if f.endswith('.wad.client'):
                        c_name = f.replace('.wad.client', '').split('.')[0]
                        if c_name and c_name not in seen:
                            seen.add(c_name)
                            wad_champs.append(c_name)
            if not wad_champs and champ_alias_map:
                wad_champs = sorted(list(set(champ_alias_map.values())))
            
            for c_name in sorted(wad_champs):
                target_dir = os.path.join(CHAMPIONS_OUTPUT_PATH, c_name, f"{c_name}e_Yapilan_Tum_Ozel_Atiflar")
                is_ext = os.path.exists(target_dir)
                total_q = 0
                speakers_set = set()
                base_to_base = 0
                if is_ext:
                    for root, dirs, files in os.walk(target_dir):
                        wavs = [f for f in files if f.lower().endswith('.wav')]
                        total_q += len(wavs)
                        if wavs:
                            rel = os.path.relpath(root, target_dir)
                            parts = rel.split(os.sep)
                            if len(parts) >= 2:
                                speakers_set.add(parts[1])
                                if "varsayilan" in parts[0].lower() and ("varsayilan" in parts[-1].lower() or parts[-1] == "Varsayilan_Hali"):
                                    base_to_base += len(wavs)
                
                champions_summary.append({
                    "name": c_name,
                    "icon_url": get_champ_icon(c_name),
                    "is_extracted": is_ext,
                    "total_quotes": total_q,
                    "speakers_count": len(speakers_set),
                    "base_to_base": base_to_base
                })

            handler.send_json(champions_summary)
            return True

        # Target specific deep analysis
        target_dir = os.path.join(CHAMPIONS_OUTPUT_PATH, target, f"{target}e_Yapilan_Tum_Ozel_Atiflar")
        if not os.path.exists(target_dir):
            target_dir = os.path.join(CHAMPIONS_OUTPUT_PATH, f"Interactions_{target}")
        
        if not os.path.exists(target_dir):
            handler.send_json({
                "target": target,
                "icon_url": get_champ_icon(target),
                "is_extracted": False,
                "total_quotes": 0,
                "unique_speakers": 0,
                "matrix": {"base_to_base": 0, "skin_to_base": 0, "base_to_skin": 0, "skin_to_skin": 0},
                "action_types": {},
                "speakers": [],
                "items": []
            })
            return True

        voice_cache_file = os.path.join(CHAMPIONS_OUTPUT_PATH, target, ".ai_voice_cache.json")
        voice_cache = {}
        if os.path.exists(voice_cache_file):
            try:
                with open(voice_cache_file, 'r', encoding='utf-8') as f:
                    voice_cache = json.load(f)
            except Exception:
                pass

        items = []
        matrix_counts = {"base_to_base": 0, "skin_to_base": 0, "base_to_skin": 0, "skin_to_skin": 0}
        action_counts = {}
        speakers_map = {}
        target_skins_set = set()

        for cat_folder in sorted(os.listdir(target_dir)):
            cat_path = os.path.join(target_dir, cat_folder)
            if not os.path.isdir(cat_path):
                continue

            is_target_base = ("varsayilan" in cat_folder.lower())
            target_skin_clean = cat_folder.replace(f"{target}e_Yapilan_Atiflar", "").replace("_", " ").strip()
            if not target_skin_clean:
                target_skin_clean = "Varsayılan"
            target_skins_set.add(target_skin_clean)

            for spk_folder in sorted(os.listdir(cat_path)):
                spk_path = os.path.join(cat_path, spk_folder)
                if not os.path.isdir(spk_path):
                    if spk_folder.lower().endswith('.wav'):
                        fname = spk_folder
                        spk_name = fname.split('_')[0].capitalize()
                        is_speaker_base = True
                        speaker_skin_name = "Varsayılan Hali"
                        m_type = "base_to_base" if is_target_base else "base_to_skin"
                        matrix_counts[m_type] += 1

                        act = "karsilasma"
                        fn_low = fname.lower()
                        if "katletme" in fn_low or "kill" in fn_low:
                            act = "katletme"
                        elif "dost" in fn_low:
                            act = "dost_karsilasma"
                        elif "kiskirtma" in fn_low or "taunt" in fn_low:
                            act = "kiskirtma"
                        elif "saka" in fn_low or "joke" in fn_low:
                            act = "saka"
                        elif "yetenek" in fn_low:
                            act = "yetenek_etkilesimi"
                        action_counts[act] = action_counts.get(act, 0) + 1

                        text = voice_cache.get(fname, {}).get('text', '')
                        item = {
                            "file_name": fname,
                            "file_path": spk_path,
                            "target_skin": target_skin_clean,
                            "is_target_base": is_target_base,
                            "speaker_champion": spk_name,
                            "speaker_skin": speaker_skin_name,
                            "is_speaker_base": is_speaker_base,
                            "matrix_type": m_type,
                            "action_type": act,
                            "text": text
                        }
                        items.append(item)
                        if spk_name not in speakers_map:
                            speakers_map[spk_name] = {"count": 0, "skins": set()}
                        speakers_map[spk_name]["count"] += 1
                        speakers_map[spk_name]["skins"].add(speaker_skin_name)
                    continue

                spk_name = spk_folder
                for sk_folder in sorted(os.listdir(spk_path)):
                    sk_path = os.path.join(spk_path, sk_folder)
                    if not os.path.isdir(sk_path):
                        continue

                    is_speaker_base = ("varsayilan" in sk_folder.lower() or sk_folder == "Varsayilan_Hali")
                    speaker_skin_clean = sk_folder.replace("_", " ").strip()

                    for fname in sorted(os.listdir(sk_path)):
                        if not fname.lower().endswith('.wav'):
                            continue

                        if is_target_base and is_speaker_base:
                            m_type = "base_to_base"
                        elif is_target_base and not is_speaker_base:
                            m_type = "skin_to_base"
                        elif not is_target_base and is_speaker_base:
                            m_type = "base_to_skin"
                        else:
                            m_type = "skin_to_skin"
                        matrix_counts[m_type] += 1

                        act = "karsilasma"
                        fn_low = fname.lower()
                        if "katletme" in fn_low or "kill" in fn_low:
                            act = "katletme"
                        elif "dost" in fn_low:
                            act = "dost_karsilasma"
                        elif "kiskirtma" in fn_low or "taunt" in fn_low:
                            act = "kiskirtma"
                        elif "saka" in fn_low or "joke" in fn_low:
                            act = "saka"
                        elif "yetenek" in fn_low:
                            act = "yetenek_etkilesimi"
                        action_counts[act] = action_counts.get(act, 0) + 1

                        text = voice_cache.get(fname, {}).get('text', '')
                        item = {
                            "file_name": fname,
                            "file_path": os.path.join(sk_path, fname),
                            "target_skin": target_skin_clean,
                            "is_target_base": is_target_base,
                            "speaker_champion": spk_name,
                            "speaker_skin": speaker_skin_clean,
                            "is_speaker_base": is_speaker_base,
                            "matrix_type": m_type,
                            "action_type": act,
                            "text": text
                        }
                        items.append(item)
                        if spk_name not in speakers_map:
                            speakers_map[spk_name] = {"count": 0, "skins": set()}
                        speakers_map[spk_name]["count"] += 1
                        speakers_map[spk_name]["skins"].add(speaker_skin_clean)

        speakers_list = []
        for spk, info in sorted(speakers_map.items(), key=lambda x: x[1]['count'], reverse=True):
            speakers_list.append({
                "speaker": spk,
                "icon_url": get_champ_icon(spk),
                "count": info["count"],
                "skins": sorted(list(info["skins"]))
            })

        handler.send_json({
            "target": target,
            "icon_url": get_champ_icon(target),
            "is_extracted": True,
            "total_quotes": len(items),
            "unique_speakers": len(speakers_list),
            "target_skins": sorted(list(target_skins_set)),
            "matrix": matrix_counts,
            "action_types": action_counts,
            "speakers": speakers_list,
            "items": items
        })
        return True

    return False

def handle_references_post(handler, path, body, context):
    broadcast_log = context['broadcast_log']
    LogStreamEmitter = context['LogStreamEmitter']
    # 2. Reverse References Extraction
    if path == '/api/extract-references':
        target_champion = body.get('target_champion')
        target_skin = body.get('target_skin', None)
        speaker_base_only = body.get('speaker_base_only', False)
        def run_ref():
            global is_busy
            is_busy = True
            emitter = LogStreamEmitter()
            try:
                skin_log = f" ({target_skin})" if (target_skin and target_skin.upper() != 'ALL') else ""
                spk_log = " [Sadece Varsayılan Kostümler]" if speaker_base_only else ""
                broadcast_log(f"🎯 Hedef: {target_champion}{skin_log}{spk_log} için tüm şampiyonlar taranıyor...")
                with redirect_stdout(emitter):
                    ref_extractor.extract_all_interactions_for_champion(target_champion, target_skin=target_skin, speaker_base_only=speaker_base_only)
                emitter.flush()
                is_busy = False
                broadcast_log(f"✨ {target_champion} için tüm atıflar başarıyla çıkarıldı!")
            except Exception as e:
                is_busy = False
                broadcast_log(f"❌ Hata oluştu: {e}")

        threading.Thread(target=run_ref, daemon=True).start()
        handler.send_json({"status": "started"})
        return True



    return False
