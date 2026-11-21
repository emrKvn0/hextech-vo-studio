# -*- coding: utf-8 -*-
"""
🎙️ LoL Champion Voice & SFX Studio Extractor (JIT On-Demand)
HIRC & WAD tabanlı ultra hızlı şampiyon replik ve ses efekti çıkarıcı.
Her şampiyon ve kostüm için 11 standart kategoride sesleri çözer.
Dublaj durumunu (Eşsiz Yeni Replik vs Vokal Filtreli vs Standart) analiz eder
ve eylemleri kusursuz mantıksal sıraya ve açıklayıcı Türkçe isimlere göre dizer.
"""

import os
import sys
import re
import json
import struct
import zstandard as zstd

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(ROOT_DIR, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import importlib
import event_categorizer
import extract_target_references as ref_ext

WAD_DIR = r"C:\Riot Games\League of Legends\Game\DATA\FINAL\Champions"
CACHE_DIR = os.path.join(ROOT_DIR, "cache", "champion_voices")
os.makedirs(CACHE_DIR, exist_ok=True)
SKINS_DB_PATH = os.path.join(ROOT_DIR, "all_lol_skins_database.json")
VO_DB_PATH = os.path.join(ROOT_DIR, "champions_vo_database.json")
MASTER_TRANSCRIPTS_PATH = os.path.join(ROOT_DIR, "cache", "master_transcripts.json")

# Kategori başlıkları ve ikon/renk haritası (İzleyiciyi videoda tutan optimum YouTube akış sırasıyla: Atıflar -> Seçim -> Genel -> Şaka -> Eşyalar -> Q -> W -> E -> R Ulti -> Hareket -> Dönüş -> SFX En Sonda)
CATEGORY_ORDER = [
    "5_Ozel_Karsilasmalar_ve_Atiflar",
    "0_Secim_ve_Ozel_Sesler",
    "10_Genel_Replikler",
    "7_Saka_Kiskirtma_Kahkaha",
    "6_Esya_Alimi_ve_Magaza",
    "1_Q_Yetenegi",
    "2_W_Yetenegi",
    "3_E_Yetenegi",
    "4_R_Ulti",
    "9_Hareket_ve_Saldiri",
    "8_Donus_ve_Olum",
    "11_Efektler_ve_Homurtular"
]

CATEGORY_META = {
    "5_Ozel_Karsilasmalar_ve_Atiflar": {"title": "Özel Karşılaşmalar, Karakter Atıfları & Destansı Katletmeler", "icon": "Users", "color": "purple"},
    "0_Secim_ve_Ozel_Sesler": {"title": "Seçim, Yasaklama & Oyun Başlangıcı", "icon": "Sparkles", "color": "amber"},
    "10_Genel_Replikler": {"title": "Genel Hikâye Replikleri & Seviye Atlama", "icon": "MessageSquare", "color": "slate"},
    "7_Saka_Kiskirtma_Kahkaha": {"title": "Şaka, Kışkırtma, Dans & Kahkaha", "icon": "Smile", "color": "yellow"},
    "6_Esya_Alimi_ve_Magaza": {"title": "Eşya & Mağaza Alımı", "icon": "ShoppingBag", "color": "emerald"},
    "4_R_Ulti": {"title": "R Yeteneği (Ulti)", "icon": "Crown", "color": "rose"},
    "1_Q_Yetenegi": {"title": "Q Yeteneği", "icon": "Zap", "color": "cyan"},
    "2_W_Yetenegi": {"title": "W Yeteneği", "icon": "Shield", "color": "blue"},
    "3_E_Yetenegi": {"title": "E Yeteneği", "icon": "Flame", "color": "indigo"},
    "9_Hareket_ve_Saldiri": {"title": "Hareket & Normal Saldırı", "icon": "Compass", "color": "teal"},
    "8_Donus_ve_Olum": {"title": "Recall, Doğuş & Ölüm", "icon": "Skull", "color": "red"},
    "11_Efektler_ve_Homurtular": {"title": "Ses Efektleri, Efor & Homurtular", "icon": "Activity", "color": "orange"}
}

_skins_cache = None
_vo_db_cache = None
_master_transcripts_cache = None

def get_all_skins_data():
    global _skins_cache
    if _skins_cache is not None:
        return _skins_cache
    if os.path.exists(SKINS_DB_PATH):
        try:
            with open(SKINS_DB_PATH, 'r', encoding='utf-8') as f:
                _skins_cache = json.load(f)
                return _skins_cache
        except Exception:
            pass
    _skins_cache = []
    return _skins_cache

def get_vo_db():
    global _vo_db_cache
    if _vo_db_cache is not None:
        return _vo_db_cache
    if os.path.exists(VO_DB_PATH):
        try:
            with open(VO_DB_PATH, 'r', encoding='utf-8') as f:
                _vo_db_cache = json.load(f)
                return _vo_db_cache
        except Exception:
            pass
    _vo_db_cache = {}
    return _vo_db_cache

_master_transcripts_mtime = 0

def get_master_transcripts(force_reload=False):
    global _master_transcripts_cache, _master_transcripts_mtime
    if not os.path.exists(MASTER_TRANSCRIPTS_PATH):
        _master_transcripts_cache = {}
        return _master_transcripts_cache
    
    try:
        current_mtime = os.path.getmtime(MASTER_TRANSCRIPTS_PATH)
        if force_reload or _master_transcripts_cache is None or current_mtime != _master_transcripts_mtime:
            with open(MASTER_TRANSCRIPTS_PATH, 'r', encoding='utf-8') as f:
                _master_transcripts_cache = json.load(f)
                _master_transcripts_mtime = current_mtime
            return _master_transcripts_cache
    except Exception:
        pass

    if _master_transcripts_cache is not None:
        return _master_transcripts_cache
    _master_transcripts_cache = {}
    return _master_transcripts_cache

def get_champion_skins_list(champ_name):
    """
    Belirli bir şampiyonun tüm kostümlerini listeler ve
    hangi kostümün EŞSİZ YENİ DUBLAJLI, hangisinin VOKAL FİLTRELİ,
    hangisinin STANDART olduğunu kristal netliğinde etiketler.
    """
    all_skins = get_all_skins_data()
    vo_db = get_vo_db()
    champ_clean = champ_name.lower().replace(" ", "").replace("'", "")
    
    champ_skins = []
    seen_nums = set()
    for s in all_skins:
        c_name = (s.get('champion_name') or s.get('champion_alias') or '').lower().replace(" ", "").replace("'", "")
        if c_name == champ_clean:
            s_num = s.get('skin_num', 0)
            if s_num not in seen_nums:
                seen_nums.add(s_num)
                is_base = s.get('is_base', s_num == 0)
                name_tr = s.get('name_tr') or f"{champ_name} (Kostüm {s_num})"
                rarity_tr = s.get('rarity_tr', 'Varsayılan' if s_num == 0 else 'Standart')
                rarity_raw = s.get('rarity_raw', '')

                # VO Veritabanı Eşleştirme
                clean_name = name_tr.lower().replace("_", "").replace(" ", "")
                vo_info = (
                    vo_db.get(f"{champ_clean}_{s_num}") or
                    vo_db.get(f"{champ_clean}_skin{s_num:02d}") or
                    vo_db.get(f"{champ_clean}_skin{s_num}") or
                    vo_db.get(clean_name)
                )

                if is_base or s_num == 0:
                    voice_type = "base"
                    voice_badge = "🛡️ VARSAYILAN DUBLAJ"
                    voice_tag = "Ana Şampiyon Sesi"
                    voice_desc = "Şampiyonun orijinal varsayılan Türkçe seslendirmesi."
                    is_unique = False
                elif vo_info:
                    raw_type = vo_info.get('voice_type', 'unique')
                    if raw_type == 'unique' or vo_info.get('is_recommended') or rarity_raw in ('kLegendary', 'kUltimate', 'kTranscendent') or 'Efsanevi' in rarity_tr or 'Ebedi' in rarity_tr:
                        voice_type = "unique"
                        voice_badge = "👑 EŞSİZ YENİ DUBLAJ"
                        voice_tag = "Eşsiz Yeni Replikler 🔥"
                        voice_desc = "Tamamen sıfırdan kaydedilmiş bağımsız yeni replikler ve özel atıflar barındırır. Video potansiyeli çok yüksektir!"
                        is_unique = True
                    elif raw_type == 'filtered':
                        voice_type = "filtered"
                        voice_badge = "🎛️ AYNI REPLİK (Ses Efektli)"
                        voice_tag = "Aynı Replik + Vokal Filtre"
                        voice_desc = "Temel Türkçe seslendirme üzerine kostüme özel robotik/vokal filtre uygulanmıştır. Replik sözleri temel ile aynıdır."
                        is_unique = False
                    elif raw_type == 'partial':
                        voice_type = "partial"
                        voice_badge = "⚡ KISMİ DUBLAJ"
                        voice_tag = "Kısmi Replikler"
                        voice_desc = "Yalnızca birkaç ek replik veya efor barındırır."
                        is_unique = False
                    else:
                        voice_type = raw_type
                        voice_badge = "🎙️ ÖZEL DUBLAJ"
                        voice_tag = "Özel Ses"
                        voice_desc = "Kostüme özel ses bankası."
                        is_unique = True
                else:
                    # Rarity'ye göre kontrol
                    if rarity_raw in ('kLegendary', 'kUltimate', 'kTranscendent') or 'Efsanevi' in rarity_tr or 'Ebedi' in rarity_tr:
                        voice_type = "unique"
                        voice_badge = "👑 EŞSİZ YENİ DUBLAJ"
                        voice_tag = "Eşsiz Yeni Replikler 🔥"
                        voice_desc = "Efsanevi/Ebedi seviye: Sıfırdan kaydedilmiş yeni replikler barındırır. Video potansiyeli yüksektir!"
                        is_unique = True
                    else:
                        voice_type = "none"
                        voice_badge = "❌ ÖZEL DUBLAJ YOK"
                        voice_tag = "Temel Ses"
                        voice_desc = "Ayrı bir ses bankası yoktur; şampiyonun standart temel repliklerini kullanır."
                        is_unique = False

                champ_skins.append({
                    "skin_num": s_num,
                    "name": name_tr,
                    "is_base": is_base,
                    "splash_url": s.get('splash_url', ''),
                    "rarity_tr": rarity_tr,
                    "rarity_raw": rarity_raw,
                    "voice_type": voice_type,
                    "voice_badge": voice_badge,
                    "voice_tag": voice_tag,
                    "voice_desc": voice_desc,
                    "is_unique": is_unique
                })
    
    # Her zaman en azından Varsayılan kostümü garanti et
    if not any(s['skin_num'] == 0 for s in champ_skins):
        champ_skins.insert(0, {
            "skin_num": 0,
            "name": f"Varsayılan {champ_name}",
            "is_base": True,
            "splash_url": f"https://ddragon.leagueoflegends.com/cdn/img/champion/splash/{champ_name}_0.jpg",
            "rarity_tr": "Varsayılan",
            "rarity_raw": "kBase",
            "voice_type": "base",
            "voice_badge": "🛡️ VARSAYILAN DUBLAJ",
            "voice_tag": "Ana Şampiyon Sesi",
            "voice_desc": "Şampiyonun orijinal varsayılan Türkçe seslendirmesi.",
            "is_unique": False
        })
    champ_skins.sort(key=lambda x: x['skin_num'])
    return champ_skins

def _resolve_target_skin_meta(t_champ, t_snum):
    if not t_champ:
        return "", ""
    tc_clean = t_champ.lower().replace(" ", "").replace("'", "")
    all_skins_db = get_all_skins_data()
    for s in all_skins_db:
        cn = (s.get('champion_name') or s.get('champion_alias') or '').lower().replace(" ", "").replace("'", "")
        if cn == tc_clean and s.get('skin_num', 0) == t_snum:
            return (s.get('name_tr') or f"Varsayılan {t_champ}"), (s.get('splash_url') or f"https://ddragon.leagueoflegends.com/cdn/img/champion/splash/{t_champ}_{t_snum}.jpg")
    return (f"Varsayılan {t_champ}" if t_snum == 0 else f"{t_champ} (Kostüm {t_snum})"), f"https://ddragon.leagueoflegends.com/cdn/img/champion/splash/{t_champ}_{t_snum}.jpg"


def enrich_categories_with_transcripts(categories, champ_name):
    """
    Kategoriler içindeki WEM repliklerini master_transcripts.json ile
    deterministik ve anında eşleştirip doldurur; ayrıca eylem adlarını, hedef şampiyonları,
    kategori gruplarını (cat_id) ve sıralama ağırlıklarını güncel event_categorizer kurallarıyla
    sıfırdan yeniden gruplayarak tazeler (eski cache sızıntılarını anında temizler).
    """
    try:
        importlib.reload(event_categorizer)
    except Exception:
        pass
    master_trans = get_master_transcripts() or {}
    regrouped = {}

    for cat in categories:
        old_cid = cat.get('id', '')
        for item in cat.get('items', []):
            ev = item.get('raw_event', '')
            new_cid = old_cid
            if ev:
                parsed_cid, fresh_action = event_categorizer.parse_event_info(ev, champ_name)
                if parsed_cid:
                    new_cid = parsed_cid
                t_champ, t_snum = event_categorizer.parse_event_target(ev, champ_name)
                t_sname, t_splash = _resolve_target_skin_meta(t_champ, t_snum)
                item['target_champ'] = t_champ or ""
                item['target_skin_num'] = t_snum if t_champ else 0
                item['target_skin_name'] = t_sname if t_champ else ""
                item['target_splash_url'] = t_splash if t_champ else ""

                if t_champ and t_snum > 0 and f"(Kostüm {t_snum})" in fresh_action and t_sname:
                    fresh_action = fresh_action.replace(f"{t_champ} (Kostüm {t_snum})", t_sname)
                if fresh_action:
                    item['action_name'] = fresh_action
                item['sort_weight'] = event_categorizer.get_event_sort_weight(new_cid, item.get('action_name', ''), ev, champ_name)

            wems = item.get('wems', [])
            is_single = len(wems) == 1
            for w in wems:
                wid = str(w.get('wem_id', ''))
                t = ""
                if wid and master_trans:
                    t = (master_trans.get(wid) or
                         master_trans.get(f"{champ_name}_{ev}_{wid}") or
                         master_trans.get(f"{ev}_{wid}".lower()))
                    if not t:
                        ev_alt = ev.replace('20', '2D') if '20' in ev else ev.replace('2D', '20')
                        t = (master_trans.get(f"{champ_name}_{ev_alt}_{wid}") or
                             master_trans.get(f"{ev_alt}_{wid}".lower()))
                if not t and is_single and master_trans:
                    t = (master_trans.get(ev) or
                         master_trans.get(ev.lower()) or
                         master_trans.get(f"{champ_name}_{ev}"))
                if t:
                    w['transcript'] = t

            regrouped.setdefault(new_cid, []).append(item)

    fresh_categories = []
    for cat_key in CATEGORY_ORDER:
        if cat_key in regrouped and regrouped[cat_key]:
            meta = CATEGORY_META.get(cat_key, {"title": cat_key, "icon": "🔊", "color": "#c89b3c"})
            items = regrouped[cat_key]
            items.sort(key=lambda it: (
                0 if it.get('target_champ') else 1,
                it.get('target_champ', ''),
                it.get('sort_weight', 999),
                it.get('action_name', '')
            ))
            fresh_categories.append({
                "id": cat_key,
                "title": meta["title"],
                "icon": meta["icon"],
                "color": meta["color"],
                "count": len(items),
                "total_wems": sum(len(it.get("wems", [])) for it in items),
                "items": items
            })
    return fresh_categories

def extract_champion_voices(champ_name, skin_num=0, include_sfx=True):
    """
    Belirli bir şampiyonun ve seçilen kostüm numarasının tüm repliklerini
    ve ses efektlerini HIRC ağacından deterministik olarak çözer.
    Eylemleri açıklayıcı Türkçe adlara dönüştürür ve mantıksal sırada dizer.
    """
    skin_num = int(skin_num)
    cache_file = os.path.join(CACHE_DIR, f"{champ_name}_{skin_num}.json")
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)
                if cached_data.get('schema_version') == 4:
                    # Cache'deki veriyi her zaman master_transcripts ve güncel eşya/sıralama motoru ile zenginleştir
                    cached_data['categories'] = enrich_categories_with_transcripts(cached_data.get('categories', []), champ_name)
                    if not include_sfx:
                        cached_data = dict(cached_data)
                        cached_data['categories'] = [c for c in cached_data.get('categories', []) if c['id'] != '11_Efektler_ve_Homurtular']
                    return cached_data
        except Exception:
            pass

    tr_wad = os.path.join(WAD_DIR, f"{champ_name}.tr_TR.wad.client")
    base_wad = os.path.join(WAD_DIR, f"{champ_name}.wad.client")
    
    if not os.path.exists(tr_wad) and not os.path.exists(base_wad):
        return None

    dctx = zstd.ZstdDecompressor()
    events = set()
    bnks = []
    wpk_wems = set()

    def _extract_clean_events_from_blob(data):
        is_prop = len(data) >= 4 and data[:4] == b'PROP'
        for m in re.finditer(rb'(?:Play_vo_|vo_)[a-zA-Z0-9_]+', data):
            s_pos = m.start()
            s = m.group(0).decode('ascii', errors='ignore')
            if is_prop and s_pos >= 2:
                slen = struct.unpack('<H', data[s_pos-2:s_pos])[0]
                if 5 <= slen <= len(s):
                    s = s[:slen]
            events.add(s)

    # 1. Base WAD'dan sadece PROP oku (event isimleri için)
    if os.path.exists(base_wad):
        try:
            with open(base_wad, 'rb') as f:
                f.seek(268)
                fc_bytes = f.read(4)
                if len(fc_bytes) == 4:
                    fc = struct.unpack('<I', fc_bytes)[0]
                    entries = f.read(fc * 32)
                    for i in range(fc):
                        eb = entries[i*32:(i+1)*32]
                        phash, doff, csz, usz, tflags = struct.unpack('<QIII4s', eb[:24])
                        if csz <= 0 or usz > 1200000: continue
                        f.seek(doff)
                        raw = f.read(csz)
                        try:
                            data = dctx.decompress(raw, max_output_size=usz) if (tflags[0]&0xF)==3 else raw
                            if len(data) >= 4 and (data[:4] == b'PROP' or data[:4] == b'BKHD'):
                                _extract_clean_events_from_blob(data)
                        except Exception:
                            pass
        except Exception:
            pass

    # 2. Audio WAD'dan ses bankalarını ve WPK seslerini oku
    if os.path.exists(tr_wad):
        try:
            with open(tr_wad, 'rb') as f:
                f.seek(268)
                fc_bytes = f.read(4)
                if len(fc_bytes) == 4:
                    fc = struct.unpack('<I', fc_bytes)[0]
                    entries = f.read(fc * 32)
                    for i in range(fc):
                        eb = entries[i*32:(i+1)*32]
                        phash, doff, csz, usz, tflags = struct.unpack('<QIII4s', eb[:24])
                        if csz <= 0: continue
                        f.seek(doff)
                        raw = f.read(csz)
                        try:
                            data = dctx.decompress(raw, max_output_size=usz) if (tflags[0]&0xF)==3 else raw
                            if len(data) >= 4 and data[:4] == b'BKHD':
                                bnks.append(data)
                                _extract_clean_events_from_blob(data)
                            elif len(data) >= 12 and data[:4] == b'r3d2':
                                w_dict = ref_ext.extract_wpk_wems(data)
                                wpk_wems.update(w_dict.keys())
                        except Exception:
                            pass
        except Exception:
            pass

    # Eventleri kostüm numarasına göre filtrele
    filtered_events = set()
    champ_esc = re.escape(champ_name)
    for ev in events:
        m_skin = re.search(champ_esc + r'Skin0*([0-9]{1,2})', ev, re.IGNORECASE)
        if not m_skin:
            # Eğer kendi adından hemen sonra değilse ama sadece tek SkinXX varsa ve başka şampiyon yoksa
            t_ch, _ = event_categorizer.parse_event_target(ev, champ_name)
            if not t_ch:
                m_skin = re.search(r'Skin0*([0-9]{1,2})', ev, re.IGNORECASE)
        ev_skin_num = int(m_skin.group(1)) if m_skin else 0
        if skin_num == 0:
            if ev_skin_num == 0:
                filtered_events.add(ev)
        else:
            if ev_skin_num == skin_num:
                filtered_events.add(ev)

    # Eğer seçilen kostüm için özel ses bulunamadıysa (kostüm temel sesi kullanıyorsa)
    if not filtered_events and skin_num != 0:
        for ev in events:
            m_skin = re.search(champ_esc + r'Skin0*([0-9]{1,2})', ev, re.IGNORECASE)
            if not m_skin:
                filtered_events.add(ev)

    # HIRC çözümlemesi
    target_map = {}
    for ev in filtered_events:
        target_map[ref_ext.fnv_1(ev)] = ev
        clean_ev = re.sub(r'(K|k)$', '', ev)
        if clean_ev != ev:
            target_map[ref_ext.fnv_1(clean_ev)] = ev

    event_to_wems = {}
    for b in bnks:
        w2e = ref_ext.parse_hirc_soundbank(b, target_map)
        for w, ev_name in w2e.items():
            if ev_name not in event_to_wems:
                event_to_wems[ev_name] = []
            if w not in event_to_wems[ev_name]:
                event_to_wems[ev_name].append(w)

    master_trans = get_master_transcripts()
    skins_list = get_champion_skins_list(champ_name)
    current_skin = next((s for s in skins_list if s['skin_num'] == skin_num), skins_list[0])
    all_skins_db = get_all_skins_data()

    def _resolve_target_skin_meta(t_champ, t_snum):
        if not t_champ:
            return "", ""
        tc_clean = t_champ.lower().replace(" ", "").replace("'", "")
        for s in all_skins_db:
            cn = (s.get('champion_name') or s.get('champion_alias') or '').lower().replace(" ", "").replace("'", "")
            if cn == tc_clean and s.get('skin_num', 0) == t_snum:
                return (s.get('name_tr') or f"Varsayılan {t_champ}"), (s.get('splash_url') or f"https://ddragon.leagueoflegends.com/cdn/img/champion/splash/{t_champ}_{t_snum}.jpg")
        return (f"Varsayılan {t_champ}" if t_snum == 0 else f"{t_champ} (Kostüm {t_snum})"), f"https://ddragon.leagueoflegends.com/cdn/img/champion/splash/{t_champ}_{t_snum}.jpg"

    categorized = {}
    total_wems_count = 0

    for ev in sorted(filtered_events):
        cat_id, action_clean = event_categorizer.parse_event_info(ev, champ_name)
        target_champ, target_skin_num = event_categorizer.parse_event_target(ev, champ_name)
        target_skin_name, target_splash_url = _resolve_target_skin_meta(target_champ, target_skin_num)

        if target_champ and target_skin_num > 0 and f"(Kostüm {target_skin_num})" in action_clean and target_skin_name:
            action_clean = action_clean.replace(f"{target_champ} (Kostüm {target_skin_num})", target_skin_name)

        sort_weight = event_categorizer.get_event_sort_weight(cat_id, action_clean, ev, champ_name)
        
        # 2D/3D tekilleştirme: Eğer 3D varsa 2D'yi atla
        if '2d' in ev.lower():
            ev_3d = re.sub(r'2d', '3D', ev, flags=re.IGNORECASE)
            if ev_3d in filtered_events:
                continue

        wems = event_to_wems.get(ev, [])
        if not wems:
            clean_ev = re.sub(r'(K|k)$', '', ev)
            wems = event_to_wems.get(clean_ev, [])

        valid_wems = [w for w in wems if w in wpk_wems] if wpk_wems and wems else [w for w in wems if w]
        if not valid_wems:
            # Ses bankasında (BNK/WPK) gerçek karşılığı olmayan kukla/hayalet eventleri atla (404 önleme)
            continue

        is_sfx = (cat_id == "11_Efektler_ve_Homurtular") or any(k in ev.lower() for k in ['effort', 'grunt', 'cast_effort', 'hit_vo', 'exertion'])
        
        wem_items = []
        for idx, wid in enumerate(valid_wems):
            transcript = ""
            if wid:
                transcript = master_trans.get(str(wid), "")
                if not transcript:
                    transcript = master_trans.get(f"{champ_name}_{ev}_{wid}", "")
                if not transcript:
                    transcript = master_trans.get(f"{ev}_{wid}".lower(), "")
            if not transcript and len(valid_wems) == 1:
                transcript = master_trans.get(ev.lower(), "")

            wem_items.append({
                "wem_id": wid,
                "variation_index": idx + 1,
                "variation_total": len(valid_wems),
                "transcript": transcript
            })
            if wid:
                total_wems_count += 1

        item = {
            "raw_event": ev,
            "action_name": action_clean,
            "sort_weight": sort_weight,
            "is_sfx": is_sfx,
            "target_champ": target_champ or "",
            "target_skin_num": target_skin_num if target_champ else 0,
            "target_skin_name": target_skin_name if target_champ else "",
            "target_splash_url": target_splash_url if target_champ else "",
            "wems": wem_items
        }

        categorized.setdefault(cat_id, []).append(item)

    # Her kategori altındaki itemleri sort_weight ve hedef şampiyona göre mükemmel sırada diz
    # (Önce Karakter Atıfları hedef şampiyona göre gruplu -> İlk Kan -> Penta -> Baron -> Ejder -> Seçim -> Genel -> Eşyalar -> Yetenekler -> Hareket -> Ölüm & Homurtular)
    result_categories = []
    for cat_key in CATEGORY_ORDER:
        if cat_key in categorized:
            meta = CATEGORY_META[cat_key]
            items = categorized[cat_key]
            # Önce karakter atıfları (aynı hedef şampiyona söylenenler peş peşe blok), sonra sort_weight
            items.sort(key=lambda it: (
                0 if it.get('target_champ') else 1,
                it.get('target_champ', ''),
                it.get('sort_weight', 999),
                it.get('action_name', '')
            ))
            
            result_categories.append({
                "id": cat_key,
                "title": meta["title"],
                "icon": meta["icon"],
                "color": meta["color"],
                "count": len(items),
                "total_wems": sum(len(it["wems"]) for it in items),
                "items": items
            })

    output_payload = {
        "schema_version": 4,
        "champion": champ_name,
        "skin_num": skin_num,
        "skin_name": current_skin["name"],
        "splash_url": current_skin["splash_url"],
        "voice_type": current_skin.get("voice_type", "base"),
        "voice_badge": current_skin.get("voice_badge", "🛡️ VARSAYILAN DUBLAJ"),
        "voice_tag": current_skin.get("voice_tag", "Ana Şampiyon Sesi"),
        "voice_desc": current_skin.get("voice_desc", ""),
        "is_unique": current_skin.get("is_unique", False),
        "total_events": len(filtered_events),
        "total_wems": total_wems_count,
        "skins": skins_list,
        "categories": result_categories
    }

    # Önbelleğe yaz
    try:
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(output_payload, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    if not include_sfx:
        output_payload = dict(output_payload)
        output_payload['categories'] = [c for c in output_payload['categories'] if c['id'] != '11_Efektler_ve_Homurtular']

    return output_payload

if __name__ == '__main__':
    # Hızlı test
    res = extract_champion_voices('Yasuo', 0)
    print(f"Yasuo: {res['total_events']} event, {res['total_wems']} ses, {len(res['categories'])} kategori.")
    for c in res['categories']:
        print(f" - {c['title']}: {c['count']} event")
        for it in c['items'][:3]:
            print(f"     • [{it.get('sort_weight')}] {it['action_name']}")
