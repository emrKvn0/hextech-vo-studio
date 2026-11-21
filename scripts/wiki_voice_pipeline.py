# -*- coding: utf-8 -*-
"""
================================================================================
LoL Ses & Replik Entegrasyon Motoru (League Wiki & SkinSpotlights CC Pipeline)
================================================================================
HUKUKİ VE LİSANS BİLDİRİMİ:
- League of Legends Wiki metinleri ve alıntıları Creative Commons Attribution-
  ShareAlike (CC BY-SA 3.0 / 4.0) lisansına tabidir.
  Kaynak ve atıf URL'si: https://wiki.leagueoflegends.com/
  Oyun içi tüm ses dosyaları, karakter adları ve replik telifleri Riot Games Inc.'e aittir.
- YouTube SkinSpotlights altyazıları kanal sahibine aittir. Yalnızca wiki'de metin
  bulunmayan durumlarda yedek/referans amaçlı kullanılır ve kaynak olarak işaretlenir.
================================================================================
"""

import os
import sys
import re
import json
import time
import datetime
import urllib.parse
import subprocess
from typing import Dict, List, Optional, Tuple, Any

import requests
from bs4 import BeautifulSoup
from rapidfuzz import fuzz

try:
    from deep_translator import GoogleTranslator
except ImportError:
    GoogleTranslator = None

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORAGE_DIR = os.path.join(PROJECT_ROOT, ".app_storage")
WIKI_CACHE_DIR = os.path.join(STORAGE_DIR, "wiki_cache")
YOUTUBE_CACHE_DIR = os.path.join(STORAGE_DIR, "youtube_cc_cache")
CHAMPIONS_DIR = os.path.join(PROJECT_ROOT, "Champions")
TRANSLATION_CACHE_FILE = os.path.join(WIKI_CACHE_DIR, "translation_cache.json")

os.makedirs(WIKI_CACHE_DIR, exist_ok=True)
os.makedirs(YOUTUBE_CACHE_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# Rate Limiter & HTTP İstemcisi
# ---------------------------------------------------------------------------
class RateLimitedSession:
    """Wiki sunucusuna en fazla 1 istek/saniye atan, kibar User-Agent kullanan oturum."""
    USER_AGENT = "LoLVoiceStudio/1.0 (+https://github.com/lol-ses-veriler; Educational and Research Purpose)"

    def __init__(self, min_interval: float = 1.0):
        self.min_interval = min_interval
        self.last_request_time = 0.0
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.USER_AGENT})

    def get(self, url: str, **kwargs) -> requests.Response:
        now = time.time()
        elapsed = now - self.last_request_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_request_time = time.time()
        return self.session.get(url, **kwargs)

HTTP_CLIENT = RateLimitedSession(min_interval=1.0)

# ---------------------------------------------------------------------------
# Runeterra Özel İsimleri Koruma Listesi (Çeviri Esnasında Bozulmayacak Terimler)
# ---------------------------------------------------------------------------
PROTECTED_TERMS = [
    # Şampiyonlar & Varlıklar
    "Aatrox", "Ahri", "Akali", "Akshan", "Alistar", "Ambessa", "Amumu", "Anivia",
    "Annie", "Aphelios", "Ashe", "Aurelion Sol", "Azir", "Bard", "Bel'Veth",
    "Blitzcrank", "Brand", "Braum", "Briar", "Caitlyn", "Camille", "Cassiopeia",
    "Cho'Gath", "Corki", "Darius", "Diana", "Dr. Mundo", "Draven", "Ekko",
    "Elise", "Evelynn", "Ezreal", "Fiddlesticks", "Fiora", "Fizz", "Galio",
    "Gangplank", "Garen", "Gnar", "Gragas", "Graves", "Gwen", "Hecarim",
    "Heimerdinger", "Hwei", "Illaoi", "Irelia", "Ivern", "Janna", "Jarvan IV",
    "Jax", "Jayce", "Jhin", "Jinx", "K'Sante", "Kai'Sa", "Kalista", "Karma",
    "Karthus", "Kassadin", "Katarina", "Kayle", "Kayn", "Kennen", "Kha'Zix",
    "Kindred", "Kled", "Kog'Maw", "LeBlanc", "Lee Sin", "Leona", "Lillia",
    "Lissandra", "Lucian", "Lulu", "Lux", "Malphite", "Malzahar", "Maokai",
    "Master Yi", "Milio", "Miss Fortune", "Mordekaiser", "Morgana", "Naafiri",
    "Nami", "Nasus", "Nautilus", "Neeko", "Nidalee", "Nilah", "Nocturne",
    "Nunu & Willump", "Olaf", "Orianna", "Ornn", "Pantheon", "Poppy", "Pyke",
    "Qiyana", "Quinn", "Rakan", "Rammus", "Rek'Sai", "Rell", "Renata Glasc",
    "Renekton", "Rengar", "Riven", "Rumble", "Ryze", "Samira", "Sejuani",
    "Senna", "Seraphine", "Sett", "Shaco", "Shen", "Shyvana", "Singed",
    "Sion", "Sivir", "Skarner", "Smolder", "Sona", "Soraka", "Swain",
    "Sylas", "Syndra", "Tahm Kench", "Taliyah", "Talon", "Taric", "Teemo",
    "Thresh", "Tristana", "Trundle", "Tryndamere", "Twisted Fate", "Twitch",
    "Udyr", "Urgot", "Varus", "Vayne", "Veigar", "Vel'Koz", "Vex", "Vi",
    "Viego", "Viktor", "Vladimir", "Volibear", "Warwick", "Wukong", "Xayah",
    "Xerath", "Xin Zhao", "Yasuo", "Yone", "Yorick", "Yuumi", "Zac", "Zed",
    "Zeri", "Ziggs", "Zilean", "Zoe", "Zyra",
    # Bölgeler ve Konseptler
    "Darkin", "Targon", "Ionia", "Shurima", "Noxus", "Demacia", "Freljord",
    "Piltover", "Zaun", "Bilgewater", "Bandle City", "Runeterra", "Void",
    "Shadow Isles", "Mount Targon", "Ixtal", "Vastaya", "Lunari", "Solari",
    "Ascended", "Baccai", "Poro", "Yordle", "Baron Nashor", "Rift Herald",
    "Anima Squad", "Primordian", "Mecha Kingdoms", "Spirit Blossom"
]

def clean_wiki_formatting(text: str) -> Tuple[str, List[str], str]:
    """
    Wikitext tırnak, kalın, italik ve sahne notlarını temizler.
    Döner: (temiz_metin, vurgulanan_kelimeler, sahne_notu)
    """
    if not text:
        return "", [], ""

    # 1. Vurgulanan kelimeleri (üçlü tırnak '''bold''') tespit et
    bold_matches = re.findall(r"'''(.*?)'''", text)
    emphasis_words = [w.strip() for w in bold_matches if w.strip()]

    # 2. Kalın işaretlerini temizle
    text = re.sub(r"'''(.*?)'''", r"\1", text)

    # 3. İtalik işaretlerini temizle
    text = re.sub(r"''(.*?)''", r"\1", text)

    # 4. Sahne notlarını tespit et (*laughs*, *sighs*, [giggles], (chuckles), Sett sighs. vb.)
    action_notes = []
    # Asteriks veya parantez içi sahneler
    for m in re.finditer(r"(\*[^*]+\*|\([^)]{2,40}\)|\[[^\]]{2,40}\])", text):
        raw_act = m.group(1).strip()
        # Eğer bu bir diyalog değilse sahne notu olarak al
        action_notes.append(raw_act.strip("*()[] "))
    
    # Text başındaki "Sett sighs. " gibi anlatıcı kalıpları
    lead_action = re.match(r"^([A-Z][a-zA-Z\s]{2,20}(?:sighs|laughs|chuckles|roars|groans|screams|whispers|gasps|shouts)\.?)\s*", text)
    if lead_action:
        action_notes.append(lead_action.group(1).strip(". "))
        text = text[lead_action.end():]

    # Replikten sahne notu asterikslerini temizle
    text = re.sub(r"\*[^*]+\*", "", text)
    text = re.sub(r"\([^)]{2,40}\)", "", text)
    text = re.sub(r"\[[^\]]{2,40}\]", "", text)

    # 5. Tırnak işaretlerini temizle
    text = text.strip()
    text = re.sub(r'^["\'“‘”’\s]+|["\'“‘”’\s]+$', '', text)
    text = text.strip()

    # 6. Wiki iç bağlantıları temizle [[Page|Label]] -> Label
    text = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]+)\]\]', r'\1', text)

    # 7. Wiki şablonlarını temizle {{...}}
    text = re.sub(r'\{\{[^}]+\}\}', '', text)

    # Birden çok boşluğu teke indir
    text = re.sub(r'\s+', ' ', text).strip()

    action_note = ", ".join(action_notes) if action_notes else ""
    return text, emphasis_words, action_note


# ---------------------------------------------------------------------------
# 1. Wiki Audio Çekici ve Ayrıştırıcı (Adım 1 & Adım 2)
# ---------------------------------------------------------------------------
class WikiAudioFetcher:
    """
    League of Legends Wiki'den şampiyon ses repliklerini çeken ve ayrıştıran sınıf.
    MediaWiki API + HTML yedekli, disk önbellekli, tabber ve bölüm duyarlı.
    """
    API_URL = "https://wiki.leagueoflegends.com/api.php"

    @classmethod
    def get_cache_path(cls, champion: str) -> str:
        safe_champ = re.sub(r'[^a-zA-Z0-9_]', '_', champion)
        return os.path.join(WIKI_CACHE_DIR, f"{safe_champ}_Audio.json")

    @classmethod
    def fetch_champion_audio_page(cls, champion: str) -> Dict[str, Any]:
        """Sayfayı disk önbelleğinden yükler veya MediaWiki API'den 1 kez çeker."""
        cache_path = cls.get_cache_path(champion)
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass

        page_name = f"{champion}/Audio"
        params = {
            "action": "parse",
            "page": page_name,
            "prop": "sections|wikitext|text",
            "format": "json"
        }
        url = f"{cls.API_URL}?{urllib.parse.urlencode(params)}"
        
        try:
            resp = HTTP_CLIENT.get(url, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                if "parse" in data:
                    res = {
                        "champion": champion,
                        "source_url": f"https://wiki.leagueoflegends.com/en-us/{urllib.parse.quote(page_name)}",
                        "fetched_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                        "sections": data["parse"].get("sections", []),
                        "wikitext": data["parse"].get("wikitext", {}).get("*", ""),
                        "html": data["parse"].get("text", {}).get("*", "")
                    }
                    with open(cache_path, "w", encoding="utf-8") as f:
                        json.dump(res, f, ensure_ascii=False, indent=2)
                    return res
        except Exception as e:
            print(f"[WikiAudioFetcher] MediaWiki API hatası ({champion}): {e}")

        # Fallback: Doğrudan HTML çekme
        direct_url = f"https://wiki.leagueoflegends.com/en-us/{urllib.parse.quote(page_name)}"
        try:
            resp = HTTP_CLIENT.get(direct_url, timeout=15)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                content_div = soup.find("div", {"class": "mw-parser-output"})
                html_content = str(content_div) if content_div else resp.text
                res = {
                    "champion": champion,
                    "source_url": direct_url,
                    "fetched_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "sections": [],
                    "wikitext": "",
                    "html": html_content
                }
                with open(cache_path, "w", encoding="utf-8") as f:
                    json.dump(res, f, ensure_ascii=False, indent=2)
                return res
        except Exception as e:
            print(f"[WikiAudioFetcher] Doğrudan HTML çekme hatası ({champion}): {e}")

        return {}

    @classmethod
    def list_available_sections_and_tabs(cls, champion: str) -> Dict[str, Any]:
        """Şampiyonun sayfasındaki ana bölümleri ve Tabber sekmelerini listeler."""
        data = cls.fetch_champion_audio_page(champion)
        if not data:
            return {"champion": champion, "tabs": [], "sections": [], "error": "Sayfa çekilemedi"}

        wikitext = data.get("wikitext", "")
        # Tabber sekmelerini çıkar
        tab_names = []
        if wikitext:
            matches = re.findall(r'(?:<tabber>|\|-\|)\s*([^=\n\r]+)=', wikitext)
            tab_names = [m.strip() for m in matches if m.strip()]

        # Eğer wikitext yoksa HTML'den tabber başlıklarını ara
        if not tab_names and data.get("html"):
            soup = BeautifulSoup(data["html"], "html.parser")
            for tab_div in soup.find_all(class_=re.compile(r'tabber__tab|wds-tab__label')):
                name = tab_div.get_text(strip=True)
                if name and name not in tab_names:
                    tab_names.append(name)

        sec_lines = [s.get("line", "") for s in data.get("sections", [])]
        return {
            "champion": champion,
            "tabs": tab_names,
            "sections": sec_lines,
            "source_url": data.get("source_url", "")
        }

    @classmethod
    def match_skin_to_tab(cls, requested_skin: str, available_tabs: List[str]) -> Optional[str]:
        """
        Kullanıcının talep ettiği kostüm adını (örn: 'Radiant Serpent', 'Classic', 'Primordian Aatrox')
        mevcut wiki tabber sekme adına eşler.
        """
        if not requested_skin or not available_tabs:
            return None

        req_clean = re.sub(r'[^a-z0-9]', '', requested_skin.lower())

        # 1. Birebir veya tam kapsama
        for tab in available_tabs:
            tab_clean = re.sub(r'[^a-z0-9]', '', tab.lower())
            if req_clean == tab_clean:
                return tab

        # 2. İçerme kontrolü (ör. "Primordian Aatrox" -> "Primordian")
        for tab in available_tabs:
            tab_clean = re.sub(r'[^a-z0-9]', '', tab.lower())
            if tab_clean and (tab_clean in req_clean or req_clean in tab_clean):
                return tab

        # 3. Fuzzy eşleme
        best_tab = None
        best_ratio = 0
        for tab in available_tabs:
            ratio = fuzz.ratio(req_clean, re.sub(r'[^a-z0-9]', '', tab.lower()))
            if ratio > best_ratio and ratio >= 70:
                best_ratio = ratio
                best_tab = tab

        return best_tab

    @classmethod
    def parse_quotes_for_skin(cls, champion: str, requested_skin: str = "Classic") -> List[Dict[str, Any]]:
        """
        Belirtilen şampiyon ve kostüm için replay/ses satırlarını çıkarır.
        """
        page_data = cls.fetch_champion_audio_page(champion)
        if not page_data:
            return []

        wikitext = page_data.get("wikitext", "")
        tabs_info = cls.list_available_sections_and_tabs(champion)
        matched_tab = cls.match_skin_to_tab(requested_skin, tabs_info["tabs"])

        is_classic = (requested_skin.lower() in ["classic", "original", "default", "varsayilan"] or 
                      (matched_tab and matched_tab.lower() in ["classic", "original"]))

        target_wikitext = ""
        common_select_text = ""

        # Champion Select bölümü tabber dışında olabilir, onu Classic veya genel seçim için al
        if wikitext:
            # Champion Select bölümünü ayıkla
            cs_match = re.search(r'== Champion Select ==(.*?)(?:== [^=]|$)', wikitext, re.DOTALL)
            if cs_match:
                common_select_text = cs_match.group(1)

            # Tabber bloğunu bul
            tabber_match = re.search(r'<tabber>(.*?)</tabber>', wikitext, re.DOTALL)
            if tabber_match:
                tab_parts = re.split(r'\n\|-\|\s*', tabber_match.group(1).strip())
                for part in tab_parts:
                    lines = part.strip().split('\n', 1)
                    tab_header = lines[0].split('=')[0].strip()
                    content = lines[1] if len(lines) > 1 else ""

                    if matched_tab and tab_header.lower() == matched_tab.lower():
                        target_wikitext = content
                        break
                    elif is_classic and tab_header.lower() in ["classic", "original"]:
                        target_wikitext = content
                        break
            else:
                # Tabber yoksa tüm sayfa hedeftir
                target_wikitext = wikitext

        if not target_wikitext and not common_select_text:
            return []

        # Eğer Classic isteniyorsa ve common_select_text varsa başa ekle
        full_parse_text = ""
        if is_classic and common_select_text:
            full_parse_text += "== Champion Select ==\n" + common_select_text + "\n"
        full_parse_text += target_wikitext

        # Satır satır parse
        quotes: List[Dict[str, Any]] = []
        current_h2 = "General"
        current_h3 = ""

        lines = full_parse_text.splitlines()
        for raw_line in lines:
            line = raw_line.strip()
            if not line:
                continue

            # Başlıkları takip et
            if line.startswith("=="):
                # Başlık şablonlarını temizle: {{ai|...}}, {{si|...}}, {{ccib|...}}
                clean_heading = re.sub(r'\{\{[^|}]*\|?([^}]*)\}\}', r'\1', line)
                clean_heading = re.sub(r'[=\[\]]', '', clean_heading).strip()
                clean_heading = re.sub(r'\.png|size=\d+', '', clean_heading).strip()
                
                # Seviye tespiti
                if line.startswith("==="):
                    current_h3 = clean_heading
                else:
                    current_h2 = clean_heading
                    current_h3 = ""
                continue

            # SFX, Trivia, References bölümlerini atla
            heading_lower = f"{current_h2} {current_h3}".lower()
            if any(skip_word in heading_lower for skip_word in ["sound effect", "sfx", "trivia", "reference", "accompanying"]):
                continue

            # Sadece '*' ile başlayan replik satırlarını al
            if not line.startswith("*"):
                continue

            # Replik satırında ses efekti veya placeholder var mı kontrol et
            if "'''''Sound Effect'''''" in line or "''Sound Effect''" in line or "PLACEHOLDER" in line:
                continue

            if "AccompanyingSFX" in line:
                continue

            # Trigger belirle
            trigger = current_h3 if current_h3 else current_h2
            trigger = re.sub(r'\s+', ' ', trigger).strip()

            # sm2 şablonlarını çıkar: {{sm2|file.ogg|icon1|icon2...}}
            sm2_matches = re.findall(r'\{\{sm2\|([^}]+)\}\}', line)
            audio_files = []
            skin_labels = []

            for sm2_args in sm2_matches:
                parts = [p.strip() for p in sm2_args.split('|')]
                if parts:
                    audio_files.append(parts[0])
                    for skin_p in parts[1:]:
                        if skin_p and skin_p not in skin_labels:
                            skin_labels.append(skin_p)

            # csl / ci şablonlarından da kostüm ikonlarını çek
            for csl_m in re.findall(r'\{\{csl\|[^|]+\|([^|}]+)', line):
                if csl_m.strip() and csl_m.strip() not in skin_labels:
                    skin_labels.append(csl_m.strip())

            # Ses şablonlarını satırdan temizle ki geriye sadece metin kalsın
            clean_line_text = re.sub(r'\{\{sm2\|[^}]+\}\}', '', line)
            clean_line_text = re.sub(r'\{\{csl\|[^}]+\}\}', '', clean_line_text)
            clean_line_text = re.sub(r'\{\{ci\|[^}]+\}\}', '', clean_line_text)
            clean_line_text = clean_line_text.lstrip('* ').strip()

            # Metin, vurgular ve sahne notunu ayrıştır
            text_en, emphasis_words, action_note = clean_wiki_formatting(clean_line_text)

            # Eğer diyalog metni ve sahne notu tamamen boşsa bu bir replik değildir
            if not text_en and not action_note:
                continue

            # Skin listesini derle
            if not skin_labels:
                skin_labels = [requested_skin if requested_skin else "Classic"]
            elif requested_skin and requested_skin not in skin_labels:
                # Eşleşen skin etiketini ekle
                skin_labels.append(requested_skin)

            quote_item = {
                "champion": champion,
                "skin_list": skin_labels,
                "trigger": trigger,
                "text_en": text_en,
                "action_note": action_note,
                "audio_file": audio_files[0] if audio_files else "",
                "all_audio_files": audio_files,
                "emphasis_words": emphasis_words,
                "source": "wiki",
                "source_url": page_data.get("source_url", ""),
                "fetched_at": page_data.get("fetched_at", "")
            }
            quotes.append(quote_item)

        return quotes


# ---------------------------------------------------------------------------
# 2. SkinSpotlights CC Yedek Kaynak (Adım 5 - Gelişmiş Video & Rolling VTT Çözücü)
# ---------------------------------------------------------------------------
class SkinSpotlightsCCFetcher:
    """
    Wiki'de replik bulunamadığında SkinSpotlights YouTube kanalındaki videolardan
    altyazı (CC) çeken, tam seslendirme videolarını önceliklendiren ve
    YouTube'un kayan (rolling) altyazılarını tam cümlelere dönüştüren yedek sınıf.
    """

    @classmethod
    def search_video_and_subtitles(cls, champion: str, skin_name: str) -> Dict[str, Any]:
        """
        yt-dlp ile arama yapar. 'Special Interactions' veya 'Full Voice' videolarını
        en yüksek öncelikle seçer, aksi halde standart spotlight videosunu alır.
        """
        queries = [
            f"ytsearch5:SkinSpotlights {skin_name} {champion} Voice",
            f"ytsearch5:SkinSpotlights {skin_name} {champion} Special Interactions",
            f"ytsearch5:SkinSpotlights {skin_name} {champion}"
        ]

        best_candidate = None
        highest_score = -1

        for q in queries:
            cmd = [
                sys.executable, "-m", "yt_dlp",
                q,
                "--dump-json",
                "--no-warnings",
                "--skip-download"
            ]
            try:
                proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=35)
                if proc.returncode != 0 or not proc.stdout.strip():
                    continue

                for line in proc.stdout.splitlines():
                    if not line.strip():
                        continue
                    try:
                        info = json.loads(line)
                    except Exception:
                        continue

                    title = info.get("title", "")
                    title_lower = title.lower()
                    duration = info.get("duration", 0) or 0
                    video_id = info.get("id")

                    # Şampiyon adı ve skin adı başlıkta geçmeli
                    champ_clean = champion.lower()
                    skin_clean = skin_name.lower().replace("skin", "").strip()
                    if champ_clean not in title_lower and skin_clean not in title_lower:
                        continue

                    manual_subs = list(info.get("subtitles", {}).keys())
                    auto_subs = list(info.get("automatic_captions", {}).keys())

                    sub_type = "none"
                    if "en" in manual_subs or any("en" in s for s in manual_subs):
                        sub_type = "manual"
                    elif "en" in auto_subs or any("en" in s for s in auto_subs):
                        sub_type = "auto"

                    if sub_type == "none":
                        continue

                    # Skorlama: Full Voice / Special Interactions > Normal Spotlight
                    score = 10
                    if "special interactions" in title_lower or "full voice" in title_lower:
                        score += 50
                    elif "voice" in title_lower:
                        score += 30
                    if sub_type == "manual":
                        score += 20
                    # Uzunluk avantajı (tam seslendirme videoları genellikle 5-15 dakika sürer)
                    if duration > 300:
                        score += 25

                    if score > highest_score:
                        highest_score = score
                        best_candidate = {
                            "found": True,
                            "video_id": video_id,
                            "title": title,
                            "video_url": f"https://www.youtube.com/watch?v={video_id}",
                            "sub_type": sub_type,
                            "duration": duration
                        }
            except Exception as e:
                print(f"[SkinSpotlightsCCFetcher] Arama hatası: {e}")

            if best_candidate and highest_score >= 60:
                break

        return best_candidate or {"found": False, "sub_type": "none", "video_id": "", "title": ""}

    @classmethod
    def download_and_parse_vtt(cls, video_id: str, champion: str, skin_name: str, sub_type: str) -> List[Dict[str, Any]]:
        """
        VTT altyazısını indirir ve YouTube rolling/scrolling örtüşmelerini tam cümle
        diyaloglarına rekonstrükte eder.
        """
        if not video_id:
            return []

        vtt_output_template = os.path.join(YOUTUBE_CACHE_DIR, f"{video_id}.%(ext)s")
        expected_vtt = os.path.join(YOUTUBE_CACHE_DIR, f"{video_id}.en.vtt")

        if not os.path.exists(expected_vtt):
            cmd = [
                sys.executable, "-m", "yt_dlp",
                f"https://www.youtube.com/watch?v={video_id}",
                "--skip-download",
                "--write-subs" if sub_type == "manual" else "--write-auto-subs",
                "--sub-langs", "en",
                "--convert-subs", "vtt",
                "-o", vtt_output_template,
                "--no-warnings"
            ]
            try:
                subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=45)
            except Exception as e:
                print(f"[SkinSpotlightsCCFetcher] Altyazı indirme hatası: {e}")
                return []

        if not os.path.exists(expected_vtt):
            for f in os.listdir(YOUTUBE_CACHE_DIR):
                if f.startswith(video_id) and f.endswith(".vtt"):
                    expected_vtt = os.path.join(YOUTUBE_CACHE_DIR, f)
                    break

        if not os.path.exists(expected_vtt):
            return []

        raw_blocks = []
        try:
            with open(expected_vtt, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            blocks = re.split(r'\n\s*\n', content)
            for b in blocks:
                lines = [l.strip() for l in b.splitlines() if l.strip()]
                if not lines or lines[0].startswith("WEBVTT") or lines[0].startswith("NOTE"):
                    continue

                time_line = None
                text_lines = []
                for l in lines:
                    if "-->" in l:
                        time_line = l
                    elif time_line:
                        clean_l = re.sub(r'<[^>]+>', '', l).strip()
                        if clean_l:
                            text_lines.append(clean_l)

                if time_line and text_lines:
                    text_str = " ".join(text_lines).strip()
                    # >> işaretlerini kaldır
                    text_str = re.sub(r'^(?:>>\s*)+', '', text_str).strip()
                    start_t = time_line.split("-->")[0].strip()
                    raw_blocks.append((start_t, text_str))
        except Exception as e:
            print(f"[SkinSpotlightsCCFetcher] VTT okuma hatası: {e}")
            return []

        # YouTube Rolling Caption Rekonstrüksiyonu & Örtüşme Kesici (Prefix Overlap Trimming)
        def trim_overlap(prev_text: str, new_text: str) -> str:
            if not prev_text or not new_text:
                return new_text.strip()
            prev_words = prev_text.lower().split()
            new_words = new_text.split()
            max_k = min(len(prev_words), len(new_words), 8)
            for k in range(max_k, 0, -1):
                prev_tail = [w.strip('.,!?;:\"\'') for w in prev_words[-k:]]
                new_head = [w.strip('.,!?;:\"\'').lower() for w in new_words[:k]]
                if prev_tail == new_head:
                    return ' '.join(new_words[k:]).strip()
            return new_text.strip()

        cleaned_dialogues = []
        current_sentence = ""
        current_start_time = ""
        current_action_notes = []
        last_saved_sentence = ""

        promo_keywords = ["skin spotlight", "subscribe", "tier", "chroma", "price", "rp", "discord", "pre-release", "pbe preview"]

        for start_t, block_text in raw_blocks:
            # Sahne notlarını ayıkla: [music], [laughter], [screams] vb.
            for m in re.finditer(r'\[(.*?)\]', block_text):
                act = m.group(1).strip()
                if act.lower() not in ["music"] and act not in current_action_notes:
                    current_action_notes.append(act)

            # [music] vb. temizle
            clean_t = re.sub(r'\[.*?\]', '', block_text).strip()
            clean_t = re.sub(r'\s+', ' ', clean_t)
            if not clean_t:
                continue

            # Tanıtım metinlerini atla
            if any(pk in clean_t.lower() for pk in promo_keywords):
                continue

            if not current_sentence:
                # Yeni cümle başlarken önceki kaydedilen cümlenin ardılı ise örtüşmeyi buda
                trimmed_t = trim_overlap(last_saved_sentence, clean_t)
                if trimmed_t:
                    current_sentence = trimmed_t
                    current_start_time = start_t
            else:
                # Rolling örtüşme kontrolü
                if clean_t in current_sentence or current_sentence.endswith(clean_t):
                    continue
                elif current_sentence in clean_t:
                    current_sentence = clean_t
                else:
                    w_curr = current_sentence.split()
                    w_new = clean_t.split()
                    merged = False
                    for k in range(min(len(w_curr), len(w_new)), 0, -1):
                        if w_curr[-k:] == w_new[:k]:
                            current_sentence = " ".join(w_curr + w_new[k:])
                            merged = True
                            break
                    if not merged:
                        if len(current_sentence.split()) >= 2:
                            cleaned_dialogues.append((current_start_time, current_sentence, list(current_action_notes)))
                            last_saved_sentence = current_sentence
                        trimmed_t = trim_overlap(last_saved_sentence, clean_t)
                        current_sentence = trimmed_t
                        current_start_time = start_t
                        current_action_notes = []

            # Cümle bitişi (nokta, ünlem, soru işareti)
            if current_sentence.endswith(('.', '?', '!')) and len(current_sentence.split()) >= 3:
                cleaned_dialogues.append((current_start_time, current_sentence, list(current_action_notes)))
                last_saved_sentence = current_sentence
                current_sentence = ""
                current_start_time = ""
                current_action_notes = []

        if current_sentence and len(current_sentence.split()) >= 2:
            cleaned_dialogues.append((current_start_time, current_sentence, list(current_action_notes)))

        # Nihai tekilleştirme ve filtreleme
        quotes = []
        seen_texts = set()
        source_label = "skinspotlights_cc_manual" if sub_type == "manual" else "skinspotlights_cc_auto"

        for start_t, text_raw, acts in cleaned_dialogues:
            text_norm = re.sub(r'[^a-zA-Z0-9]', '', text_raw.lower())
            if not text_norm or len(text_norm) < 6 or text_norm in seen_texts:
                continue
            seen_texts.add(text_norm)

            text_en, emphasis_words, parsed_act = clean_wiki_formatting(text_raw)
            if not text_en or len(text_en.split()) < 2:
                continue

            action_note_str = ", ".join(acts) if acts else parsed_act
            short_time = start_t.split('.')[0] if '.' in start_t else start_t
            if short_time.startswith("00:"):
                short_time = short_time[3:]

            quotes.append({
                "champion": champion,
                "skin_list": [skin_name],
                "trigger": f"SkinSpotlights ({short_time})",
                "text_en": text_en,
                "action_note": action_note_str,
                "audio_file": "",
                "all_audio_files": [],
                "emphasis_words": emphasis_words,
                "source": source_label,
                "timestamp": short_time,
                "source_url": f"https://www.youtube.com/watch?v={video_id}",
                "fetched_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
            })

        return quotes


# ---------------------------------------------------------------------------
# LoL & Tematik Evren Lore Terminoloji Sözlüğü (Resmi Dublaj & Lore Uyumu)
# ---------------------------------------------------------------------------
LOL_LORE_TERMS = {
    "old gods": "Kadim Tanrılar",
    "old god": "Kadim Tanrı",
    "horned king": "Boynuzlu Kral",
    "coven": "Cadılar Meclisi",
    "witchling": "Toy Cadı",
    "mother most ancient": "En Kadim Anne",
    "ruinous winds": "yıkıcı rüzgârlar",
    "ruinous": "yıkıcı",
    "maelstrom": "azgın girdap",
    "sacrament": "kutsal adak",
    "vestiges of humanity": "insanlığın kalıntıları",
    "mortal realm": "fani diyar",
    "primal winds": "ilkel rüzgârlar",
    "primal storm": "ilkel fırtına",
    "zephyr": "Zephyr",
    "darkin": "Darkin",
    "void": "Hiçlik",
    "aspect": "Suret",
    "celestial": "Kozmik Varlık",
    "world ender": "Dünyaların Sonu",
    "first encounter": "İlk Karşılaşma",
    "show stopper": "Gösteri Zamanı"
}


# ---------------------------------------------------------------------------
# 3. Türkçe Çeviri Motoru (Adım 6 - LoL Lore & Çoklu Sağlayıcı Korumalı)
# ---------------------------------------------------------------------------
class QuoteTranslator:
    """
    İngilizce replikleri Türkçeye çeviren, Runeterra özel isimlerini koruyan,
    GTX ve MyMemory yedekli, diskte önbellekli ve engelsiz toplu çeviri sınıfı.
    """
    _cache: Dict[str, str] = {}
    _cache_loaded = False

    @classmethod
    def load_cache(cls):
        if cls._cache_loaded:
            return
        if os.path.exists(TRANSLATION_CACHE_FILE):
            try:
                with open(TRANSLATION_CACHE_FILE, "r", encoding="utf-8") as f:
                    cls._cache = json.load(f)
            except Exception:
                cls._cache = {}
        cls._cache_loaded = True

    @classmethod
    def save_cache(cls):
        try:
            with open(TRANSLATION_CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(cls._cache, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    @classmethod
    def protect_special_names(cls, text: str) -> Tuple[str, Dict[str, str]]:
        """Özel isimleri __PROT_X__ yer tutucuları ile maskeler."""
        mapping = {}
        idx = 0
        masked_text = text
        for term in PROTECTED_TERMS:
            pattern = re.compile(r'\b' + re.escape(term) + r'\b', re.IGNORECASE)
            matches = pattern.findall(masked_text)
            if matches:
                placeholder = f"__PROT{idx}__"
                mapping[placeholder] = term
                masked_text = pattern.sub(placeholder, masked_text)
                idx += 1
        return masked_text, mapping

    @classmethod
    def restore_special_names(cls, text: str, mapping: Dict[str, str]) -> str:
        """Maskelenen yer tutucuları orijinal isimlerle değiştirir ve LoL Lore lügatını uygular."""
        restored = text
        for placeholder, original in mapping.items():
            restored = re.sub(re.escape(placeholder), original, restored, flags=re.IGNORECASE)

        # LoL Lore Terimleri İyileştirmesi (Kuru çeviriyi oyun lügatına uyarlama)
        lore_post_fixes = {
            r'\beski tanrılar\b': 'Kadim Tanrılar',
            r'\beski tanrı\b': 'Kadim Tanrı',
            r'\bcoven\b': 'Cadılar Meclisi',
            r'\bboynuzlu kral\b': 'Boynuzlu Kral',
            r'\btoy cadı\b': 'Toy Cadı',
            r'\ben kadim anne\b': 'En Kadim Anne',
            r'\byıkıcı rüzgarlar\b': 'yıkıcı rüzgârlar',
            r'\banafor\b': 'azgın girdap',
            r'\bkara büyü meclisi\b': 'Cadılar Meclisi',
            r'\bfani alem\b': 'fani diyar',
            r'\bfani dünyası\b': 'faniler dünyası'
        }
        for pat, rep in lore_post_fixes.items():
            restored = re.sub(pat, rep, restored, flags=re.IGNORECASE)

        return restored

    @classmethod
    def _translate_single_text(cls, text: str) -> str:
        """GTX API dener, 429 veya hata durumunda MyMemory API fallback yapar."""
        if not text:
            return ""

        # 1. Google GTX API
        try:
            url = "https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=tr&dt=t&q=" + urllib.parse.quote(text)
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            with urllib.request.urlopen(req, timeout=6) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                translated_parts = [p[0] for p in res[0] if p and p[0]]
                translated = "".join(translated_parts).strip()
                if translated and translated.lower() != text.lower():
                    return translated
        except Exception:
            pass

        # 2. MyMemory Fallback (Rate-limit toleranslı)
        try:
            url_mm = f"https://api.mymemory.translated.net/get?q={urllib.parse.quote(text)}&langpair=en|tr"
            req_mm = urllib.request.Request(url_mm, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req_mm, timeout=6) as resp_mm:
                res_mm = json.loads(resp_mm.read().decode("utf-8"))
                translated_mm = res_mm.get("responseData", {}).get("translatedText", "").strip()
                if translated_mm and not translated_mm.startswith("MYMEMORY WARNING"):
                    return translated_mm
        except Exception:
            pass

        return text

    @classmethod
    def _translate_batch_lines(cls, texts: List[str]) -> List[str]:
        """GTX API üzerinden toplu satır dener, başarısız olanları MyMemory fallback ile çevirir."""
        if not texts:
            return []
        joined = "\n".join(texts)
        try:
            url = "https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=tr&dt=t&q=" + urllib.parse.quote(joined)
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                full_translated = "".join([p[0] for p in res[0] if p and p[0]])
                translated_lines = full_translated.split("\n")
                if len(translated_lines) == len(texts):
                    return [tl.strip() for tl in translated_lines]
        except Exception:
            pass

        # Fallback: Tek tek çevir (GTX + MyMemory)
        results = []
        for t in texts:
            results.append(cls._translate_single_text(t))
        return results

    @classmethod
    def translate_quotes_batch(cls, quotes: List[Dict[str, Any]], batch_size: int = 30) -> List[Dict[str, Any]]:
        """Replik listesini toplu ve önbellekli olarak Türkçeye çevirir."""
        cls.load_cache()

        needed_items = []
        for i, q in enumerate(quotes):
            en = q.get("text_en", "").strip()
            if not en:
                q["text_tr"] = ""
                q["translation_method"] = "empty"
                q["translated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
                continue

            if en in cls._cache:
                q["text_tr"] = cls._cache[en]
                q["translation_method"] = "cache"
                q["translated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
            else:
                needed_items.append((i, en))

        # Toplu multi-line isteklerle çeviri
        for start_idx in range(0, len(needed_items), batch_size):
            chunk = needed_items[start_idx:start_idx + batch_size]
            masked_texts = []
            mappings = []
            for orig_idx, en_text in chunk:
                masked_t, m = cls.protect_special_names(en_text)
                masked_texts.append(masked_t)
                mappings.append(m)

            translated_masked = cls._translate_batch_lines(masked_texts)

            for (orig_idx, en_text), tr_res, m in zip(chunk, translated_masked, mappings):
                final_tr = cls.restore_special_names(tr_res, m)
                cls._cache[en_text] = final_tr
                quotes[orig_idx]["text_tr"] = final_tr
                quotes[orig_idx]["translation_method"] = "machine_translation_gtx"
                quotes[orig_idx]["translated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()

            time.sleep(0.05)

        cls.save_cache()
        return quotes


# ---------------------------------------------------------------------------
# 4. Ses - Metin Eşleştirme Motoru (Adım 4)
# ---------------------------------------------------------------------------
EVENT_TRIGGER_MAP = {
    # Oyun içi event pattern <-> Wiki trigger başlıkları
    "katletme": ["kill", "kills", "kills and objectives", "first blood", "pentakill"],
    "kill": ["kill", "kills", "kills and objectives", "first blood", "pentakill"],
    "karsilasma": ["first encounter", "encounter", "first move"],
    "encounter": ["first encounter", "encounter", "first move"],
    "hedef": ["first encounter", "taunt", "joke", "kill", "encounter"],
    "saka": ["joke", "jokes"],
    "joke": ["joke", "jokes"],
    "kiskirtma": ["taunt", "taunts"],
    "taunt": ["taunt", "taunts"],
    "kahkaha": ["laugh", "laughs"],
    "laugh": ["laugh", "laughs"],
    "donus": ["recall"],
    "recall": ["recall"],
    "olum": ["death"],
    "death": ["death"],
    "canlanma": ["respawn", "revive"],
    "q_yetenek": ["ability", "knuckle down", "the darkin blade", "blade", "q"],
    "w_yetenek": ["ability", "haymaker", "infernal chains", "chains", "w"],
    "e_yetenek": ["ability", "facebreaker", "umbral dash", "e"],
    "r_ulti": ["ability", "the show stopper", "show stopper", "world ender", "r", "ult"],
    "magaza": ["shopping", "shop", "item", "buying"],
    "esya": ["shopping", "shop", "item", "buying"],
    "hareket": ["movement", "moving", "long move", "first move"],
    "saldiri": ["attack", "attacking", "basic attacking"]
}

class AudioMatcher:
    """
    Yerel ses dosyaları, Wwise event adları ve Faster-Whisper transkripsiyonu ile
    Wiki replik satırlarını eşleştirir.
    >= 90: Otomatik eşleşme
    75-89: Elle kontrol listesi
    < 75:  Eşleşmedi
    """

    @classmethod
    def get_local_audio_files(cls, champion: str, skin_folder_keyword: str = "") -> List[str]:
        """Projedeki Champions dizini altında şampiyonun yerel ses dosyalarını listeler."""
        champ_dir = os.path.join(CHAMPIONS_DIR, champion)
        if not os.path.isdir(champ_dir):
            return []

        audio_files = []
        clean_kw = re.sub(r'[^a-z0-9]', '', skin_folder_keyword.lower()) if skin_folder_keyword else ""
        # Türkçe karakter düzeltmeleri ve kök bulma (örn: primordian -> primordi)
        stem_kw = clean_kw[:6] if len(clean_kw) >= 6 else clean_kw

        for root, dirs, files in os.walk(champ_dir):
            if stem_kw:
                clean_root = re.sub(r'[^a-z0-9]', '', root.lower())
                clean_root = clean_root.replace('ı', 'i').replace('ö', 'o').replace('ü', 'u').replace('ş', 's').replace('ç', 'c').replace('ğ', 'g')
                if stem_kw not in clean_root and clean_kw not in clean_root:
                    continue

            for f in files:
                if f.lower().endswith(".wav"):
                    audio_files.append(os.path.join(root, f))
        return audio_files

    @classmethod
    def match_quotes_with_audio(cls, champion: str, quotes: List[Dict[str, Any]], 
                                skin_keyword: str = "", use_whisper: bool = False) -> Dict[str, Any]:
        """
        Replikleri yerel ses dosyaları ve event haritasıyla eşleştirir.
        """
        local_files = cls.get_local_audio_files(champion, skin_keyword)
        matched_results = []
        needs_review = []
        unmatched = []

        # Faster-Whisper transkriptleri için opsiyonel hazırlık
        whisper_transcripts = {}
        if use_whisper and local_files:
            try:
                from ai_voice_detector import AIVoiceDetector
                model = AIVoiceDetector.get_model()
                initial_prompt = f"League of Legends, {champion}, Darkin, Targon, Ionia, Shurima, Demacia, Noxus."
                for af in local_files[:30]: # Performans ve kota tasarrufu için ilk 30 ses
                    try:
                        segments, _ = model.transcribe(af, initial_prompt=initial_prompt, language="tr")
                        text = " ".join([s.text for s in segments]).strip()
                        if text:
                            whisper_transcripts[af] = text
                    except Exception:
                        pass
            except Exception as e:
                print(f"[AudioMatcher] Whisper yükleme/transkript hatası: {e}")

        # Her replik için en uygun sesi ara
        for q in quotes:
            trigger_lower = q.get("trigger", "").lower()
            en_text = q.get("text_en", "")
            tr_text = q.get("text_tr", "")
            wiki_audio = q.get("audio_file", "")

            best_file = None
            best_score = 0
            best_method = "unmatched"

            # 1. Wiki dosya adı tam veya parça eşleşmesi (.ogg vs .wav)
            if wiki_audio:
                clean_wiki_base = re.sub(r'\.ogg|\.wem|\.wav', '', wiki_audio, flags=re.IGNORECASE).lower()
                for lf in local_files:
                    lf_name = os.path.basename(lf).lower()
                    if clean_wiki_base in lf_name:
                        best_file = lf
                        best_score = 98
                        best_method = "wiki_audio_name_exact"
                        break

            # 2. Whisper transkripsiyonu ile fuzzy eşleme (Türkçe veya İngilizce)
            if best_score < 90 and whisper_transcripts:
                for lf, trans in whisper_transcripts.items():
                    # Türkçe çeviri ile karşılaştır
                    score_tr = fuzz.token_set_ratio(trans.lower(), tr_text.lower()) if tr_text else 0
                    score_en = fuzz.token_set_ratio(trans.lower(), en_text.lower()) if en_text else 0
                    score = max(score_tr, score_en)
                    if score > best_score:
                        best_score = score
                        best_file = lf
                        best_method = "whisper_stt_fuzzy"

            # 3. Olay/Trigger Desen Eşlemesi (Event Trigger Mapping)
            if best_score < 75 and local_files:
                for event_key, trigger_words in EVENT_TRIGGER_MAP.items():
                    # Replik trigger'ı bu kurala uyuyor mu?
                    if any(tw in trigger_lower for tw in trigger_words):
                        # Dosya adında bu event_key var mı?
                        for lf in local_files:
                            lf_base = os.path.basename(lf).lower()
                            if event_key in lf_base:
                                score = 82 # Event pattern uyumu
                                if score > best_score:
                                    best_score = score
                                    best_file = lf
                                    best_method = "event_trigger_pattern"
                                    break

            # Sonuç kaydı
            record = dict(q)
            record["matched_audio_file"] = best_file if best_file else ""
            record["match_score"] = best_score
            record["match_method"] = best_method

            if best_score >= 90:
                record["match_status"] = "matched"
                matched_results.append(record)
            elif 75 <= best_score < 90:
                record["match_status"] = "needs_review"
                needs_review.append(record)
            else:
                record["match_status"] = "unmatched"
                unmatched.append(record)

        return {
            "total_quotes": len(quotes),
            "matched_count": len(matched_results),
            "needs_review_count": len(needs_review),
            "unmatched_count": len(unmatched),
            "matched": matched_results,
            "needs_review": needs_review,
            "unmatched": unmatched
        }


# ---------------------------------------------------------------------------
# 5. Uçtan Uca Entegrasyon Hattı (Pipeline Orchestrator - 1. Yol Öncelikli)
# ---------------------------------------------------------------------------
class VOPipeline:
    """
    Şampiyon ve kostüm repliklerini yöneten ana boru hattı.
    
    ÖNCELİK SIRASI:
    1. YOL (Varsayılan & Asıl Omurga): Yerel Riot Türkçe .wav sesleri + Faster-Whisper
       -> Sıfır web isteği, %100 orijinal Riot Games Türkiye stüdyo dublajı.
    2. YOL (Pasif Fallback): Yalnızca yerelde ses dosyası yoksa veya force_wiki=True ise:
       -> League Wiki -> (Yoksa) SkinSpotlights YouTube CC -> Çeviri Motoru.
    """

    @classmethod
    def run(cls, champion: str, skin_name: str = "Classic", use_whisper: bool = True, 
            translate: bool = True, force_wiki: bool = False) -> Dict[str, Any]:
        report = {
            "champion": champion,
            "requested_skin": skin_name,
            "api_success": False,
            "source_used": "",
            "total_quotes": 0,
            "trigger_distribution": {},
            "first_5_quotes": [],
            "match_summary": {},
            "skinspotlights_check": {},
            "output_file": ""
        }

        # -------------------------------------------------------------------
        # 1. YOL: YEREL SESLER & FASTER-WHISPER (ASIL OMURGA)
        # -------------------------------------------------------------------
        local_files = AudioMatcher.get_local_audio_files(champion, skin_name)
        quotes = []

        if local_files and not force_wiki:
            report["source_used"] = "local_riot_dub_whisper"
            try:
                from ai_voice_detector import AIVoiceDetector
                model = AIVoiceDetector.get_model()
                initial_prompt = f"League of Legends, {champion}, Darkin, Targon, Ionia, Shurima, Demacia, Noxus."
                
                # Yerel ses dosyalarını Whisper ile dinle
                for af in local_files:
                    fname = os.path.basename(af)
                    # Klasör ve event adından trigger çıkar
                    parent_folder = os.path.basename(os.path.dirname(af))
                    trigger_name = parent_folder.replace("_", " ")

                    # Faster-Whisper ile Türkçe konuşmayı algıla
                    try:
                        segments, info = model.transcribe(af, initial_prompt=initial_prompt, language="tr")
                        text_tr = " ".join([s.text for s in segments]).strip()
                    except Exception:
                        text_tr = ""

                    if text_tr and len(text_tr) > 2:
                        quotes.append({
                            "champion": champion,
                            "skin_list": [skin_name],
                            "trigger": trigger_name,
                            "text_en": "", # Yerel resmi dublaj olduğu için orijinal TR
                            "text_tr": text_tr,
                            "action_note": "",
                            "audio_file": fname,
                            "all_audio_files": [fname],
                            "matched_audio_file": af,
                            "match_score": 100,
                            "match_method": "whisper_native_local_dub",
                            "match_status": "matched",
                            "emphasis_words": [],
                            "source": "local_riot_dub_whisper",
                            "timestamp": "",
                            "source_url": "local_disk",
                            "fetched_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
                        })
            except Exception as e:
                print(f"[VOPipeline] Whisper yerel ses analizi hatası ({e}); fallback'e geçiliyor...")

        # -------------------------------------------------------------------
        # 2. YOL: PASİF FALLBACK (WIKI & SKINSPOTLIGHTS CC)
        # (Yalnızca yerel ses yoksa veya force_wiki aktifse devreye girer)
        # -------------------------------------------------------------------
        if not quotes:
            # 2a. Wiki'den replikleri çekmeyi dene
            wiki_quotes = WikiAudioFetcher.parse_quotes_for_skin(champion, skin_name)
            if wiki_quotes:
                report["api_success"] = True
                report["source_used"] = "wiki"
                quotes = wiki_quotes
            else:
                # 2b. Wiki boşsa SkinSpotlights CC'ye düş
                ss_info = SkinSpotlightsCCFetcher.search_video_and_subtitles(champion, skin_name)
                report["skinspotlights_check"] = ss_info

                if ss_info.get("found") and ss_info.get("sub_type") in ["manual", "auto"]:
                    quotes = SkinSpotlightsCCFetcher.download_and_parse_vtt(
                        ss_info["video_id"], champion, skin_name, ss_info["sub_type"]
                    )
                    report["source_used"] = f"skinspotlights_cc_{ss_info['sub_type']}"
                else:
                    report["source_used"] = "whisper_unverified"

            # 2c. Türkçe Çeviri (Sadece Wiki/CC İngilizce replikleri için)
            if quotes and translate:
                quotes = QuoteTranslator.translate_quotes_batch(quotes)

            # 2d. Yerel ses dosyaları varsa eşleştir
            match_data = AudioMatcher.match_quotes_with_audio(champion, quotes, skin_keyword=skin_name, use_whisper=False)
            quotes = match_data["matched"] + match_data["needs_review"] + match_data["unmatched"]
            report["match_summary"] = {
                "matched_count": match_data["matched_count"],
                "needs_review_count": match_data["needs_review_count"],
                "unmatched_count": match_data["unmatched_count"]
            }
        else:
            report["match_summary"] = {
                "matched_count": len(quotes),
                "needs_review_count": 0,
                "unmatched_count": 0
            }

        # İstatistikleri hesapla
        triggers_count = {}
        for q in all_processed_quotes:
            trig = q.get("trigger", "Unknown")
            triggers_count[trig] = triggers_count.get(trig, 0) + 1

        report["total_quotes"] = len(all_processed_quotes)
        report["trigger_distribution"] = triggers_count
        report["first_5_quotes"] = all_processed_quotes[:5]
        report["match_summary"] = {
            "matched_count": match_data["matched_count"],
            "needs_review_count": match_data["needs_review_count"],
            "unmatched_count": match_data["unmatched_count"]
        }

        # 4. JSON Çıktısını Projenin Veri Klasörüne Kaydet (Adım 7)
        champ_output_dir = os.path.join(CHAMPIONS_DIR, champion)
        os.makedirs(champ_output_dir, exist_ok=True)
        out_json_path = os.path.join(champ_output_dir, f"{champion}_voice_quotes.json")

        # Mevcut JSON varsa güncelle (skin bazında birleştir)
        master_data = {}
        if os.path.exists(out_json_path):
            try:
                with open(out_json_path, "r", encoding="utf-8") as f:
                    master_data = json.load(f)
            except Exception:
                master_data = {}

        master_data["champion"] = champion
        master_data["last_updated"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        master_data["legal_notice"] = (
            "Wiki quotes CC BY-SA (https://wiki.leagueoflegends.com/). "
            "Game audio and characters belong to Riot Games Inc. "
            "YouTube CC belongs to content creators."
        )
        if "skins" not in master_data:
            master_data["skins"] = {}

        master_data["skins"][skin_name] = {
            "skin_name": skin_name,
            "source": report["source_used"],
            "quote_count": len(all_processed_quotes),
            "quotes": all_processed_quotes
        }

        with open(out_json_path, "w", encoding="utf-8") as f:
            json.dump(master_data, f, ensure_ascii=False, indent=2)

        report["output_file"] = out_json_path
        return report
