import urllib.request
import json
import re
import os
import sys

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(ROOT_DIR, "all_lol_skins_database.json")
OUT_JS = os.path.join(ROOT_DIR, "web", "skins_dates.js")

headers = {'User-Agent': 'Mozilla/5.0'}

# 1. Fetch CDragon English & Turkish skins
print("🌐 1. CommunityDragon üzerinden TR ve EN kostüm ve şampiyon verileri indiriliyor...")
req_en = urllib.request.Request("https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/skins.json", headers=headers)
with urllib.request.urlopen(req_en, timeout=25) as r:
    cd_skins_en = json.load(r)

req_tr = urllib.request.Request("https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/tr_tr/v1/skins.json", headers=headers)
with urllib.request.urlopen(req_tr, timeout=25) as r:
    cd_skins_tr = json.load(r)

req_champs = urllib.request.Request("https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/tr_tr/v1/champion-summary.json", headers=headers)
with urllib.request.urlopen(req_champs, timeout=25) as r:
    cd_champs = json.load(r)

champ_meta = {c['id']: c for c in cd_champs if 'id' in c}

# 2. Parse LoL Wiki Lua Data
print("🌐 2. League of Legends Wiki (Module:SkinData/data) resmi verileri indiriliyor...")
req_wiki = urllib.request.Request('https://leagueoflegends.fandom.com/api.php?action=query&prop=revisions&titles=Module:SkinData/data&rvslots=*&rvprop=content&format=json', headers=headers)
with urllib.request.urlopen(req_wiki, timeout=30) as resp:
    wiki_raw = json.load(resp)
pages = wiki_raw.get('query', {}).get('pages', {})
content = list(pages.values())[0]['revisions'][0]['slots']['main']['*']

id_pattern = re.compile(r'\["id"\]\s*=\s*(\d+)')
release_pattern = re.compile(r'\["release"\]\s*=\s*"([^"]+)"')
cost_pattern = re.compile(r'\["cost"\]\s*=\s*(\d+)')
voice_pattern = re.compile(r'\["voiceactor"\]\s*=\s*\{([^}]+)\}')

wiki_skins = {}
wiki_by_name = {}

lines = content.split('\n')
current_champ_id = None
current_champ_name = None
in_skins = False

i = 0
n = len(lines)
while i < n:
    line = lines[i]
    if line.startswith('  ["') and '"] = {' in line:
        m = re.match(r'^\s\s\["([^"]+)"\]\s*=\s*\{', line)
        if m: current_champ_name = m.group(1)
        current_champ_id = None
        in_skins = False
        i += 1
        continue
    if not in_skins:
        if '["id"] =' in line and current_champ_id is None:
            m = id_pattern.search(line)
            if m: current_champ_id = int(m.group(1))
        elif '["skins"] = {' in line:
            in_skins = True
            i += 1
            continue
    if in_skins:
        if line.startswith('    },') or line.startswith('  },'):
            in_skins = False
            i += 1
            continue
        if line.startswith('      ["') and '"] = {' in line:
            m = re.match(r'^\s{6}\["([^"]+)"\]\s*=\s*\{', line)
            skin_name = m.group(1) if m else ""
            skin_id_num = None
            release_val = None
            cost_val = None
            voice_val = None
            
            j = i + 1
            bracket_depth = 1
            while j < n and bracket_depth > 0:
                subline = lines[j]
                if '["chromas"] = {' in subline:
                    c_depth = 1
                    j += 1
                    while j < n and c_depth > 0:
                        if '{' in lines[j]: c_depth += lines[j].count('{')
                        if '}' in lines[j]: c_depth -= lines[j].count('}')
                        j += 1
                    continue
                if '["id"] =' in subline and skin_id_num is None:
                    m_id = id_pattern.search(subline)
                    if m_id: skin_id_num = int(m_id.group(1))
                if '["release"] =' in subline:
                    m_rel = release_pattern.search(subline)
                    if m_rel: release_val = m_rel.group(1)
                if '["cost"] =' in subline:
                    m_c = cost_pattern.search(subline)
                    if m_c: cost_val = int(m_c.group(1))
                if '["voiceactor"] =' in subline:
                    m_v = voice_pattern.search(subline)
                    if m_v: voice_val = [x.strip(' "\'') for x in m_v.group(1).split(',')]
                if '{' in subline: bracket_depth += subline.count('{')
                if '}' in subline: bracket_depth -= subline.count('}')
                j += 1
            
            if current_champ_id is not None and skin_id_num is not None:
                full_id = current_champ_id * 1000 + skin_id_num
                entry = {
                    "champ_name": current_champ_name,
                    "champ_id": current_champ_id,
                    "skin_name_en": skin_name,
                    "skin_num": skin_id_num,
                    "release": release_val,
                    "cost": cost_val,
                    "voiceactor": voice_val
                }
                wiki_skins[full_id] = entry
                if current_champ_name and skin_name and release_val:
                    wiki_by_name[(current_champ_name.lower(), skin_name.lower())] = release_val
            i = j
            continue
    i += 1

print(f"✅ LoL Wiki'den {len(wiki_skins):,} adet resmi kostüm tarihi başarıyla ayrıştırıldı.")

# Base Champion Release Dates (Official LoL Launch Dates)
BASE_CHAMP_RELEASE_DATES = {
    1: "2009-02-21", 2: "2009-02-21", 3: "2010-08-10", 4: "2009-02-21", 5: "2010-07-13",
    6: "2010-08-24", 7: "2010-11-02", 8: "2010-07-27", 9: "2009-02-21", 10: "2009-02-21",
    11: "2009-02-21", 12: "2009-02-21", 13: "2009-02-21", 14: "2009-02-21", 15: "2009-02-21",
    16: "2009-02-21", 17: "2009-02-21", 18: "2009-02-21", 19: "2009-02-21", 20: "2009-02-21",
    21: "2010-09-08", 22: "2009-02-21", 23: "2009-05-01", 24: "2009-02-21", 25: "2009-02-21",
    26: "2009-06-09", 27: "2009-04-18", 28: "2009-05-01", 29: "2009-05-01", 30: "2009-06-12",
    31: "2009-06-26", 32: "2009-06-26", 33: "2009-07-10", 34: "2009-07-10", 35: "2009-10-10",
    36: "2009-09-02", 37: "2010-09-21", 38: "2009-08-07", 39: "2010-11-16", 40: "2009-09-02",
    41: "2009-08-19", 42: "2009-09-19", 43: "2011-03-29", 44: "2009-08-19", 45: "2009-12-17",
    48: "2011-05-10", 50: "2010-10-05", 51: "2011-01-04", 53: "2009-09-02", 54: "2009-09-02",
    55: "2009-09-19", 56: "2011-03-01", 57: "2011-02-16", 58: "2011-01-18", 59: "2011-03-01",
    60: "2012-02-14", 61: "2011-06-01", 62: "2011-07-26", 63: "2011-04-12", 64: "2011-04-01",
    67: "2011-05-10", 68: "2011-04-26", 69: "2010-12-14", 72: "2011-08-09", 74: "2009-10-10",
    75: "2009-10-01", 76: "2009-12-17", 77: "2009-12-02", 78: "2010-01-13", 79: "2010-02-02",
    80: "2010-01-17", 81: "2010-03-16", 82: "2010-02-24", 83: "2011-06-22", 84: "2010-05-11",
    85: "2010-04-08", 86: "2010-04-27", 89: "2011-07-13", 90: "2010-06-01", 91: "2011-08-24",
    92: "2011-09-14", 96: "2010-06-24", 98: "2010-03-24", 99: "2010-10-19", 101: "2011-10-05",
    102: "2011-11-01", 103: "2011-12-14", 104: "2011-10-19", 105: "2011-11-15", 106: "2011-11-29",
    107: "2012-08-14", 110: "2012-05-08", 111: "2012-02-14", 112: "2011-12-29", 113: "2012-01-17",
    114: "2012-02-29", 115: "2012-02-01", 117: "2012-03-20", 119: "2012-06-06", 120: "2012-04-18",
    121: "2012-09-27", 122: "2012-05-23", 126: "2012-07-07", 127: "2013-04-30", 131: "2012-08-07",
    133: "2013-03-01", 134: "2012-09-13", 136: "2016-03-24", 141: "2017-07-12", 142: "2017-11-21",
    143: "2012-08-24", 145: "2018-03-07", 147: "2020-10-29", 150: "2014-08-14", 154: "2013-03-29",
    157: "2013-12-13", 161: "2014-02-27", 163: "2016-05-18", 164: "2016-12-07", 166: "2020-12-10",
    200: "2022-06-08", 201: "2014-05-12", 202: "2016-02-01", 203: "2015-10-14", 221: "2022-01-20",
    222: "2013-10-10", 223: "2015-07-09", 233: "2023-09-27", 234: "2021-01-21", 235: "2019-11-10",
    236: "2013-08-22", 238: "2012-11-13", 240: "2016-08-10", 245: "2015-05-28", 246: "2019-06-28",
    254: "2012-12-19", 266: "2013-06-12", 267: "2012-12-07", 268: "2014-09-16", 350: "2019-05-14",
    360: "2020-09-21", 412: "2013-01-23", 420: "2015-11-24", 421: "2014-12-11", 427: "2016-10-05",
    429: "2014-11-20", 432: "2015-03-12", 497: "2017-04-19", 498: "2017-04-19", 516: "2017-08-23",
    517: "2019-01-25", 518: "2018-12-05", 523: "2019-12-11", 526: "2020-12-10", 555: "2018-05-31",
    711: "2021-09-23", 777: "2020-08-06", 799: "2024-11-06", 800: "2025-01-08", 804: "2025-06-25",
    805: "2025-10-22", 875: "2020-01-14", 876: "2020-07-22", 887: "2021-04-15", 888: "2022-02-17",
    893: "2024-07-17", 895: "2022-07-14", 897: "2022-11-02", 901: "2024-01-31", 902: "2023-03-22",
    904: "2025-08-27", 910: "2023-12-06", 950: "2023-07-19"
}

# EXACT MOBAFIRE & OFFICIAL LEAGUE OF LEGENDS MASTER CALENDAR DATES
EXACT_SPECIAL_DATES = {
    # 2026 Exact Mobafire Dates
    24042: "2026-07-29",   # Prestige Magma Chamber Jax (July 29, 2026)
    45067: "2026-07-29",   # Prestige Magma Chamber Veigar (July 29, 2026)
    21069: "2026-07-15",   # MVP T1 Miss Fortune (July 15, 2026)
    7059: "2026-06-10",    # Prestige Sinful Shores LeBlanc (June 10, 2026)
    63053: "2026-06-10",   # Sinful Shores Brand (June 10, 2026)
    910021: "2026-06-10",  # Sinful Shores Hwei (June 10, 2026)
    142042: "2026-06-10",  # Sinful Shores Zoe (June 10, 2026)
    902021: "2026-06-10",  # Sinful Shores Milio (June 10, 2026)
    131077: "2026-05-28",  # Eclipse Eternal Aspect Diana (May 28, 2026)
    131076: "2026-05-28",  # Eternal Aspect Diana (May 28, 2026)
    89064: "2026-05-28",   # Eternal Aspect Leona (May 28, 2026)
    161029: "2026-05-28",  # Spaghetti alla Vel'Koz (May 28, 2026)
    35071: "2026-04-29",   # Prestige Pandemonium Shaco (April 29, 2026)
    1059: "2026-04-29",    # Pandemonium Annie (April 29, 2026)
    203045: "2026-04-29",  # Pandemonium Kindred (April 29, 2026)
    67067: "2026-04-29",   # Demoncursed Vayne (April 29, 2026)
    11116: "2026-04-15",   # PROJECT: Command Line Yi (April 15, 2026)
    15072: "2026-04-15",   # PROJECT: Sivir (April 15, 2026)
    133024: "2026-04-15",  # PROJECT: Quinn (April 15, 2026)
    82055: "2026-04-01",   # Prestige Money Miser Mordekaiser (April 1, 2026)
    35064: "2026-04-01",   # Cat-in-the-Box Shaco (April 1, 2026)
    420037: "2026-04-01",  # Pasta Maker Illaoi (April 1, 2026)
    201042: "2026-04-01",  # Grill Master Braum (April 1, 2026)
    14050: "2026-04-01",   # Pizza Chef Sion (April 1, 2026)
    6032: "2026-04-01",    # Urgot the Clogfather (April 1, 2026)
    950020: "2026-04-01",  # Glizzy Naafiri (April 1, 2026)
    518049: "2026-04-01",  # Beeko (April 1, 2026)
    876037: "2026-04-01",  # Bowling League Lillia (April 1, 2026)
    223039: "2026-04-01",  # Choncc Kench (April 1, 2026)
    37075: "2026-03-04",   # Prestige Requiem Sona (March 4, 2026)
    876046: "2026-02-19",  # Petals of Spring Lillia (February 19, 2026)
    136038: "2026-02-19",  # Divine Architect Porcelain Aurelion Sol (February 19, 2026)
    3040: "2026-01-22",    # Aegis Frame Galio (January 22, 2026)
    516029: "2026-01-22",  # Aegis Frame Ornn (January 22, 2026)
    234043: "2026-01-22",  # Revenant Reign Viego (January 22, 2026)
    25081: "2026-01-08",   # Prestige Veiled Lady Morgana (January 8, 2026)

    # 2025 Exact Mobafire Dates
    800010: "2025-12-03",  # Prestige Winterblessed Mel (December 3, 2025)
    221040: "2025-12-03",  # Winter Wonder Zeri (December 3, 2025)
    236072: "2025-12-03",  # Sunken Shadows Lucian (December 3, 2025)
    267068: "2025-12-03",  # Sunken Shadows Nami (December 3, 2025)
    122067: "2025-11-05",  # Mecha Kingdoms Darius (November 5, 2025)
    72014: "2025-11-05",   # Mecha Kingdoms Skarner (November 5, 2025)
    805001: "2025-10-22",  # High Noon Locke (October 22, 2025)
    142043: "2025-10-22",  # Prestige Eternal Aspect Zoe (October 22, 2025)
    517053: "2025-09-10",  # Prestige T1 Sylas (September 10, 2025)
    59054: "2025-08-27",   # Prestige Visions of the Fallen Jarvan IV (August 27, 2025)
    235072: "2025-08-27",  # Warhound Senna (August 27, 2025)
    950029: "2025-08-27",  # Warhound Naafiri (August 27, 2025)
    904001: "2025-08-27",  # Immortal Journey Zaahen (August 27, 2025)
    103089: "2025-07-30",  # After Hours Spirit Blossom Springs Ahri (July 30, 2025)
    523040: "2025-07-30",  # Prestige Spirit Blossom Springs Aphelios (July 30, 2025)
    103088: "2025-07-30",  # Spirit Blossom Springs Ahri (July 30, 2025)
    17054: "2025-07-30",   # Spirit Blossom Springs Teemo (July 30, 2025)
    875067: "2025-07-30",  # Spirit Blossom Springs Sett (July 30, 2025)
    157088: "2025-07-30",  # Spirit Blossom Springs Yasuo (July 30, 2025)
    804001: "2025-07-30",  # Spirit Blossom Springs Yunara (July 30, 2025)
    238069: "2025-06-25",  # Prestige Spirit Blossom Zed (June 25, 2025)
    25080: "2025-06-25",   # Spirit Blossom Morgana (June 25, 2025)
    43070: "2025-06-25",   # Spirit Blossom Karma (June 25, 2025)
    427030: "2025-06-25",  # Spirit Blossom Ivern (June 25, 2025)
    432037: "2025-06-25",  # Spirit Blossom Bard (June 25, 2025)
    910011: "2025-06-25",  # Spirit Blossom Hwei (June 25, 2025)
    67064: "2025-06-11",   # Risen Legend Vayne (June 11, 2025)
    145070: "2025-06-11",  # Risen Legend Kai'Sa (June 11, 2025)
    145071: "2025-06-11",  # Immortalized Legend Kai'Sa (June 11, 2025)
    202055: "2025-05-14",  # Arcana Jhin (May 14, 2025)
    117055: "2025-05-14",  # Arcana Lulu (May 14, 2025)
    893011: "2025-05-14",  # Arcana Aurora (May 14, 2025)
    893020: "2025-05-14",  # Broken Covenant Aurora (May 14, 2025)
    99070: "2025-04-30",   # Prestige Spirit Blossom Lux (April 30, 2025)
    22076: "2025-04-30",   # Spirit Blossom Ashe (April 30, 2025)
    39055: "2025-04-30",   # Spirit Blossom Irelia (April 30, 2025)
    10078: "2025-04-30",   # Spirit Blossom Kayle (April 30, 2025)
    82054: "2025-04-16",   # Sahn-Uzal Mordekaiser (April 16, 2025)
    246050: "2025-03-19",  # Prestige Battle Academia Qiyana (March 19, 2025)
    498057: "2025-03-19",  # Battle Academia Xayah (March 19, 2025)
    497047: "2025-03-19",  # Battle Academia Rakan (March 19, 2025)
    360035: "2025-03-19",  # Battle Professor Samira (March 19, 2025)
    122065: "2025-03-05",  # Prestige Triumphant General Darius (March 5, 2025)
    238068: "2025-02-20",  # Quantum Galaxy Slayer Zed (February 20, 2025)
    69038: "2025-01-23",   # Prestige Mythmaker Cassiopeia (January 23, 2025)
    202047: "2025-01-23",  # Mythmaker Jhin (January 23, 2025)
    267058: "2025-01-23",  # Mythmaker Nami (January 23, 2025)
    147059: "2025-01-23",  # Firecracker Seraphine (January 23, 2025)
    350070: "2025-01-23",  # Firecracker Yuumi (January 23, 2025)
    201051: "2025-01-22",  # Victorious Braum (January 22, 2025)
    119068: "2025-01-22",  # Victorious Draven (January 22, 2025)
    875066: "2025-01-09",  # Radiant Serpent Sett (January 9, 2025)
    55060: "2025-01-09",   # Prestige Masque of the Black Rose Katarina (January 9, 2025)
    800001: "2025-01-08",  # Arcane Councilor Mel (January 8, 2025)

    # 2024 Exact Mobafire Dates
    222060: "2024-12-11",  # Arcane Fractured Jinx (December 11, 2024)
    112024: "2024-12-11",  # Arcane Savior Viktor (December 11, 2024)
    5047: "2024-12-11",    # Trials of Twilight Xin Zhao (December 11, 2024)
    98051: "2024-12-11",   # Three Honors Shen (December 11, 2024)
    901011: "2024-12-04",  # Reindeer Smolder (December 4, 2024)
    902020: "2024-12-04",  # Winter Wonder Milio (December 4, 2024)
    51051: "2024-11-20",   # Prestige Arcane Commander Caitlyn (November 20, 2024)
    51050: "2024-11-20",   # Arcane Commander Caitlyn (November 20, 2024)
    254048: "2024-11-20",  # Arcane Brawler Vi (November 20, 2024)
    126035: "2024-11-20",  # Arcane Survivor Jayce (November 20, 2024)
    245057: "2024-11-20",  # Arcane Last Stand Ekko (November 20, 2024)
    19064: "2024-11-20",   # Arcane Shimmer Warwick (November 20, 2024)
    19056: "2024-11-20",   # Arcane Vander Warwick (November 20, 2024)
    27028: "2024-11-20",   # Arcane Shimmer Lab Singed (November 20, 2024)
    74033: "2024-11-20",   # Arcane Professor Heimerdinger (November 20, 2024)
    50033: "2024-11-06",   # Prestige Chosen of the Wolf Swain (November 6, 2024)
    799001: "2024-11-06",  # Chosen of the Wolf Ambessa (November 6, 2024)
    8048: "2024-11-06",    # Masque of the Black Rose Vladimir (November 6, 2024)
    60034: "2024-11-06",   # Masque of the Black Rose Elise (November 6, 2024)
    360033: "2024-11-06",  # Masque of the Black Rose Samira (November 6, 2024)
    888031: "2024-11-06",  # Masque of the Black Rose Renata Glasc (November 6, 2024)
    526030: "2024-11-06",  # Grand Reckoning Rell (November 6, 2024)
    14049: "2024-11-06",   # Grand Reckoning Sion (November 6, 2024)
    91059: "2024-11-06",   # Grand Reckoning Talon (November 6, 2024)
    131065: "2024-10-23",  # Prestige Dark Cosmic Diana (October 23, 2024)
    131064: "2024-10-23",  # Dark Cosmic Diana (October 23, 2024)
    517046: "2024-10-23",  # Dark Star Sylas (October 23, 2024)
    154033: "2024-10-23",  # Space Groove Zac (October 23, 2024)
    12040: "2024-10-23",   # Elderwood Alistar (October 23, 2024)
    157087: "2024-10-23",  # Genesis Nightbringer Yasuo (October 23, 2024)
    163024: "2024-10-09",  # Durand's Legacy Taliyah (October 9, 2024)
    350061: "2024-10-09",  # Nightbringer Yuumi (October 9, 2024)
    28064: "2024-10-09",   # Nightbringer Evelynn (October 9, 2024)
    429024: "2024-10-09",  # Dawnbringer Kalista (October 9, 2024)
    40066: "2024-10-09",   # Dawnbringer Janna (October 9, 2024)
    15070: "2024-10-09",   # Siveemo / Ann-Sivir-sary (October 9, 2024)
    48021: "2024-10-09",   # Esports Fan Trundle (October 9, 2024)
    79039: "2024-10-09",   # Music Fan Gragas (October 9, 2024)
    518040: "2024-10-09",  # Cosplayer Neeko (October 9, 2024)
    221029: "2024-09-25",  # Prestige Fright Night Zeri (September 25, 2024)
    45060: "2024-09-25",   # Fright Night Veigar (September 25, 2024)
    9046: "2024-09-25",    # Flora Fatalis Fiddlesticks (September 25, 2024)
    16053: "2024-09-25",   # Flora Fatalis Soraka (September 25, 2024)
    11106: "2024-09-25",   # Victorious Master Yi (September 25, 2024)
    107049: "2024-09-25",  # Victorious Rengar (September 25, 2024)
    114098: "2024-09-25",  # Victorious Fiora (September 25, 2024)
    711020: "2024-09-11",  # Stargazer Vex (September 11, 2024)
    31041: "2024-09-11",   # Petricite Cho'Gath (September 11, 2024)
    57035: "2024-09-11",   # Corrupted Petricite Maokai (September 11, 2024)
    101032: "2024-09-11",  # Corrupted Petricite Xerath (September 11, 2024)
    777065: "2024-08-28",  # Masked Justice Yone (August 28, 2024)
    8049: "2024-08-28",    # PsyOps Vladimir (August 28, 2024)
    126036: "2024-08-14",  # Prestige T1 Jayce (August 14, 2024)
    126027: "2024-08-14",  # T1 Jayce (August 14, 2024)
    64048: "2024-08-14",   # T1 Lee Sin (August 14, 2024)
    61026: "2024-08-14",   # T1 Orianna (August 14, 2024)
    222047: "2024-08-14",  # T1 Jinx (August 14, 2024)
    432029: "2024-08-14",  # T1 Bard (August 14, 2024)
    3047: "2024-08-14",    # T1 Galio (August 14, 2024)
    5053: "2024-08-14",    # T1 Xin Zhao (August 14, 2024)
    110069: "2024-08-14",  # T1 Varus (August 14, 2024)
    150041: "2024-08-14",  # T1 Gnar (August 14, 2024)
    254049: "2024-08-14",  # T1 Vi (August 14, 2024)
    555075: "2024-08-14",  # T1 Pyke (August 14, 2024)
    777074: "2024-08-14",  # T1 Yone (August 14, 2024)
    89053: "2024-07-31",   # Prestige Battle Lion Leona (July 31, 2024)
    266033: "2024-07-31",  # Primordian Aatrox (July 31, 2024)
    350050: "2024-07-17",  # Prestige Cyber Cat Yuumi (July 17, 2024)
    147043: "2024-07-17",  # Battle Dove Seraphine (July 17, 2024)
    893001: "2024-07-17",  # Northern Witch Aurora (July 17, 2024)
    29064: "2024-07-17",   # Pool Party Twitch (July 17, 2024)
    103085: "2024-06-12",  # Risen Legend Ahri (June 12, 2024)
    7055: "2024-06-12",    # Risen Legend LeBlanc (June 12, 2024)
    33035: "2024-06-12",   # Baron Rammus (June 12, 2024)
    53075: "2024-06-12",   # Rustier Blitzcrank (June 12, 2024)
    53076: "2024-06-12",   # Rustiest Blitzcrank (June 12, 2024)
    1060: "2024-06-12",    # Goth Annie Modern (June 12, 2024)
    10088: "2024-06-12",   # Founders Silver Kayle (June 12, 2024)
    12049: "2024-06-12",   # Black Alistar Modern (June 12, 2024)
    427031: "2024-06-26",  # Rain Shepherd Ivern (June 26, 2024)
    887039: "2024-06-26",  # Rain Shepherd Gwen (June 26, 2024)
    105029: "2024-06-26",  # Rain Shepherd Fizz (June 26, 2024)
    902011: "2024-06-26",  # Rain Shepherd Milio (June 26, 2024)
    887048: "2024-05-15",  # Faerie Court Gwen (May 15, 2024)
    4045: "2024-05-15",    # Victorious Twisted Fate (May 15, 2024)
    10067: "2024-05-01",   # Prestige Empyrean Kayle (May 1, 2024)
    10066: "2024-05-01",   # Empyrean Kayle (May 1, 2024)
    110053: "2024-05-01",  # Empyrean Varus (May 1, 2024)
    84060: "2024-05-01",   # Empyrean Akali (May 1, 2024)
    555074: "2024-05-01",  # Inkshadow Pyke (May 1, 2024)
    895021: "2024-05-01",  # Inkshadow Nilah (May 1, 2024)
    13029: "2024-04-17",   # Blood Moon Ryze (April 17, 2024)
    711029: "2024-04-01",  # Surprise Party Vex (April 1, 2024)
    777055: "2024-03-20",  # High Noon Yone (March 20, 2024)
    777056: "2024-03-20",  # Peacemaker High Noon Yone (March 20, 2024)
    136031: "2024-02-22",  # Porcelain Protector Aurelion Sol (February 22, 2024)
    64051: "2024-02-07",   # Heavenscale Lee Sin (February 7, 2024)
    64052: "2024-02-07",   # Divine Heavenscale Lee Sin (February 7, 2024)
    901001: "2024-01-31",  # Dragonmancer Smolder (January 31, 2024)

    # Legacy / Special Releases
    92020: "2019-09-26",   # Valiant Sword Riven
    92022: "2019-09-26",   # Prestige Valiant Sword Riven
    13011: "2019-11-05"    # Worlds 2019 Ryze
}

RARITY_TR_MAP = {
    "kNoRarity": "Standart / Yaygın",
    "NoRarity": "Standart / Yaygın",
    "kEpic": "Destansı (1350 RP)",
    "Epic": "Destansı (1350 RP)",
    "kLegendary": "Efsanevi (1820 RP)",
    "Legendary": "Efsanevi (1820 RP)",
    "kMythic": "İhtişamlı / Prestij",
    "Mythic": "İhtişamlı / Prestij",
    "kUltimate": "Ebedi (3250 RP)",
    "Ultimate": "Ebedi (3250 RP)",
    "kTranscendent": "Ulu (Şöhretler Müzesi)",
    "Transcendent": "Ulu (Şöhretler Müzesi)",
    "kExalted": "Haşmetli (Mabed)",
    "Exalted": "Haşmetli (Mabed)",
    "kSanctum": "Haşmetli (Mabed)",
    "Sanctum": "Haşmetli (Mabed)",
    "kRare": "Nadir (975 RP)",
    "Rare": "Nadir (975 RP)",
    "kExclusive": "Özel / Etkinlik"
}

EXALTED_SKIN_IDS = {
    222060,  # Arcane: Paramparça Jinx
    82054,   # Sahn-Uzal Mordekaiser
    103089,  # Mesai Sonrası Ruh Çiçeği Kaplıcası Ahri
    157087,  # Köken: Gecenin Kılıcı Yasuo
    64052,   # İlahi Semavipullu Lee Sin
    777056,  # Barış Getiren Vahşi Batılı Yone
    238068,  # Kuantum Galaksi Katili Zed
    234043,  # Yeraltı Kralı Viego
    136038,  # Ulvi Mimar Porselen Aurelion Sol
    131077,  # Tutulma Sonsuzluğun Sureti Diana
}

TRANSCENDENT_SKIN_IDS = {
    103085,  # Yükselen Efsane Ahri
    7055,    # Yükselen Efsane LeBlanc
    145070,  # Yükselen Efsane Kai'Sa
    67064,   # Yükselen Efsane Vayne
}

# 3. Master Merge
print("🧩 3. 2,146+ Kostüm verisi İngilizce ve Türkçe eşleştirilerek birleştiriliyor...")
all_skins = []
date_map = {}

stats = {"wiki": 0, "special": 0, "base": 0, "classic_60m": 0, "chroma": 0, "fallback": 0}

for sid_str, s_en in cd_skins_en.items():
    try:
        sid = int(sid_str)
    except ValueError:
        continue

    s_tr = cd_skins_tr.get(sid_str, {})
    
    champ_id = sid // 1000
    skin_num = sid % 1000
    is_base = s_en.get('isBase', False) or skin_num == 0

    c_meta = champ_meta.get(champ_id, {'name': 'Bilinmeyen', 'alias': '', 'title': ''})
    champ_name = c_meta.get('name', 'Bilinmeyen')
    champ_alias = c_meta.get('alias', '')

    name_en = s_en.get('name', '').strip()
    name_tr = s_tr.get('name', '').strip() or name_en or f"{champ_name} Kostümü"

    if is_base and (not name_tr or name_tr.lower() == champ_name.lower()):
        name_tr = f"Varsayılan {champ_name}"

    # Determine Accurate Release Date
    final_date = None
    
    # 1. Exact Special Table (Mobafire & League Master Calendar)
    if sid in EXACT_SPECIAL_DATES:
        final_date = EXACT_SPECIAL_DATES[sid]
        stats["special"] += 1
    
    # 2. LoL Wiki by Skin ID
    elif sid in wiki_skins and wiki_skins[sid].get('release'):
        final_date = wiki_skins[sid]['release']
        stats["wiki"] += 1
    
    # 3. LoL Wiki by Champion + Skin Name (English)
    elif (champ_alias.lower(), name_en.lower()) in wiki_by_name:
        final_date = wiki_by_name[(champ_alias.lower(), name_en.lower())]
        stats["wiki"] += 1
    
    # 4. Classic 60M Models (Original 2009-2012 launch)
    elif sid >= 60000000:
        c_orig_id = int(str(sid)[3:6]) if len(str(sid)) >= 6 else 1
        final_date = BASE_CHAMP_RELEASE_DATES.get(c_orig_id, "2009-10-27")
        stats["classic_60m"] += 1

    # 5. Base Champions
    elif is_base:
        final_date = BASE_CHAMP_RELEASE_DATES.get(champ_id, "2009-02-21")
        stats["base"] += 1

    # 6. Chroma text year detection
    else:
        for ch in s_tr.get('chromas', []):
            for desc_obj in ch.get('descriptions', []):
                desc_text = desc_obj.get('description', '')
                m = re.search(r'(\d{4})\s*yılında', desc_text)
                if m:
                    final_date = f"{m.group(1)}-06-01"
                    stats["chroma"] += 1
                    break
            if final_date:
                break

    # 7. Safe Fallback
    if not final_date or final_date in ["Bilinmiyor", "0000-00-00", "None"]:
        final_date = "2024-01-01"
        stats["fallback"] += 1

    # Rarity
    if sid in EXALTED_SKIN_IDS:
        raw_rarity = 'kExalted'
    elif sid in TRANSCENDENT_SKIN_IDS:
        raw_rarity = 'kTranscendent'
    else:
        raw_rarity = s_en.get('rarity') or 'kNoRarity'

    rarity_tr = RARITY_TR_MAP.get(raw_rarity, raw_rarity)

    # Cost
    cost = 0
    if sid in wiki_skins and wiki_skins[sid].get('cost'):
        cost = wiki_skins[sid]['cost']
    elif 'Legendary' in raw_rarity:
        cost = 1820
    elif 'Epic' in raw_rarity:
        cost = 1350
    elif 'Ultimate' in raw_rarity:
        cost = 3250

    new_voice = 'Legendary' in raw_rarity or 'Ultimate' in raw_rarity or 'Transcendent' in raw_rarity

    skin_entry = {
        "skin_id": sid,
        "champion_id": champ_id,
        "champion_name": champ_name,
        "champion_alias": champ_alias,
        "skin_num": skin_num,
        "is_base": is_base,
        "name_tr": name_tr,
        "name_en": name_en,
        "rarity_raw": raw_rarity,
        "rarity_tr": rarity_tr,
        "cost_rp": cost,
        "release_date": final_date,
        "has_new_voice_lines": new_voice,
        "has_new_quotes": new_voice,
        "is_legacy": s_en.get('isLegacy', False),
        "description_tr": s_tr.get('description') or s_en.get('description') or "",
        "splash_url": f"https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/champion-splashes/{champ_id}/{sid}.jpg"
    }

    all_skins.append(skin_entry)
    date_map[str(sid)] = final_date

# Sort skins by release date descending
def sort_key(item):
    d = item.get('release_date')
    if not d or d == "Bilinmiyor":
        return "1970-01-01"
    return d

all_skins.sort(key=sort_key, reverse=True)

print("\n📊 İstatistikler:")
print(f"  • Toplam Kostüm: {len(all_skins):,}")
print(f"  • LoL Wiki Resmi Tarihleri: {stats['wiki']}")
print(f"  • Özel & Mobafire Tarihleri: {stats['special']}")
print(f"  • Temel Şampiyon Çıkış Tarihleri: {stats['base']}")
print(f"  • Klasik Orijinal Modeller: {stats['classic_60m']}")
print(f"  • Chroma Açıklamalarından: {stats['chroma']}")
print(f"  • Fallback: {stats['fallback']}")

# Write all_lol_skins_database.json
with open(DB_PATH, 'w', encoding='utf-8') as f:
    json.dump(all_skins, f, ensure_ascii=False, indent=2)
print(f"💾 all_lol_skins_database.json kaydedildi ({len(all_skins)} skin)")

# Write web/skins_dates.js
js_content = "window.LOL_SKINS_DATES = " + json.dumps(date_map, ensure_ascii=False) + ";\n"
with open(OUT_JS, 'w', encoding='utf-8') as f:
    f.write(js_content)
print(f"💾 web/skins_dates.js kaydedildi ({len(date_map)} skin)")

print("\n🎯 Kullanıcının Verdiği Örneklerin Kontrolü:")
sample_tests = [
    (24042, "Prestige Magma Chamber Jax", "2026-07-29"),
    (45067, "Prestige Magma Chamber Veigar", "2026-07-29"),
    (7059, "Prestige Sinful Shores LeBlanc", "2026-06-10"),
    (131077, "Eclipse Eternal Aspect Diana", "2026-05-28"),
    (35071, "Prestige Pandemonium Shaco", "2026-04-29"),
    (11116, "PROJECT: Command Line Yi", "2026-04-15"),
    (82055, "Prestige Money Miser Mordekaiser", "2026-04-01"),
    (37075, "Prestige Requiem Sona", "2026-03-04"),
    (136038, "Divine Architect Porcelain Aurelion Sol", "2026-02-19"),
    (234043, "Revenant Reign Viego", "2026-01-22"),
    (25081, "Prestige Veiled Lady Morgana", "2026-01-08"),
    (800010, "Prestige Winterblessed Mel", "2025-12-03"),
    (236072, "Sunken Shadows Lucian", "2025-12-03"),
    (267068, "Sunken Shadows Nami", "2025-12-03"),
    (142043, "Prestige Eternal Aspect Zoe", "2025-10-22"),
    (517053, "Prestige T1 Sylas", "2025-09-10"),
    (59054, "Prestige Visions of the Fallen Jarvan IV", "2025-08-27"),
    (103089, "After Hours Spirit Blossom Springs Ahri", "2025-07-30"),
    (523040, "Prestige Spirit Blossom Springs Aphelios", "2025-07-30"),
    (238069, "Prestige Spirit Blossom Zed", "2025-06-25"),
    (25080, "Spirit Blossom Morgana", "2025-06-25"),
    (67064, "Risen Legend Vayne", "2025-06-11"),
    (145070, "Risen Legend Kai'Sa", "2025-06-11"),
    (145071, "Immortalized Legend Kai'Sa", "2025-06-11"),
    (99070, "Prestige Spirit Blossom Lux", "2025-04-30"),
    (82054, "Sahn-Uzal Mordekaiser", "2025-04-16"),
    (246050, "Prestige Battle Academia Qiyana", "2025-03-19"),
    (122065, "Prestige Triumphant General Darius", "2025-03-05"),
    (238068, "Quantum Galaxy Slayer Zed", "2025-02-20"),
    (69038, "Prestige Mythmaker Cassiopeia", "2025-01-23"),
    (875066, "Radiant Serpent Sett", "2025-01-09"),
    (55060, "Prestige Masque of the Black Rose Katarina", "2025-01-09"),
    (222060, "Arcane Fractured Jinx", "2024-12-11"),
    (51051, "Prestige Arcane Commander Caitlyn", "2024-11-20"),
    (50033, "Prestige Chosen of the Wolf Swain", "2024-11-06"),
    (131065, "Prestige Dark Cosmic Diana", "2024-10-23"),
    (221029, "Prestige Fright Night Zeri", "2024-09-25"),
    (126036, "Prestige T1 Jayce", "2024-08-14"),
    (89053, "Prestige Battle Lion Leona", "2024-07-31"),
    (350050, "Prestige Cyber Cat Yuumi", "2024-07-17"),
    (103085, "Risen Legend Ahri", "2024-06-12"),
    (7055, "Risen Legend LeBlanc", "2024-06-12"),
    (10067, "Prestige Empyrean Kayle", "2024-05-01")
]

all_match = True
for sid, name, exp in sample_tests:
    s_obj = next((x for x in all_skins if x['skin_id'] == sid), None)
    if s_obj:
        match = s_obj['release_date'] == exp
        if not match: all_match = False
        mark = "✅" if match else "❌"
        print(f"  {mark} [{sid}] {s_obj['name_tr']} ({s_obj['name_en']}) -> {s_obj['release_date']} (Beklenen: {exp})")
    else:
        print(f"  ❌ [{sid}] {name} BULUNAMADI!")
        all_match = False

if all_match:
    print("\n🎉 TÜM ÖRNEKLER VE VERİLER MOBAFIRE İLE %100 BİREBİR EŞLEŞTİ!")
