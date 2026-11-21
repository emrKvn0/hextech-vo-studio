import os
import sys
import json
import shutil
import base64
import threading
import urllib.parse
import urllib.request
import http.server
import socketserver
import time
from contextlib import redirect_stdout, redirect_stderr

# Sistemdeki mevcut DaVinci Resolve NVIDIA CUDA 12 ve cuBLAS DLL'lerini otomatik bağla
davinci_dir = r"C:\Program Files\Blackmagic Design\DaVinci Resolve"
if os.path.exists(davinci_dir):
    try:
        os.add_dll_directory(davinci_dir)
    except Exception:
        pass
    os.environ['PATH'] = davinci_dir + ';' + os.environ.get('PATH', '')

def resolve_app_directories():
    candidates = [
        os.getcwd(),
        os.path.dirname(os.path.abspath(__file__)),
        os.path.dirname(sys.executable),
        os.path.abspath(os.path.join(os.path.dirname(sys.executable), "..")),
        os.path.abspath(os.path.join(os.path.dirname(sys.executable), "..", "..")),
        getattr(sys, '_MEIPASS', '')
    ]
    resolved_root = os.path.dirname(os.path.abspath(__file__))
    resolved_web = os.path.join(resolved_root, "web")
    for c in candidates:
        if c and os.path.exists(os.path.join(c, "web", "index.html")):
            resolved_root = c
            resolved_web = os.path.join(c, "web")
            break
    return resolved_root, resolved_web

ROOT_DIR, WEB_DIR = resolve_app_directories()
SCRIPTS_DIR = os.path.join(ROOT_DIR, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from metadata_manager import MetadataManager
import lol_voice_extractor_expert as voice_extractor
import extract_target_references as ref_extractor
from analyze_competitor_channels import run_competitor_analysis, get_available_channels
from davinci_exporter import DaVinciTimelineExporter
from davinci_resolve_api import DaVinciResolveAPI
import wallpaper_engine
import skin_sync_service

import server_routes.davinci_routes as davinci_routes
import server_routes.wallpapers_routes as wallpapers_routes
import server_routes.static_wallpapers_routes as static_wallpapers_routes
import server_routes.competitors_routes as competitors_routes
import server_routes.references_routes as references_routes
import server_routes.quotes_routes as quotes_routes
from text_normalizer import normalize_turkish_vo

LOL_CHAMPIONS_PATH = voice_extractor.LOL_CHAMPIONS_PATH
CHAMPIONS_OUTPUT_PATH = os.path.join(ROOT_DIR, "Champions")
VO_DB_FILE = os.path.join(ROOT_DIR, "champions_vo_database.json")

GLOBAL_VO_MAP = {}
def get_global_vo_map():
    global GLOBAL_VO_MAP
    if os.path.exists(VO_DB_FILE):
        try:
            with open(VO_DB_FILE, 'r', encoding='utf-8') as f:
                GLOBAL_VO_MAP = json.load(f)
        except Exception as e:
            print(f"⚠️ champions_vo_database.json yüklenirken hata: {e}")
    return GLOBAL_VO_MAP

get_global_vo_map()

SETTINGS_FILE = os.path.join(ROOT_DIR, ".app_storage", "app_settings.json")

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def update_setting(key, value):
    try:
        data = load_settings()
        data[key] = value
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"⚠️ update_setting hatası ({key}): {e}")

# Track last extracted champion in the active session
LAST_EXTRACTED_CHAMPION = None

def set_last_extracted_champion(champ_name):
    global LAST_EXTRACTED_CHAMPION
    if champ_name:
        LAST_EXTRACTED_CHAMPION = champ_name

def resolve_output_target_folder(requested_folder=None):
    """
    Kullanıcı çıktı klasörünü açmak istediğinde:
    1. Eğer özel bir alt klasör istendiyse (_CDN_Downloads vb.) ve varsa onu açar.
    2. Eğer bu oturumda bir ses çıkartılmışsa (LAST_EXTRACTED_CHAMPION), o şampiyonun klasörünü açar.
    3. Eğer henüz ses çıkartılmamışsa, doğrudan normal Champions ana klasörünü açar.
    """
    global LAST_EXTRACTED_CHAMPION

    AUDIO_EXTS = ('.wav', '.ogg', '.mp3', '.wem', '.flac')

    def folder_has_audio(fpath):
        if not os.path.isdir(fpath):
            return False
        for root, _, files in os.walk(fpath):
            if any(f.lower().endswith(AUDIO_EXTS) for f in files):
                return True
        return False

    # 1. Özel bir alt klasör istenmişse (_CDN_Downloads vb.)
    if requested_folder and requested_folder not in ('', 'auto', 'latest', 'ALL'):
        candidate = os.path.join(CHAMPIONS_OUTPUT_PATH, requested_folder)
        if os.path.isdir(candidate):
            if requested_folder.startswith('_') or 'Tum_Ozel_Atiflar' in requested_folder:
                return candidate
            if folder_has_audio(candidate):
                return candidate

    # 2. En son çıkartılan ses hangi karaktere aitse oraya git
    if LAST_EXTRACTED_CHAMPION:
        candidate = os.path.join(CHAMPIONS_OUTPUT_PATH, LAST_EXTRACTED_CHAMPION)
        if os.path.isdir(candidate) and folder_has_audio(candidate):
            return candidate

    # 3. Ses çıkartılmamışsa normal Champions klasörüne git!
    if not os.path.exists(CHAMPIONS_OUTPUT_PATH):
        os.makedirs(CHAMPIONS_OUTPUT_PATH, exist_ok=True)
    return CHAMPIONS_OUTPUT_PATH

# Global Event Listeners for SSE (Server-Sent Events) live log streaming
sse_clients = []
sse_lock = threading.Lock()

def broadcast_log(message):
    with sse_lock:
        data = f"data: {json.dumps(message, ensure_ascii=False)}\n\n"
        dead_clients = []
        for client_wfile in sse_clients:
            try:
                client_wfile.write(data.encode('utf-8'))
                client_wfile.flush()
            except Exception:
                dead_clients.append(client_wfile)
        for d in dead_clients:
            if d in sse_clients:
                sse_clients.remove(d)

class LogStreamEmitter:
    def __init__(self):
        self.buffer = ""
        self.lock = threading.Lock()

    def write(self, text):
        if not text:
            return
        with self.lock:
            self.buffer += str(text)
            while "\n" in self.buffer:
                line, self.buffer = self.buffer.split("\n", 1)
                clean_line = line.strip()
                if clean_line:
                    broadcast_log(clean_line)

    def flush(self):
        with self.lock:
            clean = self.buffer.strip()
            if clean:
                broadcast_log(clean)
            self.buffer = ""

meta_mgr = MetadataManager()
is_busy = False

class StudioHTTPHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_DIR, **kwargs)

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Cache-Control', 'no-cache')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        params = urllib.parse.parse_qs(parsed.query)

        # 1. Server-Sent Events (SSE) Live Log Stream
        if path == '/api/logs-stream':
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream; charset=utf-8')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Connection', 'keep-alive')
            self.end_headers()
            
            with sse_lock:
                sse_clients.append(self.wfile)
            
            # Keep connection open
            try:
                while True:
                    time.sleep(1)
            except Exception:
                with sse_lock:
                    if self.wfile in sse_clients:
                        sse_clients.remove(self.wfile)
            return

        # 2. Get Champions List
        if path == '/api/champions':
            champions = []
            seen = set()
            if os.path.exists(LOL_CHAMPIONS_PATH):
                for f in sorted(os.listdir(LOL_CHAMPIONS_PATH)):
                    if f.endswith('.wad.client'):
                        base = f.replace('.wad.client', '')
                        c_name = base.split('.')[0]
                        if c_name and c_name not in seen:
                            seen.add(c_name)
                            champions.append(c_name)
            # Fallback to database if no files found on disk
            if not champions and meta_mgr.skins_raw_db:
                for s in meta_mgr.skins_raw_db:
                    c_name = s.get('champion_name') or s.get('champion_alias')
                    if c_name and c_name not in seen:
                        seen.add(c_name)
                        champions.append(c_name)
            champions.sort()
            self.send_json(champions)
            return

        # 3. Get Skins for Champion (Enriched with Instant Wwise VO Bank Detection)
        if path == '/api/skins':
            champ = params.get('champion', [''])[0]
            if not champ:
                self.send_json([])
                return

            c_clean = champ.lower().replace("'", "").replace(" ", "").replace("_", "")
            skins_found = dict(meta_mgr.skins_by_champ.get(c_clean, {}))

            if not skins_found:
                for s in meta_mgr.skins_raw_db:
                    c_alias = s.get('champion_alias', '').lower()
                    c_name = s.get('champion_name', '').lower()
                    if c_alias == c_clean or c_name == c_clean:
                        s_num = s.get('skin_num', 0)
                        s_name = s.get('name_tr', '')
                        if s_name:
                            skins_found[s_num] = s_name.replace(" ", "_")

            # Check dedicated voice banks from WAD in 20ms
            vo_info = voice_extractor.inspect_champion_skins_vo(champ)
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

            results = [{
                "label": "🌟 Tüm Kostümleri Çıkar (Full Paket)",
                "display_name": "Tüm Kostümler (Full Paket)",
                "value": "ALL",
                "num": -1,
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
            }]

            for s_num, s_name in sorted(skins_found.items(), key=lambda x: x[0]):
                val = f"Varsayilan_{champ}" if s_num == 0 else s_name
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

                skin_info = meta_mgr.get_skin_info(champ, s_num) or {}
                rarity_raw = skin_info.get('rarity_raw', 'kNoRarity')
                rarity_tr = skin_info.get('rarity_tr', 'Varsayılan' if s_num == 0 else 'Standart / Yaygın')
                cost_rp = skin_info.get('cost_rp', 0)
                release_date = skin_info.get('release_date', '')
                splash_url = skin_info.get('splash_url', '')
                description_tr = skin_info.get('description_tr', '')

                # Determine rarity tier for UI filtering
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

                # Voice type and exact custom dubbing status determination
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

                display_name = f"Varsayılan {champ}" if s_num == 0 else s_name.replace('_', ' ')
                
                results.append({
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
            self.send_json(results)
            return

        # 3b. Dedicated Skin VO Inspection Endpoint
        if path == '/api/check-skin-vo':
            champ = params.get('champion', [''])[0]
            if not champ:
                self.send_json({"status": "error", "message": "Şampiyon belirtilmedi"}, 400)
                return
            res = voice_extractor.inspect_champion_skins_vo(champ)
            self.send_json(res)
            return

        # 3c. Global All Champions VO Map Endpoint (Instant CDN / SkinHub mapping)
        if path == '/api/all-vo-map':
            self.send_json(GLOBAL_VO_MAP)
            return

        # 4. Get Extracted Voices Tree
        if path == '/api/extracted-tree':
            champ = params.get('champion', [''])[0]
            if not champ:
                self.send_json([])
                return

            champ_dir = os.path.join(CHAMPIONS_OUTPUT_PATH, champ)
            if not os.path.exists(champ_dir):
                self.send_json([])
                return

            tree = []
            for skin_folder in sorted(os.listdir(champ_dir)):
                skin_path = os.path.join(champ_dir, skin_folder)
                if not os.path.isdir(skin_path) or skin_folder.startswith('_'):
                    continue

                categories = []
                root_files = []
                for item in sorted(os.listdir(skin_path)):
                    item_path = os.path.join(skin_path, item)
                    if os.path.isdir(item_path):
                        files = []
                        for fname in sorted(os.listdir(item_path)):
                            if fname.lower().endswith(('.wav', '.ogg', '.mp3')):
                                files.append({
                                    "name": fname,
                                    "path": os.path.join(item_path, fname)
                                })
                        if files:
                            categories.append({
                                "name": item,
                                "files": files,
                                "fileCount": len(files)
                            })
                    elif os.path.isfile(item_path) and item.lower().endswith(('.wav', '.ogg', '.mp3')):
                        root_files.append({
                            "name": item,
                            "path": item_path
                        })

                if root_files:
                    categories.insert(0, {
                        "name": "0_Secim_ve_Ozel_Sesler",
                        "files": root_files,
                        "fileCount": len(root_files)
                    })

                if categories:
                    tree.append({
                        "skinName": skin_folder,
                        "categories": categories
                    })

            self.send_json(tree)
            return

        # Context for modular sub-routers
        ctx = {
            'ROOT_DIR': ROOT_DIR,
            'CHAMPIONS_OUTPUT_PATH': CHAMPIONS_OUTPUT_PATH,
            'LOL_CHAMPIONS_PATH': LOL_CHAMPIONS_PATH,
            'broadcast_log': broadcast_log,
            'meta_mgr': meta_mgr,
            'LogStreamEmitter': LogStreamEmitter
        }

        # 5. References Tree (Modular)
        if references_routes.handle_references_get(self, path, params, ctx):
            return

        # 5b. Quotes & Subtitles (Modular)
        if quotes_routes.handle_quotes_get(self, path, params, ctx):
            return

        # 6. Get Audio File (Direct Stream / Base64)
        if path == '/api/audio':
            filepath = params.get('path', [''])[0]
            if filepath and os.path.exists(filepath):
                try:
                    with open(filepath, 'rb') as f:
                        data = f.read()
                    self.send_response(200)
                    self.send_header('Content-Type', 'audio/wav')
                    self.send_header('Content-Length', str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                    return
                except Exception as e:
                    self.send_json({"error": str(e)}, 500)
                    return
            self.send_json({"error": "File not found"}, 404)
            return

        # 6b. JIT On-Demand Audio Streaming (Extracts & streams single event in ~80ms)
        if path == '/api/audio-play':
            speaker = params.get('speaker', [''])[0]
            raw_event = params.get('event', [''])[0]
            target = params.get('target', [''])[0]
            wem_id = params.get('wem_id', [''])[0] or None
            import jit_audio_streamer
            wav_path = jit_audio_streamer.get_or_extract_audio(speaker, raw_event, target, wem_id=wem_id)
            if wav_path and os.path.exists(wav_path):
                try:
                    with open(wav_path, 'rb') as f:
                        data = f.read()
                    self.send_response(200)
                    self.send_header('Content-Type', 'audio/wav')
                    self.send_header('Content-Length', str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                    return
                except Exception as e:
                    self.send_json({"error": str(e)}, 500)
                    return
            self.send_json({"error": "Audio cue could not be resolved from soundbank"}, 404)
            return

        # 7. Get Base Champions Hub Status
        if path == '/api/base-hub-status':
            try:
                import base_champions_hub as base_hub
                status = base_hub.get_hub_status()
                self.send_json({"status": "success", "data": status})
            except Exception as e:
                self.send_json({"status": "error", "message": str(e)}, 500)
            return

        # 8. Get / Save Settings
        if path == '/api/settings':
            settings_file = SETTINGS_FILE
            data = {"zoom_level": 1.0, "theme": "hextech"}
            if os.path.exists(settings_file):
                try:
                    with open(settings_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                except Exception:
                    pass
            self.send_json({"status": "success", "data": data})
            return

        # 9 & 10. Competitor Analysis (Modular)
        if competitors_routes.handle_competitors_get(self, path, params, ctx):
            return

        # 11, 12, 13. Wallpapers API (Modular)
        if wallpapers_routes.handle_wallpapers_get(self, path, params, ctx):
            return

        # 14. Static 4K Wallpapers API
        if static_wallpapers_routes.handle_static_wallpapers_get(self, path, params, ctx):
            return

        # 14. Static Database / File Fallback

        if path == '/all_lol_skins_database.json':
            db_file = os.path.join(ROOT_DIR, "all_lol_skins_database.json")
            if os.path.exists(db_file):
                with open(db_file, 'rb') as f:
                    content = f.read()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(content)
                return
        # Serve regular files from web directory
        return super().do_GET()

    def do_POST(self):
        try:
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path

            content_len = int(self.headers.get('Content-Length', 0))
            post_body = self.rfile.read(content_len) if content_len > 0 else b'{}'
            try:
                body = json.loads(post_body.decode('utf-8'))
            except Exception:
                body = {}

            # 0. Save App Settings (Zoom, Theme, Window)
            if path == '/api/settings':
                settings_file = SETTINGS_FILE
                current = {}
                if os.path.exists(settings_file):
                    try:
                        with open(settings_file, 'r', encoding='utf-8') as f:
                            current = json.load(f)
                    except Exception:
                        pass
                current.update(body)
                try:
                    with open(settings_file, 'w', encoding='utf-8') as f:
                        json.dump(current, f, ensure_ascii=False, indent=2)
                except Exception as e:
                    print(f"⚠️ Settings save error: {e}")
                self.send_json({"status": "success", "data": current})
                return

            # 0b. Live Update Transcript (Directly save user edits into master & pair cache)
            if path == '/api/update-transcript':
                wem_id = str(body.get('wem_id', ''))
                raw_text = body.get('transcript', '').strip()
                new_text = normalize_turkish_vo(raw_text)
                champA = body.get('champA', 'Rakan')
                champB = body.get('champB', 'Xayah')
                if not wem_id or not new_text:
                    self.send_json({"error": "wem_id and transcript required"}, 400)
                    return

                # Update master_transcripts.json
                master_file = os.path.join(ROOT_DIR, "cache", "master_transcripts.json")
                if os.path.exists(master_file):
                    try:
                        with open(master_file, 'r', encoding='utf-8') as f:
                            m_data = json.load(f)
                        m_data[wem_id] = new_text
                        for k in list(m_data.keys()):
                            if wem_id in k:
                                m_data[k] = new_text
                        with open(master_file, 'w', encoding='utf-8') as f:
                            json.dump(m_data, f, ensure_ascii=False, indent=2)
                    except Exception as e:
                        print(f"⚠️ Master update error: {e}")

                # Update pair cache if exists
                pair_cache = os.path.join(ROOT_DIR, "cache", "pair_interactions", f"{champA}_{champB}.json")
                if os.path.exists(pair_cache):
                    try:
                        with open(pair_cache, 'r', encoding='utf-8') as f:
                            p_data = json.load(f)
                        for c in p_data.get('dialogue_chains', []):
                            for t in c.get('turns', []):
                                if str(t.get('wem_id')) == wem_id:
                                    t['transcript'] = new_text
                        for s in p_data.get('sections', []):
                            for g in s.get('groups', []):
                                for q in g.get('quotes', []):
                                    if str(q.get('wem_id')) == wem_id:
                                        q['transcript'] = new_text
                        with open(pair_cache, 'w', encoding='utf-8') as f:
                            json.dump(p_data, f, ensure_ascii=False, indent=2)
                    except Exception as e:
                        print(f"⚠️ Pair update error: {e}")

                self.send_json({"status": "success", "wem_id": wem_id, "transcript": new_text})
                return

            # 1. Voice Extraction
            if path == '/api/extract':
                global is_busy
                if is_busy:
                    self.send_json({"status": "busy", "message": "Şu anda başka bir işlem yürütülüyor."}, 409)
                    return

                champ = body.get('champion')
                skin = body.get('skin')

                def run_extract():
                    global is_busy
                    is_busy = True
                    emitter = LogStreamEmitter()
                    try:
                        broadcast_log(f"🚀 {champ} için ses çıkarma işlemi başlatıldı...")
                        with redirect_stdout(emitter):
                            voice_extractor.extract_champion_voices(champ, skin)
                        emitter.flush()
                        set_last_extracted_champion(champ)
                        is_busy = False
                        broadcast_log(f"✨ {champ} için ses çıkarma işlemi tamamlandı!")
                    except Exception as e:
                        is_busy = False
                        broadcast_log(f"❌ Hata oluştu: {e}")

                threading.Thread(target=run_extract, daemon=True).start()
                self.send_json({"status": "started"})
                return

            # Context for modular sub-routers
            ctx = {
                'ROOT_DIR': ROOT_DIR,
                'CHAMPIONS_OUTPUT_PATH': CHAMPIONS_OUTPUT_PATH,
                'broadcast_log': broadcast_log,
                'meta_mgr': meta_mgr,
                'LogStreamEmitter': LogStreamEmitter
            }

            # 2. Reverse References Extraction (Modular)
            if references_routes.handle_references_post(self, path, body, ctx):
                return

            # 2b. Quotes & Subtitles Sync (Modular)
            if quotes_routes.handle_quotes_post(self, path, body, ctx):
                return


            # 3. Download CDN Asset
            if path == '/api/download-cdn':
                url = body.get('url')
                folder_name = body.get('folder_name', 'Splashes')
                filename = body.get('filename', 'asset.jpg')
                try:
                    save_dir = os.path.join(CHAMPIONS_OUTPUT_PATH, "_CDN_Downloads", folder_name)
                    os.makedirs(save_dir, exist_ok=True)
                    save_path = os.path.join(save_dir, filename)

                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
                    with urllib.request.urlopen(req, timeout=20) as resp:
                        with open(save_path, 'wb') as f:
                            f.write(resp.read())

                    broadcast_log(f"💾 Başarıyla indirildi: {filename} -> {save_dir}")
                    self.send_json({"status": "success", "path": save_path})
                except Exception as e:
                    broadcast_log(f"❌ İndirme hatası ({filename}): {e}")
                    self.send_json({"status": "error", "message": str(e)}, 500)
                return

            # 4. DaVinci Resolve Timeline Exporter & Fusion Scripts (Modular)
            if davinci_routes.handle_davinci_post(self, path, body, ctx):
                return

            # 5. Export Selected Audio Files to Dedicated Folder & Open in Explorer
            if path == '/api/export-selected-to-folder':
                try:
                    custom_files = body.get('audio_files', [])
                    champion = body.get('champion', 'Ozel_Atiflar')
                    folder_label = body.get('folder_name', 'Secilen_Replikler')

                    if not custom_files or not isinstance(custom_files, list):
                        self.send_json({"status": "error", "message": "Lütfen en az bir ses dosyası seçin."}, 400)
                        return

                    safe_champ = champion.replace(' ', '_')
                    clean_label = folder_label.replace(' ', '_')
                    out_dir = os.path.join(CHAMPIONS_OUTPUT_PATH, safe_champ, f"{clean_label}_{len(custom_files)}_Ses")
                    os.makedirs(out_dir, exist_ok=True)

                    copied_count = 0
                    for fpath in custom_files:
                        if not os.path.isfile(fpath):
                            continue
                        # Get speaker and skin name from directory structure
                        parent_skin = os.path.basename(os.path.dirname(fpath))
                        parent_spk = os.path.basename(os.path.dirname(os.path.dirname(fpath)))
                        orig_name = os.path.basename(fpath)

                        # Clean readable name
                        prefix = f"{parent_spk}_" if parent_spk and not orig_name.lower().startswith(parent_spk.lower()) else ""
                        dst_name = f"{prefix}{orig_name}"
                        dst_path = os.path.join(out_dir, dst_name)

                        shutil.copy2(fpath, dst_path)
                        copied_count += 1

                    broadcast_log(f"📁 {copied_count} ses dosyası '{os.path.basename(out_dir)}' klasörüne aktarıldı!")
                    
                    if sys.platform == 'win32':
                        os.startfile(out_dir)

                    self.send_json({
                        "status": "success",
                        "folder_path": out_dir,
                        "folder_name": os.path.basename(out_dir),
                        "total_files": copied_count
                    })
                except Exception as e:
                    broadcast_log(f"❌ Klasöre Aktarma Hatası: {e}")
                    self.send_json({"status": "error", "message": str(e)}, 500)
                return

            # 6. Sync Base Champions Hub
            if path == '/api/sync-base-hub':
                try:
                    import base_champions_hub as base_hub
                    res = base_hub.sync_all_base_champions_to_hub()
                    broadcast_log(f"📦 A-Z Hub Senkronize Edildi: {res['synced_champions']} şampiyon, {res['total_files']} replik hazır!")
                    self.send_json({"status": "success", "data": res})
                except Exception as e:
                    broadcast_log(f"❌ A-Z Hub Senkronizasyon Hatası: {e}")
                    self.send_json({"status": "error", "message": str(e)}, 500)
                return

            # 7. Sync Skins with CDragon
            if path == '/api/sync-skins':
                try:
                    broadcast_log("🌐 Topluluk Dragon (CDragon) kostüm senkronizasyonu başlatılıyor...")
                    res = skin_sync_service.sync_skins(log_callback=broadcast_log)
                    if res.get('status') == 'success':
                        meta_mgr.load_database()
                        broadcast_log(f"🎉 Kostüm veritabanı başarıyla güncellendi ({res.get('total', 0)} kostüm)!")
                    self.send_json(res)
                except Exception as e:
                    broadcast_log(f"❌ Kostüm senkronizasyon hatası: {e}")
                    self.send_json({"status": "error", "message": str(e)}, 500)
                return

            # 8. Open File Location in Windows Explorer
            if path == '/api/open-file-location':
                file_path = body.get('file_path')
                if file_path and os.path.exists(file_path):
                    if sys.platform == 'win32':
                        import subprocess
                        subprocess.Popen(['explorer', '/select,', os.path.abspath(file_path)])
                    self.send_json({"status": "success"})
                else:
                    self.send_json({"status": "error", "message": "Dosya bulunamadı"}, 404)
                return

            # 9. Open Explorer Folder (Smart Target: Latest Extracted Champion or Champions Root)
            if path == '/api/open-folder':
                folder = body.get('folder')
                target = resolve_output_target_folder(folder)

                os.makedirs(target, exist_ok=True)
                if sys.platform == 'win32':
                    os.startfile(target)

                target_rel = os.path.relpath(target, ROOT_DIR)
                is_champ = (os.path.abspath(target) != os.path.abspath(CHAMPIONS_OUTPUT_PATH))
                champ_name = os.path.basename(target) if is_champ else None
                broadcast_log(f"📂 Çıktı klasörü açıldı: {target_rel}")
                self.send_json({
                    "status": "success",
                    "target": target,
                    "target_rel": target_rel,
                    "is_champion_folder": is_champ,
                    "champion": champ_name
                })
                return

            # 10 & 11. Wallpapers POST API (Modular)
            if wallpapers_routes.handle_wallpapers_post(self, path, body, ctx):
                return

            # 12. Static 4K Wallpapers POST API
            if static_wallpapers_routes.handle_static_wallpapers_post(self, path, body, ctx):
                return

            self.send_json({"error": "Endpoint not found"}, 404)
        except Exception as e:
            print(f"❌ HTTP POST Hatası: {e}")
            try:
                self.send_json({"status": "error", "message": str(e)}, 500)
            except Exception:
                pass

def start_server(port=0):
    server = socketserver.ThreadingTCPServer(('127.0.0.1', port), StudioHTTPHandler)
    server.daemon_threads = True
    actual_port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    # Arka planda kostüm veritabanı güncelliğini kontrol et ve senkronize et
    def _on_sync_done(res):
        if res.get('status') == 'success' and res.get('updated', 0) > 0:
            meta_mgr.load_database()
            broadcast_log(f"🎉 Kostüm veritabanı otomatik olarak güncellendi (+{res['updated']} yeni kostüm)!")

    skin_sync_service.trigger_background_sync(on_complete=_on_sync_done)

    return server, actual_port

if __name__ == '__main__':
    import webbrowser
    target_port = 8080
    try:
        server, port = start_server(port=target_port)
    except OSError:
        server, port = start_server(port=0)
    url = f"http://127.0.0.1:{port}/index.html#references"
    print(f"\n=======================================================")
    print(f"🚀 Hextech Studio & Analiz Hub Web Sunucusu Calisiyor!")
    print(f"🌐 Adres: {url}")
    print(f"=======================================================\n")
    print("Tarayici otomatik aciliyor... (Durdurmak icin Ctrl+C yapabilirsiniz)\n")
    webbrowser.open(url)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Sunucu durduruldu.")
        server.shutdown()
