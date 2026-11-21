# -*- coding: utf-8 -*-
"""
🎭 LoL Pair Interactions & Multi-Turn Conversational Dialogue Extractor
Riot WAD/WPK gömülü RIFF/cue işaretleyicileri ve BNK HIRC ses ağacını birleştirerek
iki şampiyon arasındaki:
  1. Karşılıklı Sıralı Diyalog Zincirlerini (Chat1 ➔ Chat2 ➔ Chat3 ➔ Chat4 & Taunt ➔ Response)
  2. İlk Karşılaşmaları (First Encounter - Kostüm kırılımlı: Star Guardian, Redeemed, Battle Academia vb.)
  3. Katletmeleri (Kills - A ➔ B ve B ➔ A)
  4. Kışkırtma & Şakaları (Taunts & Jokes)
  5. Diğer Oyun İçi Etkileşimleri (Kalkan, İyileştirme, Sinyal/Ping, Recall, Dans, Yetenek)
%100 deterministik olarak çözer ve Türkçe metinleriyle birlikte sunar.
"""

import os
import sys
import re
import json
import struct
import xxhash
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

import extract_target_references as ref_ext

WAD_DIR = r"C:\Riot Games\League of Legends\Game\DATA\FINAL\Champions"
PAIR_CACHE_DIR = os.path.join(ROOT_DIR, "cache", "pair_interactions")
os.makedirs(PAIR_CACHE_DIR, exist_ok=True)

SKINS_DB_PATH = os.path.join(ROOT_DIR, "all_lol_skins_database.json")
MASTER_TRANSCRIPTS_PATH = os.path.join(ROOT_DIR, "cache", "master_transcripts.json")
MATRIX_DATA_PATH = os.path.join(ROOT_DIR, "lol-matrix-web", "public", "data", "lol_matrix_data.json")

SCHEMA_VERSION = 2

_skins_db_cache = None
_transcripts_cache = None

def get_skins_db():
    global _skins_db_cache
    if _skins_db_cache is not None:
        return _skins_db_cache
    if os.path.exists(SKINS_DB_PATH):
        try:
            with open(SKINS_DB_PATH, 'r', encoding='utf-8') as f:
                _skins_db_cache = json.load(f)
                return _skins_db_cache
        except Exception:
            pass
    _skins_db_cache = []
    return _skins_db_cache

def get_transcripts():
    global _transcripts_cache
    if _transcripts_cache is not None:
        return _transcripts_cache
    if os.path.exists(MASTER_TRANSCRIPTS_PATH):
        try:
            with open(MASTER_TRANSCRIPTS_PATH, 'r', encoding='utf-8') as f:
                _transcripts_cache = json.load(f)
                return _transcripts_cache
        except Exception:
            pass
    _transcripts_cache = {}
    return _transcripts_cache

def resolve_skin_meta(champ_name, skin_num=0):
    """Şampiyon ve kostüm numarasından Türkçe kostüm adını ve splash URL'sini döner."""
    skin_num = int(skin_num or 0)
    skins = get_skins_db()
    c_clean = champ_name.lower().replace(" ", "").replace("'", "")
    for s in skins:
        cn = (s.get('champion_name') or s.get('champion_alias') or '').lower().replace(" ", "").replace("'", "")
        if cn == c_clean and int(s.get('skin_num', 0)) == skin_num:
            name_tr = s.get('name_tr') or (f"Varsayılan {champ_name}" if skin_num == 0 else f"{champ_name} (Kostüm {skin_num})")
            splash = s.get('splash_url') or f"https://ddragon.leagueoflegends.com/cdn/img/champion/splash/{champ_name}_{skin_num}.jpg"
            return {
                "skin_num": skin_num,
                "skin_name": name_tr,
                "is_base": skin_num == 0,
                "splash_url": splash
            }
    return {
        "skin_num": skin_num,
        "skin_name": f"Varsayılan {champ_name}" if skin_num == 0 else f"{champ_name} (Kostüm {skin_num})",
        "is_base": skin_num == 0,
        "splash_url": f"https://ddragon.leagueoflegends.com/cdn/img/champion/splash/{champ_name}_{skin_num}.jpg"
    }

def lookup_transcript(speaker, raw_event, wem_id):
    """Önbellekten repliğin Türkçe metnini bulur."""
    trans = get_transcripts()
    wid_str = str(wem_id).strip() if wem_id else ""
    if wid_str:
        if wid_str in trans and trans[wid_str]:
            return trans[wid_str]
        k1 = f"{speaker}_{raw_event}_{wid_str}"
        if k1 in trans and trans[k1]:
            return trans[k1]
        k2 = f"{raw_event}_{wid_str}".lower()
        if k2 in trans and trans[k2]:
            return trans[k2]
        k3 = f"{speaker}_{wid_str}.wav"
        if k3 in trans and trans[k3]:
            return trans[k3]
    return ""

def build_wad_skin_hash_map(champ_name):
    """WAD içindeki xxhash64 dosya yollarından kostüm numarasını (0..99) eşler."""
    ch_low = champ_name.lower()
    hash_to_skin = {}
    for s in range(0, 100):
        stag = "base" if s == 0 else f"skin{s:02d}"
        for loc in ["tr_tr", "en_us"]:
            for ext in ["audio.wpk", "audio.bnk", "events.bnk"]:
                p1 = f"assets/sounds/wwise2016/vo/{loc}/characters/{ch_low}/skins/{stag}/{ch_low}_{stag}_vo_{ext}"
                hash_to_skin[xxhash.xxh64(p1.encode('ascii')).intdigest()] = s
    return hash_to_skin

def extract_champion_raw_data(champ_name):
    """
    Bir şampiyonun Base WAD (PROP) ve TR WAD (BNK + WPK) dosyalarını tarayarak:
    - PROP ve BNK içindeki tüm temizlenmiş VO event isimlerini
    - BNK HIRC tablosu üzerinden event -> [wem_id] eşleşmelerini
    - WPK içindeki her .wem dosyasının ait olduğu kostüm numarasını ve ilk 1024 baytındaki gömülü marker'ları
    çıkarır.
    """
    base_wad = os.path.join(WAD_DIR, f"{champ_name}.wad.client")
    tr_wad = os.path.join(WAD_DIR, f"{champ_name}.tr_TR.wad.client")
    dctx = zstd.ZstdDecompressor()

    events = set()
    bnks = []  # (skin_num, data)
    wpks = []  # (skin_num, {wem_id: wem_bytes})
    hash_to_skin = build_wad_skin_hash_map(champ_name)

    def _scan_events(blob):
        is_prop = len(blob) >= 4 and blob[:4] == b'PROP'
        for m in re.finditer(rb'(?:Play_vo_|vo_)[a-zA-Z0-9_]+', blob):
            s_pos = m.start()
            s = m.group(0).decode('ascii', errors='ignore')
            if is_prop and s_pos >= 2:
                slen = struct.unpack('<H', blob[s_pos-2:s_pos])[0]
                if 5 <= slen <= len(s):
                    s = s[:slen]
            events.add(s)

    if os.path.exists(base_wad):
        try:
            with open(base_wad, 'rb') as f:
                f.seek(268)
                fc_b = f.read(4)
                if len(fc_b) == 4:
                    fc = struct.unpack('<I', fc_b)[0]
                    entries = f.read(fc * 32)
                    for i in range(fc):
                        phash, doff, csz, usz, tflags = struct.unpack('<QIII4s', entries[i*32:(i+1)*32][:24])
                        if csz <= 0 or usz > 2000000:
                            continue
                        f.seek(doff)
                        raw = f.read(csz)
                        try:
                            data = dctx.decompress(raw, max_output_size=usz) if (tflags[0] & 0xF) == 3 else raw
                            if len(data) >= 4 and data[:4] in (b'PROP', b'BKHD'):
                                _scan_events(data)
                        except Exception:
                            pass
        except Exception:
            pass

    if os.path.exists(tr_wad):
        try:
            with open(tr_wad, 'rb') as f:
                f.seek(268)
                fc_b = f.read(4)
                if len(fc_b) == 4:
                    fc = struct.unpack('<I', fc_b)[0]
                    entries = f.read(fc * 32)
                    for i in range(fc):
                        phash, doff, csz, usz, tflags = struct.unpack('<QIII4s', entries[i*32:(i+1)*32][:24])
                        if csz <= 0:
                            continue
                        f.seek(doff)
                        raw = f.read(csz)
                        try:
                            data = dctx.decompress(raw, max_output_size=usz) if (tflags[0] & 0xF) == 3 else raw
                            s_num = hash_to_skin.get(phash, 0)
                            if len(data) >= 4 and data[:4] == b'BKHD':
                                bnks.append((s_num, data))
                                _scan_events(data)
                            elif len(data) >= 12 and data[:4] == b'r3d2':
                                w_dict = ref_ext.extract_wpk_wems(data)
                                wpks.append((s_num, w_dict))
                        except Exception:
                            pass
        except Exception:
            pass

    # Base WPK içindeki WEM ID'lerini kaydet ki kostüm WPK'larında ortak temel sesleri ayıklayabilelim
    base_wem_ids = set()
    all_wpk_wems = set()
    wem_to_skin = {}
    embedded_markers = {}  # (skin_num, wem_id) -> marker_str

    for s_num, w_dict in wpks:
        all_wpk_wems.update(w_dict.keys())
        if s_num == 0:
            base_wem_ids.update(w_dict.keys())

    for s_num, w_dict in wpks:
        for wid, wbytes in w_dict.items():
            if s_num != 0 and wid in base_wem_ids:
                continue
            wem_to_skin[wid] = s_num
            head = wbytes[:1024]
            for m in re.finditer(rb'[A-Za-z0-9_]{12,90}', head):
                ms = m.group(0).decode('ascii', errors='ignore')
                if any(k in ms.lower() for k in ['chat', 'near', 'with', 'taunt', 'joke', 'firstencounter', 'kill', 'move', 'recall']):
                    embedded_markers[(s_num, wid)] = ms
                    break

    # HIRC çözümlemesi
    target_map = {}
    for ev in events:
        target_map[ref_ext.fnv_1(ev)] = ev
        clean_ev = re.sub(r'(K|k)$', '', ev)
        if clean_ev != ev:
            target_map[ref_ext.fnv_1(clean_ev)] = ev

    event_to_wems = {}
    for s_num, b_data in bnks:
        w2e = ref_ext.parse_hirc_soundbank(b_data, target_map)
        for wid, ev_name in w2e.items():
            if all_wpk_wems and wid not in all_wpk_wems:
                continue
            event_to_wems.setdefault(ev_name, [])
            if wid not in event_to_wems[ev_name]:
                event_to_wems[ev_name].append(wid)

    return {
        "champion": champ_name,
        "events": events,
        "event_to_wems": event_to_wems,
        "all_wpk_wems": all_wpk_wems,
        "base_wem_ids": base_wem_ids,
        "wem_to_skin": wem_to_skin,
        "embedded_markers": embedded_markers
    }

def parse_skin_from_event_or_marker(text, speaker_champ, other_champ):
    """
    Event veya WEM gömülü marker içinden konuşan kostüm numarasını ve hedef kostüm numarasını çözer.
    Örn: Play_vo_RakanSkin05_XayahSkin04FirstEncounter -> (5, 4)
    """
    spk_skin = 0
    tgt_skin = 0
    m_spk = re.search(re.escape(speaker_champ) + r'Skin0*([0-9]{1,2})', text, re.IGNORECASE)
    if m_spk:
        spk_skin = int(m_spk.group(1))
    m_tgt = re.search(re.escape(other_champ) + r'Skin0*([0-9]{1,2})', text, re.IGNORECASE)
    if m_tgt:
        tgt_skin = int(m_tgt.group(1))
    return spk_skin, tgt_skin

def normalize_dialogue_topic(raw_topic, champA, champB):
    """
    Karşılıklı diyalog anahtarını (örn. Kill3DGeneral01, Move2DLong05, FirstMove2D06)
    insan dostu Türkçe senaryo başlığına ve grup kategorisine dönüştürür.
    """
    tl = raw_topic.lower()
    num_m = re.search(r'(\d+)$', raw_topic)
    seq_num = int(num_m.group(1)) if num_m else 1

    if 'kill' in tl:
        if 'champ' in tl or 'general' in tl:
            return "kill_near", "Yakındayken Şampiyon Katletme Diyaloğu", f"Beraber Şampiyon Katledince #{seq_num}"
        return "kill_near", "Katletme Diyaloğu", f"Katletme Diyaloğu #{seq_num}"
    if 'firstmove' in tl:
        return "move_together", "Vadiye İlk Adım & Beraber Yürüyüş Diyaloğu", f"Oyuna Başlarken / İlk Yürüyüş #{seq_num}"
    if 'move' in tl:
        return "move_together", "Yan Yana Yürürken Sohbet Diyaloğu", f"Beraber Yürürken Sohbet #{seq_num}"
    if 'recall' in tl:
        return "recall_together", "Birlikte Üsse Dönüş (Recall) Diyaloğu", f"Beraber Üsse Dönerken (Recall) #{seq_num}"
    if 'taunt' in tl:
        return "taunt_exchange", "Karşılıklı Kışkırtma (CTRL+2) Atışması", f"Kışkırtma & Yanıt Atışması #{seq_num}"
    if 'joke' in tl:
        return "joke_exchange", "Karşılıklı Şaka (CTRL+1) Atışması", f"Şaka & Yanıt Atışması #{seq_num}"
    if 'engage' in tl or 'allin' in tl or 'attack' in tl:
        return "combat_together", "Omuz Omuza Çatışma Diyaloğu", f"Savaşa Girerken Diyalog #{seq_num}"
    return "special_dialogue", "Özel Karşılıklı Diyalog", f"Karşılıklı Diyalog #{seq_num}"

def describe_one_way_interaction(ev_name, speaker_champ, target_champ):
    """
    Tek yönlü etkileşim event'ini nerfplz.com tarzı kategori ve Türkçe alt başlığa ayırır.
    Dönüş: (section_key, section_title, sub_category_tr, sort_order)
    """
    el = ev_name.lower()

    if 'firstencounter' in el or ('encounter' in el and 'first' in el):
        if 'ally' in el:
            return "first_encounter", "İlk Karşılaşma (First Encounter)", f"Dost {target_champ} ile İlk Karşılaşma", 10
        if 'enemy' in el:
            return "first_encounter", "İlk Karşılaşma (First Encounter)", f"Düşman {target_champ} ile İlk Karşılaşma", 12
        return "first_encounter", "İlk Karşılaşma (First Encounter)", f"{target_champ} ile İlk Karşılaşma", 11

    if 'kill' in el or 'firstblood' in el:
        if 'near' in el or 'with' in el or 'assist' in el:
            return "other_gameplay", "Diğer Oyun İçi Etkileşimler (Other Gameplay)", f"{target_champ} Yakındayken Şampiyon Katletme / Asist", 40
        return "kills", "Katletmeler (Kills & Objectives)", f"{target_champ} Şampiyonunu Katletme", 20

    if 'tauntresponse' in el:
        return "taunts_jokes", "Kışkırtma & Şaka (Taunts & Jokes)", f"{target_champ} Kışkırtmasına Yanıt (Taunt Response)", 32
    if 'jokeresponse' in el:
        return "taunts_jokes", "Kışkırtma & Şaka (Taunts & Jokes)", f"{target_champ} Şakasına Yanıt (Joke Response)", 34
    if 'taunt' in el:
        return "taunts_jokes", "Kışkırtma & Şaka (Taunts & Jokes)", f"{target_champ} Şampiyonunu Kışkırtma (CTRL+2)", 30
    if 'joke' in el:
        return "taunts_jokes", "Kışkırtma & Şaka (Taunts & Jokes)", f"{target_champ} Şampiyonuna Şaka Yapma (CTRL+1)", 33
    if 'laugh' in el:
        return "taunts_jokes", "Kışkırtma & Şaka (Taunts & Jokes)", f"{target_champ} ile Kahkaha (CTRL+4)", 35
    if 'dance' in el:
        return "other_gameplay", "Diğer Oyun İçi Etkileşimler (Other Gameplay)", f"{target_champ} ile Birlikte Dans Etme (CTRL+3)", 45

    if 'recall' in el:
        return "other_gameplay", "Diğer Oyun İçi Etkileşimler (Other Gameplay)", f"{target_champ} ile Birlikte Üsse Dönüş (Recall)", 41
    if 'move' in el:
        return "other_gameplay", "Diğer Oyun İçi Etkileşimler (Other Gameplay)", f"{target_champ} Yakınında Hareket / Yürüyüş", 42
    if 'ping' in el or 'omw' in el or 'danger' in el or 'missing' in el or 'help' in el:
        return "other_gameplay", "Diğer Oyun İçi Etkileşimler (Other Gameplay)", f"{target_champ} İçin Akıllı Sinyal (Ping) Verme", 43
    if 'shield' in el or 'heal' in el or 'buff' in el or 'protect' in el or 'save' in el:
        return "other_gameplay", "Diğer Oyun İçi Etkileşimler (Other Gameplay)", f"{target_champ} Üzerinde Kalkan / İyileştirme / Koruma", 44
    if 'death' in el or 'die' in el or 'mourn' in el:
        return "other_gameplay", "Diğer Oyun İçi Etkileşimler (Other Gameplay)", f"{target_champ} Katledildiğinde / Ölürken Tepki", 46
    if 'assist' in el:
        return "other_gameplay", "Diğer Oyun İçi Etkileşimler (Other Gameplay)", f"{target_champ} İle Asist / Yardımlaşma", 47
    if 'spell' in el or 'cast' in el or 'hit' in el or any(k in el for k in ['_q', '_w', '_e', '_r', 'ult']):
        return "other_gameplay", "Diğer Oyun İçi Etkileşimler (Other Gameplay)", f"{target_champ} Üzerinde Yetenek Kullanımı", 48

    return "other_gameplay", "Diğer Oyun İçi Etkileşimler (Other Gameplay)", f"{target_champ} ile Özel Etkileşim", 50


# Popüler kostüm serisi eşleştirmeleri (Örn: Rakan Skin05 Star Guardian <-> Xayah Skin04 Star Guardian)
SKIN_PAIR_CORRESPONDENCE = {
    ("rakan", 0, "xayah"): 0,
    ("rakan", 1, "xayah"): 1,   # Kozmik
    ("rakan", 2, "xayah"): 2,   # Gönül Avcısı
    ("rakan", 3, "xayah"): 3,   # SSG
    ("rakan", 5, "xayah"): 4,   # Yıldız Muhafızı
    ("rakan", 36, "xayah"): 38, # Arınmış Yıldız Muhafızı
    ("rakan", 47, "xayah"): 57, # Savaş Akademisi
    ("xayah", 0, "rakan"): 0,
    ("xayah", 1, "rakan"): 1,
    ("xayah", 2, "rakan"): 2,
    ("xayah", 3, "rakan"): 3,
    ("xayah", 4, "rakan"): 5,   # Yıldız Muhafızı
    ("xayah", 38, "rakan"): 36, # Arınmış Yıldız Muhafızı
    ("xayah", 57, "rakan"): 47, # Savaş Akademisi
    ("kayle", 6, "morgana"): 5,
    ("morgana", 5, "kayle"): 6,
}

def infer_partner_skin_num(speaker_champ, speaker_skin_num, partner_champ, explicit_partner_skin=0):
    if explicit_partner_skin > 0:
        return explicit_partner_skin
    key = (speaker_champ.lower(), int(speaker_skin_num), partner_champ.lower())
    if key in SKIN_PAIR_CORRESPONDENCE:
        return SKIN_PAIR_CORRESPONDENCE[key]
    if speaker_skin_num > 0:
        # Aynı kostüm serisi adı varsa (örn. Vahşi Batılı Lucian <-> Vahşi Batılı Senna)
        spk_meta = resolve_skin_meta(speaker_champ, speaker_skin_num)
        spk_words = set(spk_meta["skin_name"].lower().replace(speaker_champ.lower(), "").split())
        skins = get_skins_db()
        p_clean = partner_champ.lower().replace(" ", "").replace("'", "")
        for s in skins:
            cn = (s.get('champion_name') or s.get('champion_alias') or '').lower().replace(" ", "").replace("'", "")
            if cn == p_clean and int(s.get('skin_num', 0)) > 0:
                p_name = (s.get('name_tr') or '').lower().replace(partner_champ.lower(), "")
                p_words = set(p_name.split())
                if len(spk_words & p_words) >= 1 and not (spk_words & p_words).issubset({'ve', 'ile', 'kostümü', 'varsayılan'}):
                    return int(s.get('skin_num', 0))
    return 0


def extract_pair_interactions(champA, champB, force_refresh=False):
    """
    İki şampiyon arasındaki tüm birebir etkileşimleri ve çok turlu karşılıklı diyalog zincirlerini
    çıkarır, kostümlere ve konuşma sıralarına göre gruplar.
    """
    if not champA or not champB:
        return None

    # Önbellek kontrolü
    pair_key = f"{champA}_{champB}"
    cache_path = os.path.join(PAIR_CACHE_DIR, f"{pair_key}.json")
    if not force_refresh and os.path.exists(cache_path):
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cached = json.load(f)
                if cached.get("schema_version") == SCHEMA_VERSION:
                    # Transkriptleri güncel master_transcripts ile tazele
                    _refresh_cached_transcripts(cached)
                    return cached
        except Exception:
            pass

    dataA = extract_champion_raw_data(champA)
    dataB = extract_champion_raw_data(champB)

    a_low = champA.lower()
    b_low = champB.lower()

    # -------------------------------------------------------------------------
    # BÖLÜM 1: KARŞILIKLI SIRALI DİYALOG ZİNCİRLERİ (Chat1 ➔ Chat2 ➔ Chat3 ➔ Chat4)
    # -------------------------------------------------------------------------
    # Anahtar: (skin_pair_key, proximity, topic_key) -> { step_num: [turn_entry, ...] }
    # DİKKAT: Near (Yakında) ve Far (Uzaktan Sesleniş) kesinlikle iki AYRI diyalog zinciridir!
    chat_Regex = re.compile(
        r'(?:Play_vo_)?([A-Za-z]+?)(?:Skin0*(\d+))?_'
        r'(?:Chat3D|With)([A-Za-z]+?)(?:Skin0*(\d+))?(Near|Far)_'
        r'([A-Za-z0-9]+?)_Chat0*(\d+)',
        re.IGNORECASE
    )

    dialogue_buckets = {}
    used_dialogue_wems = set()

    def _register_chat_turn(speaker_champ, partner_champ, spk_skin, prt_skin, proximity, topic_raw, step_num, wem_id, raw_event_name):
        spk_low = speaker_champ.lower()
        if spk_low == a_low:
            skinA = spk_skin
            skinB = infer_partner_skin_num(champA, spk_skin, champB, prt_skin)
        else:
            skinB = spk_skin
            skinA = infer_partner_skin_num(champB, spk_skin, champA, prt_skin)

        prox_clean = str(proximity).capitalize() if proximity else "Near"
        bucket_key = (skinA, skinB, prox_clean, topic_raw)
        dialogue_buckets.setdefault(bucket_key, {})
        dialogue_buckets[bucket_key].setdefault(step_num, [])

        # Aynı adımda aynı wem_id mükerrer eklenmesin
        if any(str(x["wem_id"]) == str(wem_id) for x in dialogue_buckets[bucket_key][step_num]):
            return

        spk_meta = resolve_skin_meta(speaker_champ, spk_skin)
        prt_actual_skin = skinB if spk_low == a_low else skinA
        prt_meta = resolve_skin_meta(partner_champ, prt_actual_skin)

        dialogue_buckets[bucket_key][step_num].append({
            "step": step_num,
            "speaker_champ": speaker_champ,
            "speaker_skin_num": spk_skin,
            "speaker_skin_name": spk_meta["skin_name"],
            "speaker_splash_url": spk_meta["splash_url"],
            "target_champ": partner_champ,
            "target_skin_num": prt_actual_skin,
            "target_skin_name": prt_meta["skin_name"],
            "target_splash_url": prt_meta["splash_url"],
            "proximity": prox_clean,
            "raw_event": raw_event_name,
            "wem_id": str(wem_id),
            "transcript": lookup_transcript(speaker_champ, raw_event_name, wem_id)
        })

    # 1A. WPK gömülü RIFF/cue işaretleyicilerinden Chat adımlarını topla
    for spk_champ, prt_champ, raw_d in [(champA, champB, dataA), (champB, champA, dataB)]:
        for (wpk_skin, wid), marker in raw_d["embedded_markers"].items():
            m = chat_Regex.search(marker)
            if m:
                c1, s1, c2, s2, prox, topic, chat_step = m.groups()
                if c1.lower() == spk_champ.lower() and c2.lower() == prt_champ.lower():
                    spk_s = int(s1) if s1 else wpk_skin
                    prt_s = int(s2) if s2 else 0
                    ev_Synth = f"Play_vo_{marker}" if not marker.startswith("Play_vo_") else marker
                    _register_chat_turn(spk_champ, prt_champ, spk_s, prt_s, prox, topic, int(chat_step), wid, ev_Synth)

    # 1B. BNK HIRC tablosundaki Chat eventlerinden (özellikle son tur olan Chat2/Chat4 için) topla
    for spk_champ, prt_champ, raw_d in [(champA, champB, dataA), (champB, champA, dataB)]:
        for ev, wems in raw_d["event_to_wems"].items():
            m = chat_Regex.search(ev)
            if m:
                c1, s1, c2, s2, prox, topic, chat_step = m.groups()
                if c1.lower() == spk_champ.lower() and c2.lower() == prt_champ.lower():
                    for wid in wems:
                        wpk_skin = raw_d["wem_to_skin"].get(wid, 0)
                        spk_s = int(s1) if s1 else wpk_skin
                        prt_s = int(s2) if s2 else 0
                        _register_chat_turn(spk_champ, prt_champ, spk_s, prt_s, prox, topic, int(chat_step), wid, ev)

    # 1C. Gerçek karşılıklı (en az 2 adımlı) diyalog zincirlerini oluştur
    dialogue_chains = []
    for (skinA, skinB, prox_clean, topic_raw), steps_dict in sorted(dialogue_buckets.items(), key=lambda x: (x[0][0], x[0][1], x[0][2], x[0][3])):
        sorted_step_nums = sorted(steps_dict.keys())
        if len(sorted_step_nums) < 2:
            continue

        turns = []
        for s_num in sorted_step_nums:
            for turn_item in steps_dict[s_num]:
                turns.append(turn_item)
                used_dialogue_wems.add((turn_item["speaker_champ"].lower(), str(turn_item["wem_id"])))

        if not turns:
            continue

        group_id, group_title, chain_title = normalize_dialogue_topic(topic_raw, champA, champB)
        if prox_clean == "Far":
            chain_title = f"{chain_title} (Uzaktan Sesleniş)"

        metaA = resolve_skin_meta(champA, skinA)
        metaB = resolve_skin_meta(champB, skinB)

        dialogue_chains.append({
            "chain_id": f"{champA}_{skinA}_{champB}_{skinB}_{prox_clean}_{topic_raw}",
            "topic_raw": topic_raw,
            "proximity": prox_clean,
            "group_id": group_id,
            "group_title": group_title,
            "title": chain_title,
            "skinA_num": skinA,
            "skinA_name": metaA["skin_name"],
            "skinA_splash": metaA["splash_url"],
            "skinB_num": skinB,
            "skinB_name": metaB["skin_name"],
            "skinB_splash": metaB["splash_url"],
            "is_multi_turn": True,
            "turn_count": len(turns),
            "turns": turns
        })

    # -------------------------------------------------------------------------
    # BÖLÜM 2: TÜM BİREBİR ETKİLEŞİMLER (İlk Karşılaşma, Katletme, Kışkırtma/Şaka, Diğer)
    # -------------------------------------------------------------------------
    sections_map = {
        "first_encounter": {
            "id": "first_encounter",
            "title": "İlk Karşılaşma (First Encounter)",
            "subtitle": "Vadi'de birbirlerini ilk kez gördüklerinde tetiklenen özel karşılaşma replikleri",
            "groups": []
        },
        "kills": {
            "id": "kills",
            "title": "Katletmeler (Kills & Objectives)",
            "subtitle": "Birbirlerini katlettiklerinde veya skor aldıklarında söyledikleri replikler",
            "groups": []
        },
        "taunts_jokes": {
            "id": "taunts_jokes",
            "title": "Kışkırtma, Şaka & Yanıtlar (Taunts & Jokes)",
            "subtitle": "Yakındayken CTRL+1 / CTRL+2 yapıldığında tetiklenen özel atışmalar ve yanıtlar",
            "groups": []
        },
        "other_gameplay": {
            "id": "other_gameplay",
            "title": "Diğer Oyun İçi Etkileşimler (Other Gameplay)",
            "subtitle": "Beraber yürüyüş, üsse dönüş (Recall), kalkan/iyileştirme, asist, dans ve yetenek etkileşimleri",
            "groups": []
        }
    }

    # Yardımcı: Tek yönlü etkileşimleri (A -> B ve B -> A) topla
    one_way_groups = {}  # (section_key, direction_key, spk_skin, tgt_skin, sub_cat_tr, sort_ord) -> [quotes]

    def _collect_directed_events(speaker_champ, target_champ, raw_d, direction_key):
        t_low = target_champ.lower()
        s_low = speaker_champ.lower()

        for ev in sorted(raw_d["events"]):
            # Kendi şampiyon adını silip hedef şampiyon adı geçiyor mu kontrol et
            cleaned = re.sub(re.escape(speaker_champ) + r'(skin\d+)?', '', ev, flags=re.IGNORECASE)
            if t_low not in cleaned.lower():
                continue

            # 2D/3D tekilleştirme
            if '2d' in ev.lower():
                ev_3d = re.sub(r'2d', '3D', ev, flags=re.IGNORECASE)
                if ev_3d in raw_d["events"]:
                    continue

            wems = raw_d["event_to_wems"].get(ev, [])
            if not wems:
                clean_ev = re.sub(r'(K|k)$', '', ev)
                wems = raw_d["event_to_wems"].get(clean_ev, [])
            if not wems:
                continue

            ev_spk_skin, ev_tgt_skin = parse_skin_from_event_or_marker(ev, speaker_champ, target_champ)
            sec_key, sec_title, sub_cat_tr, sort_ord = describe_one_way_interaction(ev, speaker_champ, target_champ)

            for idx, wid in enumerate(wems):
                if (s_low, str(wid)) in used_dialogue_wems:
                    continue
                wpk_skin = raw_d["wem_to_skin"].get(wid, 0)
                actual_spk_skin = ev_spk_skin if ev_spk_skin > 0 else wpk_skin
                actual_tgt_skin = infer_partner_skin_num(speaker_champ, actual_spk_skin, target_champ, ev_tgt_skin)

                spk_meta = resolve_skin_meta(speaker_champ, actual_spk_skin)
                tgt_meta = resolve_skin_meta(target_champ, actual_tgt_skin)

                g_key = (sec_key, direction_key, speaker_champ, target_champ, actual_spk_skin, actual_tgt_skin, sub_cat_tr, sort_ord)
                one_way_groups.setdefault(g_key, {
                    "direction": direction_key,
                    "speaker_champ": speaker_champ,
                    "speaker_skin_num": actual_spk_skin,
                    "speaker_skin_name": spk_meta["skin_name"],
                    "speaker_splash_url": spk_meta["splash_url"],
                    "target_champ": target_champ,
                    "target_skin_num": actual_tgt_skin,
                    "target_skin_name": tgt_meta["skin_name"],
                    "target_splash_url": tgt_meta["splash_url"],
                    "sub_category": sub_cat_tr,
                    "sort_order": sort_ord,
                    "quotes": []
                })

                if any(str(q["wem_id"]) == str(wid) for q in one_way_groups[g_key]["quotes"]):
                    continue

                one_way_groups[g_key]["quotes"].append({
                    "speaker_champ": speaker_champ,
                    "speaker_skin_num": actual_spk_skin,
                    "speaker_skin_name": spk_meta["skin_name"],
                    "speaker_splash_url": spk_meta["splash_url"],
                    "target_champ": target_champ,
                    "target_skin_num": actual_tgt_skin,
                    "target_skin_name": tgt_meta["skin_name"],
                    "target_splash_url": tgt_meta["splash_url"],
                    "raw_event": ev,
                    "action_name": sub_cat_tr,
                    "wem_id": str(wid),
                    "variation_index": idx + 1,
                    "variation_total": len(wems),
                    "transcript": lookup_transcript(speaker_champ, ev, wid)
                })

    _collect_directed_events(champA, champB, dataA, "A_to_B")
    _collect_directed_events(champB, champA, dataB, "B_to_A")

    # Taunt ➔ TauntResponse veya Joke ➔ JokeResponse karşılıklı çiftleri varsa onları dialogue_chains'e de ekle!
    _build_taunt_joke_response_chains(champA, champB, one_way_groups, dialogue_chains)

    for g_key, g_obj in sorted(one_way_groups.items(), key=lambda x: (x[0][7], 0 if x[0][1] == "A_to_B" else 1, x[0][4], x[0][5], x[0][6])):
        sec_key = g_key[0]
        if sec_key in sections_map and g_obj["quotes"]:
            sections_map[sec_key]["groups"].append(g_obj)

    total_dialogue_turns = sum(c["turn_count"] for c in dialogue_chains)
    total_one_way_quotes = sum(
        sum(len(g["quotes"]) for g in sec["groups"])
        for sec in sections_map.values()
    )

    metaA0 = resolve_skin_meta(champA, 0)
    metaB0 = resolve_skin_meta(champB, 0)

    result_payload = {
        "schema_version": SCHEMA_VERSION,
        "champA": {
            "name": champA,
            "splash_url": metaA0["splash_url"],
            "icon_url": f"https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/champion-icons/{_get_champ_id(champA)}.png"
        },
        "champB": {
            "name": champB,
            "splash_url": metaB0["splash_url"],
            "icon_url": f"https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/champion-icons/{_get_champ_id(champB)}.png"
        },
        "summary": {
            "dialogue_chains_count": len(dialogue_chains),
            "dialogue_turns_count": total_dialogue_turns,
            "one_way_quotes_count": total_one_way_quotes,
            "total_interactions": total_dialogue_turns + total_one_way_quotes,
            "total_dialogue_chains": len(dialogue_chains),
            "total_dialogue_turns": total_dialogue_turns,
            "total_one_way_quotes": total_one_way_quotes
        },
        "dialogue_chains": dialogue_chains,
        "sections": [
            sec for sec in [
                sections_map["first_encounter"],
                sections_map["kills"],
                sections_map["taunts_jokes"],
                sections_map["other_gameplay"]
            ] if len(sec["groups"]) > 0
        ]
    }

    try:
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(result_payload, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    return result_payload


def _build_taunt_joke_response_chains(champA, champB, one_way_groups, dialogue_chains):
    """
    Bir şampiyonun diğerine yaptığı Kışkırtma (Taunt) veya Şaka (Joke) ile
    diğer şampiyonun verdiği Yanıt (TauntResponse / JokeResponse) varsa bunları
    sıralı karşılıklı konuşma zinciri olarak da birleştirir.
    """
    existing_ids = {c["chain_id"] for c in dialogue_chains}

    for mode, init_kw, resp_kw, title_tr in [
        ("taunt", "Kışkırtma (CTRL+2)", "Kışkırtmasına Yanıt", "Karşılıklı Kışkırtma & Yanıt Atışması"),
        ("joke", "Şaka Yapma (CTRL+1)", "Şakasına Yanıt", "Karşılıklı Şaka & Yanıt Atışması")
    ]:
        for dir_init, dir_resp, spk1, spk2 in [
            ("A_to_B", "B_to_A", champA, champB),
            ("B_to_A", "A_to_B", champB, champA)
        ]:
            inits = [
                g for k, g in one_way_groups.items()
                if k[0] == "taunts_jokes" and k[1] == dir_init and init_kw in g["sub_category"]
            ]
            resps = [
                g for k, g in one_way_groups.items()
                if k[0] == "taunts_jokes" and k[1] == dir_resp and resp_kw in g["sub_category"]
            ]
            if not inits or not resps:
                continue

            for ig in inits:
                for rg in resps:
                    if ig["speaker_skin_num"] == rg["target_skin_num"] or (ig["speaker_skin_num"] == 0 and rg["speaker_skin_num"] == 0):
                        chain_id = f"{spk1}_{ig['speaker_skin_num']}_{spk2}_{rg['speaker_skin_num']}_{mode}_exchange"
                        if chain_id in existing_ids:
                            continue
                        existing_ids.add(chain_id)

                        turns = []
                        # İlk konuşan (Taunt/Joke) ve yanıt veren (Response) repliklerini sırayla eşle
                        max_len = max(len(ig["quotes"]), len(rg["quotes"]))
                        for i in range(min(max_len, 4)):
                            if i < len(ig["quotes"]):
                                q1 = dict(ig["quotes"][i])
                                q1["step"] = len(turns) + 1
                                turns.append(q1)
                            if i < len(rg["quotes"]):
                                q2 = dict(rg["quotes"][i])
                                q2["step"] = len(turns) + 1
                                turns.append(q2)

                        skinA_num = ig["speaker_skin_num"] if spk1 == champA else rg["speaker_skin_num"]
                        skinB_num = rg["speaker_skin_num"] if spk1 == champA else ig["speaker_skin_num"]
                        metaA = resolve_skin_meta(champA, skinA_num)
                        metaB = resolve_skin_meta(champB, skinB_num)

                        dialogue_chains.append({
                            "chain_id": chain_id,
                            "topic_raw": f"{mode}_response",
                            "group_id": f"{mode}_exchange",
                            "group_title": title_tr,
                            "title": f"{spk1} ➔ {spk2} {title_tr}",
                            "skinA_num": skinA_num,
                            "skinA_name": metaA["skin_name"],
                            "skinA_splash": metaA["splash_url"],
                            "skinB_num": skinB_num,
                            "skinB_name": metaB["skin_name"],
                            "skinB_splash": metaB["splash_url"],
                            "is_multi_turn": True,
                            "turn_count": len(turns),
                            "turns": turns
                        })


def _refresh_cached_transcripts(payload):
    """Önbellekteki verinin transkriptlerini master_transcripts.json'dan anlık günceller."""
    for ch in payload.get("dialogue_chains", []):
        for t in ch.get("turns", []):
            tr = lookup_transcript(t.get("speaker_champ", ""), t.get("raw_event", ""), t.get("wem_id", ""))
            if tr:
                t["transcript"] = tr
    for sec in payload.get("sections", []):
        for grp in sec.get("groups", []):
            for q in grp.get("quotes", []):
                tr = lookup_transcript(q.get("speaker_champ", ""), q.get("raw_event", ""), q.get("wem_id", ""))
                if tr:
                    q["transcript"] = tr


def _get_champ_id(champ_name):
    skins = get_skins_db()
    c_clean = champ_name.lower().replace(" ", "").replace("'", "")
    for s in skins:
        cn = (s.get('champion_name') or s.get('champion_alias') or '').lower().replace(" ", "").replace("'", "")
        if cn == c_clean and s.get('champion_id'):
            return s['champion_id']
    return -1


# Öne çıkan popüler birebir etkileşim ve diyalog ikilileri
FEATURED_PAIRS = [
    {"champA": "Rakan", "champB": "Xayah", "tag": "🔥 223 Karşılıklı Diyalog & Kostüm Atışması", "desc": "Varsayılan, Yıldız Muhafızı, Arınmış Yıldız Muhafızı ve Savaş Akademisi tam soru-cevap diyalogları"},
    {"champA": "Kayle", "champB": "Morgana", "tag": "⚔️ 27 Karşılıklı Diyalog & Kardeş Çatışması", "desc": "İkiz kız kardeşlerin beraber yürüyüş, katletme ve kışkırtma atışmaları"},
    {"champA": "Lucian", "champB": "Senna", "tag": "💫 15+ Karşılıklı Diyalog & Vahşi Batılı / KOD ADI", "desc": "Işık Muhafızlarının vadiye ilk adım, beraber katletme ve kostüm diyalogları"},
    {"champA": "Yasuo", "champB": "Yone", "tag": "🗡️ Kardeşlerin Karşılaşması & Ruh Çiçeği", "desc": "Onur, kefaret, ilk karşılaşma ve katletme replikleri"},
    {"champA": "Jinx", "champB": "Vi", "tag": "💥 Piltover & Zaun Kardeş Rekabeti", "desc": "İlk karşılaşma, kışkırtma yanıtları ve yakalama etkileşimleri"},
    {"champA": "Caitlyn", "champB": "Vi", "tag": "🚓 Piltover Ortakları", "desc": "Beraber çalışma, kışkırtma yanıtları ve özel kostüm etkileşimleri"},
    {"champA": "Garen", "champB": "Darius", "tag": "🛡️ Demacia vs Noxus & Yüce Kral", "desc": "Yüce Kral Garen ve Yüce Kral Darius karşılıklı kışkırtma ve düello replikleri"},
    {"champA": "Ashe", "champB": "Tryndamere", "tag": "❄️ Freljord Hükümdarları", "desc": "Savaş Anası ve Barbar Kralın karşılıklı etkileşimleri"},
    {"champA": "Diana", "champB": "Leona", "tag": "🌙 Ay ve Güneşin Çatışması", "desc": "Tutulma Şövalyeleri ve Targon suretlerinin düellosu"},
    {"champA": "Nasus", "champB": "Renekton", "tag": "🏜️ Shurima Yükseliş Kardeşleri", "desc": "Kadim Shurima kardeşlerinin trajik karşılaşma ve katletme replikleri"},
    {"champA": "KhaZix", "champB": "Rengar", "tag": "🩸 Av Başlıyor!", "desc": "Ezeli avcı ve avın özel karşılaşma ve katletme replikleri"},
    {"champA": "Shen", "champB": "Zed", "tag": "🌑 Alacakaranlık ve Gölge Tarikatı", "desc": "Ionia dengesi ve gölge ustasının hesaplaşması"}
]

def get_cached_pair_summaries():
    """Önbellekteki tüm ikililerin gerçek WPK/BNK ses ve diyalog sayılarını döndürür."""
    summaries = {}
    if os.path.exists(PAIR_CACHE_DIR):
        for fn in os.listdir(PAIR_CACHE_DIR):
            if not fn.endswith(".json"):
                continue
            fpath = os.path.join(PAIR_CACHE_DIR, fn)
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    d = json.load(f)
                cA = d.get("champA", {}).get("name", "")
                cB = d.get("champB", {}).get("name", "")
                if cA and cB and "summary" in d:
                    first, second = sorted([cA.lower(), cB.lower()])
                    summaries[f"{first}__{second}"] = d["summary"]
            except Exception:
                pass
    return summaries

def get_featured_pairs():
    return FEATURED_PAIRS


if __name__ == "__main__":
    res = extract_pair_interactions("Rakan", "Xayah", force_refresh=True)
    print("Rakan & Xayah Summary:", json.dumps(res["summary"], ensure_ascii=False, indent=2))

