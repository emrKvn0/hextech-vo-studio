import os
import sys
import re
import json

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_DIR = os.path.join(ROOT_DIR, "data", "wiki_quotes")
os.makedirs(DATASET_DIR, exist_ok=True)

def parse_wiki_audio_html(html_path_or_content, champion_name):
    if os.path.isfile(html_path_or_content):
        with open(html_path_or_content, 'r', encoding='utf-8') as f:
            html = f.read()
    else:
        html = html_path_or_content

    entries = []
    
    # <li> bloklarını tara
    li_matches = re.finditer(r'<li>\s*(.*?)(?=</li>)', html, re.DOTALL | re.IGNORECASE)
    for m in li_matches:
        block = m.group(1)
        m_audio = re.search(r'data-mwtitle=["\']([^"\']+\.ogg)["\']', block)
        if not m_audio:
            continue
        ogg_name = m_audio.group(1)
        
        # Altyazıyı yakala
        m_quote = re.search(r'<i>["\']?([^"\'<]+)["\']?</i>', block)
        if not m_quote:
            continue
        quote_text = m_quote.group(1).strip()
        if "Sound Effect" in quote_text or not quote_text:
            continue

        # Konuşmacıyı yakala (örn. <b>Speaker:</b>)
        m_spk = re.search(r'<b>\s*([^<:]+?)\s*:\s*</b>', block)
        speaker = m_spk.group(1).strip() if m_spk else champion_name

        # Temiz event anahtarı türet
        clean_key = re.sub(r'^[a-zA-Z0-9]+_(Original|[a-zA-Z0-9]+)_', '', ogg_name)
        clean_key = re.sub(r'\.ogg$', '', clean_key)

        entries.append({
            "ogg": ogg_name,
            "event_key": clean_key,
            "speaker": speaker,
            "english_quote": quote_text
        })

    out_file = os.path.join(DATASET_DIR, f"{champion_name}.json")
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)

    print(f"✅ {champion_name} için {len(entries)} adet resmi Wiki repliği kaydedildi: {out_file}")
    return entries

if __name__ == "__main__":
    cache_step_file = r"C:\Users\PC\.gemini\antigravity\brain\336ccb3f-eae3-46bd-9e49-001a34ad8040\.system_generated\steps\3326\content.md"
    if os.path.exists(cache_step_file):
        parse_wiki_audio_html(cache_step_file, "Swain")
