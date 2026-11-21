import os
import sys
import re
import json
import urllib.request

def get_resource_path(filename):
    candidates = [
        os.path.join(getattr(sys, '_MEIPASS', ''), filename),
        os.path.join(os.path.dirname(sys.executable), filename),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), filename),
        os.path.join(os.getcwd(), filename)
    ]
    for c in candidates:
        if c and os.path.exists(c):
            return c
    return filename

DB_FILE = get_resource_path("all_lol_skins_database.json")
CACHE_FILE = get_resource_path("champions_metadata.json")

def sanitize_folder_name(name):
    if not name:
        return ""
    cleaned = re.sub(r'[\\/*?:"<>|]', '', name).strip()
    cleaned = cleaned.replace(' ', '_').replace('-', '_').replace('(', '').replace(')', '').replace("'", "")
    cleaned = re.sub(r'_+', '_', cleaned).strip('_')
    return cleaned

class MetadataManager:
    def __init__(self):
        self.skins_raw_db = []
        self.skins_by_champ = {} # { 'garen': { 0: 'Varsayilan_Garen', 11: 'Savas_Ustasi_Garen', 13: 'Yuce_Kral_Garen', ... } }
        self.load_database()

    def load_database(self):
        if os.path.exists(DB_FILE):
            try:
                with open(DB_FILE, 'r', encoding='utf-8') as f:
                    all_skins = json.load(f)
                self.skins_raw_db = all_skins
                self.skins_by_champ = {}
                for item in all_skins:
                    c_name = item.get('champion_name', '').lower()
                    c_alias = item.get('champion_alias', '').lower()
                    s_num = item.get('skin_num', 0)
                    s_name_tr = item.get('name_tr', '')
                    clean_name = sanitize_folder_name(s_name_tr)
                    
                    if not clean_name:
                        continue

                    for key in [c_name, c_alias]:
                        if key:
                            self.skins_by_champ.setdefault(key, {})[s_num] = clean_name
                return
            except Exception as e:
                print(f"⚠️ all_lol_skins_database yüklenirken hata: {e}")

    def resolve_skin_name(self, champion_name, raw_skin_name):
        champ_key = champion_name.lower().replace("'", "").replace(" ", "").replace("_", "")
        champ_skins = self.skins_by_champ.get(champ_key, {})
        
        if not champ_skins:
            for k in self.skins_by_champ.keys():
                if k in champ_key or champ_key in k:
                    champ_skins = self.skins_by_champ[k]
                    break

        if str(raw_skin_name).lower() in ("base", "skin0", "skin00", "0", ""):
            return f"Varsayilan_{sanitize_folder_name(champion_name)}"

        # Sayıyı tespit et (Örn: skin11 -> 11, Skin022 -> 22, 43 -> 43)
        m = re.search(r'(\d+)', str(raw_skin_name))
        if m:
            s_num = int(m.group(1))
            if s_num == 0:
                return f"Varsayilan_{sanitize_folder_name(champion_name)}"
            if s_num in champ_skins:
                return champ_skins[s_num]
            # 1000 mod kontrolü (Örn: 86013 -> 13)
            s_mod = s_num % 1000
            if s_mod in champ_skins:
                return champ_skins[s_mod]

        # Özel form varyantları (Örn: Seraphine Ultimate ve PBE Formları)
        if champ_key == 'seraphine':
            if str(raw_skin_name) in ('skin02', 'skin2', '2'):
                return "KDA_ALL_OUT_Seraphine_Yukselen_Yildiz"
            if str(raw_skin_name) in ('skin03', 'skin3', '3'):
                return "KDA_ALL_OUT_Seraphine_Superstar"
            if str(raw_skin_name) in ('skin69', 'skin069', '69'):
                return "Kalp_Şarkısı_Seraphine"

        # Fallback temiz isim
        clean_raw = sanitize_folder_name(str(raw_skin_name))
        return f"{sanitize_folder_name(champion_name)}_{clean_raw}"

    def get_skin_info(self, champion_name, skin_num_or_raw):
        champ_key = champion_name.lower().replace("'", "").replace(" ", "").replace("_", "")
        
        target_str = str(skin_num_or_raw or "").strip()
        s_num = None
        m = re.search(r'(\d+)', target_str)
        if m:
            s_num = int(m.group(1))
            if s_num > 1000:
                s_num = s_num % 1000

        target_norm = re.sub(r'[^a-z0-9]', '', target_str.lower().replace('ı', 'i').replace('ş', 's').replace('ğ', 'g').replace('ü', 'u').replace('ö', 'o').replace('ç', 'c'))

        for item in self.skins_raw_db:
            c_name = item.get('champion_name', '').lower().replace("'", "").replace(" ", "").replace("_", "")
            c_alias = item.get('champion_alias', '').lower().replace("'", "").replace(" ", "").replace("_", "")
            if c_name == champ_key or c_alias == champ_key or champ_key in c_name:
                item_snum = item.get('skin_num', 0)
                if s_num is not None and item_snum == s_num:
                    return item
                
                # Check name match
                tr_name = item.get('name_tr', '')
                en_name = item.get('name_en', '')
                tr_norm = re.sub(r'[^a-z0-9]', '', tr_name.lower().replace('ı', 'i').replace('ş', 's').replace('ğ', 'g').replace('ü', 'u').replace('ö', 'o').replace('ç', 'c'))
                en_norm = re.sub(r'[^a-z0-9]', '', en_name.lower().replace('ı', 'i').replace('ş', 's').replace('ğ', 'g').replace('ü', 'u').replace('ö', 'o').replace('ç', 'c'))
                
                if target_norm and (target_norm == tr_norm or target_norm == en_norm or target_norm in tr_norm or tr_norm in target_norm):
                    return item

        return None

if __name__ == "__main__":
    mgr = MetadataManager()
    for champ, sk in [("Garen", "skin11"), ("Garen", "skin24"), ("Garen", "skin33"), ("Garen", "skin13"), ("Belveth", "skin19"), ("Belveth", "skin29")]:
        print(f"{champ} {sk} -> {mgr.resolve_skin_name(champ, sk)}")
