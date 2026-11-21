import os
import sys
import json
import base64
import threading
from contextlib import redirect_stdout, redirect_stderr

# Ensure scripts dir is in path
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.join(ROOT_DIR, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from metadata_manager import MetadataManager
import lol_voice_extractor_expert as voice_extractor
import extract_target_references as ref_extractor

LOL_CHAMPIONS_PATH = voice_extractor.LOL_CHAMPIONS_PATH
CHAMPIONS_OUTPUT_PATH = os.path.join(ROOT_DIR, "Champions")

CACHED_HASHES = None

class WebStreamEmitter:
    def __init__(self, callback):
        self.callback = callback
        self.buffer = ""

    def write(self, text):
        if not text:
            return
        self.buffer += text
        while "\n" in self.buffer:
            line, self.buffer = self.buffer.split("\n", 1)
            line = line.strip()
            if line:
                self.callback(line)

    def flush(self):
        if self.buffer.strip():
            self.callback(self.buffer.strip())
            self.buffer = ""

class AppAPI:
    def __init__(self):
        self.window = None
        self.meta_mgr = MetadataManager()
        self.is_busy = False

    def set_window(self, window):
        self.window = window

    def log(self, message):
        if self.window:
            safe_msg = json.dumps(message)
            self.window.evaluate_js(f"if (window.onLog) window.onLog({safe_msg});")

    def get_champions(self):
        champions = []
        seen = set()
        if os.path.exists(LOL_CHAMPIONS_PATH):
            for f in sorted(os.listdir(LOL_CHAMPIONS_PATH)):
                if f.endswith('.wad.client'):
                    base = f.replace('.wad.client', '')
                    ch = base.split('.')[0]
                    if ch and ch not in seen:
                        seen.add(ch)
                        champions.append(ch)
        if not champions and self.meta_mgr.skins_raw_db:
            for s in self.meta_mgr.skins_raw_db:
                c_name = s.get('champion_name') or s.get('champion_alias')
                if c_name and c_name not in seen:
                    seen.add(c_name)
                    champions.append(c_name)
        champions.sort()
        return champions

    def get_skins(self, champion_name):
        skins = []
        c_clean = champion_name.lower().replace("'", "").replace(" ", "").replace("_", "")
        skins_found = dict(self.meta_mgr.skins_by_champ.get(c_clean, {}))

        if not skins_found:
            for s in self.meta_mgr.skins_raw_db:
                c_alias = s.get('champion_alias', '').lower()
                c_name = s.get('champion_name', '').lower()
                if c_alias == c_clean or c_name == c_clean:
                    s_num = s.get('skin_num', 0)
                    s_name = s.get('name_tr', '')
                    if s_name:
                        skins_found[s_num] = s_name.replace(" ", "_")

        vo_info = voice_extractor.inspect_champion_skins_vo(champion_name)
        custom_vo_map = {}
        custom_vo_by_num = {}
        if vo_info.get('status') == 'success':
            for sk_item in vo_info.get('skins', []):
                clean_name = sk_item['skin_name'].lower().replace('_', '').replace(' ', '')
                custom_vo_map[clean_name] = sk_item
                custom_vo_map[sk_item['skin_id'].lower()] = sk_item
                s_num_val = sk_item.get('skin_num')
                if s_num_val is not None:
                    custom_vo_by_num[s_num_val] = sk_item
                if sk_item.get('is_base'):
                    custom_vo_by_num[0] = sk_item

        # Add "ALL" option first
        skins.append({
            "num": -1,
            "label": "🌟 Tüm Kostümleri Çıkar (Full Paket)",
            "display_name": "Tüm Kostümler (Full Paket)",
            "value": "ALL",
            "has_vo": True,
            "has_custom_vo": True,
            "vo_count": 0,
            "voice_type": "all",
            "vo_status_short": "Full Paket",
            "vo_status_text": "Tüm kostüm ses bankalarını tek tıkla çıkarır",
            "voice_badge": "🌟 FULL PAKET",
            "voice_desc": "Şampiyona ait tüm mevcut kostüm ses bankalarını tek tıkla çıkarır.",
            "is_recommended": False,
            "recommendation_text": "Toplu Çıkarma",
            "rarity_raw": "kAll",
            "rarity_tr": "Tüm Kostümler",
            "rarity_tier": "all",
            "cost_rp": 0,
            "release_date": "",
            "splash_url": "",
            "description_tr": "Şampiyona ait tüm kostümleri topluca çıkarma paketi."
        })

        for s_num, s_name in sorted(skins_found.items(), key=lambda x: x[0]):
            val = f"Varsayilan_{champion_name}" if s_num == 0 else s_name
            clean_lookup = val.lower().replace('_', '').replace(' ', '')
            skin_id_lookup = f"skin{s_num:02d}"
            
            vo_data = (
                custom_vo_by_num.get(s_num) or 
                custom_vo_map.get(clean_lookup) or 
                custom_vo_map.get(skin_id_lookup) or 
                custom_vo_map.get(f"skin{s_num}") or
                (custom_vo_by_num.get(0) if s_num == 0 else None)
            )
            
            has_vo = bool(vo_data)
            vo_count = vo_data.get('vo_count', 0) if vo_data else 0

            skin_info = self.meta_mgr.get_skin_info(champion_name, s_num) or {}
            rarity_raw = skin_info.get('rarity_raw', 'kNoRarity')
            rarity_tr = skin_info.get('rarity_tr', 'Varsayılan' if s_num == 0 else 'Standart / Yaygın')
            cost_rp = skin_info.get('cost_rp', 0)
            release_date = skin_info.get('release_date', '')
            splash_url = skin_info.get('splash_url', '')
            description_tr = skin_info.get('description_tr', '')

            rarity_tier = "standard"
            if s_num == 0 or skin_info.get('is_base'):
                rarity_tier = "base"
            elif "Legendary" in rarity_raw or "Efsanevi" in rarity_tr:
                rarity_tier = "legendary"
            elif "Mythic" in rarity_raw or "İhtişamlı" in rarity_tr or "Prestij" in rarity_tr:
                rarity_tier = "mythic"
            elif "Epic" in rarity_raw or "Destansı" in rarity_tr:
                rarity_tier = "epic"
            elif "Ultimate" in rarity_raw or "Ebedi" in rarity_tr:
                rarity_tier = "ultimate"
            elif "Exalted" in rarity_raw or "Transcendent" in rarity_raw or "Haşmetli" in rarity_tr or "Ulu" in rarity_tr:
                rarity_tier = "mythic"
            elif "Rare" in rarity_raw or "Nadir" in rarity_tr:
                rarity_tier = "rare"

            if s_num == 0:
                voice_type = "base"
                has_custom_vo = False
                vo_status_short = "Orijinal Dublaj"
                vo_status_text = f"Orijinal Şampiyon Dublajı ({vo_count or 71} Replik)"
                voice_badge = f"🎮 ORİJİNAL DUBLAJ ({vo_count or 71} Replik)"
                voice_desc = "Şampiyonun orijinal varsayılan Türkçe seslendirmesi."
                is_recommended = False
                recommendation_text = "Standart Şampiyon Sesi"
            elif vo_data:
                raw_type = vo_data.get('voice_type', 'unique')
                if raw_type == 'unique' or vo_data.get('is_recommended'):
                    voice_type = "unique"
                    has_custom_vo = True
                    vo_status_short = "Özel Dublaj: VAR"
                    vo_status_text = f"Özel Yeni Dublaj ({vo_count} Replik - Sıfırdan Kayıt)"
                    voice_badge = f"👑 ÖZEL DUBLAJ ({vo_count} Replik)"
                    voice_desc = "Tamamen sıfırdan kaydedilmiş bağımsız yeni replikler ve özel atıflar içerir."
                    is_recommended = True
                    recommendation_text = "🔥 Özel Yeni Dublaj"
                elif raw_type == 'filtered':
                    voice_type = "filtered"
                    has_custom_vo = True
                    vo_status_short = "Özel Efekt: VAR"
                    vo_status_text = f"Vokal Filtreli Dublaj ({vo_count} Replik - Ses Efektli)"
                    voice_badge = f"🎛️ ÖZEL EFEKT ({vo_count} Replik)"
                    voice_desc = f"Temel Türkçe seslendirme üzerine kostüme özel ses efekti/filtresi uygulanmıştır ({vo_count} ses)."
                    is_recommended = False
                    recommendation_text = "🎛️ Vokal Filtreli Dublaj"
                elif raw_type == 'partial':
                    voice_type = "partial"
                    has_custom_vo = True
                    vo_status_short = "Özel Dublaj: KISMİ"
                    vo_status_text = f"Kısmi Ses Bankası ({vo_count} Ek Replik)"
                    voice_badge = f"⚡ KISMİ DUBLAJ ({vo_count} Replik)"
                    voice_desc = f"Yalnızca {vo_count} adet ek replik/efekt barındırır."
                    is_recommended = False
                    recommendation_text = "Kısmi Sesler"
                else:
                    voice_type = raw_type
                    has_custom_vo = True
                    vo_status_short = "Özel Dublaj: VAR"
                    vo_status_text = f"Özel Ses Bankası ({vo_count} Replik)"
                    voice_badge = vo_data.get('voice_badge', f'🎙️ {vo_count} Replik')
                    voice_desc = vo_data.get('voice_desc', '')
                    is_recommended = vo_data.get('is_recommended', False)
                    recommendation_text = vo_data.get('recommendation_text', '')
            else:
                voice_type = "shared_base"
                has_custom_vo = False
                vo_status_short = "Özel Dublaj: YOK"
                vo_status_text = "Özel Dublaj Yok (Temel Dublajı Kullanır)"
                voice_badge = "❌ ÖZEL DUBLAJ: YOK"
                voice_desc = "Ayrı bir ses bankası yoktur; şampiyonun standart temel repliklerini kullanır."
                is_recommended = False
                recommendation_text = "Standart Şampiyon Sesi"

            display_name = f"Varsayılan {champion_name}" if s_num == 0 else s_name.replace('_', ' ')
            skins.append({
                "label": display_name,
                "display_name": display_name,
                "value": val,
                "num": s_num,
                "has_vo": has_vo,
                "has_custom_vo": has_custom_vo,
                "vo_count": vo_count,
                "voice_type": voice_type,
                "vo_status_short": vo_status_short,
                "vo_status_text": vo_status_text,
                "voice_badge": voice_badge,
                "voice_desc": voice_desc,
                "is_recommended": is_recommended,
                "recommendation_text": recommendation_text,
                "rarity_raw": rarity_raw,
                "rarity_tr": rarity_tr,
                "rarity_tier": rarity_tier,
                "cost_rp": cost_rp,
                "release_date": release_date,
                "splash_url": splash_url,
                "description_tr": description_tr
            })

        return skins

    def get_all_vo_map(self):
        vo_file = os.path.join(ROOT_DIR, "champions_vo_database.json")
        if os.path.exists(vo_file):
            try:
                with open(vo_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def get_cdn_skins_cached(self):
        """Returns skin list either freshly fetched from CDragon or from local database."""
        try:
            import urllib.request
            CD_PBE_URL = "https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/tr_tr/v1/skins.json"
            CD_CHAMPS_URL = "https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/tr_tr/v1/champion-summary.json"
            
            # Fast check if local database exists first
            local_db = self.meta_mgr.skins_raw_db
            return {"status": "success", "data": local_db, "is_live": False}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": self.meta_mgr.skins_raw_db}

    def get_extracted_tree(self, champion_name):
        target_dir = os.path.join(CHAMPIONS_OUTPUT_PATH, champion_name)
        if not os.path.exists(target_dir):
            return []

        tree = []
        for skin_dir in sorted(os.listdir(target_dir)):
            skin_path = os.path.join(target_dir, skin_dir)
            if not os.path.isdir(skin_path) or skin_dir.startswith('_'):
                continue

            categories = []
            for cat_dir in sorted(os.listdir(skin_path)):
                cat_path = os.path.join(skin_path, cat_dir)
                if not os.path.isdir(cat_path):
                    continue

                files = []
                for f in sorted(os.listdir(cat_path)):
                    if f.endswith('.wav'):
                        full_fpath = os.path.join(cat_path, f)
                        files.append({
                            "name": f,
                            "path": full_fpath
                        })

                if files:
                    categories.append({
                        "name": cat_dir,
                        "fileCount": len(files),
                        "files": files
                    })

            if categories:
                tree.append({
                    "skinName": skin_dir,
                    "categories": categories
                })

        return tree

    def get_references_tree(self, target_champion, target_skin=None, speaker_type='all'):
        target_dir = os.path.join(CHAMPIONS_OUTPUT_PATH, target_champion, f"{target_champion}e_Yapilan_Tum_Ozel_Atiflar")
        if not os.path.exists(target_dir):
            target_dir = os.path.join(CHAMPIONS_OUTPUT_PATH, f"Interactions_{target_champion}")
            if not os.path.exists(target_dir):
                return []

        norm_skin = None
        if target_skin and target_skin.upper() != 'ALL':
            norm_skin = target_skin.lower().replace('_', '').replace(' ', '').replace("'", "")

        speaker_type_lower = (speaker_type or 'all').lower()

        tree = []
        for root_cat in sorted(os.listdir(target_dir)):
            if norm_skin:
                clean_cat = root_cat.lower().replace('_', '').replace(' ', '')
                if norm_skin not in clean_cat and clean_cat not in norm_skin:
                    continue

            cat_path = os.path.join(target_dir, root_cat)
            if not os.path.isdir(cat_path):
                continue

            speakers = []
            for spk_champ in sorted(os.listdir(cat_path)):
                spk_path = os.path.join(cat_path, spk_champ)
                if not os.path.isdir(spk_path):
                    continue

                skins = []
                for spk_skin in sorted(os.listdir(spk_path)):
                    spk_skin_path = os.path.join(spk_path, spk_skin)
                    if not os.path.isdir(spk_skin_path):
                        continue

                    is_base = (spk_skin == "Varsayilan_Hali" or "varsayilan" in spk_skin.lower())

                    if speaker_type_lower == 'base_only' and not is_base:
                        continue
                    if speaker_type_lower == 'skins_only' and is_base:
                        continue

                    files = []
                    for f in sorted(os.listdir(spk_skin_path)):
                        if f.endswith('.wav'):
                            files.append({
                                "name": f,
                                "path": os.path.join(spk_skin_path, f)
                            })

                    if files:
                        skins.append({
                            "skinName": spk_skin,
                            "isBase": is_base,
                            "files": files
                        })

                if skins:
                    speakers.append({
                        "speakerChampion": spk_champ,
                        "skins": skins
                    })

            if speakers:
                tree.append({
                    "category": root_cat,
                    "speakers": speakers
                })

        return tree



    def get_audio_base64(self, file_path):
        if not file_path or not os.path.exists(file_path):
            return None
        try:
            with open(file_path, "rb") as f:
                data = base64.b64encode(f.read()).decode("ascii")
            
            # Check subtitle if exists
            subtitle = ""
            txt_path = file_path.replace('.wav', '.txt')
            if os.path.exists(txt_path):
                with open(txt_path, 'r', encoding='utf-8', errors='ignore') as tf:
                    subtitle = tf.read().strip()

            return {
                "base64": f"data:audio/wav;base64,{data}",
                "filename": os.path.basename(file_path),
                "subtitle": subtitle
            }
        except Exception as e:
            return {"error": str(e)}

    def open_output_dir(self, champion_name=None):
        if champion_name:
            target = os.path.join(CHAMPIONS_OUTPUT_PATH, champion_name)
        else:
            target = CHAMPIONS_OUTPUT_PATH
        os.makedirs(target, exist_ok=True)
        os.startfile(target)

    def extract_voices(self, champion_name, target_skin=None):
        if self.is_busy:
            return {"status": "error", "message": "Zaten devam eden bir işlem var!"}

        self.is_busy = True

        def run_task():
            global CACHED_HASHES
            try:
                self.log(f"🚀 [{champion_name}] {target_skin or 'Tüm Kostümler'} için ses çıkarma başlatıldı...")
                emitter = WebStreamEmitter(self.log)
                
                with redirect_stdout(emitter), redirect_stderr(emitter):
                    if CACHED_HASHES is None:
                        emitter.write("📂 Obsidian hash tablosu yükleniyor...\n")
                        CACHED_HASHES = voice_extractor.load_hashes()

                    voice_extractor.extract_champion_full(
                        champion_name,
                        CACHED_HASHES,
                        target_skin=target_skin
                    )
                emitter.flush()
                self.is_busy = False
                if self.window:
                    self.window.evaluate_js(f"if (window.onExtractionFinished) window.onExtractionFinished(true, '✅ {champion_name} sesleri başarıyla çıkarıldı!');")
            except Exception as e:
                self.is_busy = False
                self.log(f"❌ Hata oluştu: {e}")
                if self.window:
                    self.window.evaluate_js(f"if (window.onExtractionFinished) window.onExtractionFinished(false, '❌ Hata: {str(e)}');")

        thread = threading.Thread(target=run_task, daemon=True)
        thread.start()
        return {"status": "started"}

    def extract_references(self, target_champion, target_skin=None):
        if self.is_busy:
            return {"status": "error", "message": "Zaten devam eden bir işlem var!"}

        self.is_busy = True

        def run_task():
            try:
                skin_log = f" ({target_skin})" if (target_skin and target_skin.upper() != 'ALL') else ""
                self.log(f"🎯 [{target_champion.upper()}]{skin_log} için tüm şampiyon atıf taraması başlatıldı...")
                emitter = WebStreamEmitter(self.log)
                
                with redirect_stdout(emitter), redirect_stderr(emitter):
                    ref_extractor.extract_all_interactions_for_champion(target_champion, target_skin=target_skin)

                emitter.flush()
                self.is_busy = False
                if self.window:
                    self.window.evaluate_js(f"if (window.onReferencesFinished) window.onReferencesFinished(true, '✨ {target_champion} için tüm atıflar başarıyla çıkarıldı!');")
            except Exception as e:
                self.is_busy = False
                self.log(f"❌ Hata oluştu: {e}")
                if self.window:
                    self.window.evaluate_js(f"if (window.onReferencesFinished) window.onReferencesFinished(false, '❌ Hata: {str(e)}');")

        thread = threading.Thread(target=run_task, daemon=True)
        thread.start()
        return {"status": "started"}


    def download_cdn_asset(self, url, folder_name, filename):
        try:
            import urllib.request
            save_dir = os.path.join(CHAMPIONS_OUTPUT_PATH, "_CDN_Downloads", folder_name)
            os.makedirs(save_dir, exist_ok=True)
            save_path = os.path.join(save_dir, filename)

            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
            with urllib.request.urlopen(req, timeout=20) as resp:
                with open(save_path, 'wb') as f:
                    f.write(resp.read())

            self.log(f"💾 Başarıyla indirildi: {filename} -> {save_dir}")
            return {"status": "success", "path": save_path}
        except Exception as e:
            self.log(f"❌ İndirme hatası ({filename}): {e}")
            return {"status": "error", "message": str(e)}

    def open_download_folder(self, folder_name=None):
        if folder_name:
            target = os.path.join(CHAMPIONS_OUTPUT_PATH, "_CDN_Downloads", folder_name)
        else:
            target = os.path.join(CHAMPIONS_OUTPUT_PATH, "_CDN_Downloads")
        os.makedirs(target, exist_ok=True)
        os.startfile(target)

    def export_to_davinci(self, champion, skin, gap_seconds=0.8, fps=60, custom_files=None, fade_in_seconds=0.5, fade_out_seconds=0.3, background_media=None, include_splash=True, splash_pos_x=-430, splash_pos_y=160, splash_zoom=0.6, text_pos_x=-430, text_pos_y=-450, text_zoom=1.0, timeline_w=2560, timeline_h=1440):
        try:
            from davinci_exporter import DaVinciTimelineExporter
            files_to_export = []

            if custom_files and isinstance(custom_files, list) and len(custom_files) > 0:
                for rel_or_abs in custom_files:
                    if os.path.isabs(rel_or_abs) and os.path.exists(rel_or_abs):
                        files_to_export.append(rel_or_abs)
                    else:
                        full_p = os.path.join(CHAMPIONS_OUTPUT_PATH, rel_or_abs)
                        if os.path.exists(full_p):
                            files_to_export.append(full_p)
            else:
                search_dir = None
                if champion:
                    c_clean = champion.lower().replace(" ", "").replace("'", "").replace("_", "")
                    if os.path.exists(CHAMPIONS_OUTPUT_PATH):
                        for c_dir in os.listdir(CHAMPIONS_OUTPUT_PATH):
                            if c_dir.lower().replace(" ", "").replace("'", "").replace("_", "") == c_clean:
                                champ_full = os.path.join(CHAMPIONS_OUTPUT_PATH, c_dir)
                                search_dir = champ_full
                                if skin and skin != 'ALL':
                                    s_clean = skin.lower().replace(" ", "").replace("'", "").replace("_", "")
                                    for s_dir in os.listdir(champ_full):
                                        if s_dir.lower().replace(" ", "").replace("'", "").replace("_", "") == s_clean:
                                            search_dir = os.path.join(champ_full, s_dir)
                                            break
                                break

                if search_dir and os.path.exists(search_dir):
                    for root, _, fnames in os.walk(search_dir):
                        for fn in sorted(fnames):
                            if fn.lower().endswith('.wav'):
                                files_to_export.append(os.path.join(root, fn))

            if not files_to_export:
                return {
                    "status": "error",
                    "message": f"'{champion or 'Seçili'}' için henüz çıkarılmış ses dosyası bulunamadı."
                }

            safe_champ = (champion or 'LoL_Sesler').replace(' ', '_')
            safe_skin = (skin or 'Replikler').replace(' ', '_')
            xml_name = f"{safe_champ}_{safe_skin}_DaVinci_{gap_seconds}s_Gap.xml"

            target_dir = os.path.join(CHAMPIONS_OUTPUT_PATH, safe_champ)
            if os.path.exists(CHAMPIONS_OUTPUT_PATH):
                for d in os.listdir(CHAMPIONS_OUTPUT_PATH):
                    if d.lower().replace('_', '').replace(' ', '') == safe_champ.lower().replace('_', '').replace(' ', ''):
                        target_dir = os.path.join(CHAMPIONS_OUTPUT_PATH, d)
                        break

            if skin and skin != 'ALL':
                skin_path = os.path.join(target_dir, safe_skin)
                if os.path.exists(skin_path):
                    target_dir = skin_path
                elif os.path.exists(target_dir):
                    for sd in os.listdir(target_dir):
                        if sd.lower().replace('_', '').replace(' ', '') == safe_skin.lower().replace('_', '').replace(' ', ''):
                            target_dir = os.path.join(target_dir, sd)
                            break

            # Create dedicated DaVinci_XML subfolder inside skin directory
            xml_dir = os.path.join(target_dir, "DaVinci_XML")
            os.makedirs(xml_dir, exist_ok=True)
            out_xml_path = os.path.join(xml_dir, xml_name)

            t_name = f"{champion} {skin} ({gap_seconds}s Gap)".strip()
            saved_path, count, total_dur = DaVinciTimelineExporter.generate_fcp7_xml(
                files_to_export,
                out_xml_path,
                gap_seconds=gap_seconds,
                timeline_name=t_name,
                fps=fps,
                smart_sort=True,
                exclude_sfx=True,
                target_champion=champion,
                generate_srt=True,
                fade_in_seconds=fade_in_seconds,
                fade_out_seconds=fade_out_seconds,
                background_media=background_media,
                include_splash=include_splash,
                splash_pos_x=splash_pos_x,
                splash_pos_y=splash_pos_y,
                splash_zoom=splash_zoom,
                text_pos_x=text_pos_x,
                text_pos_y=text_pos_y,
                text_zoom=text_zoom,
                timeline_w=timeline_w,
                timeline_h=timeline_h
            )

            setting_path = os.path.splitext(saved_path)[0] + "_Daktilo_TextPlus.setting"
            has_setting = os.path.isfile(setting_path)

            self.log(f"🎬 DaVinci Resolve Timeline hazırlandı: {xml_name} ({count} ses, {gap_seconds}s aralık, In:{fade_in_seconds}s Out:{fade_out_seconds}s, {total_dur:.1f}s)")
            if has_setting:
                self.log(f"✨ Daktilo animasyonlu Text+ Fusion şablonu panonuza kopyalandı! DaVinci Fusion sayfasına geçip Ctrl+V yapabilirsiniz.")

            return {
                "status": "success",
                "file_path": saved_path,
                "file_name": os.path.basename(saved_path),
                "setting_path": setting_path if has_setting else None,
                "setting_name": os.path.basename(setting_path) if has_setting else None,
                "clipboard_copied": has_setting,
                "clips_count": count,
                "total_duration_sec": total_dur,
                "gap_seconds": gap_seconds,
                "fade_in_seconds": fade_in_seconds,
                "fade_out_seconds": fade_out_seconds
            }
        except Exception as e:
            self.log(f"❌ DaVinci Export Hatası: {e}")
            return {"status": "error", "message": str(e)}

    def davinci_get_status(self):
        try:
            from davinci_resolve_api import DaVinciResolveAPI
            return DaVinciResolveAPI.get_status()
        except Exception as e:
            return {"connected": False, "message": str(e)}

    def davinci_direct_push(self, champion, skin, gap_seconds=0.2, fade_in_seconds=1.5, fade_out_seconds=0.5, fps=60, custom_files=None):
        try:
            from davinci_resolve_api import DaVinciResolveAPI
            files_to_export = []
            if custom_files and isinstance(custom_files, list) and len(custom_files) > 0:
                files_to_export = [f for f in custom_files if os.path.isfile(f)]
            
            if not files_to_export:
                return {"status": "error", "message": "DaVinci'ye aktarılacak ses bulunamadı."}

            return DaVinciResolveAPI.create_direct_timeline_with_textplus(
                files_to_export,
                timeline_name=f"{champion} {skin}".strip() or "LoL Replikler",
                gap_seconds=gap_seconds,
                fade_in_sec=fade_in_seconds,
                fade_out_sec=fade_out_seconds,
                fps=fps,
                target_champion=champion
            )
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def davinci_convert_textplus(self, fade_in_seconds=1.5, fade_out_seconds=0.5):
        try:
            from davinci_resolve_api import DaVinciResolveAPI
            return DaVinciResolveAPI.convert_timeline_text_to_textplus(
                fade_in_sec=fade_in_seconds,
                fade_out_sec=fade_out_seconds
            )
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def davinci_install_scripts(self):
        try:
            from davinci_resolve_api import DaVinciResolveAPI
            return DaVinciResolveAPI.install_davinci_scripts()
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def open_file_location(self, file_path):
        try:
            if file_path and os.path.exists(file_path):
                import subprocess
                subprocess.Popen(f'explorer /select,"{os.path.abspath(file_path)}"')
                return {"status": "success"}
            return {"status": "error", "message": "Dosya bulunamadı"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

