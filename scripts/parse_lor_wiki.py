import os
import re
import json
import sys

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

wiki_path = r"C:\Users\PC\.gemini\antigravity\brain\336ccb3f-eae3-46bd-9e49-001a34ad8040\.system_generated\steps\882\content.md"
if not os.path.exists(wiki_path):
    print("Wiki content not found!")
    sys.exit(1)

with open(wiki_path, 'r', encoding='utf-8') as f:
    text = f.read()

# Her satırda VO_ ve <i>"..."</i> aranıyor
pattern = re.compile(r'(VO_[A-Za-z0-9_]+)\.ogg.*?<i>\"([^\"]+)\"</i>')
matches = pattern.findall(text)
print(f"Toplam eşleşen replik sayısı: {len(matches)}")

transcripts = {}
for vo, quote in matches:
    transcripts[vo] = quote.strip()

out_json = "cache/lor_azir_wiki_transcripts.json"
os.makedirs("cache", exist_ok=True)
with open(out_json, 'w', encoding='utf-8') as f:
    json.dump(transcripts, f, ensure_ascii=False, indent=2)

print(f"Başarıyla kaydedildi: {out_json}")
for k, v in list(transcripts.items())[:5]:
    print(f"  {k} => {v}")
