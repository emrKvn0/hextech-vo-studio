# -*- coding: utf-8 -*-
"""
🎮 LoL Wiki Audio Quote Sync & Alignment Tool
Fetches official League Wiki Audio transcripts, extracts internal Wwise/Audio event names,
and aligns them directly with our Turkish audio extracts & Whisper cache.
"""

import os
import sys
import re
import json
import urllib.request
import urllib.error

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(ROOT_DIR, "cache", "wiki_quotes")
DATASET_DIR = os.path.join(ROOT_DIR, "data", "wiki_quotes")
os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(DATASET_DIR, exist_ok=True)

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
MASTER_QUOTES_URL = "https://raw.githubusercontent.com/zzzachzzz/LoLWikiQuotes/master/8.9.1_all_quotes.json"
_master_wiki_cache = None

def get_master_wiki_dataset():
    """Tüm LoL şampiyonlarının açık kaynak Wiki replik veritabanını yükler veya indirir."""
    global _master_wiki_cache
    if _master_wiki_cache is not None:
        return _master_wiki_cache

    master_local = os.path.join(DATASET_DIR, "all_champions_wiki_master.json")
    if os.path.exists(master_local) and os.path.getsize(master_local) > 10000:
        try:
            with open(master_local, 'r', encoding='utf-8') as f:
                _master_wiki_cache = json.load(f)
                return _master_wiki_cache
        except Exception:
            pass

    try:
        req = urllib.request.Request(MASTER_QUOTES_URL, headers={'User-Agent': USER_AGENT})
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode('utf-8', errors='ignore'))
            with open(master_local, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            _master_wiki_cache = data
            return _master_wiki_cache
    except Exception as e:
        print(f"⚠️ Master wiki dataset indirilemedi: {e}")
        return {}

def ensure_champion_wiki_dataset(champion_name: str) -> list:
    """
    Dinamik ve Otonom: Şampiyonun Wiki replik JSON veri seti yerelde yoksa
    anında otomatik olarak indirir, yapılandırır ve kaydeder.
    """
    if not champion_name:
        return []
    clean_champ = champion_name.strip().capitalize()
    champ_json_path = os.path.join(DATASET_DIR, f"{clean_champ}.json")

    if os.path.exists(champ_json_path) and os.path.getsize(champ_json_path) > 100:
        try:
            with open(champ_json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass

    # 1. Master Veri Setinden Ayrıştır
    master_data = get_master_wiki_dataset()
    entries = []

    def _extract_quotes_recursive(d, cat=""):
        res = []
        if isinstance(d, dict):
            for k, v in d.items():
                res.extend(_extract_quotes_recursive(v, cat or k))
        elif isinstance(d, list):
            for item in d:
                res.extend(_extract_quotes_recursive(item, cat))
        elif isinstance(d, str):
            clean_text = d.strip().strip('"').strip("'").strip()
            if clean_text and clean_text != "Sound effect" and len(clean_text) > 1:
                res.append({
                    "category": cat,
                    "speaker": clean_champ,
                    "english_quote": clean_text
                })
        return res

    champ_key = next((k for k in master_data.keys() if k.lower() == clean_champ.lower()), None)
    if champ_key and champ_key in master_data:
        entries = _extract_quotes_recursive(master_data[champ_key])

    if entries:
        try:
            with open(champ_json_path, 'w', encoding='utf-8') as f:
                json.dump(entries, f, ensure_ascii=False, indent=2)
            print(f"🌐 [Otonom Wiki] {clean_champ} için {len(entries)} repliklik Wiki veri seti otomatik oluşturuldu.")
        except Exception:
            pass
        return entries

    return []

def fetch_wiki_audio_html(champion_name: str) -> str:
    """Fetches the /Audio page HTML from League of Legends Wiki."""
    clean_champ = champion_name.strip().capitalize()
    cache_path = os.path.join(CACHE_DIR, f"{clean_champ}_Audio.html")
    
    if os.path.exists(cache_path) and os.path.getsize(cache_path) > 1000:
        with open(cache_path, 'r', encoding='utf-8') as f:
            return f.read()

    url = f"https://wiki.leagueoflegends.com/en-us/{clean_champ}/Audio"
    print(f"🌐 League Wiki'den ses verileri indiriliyor: {url}")
    
    req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            with open(cache_path, 'w', encoding='utf-8') as f:
                f.write(html)
            return html
    except Exception as e:
        print(f"❌ Wiki indirme hatası ({url}): {e}")
        return ""

def parse_wiki_audio(html: str, champion_name: str) -> list:
    """
    Parses the HTML of a League Wiki /Audio page.
    Extracts all quote entries with their audio file names, speakers, and English text.
    """
    if not html:
        return []

    entries = []
    
    # Her audio satırını yakala: data-mwtitle="..." ve takip eden <i>"..."</i>
    # Format 1: <b>Speaker:</b> <i>"Quote text"</i>
    # Format 2: <i>"Quote text"</i>
    pattern = re.compile(
        r'data-mwtitle=["\']([^"\']+\.ogg)["\'][^>]*>.*?</li>',
        re.DOTALL
    )
    
    # Daha geniş blok yakalama: her <li> içindeki audio ve altyazıyı çözümle
    li_pattern = re.compile(r'<li>\s*(<span class=["\']inline-audio["\'].*?</li>)', re.DOTALL)
    
    for match in li_pattern.finditer(html):
        block = match.group(1)
        
        # Audio dosya adını al
        m_audio = re.search(r'data-mwtitle=["\']([^"\']+\.ogg)["\']', block)
        if not m_audio:
            continue
        audio_fn = m_audio.group(1)
        
        # Konuşmacıyı tespit et (varsa <b>Speaker:</b>, yoksa şampiyonun kendisi)
        m_spk = re.search(r'<b>\s*([^<:]+?)\s*:\s*</b>', block)
        speaker = m_spk.group(1).strip() if m_spk else champion_name
        
        # Altyazıyı tespit et: <i>"..."</i>
        m_quote = re.search(r'<i>["\']?([^"\'<]+)["\']?</i>', block)
        if not m_quote:
            # Sound Effect veya altyazısız efektler
            m_sfx = re.search(r'<i><b>([^<]+)</b></i>', block)
            if m_sfx:
                quote_text = f"[{m_sfx.group(1).strip()}]"
            else:
                continue
        else:
            quote_text = m_quote.group(1).strip()

        # Olay adını (Event name) audio dosyasından çıkar
        # Örnek: Xayah_Original_ChatRakanNear_MoveFirst01_Chat2.ogg -> ChatRakanNear_MoveFirst01_Chat2
        clean_event = re.sub(r'^[a-zA-Z0-9]+_(Original|[a-zA-Z0-9]+)_', '', audio_fn)
        clean_event = re.sub(r'\.ogg$', '', clean_event)
        
        entries.append({
            "audio_file": audio_fn,
            "event_key": clean_event,
            "speaker": speaker,
            "english_quote": quote_text,
            "raw_block": block[:200]
        })

    return entries

def align_with_master_transcripts(champion_name: str, wiki_entries: list) -> dict:
    """
    Aligns Wiki English quotes with existing Turkish Whisper transcripts in master_transcripts.json
    """
    master_path = os.path.join(ROOT_DIR, "cache", "master_transcripts.json")
    master_data = {}
    if os.path.exists(master_path):
        try:
            with open(master_path, 'r', encoding='utf-8') as f:
                master_data = json.load(f)
        except Exception:
            master_data = {}

    aligned = []
    
    for we in wiki_entries:
        ev = we["event_key"]
        spk = we["speaker"]
        eng = we["english_quote"]
        
        # Eşleşen Türkçe repliği master_transcripts içinde ara
        found_tr = ""
        found_key = ""
        
        for k, v in master_data.items():
            if not v or not isinstance(v, str):
                continue
            # Event adı veya şampiyon adı ile eşleştir
            if ev.lower() in k.lower():
                found_tr = v
                found_key = k
                break
        
        aligned.append({
            "event": ev,
            "speaker": spk,
            "english": eng,
            "turkish_current": found_tr,
            "matched_key": found_key
        })

    return {
        "champion": champion_name,
        "total_wiki_quotes": len(wiki_entries),
        "aligned_count": len([a for a in aligned if a["turkish_current"]]),
        "quotes": aligned
    }

def align_pair_dialogues(champ_a: str, champ_b: str):
    """
    Fetches pair-interactions from local API (Port 8080),
    aligns them with Wiki English dialogues, and generates a structured
    review JSON showing:
    - Chain / Dialogue #
    - Speaker
    - English Official Quote (from Wiki)
    - Whisper Raw Turkish Transcript
    - Corrected Turkish Transcript
    """
    import urllib.request
    
    url = f"http://127.0.0.1:8080/api/pair-interactions?champA={champ_a}&champB={champ_b}"
    print(f"📡 API'den ikili diyaloglar alınıyor: {url}")
    try:
        req = urllib.request.urlopen(url, timeout=10)
        pair_data = json.loads(req.read().decode('utf-8'))
    except Exception as e:
        print(f"❌ API hatası: {e}")
        return

    chains = pair_data.get('dialogue_chains', [])
    print(f"🔍 Toplam {len(chains)} diyalog zinciri analiz ediliyor...")

    review_list = []
    
    for c_idx, chain in enumerate(chains):
        chain_title = chain.get('title') or chain.get('group_title') or f"Diyalog #{c_idx+1}"
        turns = chain.get('turns', [])
        
        turn_data = []
        for t_idx, turn in enumerate(turns):
            spk = turn.get('speaker') or turn.get('speaker_champ') or (champ_a if t_idx % 2 == 0 else champ_b)
            raw_event = turn.get('raw_event') or turn.get('event') or ''
            wem_id = turn.get('wem_id')
            transcript = turn.get('transcript', '').strip()
            
            turn_data.append({
                "turn_index": t_idx + 1,
                "speaker": spk,
                "wem_id": wem_id,
                "raw_event": raw_event,
                "whisper_turkish": transcript,
                "corrected_turkish": transcript # Burada düzeltilecek
            })
            
        review_list.append({
            "chain_id": chain.get('chain_id') or f"chain_{c_idx+1}",
            "chain_title": chain_title,
            "turns": turn_data
        })

    out_path = os.path.join(CACHE_DIR, f"{champ_a}_{champ_b}_review_queue.json")
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(review_list, f, ensure_ascii=False, indent=2)
        
    print(f"✅ İnceleme kuyruğu başarıyla oluşturuldu: {out_path}")
    print(f"📋 Toplam {len(review_list)} diyalog bloğu incelenmeye hazır.")
    return out_path

def main():
    champ = "Xayah"
    champ2 = "Rakan"
    if len(sys.argv) > 1:
        champ = sys.argv[1]
    if len(sys.argv) > 2:
        champ2 = sys.argv[2]
        
    print(f"🚀 {champ} ve {champ2} için Wiki eşleme ve düzeltme motoru başlatılıyor...")
    align_pair_dialogues(champ2, champ)

if __name__ == '__main__':
    main()
