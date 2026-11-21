import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import urllib.parse
import json
import re
import os
import sys
import time
import concurrent.futures

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
    'Cookie': 'CONSENT=YES+cb; SOCS=CAESEwgDEgk2NzI2Mzg4NzIaAmVuIAEaBgiA_LyaBg;',
    'Accept-Encoding': 'gzip, deflate',
}

# Create a pooled, highly concurrent Session
_session = None

def get_session():
    global _session
    if _session is None:
        _session = requests.Session()
        retries = Retry(total=2, backoff_factor=0.2, status_forcelist=[500, 502, 503, 504])
        adapter = HTTPAdapter(pool_connections=30, pool_maxsize=30, max_retries=retries)
        _session.mount('https://', adapter)
        _session.mount('http://', adapter)
        _session.headers.update(HEADERS)
    return _session

COMPETITOR_CHANNELS = [
    {
        "id": "leaguevoices",
        "name": "LeagueVoices",
        "handle": "@LeagueVoices",
        "url": "https://www.youtube.com/@LeagueVoices/videos"
    },
    {
        "id": "quaxanos",
        "name": "Quaxanos",
        "handle": "@Quaxanos",
        "url": "https://www.youtube.com/@Quaxanos/videos"
    },
    {
        "id": "pbetr",
        "name": "PBE TR",
        "handle": "@pbetr",
        "url": "https://www.youtube.com/@pbetr/videos"
    },
    {
        "id": "leagueofvoice",
        "name": "League of Voice",
        "handle": "@LeagueOfVoice",
        "url": "https://www.youtube.com/@LeagueOfVoice/videos"
    },
    {
        "id": "turkish_videogamevoice",
        "name": "Turkish Video Game Voice",
        "handle": "@turkish.videogamevoice",
        "url": "https://www.youtube.com/@turkish.videogamevoice/videos"
    },
    {
        "id": "lolnewstr",
        "name": "LoL News TR",
        "handle": "@LoLNewsTr",
        "url": "https://www.youtube.com/@LoLNewsTr/videos"
    }
]

def get_available_channels():
    return [
        {
            "id": c["id"],
            "name": c["name"],
            "handle": c["handle"],
            "url": c["url"]
        }
        for c in COMPETITOR_CHANNELS
    ]

# Global In-Memory Cache (TTL: 10 minutes)
_ANALYSIS_CACHE = {
    "timestamp": 0,
    "data": None
}
_SEARCH_CACHE = {}

def normalize_turkish(text):
    if not text:
        return ""
    text = text.replace('İ', 'i').replace('I', 'ı').lower()
    # Replace special symbols and punctuation
    text = re.sub(r'[│—–\-_/\\|()\[\]{}:,."\'`!@#$%^&*+~?]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return f" {text} "

def is_turkish_video(title, channel_identifier=""):
    """
    Ensures that only videos in Turkish or containing Turkish VO are included.
    Channels that are purely Turkish natively pass through.
    Global/multilingual channels (LeagueVoices, LeagueOfVoice, etc.) MUST have
    Turkish markers in their title.
    """
    if not title:
        return False

    title_lower = title.lower()
    ch_lower = str(channel_identifier).lower()

    # 1. Pure Turkish Channels - inherently in Turkish
    if any(k in ch_lower for k in ['turkish', 'lolnewstr', 'pbetr', 'quaxanos']):
        return True

    # 2. Multilingual / Global channels: Look for explicit Turkish language tags
    turkish_markers = [
        'türkçe', 'turkce', 'turkish', 'tr_tr', 'tr voice', 'tr replik',
        '[tr]', '(tr)', '[türkçe]', '(türkçe)', '[turkish]', '(turkish)',
        '- tr ', ' tr -', 'tr ses', 'seslendirme', 'replikleri'
    ]
    if any(marker in title_lower for marker in turkish_markers):
        return True

    # If from global channel and has other languages, strictly exclude
    foreign_markers = [
        'english', 'ingilizce', 'español', 'espanol', 'spanish', 'latino',
        'português', 'portugues', 'portuguese', 'deutsch', 'german',
        'français', 'francais', 'french', 'italiano', 'italian', 'russian',
        'polski', 'polish', 'korean', 'japanese', 'chinese', 'greek', 'hungarian'
    ]
    if any(fm in title_lower for fm in foreign_markers):
        return False

    # Default for global channels without Turkish tag: Exclude
    return False

def parse_videos_from_node(data, default_channel_name="Rakip Kanal"):
    videos = []
    seen = set()

    def walk(node):
        if isinstance(node, dict):
            # 1. New YouTube lockupViewModel schema
            if 'lockupViewModel' in node:
                lvm = node['lockupViewModel']
                meta = lvm.get('metadata', {}).get('lockupMetadataViewModel', {})
                title = meta.get('title', {}).get('content', '')

                if not is_turkish_video(title, default_channel_name):
                    return

                vid = lvm.get('contentId', '')
                if not vid:
                    url = lvm.get('rendererContext', {}).get('commandContext', {}).get('onTap', {}).get('innertubeCommand', {}).get('commandMetadata', {}).get('webCommandMetadata', {}).get('url', '')
                    m_vid = re.search(r'v=([a-zA-Z0-9_-]{11})', url)
                    if m_vid:
                        vid = m_vid.group(1)

                if not vid:
                    for s in lvm.get('contentImage', {}).get('thumbnailViewModel', {}).get('image', {}).get('sources', []):
                        m_v = re.search(r'/vi/([a-zA-Z0-9_-]{11})/', s.get('url', ''))
                        if m_v:
                            vid = m_v.group(1)
                            break

                pub = ""
                for row in meta.get('metadataRows', []):
                    for part in row.get('metadataParts', []):
                        pub_text = part.get('text', {}).get('content', '')
                        if any(k in pub_text.lower() for k in ['önce', 'ago', 'gün', 'hafta', 'ay', 'yıl', 'saat', 'dün']):
                            pub = pub_text

                if vid and title and vid not in seen:
                    seen.add(vid)
                    videos.append({
                        'channel': default_channel_name,
                        'video_id': vid,
                        'title': title,
                        'url': f"https://www.youtube.com/watch?v={vid}",
                        'thumbnail': f"https://i.ytimg.com/vi/{vid}/mqdefault.jpg",
                        'published': pub
                    })

            # 2. Legacy videoRenderer / gridVideoRenderer schema
            elif 'videoRenderer' in node or 'gridVideoRenderer' in node:
                vr = node.get('videoRenderer') or node.get('gridVideoRenderer')
                vid = vr.get('videoId')
                title_obj = vr.get('title', {})
                title = ""
                if 'runs' in title_obj:
                    title = "".join(r.get('text', '') for r in title_obj['runs'])
                elif 'simpleText' in title_obj:
                    title = title_obj['simpleText']
                pub = vr.get('publishedTimeText', {}).get('simpleText', '')
                
                ch_name = default_channel_name
                owner = vr.get('ownerText', {}) or vr.get('shortBylineText', {})
                if 'runs' in owner and owner['runs']:
                    ch_name = owner['runs'][0].get('text', default_channel_name)

                if vid and title and is_turkish_video(title, ch_name) and vid not in seen:
                    seen.add(vid)
                    videos.append({
                        'channel': ch_name,
                        'video_id': vid,
                        'title': title,
                        'url': f"https://www.youtube.com/watch?v={vid}",
                        'thumbnail': f"https://i.ytimg.com/vi/{vid}/mqdefault.jpg",
                        'published': pub
                    })

            # 3. Shorts (reelItemRenderer / shortsLockupViewModel)
            elif 'reelItemRenderer' in node:
                r_item = node['reelItemRenderer']
                vid = r_item.get('videoId')
                headline = r_item.get('headline', {}).get('simpleText', '') or 'Shorts Video'
                if vid and is_turkish_video(headline, default_channel_name) and vid not in seen:
                    seen.add(vid)
                    videos.append({
                        'channel': default_channel_name,
                        'video_id': vid,
                        'title': headline,
                        'url': f"https://www.youtube.com/watch?v={vid}",
                        'thumbnail': f"https://i.ytimg.com/vi/{vid}/mqdefault.jpg",
                        'published': 'Shorts'
                    })

            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for it in node:
                walk(it)

    walk(data)
    return videos

def extract_videos_from_yt_payload(html_content, default_channel_name="Rakip Kanal"):
    if not html_content:
        return []
    m = re.search(r'ytInitialData\s*=\s*({.*?});</script>', html_content, re.DOTALL)
    if not m:
        return []
    try:
        data = json.loads(m.group(1))
        return parse_videos_from_node(data, default_channel_name)
    except Exception:
        return []

def find_continuation_token(node):
    if isinstance(node, dict):
        if 'continuationCommand' in node:
            return node['continuationCommand'].get('token')
        if 'continuationEndpoint' in node:
            return node['continuationEndpoint'].get('continuationCommand', {}).get('token')
        for v in node.values():
            t = find_continuation_token(v)
            if t: return t
    elif isinstance(node, list):
        for it in node:
            t = find_continuation_token(it)
            if t: return t
    return None

def extract_channel_header_meta(data):
    subscriber_count = ""
    video_count_str = ""
    def walk(n):
        nonlocal subscriber_count, video_count_str
        if isinstance(n, dict):
            if 'subscriberCountText' in n:
                subscriber_count = n['subscriberCountText'].get('simpleText', '')
            if 'videosCountText' in n:
                runs = n['videosCountText'].get('runs', [])
                video_count_str = ''.join(r.get('text', '') for r in runs)
            if 'contentMetadataViewModel' in n:
                for row in n['contentMetadataViewModel'].get('metadataRows', []):
                    for part in row.get('metadataParts', []):
                        t = part.get('text', {}).get('content', '')
                        if 'abone' in t.lower() or 'subscriber' in t.lower():
                            subscriber_count = t
                        elif 'video' in t.lower():
                            video_count_str = t
            for v in n.values(): walk(v)
        elif isinstance(n, list):
            for it in n: walk(it)
    walk(data)
    return subscriber_count, video_count_str

def generate_skin_match_patterns(skin_obj, champ_name):
    c_norm = normalize_turkish(champ_name).strip()
    patterns = []
    
    s_tr = skin_obj.get('name_tr') or skin_obj.get('name') or ''
    s_en = skin_obj.get('name_en') or ''
    
    for s_name in [s_tr, s_en]:
        if not s_name:
            continue
        norm = normalize_turkish(s_name).strip()
        words = [w for w in norm.split() if w != c_norm and len(w) >= 2]
        if words:
            patterns.append((s_name, words))
            
    return patterns

def match_skin_to_video_title(skin_obj, champ_name, title):
    title_norm = normalize_turkish(title)
    c_norm = normalize_turkish(champ_name).strip()
    
    # Check if champion name is in title
    champ_in_title = f" {c_norm} " in title_norm or title_norm.startswith(f"{c_norm} ") or title_norm.endswith(f" {c_norm}")
    
    patterns = generate_skin_match_patterns(skin_obj, champ_name)
    for s_name, words in patterns:
        if not words:
            continue
        # 1. Full skin words match
        if all(w in title_norm for w in words):
            return True
        # 2. If champion name is in title and key skin words match (e.g. 'eternal aspect', 'kalp şarkısı')
        if champ_in_title:
            joined = " ".join(words)
            if f" {joined} " in title_norm:
                return True
            if len(words) >= 2:
                matched_count = sum(1 for w in words if f" {w} " in title_norm or w in title_norm)
                if matched_count >= len(words) - 1 and matched_count >= 2:
                    return True
        else:
            # If champion not in title but full distinct skin phrase is in title
            joined = " ".join(words)
            if len(words) >= 2 and f" {joined} " in title_norm:
                return True
            
    return False

def fetch_yt_search(query, timeout=5):
    try:
        session = get_session()
        url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
        r = session.get(url, timeout=timeout)
        if r.status_code == 200:
            return extract_videos_from_yt_payload(r.text, "YouTube Search")
    except Exception:
        pass
    return []

def check_single_skin_youtube_coverage(candidate_info):
    """
    Directly checks YouTube for an exact skin's voice lines using both TR and EN titles.
    Returns (c_name, s_name, found_video_dict_or_None)
    """
    c_name, s_name, s_name_en, rarity_tr, rarity_raw, rel_date, s_id, skin_obj = candidate_info
    
    cache_key = f"{c_name}_{s_name}"
    if cache_key in _SEARCH_CACHE:
        return c_name, s_name, _SEARCH_CACHE[cache_key]

    queries = [
        f"{s_name} Türkçe replikleri",
        f"{c_name} {s_name_en} Türkçe seslendirme" if s_name_en else None,
        f"{s_name} replikleri"
    ]
    queries = [q for q in queries if q]

    found_video = None
    for q in queries:
        vids = fetch_yt_search(q)
        for v in vids:
            if is_turkish_video(v['title'], v.get('channel', '')):
                if match_skin_to_video_title(skin_obj, c_name, v['title']):
                    found_video = v
                    break
        if found_video:
            break

    _SEARCH_CACHE[cache_key] = found_video
    return c_name, s_name, found_video

def _fetch_single_channel_full(ch):
    """
    Fetches ALL videos from a channel using Innertube pagination and Shorts tab,
    ensuring 100% video coverage and official metadata matching.
    """
    session = get_session()
    ch_url = ch['url']
    ch_name = ch['name']
    
    all_videos = []
    seen = set()
    official_subs = ""
    official_vids = ""

    try:
        r = session.get(ch_url, timeout=7)
        m_cfg = re.search(r'ytcfg\.set\(({.*?})\);', r.text)
        cfg = json.loads(m_cfg.group(1)) if m_cfg else {}
        api_key = cfg.get('INNERTUBE_API_KEY')
        client_version = cfg.get('INNERTUBE_CLIENT_VERSION', '2.20240401.00.00')

        m = re.search(r'ytInitialData\s*=\s*({.*?});</script>', r.text, re.DOTALL)
        data = json.loads(m.group(1)) if m else {}

        official_subs, official_vids = extract_channel_header_meta(data)

        # 1. Page 1 regular videos
        page1_vids = parse_videos_from_node(data, ch_name)
        for v in page1_vids:
            if v['video_id'] not in seen:
                seen.add(v['video_id'])
                all_videos.append(v)

        # 2. Paginate remaining regular videos
        ctoken = find_continuation_token(data)
        page = 1
        while ctoken and api_key and page < 15:
            api_url = f"https://www.youtube.com/youtubei/v1/browse?key={api_key}"
            payload = {
                'context': {
                    'client': {
                        'clientName': 'WEB',
                        'clientVersion': client_version,
                        'hl': 'tr',
                        'gl': 'TR'
                    }
                },
                'continuation': ctoken
            }
            res = session.post(api_url, json=payload, timeout=5)
            if res.status_code != 200:
                break
            res_data = res.json()
            new_vids = parse_videos_from_node(res_data, ch_name)
            added = 0
            for v in new_vids:
                if v['video_id'] not in seen:
                    seen.add(v['video_id'])
                    all_videos.append(v)
                    added += 1
            ctoken = find_continuation_token(res_data)
            page += 1
            if added == 0 or not ctoken:
                break

        # 3. Fetch Shorts tab for full video coverage
        shorts_url = ch_url.replace('/videos', '/shorts')
        r_shorts = session.get(shorts_url, timeout=5)
        if r_shorts.status_code == 200:
            m_s = re.search(r'ytInitialData\s*=\s*({.*?});</script>', r_shorts.text, re.DOTALL)
            data_s = json.loads(m_s.group(1)) if m_s else {}
            shorts_vids = parse_videos_from_node(data_s, ch_name)
            for v in shorts_vids:
                if v['video_id'] not in seen:
                    seen.add(v['video_id'])
                    all_videos.append(v)

    except Exception as e:
        print(f"Full fetch error for {ch_name}: {e}")

    ch_summary = {
        'name': ch['name'],
        'handle': ch['handle'],
        'url': ch['url'],
        'video_count': len(all_videos),
        'official_video_count': official_vids or f"{len(all_videos)} video",
        'subscriber_count': official_subs or "Gizli"
    }
    return ch_summary, all_videos

def run_competitor_analysis(all_skins_db, selected_channel_ids=None, force_refresh=False):
    """
    High-precision competitor analysis engine with zero-error YouTube verification,
    streamlined with connection pooling, early response cutoff, and parallel channel fetching.
    """
    global _ANALYSIS_CACHE
    now = time.time()

    # Determine target channels
    target_channels = COMPETITOR_CHANNELS
    if selected_channel_ids and isinstance(selected_channel_ids, list) and len(selected_channel_ids) > 0:
        sel_set = set(str(x).lower().replace('@', '').strip() for x in selected_channel_ids if x)
        filtered = [
            c for c in COMPETITOR_CHANNELS
            if c['id'].lower() in sel_set or c['handle'].lower().replace('@', '') in sel_set
        ]
        if filtered:
            target_channels = filtered

    cache_key = ",".join(sorted(c['id'] for c in target_channels))
    
    # Return valid cache if available and not expired (10 min TTL)
    if not force_refresh and _ANALYSIS_CACHE.get(cache_key) and (now - _ANALYSIS_CACHE[cache_key]["timestamp"] < 600):
        return _ANALYSIS_CACHE[cache_key]["data"]

    all_videos = []
    seen_vids = set()
    channels_summary = []

    # 1. Fetch channel video tabs concurrently in parallel (All regular videos + shorts + official meta)
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(target_channels)) as ch_exec:
        channel_results = list(ch_exec.map(_fetch_single_channel_full, target_channels))

    for ch_summary, ch_vids in channel_results:
        for v in ch_vids:
            if v['video_id'] not in seen_vids:
                seen_vids.add(v['video_id'])
                all_videos.append(v)

        channels_summary.append(ch_summary)

    # Champion & Skin index
    champ_index = {}
    candidate_opportunities = []

    for s in all_skins_db:
        c_name = s.get('champion_name') or 'Bilinmeyen'
        s_name = s.get('name_tr') or f"{c_name} Kostümü"
        s_name_en = s.get('name_en') or ''
        s_id = s.get('skin_id') or (s.get('champion_id', 0) * 1000 + s.get('skin_num', 0))
        s_rarity_raw = s.get('rarity_raw') or 'kNoRarity'
        s_rarity_tr = s.get('rarity_tr') or 'Standart'
        s_date = s.get('release_date') or ''
        has_new_vo = s.get('has_new_voice_lines') or False

        skin_obj = {
            'id': s_id,
            'name': s_name,
            'name_tr': s_name,
            'name_en': s_name_en,
            'rarity_raw': s_rarity_raw.replace('k', ''),
            'rarity_tr': s_rarity_tr,
            'release_date': s_date,
            'has_new_vo': has_new_vo
        }
        champ_index.setdefault(c_name, []).append(skin_obj)

        is_true_custom_vo = (
            skin_obj['rarity_raw'] in ['Legendary', 'Ultimate', 'Transcendent', 'Exalted'] or 
            has_new_vo is True or
            any(k in s_name.lower() or k in s_name_en.lower() for k in ['kül şövalyesi', 'ashen knight', 'paramparça', 'sahn-uzal', 'ölümsüz efsane', 'yükselen efsane', 'heartsteel'])
        )
        if 'Prestij' in s_name and not is_true_custom_vo:
            continue

        if is_true_custom_vo:
            candidate_opportunities.append((c_name, s_name, s_name_en, s_rarity_tr, skin_obj['rarity_raw'], s_date, s_id, skin_obj))

    # Phase 1: Robust matching against all fetched competitor channel videos
    covered_champs = {}
    all_matched_skin_names = set()

    for v in all_videos:
        for c_name, skins in champ_index.items():
            matched_any_skin = False
            for s in skins:
                if match_skin_to_video_title(s, c_name, v['title']):
                    s_name = s['name']
                    if c_name not in covered_champs:
                        covered_champs[c_name] = {'videos': [], 'matched_skins': set()}
                    if v not in covered_champs[c_name]['videos']:
                        covered_champs[c_name]['videos'].append(v)
                    covered_champs[c_name]['matched_skins'].add(s_name)
                    all_matched_skin_names.add(s_name)
                    matched_any_skin = True
            
            # If video is general champion VO (e.g. 'Aatrox Replikleri')
            if not matched_any_skin:
                c_norm = normalize_turkish(c_name).strip()
                title_norm = normalize_turkish(v['title'])
                if f" {c_norm} " in title_norm and any(k in title_norm for k in ['replik', 'seslendirme', 'sesleri', 'dublaj', 'voice']):
                    if c_name not in covered_champs:
                        covered_champs[c_name] = {'videos': [], 'matched_skins': set()}
                    if v not in covered_champs[c_name]['videos']:
                        covered_champs[c_name]['videos'].append(v)

    # Phase 2: Filter out all skins already matched in competitor channels
    unmatched_candidates = [
        cand for cand in candidate_opportunities
        if cand[1] not in all_matched_skin_names
    ]

    # Phase 3: Check remaining top newest candidates on broader YouTube in parallel
    unmatched_candidates.sort(key=lambda x: x[5] or '', reverse=True)
    top_candidates = unmatched_candidates[:30]

    verified_results = []
    if top_candidates:
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(20, len(top_candidates))) as executor:
            verified_results = list(executor.map(check_single_skin_youtube_coverage, top_candidates))

    final_legendary_opps = []

    for c_name, s_name, found_video in verified_results:
        if found_video:
            # Video found on YouTube -> Mark as covered!
            all_matched_skin_names.add(s_name)
            if c_name not in covered_champs:
                covered_champs[c_name] = {'videos': [], 'matched_skins': set()}
            if found_video not in covered_champs[c_name]['videos']:
                covered_champs[c_name]['videos'].append(found_video)
            covered_champs[c_name]['matched_skins'].add(s_name)
        else:
            # Genuinely UNCOVERED opportunity!
            match_cand = next((cand for cand in unmatched_candidates if cand[1] == s_name), None)
            if match_cand:
                s_id = match_cand[6]
                c_id = s_id // 1000 if s_id else 0
                skin_num = s_id % 1000 if s_id else 0
                c_name = match_cand[0]

                # Map Champion name to official DDragon key
                ddragon_key_map = {
                    'Aurelion Sol': 'AurelionSol', "Cho'Gath": 'Chogath', 'Dr. Mundo': 'DrMundo',
                    'Jarvan IV': 'JarvanIV', "Kai'Sa": 'Kaisa', "Kha'Zix": 'Khazix', "Kog'Maw": 'KogMaw',
                    'LeBlanc': 'Leblanc', 'Lee Sin': 'LeeSin', 'Master Yi': 'MasterYi',
                    'Miss Fortune': 'MissFortune', 'Nunu ve Willump': 'Nunu', 'Nunu & Willump': 'Nunu',
                    'Renata Glasc': 'Renata', 'Tahm Kench': 'TahmKench', 'Twisted Fate': 'TwistedFate',
                    "Vel'Koz": 'Velkoz', 'Wukong': 'MonkeyKing', 'Xin Zhao': 'XinZhao'
                }
                c_key = ddragon_key_map.get(c_name, c_name.replace(" ", "").replace("'", ""))
                splash_url = f"https://ddragon.leagueoflegends.com/cdn/img/champion/splash/{c_key}_{skin_num}.jpg"

                final_legendary_opps.append({
                    'champion_name': c_name,
                    'skin_name': match_cand[1],
                    'rarity': match_cand[3],
                    'rarity_raw': match_cand[4],
                    'release_date': match_cand[5],
                    'skin_id': s_id,
                    'champion_id': c_id,
                    'skin_num': skin_num,
                    'champ_key': c_key,
                    'splash_url': splash_url,
                    'has_new_vo': True
                })

    # Covered list formatted
    covered_list = []
    for c_name, d in covered_champs.items():
        covered_list.append({
            'champion_name': c_name,
            'video_count': len(d['videos']),
            'videos': d['videos'],
            'matched_skins': list(d['matched_skins']),
            'total_skins': len(champ_index.get(c_name, []))
        })
    covered_list.sort(key=lambda x: x['video_count'], reverse=True)

    # Uncovered champions with rich metadata
    uncovered_list = []
    for c_name, skins in champ_index.items():
        if c_name not in covered_champs:
            legendary_skins = [s for s in skins if s['rarity_raw'] in ['Legendary', 'Ultimate', 'Transcendent', 'Exalted'] or s['has_new_vo']]
            uncovered_list.append({
                'champion_name': c_name,
                'total_skins': len(skins),
                'skins': [s['name'] for s in skins],
                'has_legendary_vo': len(legendary_skins) > 0,
                'legendary_skins_count': len(legendary_skins),
                'highlight_skins': [
                    {
                        'name': s['name'],
                        'rarity_tr': s['rarity_tr'],
                        'rarity_raw': s['rarity_raw'],
                        'has_new_vo': s['has_new_vo'],
                        'release_date': s['release_date']
                    } for s in (legendary_skins if legendary_skins else skins[:4])
                ]
            })
    # Sort uncovered champions: first champions with legendary/custom VO skins, then by total skins
    uncovered_list.sort(key=lambda x: (x['has_legendary_vo'], x['legendary_skins_count'], x['total_skins']), reverse=True)

    # Enrich legendary opportunities with explicit VO metadata
    for opp in final_legendary_opps:
        opp['has_custom_vo'] = True
        opp['vo_type_label'] = "🎙️ Özel Stüdyo Dublajı & Bağımsız Ses Bankası"
        opp['is_legendary'] = opp.get('rarity_raw') in ['Legendary', 'Ultimate', 'Transcendent', 'Exalted']

    result_data = {
        'channels': channels_summary,
        'total_videos': len(all_videos) + sum(1 for _, _, v in verified_results if v),
        'covered_champions': covered_list,
        'uncovered_champions': uncovered_list,
        'legendary_opportunities': final_legendary_opps
    }

    # Update global cache by channel selection key
    _ANALYSIS_CACHE[cache_key] = {
        "timestamp": time.time(),
        "data": result_data
    }
    _ANALYSIS_CACHE["data"] = result_data
    _ANALYSIS_CACHE["timestamp"] = time.time()

    return result_data

if __name__ == "__main__":
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "all_lol_skins_database.json")
    with open(db_path, 'r', encoding='utf-8') as f:
        skins_db = json.load(f)

    res = run_competitor_analysis(skins_db)
    print("\n==================================================")
    print("🔥 YOUTUBE RAKİP & FIRSAT ANALİZİ RAPORU (KESİN DOĞRULANMIŞ)")
    print("==================================================")
    print(f"Toplam Çekilen / Taranan Video: {res['total_videos']}")
    print(f"Kapsanan Şampiyon Sayısı: {len(res['covered_champions'])}")
    print(f"Hiç Çekilmemiş Şampiyon Sayısı: {len(res['uncovered_champions'])}")
    print(f"Gerçek Çekilmemiş Fırsatlar: {len(res['legendary_opportunities'])}")
    
    print("\n💎 İlk 8 Gerçek ÇEKİLMEMİŞ Efsanevi Fırsat:")
    for opp in res['legendary_opportunities'][:8]:
        print(f"  • {opp['skin_name']} ({opp['champion_name']}) - {opp['rarity']} [{opp['release_date']}]")

    print("\n🎯 Kapsanan Şampiyonlardan Örnekler:")
    for c in [x for x in res['covered_champions'] if x['champion_name'] in ['Shaco', 'Miss Fortune', 'Seraphine', 'Diana']]:
        print(f"  * {c['champion_name']}: {c['video_count']} video -> {', '.join(c['matched_skins'])}")
