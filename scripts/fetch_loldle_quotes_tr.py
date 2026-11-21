import os
import sys
import json
import time
import urllib.request
import subprocess

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "loldle", "data")
CACHE_DIR = os.path.join(PROJECT_ROOT, "loldle", "static", "audio_cache")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

MASTER_QUOTES_PATH = os.path.join(DATA_DIR, "champion_quotes_master.json")

def load_master_quotes():
    if os.path.exists(MASTER_QUOTES_PATH):
        try:
            with open(MASTER_QUOTES_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_master_quotes(data):
    with open(MASTER_QUOTES_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Master quotes database saved: {len(data)} champions updated.")

def fetch_loldle_cache():
    """Fetches and decrypts today's live LoLdle quotes (Europe and America)"""
    js_script = """
    const https = require('https');
    const crypto = require('crypto');

    function evpBytesToKey(password, salt, keyLen, ivLen) {
        let dt = Buffer.alloc(0);
        let d = Buffer.alloc(0);
        while (dt.length < keyLen + ivLen) {
            d = crypto.createHash('md5').update(Buffer.concat([d, Buffer.from(password, 'utf8'), salt])).digest();
            dt = Buffer.concat([dt, d]);
        }
        return {
            key: dt.slice(0, keyLen),
            iv: dt.slice(keyLen, keyLen + ivLen)
        };
    }

    function decryptAes(ciphertextB64, password) {
        const raw = ciphertextB64.replace(/^["']|["']$/g, '').trim();
        const buf = Buffer.from(raw, 'base64');
        const salt = buf.slice(8, 16);
        const ciphertext = buf.slice(16);
        
        const keyAndIv = evpBytesToKey(password, salt, 32, 16);
        const decipher = crypto.createDecipheriv('aes-256-cbc', keyAndIv.key, keyAndIv.iv);
        let decrypted = decipher.update(ciphertext);
        decrypted = Buffer.concat([decrypted, decipher.final()]);
        return decrypted.toString('utf8');
    }

    https.get('https://cache.loldle.net/cache.json', { headers: { 'User-Agent': 'Mozilla/5.0' } }, (res) => {
        let raw = '';
        res.on('data', chunk => raw += chunk);
        res.on('end', () => {
            try {
                const cacheJsonStr = decryptAes(raw, 'D5XCtTOObw');
                const cache = JSON.parse(cacheJsonStr);
                
                const results = [];
                for (const region of ['europe', 'america']) {
                    const qKey = 'quote_answerEncrypted_' + region;
                    if (cache[qKey]) {
                        const qStr = decryptAes(cache[qKey], 'QhDZJfngdx');
                        results.push(JSON.parse(qStr));
                    }
                }
                console.log(JSON.stringify(results));
            } catch (err) {
                console.error(err);
                process.exit(1);
            }
        });
    });
    """
    try:
        proc = subprocess.run(
            ["node", "-e", js_script],
            capture_output=True,
            encoding="utf-8",
            errors="ignore",
            timeout=15
        )
        if proc.returncode == 0 and proc.stdout and proc.stdout.strip():
            return json.loads(proc.stdout.strip())
    except Exception as e:
        print("LoLdle cache fetch error:", e)
    return []

def main():
    master = load_master_quotes()
    print(f"Mevcut Master Quotes: {len(master)} şampiyon kayıtlı.")
    
    # 1. Fetch live quotes from LoLdle cache
    print("LoLdle canlı şifreli cache sorgulanıyor...")
    live_quotes = fetch_loldle_cache()
    added = 0
    for q_data in live_quotes:
        champ_name = q_data.get("champion_name")
        if not champ_name:
            continue
            
        tr_trans = [t for t in q_data.get("quote_translations", []) if t.get("locale") == "tr_TR"]
        if not tr_trans:
            continue
            
        tr_quote_text = tr_trans[0].get("quote", "").strip()
        tr_audio_url = tr_trans[0].get("url", "").strip()
        
        if champ_name not in master:
            master[champ_name] = []
            
        # Check if already exists
        exists = any(q["text"] == tr_quote_text for q in master[champ_name])
        if not exists and tr_quote_text:
            master[champ_name].append({
                "text": tr_quote_text,
                "audio_url": tr_audio_url,
                "english_original": q_data.get("question", ""),
                "game_numero": q_data.get("game_numero"),
                "source": "loldle_verified_i18n"
            })
            added += 1
            print(f"Yeni Replik Eklendi -> {champ_name}: '{tr_quote_text}'")

    save_master_quotes(master)
    print(f"Tamamlandı. {added} yeni doğrulanmış replik havuza eklendi.")

if __name__ == "__main__":
    main()
