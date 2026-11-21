import os
import sys
import re
import time
import json
import shutil
import threading
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Try importing yt_dlp
try:
    import yt_dlp
except ImportError:
    yt_dlp = None

# Project Download Directory: Duvar Kağıtları/Canlı Duvar Kağıtları
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
USER_DOWNLOADS = os.path.join(ROOT_DIR, "Duvar Kağıtları", "Canlı Duvar Kağıtları")
os.makedirs(USER_DOWNLOADS, exist_ok=True)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9,tr;q=0.8',
}

ACTIVE_DOWNLOADS = {}

def get_clean_name(name):
    clean = re.sub(r'[\\/*?:"<>|]', '', name)
    clean = clean.replace(' ', '_').strip('_')
    return clean

def extract_direct_video_url(html, page_url=""):
    """
    Herhangi bir web sayfasından (DesktopHut, MotionBGS, MoeWalls vb.) doğrudan video linkini %100 doğrulukla çıkarır.
    DesktopHut sayfalarında 10 saniyelik düşük kaliteli önizleme yerine gerçek tam boyutlu dosyayı (/files/) önceliklendirir.
    """
    candidates = []

    # 1. DesktopHut tam çözünürlüklü asıl indirme dosyası (/files/....mp4)
    for m in re.finditer(r'href=["\']([^"\']+/files/[^"\']+\.(?:mp4|webm))["\']', html, re.I):
        candidates.append(m.group(1).strip())

    # 2. Doğrudan download niteliği taşıyan indirme butonları
    for m in re.finditer(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*download', html, re.I):
        candidates.append(m.group(1).strip())
    for m in re.finditer(r'id=["\']primaryDownloadBtn["\'][^>]*href=["\']([^"\']+)["\']', html, re.I):
        candidates.append(m.group(1).strip())

    # 3. /files/ içeren diğer bağlantılar
    for m in re.finditer(r'["\'](https?://[^\'"]+?/files/[^\'"]+)["\']', html, re.I):
        candidates.append(m.group(1).strip())

    # 4. Önizleme olmayan doğrudan yüksek kaliteli video URL'leri
    for m in re.finditer(r'["\'](https?://[^\'"]+?\.(?:mp4|webm))["\']', html, re.I):
        url_cand = m.group(1).strip()
        if '-player.mp4' not in url_cand and '/previews/' not in url_cand:
            candidates.append(url_cand)

    # 5. <source src="..."> (yalnızca asıl dosya bulunamazsa)
    for m in re.finditer(r'<source[^>]+src=["\']([^"\']+)["\']', html, re.I):
        candidates.append(m.group(1).strip())

    # 6. <video src="..."> (fallback)
    for m in re.finditer(r'<video[^>]+src=["\']([^"\']+)["\']', html, re.I):
        candidates.append(m.group(1).strip())

    valid = []
    seen = set()
    for c in candidates:
        if not c or c in seen:
            continue
        seen.add(c)
        
        if c.startswith('//'):
            c = 'https:' + c
        elif c.startswith('/'):
            if 'desktophut.com' in page_url:
                c = 'https://www.desktophut.com' + c
            elif 'motionbgs.com' in page_url:
                c = 'https://motionbgs.com' + c
            elif 'moewalls.com' in page_url:
                c = 'https://moewalls.com' + c
                
        if any(ext in c.lower() for ext in ['.mp4', '.webm', '/files/']) and not any(skip in c.lower() for skip in ['/page/', '/category/', '/tag/', '/about', '/search/', '/feed']):
            valid.append(c)

    return valid[0] if valid else ""

# ==============================================================================
# 1. DESKTOPHUT SCRAPER
# ==============================================================================
def _fetch_desktophut_item_details(item):
    page_url = item['page_url']
    try:
        req = urllib.request.Request(page_url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=8) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            
            # Direct video url extraction - tam çözünürlüklü linki önceliklendir
            direct_v = extract_direct_video_url(html, page_url)
            if direct_v:
                item['video_url'] = direct_v
            
            # Poster
            if not item.get('thumbnail'):
                posters = re.findall(r'poster=["\']([^"\']+)["\']', html)
                if posters:
                    item['thumbnail'] = posters[0]

            # Detect resolution & fps
            title_and_html = f"{item['title']} {html[:5000]}"
            if re.search(r'\b(4k|3840x2160|uhd)\b', title_and_html, re.I):
                item['resolution'] = '4K UHD'
            elif re.search(r'\b(2k|2560x1440|qhd)\b', title_and_html, re.I):
                item['resolution'] = '2K QHD'
            else:
                item['resolution'] = '1080p Full HD'
                
            if '60fps' in title_and_html.lower() or '60 fps' in title_and_html.lower():
                item['fps'] = '60 FPS'
            else:
                item['fps'] = '30/60 FPS'

            # File size clue
            size_match = re.search(r'(\d+(?:\.\d+)?\s*(?:MB|GB))', html, re.I)
            if size_match:
                item['file_size'] = size_match.group(1)
            else:
                item['file_size'] = "MP4"
                
            return item
    except Exception as e:
        return item

def search_desktophut(query, max_results=30):
    """
    DesktopHut (desktophut.com) üzerinde canlı duvar kağıdı arar.
    Doğrudan URL girişlerini, çoklu sayfalama (sayfa 1, 2) ve orijinal splash art önceliğini destekler.
    """
    clean_query = query.strip()
    if not clean_query:
        clean_query = "League of Legends"

    # Case 1: Kullanıcı doğrudan bir DesktopHut sayfa URL'si veya slug girmişse
    if 'desktophut.com/' in clean_query or clean_query.startswith('http'):
        direct_url = clean_query if clean_query.startswith('http') else f"https://{clean_query}"
        slug = direct_url.rstrip('/').split('/')[-1]
        title = slug.replace('-', ' ').title()
        single_item = {
            'id': f"dh_{slug}",
            'title': title,
            'page_url': direct_url,
            'video_url': "",
            'thumbnail': "",
            'source': 'DesktopHut',
            'source_badge': 'DesktopHut',
            'resolution': '4K / 2K',
            'fps': '60 FPS',
            'file_size': 'MP4',
            'downloadable': True,
            'type': 'video/mp4'
        }
        enriched = _fetch_desktophut_item_details(single_item)
        return [enriched]

    # Case 2: Çoklu sayfa araması (Sayfa 1 ve Sayfa 2 paralel)
    quoted = urllib.parse.quote(clean_query)
    search_urls = [
        f"https://www.desktophut.com/search/{quoted}",
        f"https://www.desktophut.com/search/{quoted}?page=2"
    ]

    html_pages = []
    def _fetch_page(u):
        try:
            req = urllib.request.Request(u, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=8) as resp:
                return resp.read().decode('utf-8', errors='ignore')
        except Exception:
            return ""

    with ThreadPoolExecutor(max_workers=2) as executor:
        html_pages = list(executor.map(_fetch_page, search_urls))

    results = []
    seen_slugs = set()
    candidates = []

    for html in html_pages:
        if not html:
            continue
        raw_links = re.findall(r'<a\s+[^>]*href=["\'](/[^"\'>\s]+)["\'][^>]*>(.*?)</a>', html, re.DOTALL | re.IGNORECASE)
        for href, inner in raw_links:
            if any(x in href.lower() for x in ['/search', '/feed', '/collections', '/category', '/tag', '/page', '/about', '/contact', '/privacy', '/terms', '/dmca', '/popular', '/type', '#', '/featured', '/must-have', '/discover', '/my', '/images', '/submit', '/ai-generator', '/w/', '/show/', '/rankings', '/explore']):
                continue
            slug = href.strip('/')
            if not slug or slug in seen_slugs:
                continue
            seen_slugs.add(slug)

            img_m = re.search(r'<img\s+[^>]*src=["\']([^"\']+)["\']', inner)
            thumb = img_m.group(1) if img_m else ""

            title_m = re.search(r'<img\s+[^>]*alt=["\']([^"\']+)["\']', inner)
            if title_m and title_m.group(1).strip():
                title = title_m.group(1).strip()
            else:
                title = slug.replace('-', ' ').title()

            title = re.sub(r'(?i)\s*(?:animated wallpaper preview|live wallpaper|animated wallpaper|hd live wallpaper|4k 60fps loop share|for pc)\b', '', title).strip()

            # Alakasız trend/öneri kartlarını filtrele (örn: Fiddlesticks aramasında Nissan GT-R, Itachi çıkmasın)
            query_words = [w for w in clean_query.lower().split() if len(w) > 2]
            if query_words and clean_query.lower() not in ('league of legends', 'lol', 'all'):
                text_to_check = f"{slug.lower()} {title.lower()}"
                if not any(w in text_to_check for w in query_words):
                    continue

            candidates.append({
                'id': f"dh_{slug}",
                'title': title,
                'page_url': f"https://www.desktophut.com/{slug}",
                'video_url': "",
                'thumbnail': thumb,
                'source': 'DesktopHut',
                'source_badge': 'DesktopHut',
                'resolution': '4K / 2K',
                'fps': '60 FPS',
                'file_size': 'MP4',
                'downloadable': True,
                'type': 'video/mp4'
            })
            if len(candidates) >= max_results:
                break
        if len(candidates) >= max_results:
            break

    # Splash / Orijinal olanları en üste al (Relevance sort)
    def _rank_candidate(c):
        score = 0
        t = (c['title'] + " " + c['page_url']).lower()
        if 'splash' in t:
            score += 15
        if '2k' in t or '4k' in t:
            score += 5
        if clean_query.lower() in t:
            score += 10
        return -score

    candidates.sort(key=_rank_candidate)

    if candidates:
        with ThreadPoolExecutor(max_workers=min(len(candidates), 10)) as executor:
            futures = [executor.submit(_fetch_desktophut_item_details, item) for item in candidates]
            for f in as_completed(futures):
                try:
                    res = f.result()
                    if res:
                        results.append(res)
                except Exception:
                    pass

    # Tekrar relevance sort
    results.sort(key=_rank_candidate)
    return results[:max_results]

# ==============================================================================
# 2. MOTIONBGS SCRAPER
# ==============================================================================
def search_motionbgs(query, max_results=20):
    """
    MotionBGS (motionbgs.com) 4K League of Legends ve anime canlı duvar kağıtlarını arar.
    Doğrudan URL girişlerini, unquoted HTML ayrıştırmasını ve 4K medya akışlarını tam destekler.
    """
    clean_query = query.strip()
    results = []

    # Case 1: Doğrudan MotionBGS bağlantısı girilmişse
    if 'motionbgs.com/' in clean_query or (clean_query.startswith('http') and 'motionbgs' in clean_query):
        direct_url = clean_query if clean_query.startswith('http') else f"https://{clean_query}"
        slug = direct_url.rstrip('/').split('/')[-1]
        try:
            req = urllib.request.Request(direct_url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=10) as resp:
                html = resp.read().decode('utf-8', errors='ignore')
            
            # Media ID bul (örn: /media/5114/fiddlesticks-lol)
            media_m = re.search(r'/media/(\d+)/([a-zA-Z0-9_-]+)', html)
            title_m = re.search(r'<title>(.*?)</title>', html)
            title = title_m.group(1).replace('Live Wallpaper', '').replace('(LoL)', '').strip().title() if title_m else slug.replace('-', ' ').title()
            
            if media_m:
                m_id = media_m.group(1)
                m_name = media_m.group(2).replace('.3840x2160', '').replace('.1920x1080', '').replace('.960x540', '')
                video_4k_url = f"https://motionbgs.com/media/{m_id}/{m_name}.3840x2160.mp4"
                video_1080p_url = f"https://motionbgs.com/media/{m_id}/{m_name}.1920x1080.mp4"
                thumb_url = f"https://motionbgs.com/i/c/960x540/media/{m_id}/{m_name}.jpg"
                
                return [{
                    'id': f"mb_{m_id}",
                    'title': title,
                    'page_url': direct_url,
                    'video_url': video_4k_url,
                    'video_1080p_url': video_1080p_url,
                    'thumbnail': thumb_url,
                    'source': 'MotionBGS',
                    'source_badge': 'MotionBGS 4K',
                    'resolution': '4K UHD (3840x2160)',
                    'fps': '60 FPS',
                    'file_size': '30-60 MB',
                    'downloadable': True,
                    'type': 'video/mp4'
                }]
        except Exception as e:
            print(f"⚠️ MotionBGS doğrudan link çekme hatası: {e}")

    # Case 2: Genel Arama (search?q= ve League of Legends tag)
    urls_to_try = [
        f"https://motionbgs.com/search?q={urllib.parse.quote(clean_query)}" if clean_query else "",
        "https://motionbgs.com/tag:league-of-legends/"
    ]

    seen_ids = set()

    for page_url in urls_to_try:
        if not page_url:
            continue
        try:
            req = urllib.request.Request(page_url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=10) as resp:
                html = resp.read().decode('utf-8', errors='ignore')

            # Unquoted ve Quoted HTML için esnek kart eşleştirme: <a ... href=/slug ...>
            # Örnek: <a title="Fiddlesticks (LoL) live wallpaper" href=/fiddlesticks-lol>
            raw_cards = re.findall(r'<a\b([^>]*\bhref=["\']?(/[^"\'>\s]+)["\']?[^>]*)>(.*?)</a>', html, re.DOTALL | re.IGNORECASE)

            for full_tag, href, inner in raw_cards:
                if any(x in href.lower() for x in ['/static', '/tag:', '/category', '/page', '/contact', '/privacy', '/terms', '/dmca', '/about', '/media', '/search', '#']):
                    continue

                slug = href.strip('/')
                if not slug:
                    continue

                # Title çek (title="...", alt="..." veya slug)
                title_m = re.search(r'title=["\']?([^"\'>]+)["\']?', full_tag)
                if not title_m:
                    title_m = re.search(r'alt=["\']?([^"\'>]+)["\']?', inner)
                title = title_m.group(1).strip() if title_m else slug.replace('-', ' ').title()
                title = re.sub(r'(?i)\s*(?:live wallpaper|animated wallpaper|free download)\b', '', title).strip()

                # Sorgu ile eşleşme kontrolü
                if clean_query and clean_query.lower() not in ('league of legends', 'lol', 'all'):
                    q_words = [w for w in clean_query.lower().split() if len(w) > 2]
                    check_str = f"{slug.lower()} {title.lower()}"
                    if not any(w in check_str for w in q_words):
                        continue

                # Media ID çek (/media/5114/fiddlesticks-lol)
                media_m = re.search(r'/media/(\d+)/([a-zA-Z0-9_-]+)', inner)
                if media_m:
                    m_id = media_m.group(1)
                    m_name = media_m.group(2).replace('.3840x2160', '').replace('.1920x1080', '').replace('.960x540', '').replace('.jpg', '').replace('.webp', '')

                    if m_id in seen_ids:
                        continue
                    seen_ids.add(m_id)

                    video_4k_url = f"https://motionbgs.com/media/{m_id}/{m_name}.3840x2160.mp4"
                    video_1080p_url = f"https://motionbgs.com/media/{m_id}/{m_name}.1920x1080.mp4"
                    thumb_url = f"https://motionbgs.com/i/c/960x540/media/{m_id}/{m_name}.jpg"

                    results.append({
                        'id': f"mb_{m_id}",
                        'title': title,
                        'page_url': f"https://motionbgs.com/{slug}",
                        'video_url': video_4k_url,
                        'video_1080p_url': video_1080p_url,
                        'thumbnail': thumb_url,
                        'source': 'MotionBGS',
                        'source_badge': 'MotionBGS 4K',
                        'resolution': '4K UHD (3840x2160)',
                        'fps': '60 FPS',
                        'file_size': '30-60 MB',
                        'downloadable': True,
                        'type': 'video/mp4'
                    })

                if len(results) >= max_results:
                    break
        except Exception as e:
            print(f"⚠️ MotionBGS Tarama Hatası ({page_url}): {e}")

    return results

# ==============================================================================
# 3. YOUTUBE / OFFICIAL RIOT LOGIN & ANIMATED SPLASH SCRAPER
# ==============================================================================
def search_youtube_wallpapers(query, max_results=12):
    """
    YouTube üzerinde Riot Games Resmi Giriş Ekranları, SkinSpotlights ve 4K 60FPS animasyonlu duvar kağıtlarını arar.
    """
    if not yt_dlp:
        return []

    original_user_query = query.strip()
    if not original_user_query:
        clean_query = "League of Legends official animated login screen"
    else:
        # Enriched query for highest quality animated splashes
        clean_query = f"League of Legends {original_user_query} animated splash 4k 60fps"

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
        'youtube_include_dash_manifest': False,
        'extractor_args': {'youtube': {'player_client': ['android']}}
    }

    results = []
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            search_res = ydl.extract_info(f"ytsearch{max_results*2}:{clean_query}", download=False)
            entries = search_res.get('entries', []) or []
            
            for entry in entries:
                if not entry:
                    continue
                v_id = entry.get('id')
                title = entry.get('title', '')
                dur = entry.get('duration', 0)
                uploader = entry.get('uploader', 'YouTube')
                
                if not v_id or not title:
                    continue
                    
                # Filter out very long gameplay videos (wallpapers / login screens are usually under 10 minutes)
                if dur and dur > 900:
                    continue

                # Alakasız YouTube sonuçlarını filtrele (örn: Fiddlesticks ararken Syndra/Yone çıkmasın)
                if original_user_query and original_user_query.lower() not in ('league of legends', 'lol', 'all'):
                    q_words = [w for w in original_user_query.lower().split() if len(w) > 2]
                    if q_words and not any(w in title.lower() for w in q_words):
                        continue
                    
                dur_str = f"{int(dur // 60)}:{int(dur % 60):02d}" if dur else "Loop"
                
                # Check resolution keywords
                res_badge = "4K / 1080p"
                if "4k" in title.lower():
                    res_badge = "4K UHD"
                elif "1080" in title.lower():
                    res_badge = "1080p FHD"

                results.append({
                    'id': f"yt_{v_id}",
                    'title': title,
                    'page_url': f"https://www.youtube.com/watch?v={v_id}",
                    'video_url': f"https://www.youtube.com/watch?v={v_id}",
                    'thumbnail': f"https://i.ytimg.com/vi/{v_id}/hqdefault.jpg",
                    'source': 'YouTube',
                    'source_badge': f"YouTube ({uploader[:15]})",
                    'resolution': res_badge,
                    'fps': '60 FPS',
                    'file_size': dur_str,
                    'downloadable': True,
                    'type': 'youtube'
                })
                if len(results) >= max_results:
                    break
    except Exception as e:
        print(f"⚠️ YouTube Canlı Duvar Kağıdı Arama Hatası: {e}")

    return results

# ==============================================================================
# 4. UNIFIED SEARCH (ALL SOURCES PARALLEL)
# ==============================================================================
def search_wallpapers(query="Yone", source="all", resolution="all", max_results=30):
    """
    Tüm kaynaklarda (DesktopHut, MotionBGS, YouTube) paralel arama yapar ve birleştirir.
    """
    all_results = []
    tasks = []

    with ThreadPoolExecutor(max_workers=3) as executor:
        if source in ("all", "desktophut"):
            tasks.append(("desktophut", executor.submit(search_desktophut, query, 30)))
        if source in ("all", "motionbgs"):
            tasks.append(("motionbgs", executor.submit(search_motionbgs, query, 20)))
        if source in ("all", "youtube"):
            tasks.append(("youtube", executor.submit(search_youtube_wallpapers, query, 15)))

        for src_name, fut in tasks:
            try:
                res = fut.result()
                if res:
                    all_results.extend(res)
            except Exception as e:
                print(f"⚠️ {src_name} arama işlemi başarısız: {e}")

    # Resolution filter
    if resolution != "all":
        res_clean = resolution.lower()
        if "4k" in res_clean:
            all_results = [r for r in all_results if "4k" in r.get('resolution', '').lower() or "4k" in r.get('title', '').lower()]
        elif "2k" in res_clean:
            all_results = [r for r in all_results if "2k" in r.get('resolution', '').lower() or "2k" in r.get('title', '').lower()]
        elif "1080" in res_clean:
            all_results = [r for r in all_results if "1080" in r.get('resolution', '').lower() or "1080" in r.get('title', '').lower()]

    # Sort results: Prioritize exact query match, official splash arts, 4K/2K and high quality sources
    def sort_key(item):
        score = 0
        t = (item.get('title', '') + ' ' + item.get('page_url', '')).lower()
        q_lower = query.lower().strip()
        if q_lower and q_lower in t:
            score += 50
        elif any(w in t for w in q_lower.split() if len(w) > 2):
            score += 30
        if 'splash' in t:
            score += 20
        if "4k" in item.get('resolution', '').lower() or "4k" in t:
            score += 15
        elif "2k" in item.get('resolution', '').lower() or "2k" in t:
            score += 10
        if item.get('source') == 'MotionBGS':
            score += 8
        elif item.get('source') == 'DesktopHut':
            score += 6
        return -score

    all_results.sort(key=sort_key)
    return all_results[:max_results]

# ==============================================================================
# 5. HIGH-SPEED DOWNLOAD ENGINE (MP4 & YOUTUBE 4K)
# ==============================================================================
def _resolve_direct_download_url(item_data):
    """
    Öğe için en sağlam doğrudan video URL'sini çözer.
    DesktopHut için önizleme yerine asıl tam boyutlu dosyayı (/files/) garanti eder.
    MotionBGS için HEAD request yerine donmayan GET Range doğrulaması yapar.
    """
    video_url = item_data.get('video_url') or ''
    page_url = item_data.get('page_url') or ''
    source = item_data.get('source') or ''

    # DesktopHut: Eğer video_url bir önizleme ise (-player.mp4) veya boşsa, sayfayı açıp asıl dosyayı al
    if source == 'DesktopHut' or 'desktophut.com' in page_url:
        is_preview = not video_url or '-player.mp4' in video_url or '/previews/' in video_url
        if is_preview and page_url and page_url.startswith('http'):
            try:
                req = urllib.request.Request(page_url, headers=HEADERS)
                req.add_header('Referer', 'https://www.desktophut.com/')
                with urllib.request.urlopen(req, timeout=8) as resp:
                    html = resp.read().decode('utf-8', errors='ignore')
                    extracted = extract_direct_video_url(html, page_url)
                    if extracted and '/files/' in extracted:
                        video_url = extracted
                    elif not video_url and extracted:
                        video_url = extracted
            except Exception as e:
                safe_print(f"⚠️ DesktopHut URL çözümleme uyarısı ({page_url}): {e}")

    # Diğer genel web kaynakları
    elif not video_url or not any(video_url.lower().endswith(ext) for ext in ['.mp4', '.webm']):
        if page_url and page_url.startswith('http'):
            try:
                req = urllib.request.Request(page_url, headers=HEADERS)
                with urllib.request.urlopen(req, timeout=8) as resp:
                    html = resp.read().decode('utf-8', errors='ignore')
                    extracted = extract_direct_video_url(html, page_url)
                    if extracted:
                        video_url = extracted
            except Exception as e:
                safe_print(f"⚠️ Video URL çözümleme uyarısı ({page_url}): {e}")

    # MotionBGS URL resolver: HEAD request yerine GET Range kullanarak donmaları önle
    if source == 'MotionBGS' or 'motionbgs.com' in page_url:
        candidates = [
            video_url,
            item_data.get('video_1080p_url'),
            video_url.replace('.3840x2160', '.1920x1080') if video_url else '',
            video_url.replace('.3840x2160', '') if video_url else '',
            video_url.replace('.mp4', '.webm') if video_url else ''
        ]
        for cand in candidates:
            if cand and cand.startswith('http'):
                try:
                    check_req = urllib.request.Request(cand, headers=HEADERS)
                    check_req.add_header('Range', 'bytes=0-100')
                    check_req.add_header('Referer', 'https://motionbgs.com/')
                    with urllib.request.urlopen(check_req, timeout=4) as chk_resp:
                        if chk_resp.status in (200, 206, 302):
                            video_url = cand
                            break
                except Exception:
                    continue

    return video_url or page_url

def safe_print(msg):
    try:
        print(msg, flush=True)
    except Exception:
        try:
            clean_msg = msg.encode('ascii', errors='replace').decode('ascii')
            print(clean_msg, flush=True)
        except Exception:
            pass

def download_wallpaper_task(download_id, item_data, target_folder=None, progress_callback=None):
    """
    Verilen canlı duvar kağıdı öğesini belirtilen klasöre en yüksek kalitede indirir.
    Hata yakalama, socket timeout, Referer başlıkları ve canlı ilerleme garantilidir.
    """
    import socket
    socket.setdefaulttimeout(25)

    if not target_folder:
        target_folder = USER_DOWNLOADS
    os.makedirs(target_folder, exist_ok=True)

    title = item_data.get('title', 'wallpaper')
    clean_title = get_clean_name(title)
    source = item_data.get('source', '')
    page_url = item_data.get('page_url', '')

    ACTIVE_DOWNLOADS[download_id] = {
        'id': download_id,
        'title': title,
        'status': 'downloading',
        'progress': 1,
        'speed': 'Hazırlanıyor...',
        'file_path': '',
        'error': None
    }

    try:
        # Case A: YouTube Download using yt-dlp 4K / 1080p
        if source == 'YouTube' or 'youtube.com' in page_url or 'youtu.be' in page_url:
            output_template = os.path.join(target_folder, f"{clean_title}.%(ext)s")
            
            def yt_progress_hook(d):
                if d['status'] == 'downloading':
                    total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                    downloaded = d.get('downloaded_bytes') or 0
                    pct = int((downloaded / total_bytes * 100)) if total_bytes > 0 else 50
                    speed = d.get('speed') or 0
                    speed_str = f"{speed / (1024*1024):.1f} MB/s" if speed > 1024*1024 else f"{speed / 1024:.0f} KB/s"
                    
                    ACTIVE_DOWNLOADS[download_id]['progress'] = min(max(pct, 1), 99)
                    ACTIVE_DOWNLOADS[download_id]['speed'] = speed_str
                    if progress_callback:
                        progress_callback(download_id, min(pct, 99), speed_str)

            ydl_opts = {
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best[ext=mp4]/best',
                'outtmpl': output_template,
                'merge_output_format': 'mp4',
                'quiet': True,
                'no_warnings': True,
                'socket_timeout': 30,
                'progress_hooks': [yt_progress_hook]
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(page_url, download=True)
                final_filename = ydl.prepare_filename(info)
                base_without_ext = os.path.splitext(final_filename)[0]
                if os.path.exists(base_without_ext + '.mp4'):
                    final_filename = base_without_ext + '.mp4'
                elif not os.path.exists(final_filename):
                    for cand_ext in ['.mp4', '.mkv', '.webm']:
                        if os.path.exists(base_without_ext + cand_ext):
                            final_filename = base_without_ext + cand_ext
                            break

            ACTIVE_DOWNLOADS[download_id]['progress'] = 100
            ACTIVE_DOWNLOADS[download_id]['speed'] = 'Tamamlandı'
            ACTIVE_DOWNLOADS[download_id]['status'] = 'completed'
            ACTIVE_DOWNLOADS[download_id]['file_path'] = final_filename
            safe_print(f"✅ Canlı Duvar Kağıdı İndirildi: {final_filename}")
            return True, final_filename

        # Case B: Direct MP4 / WebM streaming (DesktopHut / MotionBGS)
        else:
            resolved_url = _resolve_direct_download_url(item_data)
            if not resolved_url or not resolved_url.startswith('http'):
                raise ValueError(f"Geçerli bir video indirme bağlantısı bulunamadı ({title})")

            # URL temizliği ve güvenli kodlama
            if '%' not in resolved_url:
                clean_url = urllib.parse.quote(resolved_url, safe=':/?&=%#')
            else:
                clean_url = resolved_url

            ext = ".webm" if ".webm" in resolved_url.lower() else ".mp4"
            final_filename = os.path.join(target_folder, f"{clean_title}{ext}")

            req = urllib.request.Request(clean_url, headers=dict(HEADERS))
            req.add_header('Accept-Encoding', 'identity')
            if 'desktophut.com' in clean_url:
                req.add_header('Referer', 'https://www.desktophut.com/')
            elif 'motionbgs.com' in clean_url:
                req.add_header('Referer', 'https://motionbgs.com/')

            with urllib.request.urlopen(req, timeout=20) as resp:
                if resp.status not in (200, 206):
                    raise ValueError(f"Sunucu hatası: HTTP {resp.status}")

                total_size = int(resp.headers.get('content-length', 0) or 0)
                downloaded = 0
                chunk_size = 128 * 1024 # 128 KB chunks
                
                start_time = time.time()
                with open(final_filename, 'wb') as f:
                    while True:
                        chunk = resp.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        elapsed = time.time() - start_time
                        speed = downloaded / elapsed if elapsed > 0 else 0
                        speed_str = f"{speed / (1024*1024):.1f} MB/s" if speed > 1024*1024 else f"{speed / 1024:.0f} KB/s"
                        
                        if total_size > 0:
                            pct = min(int(downloaded / total_size * 100), 99)
                        else:
                            # Content-length yoksa tahmini megabayt tabanlı ilerleme
                            pct = min(int((downloaded / (15 * 1024 * 1024)) * 90), 95)
                        
                        ACTIVE_DOWNLOADS[download_id]['progress'] = max(pct, 2)
                        ACTIVE_DOWNLOADS[download_id]['speed'] = speed_str
                        if progress_callback:
                            progress_callback(download_id, pct, speed_str)

            ACTIVE_DOWNLOADS[download_id]['progress'] = 100
            ACTIVE_DOWNLOADS[download_id]['speed'] = 'Tamamlandı'
            ACTIVE_DOWNLOADS[download_id]['status'] = 'completed'
            ACTIVE_DOWNLOADS[download_id]['file_path'] = final_filename
            safe_print(f"✅ Canlı Duvar Kağıdı İndirildi: {final_filename}")
            return True, final_filename

    except Exception as e:
        ACTIVE_DOWNLOADS[download_id]['status'] = 'error'
        ACTIVE_DOWNLOADS[download_id]['error'] = str(e)
        safe_print(f"❌ Duvar Kağıdı İndirme Hatası ({title}): {e}")
        return False, str(e)

def start_download_async(item_data, target_folder=None, champ_name=None):
    """
    Arka planda thread başlatır ve download ID döndürür.
    Hem USER_DOWNLOADS klasörüne hem de belirtilmişse Champions/{Champ}/Live_Wallpapers klasörüne konumlandırır.
    """
    import uuid
    download_id = f"dl_{int(time.time())}_{uuid.uuid4().hex[:6]}"
    
    if not target_folder:
        target_folder = USER_DOWNLOADS

    # Hemen başlatma kaydı ekle (frontend anında status görebilsin)
    ACTIVE_DOWNLOADS[download_id] = {
        'id': download_id,
        'title': item_data.get('title', 'wallpaper'),
        'status': 'downloading',
        'progress': 1,
        'speed': 'Hazırlanıyor...',
        'file_path': '',
        'error': None
    }

    def _task_wrapper():
        ok, file_path = download_wallpaper_task(download_id, item_data, target_folder)
        if ok and file_path and champ_name and champ_name != 'ALL':
            try:
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                champ_live_dir = os.path.join(base_dir, "Champions", champ_name, "Live_Wallpapers")
                os.makedirs(champ_live_dir, exist_ok=True)
                dest = os.path.join(champ_live_dir, os.path.basename(file_path))
                if os.path.abspath(file_path) != os.path.abspath(dest):
                    shutil.copy2(file_path, dest)
                    safe_print(f"📁 Şampiyon klasörüne kopyalandı: {dest}")
            except Exception as e:
                safe_print(f"⚠️ Şampiyon klasörüne kopyalama hatası: {e}")

    threading_thread = threading.Thread(
        target=_task_wrapper,
        daemon=True
    )
    threading_thread.start()
    return download_id

# ==============================================================================
# 6. LOCAL DOWNLOADED WALLPAPERS LIST & OPEN FOLDER
# ==============================================================================
def get_downloaded_wallpapers():
    """
    Hem Downloads/LoL Canlı Duvar Kağıtları hem de Champions altındaki Live_Wallpapers klasörlerindeki videoları listeler.
    """
    files = []
    
    # 1. Global Downloads directory
    if os.path.exists(USER_DOWNLOADS):
        for f in os.listdir(USER_DOWNLOADS):
            if f.lower().endswith(('.mp4', '.webm', '.mkv', '.mov')):
                full_p = os.path.join(USER_DOWNLOADS, f)
                stat = os.stat(full_p)
                files.append({
                    'name': f,
                    'title': f.rsplit('.', 1)[0].replace('_', ' '),
                    'path': full_p,
                    'size_mb': f"{stat.st_size / (1024*1024):.1f} MB",
                    'date': time.strftime("%d.%m.%Y %H:%M", time.localtime(stat.st_mtime)),
                    'champion': 'Genel'
                })
                
    # 2. Champions directory
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    champions_dir = os.path.join(root_dir, "Champions")
    if os.path.exists(champions_dir):
        for champ in os.listdir(champions_dir):
            c_path = os.path.join(champions_dir, champ, "Live_Wallpapers")
            if os.path.exists(c_path):
                for f in os.listdir(c_path):
                    if f.lower().endswith(('.mp4', '.webm', '.mkv', '.mov')):
                        full_p = os.path.join(c_path, f)
                        stat = os.stat(full_p)
                        files.append({
                            'name': f,
                            'title': f.rsplit('.', 1)[0].replace('_', ' '),
                            'path': full_p,
                            'size_mb': f"{stat.st_size / (1024*1024):.1f} MB",
                            'date': time.strftime("%d.%m.%Y %H:%M", time.localtime(stat.st_mtime)),
                            'champion': champ
                        })

    # Sort newest first
    files.sort(key=lambda x: os.stat(x['path']).st_mtime if os.path.exists(x['path']) else 0, reverse=True)
    return files

def open_download_folder(champ_name=None):
    """
    İndirilenlerin klasörünü Windows Explorer ile açar.
    """
    target = USER_DOWNLOADS
    if champ_name:
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        c_path = os.path.join(root_dir, "Champions", champ_name, "Live_Wallpapers")
        if os.path.exists(c_path):
            target = c_path

    os.makedirs(target, exist_ok=True)
    try:
        os.startfile(target)
    except Exception:
        subprocess.Popen(
            ["explorer", target],
            creationflags=0x08000000 if sys.platform == 'win32' else 0
        )
    return target
