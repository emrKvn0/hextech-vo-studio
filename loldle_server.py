# -*- coding: utf-8 -*-
"""
League of Legends LoLdle Turkish Backend Server
FastAPI Web Server with REST API for Daily & Endless modes across 4 game types:
1. Klasik Mod (Classic)
2. Replik Modu (Quote / Voice line)
3. Yetenek Modu (Ability)
4. Emoji Modu (Emoji)
"""

import os
import sys
import json
import hashlib
import hmac
import base64
import time
import urllib.request
from typing import Optional, List, Dict, Any
from datetime import datetime, date

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from fastapi import FastAPI, HTTPException, Query, Response, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "loldle", "data")
DB_FILE = os.path.join(DATA_DIR, "champions.json")
STATIC_DIR = os.path.join(BASE_DIR, "loldle", "static")
AUDIO_CACHE_DIR = os.path.join(BASE_DIR, ".app_storage", "loldle_audio")
os.makedirs(AUDIO_CACHE_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

SECRET_KEY = b"hextech_loldle_tr_secret_key_2026"

# Load database
def load_champions_db():
    if not os.path.exists(DB_FILE):
        print("⚠️ champions.json bulunamadı, oluşturuluyor...")
        from loldle.data.build_champions_db import build_database
        return build_database()
    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

CHAMPIONS_DB: List[Dict[str, Any]] = load_champions_db()
CHAMPIONS_MAP: Dict[str, Dict[str, Any]] = {c["id"].lower(): c for c in CHAMPIONS_DB}
CHAMPIONS_BY_KEY: Dict[str, Dict[str, Any]] = {c["key"]: c for c in CHAMPIONS_DB}

print(f"✨ LoLdle Veri Tabanı Yüklendi: Toplam {len(CHAMPIONS_DB)} şampiyon hazır.")

app = FastAPI(
    title="League of Legends LoLdle Türkçe",
    description="Hextech LoLdle Web Uygulaması ve REST API Sunucusu",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Helper: Token generation & verification for challenges
def generate_challenge_token(data: dict) -> str:
    payload = json.dumps(data, sort_keys=True).encode("utf-8")
    sig = hmac.new(SECRET_KEY, payload, hashlib.sha256).digest()
    combined = payload + b"||" + sig
    return base64.urlsafe_b64encode(combined).decode("utf-8")

def verify_challenge_token(token_str: str) -> Optional[dict]:
    try:
        raw = base64.urlsafe_b64decode(token_str.encode("utf-8"))
        parts = raw.split(b"||")
        if len(parts) != 2:
            return None
        payload, sig = parts[0], parts[1]
        expected_sig = hmac.new(SECRET_KEY, payload, hashlib.sha256).digest()
        if not hmac.compare_digest(sig, expected_sig):
            return None
        return json.loads(payload.decode("utf-8"))
    except Exception:
        return None

# Load All Skins Database (2,147+ skins including base skins)
SKINS_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "all_lol_skins_database.json")
ALL_SKINS: List[Dict[str, Any]] = []
if os.path.exists(SKINS_DB_PATH):
    try:
        with open(SKINS_DB_PATH, "r", encoding="utf-8") as f:
            raw_skins = json.load(f)
            ALL_SKINS = [
                s for s in raw_skins 
                if s.get("champion_alias") and s.get("skin_num") is not None and s.get("champion_name")
            ]
    except Exception as e:
        print("Skins load error:", e)

def get_skin_splash_url(skin: Dict[str, Any]) -> str:
    alias = skin["champion_alias"]
    num = skin["skin_num"]
    return f"https://ddragon.leagueoflegends.com/cdn/img/champion/splash/{alias}_{num}.jpg"

def get_daily_champion(mode: str, target_date_str: str):
    # Hash date + mode
    seed_str = f"loldle_{mode}_{target_date_str}"
    h = int(hashlib.md5(seed_str.encode("utf-8")).hexdigest(), 16)
    champ_idx = h % len(CHAMPIONS_DB)
    target_champ = CHAMPIONS_DB[champ_idx]
    
    spell_idx = (h // 7) % len(target_champ.get("spells", [0]))
    crop_x = 25 + ((h // 13) % 51)
    crop_y = 25 + ((h // 29) % 51)
    
    if mode == "splash" and ALL_SKINS:
        skin_idx = h % len(ALL_SKINS)
        selected_skin = ALL_SKINS[skin_idx]
        found_champ = CHAMPIONS_MAP.get(selected_skin["champion_alias"].lower()) or CHAMPIONS_MAP.get(selected_skin["champion_name"].lower())
        if found_champ:
            target_champ = dict(found_champ)
        target_champ["current_skin"] = selected_skin
        
    return target_champ, spell_idx, crop_x, crop_y

def get_random_champion(mode: str):
    import random
    champ = random.choice(CHAMPIONS_DB)
    spell_idx = random.randint(0, len(champ.get("spells", [0])) - 1)
    crop_x = random.randint(25, 75)
    crop_y = random.randint(25, 75)
    
    if mode == "splash" and ALL_SKINS:
        selected_skin = random.choice(ALL_SKINS)
        found_champ = CHAMPIONS_MAP.get(selected_skin["champion_alias"].lower()) or CHAMPIONS_MAP.get(selected_skin["champion_name"].lower())
        if found_champ:
            champ = dict(found_champ)
        champ["current_skin"] = selected_skin
        
    return champ, spell_idx, crop_x, crop_y

OFFICIAL_QUOTES_PATH = os.path.join(DATA_DIR, "official_champion_quotes.json")
MASTER_QUOTES_PATH = os.path.join(DATA_DIR, "champion_quotes_master.json")
OFFICIAL_QUOTES = {}
MASTER_QUOTES = {}

def get_champion_quote(champ: Dict[str, Any], is_daily: bool = False, target_date: str = "") -> Dict[str, Any]:
    global OFFICIAL_QUOTES, MASTER_QUOTES
    if not OFFICIAL_QUOTES and os.path.exists(OFFICIAL_QUOTES_PATH):
        try:
            with open(OFFICIAL_QUOTES_PATH, "r", encoding="utf-8") as f:
                OFFICIAL_QUOTES = json.load(f)
        except Exception:
            OFFICIAL_QUOTES = {}
            
    if not MASTER_QUOTES and os.path.exists(MASTER_QUOTES_PATH):
        try:
            with open(MASTER_QUOTES_PATH, "r", encoding="utf-8") as f:
                MASTER_QUOTES = json.load(f)
        except Exception:
            MASTER_QUOTES = {}
            
    champ_id = champ["id"]
    champ_name = champ.get("name", champ_id)
    quotes_meta = champ.get("quotes", {})
    v_data = OFFICIAL_QUOTES.get(champ_id, {})
    
    options = []
    
    # 1. Check Master Verified In-Game Quotes (e.g. Wukong: "Ben hallederim.")
    m_list = MASTER_QUOTES.get(champ_name) or MASTER_QUOTES.get(champ_id) or []
    for mq in m_list:
        if mq.get("text") and mq.get("audio_url"):
            options.append({
                "text": mq["text"],
                "audio_url": f"/api/audio_proxy?url={urllib.parse.quote(mq['audio_url'])}",
                "type": "ingame",
                "type_label": "Oyun İçi Replik"
            })
            
    # 2. Choose VO
    choose_text = v_data.get("choose") or quotes_meta.get("choose_quote_tr", "")
    if choose_text:
        options.append({
            "text": choose_text,
            "audio_url": f"/api/audio/{champ['id']}?type=choose",
            "type": "choose",
            "type_label": "Seçim Repliği"
        })
        
    # 3. Ban VO
    ban_text = v_data.get("ban") or quotes_meta.get("ban_quote_tr", "")
    if ban_text:
        options.append({
            "text": ban_text,
            "audio_url": f"/api/audio/{champ['id']}?type=ban",
            "type": "ban",
            "type_label": "Yasaklama Repliği"
        })
        
    if not options:
        return {
            "quote_text": quotes_meta.get("choose_quote_tr", "Korku, asil bir hisse dönüşecek!"),
            "audio_url": f"/api/audio/{champ['id']}?type=choose",
            "quote_type": "Seçim Repliği",
            "quote_length": len(quotes_meta.get("choose_quote_tr", ""))
        }
        
    if is_daily and target_date:
        h = int(hashlib.md5(f"{target_date}_{champ_id}_quote".encode()).hexdigest(), 16)
        selected = options[h % len(options)]
    else:
        import random
        selected = random.choice(options)
        
    return {
        "quote_text": selected["text"],
        "audio_url": selected["audio_url"],
        "quote_type": selected["type_label"],
        "quote_length": len(selected["text"])
    }

# Models
class GuessRequest(BaseModel):
    token: str
    guess_id: str
    guess_count: int = 1

@app.get("/api/champions")
def get_champions_list():
    """Returns champion list for search autocomplete"""
    result = []
    for c in CHAMPIONS_DB:
        result.append({
            "id": c["id"],
            "name": c["name"],
            "title": c["title"],
            "image": c["images"]["square"]
        })
    return result

@app.get("/api/champions/all")
def get_all_champions():
    """Returns full champions database"""
    return CHAMPIONS_DB

@app.get("/api/daily")
def get_daily_challenge(
    mode: str = Query(..., pattern="^(classic|quote|ability|emoji|splash)$"),
    target_date: Optional[str] = Query(None, alias="date")
):
    """Generates or retrieves deterministic Daily Challenge"""
    if not target_date:
        target_date = date.today().isoformat()
        
    champ, spell_idx, crop_x, crop_y = get_daily_champion(mode, target_date)
    
    current_skin = champ.get("current_skin")
    splash_url = get_skin_splash_url(current_skin) if current_skin else champ["images"]["splash"]
    skin_name = current_skin.get("name_tr", champ["name"]) if current_skin else champ["name"]

    token_data = {
        "mode": mode,
        "is_daily": True,
        "date": target_date,
        "champ_id": champ["id"],
        "spell_idx": spell_idx,
        "crop_x": crop_x,
        "crop_y": crop_y,
        "skin_name": skin_name,
        "splash_url": splash_url,
        "ts": int(time.time())
    }
    token = generate_challenge_token(token_data)
    
    response_data: Dict[str, Any] = {
        "mode": mode,
        "is_daily": True,
        "date": target_date,
        "token": token
    }
    
    if mode == "quote":
        q_data = get_champion_quote(champ, is_daily=True, target_date=target_date)
        response_data["quote_text"] = q_data["quote_text"]
        response_data["audio_url"] = q_data["audio_url"]
        response_data["quote_type"] = q_data["quote_type"]
        response_data["quote_length"] = q_data["quote_length"]
    elif mode == "ability":
        sp = champ["spells"][spell_idx]
        response_data["spell_icon_url"] = sp["icon_url"]
        response_data["spell_key"] = sp["key"]
    elif mode == "emoji":
        response_data["emojis"] = champ["emojis"]
    elif mode == "splash":
        response_data["splash_image_url"] = splash_url
        response_data["skin_name"] = skin_name
        response_data["crop_x"] = crop_x
        response_data["crop_y"] = crop_y
        
    return response_data

@app.get("/api/random")
def get_random_challenge(
    mode: str = Query(..., pattern="^(classic|quote|ability|emoji|splash)$")
):
    """Generates random Endless Challenge"""
    champ, spell_idx, crop_x, crop_y = get_random_champion(mode)
    
    current_skin = champ.get("current_skin")
    splash_url = get_skin_splash_url(current_skin) if current_skin else champ["images"]["splash"]
    skin_name = current_skin.get("name_tr", champ["name"]) if current_skin else champ["name"]

    token_data = {
        "mode": mode,
        "is_daily": False,
        "champ_id": champ["id"],
        "spell_idx": spell_idx,
        "crop_x": crop_x,
        "crop_y": crop_y,
        "skin_name": skin_name,
        "splash_url": splash_url,
        "salt": hashlib.md5(str(time.time()).encode()).hexdigest()[:8],
        "ts": int(time.time())
    }
    token = generate_challenge_token(token_data)
    
    response_data: Dict[str, Any] = {
        "mode": mode,
        "is_daily": False,
        "token": token
    }
    
    if mode == "quote":
        q_data = get_champion_quote(champ, is_daily=False)
        response_data["quote_text"] = q_data["quote_text"]
        response_data["audio_url"] = q_data["audio_url"]
        response_data["quote_type"] = q_data["quote_type"]
        response_data["quote_length"] = q_data["quote_length"]
    elif mode == "ability":
        sp = champ["spells"][spell_idx]
        response_data["spell_icon_url"] = sp["icon_url"]
        response_data["spell_key"] = sp["key"]
    elif mode == "emoji":
        response_data["emojis"] = champ["emojis"]
    elif mode == "splash":
        response_data["splash_image_url"] = splash_url
        response_data["skin_name"] = skin_name
        response_data["crop_x"] = crop_x
        response_data["crop_y"] = crop_y
        
    return response_data

def compare_lists(guess_list: List[str], target_list: List[str]) -> str:
    """Returns 'exact', 'partial', or 'wrong'"""
    g_set = set(g.strip().lower() for g in guess_list)
    t_set = set(t.strip().lower() for t in target_list)
    if g_set == t_set:
        return "exact"
    if g_set & t_set:
        return "partial"
    return "wrong"

@app.post("/api/guess")
def submit_guess(req: GuessRequest):
    """Validates user guess and computes detailed feedback / clues"""
    token_data = verify_challenge_token(req.token)
    if not token_data:
        raise HTTPException(status_code=400, detail="Geçersiz veya süresi dolmuş oyun jetonu.")
        
    target_id = token_data["champ_id"]
    mode = token_data["mode"]
    spell_idx = token_data.get("spell_idx", 0)
    
    target_champ = CHAMPIONS_MAP.get(target_id.lower())
    if not target_champ:
        raise HTTPException(status_code=500, detail="Hedef şampiyon veri tabanında bulunamadı.")
        
    # Find guessed champion by id or name
    guess_key = req.guess_id.strip().lower()
    guess_champ = CHAMPIONS_MAP.get(guess_key)
    if not guess_champ:
        # Search by exact name match
        for c in CHAMPIONS_DB:
            if c["name"].lower() == guess_key:
                guess_champ = c
                break
                
    if not guess_champ:
        raise HTTPException(status_code=404, detail="Tahmin edilen şampiyon bulunamadı.")
        
    is_correct = (guess_champ["id"].lower() == target_champ["id"].lower())
    guess_count = max(1, req.guess_count)
    
    feedback: Dict[str, Any] = {
        "is_correct": is_correct,
        "guess_count": guess_count,
        "mode": mode,
        "guess_champion": {
            "id": guess_champ["id"],
            "name": guess_champ["name"],
            "title": guess_champ["title"],
            "image": guess_champ["images"]["square"]
        }
    }
    
    if mode == "classic":
        # Classic comparison
        # 1. Gender
        gender_correct = (guess_champ["gender"] == target_champ["gender"])
        
        # 2. Positions
        pos_status = compare_lists(guess_champ["positions"], target_champ["positions"])
        
        # 3. Species
        species_status = compare_lists(guess_champ["species"], target_champ["species"])
        
        # 4. Resource
        resource_correct = (guess_champ["resource"] == target_champ["resource"])
        
        # 5. Range Type
        range_status = compare_lists(guess_champ["range_type"], target_champ["range_type"])
        
        # 6. Regions
        region_status = compare_lists(guess_champ["regions"], target_champ["regions"])
        
        # 7. Release Year
        t_year = int(target_champ["release_year"])
        g_year = int(guess_champ["release_year"])
        if g_year == t_year:
            year_status = "exact"
            year_direction = "equal"
        elif t_year > g_year:
            year_status = "wrong"
            year_direction = "higher" # Target is newer / higher
        else:
            year_status = "wrong"
            year_direction = "lower" # Target is older / lower
            
        feedback["comparison"] = {
            "gender": {"value": guess_champ["gender"], "status": "exact" if gender_correct else "wrong"},
            "positions": {"value": guess_champ["positions"], "status": pos_status},
            "species": {"value": guess_champ["species"], "status": species_status},
            "resource": {"value": guess_champ["resource"], "status": "exact" if resource_correct else "wrong"},
            "range_type": {"value": guess_champ["range_type"], "status": range_status},
            "regions": {"value": guess_champ["regions"], "status": region_status},
            "release_year": {"value": g_year, "status": year_status, "direction": year_direction}
        }
        
    elif mode == "quote":
        # Quote hint unlock system
        hints = []
        quote_text = target_champ["quotes"]["choose_quote_tr"]
        
        if guess_count >= 1:
            hints.append({"level": 1, "type": "quote_text", "label": "Replik Metni", "value": f'"{quote_text}"'})
        if guess_count >= 2:
            hints.append({"level": 2, "type": "gender_region", "label": "Cinsiyet & Bölge", "value": f"{target_champ['gender']} • {', '.join(target_champ['regions'])}"})
        if guess_count >= 3:
            hints.append({"level": 3, "type": "role_year", "label": "Rol & Çıkış Yılı", "value": f"{', '.join(target_champ['positions'])} • {target_champ['release_year']}"})
        if guess_count >= 4:
            hints.append({"level": 4, "type": "thematic_hint", "label": "İpucu", "value": target_champ["quotes"].get("hint", target_champ["title"])})
            
        feedback["hints"] = hints
        
    elif mode == "ability":
        hints = []
        target_spell = target_champ["spells"][spell_idx]
        
        if guess_count >= 1:
            hints.append({"level": 1, "type": "spell_slot", "label": "Yetenek Tuşu", "value": f"Bu yetenek '{target_spell['key']}' tuşuna aittir."})
        if guess_count >= 2:
            hints.append({"level": 2, "type": "spell_first_letter", "label": "İlk Harf & Bölge", "value": f"Yetenek Adı '{target_spell['name'][:1]}...' • Bölge: {', '.join(target_champ['regions'])}"})
        if guess_count >= 3:
            hints.append({"level": 3, "type": "full_spell_name", "label": "Yetenek Adı", "value": f"'{target_spell['name']}' ({', '.join(target_champ['positions'])})"})
            
        feedback["hints"] = hints
        
    elif mode == "emoji":
        hints = []
        if guess_count >= 1:
            hints.append({"level": 1, "type": "region", "label": "Bölge", "value": ", ".join(target_champ["regions"])})
        if guess_count >= 2:
            hints.append({"level": 2, "type": "title_hint", "label": "Unvan İpucu", "value": f"... {target_champ['title'].split()[-1]}"})
        if guess_count >= 3:
            hints.append({"level": 3, "type": "role_year", "label": "Rol & Yıl", "value": f"{', '.join(target_champ['positions'])} • {target_champ['release_year']}"})
            
        feedback["hints"] = hints

    elif mode == "splash":
        hints = []
        if guess_count >= 1:
            hints.append({"level": 1, "type": "positions", "label": "Rol / Konum", "value": ", ".join(target_champ["positions"])})
        if guess_count >= 2:
            hints.append({"level": 2, "type": "region", "label": "Bölge", "value": ", ".join(target_champ["regions"])})
        if guess_count >= 3:
            hints.append({"level": 3, "type": "year", "label": "Çıkış Yılı", "value": str(target_champ["release_year"])})
        if guess_count >= 4:
            hints.append({"level": 4, "type": "range_gender", "label": "Menzil & Cinsiyet", "value": f"{', '.join(target_champ['range_type'])} • {target_champ['gender']}"})
            
        feedback["hints"] = hints
        
    # If guess is correct, reveal full champion dossier for victory modal
    if is_correct:
        victory_payload = {
            "champion": target_champ,
            "total_guesses": guess_count,
            "share_text": generate_share_summary(mode, guess_count, is_daily=token_data.get("is_daily", False), target_date=token_data.get("date", ""))
        }
        if token_data.get("skin_name"):
            victory_payload["skin_name"] = token_data["skin_name"]
        if token_data.get("splash_url"):
            victory_payload["splash_url"] = token_data["splash_url"]
            
        feedback["victory"] = victory_payload
        
    return feedback

def generate_share_summary(mode: str, guesses: int, is_daily: bool, target_date: str) -> str:
    mode_names = {
        "classic": "🎯 Klasik",
        "quote": "🎙️ Replik",
        "ability": "⚡ Yetenek",
        "emoji": "✨ Emoji",
        "splash": "🖼️ Splash"
    }
    m_name = mode_names.get(mode, "LoLdle")
    day_str = f" ({target_date})" if is_daily and target_date else ""
    return f"LoLdle TR {m_name}{day_str}\n🏆 {guesses}. tahminde buldum!\n🔥 hextech.loldle"

@app.get("/api/audio/{champ_id}")
def get_audio_proxy(champ_id: str, type: str = "choose"):
    """
    Proxies and caches champion Turkish voice lines locally to eliminate CORS and 403 issues.
    Supports resolution by champion ID (e.g. MonkeyKing), name (e.g. Wukong), or numeric key (e.g. 62).
    """
    champ_query = champ_id.strip().lower()
    champ = CHAMPIONS_MAP.get(champ_query)
    if not champ:
        champ = CHAMPIONS_BY_KEY.get(champ_id.strip())
    if not champ:
        for c in CHAMPIONS_DB:
            if c["name"].lower() == champ_query or c["id"].lower() == champ_query:
                champ = c
                break
                
    if not champ:
        raise HTTPException(status_code=404, detail="Şampiyon bulunamadı.")
        
    key_num = champ["key"]
    cache_filename = f"{key_num}_{type}.ogg"
    cached_path = os.path.join(AUDIO_CACHE_DIR, cache_filename)
    
    # Return cached audio if present
    if os.path.exists(cached_path) and os.path.getsize(cached_path) > 1000:
        return FileResponse(cached_path, media_type="audio/ogg")
        
    # Otherwise fetch from Community Dragon TR_TR
    url_vo_type = "champion-choose-vo" if type == "choose" else "champion-ban-vo"
    remote_url = f"https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/tr_tr/v1/{url_vo_type}/{key_num}.ogg"
    
    try:
        req = urllib.request.Request(remote_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            audio_bytes = resp.read()
            with open(cached_path, "wb") as f:
                f.write(audio_bytes)
        return FileResponse(cached_path, media_type="audio/ogg")
    except Exception as e:
        # Fallback to default language VO if tr_tr has missing file
        try:
            fallback_url = f"https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/{url_vo_type}/{key_num}.ogg"
            req = urllib.request.Request(fallback_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            with urllib.request.urlopen(req, timeout=6) as resp:
                audio_bytes = resp.read()
                with open(cached_path, "wb") as f:
                    f.write(audio_bytes)
            return FileResponse(cached_path, media_type="audio/ogg")
        except Exception as e2:
            raise HTTPException(status_code=502, detail=f"Ses dosyası indirilemedi: {e2}")

@app.get("/api/audio_proxy")
def proxy_custom_audio(url: str = Query(...)):
    """
    Safely streams and caches verified audio files locally to prevent CORS and rate limits.
    """
    clean_url = url.strip()
    if not clean_url:
        raise HTTPException(status_code=400, detail="Geçersiz ses URL'si")
        
    filename = os.path.basename(urllib.parse.urlparse(clean_url).path)
    if not filename:
        filename = hashlib.md5(clean_url.encode()).hexdigest() + ".wav"
        
    cached_path = os.path.join(AUDIO_CACHE_DIR, filename)
    if os.path.exists(cached_path) and os.path.getsize(cached_path) > 1000:
        media_type = "audio/wav" if filename.endswith(".wav") else "audio/ogg"
        return FileResponse(cached_path, media_type=media_type)
        
    try:
        req = urllib.request.Request(clean_url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Origin": "https://loldle.net",
            "Referer": "https://loldle.net/"
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            audio_bytes = resp.read()
            with open(cached_path, "wb") as f:
                f.write(audio_bytes)
                
        media_type = "audio/wav" if filename.endswith(".wav") else "audio/ogg"
        return FileResponse(cached_path, media_type=media_type)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Ses proxy hatası: {e}")

# Serve Static Frontend Files
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/favicon.ico")
def serve_favicon():
    favicon_file = os.path.join(STATIC_DIR, "assets", "favicon.ico")
    if os.path.exists(favicon_file):
        return FileResponse(favicon_file, media_type="image/x-icon")
    return Response(status_code=204)

@app.get("/")
def serve_index():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return HTMLResponse("<h1>LoLdle TR Sunucusu Çalışıyor. Statik index.html hazırlanıyor...</h1>")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"🚀 Hextech LoLdle Sunucusu Başlatılıyor: http://127.0.0.1:{port}")
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")
