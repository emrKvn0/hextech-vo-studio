import os
import sys
import re
import json
import shutil
import ctypes
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from PIL import Image, ImageFilter

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Project Download Directory: Duvar Kağıtları/4K Duvar Kağıtları
USER_DOWNLOADS = os.path.join(ROOT_DIR, "Duvar Kağıtları", "4K Duvar Kağıtları")
os.makedirs(USER_DOWNLOADS, exist_ok=True)
DB_PATH = os.path.join(ROOT_DIR, "all_lol_skins_database.json")

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9,tr;q=0.8',
    'Referer': 'https://leagueoflegends.fandom.com/',
}

# Cache for loaded skins database and wiki queries
_SKINS_DB_CACHE = None
_WIKI_HD_CACHE = {}

def get_clean_name(name):
    clean = re.sub(r'[\\/*?:"<>|]', '', str(name))
    clean = clean.replace(' ', '_').strip('_')
    return clean

def load_skins_database():
    global _SKINS_DB_CACHE
    if _SKINS_DB_CACHE is not None:
        return _SKINS_DB_CACHE
    
    if os.path.exists(DB_PATH):
        try:
            with open(DB_PATH, 'r', encoding='utf-8') as f:
                _SKINS_DB_CACHE = json.load(f)
                return _SKINS_DB_CACHE
        except Exception as e:
            print(f"[StaticWP] Skins DB yüklenirken hata: {e}")
    _SKINS_DB_CACHE = []
    return _SKINS_DB_CACHE

def get_all_champions():
    skins = load_skins_database()
    champs_map = {}
    for s in skins:
        c_alias = s.get('champion_alias') or s.get('champion_name')
        c_name = s.get('champion_name') or c_alias
        if c_alias and c_alias not in champs_map:
            champs_map[c_alias] = {
                "alias": c_alias,
                "name": c_name,
                "champion_id": s.get('champion_id'),
                "skin_count": 0
            }
        if c_alias in champs_map:
            champs_map[c_alias]["skin_count"] += 1
    
    sorted_champs = sorted(champs_map.values(), key=lambda x: x['name'])
    return sorted_champs

def get_champion_skins(champ_query):
    skins = load_skins_database()
    champ_query_norm = champ_query.strip().lower()
    
    matched = []
    c_alias_found = None
    for s in skins:
        c_alias = (s.get('champion_alias') or '').lower()
        c_name = (s.get('champion_name') or '').lower()
        if c_alias == champ_query_norm or c_name == champ_query_norm:
            enriched = enrich_skin_data(s)
            matched.append(enriched)
            if not c_alias_found:
                c_alias_found = s.get('champion_alias') or s.get('champion_name')
            
    # Sort by skin_num
    matched.sort(key=lambda x: x.get('skin_num', 0))

    if c_alias_found:
        wiki_files = fetch_wiki_hd_skins_for_champ(c_alias_found)
        for item in matched:
            s_en = item.get('name_en', '')
            is_base = item.get('is_base', False) or item.get('skin_num', 0) == 0
            has_wiki = False
            if wiki_files:
                if is_base:
                    for t in wiki_files:
                        if any(k in t.lower() for k in ['original', 'base', 'default']):
                            has_wiki = True
                            break
                else:
                    for w in s_en.split():
                        cw = _normalize_string_for_matching(w)
                        if len(cw) >= 4:
                            for t in wiki_files:
                                if cw in _normalize_string_for_matching(t):
                                    has_wiki = True
                                    break
                            if has_wiki:
                                break
            if has_wiki:
                item['source'] = 'LoL Fandom 6K Master'
            else:
                item['source'] = 'UHD Paper 4K'

    return matched

def search_skins(query, max_results=120):
    if not query or not query.strip():
        # Varsayılan popüler kostümleri dön (ilk 60)
        skins = load_skins_database()
        res = [enrich_skin_data(s) for s in skins[:max_results]]
        for r in res:
            r['source'] = 'UHD Paper 4K'
        return res
        
    skins = load_skins_database()
    q_tokens = [t.lower() for t in query.strip().split() if t.strip()]
    
    results = []
    for s in skins:
        c_name = (s.get('champion_name') or '').lower()
        c_alias = (s.get('champion_alias') or '').lower()
        s_tr = (s.get('name_tr') or '').lower()
        s_en = (s.get('name_en') or '').lower()
        r_tr = (s.get('rarity_tr') or '').lower()
        
        full_text = f"{c_name} {c_alias} {s_tr} {s_en} {r_tr}"
        if all(token in full_text for token in q_tokens):
            enriched = enrich_skin_data(s)
            enriched['source'] = 'UHD Paper 4K'
            results.append(enriched)
            if len(results) >= max_results:
                break
                
    return results

def enrich_skin_data(skin):
    """
    DataDragon doğrudan çalışan güvenilir splash ve cdragon yollarını ekler.
    """
    item = dict(skin)
    c_alias = item.get('champion_alias') or item.get('champion_name', 'Aatrox')
    skin_num = item.get('skin_num', 0)
    
    # Official Riot DataDragon Direct Splash (100% reliable)
    ddragon_url = f"https://ddragon.leagueoflegends.com/cdn/img/champion/splash/{c_alias}_{skin_num}.jpg"
    item['ddragon_splash_url'] = ddragon_url
    
    # Fallback to ddragon if current splash_url is empty or broken
    if not item.get('splash_url'):
        item['splash_url'] = ddragon_url
        
    return item

def _normalize_string_for_matching(s):
    if not s:
        return ""
    # remove punctuation, spaces, lowercase
    return re.sub(r'[^a-z0-9]', '', str(s).lower())

def fetch_wiki_hd_skins_for_champ(champion_alias):
    """
    League Fandom MediaWiki API üzerinden şampiyonun resmi 4K/6K HD Master Splash dosyalarını çeker.
    """
    global _WIKI_HD_CACHE
    if champion_alias in _WIKI_HD_CACHE:
        return _WIKI_HD_CACHE[champion_alias]
        
    cat_title = f"Category:High_definition_{champion_alias}_skins"
    params = urllib.parse.urlencode({
        'action': 'query',
        'list': 'categorymembers',
        'cmtitle': cat_title,
        'cmlimit': '100',
        'format': 'json'
    })
    api_url = f"https://leagueoflegends.fandom.com/api.php?{params}"
    
    try:
        req = urllib.request.Request(api_url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            members = data.get('query', {}).get('categorymembers', [])
            
            # File: başlıklarını filtrele
            file_titles = [m['title'] for m in members if m.get('ns') == 6 and 'HD' in m.get('title', '')]
            
            if not file_titles:
                _WIKI_HD_CACHE[champion_alias] = {}
                return {}
                
            # Dosyaların doğrudan URL ve çözünürlüklerini çek (max 50 parça)
            details_map = {}
            for i in range(0, len(file_titles), 45):
                batch = file_titles[i:i+45]
                batch_str = '|'.join(batch)
                q_params = urllib.parse.urlencode({
                    'action': 'query',
                    'titles': batch_str,
                    'prop': 'imageinfo',
                    'iiprop': 'url|size|mime',
                    'format': 'json'
                })
                info_url = f"https://leagueoflegends.fandom.com/api.php?{q_params}"
                req2 = urllib.request.Request(info_url, headers=HEADERS)
                with urllib.request.urlopen(req2, timeout=6) as resp2:
                    d2 = json.loads(resp2.read().decode('utf-8'))
                    pages = d2.get('query', {}).get('pages', {}).values()
                    for p in pages:
                        t = p.get('title', '')
                        ii = p.get('imageinfo', [{}])[0]
                        if ii.get('url'):
                            details_map[t] = {
                                "title": t,
                                "url": ii.get('url'),
                                "width": ii.get('width', 3840),
                                "height": ii.get('height', 2160),
                                "size": ii.get('size', 0)
                            }
                            
            _WIKI_HD_CACHE[champion_alias] = details_map
            return details_map
    except Exception as e:
        print(f"[StaticWP] Wiki HD sorgusu hatası ({champion_alias}): {e}")
        _WIKI_HD_CACHE[champion_alias] = {}
        return {}

def resolve_best_hd_splash(skin_data):
    """
    Verilen kostüm için en yüksek çözünürlüklü (4K/6K Wiki veya DataDragon) görsel URL'sini belirler.
    """
    c_alias = skin_data.get('champion_alias') or skin_data.get('champion_name') or 'Aatrox'
    s_en = skin_data.get('name_en') or ''
    s_tr = skin_data.get('name_tr') or ''
    is_base = skin_data.get('is_base', False) or skin_data.get('skin_num', 0) == 0
    
    # 1. Wiki HD sorgusu yap
    wiki_files = fetch_wiki_hd_skins_for_champ(c_alias)
    
    best_candidate = None
    if wiki_files:
        norm_en = _normalize_string_for_matching(s_en)
        norm_tr = _normalize_string_for_matching(s_tr)
        
        # Base skin için özel kontrol
        if is_base:
            for t, info in wiki_files.items():
                t_lower = t.lower()
                if 'original' in t_lower or 'base' in t_lower or 'default' in t_lower:
                    best_candidate = info
                    break
        else:
            # Kostüm adından anahtar kelimeleri çıkar
            # Örn: 'Dawnbringer Yone' -> 'dawnbringer'
            keywords = []
            for name in [s_en, s_tr]:
                words = [w for w in re.split(r'[\s\-_\']+', name) if w and w.lower() != c_alias.lower()]
                for w in words:
                    cleaned_w = _normalize_string_for_matching(w)
                    if len(cleaned_w) >= 3:
                        keywords.append(cleaned_w)
            
            # Eşleştirme puanı ver
            best_score = 0
            for t, info in wiki_files.items():
                norm_title = _normalize_string_for_matching(t)
                score = 0
                for kw in keywords:
                    if kw in norm_title:
                        score += len(kw)
                if 'prestige' in norm_en and 'prestige' in norm_title:
                    score += 15
                if 'prestige' not in norm_en and 'prestige' in norm_title:
                    score -= 20
                if score > best_score:
                    best_score = score
                    best_candidate = info
                    
_UHDPAPER_CACHE = {}

def extract_uhdpaper_direct_url(html):
    """
    UHDPaper.com üzerindeki hem eski (2018-2020) hem de yeni (2021-2026) nesil tüm 4K/8K indirme linklerini %100 çözer.
    """
    if not html:
        return None

    # Format 1: Yeni Nesil (2021-2026) JavaScript Şablonu
    # var imgL = '...';
    m_imgL = re.search(r'var\s+imgL\s*=\s*[\x22\x27]([^\x22\x27]+)[\x22\x27]', html)
    if m_imgL:
        try:
            imgL = m_imgL.group(1)
            m_fld = re.search(r'\.com-([^\-]+)', imgL, re.I)
            if m_fld:
                fld = m_fld.group(1)
                c = fld.split('.')[-1]
                mF, sF = c.split('_', 1) if '_' in c else (c, 'a')
                dmn = f'-uhdpaper.com-{fld}.jpg'
                filename_base = imgL.split('/')[-1]
                m_fname = re.sub(r'-(8k|4k)-.*', '', filename_base, flags=re.I)
                fName = '/' + m_fname
                en4k = f'3840x2160{dmn}'
                wp4k = f'https://image-{mF}.uhdpaper.com/{sF}/pc-4k{fName}-4k-wallpaper-{en4k}'
                return wp4k
        except Exception:
            pass

    # Format 2: Klasik Nesil (2018-2020) - Lee Sin vb.
    # //img.uhdpaper.com/image/{N}/wallpaper.jpg?4K=.../{slug}-wp.thumbnail.jpg
    m1 = re.search(r'//img\.uhdpaper\.com/image/(\d+)/[^\x22\x27]*\?4K=[^\x22\x27]*/([^/\x22\x27]+)-wp\.thumbnail\.(jpg|png|jpeg)', html, re.I)
    if m1:
        server_num = m1.group(1)
        slug = m1.group(2)
        ext = m1.group(3)
        return f'https://image{server_num}.uhdpaper.com/wallpaper/{slug}.{ext}'

    # Format 3: Doğrudan img.uhdpaper.com 4K PC linkleri
    m2 = re.findall(r'href=[\x22\x27](https?://img\.uhdpaper\.com/[^\x22\x27]+(?:-pc-4k|\.com-4K)[^\x22\x27]*\.(?:jpg|png|jpeg))[\x22\x27]', html, re.I)
    if m2:
        return m2[0]

    # Format 4: Doğrudan image{N}.uhdpaper.com linkleri
    m3 = re.findall(r'href=[\x22\x27](https?://image\d+\.uhdpaper\.com/wallpaper/[^\x22\x27]+)[\x22\x27]', html, re.I)
    if m3:
        return m3[0]

    return None

def search_uhdpaper_wallpaper(champ_name, skin_en, is_base=False):
    """
    UHDPaper.com üzerinden League of Legends 4K UHD masaüstü duvar kağıdı linkini arar.
    """
    global _UHDPAPER_CACHE
    cache_key = f"{champ_name}_{skin_en}_{is_base}".lower().strip()
    if cache_key in _UHDPAPER_CACHE:
        return _UHDPAPER_CACHE[cache_key]

    clean_champ = re.sub(r'[^a-z0-9]', '-', champ_name.lower()).strip('-')

    queries = []
    if is_base:
        queries.append(f"{champ_name} lol splash art")
        queries.append(f"{champ_name} splash art")
        queries.append(f"{champ_name} 4k")
    else:
        if skin_en and skin_en.lower() != champ_name.lower():
            clean_skin = re.sub(r'[\s\-_\']+', ' ', skin_en).strip()
            queries.append(f"{champ_name} {clean_skin}")
            queries.append(f"{clean_skin} {champ_name}")
        queries.append(f"{champ_name} lol")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.uhdpaper.com/'
    }

    found_img_url = None
    for q in queries:
        try:
            url = f"https://www.uhdpaper.com/search?q={urllib.parse.quote_plus(q)}"
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=5) as resp:
                html = resp.read().decode('utf-8', 'ignore')

            posts = list(dict.fromkeys(re.findall(r'href=[\x22\x27](https://www\.uhdpaper\.com/[^\x22\x27]+\.html)', html)))
            if not posts:
                continue

            # En uygun postu seç
            best_post = None
            if is_base:
                # Base skin için postun slug'ı doğrudan {clean_champ} ile başlamalı ve başka kostüm sıfatı içermemelidir!
                candidate_base_posts = []
                for p in posts:
                    m_slug = re.search(r'/\d{4}/\d{2}/([^/]+)\.html', p)
                    if m_slug:
                        slug = m_slug.group(1).lower()
                        # Slug şampiyon adı ile başlamalı
                        clean_no_dash = clean_champ.replace('-', '')
                        if slug.startswith(f"{clean_champ}-") or slug.startswith(f"{clean_no_dash}-"):
                            has_other_skin_kw = any(k in slug for k in [
                                'storm', 'dragon', 'muay', 'god', 'fist', 'pool', 'party', 'knockout',
                                'nightbringer', 'acolyte', 'traditional', 'zenith', 'heavenscale', 'sweeper',
                                'playmaker', 'prestige', 'project', 'coven', 'inkshadow', 'spirit', 'blossom',
                                'dawnbringer', 'blood-moon', 'high-noon', 'battle', 'arcade', 'mecha', 'star-guardian'
                            ])
                            if not has_other_skin_kw:
                                candidate_base_posts.append((p, 100))
                            elif f'{clean_champ}-lol-splash-art' in slug:
                                candidate_base_posts.append((p, 10))

                if candidate_base_posts:
                    candidate_base_posts.sort(key=lambda x: x[1], reverse=True)
                    best_post = candidate_base_posts[0][0]
                elif posts:
                    best_post = posts[0]
            else:
                keywords = [re.sub(r'[^a-z0-9]', '', w.lower()) for w in skin_en.split() if w.lower() != champ_name.lower()]
                best_score = -1
                for p in posts:
                    m_slug = re.search(r'/\d{4}/\d{2}/([^/]+)\.html', p)
                    if m_slug:
                        slug = m_slug.group(1).lower()
                        score = sum(1 for kw in keywords if kw and kw in slug)
                        if score > best_score:
                            best_score = score
                            best_post = p
                if not best_post and posts:
                    best_post = posts[0]

            if best_post:
                p_req = urllib.request.Request(best_post, headers=headers)
                with urllib.request.urlopen(p_req, timeout=5) as p_resp:
                    p_html = p_resp.read().decode('utf-8', 'ignore')
                direct = extract_uhdpaper_direct_url(p_html)
                if direct:
                    found_img_url = direct
                    break
        except Exception:
            pass

    _UHDPAPER_CACHE[cache_key] = found_img_url
    return found_img_url

def resolve_best_hd_splash(skin_data):
    """
    Verilen kostüm için en yüksek çözünürlüklü (4K/6K Wiki, UHDPaper veya DataDragon) görsel URL'sini belirler.
    """
    c_alias = skin_data.get('champion_alias') or skin_data.get('champion_name') or 'Aatrox'
    c_name = skin_data.get('champion_name') or c_alias
    s_en = skin_data.get('name_en') or ''
    s_tr = skin_data.get('name_tr') or ''
    is_base = skin_data.get('is_base', False) or skin_data.get('skin_num', 0) == 0
    
    # 0. Özel Resmi Riot Öncelikleri (Official First)
    c_low = c_name.lower()
    if c_low == 'yunara':
        return {
            "source": "Riot CommunityDragon Official",
            "url": "https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/assets/characters/yunara/skins/base/images/yunara_splash_centered_0.jpg",
            "width": 1920,
            "height": 1080,
            "is_native_4k": False
        }

    if c_low == 'morgana' and is_base:
        return {
            "source": "Riot DataDragon Official (Güncel VGU)",
            "url": "https://ddragon.leagueoflegends.com/cdn/img/champion/splash/Morgana_0.jpg",
            "width": 1215,
            "height": 717,
            "is_native_4k": False
        }

    # 1. Wiki HD sorgusu yap (Riot Orijinal Basın & Master Arşivi)
    wiki_files = fetch_wiki_hd_skins_for_champ(c_alias)
    
    best_candidate = None
    if wiki_files:
        norm_en = _normalize_string_for_matching(s_en)
        norm_tr = _normalize_string_for_matching(s_tr)
        
        # Base skin için özel kontrol
        if is_base:
            for t, info in wiki_files.items():
                t_lower = t.lower()
                if 'original' in t_lower or 'base' in t_lower or 'default' in t_lower:
                    best_candidate = info
                    break
        else:
            keywords = []
            for name in [s_en, s_tr]:
                words = [w for w in re.split(r'[\s\-_\']+', name) if w and w.lower() != c_alias.lower()]
                for w in words:
                    cleaned_w = _normalize_string_for_matching(w)
                    if len(cleaned_w) >= 3:
                        keywords.append(cleaned_w)
            
            best_score = 0
            for t, info in wiki_files.items():
                norm_title = _normalize_string_for_matching(t)
                score = 0
                for kw in keywords:
                    if kw in norm_title:
                        score += len(kw)
                if 'prestige' in norm_en and 'prestige' in norm_title:
                    score += 15
                if 'prestige' not in norm_en and 'prestige' in norm_title:
                    score -= 20
                if score > best_score:
                    best_score = score
                    best_candidate = info
                    
    if best_candidate and best_candidate.get('url'):
        return {
            "source": "LoL Fandom 4K/6K Master",
            "url": best_candidate['url'],
            "width": best_candidate.get('width', 3840),
            "height": best_candidate.get('height', 2160),
            "is_native_4k": True
        }

    # 2. UHDPaper.com 4K Duvar Kağıdı Arşivi Kontrolü (Morgana ve Yunara için fan art önleme)
    if c_low not in ['morgana', 'yunara']:
        uhd_url = search_uhdpaper_wallpaper(c_name, s_en, is_base=is_base)
        if uhd_url:
            return {
                "source": "UHD Paper (4K UHD)",
                "url": uhd_url,
                "width": 3840,
                "height": 2160,
                "is_native_4k": True
            }
        
    # 3. Fallback: DataDragon Official Splash (Lanczos ile 4K UHD'ye dönüştürülür)
    ddragon_url = skin_data.get('ddragon_splash_url') or f"https://ddragon.leagueoflegends.com/cdn/img/champion/splash/{c_alias}_{skin_data.get('skin_num', 0)}.jpg"
    return {
        "source": "Riot DataDragon (Lanczos 4K)",
        "url": ddragon_url,
        "width": 1215,
        "height": 717,
        "is_native_4k": False
    }

def download_skin_wallpaper(skin_data, force_4k=True, set_as_desktop=False):
    """
    Kostümün 4K duvar kağıdını indirir, gerekirse kristal netliğinde 3840x2160 (4K UHD) formatına ölçekler
    ve isteğe bağlı olarak doğrudan Windows masaüstü arka planı yapar.
    """
    c_name = skin_data.get('champion_name') or skin_data.get('champion_alias') or 'Champion'
    s_name = skin_data.get('name_tr') or skin_data.get('name_en') or 'Kostum'
    skin_id = skin_data.get('skin_id', 0)
    
    # Şampiyon klasörü
    champ_dir = os.path.join(USER_DOWNLOADS, get_clean_name(c_name))
    os.makedirs(champ_dir, exist_ok=True)
    
    clean_skin_name = get_clean_name(s_name)
    file_name = f"{get_clean_name(c_name)}_{clean_skin_name}_4K.jpg"
    target_path = os.path.join(champ_dir, file_name)

    # 1. Zaten indirilmişse bir daha indirme (Disk Cache Kontrolü)
    if os.path.exists(target_path) and os.path.getsize(target_path) > 10240:
        return {
            "status": "cached",
            "file_path": target_path,
            "width": 3840,
            "height": 2160,
            "source": "Disk Cache (Zaten İndirilmiş)",
            "file_size_mb": round(os.path.getsize(target_path) / (1024 * 1024), 2)
        }
    
    # En iyi görsel kaynağını çöz (LoL Fandom HD Master -> UHDPaper 4K -> DataDragon)
    resolved = resolve_best_hd_splash(skin_data)
    img_url = resolved['url']
    source_name = resolved['source']
    
    req_headers = dict(HEADERS)
    if 'uhdpaper.com' in img_url:
        req_headers['Referer'] = 'https://www.uhdpaper.com/'
    elif 'wikia.nocookie.net' in img_url:
        req_headers['Referer'] = 'https://leagueoflegends.fandom.com/'

    # İndir
    img_bytes = None
    try:
        req = urllib.request.Request(img_url, headers=req_headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            img_bytes = resp.read()
    except Exception as e:
        print(f"[StaticWP] Öncelikli URL indirilemedi ({img_url}), DataDragon deneniyor: {e}")
        c_alias = skin_data.get('champion_alias') or skin_data.get('champion_name') or 'Champion'
        skin_num = skin_data.get('skin_num', 0)
        fallback_url = f"https://ddragon.leagueoflegends.com/cdn/img/champion/splash/{c_alias}_{skin_num}.jpg"
        req_fb = urllib.request.Request(fallback_url, headers={'User-Agent': HEADERS['User-Agent']})
        with urllib.request.urlopen(req_fb, timeout=15) as resp_fb:
            img_bytes = resp_fb.read()
        source_name = "Riot DataDragon (Lanczos 4K)"

    import io
    img = Image.open(io.BytesIO(img_bytes))
    if img.mode != 'RGB':
        img = img.convert('RGB')
        
    orig_w, orig_h = img.size

    # Rakan / Xayah Base ikili görselinden tekil karaktere odaklanma (Solo Crop)
    c_low = c_name.lower()
    is_base = skin_data.get('is_base', False) or skin_data.get('skin_num', 0) == 0
    if is_base and orig_w > orig_h:
        if c_low == 'rakan':
            # Rakan solda: Sol %12 ile %68 arası kesilir (Xayah kadraj dışı kalır)
            img = img.crop((int(orig_w * 0.12), 0, int(orig_w * 0.68), orig_h))
            orig_w, orig_h = img.size
        elif c_low == 'xayah':
            # Xayah sağda: Sağ %42 ile %96 arası kesilir (Rakan kadraj dışı kalır)
            img = img.crop((int(orig_w * 0.42), 0, int(orig_w * 0.96), orig_h))
            orig_w, orig_h = img.size
    
    # 4K UHD Ölçekleme: Eğer görsel 4K'dan (3840x2160) küçükse ve force_4k True ise
    if force_4k and (orig_w < 3840 or orig_h < 2160):
        img = img.resize((3840, 2160), Image.Resampling.LANCZOS)
        img = img.filter(ImageFilter.UnsharpMask(radius=1.2, percent=100, threshold=3))
        final_w, final_h = 3840, 2160
    else:
        final_w, final_h = orig_w, orig_h
        
    # En yüksek kalite JPEG olarak kaydet
    img.save(target_path, 'JPEG', quality=95, subsampling=0)
    
    file_size_mb = round(os.path.getsize(target_path) / (1024 * 1024), 2)
    
    # Windows Duvar Kağıdı Yap
    desktop_set = False
    if set_as_desktop:
        desktop_set = set_desktop_wallpaper(target_path)
        
    return {
        "status": "success",
        "file_name": file_name,
        "file_path": target_path,
        "resolution": f"{final_w}x{final_h}",
        "original_resolution": f"{orig_w}x{orig_h}",
        "file_size_mb": file_size_mb,
        "source": source_name,
        "desktop_set": desktop_set,
        "champion": c_name,
        "skin_name": s_name
    }

def set_desktop_wallpaper(file_path):
    """
    Verilen görsel dosyasını Windows masaüstü duvar kağıdı yapar.
    """
    if sys.platform != 'win32':
        return False
        
    try:
        abs_path = os.path.abspath(file_path)
        if not os.path.exists(abs_path):
            return False
        # SPI_SETDESKWALLPAPER = 20, SPIF_UPDATEINIFILE = 1, SPIF_SENDCHANGE = 2
        res = ctypes.windll.user32.SystemParametersInfoW(20, 0, abs_path, 3)
        return bool(res)
    except Exception as e:
        print(f"[StaticWP] Masaüstü arka planı yapılırken hata: {e}")
        return False

def get_downloaded_static_wallpapers():
    """
    İndirilen tüm 4K statik duvar kağıtlarını listeler.
    """
    if not os.path.exists(USER_DOWNLOADS):
        return []
        
    items = []
    for root, dirs, files in os.walk(USER_DOWNLOADS):
        for f in files:
            if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                full_path = os.path.join(root, f)
                try:
                    stat = os.stat(full_path)
                    size_mb = round(stat.st_size / (1024 * 1024), 2)
                    mtime = stat.st_mtime
                    rel_dir = os.path.relpath(root, USER_DOWNLOADS)
                    champ_name = rel_dir if rel_dir != '.' else 'Genel'
                    
                    items.append({
                        "file_name": f,
                        "file_path": full_path,
                        "champ_name": champ_name,
                        "size_mb": size_mb,
                        "mtime": mtime,
                        "is_4k": True
                    })
                except Exception:
                    pass
                    
    # En yeni indirilen en üstte
    items.sort(key=lambda x: x['mtime'], reverse=True)
    return items

def open_download_folder(champ_name=None):
    target = USER_DOWNLOADS
    if champ_name:
        champ_dir = os.path.join(USER_DOWNLOADS, get_clean_name(champ_name))
        if os.path.exists(champ_dir):
            target = champ_dir
            
    if sys.platform == 'win32':
        os.startfile(target)
    return target

def delete_downloaded_wallpaper(file_path):
    if os.path.exists(file_path) and file_path.startswith(USER_DOWNLOADS):
        try:
            os.remove(file_path)
            return True
        except Exception:
            return False
    return False
