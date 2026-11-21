# -*- coding: utf-8 -*-
"""
🃏 Legends of Runeterra (LoR) Tam Kapsamlı Ses, Replik, Matris ve Diyalog Veritabanı Üretici
C:\Riot Games\LoR\live kurulumundaki:
  - GamePlayData.bin & LocalizedText_tr_tr.bin (Kartlar, Şampiyonlar, Takipçiler ve Kostümler)
  - AssetBundles/*.bbq (1.388 CardSoundProfile: PersonalVO ve GlobalVO 1-turlu/2-turlu etkileşimler)
  - Audio/Turkish(Turkey)_stage1.pck & stage0.pck (20.696 Türkçe WEM ses dosyası)
verilerini %100 deterministik olarak çözer ve Web Stüdyosu + JIT Ses Sunucusu için kaydeder.
"""

import os
import re
import sys
import json
import time
import struct

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOR_LIVE_DIR = r"C:\Riot Games\LoR\live\PatcherData\PatchableFiles"
GPD_PATH = os.path.join(LOR_LIVE_DIR, "GamePlayData", "GamePlayData.bin")
LOC_TR_PATH = os.path.join(LOR_LIVE_DIR, "GamePlayData", "LocalizedText_tr_tr.bin")
AB_DIR = os.path.join(LOR_LIVE_DIR, "AssetBundles")
ABM_PATH = os.path.join(AB_DIR, "AssetToBundleMap.txt")
AUDIO_DIR = os.path.join(LOR_LIVE_DIR, "Audio")

LOL_MATRIX_PATH = os.path.join(ROOT_DIR, "lol-matrix-web", "public", "data", "lol_matrix_data.json")
LOR_MATRIX_OUT = os.path.join(ROOT_DIR, "lol-matrix-web", "public", "data", "lor_matrix_data.json")
LOR_FULL_DB_OUT = os.path.join(ROOT_DIR, "cache", "lor_full_database.json")
os.makedirs(os.path.dirname(LOR_MATRIX_OUT), exist_ok=True)
os.makedirs(os.path.dirname(LOR_FULL_DB_OUT), exist_ok=True)


def fnv1_64_lor(wem_filename: str) -> int:
    """LoR Wwise External Source 64-bit FNV-1 hash hesaplayıcı."""
    s = f"turkish(turkey)\\{wem_filename.lower()}"
    h = 0xcbf29ce484222325
    prime = 0x100000001b3
    for b in s.encode('ascii', 'ignore'):
        h = ((h * prime) & 0xFFFFFFFFFFFFFFFF) ^ b
    return h


def load_pck_hashes() -> dict:
    """Turkish(Turkey)_stage0.pck ve stage1.pck içindeki tüm 64-bit ses hashlerini indeksler."""
    pck_map = {}
    for stage_file in ["Turkish(Turkey)_stage0.pck", "Turkish(Turkey)_stage1.pck"]:
        p = os.path.join(AUDIO_DIR, stage_file)
        if not os.path.exists(p):
            continue
        with open(p, 'rb') as f:
            header = f.read(0x3C)
            if len(header) < 0x3C or header[:4] != b'AKPK':
                continue
            ext_count = struct.unpack_from('<I', header, 0x38)[0]
            table = f.read(ext_count * 24)
            for i in range(ext_count):
                h64, mult, fsize, offset_blocks, folder_id = struct.unpack_from('<QIIII', table, i * 24)
                pck_map[h64] = (stage_file, offset_blocks * mult, fsize)
    return pck_map


def lz4_decompress(src: bytes, uncompressed_size: int) -> bytes:
    dst = bytearray()
    i = 0
    n = len(src)
    while i < n and len(dst) < uncompressed_size:
        token = src[i]
        i += 1
        lit_len = token >> 4
        if lit_len == 15:
            while i < n:
                b = src[i]
                i += 1
                lit_len += b
                if b != 255:
                    break
        dst.extend(src[i:i + lit_len])
        i += lit_len
        if i >= n or len(dst) >= uncompressed_size:
            break
        offset = src[i] | (src[i + 1] << 8)
        i += 2
        if offset == 0:
            break
        match_len = (token & 0x0F) + 4
        if (token & 0x0F) == 15:
            while i < n:
                b = src[i]
                i += 1
                match_len += b
                if b != 255:
                    break
        start = len(dst) - offset
        for j in range(match_len):
            dst.append(dst[start + j])
    return bytes(dst[:uncompressed_size])


def read_unityfs(path: str) -> bytes:
    with open(path, 'rb') as f:
        data = f.read()
    pos = 0

    def r_cstr():
        nonlocal pos
        e = data.index(b'\x00', pos)
        s = data[pos:e].decode('utf-8', 'ignore')
        pos = e + 1
        return s

    r_cstr()
    pos += 4
    r_cstr()
    r_cstr()
    size, cib, uib, flags = struct.unpack_from('>qIII', data, pos)
    pos += 20
    if (flags & 0x200) and (pos % 16 != 0):
        pos += 16 - (pos % 16)
    ib_comp = data[pos:pos + cib]
    pos += cib
    ib = lz4_decompress(ib_comp, uib) if (flags & 0x3f) in (2, 3) else ib_comp
    b_count = struct.unpack_from('>i', ib, 16)[0]
    bpos = 20
    blocks = []
    for _ in range(b_count):
        blocks.append(struct.unpack_from('>IIH', ib, bpos))
        bpos += 10
    dpos = len(data) - sum(b[1] for b in blocks)
    out = bytearray()
    for bu, bc, bf in blocks:
        chunk = data[dpos:dpos + bc]
        dpos += bc
        out.extend(lz4_decompress(chunk, bu) if (bf & 0x3f) in (2, 3) else chunk)
    return bytes(out)


def dd_card_image(code: str, set_str: str = "") -> str:
    """runeterra.ar LoR tam ekran (full art) kart görseli URL'si üretir."""
    return f"https://cdn.runeterra.ar/assets/img/card/en_us/{code}-full.webp"


def classify_wem_action(wem_name: str, target_name: str = "") -> tuple:
    """
    LoR .wem dosya adından:
    (cat_id, base_action, action_label_tr, sort_weight) döner.
    """
    w = wem_name.lower()
    if '_arrival_interaction_ally_' in w or '_arrival_ally_' in w:
        return (
            "5_Ozel_Karsilasmalar_ve_Atiflar",
            "karsilasma",
            f"Dost Karşılaşması ({target_name})" if target_name else "Dost Karşılaşması",
            10
        )
    if '_arrival_interaction_enemy_' in w or '_arrival_enemy_' in w:
        return (
            "5_Ozel_Karsilasmalar_ve_Atiflar",
            "karsilasma",
            f"Düşman Karşılaşması ({target_name})" if target_name else "Düşman Karşılaşması",
            12
        )
    if '_attack_declare_ally_' in w or '_attack_declare_enemy_' in w:
        side = "Dost" if "_ally_" in w else "Düşman"
        return (
            "5_Ozel_Karsilasmalar_ve_Atiflar",
            "saldiri",
            f"Saldırı Etkileşimi - {side} ({target_name})" if target_name else f"Saldırı Etkileşimi ({side})",
            20
        )
    if '_block_declare_ally_' in w or '_block_declare_enemy_' in w:
        side = "Dost" if "_ally_" in w else "Düşman"
        return (
            "5_Ozel_Karsilasmalar_ve_Atiflar",
            "kiskirtma",
            f"Bloklama Etkileşimi - {side} ({target_name})" if target_name else f"Bloklama Etkileşimi ({side})",
            25
        )
    if '_death_ally_' in w:
        return (
            "5_Ozel_Karsilasmalar_ve_Atiflar",
            "olum",
            f"Dost Ölümüne Tepki ({target_name})" if target_name else "Dost Ölümüne Tepki",
            30
        )
    if '_death_enemy_' in w:
        return (
            "5_Ozel_Karsilasmalar_ve_Atiflar",
            "katletme",
            f"Düşman Katletme / Ölümü ({target_name})" if target_name else "Düşman Katletme",
            15
        )
    if '_spell_resolve_' in w or '_spell_cast_' in w:
        return (
            "1_Q_Yetenegi",
            "yetenek",
            f"Büyü Tepkisi ({target_name})" if target_name else "Büyü Kullanımı",
            18
        )
    if '_summon_' in w:
        return ("0_Secim_ve_Ozel_Sesler", "secim", "Sahaya Çağrılma (Summon)", 1)
    if '_choose_me_' in w:
        return ("0_Secim_ve_Ozel_Sesler", "secim", "Desteye / Ele Seçilme", 2)
    if '_remove_me_' in w:
        return ("0_Secim_ve_Ozel_Sesler", "secim", "Desteden Çıkarılma", 3)
    if '_levelup_' in w:
        return ("4_R_Ulti", "yetenek", "Seviye Atlama (Level Up!)", 5)
    if '_ability_' in w or '_skill_' in w:
        return ("1_Q_Yetenegi", "yetenek", "Özel Yetenek / Büyü Tetikleme", 15)
    if '_attack_declare_' in w:
        return ("9_Hareket_ve_Saldiri", "saldiri", "Saldırıya Geçme (Attack Declare)", 40)
    if '_block_declare_' in w:
        return ("2_W_Yetenegi", "hareket", "Savunma / Bloklama (Block Declare)", 45)
    if '_victory_' in w:
        return ("7_Saka_Kiskirtma_Kahkaha", "saka", "Zafer (Victory)", 50)
    if '_defeat_' in w:
        return ("8_Donus_ve_Olum", "olum", "Yenilgi (Defeat)", 55)
    if '_death_' in w:
        return ("8_Donus_ve_Olum", "olum", "Ölüm / Yok Olma (Death)", 60)
    if '_timer_idle_' in w or '_idle_' in w or '_turn_' in w:
        return ("7_Saka_Kiskirtma_Kahkaha", "kiskirtma", "Süre / Bekleme Repliği (Idle Timer)", 65)
    if '_emote_' in w or '_laugh_' in w or '_taunt_' in w:
        return ("7_Saka_Kiskirtma_Kahkaha", "saka", "İfade / Gülüş", 70)
    return ("10_Genel_Replikler", "diger", "Oyun İçi Özel Replik", 80)


def main():
    t0 = time.time()
    print("🃏 Legends of Runeterra (LoR) Ses ve Etkileşim Veritabanı Üretiliyor...")

    # 1. LoL şampiyon ikonlarını yükle (ortak şampiyonlarda kusursuz avatar için)
    lol_icons = {}
    lol_splashes = {}
    if os.path.exists(LOL_MATRIX_PATH):
        try:
            with open(LOL_MATRIX_PATH, 'r', encoding='utf-8') as f:
                lol_data = json.load(f)
                for c in lol_data.get('champions', []):
                    k = c['name'].lower().replace(" ", "").replace("'", "").replace(".", "")
                    lol_icons[k] = c.get('icon_url', '')
                    lol_splashes[k] = f"https://ddragon.leagueoflegends.com/cdn/img/champion/splash/{c['id']}_0.jpg"
        except Exception:
            pass

    # 2. PCK ses indeksini yükle
    pck_map = load_pck_hashes()
    print(f"  ✓ PCK Ses Paketi İndekslendi: {len(pck_map):,} Türkçe .wem kaydı")

    # 3. LocalizedText_tr_tr.bin ayrıştır
    with open(LOC_TR_PATH, 'rb') as f:
        loc_bytes = f.read()

    tr_card_names = {}
    for m in re.finditer(rb'card_([0-9A-Z]+)_Name', loc_bytes):
        code = m.group(1).decode('ascii')
        pos = m.end()
        if pos + 2 <= len(loc_bytes):
            ln = struct.unpack_from('<H', loc_bytes, pos)[0]
            if 0 < ln < 200 and pos + 2 + ln <= len(loc_bytes):
                try:
                    tr_card_names[code] = loc_bytes[pos + 2:pos + 2 + ln].decode('utf-8').strip()
                except Exception:
                    pass

    skin_tr_map = {}
    for m in re.finditer(rb'(client_champskin_[a-zA-Z0-9_]+)', loc_bytes):
        k = m.group(1).decode('ascii').lower()
        pos = m.end()
        if pos + 2 <= len(loc_bytes):
            ln = struct.unpack_from('<H', loc_bytes, pos)[0]
            if 0 < ln < 200 and pos + 2 + ln <= len(loc_bytes):
                try:
                    skin_tr_map[k] = loc_bytes[pos + 2:pos + 2 + ln].decode('utf-8').strip()
                except Exception:
                    pass

    comic_subtitles = {}
    for m in re.finditer(rb'(VO_[A-Za-z0-9_]+)', loc_bytes):
        vo_key = m.group(1).decode('ascii').lower()
        pos = m.end()
        if pos + 2 <= len(loc_bytes):
            ln = struct.unpack_from('<H', loc_bytes, pos)[0]
            if 0 < ln < 400 and pos + 2 + ln <= len(loc_bytes):
                try:
                    comic_subtitles[vo_key] = loc_bytes[pos + 2:pos + 2 + ln].decode('utf-8').strip()
                except Exception:
                    pass

    # 4. GamePlayData.bin ayrıştır (Kartlar ve Kostüm GUID'leri)
    with open(GPD_PATH, 'rb') as f:
        gpd_bytes = f.read()

    guid_to_skin = {}
    for m in re.finditer(rb'(client_champskin_[a-zA-Z0-9_]+_name)', gpd_bytes):
        k_base = m.group(1).decode('ascii').lower()
        if k_base.endswith('_name'):
            k_base = k_base[:-5]
        chunk = gpd_bytes[max(0, m.start() - 800):min(len(gpd_bytes), m.end() + 800)]
        m_guid = re.search(rb'\x9a\x5b\x13\xec\x10\x24\x00([0-9a-f\-]{36})', chunk)
        m_card = re.search(rb'CardProfiles/([0-9A-Z]{7})', chunk)
        if m_guid:
            guid = m_guid.group(1).decode('ascii').lower()
            tr_name = skin_tr_map.get(k_base + '_namelower') or skin_tr_map.get(k_base + '_name') or k_base
            card_code = m_card.group(1).decode('ascii') if m_card else ''
            guid_to_skin[guid] = {
                "guid": guid,
                "card_code": card_code,
                "skin_name": tr_name,
                "skin_key": k_base
            }

    cards = {}
    csp_to_cards = {}
    for m in re.finditer(rb'\xe6\xbd\x39\x8d\x10', gpd_bytes):
        pos = m.end()
        eng_len = struct.unpack_from('<H', gpd_bytes, pos)[0]
        eng_name = gpd_bytes[pos + 2:pos + 2 + eng_len].decode('utf-8', errors='ignore').strip()
        pos2 = pos + 2 + eng_len
        if gpd_bytes[pos2:pos2 + 5] == b'\x7d\x96\x27\x0c\x10':
            kl = struct.unpack_from('<H', gpd_bytes, pos2 + 5)[0]
            key = gpd_bytes[pos2 + 7:pos2 + 7 + kl].decode('ascii', errors='ignore')
            mc = re.match(r'card_([0-9A-Z]+)_Name', key)
            if mc:
                code = mc.group(1)
                before = gpd_bytes[max(0, m.start() - 400):m.start()]
                after = gpd_bytes[pos2 + 7 + kl:min(len(gpd_bytes), pos2 + 7 + kl + 150)]
                m_csp = re.search(rb'CardSoundProfiles/([0-9a-zA-Z\-_]+)\.asset', before)
                csp = m_csp.group(1).decode('ascii').lower() if m_csp else None
                m_path = re.search(rb'Cards/([^/\x00]+)/([^/\x00]+)/([^\x00\x10]+)', before)
                cset, creg, cinternal = (
                    m_path.group(1).decode('ascii', 'ignore'),
                    m_path.group(2).decode('ascii', 'ignore'),
                    m_path.group(3).decode('ascii', 'ignore')
                ) if m_path else ('', '', '')
                is_champ = b'\x3c\x05\xd2\x49\x06\x01\x00\x00\x00' in after
                tr_name = tr_card_names.get(code, eng_name)
                cards[code] = {
                    'code': code,
                    'eng': eng_name,
                    'tr': tr_name,
                    'csp': csp,
                    'set': cset,
                    'region': creg,
                    'internal': cinternal,
                    'is_champ': is_champ
                }
                if csp:
                    csp_to_cards.setdefault(csp, []).append(code)

    print(f"  ✓ GamePlayData Çözüldü: {len(cards):,} kart, {len(guid_to_skin)} kostüm GUID")

    # 5. AssetToBundleMap.txt ayrıştır
    csp_to_bbq = {}
    with open(ABM_PATH, 'r', encoding='utf-8') as f:
        cur_bbq = None
        for line in f:
            l = line.strip()
            if l.endswith('.bbq'):
                cur_bbq = os.path.join(AB_DIR, l.replace('/', os.sep))
            elif 'cardsoundprofiles/' in l.lower() and cur_bbq:
                cid = l.lower().split('cardsoundprofiles/')[1].replace('.asset', '')
                csp_to_bbq[cid] = cur_bbq

    # 6. Karakter (Entity) birleştirme haritası oluştur
    # Her temel şampiyon (128 şampiyon) ve ses profili olan takipçi kartları kendi kanonik ismine bağlanır.
    # Örn: "01IO015" (Yasuo) ve "01IO015T1" (Yasuo Lvl 2) -> "Yasuo"
    code_to_char_name = {}
    char_meta = {}

    # Önce temel şampiyonları (T içermeyenler) kaydet
    for code, c in sorted(cards.items(), key=lambda x: (len(x[0]), x[0])):
        if c['is_champ'] and c['csp'] and 'T' not in code[4:]:
            cname = c['tr']
            code_to_char_name[code] = cname
            clean_k = cname.lower().replace(" ", "").replace("'", "").replace(".", "")
            eng_k = c['eng'].lower().replace(" ", "").replace("'", "").replace(".", "")
            icon_url = lol_icons.get(clean_k) or lol_icons.get(eng_k) or dd_card_image(code, c['set'])
            splash_url = dd_card_image(code, c['set'])
            if cname not in char_meta:
                char_meta[cname] = {
                    'name': cname,
                    'id': re.sub(r'[^a-zA-Z0-9]', '', c['eng']) or code,
                    'base_code': code,
                    'is_champ': True,
                    'region': c['region'],
                    'set': c['set'],
                    'icon_url': icon_url,
                    'splash_url': splash_url,
                    'codes': [code],
                    'skins': {
                        0: {
                            'skin_num': 0,
                            'name': f"Varsayılan {cname}",
                            'is_base': True,
                            'splash_url': splash_url,
                            'voice_type': 'base',
                            'voice_badge': '🃏 LOR VARSAYILAN DUBLAJ',
                            'voice_tag': 'Ana Kart Sesi',
                            'voice_desc': f"{cname} şampiyonunun Legends of Runeterra Türkçe kart seslendirmesi.",
                            'is_unique': True
                        }
                    }
                }
            else:
                char_meta[cname]['codes'].append(code)

    # Seviye 2 / T-kodlu şampiyonları ve tüm sesli takipçi kartlarını kaydet
    for code, c in sorted(cards.items(), key=lambda x: (len(x[0]), x[0])):
        if code in code_to_char_name:
            continue
        base_prefix = code.split('T')[0]
        if c['is_champ'] and base_prefix in code_to_char_name:
            cname = code_to_char_name[base_prefix]
            code_to_char_name[code] = cname
            char_meta[cname]['codes'].append(code)
            continue

        # Takipçi veya diğer kartlar
        cname = c['tr']
        code_to_char_name[code] = cname
        if cname not in char_meta:
            clean_k = cname.lower().replace(" ", "").replace("'", "").replace(".", "")
            icon_url = lol_icons.get(clean_k) or dd_card_image(code, c['set'])
            splash_url = dd_card_image(code, c['set'])
            char_meta[cname] = {
                'name': cname,
                'id': code,
                'base_code': code,
                'is_champ': c['is_champ'],
                'region': c['region'],
                'set': c['set'],
                'icon_url': icon_url,
                'splash_url': splash_url,
                'codes': [code],
                'skins': {
                    0: {
                        'skin_num': 0,
                        'name': f"Varsayılan {cname}",
                        'is_base': True,
                        'splash_url': splash_url,
                        'voice_type': 'base',
                        'voice_badge': '🃏 LOR KART SESİ',
                        'voice_tag': 'Şampiyon' if c['is_champ'] else 'Takipçi / Birim Kartı',
                        'voice_desc': f"{cname} kartının Legends of Runeterra Türkçe seslendirmesi.",
                        'is_unique': True
                    }
                }
            }
        else:
            char_meta[cname]['codes'].append(code)

    # 7. Tüm 1.388 CardSoundProfile (.bbq) paketini aç ve sesleri/etkileşimleri çıkar
    token_re = re.compile(
        rb'(SoundEvent: Voiceover Event(?: [12])?'
        rb'|VO_[A-Za-z0-9_]+\.wem'
        rb'|[0-9]{2}[A-Z]{2}[0-9]{3}(?:T[0-9]+)?'
        rb'|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})'
    )

    slug_to_char = {}
    csp_parsed = {}

    for cid, bbq_path in csp_to_bbq.items():
        if not os.path.exists(bbq_path):
            continue
        raw = read_unityfs(bbq_path)
        tokens = [m.group(1).decode('ascii') for m in token_re.finditer(raw)]

        # Bu CSP hangi karta veya kostüme ait?
        owner_codes = csp_to_cards.get(cid, [])
        is_skin_csp = False
        skin_label = ""
        if not owner_codes:
            m_c = re.match(r'^([0-9]{2}[a-z]{2}[0-9]{3}(?:t[0-9]+)?)', cid)
            if m_c:
                cand_code = m_c.group(1).upper()
                if cand_code in cards or cand_code.split('T')[0] in cards:
                    owner_codes = [cand_code if cand_code in cards else cand_code.split('T')[0]]
                    if len(cid) > len(cand_code):
                        is_skin_csp = True
                        skin_label = cid[len(cand_code):].strip('-_')

        if not owner_codes:
            continue

        primary_code = sorted(owner_codes, key=lambda x: len(x))[0]
        owner_char = code_to_char_name.get(primary_code) or cards.get(primary_code, {}).get('tr', primary_code)

        # Skin CSP ise kostüm numarasını ata
        skin_num = 0
        skin_display_name = f"Varsayılan {owner_char}"
        if is_skin_csp and owner_char in char_meta:
            # Kostüm adını LocalizedText'ten bulmaya çalış
            matched_tr_skin = None
            for sk_k, sk_v in skin_tr_map.items():
                if sk_k.endswith('_namelower'):
                    core = sk_k.replace('client_champskin_', '').replace('_namelower', '')
                    if core.replace('_', '') in skin_label.replace('_', '').replace('-', ''):
                        matched_tr_skin = sk_v
                        break
            if not matched_tr_skin:
                matched_tr_skin = f"{owner_char} ({skin_label.replace('_', ' ').title()})"
            # Mevcut kostümlerde var mı kontrol et
            existing_nums = [num for num, s in char_meta[owner_char]['skins'].items() if s['name'] == matched_tr_skin]
            if existing_nums:
                skin_num = existing_nums[0]
            else:
                skin_num = len(char_meta[owner_char]['skins'])
                char_meta[owner_char]['skins'][skin_num] = {
                    'skin_num': skin_num,
                    'name': matched_tr_skin,
                    'is_base': False,
                    'splash_url': char_meta[owner_char]['splash_url'],
                    'voice_type': 'unique_vo',
                    'voice_badge': '✨ ÖZEL KOSTÜM DUBLAJI',
                    'voice_tag': 'Eşsiz Kostüm Sesi',
                    'voice_desc': f"{matched_tr_skin} kostümüne özel yeni Türkçe replikler.",
                    'is_unique': True
                }
            skin_display_name = matched_tr_skin

        # PersonalVO (ilk SoundEvent'ten önceki WEM'ler)
        personal_wems = []
        i = 0
        while i < len(tokens) and not tokens[i].startswith('SoundEvent:'):
            if tokens[i].startswith('VO_'):
                w = tokens[i]
                if fnv1_64_lor(w) in pck_map:
                    personal_wems.append(w)
                m_slug = re.match(r'^VO_([A-Za-z0-9]+?)_', w)
                if m_slug:
                    slug = m_slug.group(1)
                    if slug not in slug_to_char or (char_meta.get(owner_char, {}).get('is_champ') and not char_meta.get(slug_to_char[slug], {}).get('is_champ')):
                        slug_to_char[slug] = owner_char
            i += 1

        # GlobalVO bloklarını ayrıştır
        two_turn_blocks = []
        one_turn_blocks = []
        while i < len(tokens):
            tok = tokens[i]
            if tok == 'SoundEvent: Voiceover Event 1':
                w1 = []
                i += 1
                while i < len(tokens) and tokens[i].startswith('VO_'):
                    if fnv1_64_lor(tokens[i]) in pck_map:
                        w1.append(tokens[i])
                    i += 1
                w2 = []
                if i < len(tokens) and tokens[i] == 'SoundEvent: Voiceover Event 2':
                    i += 1
                    while i < len(tokens) and tokens[i].startswith('VO_'):
                        if fnv1_64_lor(tokens[i]) in pck_map:
                            w2.append(tokens[i])
                        i += 1
                other_code = None
                skin_guid = None
                while i < len(tokens) and not tokens[i].startswith('SoundEvent:') and not tokens[i].startswith('VO_'):
                    if re.match(r'^[0-9]{2}[A-Z]{2}[0-9]{3}', tokens[i]):
                        other_code = tokens[i]
                    elif '-' in tokens[i] and len(tokens[i]) == 36:
                        skin_guid = tokens[i].lower()
                    i += 1
                if w1 and w2 and other_code:
                    two_turn_blocks.append((w1, w2, other_code, skin_guid))
            elif tok == 'SoundEvent: Voiceover Event':
                w_list = []
                i += 1
                while i < len(tokens) and tokens[i].startswith('VO_'):
                    if fnv1_64_lor(tokens[i]) in pck_map:
                        w_list.append(tokens[i])
                    i += 1
                other_code = None
                skin_guid = None
                while i < len(tokens) and not tokens[i].startswith('SoundEvent:') and not tokens[i].startswith('VO_'):
                    if re.match(r'^[0-9]{2}[A-Z]{2}[0-9]{3}', tokens[i]):
                        other_code = tokens[i]
                    elif '-' in tokens[i] and len(tokens[i]) == 36:
                        skin_guid = tokens[i].lower()
                    i += 1
                if w_list:
                    one_turn_blocks.append((w_list, other_code, skin_guid))
            else:
                i += 1

        csp_parsed[cid] = {
            'cid': cid,
            'owner_char': owner_char,
            'primary_code': primary_code,
            'skin_num': skin_num,
            'skin_name': skin_display_name,
            'personal_wems': personal_wems,
            'two_turn_blocks': two_turn_blocks,
            'one_turn_blocks': one_turn_blocks
        }

    print(f"  ✓ 1.388 CardSoundProfile Çözüldü: {len(csp_parsed)} aktif ses profili")

    # 8. Her karakter için solo sesleri, tek yönlü etkileşimleri ve karşılıklı (2-turlu) diyalogları derle
    char_solo_wems = {}  # (char_name, skin_num) -> dict of raw_event_group -> list of (wem, target_char)
    pair_dialogue_chains = {}  # pair_key (sorted a__b) -> dict of chain_id -> chain_obj
    directed_interactions = {}  # (speaker_char, target_char, wem) -> item_dict

    def resolve_speaker_from_wem(wem_file: str, char_a: str, char_b: str) -> tuple:
        """2-turlu diyalogda hangi WEM'i kimin söylediğini kesin olarak belirler."""
        m = re.match(r'^VO_([A-Za-z0-9]+?)_', wem_file)
        if m:
            slug = m.group(1)
            if slug in slug_to_char:
                spk = slug_to_char[slug]
                if spk == char_a:
                    return char_a, char_b
                if spk == char_b:
                    return char_b, char_a
            s_low = slug.lower()
            a_clean = re.sub(r'[^a-z0-9]', '', char_a.lower())
            b_clean = re.sub(r'[^a-z0-9]', '', char_b.lower())
            if a_clean and a_clean in s_low:
                return char_a, char_b
            if b_clean and b_clean in s_low:
                return char_b, char_a
        return char_a, char_b

    for cid, pdata in csp_parsed.items():
        owner_char = pdata['owner_char']
        skin_num = pdata['skin_num']
        skin_name = pdata['skin_name']

        # A) PersonalVO
        for w in pdata['personal_wems']:
            base_ev = re.sub(r'_[0-9]{1,2}\.wem$', '', w, flags=re.IGNORECASE)
            char_solo_wems.setdefault((owner_char, skin_num), {}).setdefault(base_ev, [])
            if (w, "") not in char_solo_wems[(owner_char, skin_num)][base_ev]:
                char_solo_wems[(owner_char, skin_num)][base_ev].append((w, ""))

        # B) One-Turn GlobalVO (Zafer, Yenilgi, Süre veya Tek Yönlü Kart Tepkileri)
        for w_list, other_code, skin_guid in pdata['one_turn_blocks']:
            other_char = code_to_char_name.get(other_code, "") if other_code else ""
            if other_char == owner_char:
                other_char = ""
            for w in w_list:
                base_ev = re.sub(r'_[0-9]{1,2}\.wem$', '', w, flags=re.IGNORECASE)
                char_solo_wems.setdefault((owner_char, skin_num), {}).setdefault(base_ev, [])
                if (w, other_char) not in char_solo_wems[(owner_char, skin_num)][base_ev]:
                    char_solo_wems[(owner_char, skin_num)][base_ev].append((w, other_char))

                if other_char and other_char in char_meta:
                    tgt_skin_info = guid_to_skin.get(skin_guid) if skin_guid else None
                    tgt_skin_name = tgt_skin_info['skin_name'] if tgt_skin_info else f"Varsayılan {other_char}"
                    tgt_is_base = (tgt_skin_info is None)
                    spk_is_base = (skin_num == 0)
                    cat_id, base_act, act_label, _ = classify_wem_action(w, other_char)
                    directed_interactions[(owner_char, other_char, w)] = {
                        'speaker_champ': owner_char,
                        'target_champ': other_char,
                        'speaker_skin_num': skin_num,
                        'speaker_skin_name': skin_name,
                        'speaker_is_base': spk_is_base,
                        'target_skin_num': 0 if tgt_is_base else 1,
                        'target_skin_name': tgt_skin_name,
                        'target_is_base': tgt_is_base,
                        'matrix_type': (
                            'base_to_base' if (spk_is_base and tgt_is_base) else
                            'base_to_skin' if (spk_is_base and not tgt_is_base) else
                            'skin_to_base' if (not spk_is_base and tgt_is_base) else
                            'skin_to_skin'
                        ),
                        'action_type': act_label.split(' (')[0],
                        'base_action': base_act,
                        'raw_event': w,
                        'wem_id': w,
                        'transcript': comic_subtitles.get(w.replace('.wem', '').lower(), '')
                    }

        # C) Two-Turn GlobalVO (Karşılıklı İkili Diyaloglar: Event 1 -> Event 2)
        for w1_list, w2_list, other_code, skin_guid in pdata['two_turn_blocks']:
            other_char = code_to_char_name.get(other_code, "") if other_code else ""
            if not other_char or other_char not in char_meta or other_char == owner_char:
                continue

            spk1, tgt1 = resolve_speaker_from_wem(w1_list[0], owner_char, other_char)
            spk2, tgt2 = (other_char, owner_char) if spk1 == owner_char else (owner_char, other_char)

            is_enemy = '_enemy_' in w1_list[0].lower() or '_enemy_' in w2_list[0].lower()
            prox_label = "Düşman Karşılaşması" if is_enemy else "Dost Karşılaşması"

            tgt_skin_info = guid_to_skin.get(skin_guid) if skin_guid else None
            other_skin_name = tgt_skin_info['skin_name'] if tgt_skin_info else f"Varsayılan {other_char}"
            other_is_base = (tgt_skin_info is None)

            # Konuşmacıların kostüm bilgilerini eşle
            spk1_is_owner = (spk1 == owner_char)
            spk1_skin_num = skin_num if spk1_is_owner else (0 if other_is_base else 1)
            spk1_skin_name = skin_name if spk1_is_owner else other_skin_name
            spk1_is_base = (skin_num == 0) if spk1_is_owner else other_is_base

            spk2_skin_num = (0 if other_is_base else 1) if spk1_is_owner else skin_num
            spk2_skin_name = other_skin_name if spk1_is_owner else skin_name
            spk2_is_base = other_is_base if spk1_is_owner else (skin_num == 0)

            # Her iki adımı da hem solo seslere hem de yönlü etkileşim matrisine kaydet
            for w in w1_list:
                base_ev = re.sub(r'_[0-9]{1,2}\.wem$', '', w, flags=re.IGNORECASE)
                char_solo_wems.setdefault((spk1, spk1_skin_num if spk1_is_owner else 0), {}).setdefault(base_ev, [])
                if (w, tgt1) not in char_solo_wems[(spk1, spk1_skin_num if spk1_is_owner else 0)][base_ev]:
                    char_solo_wems[(spk1, spk1_skin_num if spk1_is_owner else 0)][base_ev].append((w, tgt1))

                directed_interactions[(spk1, tgt1, w)] = {
                    'speaker_champ': spk1,
                    'target_champ': tgt1,
                    'speaker_skin_num': spk1_skin_num,
                    'speaker_skin_name': spk1_skin_name,
                    'speaker_is_base': spk1_is_base,
                    'target_skin_num': spk2_skin_num,
                    'target_skin_name': spk2_skin_name,
                    'target_is_base': spk2_is_base,
                    'matrix_type': (
                        'base_to_base' if (spk1_is_base and spk2_is_base) else
                        'base_to_skin' if (spk1_is_base and not spk2_is_base) else
                        'skin_to_base' if (not spk1_is_base and spk2_is_base) else
                        'skin_to_skin'
                    ),
                    'action_type': f"{prox_label} (1. Söz - Başlatan)",
                    'base_action': 'karsilasma',
                    'raw_event': w,
                    'wem_id': w,
                    'transcript': comic_subtitles.get(w.replace('.wem', '').lower(), '')
                }

            for w in w2_list:
                base_ev = re.sub(r'_[0-9]{1,2}\.wem$', '', w, flags=re.IGNORECASE)
                char_solo_wems.setdefault((spk2, spk2_skin_num if not spk1_is_owner else 0), {}).setdefault(base_ev, [])
                if (w, tgt2) not in char_solo_wems[(spk2, spk2_skin_num if not spk1_is_owner else 0)][base_ev]:
                    char_solo_wems[(spk2, spk2_skin_num if not spk1_is_owner else 0)][base_ev].append((w, tgt2))

                directed_interactions[(spk2, tgt2, w)] = {
                    'speaker_champ': spk2,
                    'target_champ': tgt2,
                    'speaker_skin_num': spk2_skin_num,
                    'speaker_skin_name': spk2_skin_name,
                    'speaker_is_base': spk2_is_base,
                    'target_skin_num': spk1_skin_num,
                    'target_skin_name': spk1_skin_name,
                    'target_is_base': spk1_is_base,
                    'matrix_type': (
                        'base_to_base' if (spk2_is_base and spk1_is_base) else
                        'base_to_skin' if (spk2_is_base and not spk1_is_base) else
                        'skin_to_base' if (not spk2_is_base and spk1_is_base) else
                        'skin_to_skin'
                    ),
                    'action_type': f"{prox_label} (2. Söz - Yanıt)",
                    'base_action': 'karsilasma',
                    'raw_event': w,
                    'wem_id': w,
                    'transcript': comic_subtitles.get(w.replace('.wem', '').lower(), '')
                }

            # İkili diyalog zincirini kaydet
            first_c, second_c = sorted([owner_char, other_char], key=lambda x: x.lower())
            p_key = f"{first_c.lower()}__{second_c.lower()}"
            chain_sig = f"{w1_list[0]}__{w2_list[0]}"
            if chain_sig not in pair_dialogue_chains.setdefault(p_key, {}):
                turns = []
                for w in w1_list:
                    turns.append({
                        'step': 1,
                        'speaker_champ': spk1,
                        'speaker_skin_num': spk1_skin_num,
                        'speaker_skin_name': spk1_skin_name,
                        'speaker_splash_url': char_meta[spk1]['splash_url'],
                        'target_champ': tgt1,
                        'target_skin_num': spk2_skin_num,
                        'target_skin_name': spk2_skin_name,
                        'target_splash_url': char_meta[tgt1]['splash_url'],
                        'proximity': 'Far' if is_enemy else 'Near',
                        'raw_event': w,
                        'wem_id': w,
                        'transcript': comic_subtitles.get(w.replace('.wem', '').lower(), '')
                    })
                for w in w2_list:
                    turns.append({
                        'step': 2,
                        'speaker_champ': spk2,
                        'speaker_skin_num': spk2_skin_num,
                        'speaker_skin_name': spk2_skin_name,
                        'speaker_splash_url': char_meta[spk2]['splash_url'],
                        'target_champ': tgt2,
                        'target_skin_num': spk1_skin_num,
                        'target_skin_name': spk1_skin_name,
                        'target_splash_url': char_meta[tgt2]['splash_url'],
                        'proximity': 'Far' if is_enemy else 'Near',
                        'raw_event': w,
                        'wem_id': w,
                        'transcript': comic_subtitles.get(w.replace('.wem', '').lower(), '')
                    })

                skinA_name = spk1_skin_name if spk1 == first_c else spk2_skin_name
                skinB_name = spk2_skin_name if spk1 == first_c else spk1_skin_name
                skinA_num = spk1_skin_num if spk1 == first_c else spk2_skin_num
                skinB_num = spk2_skin_num if spk1 == first_c else spk1_skin_num

                idx_num = len(pair_dialogue_chains[p_key]) + 1
                pair_dialogue_chains[p_key][chain_sig] = {
                    'chain_id': f"lor_{first_c}_{second_c}_{idx_num}",
                    'topic_raw': w1_list[0].replace('.wem', ''),
                    'proximity': 'Far' if is_enemy else 'Near',
                    'group_id': 'enemy_arrival' if is_enemy else 'ally_arrival',
                    'group_title': f"🃏 {prox_label} Diyaloğu",
                    'title': f"{spk1} ➔ {spk2} ({prox_label} #{idx_num})",
                    'skinA_num': skinA_num,
                    'skinA_name': skinA_name,
                    'skinA_splash': char_meta[first_c]['splash_url'],
                    'skinB_num': skinB_num,
                    'skinB_name': skinB_name,
                    'skinB_splash': char_meta[second_c]['splash_url'],
                    'is_multi_turn': True,
                    'turn_count': len(turns),
                    'turns': turns
                }

    print(f"  ✓ Toplam Yönlü Atıf: {len(directed_interactions):,}, İkili Diyalog Çifti: {len(pair_dialogue_chains):,}")

    # 9. Şampiyonlar + Etkileşimli Takipçiler için lor_matrix_data.json oluştur
    # Önce kimin gelen/giden etkileşimi veya solo sesi var kontrol et
    incoming_by_char = {}
    outgoing_by_char = {}
    for (spk, tgt, w), item in directed_interactions.items():
        outgoing_by_char.setdefault(spk, []).append(item)
        incoming_by_char.setdefault(tgt, []).append(item)

    # Listeye tüm LoR şampiyonlarını + en az 1 ses/etkileşimi olan tüm takipçi karakterleri dahil et
    active_chars = []
    for cname, cmeta in char_meta.items():
        has_solo = (cname, 0) in char_solo_wems and len(char_solo_wems[(cname, 0)]) > 0
        has_inc = cname in incoming_by_char
        has_out = cname in outgoing_by_char
        if cmeta['is_champ'] or (has_solo and (has_inc or has_out)):
            active_chars.append(cname)

    # Şampiyonları öne, takipçileri etkileşim sayısına göre sırala
    active_chars.sort(key=lambda nm: (
        0 if char_meta[nm]['is_champ'] else 1,
        -(len(incoming_by_char.get(nm, [])) + len(outgoing_by_char.get(nm, []))),
        nm
    ))

    global_matrix = {'base_to_base': 0, 'base_to_skin': 0, 'skin_to_base': 0, 'skin_to_skin': 0}
    total_interactions_count = 0
    champions_list = []

    for cname in active_chars:
        cmeta = char_meta[cname]
        inc_items = incoming_by_char.get(cname, [])
        out_items = outgoing_by_char.get(cname, [])

        # Ref ID ata ve sırala
        inc_items.sort(key=lambda x: (x['speaker_champ'], x['raw_event']))
        out_items.sort(key=lambda x: (x['target_champ'], x['raw_event']))

        for idx, it in enumerate(inc_items, 1):
            it['ref_id'] = f"LOR-{cmeta['base_code']}-IN-{idx:03d}"
        for idx, it in enumerate(out_items, 1):
            it['ref_id'] = f"LOR-{cmeta['base_code']}-OUT-{idx:03d}"

        mat_in = {'base_to_base': 0, 'base_to_skin': 0, 'skin_to_base': 0, 'skin_to_skin': 0}
        act_in = {}
        spk_counts = {}
        for it in inc_items:
            mt = it['matrix_type']
            mat_in[mt] = mat_in.get(mt, 0) + 1
            at = it['action_type']
            act_in[at] = act_in.get(at, 0) + 1
            sc = it['speaker_champ']
            spk_counts[sc] = spk_counts.get(sc, 0) + 1

        mat_out = {'base_to_base': 0, 'base_to_skin': 0, 'skin_to_base': 0, 'skin_to_skin': 0}
        act_out = {}
        tgt_counts = {}
        for it in out_items:
            mt = it['matrix_type']
            mat_out[mt] = mat_out.get(mt, 0) + 1
            global_matrix[mt] = global_matrix.get(mt, 0) + 1
            total_interactions_count += 1
            at = it['action_type']
            act_out[at] = act_out.get(at, 0) + 1
            tc = it['target_champ']
            tgt_counts[tc] = tgt_counts.get(tc, 0) + 1

        top_speakers = [{'champion': k, 'count': v} for k, v in sorted(spk_counts.items(), key=lambda x: -x[1])[:15]]
        top_targets = [{'champion': k, 'count': v} for k, v in sorted(tgt_counts.items(), key=lambda x: -x[1])[:15]]

        champions_list.append({
            'name': cname,
            'id': cmeta['id'],
            'card_code': cmeta['base_code'],
            'is_champion': cmeta['is_champ'],
            'region': cmeta['region'],
            'icon_url': cmeta['icon_url'],
            'splash_url': cmeta['splash_url'],
            'total_incoming': len(inc_items),
            'total_outgoing': len(out_items),
            'unique_speakers_incoming': len(spk_counts),
            'unique_targets_outgoing': len(tgt_counts),
            'matrix_incoming': mat_in,
            'matrix_outgoing': mat_out,
            'actions_incoming': act_in,
            'actions_outgoing': act_out,
            'top_speakers': top_speakers,
            'top_targets': top_targets,
            'incoming_items': inc_items,
            'outgoing_items': out_items
        })

    lor_matrix_payload = {
        'metadata': {
            'game': 'lor',
            'title': 'Legends of Runeterra Ses & Diyalog Stüdyosu',
            'total_champions': len(champions_list),
            'Pure_champions_count': sum(1 for c in champions_list if c['is_champion']),
            'followers_count': sum(1 for c in champions_list if not c['is_champion']),
            'total_interactions': total_interactions_count,
            'global_matrix': global_matrix
        },
        'champions': champions_list
    }

    with open(LOR_MATRIX_OUT, 'w', encoding='utf-8') as f:
        json.dump(lor_matrix_payload, f, ensure_ascii=False)

    # 10. JIT Ses Sunucusu (/api/champion-voices ve /api/pair-interactions) için önbellek veritabanı oluştur
    voices_by_char = {}
    for (cname, s_num), ev_dict in char_solo_wems.items():
        if cname not in char_meta:
            continue
        voices_by_char.setdefault(cname, {})[str(s_num)] = {
            ev: [{'wem': w, 'target': t, 'transcript': comic_subtitles.get(w.replace('.wem', '').lower(), '')} for (w, t) in w_list]
            for ev, w_list in ev_dict.items()
        }

    serializable_pairs = {
        pk: list(chains_dict.values())
        for pk, chains_dict in pair_dialogue_chains.items()
    }

    full_db = {
        'char_meta': char_meta,
        'voices_by_char': voices_by_char,
        'pair_dialogues': serializable_pairs
    }
    with open(LOR_FULL_DB_OUT, 'w', encoding='utf-8') as f:
        json.dump(full_db, f, ensure_ascii=False)

    print(f"✅ LoR Veritabanı Başarıyla Üretildi ({time.time() - t0:.2f} sn)!")
    print(f"   • Toplam Karakter / Birim: {len(champions_list)} ({lor_matrix_payload['metadata']['Pure_champions_count']} Şampiyon + {lor_matrix_payload['metadata']['followers_count']} Etkileşimli Kart)")
    print(f"   • Toplam Atıf & Etkileşim: {total_interactions_count:,}")
    print(f"   • Kanon (B➔B) Atıf: {global_matrix['base_to_base']:,}")
    print(f"   • Karşılıklı Konuşan Çift Sayısı: {len(serializable_pairs):,}")


if __name__ == '__main__':
    main()
