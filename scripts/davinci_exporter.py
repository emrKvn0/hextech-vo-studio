import os
import re
import json
import struct
import hashlib
import urllib.parse
from xml.sax.saxutils import escape

class DaVinciTimelineExporter:
    """
    Industry-standard DaVinci Resolve Timeline Exporter.
    Generates both FCP 7 XML (xmeml v5) and FCPXML v1.8 formats with:
    - Smart YouTube Narrative Ordering (Target Encounters -> Ult -> Skills -> General)
    - Automatic SFX / Grunt filtering for crystal-clean voice lines
    - Precise dynamic gaps between clips
    """

    @staticmethod
    def get_audio_info_fast(file_path):
        """Ultra-fast binary WAV duration & format parser (under 0.1ms per file)."""
        try:
            with open(file_path, 'rb') as f:
                header = f.read(12)
                if len(header) < 12 or header[:4] != b'RIFF' or header[8:12] != b'WAVE':
                    size = os.path.getsize(file_path)
                    return max(0.2, size / 176400.0), 44100, 2, 16

                channels = 2
                samplerate = 44100
                bitdepth = 16
                byterate = 176400
                datasize = 0

                while True:
                    chunk_header = f.read(8)
                    if len(chunk_header) < 8:
                        break
                    chunk_id, chunk_size = struct.unpack('<4sI', chunk_header)
                    if chunk_id == b'fmt ':
                        fmt_data = f.read(chunk_size)
                        if len(fmt_data) >= 16:
                            audio_fmt, channels, samplerate, byterate, block_align, bitdepth = struct.unpack('<HHIIHH', fmt_data[:16])
                    elif chunk_id == b'data':
                        datasize = chunk_size
                        break
                    else:
                        f.seek(chunk_size, 1)

                if datasize > 0 and byterate > 0:
                    dur = datasize / float(byterate)
                    return max(0.1, dur), samplerate, channels, bitdepth
                else:
                    size = os.path.getsize(file_path)
                    return max(0.2, size / float(byterate if byterate > 0 else 176400)), samplerate, channels, bitdepth
        except Exception:
            try:
                size = os.path.getsize(file_path)
                return max(0.2, size / 176400.0), 44100, 2, 16
            except Exception:
                return 1.0, 44100, 2, 16

    @classmethod
    def get_narrative_sort_key(cls, file_path):
        """
        Assigns priority scores so YouTube videos start with the most engaging lines:
        1. Character-specific Target Encounters & Kills (Bel'Veth, Yasuo, Briar etc.)
        2. Epic Monster / Pentakill / General Encounters
        3. Ultimate (R) & Skill Lines (Q, W, E)
        4. Joke, Taunt, Laugh (Şaka, Kışkırtma, Kahkaha)
        5. Selection / Ban & General Replikler
        6. Item Purchase / Store (Eşya Alımı & Mağaza)
        7. Recall, Respawn & Death (Dönüş, Canlanma, Ölüm)
        8. Movement & Attack Lines (Hareket & Saldırı)
        """
        fn = os.path.basename(file_path).lower()
        parent = os.path.basename(os.path.dirname(file_path)).lower()

        # 1. Specific Target Encounters & Kills (Bel'Veth, Yasuo, Briar etc.)
        if 'hedef_' in fn or 'target_' in fn:
            target_part = fn.split('hedef_')[-1].split('_')[0] if 'hedef_' in fn else ''
            is_encounter = 'karsilasma' in fn or 'encounter' in fn
            # Put encounter first, then kill for that champion
            return (1, target_part, 0 if is_encounter else 1, fn)

        # 2. Pentakill / Epic Monster / General Special Encounters
        if any(k in fn for k in ['pentakill', 'epik_canavar', 'baron', 'ejder', 'dragon', 'kule_yikma', 'first_blood', 'ilk_kan']):
            return (2, 'a_special', 0, fn)
        if 'karsilasma' in fn or 'encounter' in fn or '5_ozel' in parent:
            return (2, 'b_encounter', 0, fn)
        if 'katletme' in fn or 'kill' in fn:
            return (2, 'c_kill', 0, fn)

        # 3. Ultimate (R) & Skills (Q, W, E)
        if 'ulti' in fn or 'r_ulti' in fn or '4_r' in parent:
            return (3, 'a_ulti', 0, fn)
        if 'q_yetenek' in fn or '1_q' in parent:
            return (3, 'b_q', 0, fn)
        if 'w_yetenek' in fn or '2_w' in parent:
            return (3, 'c_w', 0, fn)
        if 'e_yetenek' in fn or '3_e' in parent:
            return (3, 'd_e', 0, fn)

        # 4. Joke, Taunt, Laugh
        if any(k in fn for k in ['saka', 'kiskirtma', 'kahkaha', 'joke', 'taunt', 'laugh']) or '7_saka' in parent:
            return (4, 'taunts', 0, fn)

        # 5. Selection / Ban & General Replikler
        if any(k in fn for k in ['secim', 'pick', 'yasak', 'ban']) or '10_genel' in parent or 'genel_replik' in fn:
            return (5, 'general', 0, fn)

        # 6. Item Purchase / Store
        if 'esya' in fn or 'magaza' in fn or 'item' in fn or 'shop' in fn or '6_esya' in parent:
            return (6, 'items', 0, fn)

        # 7. Recall, Respawn, Death
        if 'usse_donus' in fn or 'recall' in fn:
            return (7, 'a_recall', 0, fn)
        if 'canlanma' in fn or 'respawn' in fn:
            return (7, 'b_respawn', 0, fn)
        if 'olum' in fn or 'death' in fn or '8_donus' in parent:
            return (7, 'c_death', 0, fn)

        # 8. Movement & Attack
        if 'hareket' in fn or 'move' in fn or 'yurume' in fn or '9_hareket' in parent:
            return (8, 'a_move', 0, fn)
        if 'saldiri' in fn or 'attack' in fn:
            return (8, 'b_attack', 0, fn)

        return (9, parent, 0, fn)

    @classmethod
    def is_voiced_dialogue(cls, file_path):
        """
        Action-Driven & Semantic Dialogue Filter (Riot Wwise Event-Aware).
        Eliminates vocal SFX, grunts, shouts, roars, and swing efforts,
        while rigorously protecting true voiced speech and skill dialogues.
        """
        fn = os.path.basename(file_path).lower()
        parent = os.path.basename(os.path.dirname(file_path)).lower()
        dur, r, c, b = cls.get_audio_info_fast(file_path)

        # 0. Global Micro-Noise & Radio Frequency / Static Filter
        if dur < 0.90:
            return False

        # 1. Definite Exclusions (Explicit SFX, Efforts, Grunts, Breaths, Roars, Effects)
        sfx_keywords = [
            '_sfx_', '_swing_', '_hit_', '_effort_', '_grunt_', '_breathe_', '_breath_',
            '_pant_', '_groan_', '_gasp_', '_pain_', '_footstep_', '_vfx_', '_loop_',
            '_efor_', '_homurtu_', '_inilti_', '_efekt_', '_noise_', '_static_', '_beep_'
        ]
        if any(k in fn for k in sfx_keywords) or '11_efekt' in parent or 'efektler' in parent:
            return False

        # 2. Normal Attack Grunts
        if 'normal_saldiri' in fn or 'saldiri_efor' in fn:
            return False

        # 3. Known Radio Static Artifacts
        if any(k in fn for k in ['genel_replik_02', 'genel_replik_03']):
            return False

        # 4. Protected High-Confidence Dialogue Categories (Atıflar, Şaka, Mağaza, Dönüş)
        if any(k in parent for k in ['5_ozel', '7_saka', '6_esya', '8_donus']):
            return True

        if 'hedef_' in fn or 'karsilasma' in fn or 'katletme' in fn or 'pentakill' in fn:
            return True

        # 5. General Quotes (Genel Replikler) >= 1.20s
        if '10_genel' in parent or 'genel_replik' in fn:
            return dur >= 1.20

        # 6. Movement Lines >= 1.20s
        if 'hareket' in fn or 'yurume' in fn or '9_hareket' in parent:
            return dur >= 1.20

        # 7. Combat Skills (Q, W, E) & Ult (R): Pure deterministic duration & naming
        if any(k in parent for k in ['1_q', '2_w', '3_e', '4_r']) or any(k in fn for k in ['q_yetenek', 'w_yetenek', 'e_yetenek', 'r_ulti']):
            return dur >= 0.70

        return dur >= 0.80


    @staticmethod
    def format_srt_time(seconds):
        """Formats floating seconds to SRT timecode (hh:mm:ss,mmm)."""
        millis = int(round((seconds - int(seconds)) * 1000))
        if millis >= 1000:
            millis = 999
        total_sec = int(seconds)
        hours = total_sec // 3600
        minutes = (total_sec % 3600) // 60
        secs = total_sec % 60
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    _transcripts_cache = None

    @classmethod
    def get_transcript_cache(cls):
        if cls._transcripts_cache is None:
            root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            cache_file = os.path.join(root_dir, "cache", "master_transcripts.json")
            if os.path.exists(cache_file):
                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        cls._transcripts_cache = json.load(f)
                except Exception:
                    cls._transcripts_cache = {}
            else:
                cls._transcripts_cache = {}
        return cls._transcripts_cache

    @classmethod
    def save_transcript_cache(cls, cache_data=None):
        if cache_data is not None:
            cls._transcripts_cache = cache_data
        if cls._transcripts_cache is not None:
            root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            cache_file = os.path.join(root_dir, "cache", "master_transcripts.json")
            try:
                os.makedirs(os.path.dirname(cache_file), exist_ok=True)
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump(cls._transcripts_cache, f, ensure_ascii=False, indent=2)
            except Exception:
                pass

    @staticmethod
    def fix_champion_names_in_text(text: str) -> str:
        """Whisper transkripsiyonunda yanlış yazılan LoL şampiyon isimlerini ve fonetik replik hatalarını düzeltir."""
        if not text:
            return ""
        replacements = [
            (r'\bKane\b', 'Kayn'),
            (r'\bkane\b', 'Kayn'),
            (r'\bYasua\b', 'Yasuo'),
            (r'\bRivın\b', 'Riven'),
            (r'\bRivin\b', 'Riven'),
            (r'\bKatarine\b', 'Katarina'),
            (r'\bTresh\b', 'Thresh'),
            (r'\bTreş\b', 'Thresh'),
            (r'\bVeyn\b', 'Vayne'),
            (r'\bViktör\b', 'Viktor'),
            (r'\bHeimer\b', 'Heimerdinger'),
            (r'\bKhaZix\b', "Kha'Zix"),
            (r'\bKhazix\b', "Kha'Zix"),
            (r'\bKogMaw\b', "Kog'Maw"),
            (r'\bKogmaw\b', "Kog'Maw"),
            (r'\bVelKoz\b', "Vel'Koz"),
            (r'\bVelkoz\b', "Vel'Koz"),
            (r'\bRekSai\b', "Rek'Sai"),
            (r'\bReksai\b', "Rek'Sai"),
            (r'\bKaiSa\b', "Kai'Sa"),
            (r'\bKaisa\b', "Kai'Sa"),
            (r'\bChoGath\b', "Cho'Gath"),
            (r'\bChogath\b', "Cho'Gath"),
            (r'\bLe Blanc\b', 'LeBlanc'),
            (r'\bLeblanc\b', 'LeBlanc'),
            (r'\bMasteryi\b', 'Master Yi'),
            (r'\bMaster Yi\b', 'Master Yi'),
            (r'\bTahmkench\b', 'Tahm Kench'),
            # LoL Fonetik & Replik Düzeltmeleri
            (r'\bRakam\b', 'Rakan'),
            (r'\bZaya\b', 'Xayah'),
            (r'\bzaya\b', 'Xayah'),
            (r'\bAlfa yeşelerle\b', 'Aphae şelalesini'),
            (r'\bboşuna gidiyor mu\b', 'hoşuna gidiyor mu'),
            (r'\bherkesi güzum\b', 'herkese gıcığım'),
            (r'\bBan adamım\b', 'Bana da mı?'),
            (r'\bBuri stebile ne\b', 'Birisini işte!'),
            (r'\bMiyella\b', 'Miella'),
            (r'\bMiele\b', 'Mieli'),
            (r'\bvasayalar\b', 'Vastayalar'),
            (r'\bYa zırak\b', 'Yazık'),
            (r'\btokadır Akan\b', 'tokadı Rakan'),
            (r'\bDalsyuna\b', 'Dal şuna'),
            (r'\bBitiri şene\b', 'Bitir işini')
        ]
        res = text
        for pat, repl in replacements:
            res = re.sub(pat, repl, res, flags=re.IGNORECASE if not pat.startswith(r'\b[A-Z]') else 0)
        return res

    @classmethod
    def lookup_or_transcribe(cls, wav_path, speaker="", raw_event="", wem_id=None):
        """
        Zaten çıkarılmış replikleri diskteki master_transcripts cache'ten anında okur.
        Metin-ses ilişkisinin %100 deterministik ve benzersiz olmasını garanti eder.
        Varyasyonların birbirinin repliğini ezmesini kesinlikle engeller.
        """
        if not wav_path or not os.path.isfile(wav_path):
            return ""

        cache = cls.get_transcript_cache()
        fn = os.path.basename(wav_path)

        # 1. Dosya içeriğinin MD5 hash'i (Her benzersiz ses = Farklı hash)
        file_hash = None
        try:
            with open(wav_path, 'rb') as f:
                file_hash = hashlib.md5(f.read()).hexdigest()
        except Exception:
            file_hash = None

        # 2. wem_id tespit etme (parametreden veya dosya adından)
        detected_wem = str(wem_id).strip() if wem_id else ""
        if not detected_wem:
            m_wid = re.search(r'(\d{7,10})', fn)
            if m_wid:
                detected_wem = m_wid.group(1)

        keys_to_check = []
        if detected_wem:
            keys_to_check.append(detected_wem)
            if speaker and raw_event:
                keys_to_check.append(f"{speaker}_{raw_event}_{detected_wem}")
            keys_to_check.append(f"{speaker}_{detected_wem}.wav" if speaker else f"{detected_wem}.wav")

        if file_hash:
            keys_to_check.append(f"hash_{file_hash}")

        keys_to_check.append(fn)

        # DİKKAT: Eğer detected_wem VARSA, keys_to_check içine ASLA genel f"{speaker}_{raw_event}" eklenmez!
        # Çünkü o event altında başka varyasyonlar vardır ve hepsi ilk varyasyonun metnini kapmamalıdır!
        if not detected_wem and speaker and raw_event:
            keys_to_check.append(f"{speaker}_{raw_event}")

        for k in keys_to_check:
            if k in cache and cache[k]:
                return cls.fix_champion_names_in_text(cache[k])

        spoken = ""
        try:
            from ai_voice_detector import AIVoiceDetector
            if AIVoiceDetector:
                has_sp, text = AIVoiceDetector.is_spoken_dialogue(wav_path)
                if text and text.strip():
                    spoken = cls.fix_champion_names_in_text(text.strip())
        except Exception:
            spoken = ""

        if spoken:
            # Sadece bu varyasyona özel anahtarlara kaydet (Genel event key'ine kaydetme!)
            keys_to_save = []
            if detected_wem:
                keys_to_save.append(detected_wem)
                if speaker and raw_event:
                    keys_to_save.append(f"{speaker}_{raw_event}_{detected_wem}")
            if file_hash:
                keys_to_save.append(f"hash_{file_hash}")
            keys_to_save.append(fn)

            for k in keys_to_save:
                cache[k] = spoken
            cls.save_transcript_cache()

        return spoken

    @staticmethod
    def balance_wrap(text: str, max_chars: int = 38) -> str:
        """
        Replik metnini kadraj dışına taşmayacak şekilde 38 karakteri aşınca 
        en uygun kelime boşluklarından satırlara böler (2 veya gerekiyorsa 3 satır).
        """
        if not text or len(text) <= max_chars:
            return text
        words = text.strip().split()
        if not words:
            return text
        lines = []
        cur_line = []
        cur_len = 0
        for w in words:
            add_len = len(w) + (1 if cur_line else 0)
            if cur_len + add_len > max_chars:
                if cur_line:
                    lines.append(' '.join(cur_line))
                    cur_line = [w]
                    cur_len = len(w)
                else:
                    lines.append(w)
                    cur_line = []
                    cur_len = 0
            else:
                cur_line.append(w)
                cur_len += add_len
        if cur_line:
            lines.append(' '.join(cur_line))
        return '\n'.join(lines)

    @staticmethod
    def turkish_upper(text: str) -> str:
        """
        Türkçe karakter kurallarına uygun BÜYÜK HARF dönüşümü (i -> İ, ı -> I).
        Jarvan IV gibi Roma rakamı içeren isimlerde 'IV' korunur, 'İV' yapılmaz.
        """
        if not text:
            return ""
        mapping = {
            'i': 'İ',
            'ı': 'I',
            'ç': 'Ç',
            'ş': 'Ş',
            'ğ': 'Ğ',
            'ü': 'Ü',
            'ö': 'Ö'
        }
        special_names = {
            'irelia': 'İRELİA',
            'illaoi': 'İLLAOİ',
            'ivern': 'İVERN',
            'jarvan iv': 'JARVAN IV',
            'jarvan': 'JARVAN'
        }
        low = text.lower().strip()
        if low in special_names:
            return special_names[low]
        res = ''.join(mapping.get(c, mapping.get(c.lower(), c.upper())) if c.lower() in mapping else c.upper() for c in text)
        # Jarvan IV ve Roma rakamlarında 'İV' -> 'IV' düzeltmesi
        res = re.sub(r'\bJARVAN\s+İV\b', 'JARVAN IV', res, flags=re.IGNORECASE)
        res = re.sub(r'\bİV\b', 'IV', res)
        res = re.sub(r'\bİİ\b', 'II', res)
        res = re.sub(r'\bİİİ\b', 'III', res)
        res = re.sub(r'\bİX\b', 'IX', res)
        return res

    @staticmethod
    def turkish_to_ascii(text: str) -> str:
        """Dosya adları ve URI'ler için Türkçe karakterleri ASCII harflere dönüştürür."""
        if not text:
            return ""
        tr_map = str.maketrans({
            'ı': 'i', 'I': 'I', 'İ': 'I', 'i': 'i',
            'ğ': 'g', 'Ğ': 'G',
            'ü': 'u', 'Ü': 'U',
            'ş': 's', 'Ş': 'S',
            'ö': 'o', 'Ö': 'O',
            'ç': 'c', 'Ç': 'C'
        })
        return text.translate(tr_map)

    @classmethod
    def clean_dialogue_and_speaker(cls, file_name: str, spoken_text: str, action_type: str = "Replik"):
        """
        Karakter adını ve repliği 'Spam / YouTube' şablonuna göre ayrıştırır:
        - 1. Satır: Türkçe BÜYÜK HARFLİ şampiyon adı (örn. TALİYAH, AHRİ, YONE)
        - 2. Satır: Tırnaksız, temizlenmiş ve dengeli sarılmış replik
        """
        spk_raw = file_name.split('_')[0].capitalize()
        if file_name.lower().startswith('ruby_'):
            parts = file_name.split('_')
            spk_raw = parts[1].capitalize() if len(parts) > 1 else "TFT"

        clean_text = spoken_text.strip() if spoken_text else ""
        if ':' in clean_text:
            parts = clean_text.split(':', 1)
            if len(parts[0].strip().split()) <= 2:
                clean_text = parts[1].strip()

        # Tırnakları ve gereksiz sembolleri temizle
        clean_text = clean_text.strip(' "\'“”«»')
        if not clean_text:
            clean_text = f"({action_type})"

        wrapped_quote = cls.balance_wrap(clean_text, max_chars=42)
        spk_upper = cls.turkish_upper(spk_raw)

        return spk_upper, wrapped_quote

    @classmethod
    def get_target_reference_sort_key(cls, file_path, target_champ="Yasuo"):
        """
        Dramatik / Hikaye Odaklı YouTube Sıralaması:
        1. Kanca (Hook) & En Yakın Bağlar / Kardeş (Yone vb.)
        2. Öğrenci / Çırak / Ruined King Yol Arkadaşları (Taliyah, Ahri, Braum, Illaoi)
        3. Kader Ortakları & Ezeli Rakipler (Riven, Master Yi, Shen, Zed)
        4. Diğer Karşılaşmalar (A-Z)
        5. Katletme / Dövüş Replikleri
        6. Alaycı / Mizahi Replikler (Tahm Kench, Neeko, Zoe)
        """
        fn = os.path.basename(file_path).lower()
        spk = fn.split('_')[0].lower()
        t_clean = target_champ.lower()
        
        lore_priorities = {
            'yasuo': {
                'yone': 1,       # Abisi - En Vurucu Hook
                'taliyah': 2,    # Çırağı
                'ahri': 3,       # Ruined King Yoldaşı
                'braum': 4,      # Ruined King Yoldaşı
                'illaoi': 4,     # Ruined King Yoldaşı
                'riven': 5,      # Rüzgar Tekniği & Suçlayıcı
                'masteryi': 6,   # Wuju / Ionia Kılıç Ustası
                'shen': 7,       # Ionia Denge Koruyucusu
                'zed': 7,        # Gölge Tarikatı
                'kayn': 8,       # Gölge Mürit
                'swain': 9,      # Noxus Generali
                'irelia': 10,    # Ionia Direnişi
                'warwick': 15,   # Canavar
                'urgot': 16,     # Zaun Celladı
                'tahmkench': 90, # Alaycı Şeytan (Son Kısım)
                'neeko': 91,     # Taklitçi / Eğlenceli
                'zoe': 92        # Eğlenceli
            },
            'ahri': {
                'yasuo': 1,      # Ruined King Yoldaşı
                'yone': 2,       # Ionia Ruh Dünyası
                'illaoi': 3,     # Ruined King Yoldaşı
                'braum': 3,      # Ruined King Yoldaşı
                'lillia': 4,     # Ruhlar / Düşler
                'irelia': 5,     # Ionia
                'xayah': 6,      # Vastaya Kardeşliği / Çatışma
                'rakan': 6,      # Vastaya
                'swain': 7,      # Noxus
                'hwei': 8,       # Ionia Ressamı
                'neeko': 90,     # Taklit / Şaka
                'tahmkench': 91  # Alaycı
            }
        }
        
        champ_dict = lore_priorities.get(t_clean, {})
        priority = champ_dict.get(spk, 50)
        is_kill = 1 if ('katletme' in fn or 'kill' in fn) else 0
        return (priority, spk, is_kill, fn)

    @classmethod
    def generate_srt_subtitles(cls, sorted_files, output_srt_path, gap_seconds=0.2, target_champion=""):
        """
        DaVinci Resolve ile %100 senkronize .srt altyazı dosyası üretir.
        Timeline'a sürüklendiğinde tek tıkla tam ses anında ekranda görünür.
        """
        try:
            from ai_voice_detector import AIVoiceDetector
        except ImportError:
            try:
                import sys
                sys.path.append(os.path.dirname(os.path.abspath(__file__)))
                from ai_voice_detector import AIVoiceDetector
            except Exception:
                AIVoiceDetector = None

        srt_lines = []
        current_time = 0.0

        for idx, file_item in enumerate(sorted_files):
            abs_path = os.path.abspath(file_item['audio_path'] if isinstance(file_item, dict) else file_item)
            file_name = os.path.basename(abs_path)
            duration_sec, _, _, _ = cls.get_audio_info_fast(abs_path)

            if idx > 0 and gap_seconds > 0:
                current_time += gap_seconds

            start_time = current_time
            end_time = start_time + duration_sec
            current_time = end_time

            start_str = cls.format_srt_time(start_time)
            end_str = cls.format_srt_time(end_time)

            # Konuşan Şampiyon ve Eylem
            spk_raw = file_name.split('_')[0].capitalize()
            action_type = "Replik"
            if 'karsilasma' in file_name:
                action_type = "Karşılaşma"
            elif 'katletme' in file_name:
                action_type = "Katletme"
            elif 'yetenek' in file_name:
                action_type = "Yetenek"

            # Faster-Whisper veya Master Transcript
            if isinstance(file_item, dict) and file_item.get('transcript'):
                spk_upper = file_item.get('speaker', spk_raw).upper()
                clean_quote = file_item.get('transcript', '')
            else:
                spoken_text = ""
                if AIVoiceDetector:
                    try:
                        _, spoken_text = AIVoiceDetector.is_spoken_dialogue(abs_path)
                    except Exception:
                        spoken_text = ""
                spk_upper, clean_quote = cls.clean_dialogue_and_speaker(file_name, spoken_text, action_type)
            sub_text = f"{spk_upper}\n{clean_quote}" if clean_quote else spk_upper

            srt_lines.append(f"{idx + 1}")
            srt_lines.append(f"{start_str} --> {end_str}")
            srt_lines.append(sub_text)
            srt_lines.append("")

        os.makedirs(os.path.dirname(os.path.abspath(output_srt_path)), exist_ok=True)
        with open(output_srt_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(srt_lines))


    _SKINS_DB = None
    _SPLASH_CACHE = {}

    @classmethod
    def get_skins_database(cls):
        """Loads and caches all_lol_skins_database.json (2160+ skins)."""
        if cls._SKINS_DB is not None:
            return cls._SKINS_DB

        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        db_paths = [
            os.path.join(root_dir, "all_lol_skins_database.json"),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "all_lol_skins_database.json"),
            os.path.abspath("all_lol_skins_database.json")
        ]
        import json
        for p in db_paths:
            if os.path.exists(p):
                try:
                    with open(p, 'r', encoding='utf-8') as f:
                        cls._SKINS_DB = json.load(f)
                        return cls._SKINS_DB
                except Exception as e:
                    print(f"⚠️ all_lol_skins_database.json okunamadı ({p}): {e}")

        cls._SKINS_DB = []
        return cls._SKINS_DB

    @classmethod
    def format_event_action_template(cls, raw_event: str, action_type: str = "") -> str:
        """
        Riot Wwise olay adını ve eylem türünü temiz, şablonlaşmış Türkçe eylem kalıbına çevirir:
        Örn:
        - Taunt / Taunt3D -> 'Kışkırtınca'
        - TauntResponse -> 'Kışkırtmaya Yanıt Verince'
        - FirstEncounter / Encounter -> 'Karşılaşınca'
        - FirstEncounterAlly -> 'Dostla Karşılaşınca'
        - FirstEncounterEnemy -> 'Düşmanla Karşılaşınca'
        - Kill / ChampionKill -> 'Katledince'
        - Attack / BasicAttack -> 'Saldırınca'
        - Joke -> 'Şaka Yapınca'
        - JokeResponse -> 'Şakaya Yanıt Verince'
        - Assist -> 'Asist Yapınca'
        - SpellR / Ult / Ultimate -> 'Ulti Kullanınca'
        - SpellQ / Spell1 -> 'Q Yeteneği Kullanınca'
        - SpellW / Spell2 -> 'W Yeteneği Kullanınca'
        - SpellE / Spell3 -> 'E Yeteneği Kullanınca'
        - Hit / Spell / Cast -> 'Yetenek Kullanınca'
        - Recall -> 'Üsse Dönerken'
        - Respawn / Revive -> 'Yeniden Canlanınca'
        - Death / Die -> 'Ölünce'
        - Item / Shop -> 'Eşya Alınca'
        - Turret / Tower -> 'Kule Yıkınca'
        - Dragon / Baron -> 'Epik Canavar Katledince'
        - Penta / Pentakill -> 'Pentakill Atınca'
        - FirstBlood -> 'İlk Kanı Dökünce'
        - Move -> 'Hareket Ederken'
        - Laugh -> 'Kahkaha Atınca'
        - Dance -> 'Dans Ederken'
        """
        import re
        ev = str(raw_event or '').lower()
        act = str(action_type or '').lower()

        if 'tauntresponse' in ev or 'taunt_response' in ev:
            return 'Kışkırtmaya Yanıt Verince'
        if 'jokeresponse' in ev or 'joke_response' in ev:
            return 'Şakaya Yanıt Verince'
        if 'taunt' in ev or 'kiskirtma' in act:
            return 'Kışkırtınca'
        if 'joke' in ev or 'saka' in act:
            return 'Şaka Yapınca'
        if 'firstblood' in ev:
            return 'İlk Kanı Dökünce'
        if 'kill' in ev or 'katletme' in act:
            return 'Katledince'
        if 'attack' in ev or 'saldiri' in act:
            return 'Saldırınca'
        if 'firstencounterally' in ev or 'ally' in ev or 'dost' in act:
            return 'Dostla Karşılaşınca'
        if 'firstencounterenemy' in ev or 'dusman' in act:
            return 'Düşmanla Karşılaşınca'
        if 'firstencounter' in ev or 'encounter' in ev or 'karsilasma' in act:
            for fac_k, fac_name in [('ionia', 'Ionia'), ('noxus', 'Noxus'), ('demacia', 'Demacia'), ('freljord', 'Freljord'), ('piltover', 'Piltover'), ('zaun', 'Zaun'), ('shurima', 'Shurima'), ('bilgewater', 'Bilgewater'), ('targon', 'Targon'), ('shadowisles', 'Gölge Adalar'), ('bandle', 'Yordle'), ('void', 'Hiçlik'), ('darkin', 'Darkin'), ('vastaya', 'Vastaya')]:
                if fac_k in ev:
                    return f"Düşman {fac_name} Şampiyonu ile İlk Karşılaşınca"
            return 'Düşman Şampiyonla İlk Karşılaşınca'
        if 'assist' in ev:
            return 'Asist Yapınca'
        if 'spellr' in ev or 'spell4' in ev or '_r_' in ev or 'ult' in ev:
            return 'Ulti Kullanınca'
        if 'spellq' in ev or 'spell1' in ev or '_q_' in ev:
            return 'Q Yeteneği Kullanınca'
        if 'spellw' in ev or 'spell2' in ev or '_w_' in ev:
            return 'W Yeteneği Kullanınca'
        if 'spelle' in ev or 'spell3' in ev or '_e_' in ev:
            return 'E Yeteneği Kullanınca'
        if 'hit' in ev or 'yetenek' in act:
            return 'Yetenek Kullanınca'
        if 'recall' in ev:
            return 'Üsse Dönerken'
        if 'respawn' in ev or 'revive' in ev:
            return 'Yeniden Canlanınca'
        if 'death' in ev or 'die' in ev:
            return 'Ölünce'
        if any(k in ev for k in ['item', 'shop', 'ward', 'potion', 'trinket', 'forge', 'ornn', 'biscuit', 'elixir', 'hourglass', 'zhonya', 'gargoyle', 'redemption', 'locket', 'phantom', 'dancer', 'dansçı']):
            try:
                import event_categorizer
                item_tr = event_categorizer.resolve_item_event_turkish(raw_event)
                if item_tr:
                    return item_tr
            except Exception:
                pass
            return 'Eşya Satın Alınca'
        if 'turret' in ev or 'tower' in ev:
            return 'Kule Yıkınca'
        if 'dragon' in ev or 'baron' in ev:
            return 'Epik Canavar Katledince'
        if 'penta' in ev:
            return 'Pentakill Atınca'
        if 'laugh' in ev:
            return 'Kahkaha Atınca'
        if 'dance' in ev and not any(k in ev for k in ['dansçı', 'dancer', 'phantom']):
            return 'Dans Ederken'
        if 'move' in ev:
            return 'Hareket Ederken'

        if act:
            clean_act = re.sub(r'#\d+', '', act).strip('_ ')
            return clean_act.replace('_', ' ').capitalize()

        return 'Özel Replik'

    @staticmethod
    def _normalize_name_token(text):
        import re
        s = str(text or '').lower()
        mapping = {'ı': 'i', 'ğ': 'g', 'ü': 'u', 'ş': 's', 'ö': 'o', 'ç': 'c'}
        for k, v in mapping.items():
            s = s.replace(k, v)
        return re.sub(r'[^a-z0-9]', '', s)

    @classmethod
    def resolve_speaker_and_skin(cls, file_path, target_champion=None):
        """
        Replik dosyasından konuşan şampiyonu ve kostümünü %100 doğrulukla tespit eder:
        1. Atıf klasörleri: .../Tahmkench/Varsayilan_Hali/tahmkench_01.wav -> Tahm Kench, Varsayılan
        2. Normal kostüm klasörleri: .../Champions/Yasuo/Gecenin_Kilici_Yasuo/... -> Yasuo, Gecenin Kılıcı
        3. Dosya adı prefixleri: ruby_..., yone_...
        4. all_lol_skins_database.json üzerinden en doğru skin_data nesnesini döner.
        """
        import re
        norm_path = os.path.abspath(file_path).replace(os.sep, '/')
        parts = norm_path.split('/')
        fn = parts[-1].lower()

        clean_fn = fn
        if clean_fn.startswith('ruby_'):
            clean_fn = clean_fn[5:]
        fn_champ = clean_fn.split('_')[0]

        is_target_ref = any('yapilan' in p.lower() and 'atiflar' in p.lower() for p in parts)
        speaker_champ = None
        speaker_skin = None

        if is_target_ref:
            parent = parts[-2] if len(parts) >= 2 else ''
            grandparent = parts[-3] if len(parts) >= 3 else ''
            norm_gp = cls._normalize_name_token(grandparent)
            norm_parent = cls._normalize_name_token(parent)
            norm_fn = cls._normalize_name_token(fn_champ)

            if norm_fn in norm_gp or norm_gp in norm_fn:
                speaker_champ = grandparent
                speaker_skin = parent
            elif norm_fn in norm_parent or norm_parent in norm_fn:
                speaker_champ = parent
                speaker_skin = ''
            else:
                speaker_champ = fn_champ
                speaker_skin = parent
        else:
            for i, p in enumerate(parts):
                if p.lower() == 'champions' and i + 2 < len(parts):
                    speaker_champ = parts[i + 1]
                    speaker_skin = parts[i + 2]
                    break

        if not speaker_champ:
            speaker_champ = fn_champ

        skins = cls.get_skins_database()
        if not skins:
            return None

        c_norm = cls._normalize_name_token(speaker_champ)
        c_candidates = [s for s in skins if c_norm == cls._normalize_name_token(s.get('champion_name', '')) or c_norm == cls._normalize_name_token(s.get('champion_alias', ''))]
        if not c_candidates:
            c_candidates = [s for s in skins if c_norm in cls._normalize_name_token(s.get('champion_name', '')) or c_norm in cls._normalize_name_token(s.get('champion_alias', ''))]

        if not c_candidates:
            return None

        cleaned_hint = (speaker_skin or '').lower().replace('_hali', '').replace('hali', '').replace(c_norm, '').strip('_ ')
        if not cleaned_hint or any(k in cleaned_hint for k in ['varsayilan', 'default', 'base', 'orijinal']):
            for s in c_candidates:
                if s.get('is_base') or s.get('skin_num') == 0:
                    return s
            return c_candidates[0]

        TR_EN_MAP = {
            'ruh': 'spirit', 'cicek': 'blossom', 'cicegi': 'blossom',
            'gece': 'night', 'safak': 'dawn', 'kilic': 'bringer', 'kilici': 'bringer',
            'kod': 'project', 'adi': 'project', 'vahsi': 'high', 'bati': 'noon', 'batili': 'noon',
            'kanli': 'blood', 'ay': 'moon', 'savas': 'battle', 'akademi': 'academia',
            'okyanus': 'ocean', 'sarki': 'song', 'sarkisi': 'song', 'golge': 'shadow',
            'dovme': 'ink', 'dovmeli': 'inkshadow', 'prestij': 'prestige', 'deniz': 'sea',
            'kurdu': 'dog', 'hakikat': 'truth', 'ruya': 'dream', 'ejder': 'dragon',
            'ejderi': 'dragon', 'jeton': 'battle', 'dusmani': 'boss', 'cadi': 'bewitching'
        }

        tokens = [t for t in re.split(r'[\s\-_]+', cleaned_hint) if t]
        expanded_tokens = list(tokens)
        for t in tokens:
            nt = cls._normalize_name_token(t)
            if nt in TR_EN_MAP:
                expanded_tokens.append(TR_EN_MAP[nt])

        best_match = None
        best_score = 0
        for s in c_candidates:
            name_tr = cls._normalize_name_token(s.get('name_tr', ''))
            name_en = cls._normalize_name_token(s.get('name_en', ''))
            score = 0
            for tok in expanded_tokens:
                ntok = cls._normalize_name_token(tok)
                if len(ntok) >= 3:
                    if ntok in name_tr:
                        score += 15
                    if ntok in name_en:
                        score += 20
            if score > best_score:
                best_score = score
                best_match = s

        return best_match or c_candidates[0]

    @classmethod
    def get_or_download_splash_art(cls, skin_data, force_4k=True):
        """
        Kostümün 4K Splash Art görselini disk önbelleğinden döner;
        yoksa arka planda CDN / Static Wallpaper Engine üzerinden otomatik indirir.
        """
        if not skin_data:
            return None

        skin_id = skin_data.get('skin_id', 0)
        c_name = skin_data.get('champion_name') or skin_data.get('champion_alias') or 'Champion'
        s_name = skin_data.get('name_tr') or skin_data.get('name_en') or 'Kostum'

        cache_key = f"{skin_id}_{c_name}_{s_name}"
        if cache_key in cls._SPLASH_CACHE and os.path.exists(cls._SPLASH_CACHE[cache_key]):
            return cls._SPLASH_CACHE[cache_key]

        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        # 1. Önceden indirilmiş Duvar Kağıtları kontrolü (Eğer LoR kartı DEĞİLSE LoL Duvar Kağıtlarına bak!)
        import re
        is_lor_skin = str(skin_id).startswith("LOR_")
        c_clean = re.sub(r'[\\/*?:"<>|]', '', str(c_name)).replace(' ', '_').strip('_')
        s_clean = re.sub(r'[\\/*?:"<>|]', '', str(s_name)).replace(' ', '_').strip('_')

        if is_lor_skin:
            candidates = [
                os.path.join(root_dir, "cache", "splashes", f"LOR_{c_clean}_{skin_id}_4K.jpg"),
                os.path.join(root_dir, "cache", "splashes", f"{skin_id}.jpg")
            ]
        else:
            candidates = [
                os.path.join(root_dir, "Duvar Kağıtları", "4K Duvar Kağıtları", c_clean, f"{c_clean}_{s_clean}_4K.jpg"),
                os.path.join(root_dir, "cache", "splashes", f"{c_clean}_{skin_id}_4K.jpg"),
                os.path.join(root_dir, "cache", "splashes", f"{skin_id}.jpg")
            ]

        for cand in candidates:
            if os.path.exists(cand) and os.path.getsize(cand) > 10240:
                cls._SPLASH_CACHE[cache_key] = cand
                return cand

        # 2. Yalnızca LoL kostümleri için static_wallpaper_engine ile 4K indirme dene
        if not is_lor_skin:
            try:
                from static_wallpaper_engine import download_skin_wallpaper
                res = download_skin_wallpaper(skin_data, force_4k=force_4k, set_as_desktop=False)
                if isinstance(res, dict) and res.get('file_path') and os.path.exists(res['file_path']):
                    fp = res['file_path']
                    cls._SPLASH_CACHE[cache_key] = fp
                    return fp
            except Exception:
                pass

        # 3. Fallback: Resmi Riot LoR DataDragon (2048x1024 PNG) / runeterra.ar / CommunityDragon CDN üzerinden indirme
        import urllib.request
        fallback_dir = os.path.join(root_dir, "cache", "splashes")
        os.makedirs(fallback_dir, exist_ok=True)
        fallback_name = f"LOR_{c_clean}_{skin_id}_4K.jpg" if is_lor_skin else f"{c_clean}_{skin_id}_4K.jpg"
        fallback_path = os.path.join(fallback_dir, fallback_name)

        urls_to_try = []
        if skin_data.get('extra_urls'):
            urls_to_try.extend(skin_data['extra_urls'])
        if skin_data.get('splash_url'):
            urls_to_try.append(skin_data['splash_url'])

        if not is_lor_skin:
            c_alias = skin_data.get('champion_alias') or c_name
            skin_num = skin_data.get('skin_num', 0)
            urls_to_try.append(f"https://ddragon.leagueoflegends.com/cdn/img/champion/splash/{c_alias}_{skin_num}.jpg")
            urls_to_try.append(f"https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/champion-splashes/{skin_data.get('champion_id', 0)}/{skin_id}.jpg")

        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'}
        for u in urls_to_try:
            try:
                req = urllib.request.Request(u, headers=headers)
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = resp.read()
                    if len(data) > 10240:
                        try:
                            import io
                            from PIL import Image
                            im = Image.open(io.BytesIO(data)).convert('RGB')
                            im.save(fallback_path, 'JPEG', quality=95)
                        except Exception:
                            with open(fallback_path, 'wb') as out_f:
                                out_f.write(data)
                        cls._SPLASH_CACHE[cache_key] = fallback_path
                        return fallback_path
            except Exception:
                continue

        return None

    @staticmethod
    def get_image_dimensions_fast(image_path):
        """Hızlı görsel boyutu okuyucu (PIL veya varsayılan 3840x2160)."""
        if not image_path or not os.path.exists(image_path):
            return 3840, 2160
        try:
            from PIL import Image
            with Image.open(image_path) as im:
                return im.size
        except Exception:
            return 3840, 2160

    @classmethod
    def render_title_card_png(cls, spk_upper, quote_text, cache_dir, width=1200, height=360):
        """
        DaVinci Resolve'un %100 her sürümünde kusursuz çalışan,
        şeffaf arka planlı, yüksek çözünürlüklü Türkçe altyazı PNG başlık görseli üretir.
        """
        import hashlib
        from PIL import Image, ImageDraw, ImageFont

        os.makedirs(cache_dir, exist_ok=True)
        h_str = hashlib.md5(f"{spk_upper}_{quote_text}".encode('utf-8')).hexdigest()[:12]
        file_name = f"title_{h_str}.png"
        out_path = os.path.join(cache_dir, file_name)

        if os.path.exists(out_path) and os.path.getsize(out_path) > 1024:
            return out_path

        img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        font_paths = [
            r'C:\Windows\Fonts\segoeuib.ttf',
            r'C:\Windows\Fonts\arialbd.ttf',
            r'C:\Windows\Fonts\tahomabd.ttf'
        ]
        chosen_font = None
        for fp in font_paths:
            if os.path.exists(fp):
                chosen_font = fp
                break

        try:
            if chosen_font:
                font_spk = ImageFont.truetype(chosen_font, 46)
                font_quote = ImageFont.truetype(chosen_font, 38)
            else:
                font_spk = ImageFont.load_default()
                font_quote = ImageFont.load_default()
        except Exception:
            font_spk = ImageFont.load_default()
            font_quote = ImageFont.load_default()

        # 1. Satır: Şampiyon Adı (Altın Sarısı, Gölgeli)
        spk_color = (255, 215, 0, 255)
        shadow_color = (0, 0, 0, 230)

        for offset in [(-3, -3), (3, 3), (-3, 3), (3, -3), (0, 4)]:
            draw.text((width // 2 + offset[0], 55 + offset[1]), spk_upper, font=font_spk, fill=shadow_color, anchor='mm')
        draw.text((width // 2, 55), spk_upper, font=font_spk, fill=spk_color, anchor='mm')

        # 2. Satır: Replik Metni (Sarı Renkte, Hafif Kalın, Gölgeli)
        quote_color = (255, 230, 85, 255)
        lines = quote_text.split('\n')
        y_start = 145
        line_h = 50
        for i, line in enumerate(lines):
            y = y_start + i * line_h
            for offset in [(-3, -3), (3, 3), (-3, 3), (3, -3), (0, 4)]:
                draw.text((width // 2 + offset[0], y + offset[1]), line, font=font_quote, fill=shadow_color, anchor='mm')
            draw.text((width // 2, y), line, font=font_quote, fill=quote_color, anchor='mm')

        img.save(out_path, 'PNG')
        return out_path


    @classmethod
    def filter_and_sort_files(cls, audio_files, exclude_sfx=True, smart_sort=True, target_champion=None):
        """Filters out sound effects / swings / grunts while preserving all voiced skill dialogue."""
        filtered = []

        for f in audio_files:
            if not os.path.isfile(f):
                continue
            if exclude_sfx:
                if not cls.is_voiced_dialogue(f):
                    continue
            filtered.append(f)

        if target_champion:
            filtered.sort(key=lambda p: cls.get_target_reference_sort_key(p, target_champion))
        elif smart_sort:
            filtered.sort(key=cls.get_narrative_sort_key)
        else:
            filtered.sort()

        return filtered

    @classmethod
    def generate_fcp7_xml(cls, audio_files, output_path, gap_seconds=0.2, timeline_name="LoL Sesler Timeline", fps=60, smart_sort=True, exclude_sfx=True, target_champion=None, generate_srt=True, fade_in_seconds=0.5, fade_out_seconds=0.3, background_media=None, include_splash=True, splash_pos_x=-430, splash_pos_y=160, splash_zoom=0.6, text_pos_x=-430, text_pos_y=-480, text_zoom=1.0, timeline_w=2560, timeline_h=1440, include_action_label=True, action_pos_x=2090, action_pos_y=890, action_zoom=0.64, generate_companion_fcpxml=True, include_text=True):
        """
        Generates standard FCP 7 XML (xmeml v5) compatible with DaVinci Resolve.
        Supports 4-layer professional layout with pixel-perfect Inspector transforms:
        - Track V1: Background video / atmospheric media (or empty ready track)
        - Track V2: Speaker Champion Splash Art: Position X=-430, Y=160, Zoom=0.600
        - Track V3: Native DaVinci Text Generator (Title - Text): Position X=-430, Y=-480 (Safe Point), Zoom=1.000
        - Track V4: Olay / Eylem Şablonu (Kışkırtınca, Karşılaşınca, Saldırınca...): Position X=2090, Y=890, Zoom=0.64
        - Track A1: Sequenced dialogue audio clips with precise gaps
        """
        is_rich_list = bool(audio_files and isinstance(audio_files[0], dict))
        if is_rich_list:
            sorted_files = audio_files
        else:
            sorted_files = cls.filter_and_sort_files(audio_files, exclude_sfx=exclude_sfx, smart_sort=smart_sort, target_champion=target_champion)

        if not include_text:
            generate_srt = False

        gap_frames = int(round(float(gap_seconds) * fps))
        current_frame = 0

        fade_in_frames = max(1, int(round(float(fade_in_seconds) * fps)))
        fade_out_frames = max(1, int(round(float(fade_out_seconds) * fps)))

        # Exact DaVinci Resolve Inspector Mapping (2560x1440 QHD standard):
        splash_scale = int(round(float(splash_zoom) * 100))  # 0.6 -> 60
        splash_horiz = round(float(splash_pos_x) / float(timeline_w), 8)  # -430 / 2560 = -0.16796875
        splash_vert = round(- float(splash_pos_y) / float(timeline_h), 8)  # -160 / 1440 = -0.11111111

        text_scale = int(round(float(text_zoom) * 100))  # 1.0 -> 100
        text_horiz = round(float(text_pos_x) / float(timeline_w), 8)  # -430 / 2560 = -0.16796875
        text_vert = round(- float(text_pos_y) / float(timeline_h), 8)  # - (-450) / 1440 = 0.3125

        # Olay / Eylem Şablonu (Kışkırtınca, Karşılaşınca vb.) Normalizasyonu
        raw_ax = float(action_pos_x)
        raw_ay = float(action_pos_y)
        raw_azoom = float(action_zoom)
        if raw_azoom > 10.0:
            raw_azoom = raw_azoom / 1000.0

        act_rel_x = raw_ax - (timeline_w / 2.0) if raw_ax > (timeline_w / 2.0) else raw_ax
        act_rel_y = raw_ay - (timeline_h / 2.0) if raw_ay > (timeline_h / 2.0) else raw_ay

        action_scale = int(round(raw_azoom * 100))
        action_horiz = round(float(act_rel_x) / float(timeline_w), 8)
        action_vert = round(- float(act_rel_y) / float(timeline_h), 8)

        try:
            from ai_voice_detector import AIVoiceDetector
        except ImportError:
            try:
                import sys
                sys.path.append(os.path.dirname(os.path.abspath(__file__)))
                from ai_voice_detector import AIVoiceDetector
            except Exception:
                AIVoiceDetector = None

        audio_clip_items = []
        video_splash_items = []
        video_title_items = []
        video_action_items = []
        splash_raw_entries = []
        clip_id = 1

        title_cache_dir = os.path.join(os.path.dirname(os.path.abspath(output_path)), "Altyazi_Gorselleri")
        os.makedirs(title_cache_dir, exist_ok=True)

        for idx, file_item in enumerate(sorted_files):
            if isinstance(file_item, dict):
                abs_path = os.path.abspath(file_item['audio_path'])
                splash_path = file_item.get('splash_path')
                spk_upper = file_item.get('speaker', '').upper()
                clean_quote = file_item.get('transcript', '')
            else:
                abs_path = os.path.abspath(file_item)
                splash_path = None
                spk_upper = None
                clean_quote = None
            file_name = os.path.basename(abs_path)
            duration_sec, samplerate, channels, bitdepth = cls.get_audio_info_fast(abs_path)
            duration_frames = max(1, int(round(duration_sec * fps)))

            # If not the first clip, insert gap
            if idx > 0 and gap_frames > 0:
                current_frame += gap_frames

            start_frame = current_frame
            end_frame = start_frame + duration_frames
            current_frame = end_frame

            # Windows file path to file:// URL
            url_path = abs_path.replace(os.sep, '/')
            if not url_path.startswith('/'):
                url_path = '/' + url_path
            path_url = 'file://localhost' + urllib.parse.quote(url_path)

            clip_xml = f"""
            <clipitem id="clipitem-audio-{clip_id}">
              <name>{escape(file_name)}</name>
              <duration>{duration_frames}</duration>
              <rate>
                <timebase>{fps}</timebase>
                <ntsc>FALSE</ntsc>
              </rate>
              <start>{start_frame}</start>
              <end>{end_frame}</end>
              <in>0</in>
              <out>{duration_frames}</out>
              <file id="file-audio-{clip_id}">
                <name>{escape(file_name)}</name>
                <pathurl>{path_url}</pathurl>
                <rate>
                  <timebase>{fps}</timebase>
                  <ntsc>FALSE</ntsc>
                </rate>
                <duration>{duration_frames}</duration>
                <media>
                  <audio>
                    <samplecharacteristics>
                      <depth>{bitdepth}</depth>
                      <samplerate>{samplerate}</samplerate>
                    </samplecharacteristics>
                    <channelcount>{channels}</channelcount>
                  </audio>
                </media>
              </file>
              <sourcetrack>
                <mediatype>audio</mediatype>
                <trackindex>1</trackindex>
              </sourcetrack>
            </clipitem>"""
            audio_clip_items.append(clip_xml)

            # Opacity Fade Transition (Shared between Splash & Text)
            filter_xml = ""
            actual_in_frames = min(fade_in_frames, max(1, duration_frames // 2))
            actual_out_frames = min(fade_out_frames, max(1, duration_frames // 2))
            if (fade_in_seconds > 0 or fade_out_seconds > 0) and duration_frames > 4:
                filter_xml = f"""
              <filter>
                <effect>
                  <name>Opacity</name>
                  <effectid>opacity</effectid>
                  <effecttype>motion</effecttype>
                  <mediatype>video</mediatype>
                  <parameter>
                    <parameterid>opacity</parameterid>
                    <name>Opacity</name>
                    <valuemin>0</valuemin>
                    <valuemax>100</valuemax>
                    <valuelist>
                      <value>
                        <keyframe>0</keyframe>
                        <value>0</value>
                      </value>
                      <value>
                        <keyframe>{actual_in_frames}</keyframe>
                        <value>100</value>
                      </value>
                      <value>
                        <keyframe>{max(actual_in_frames, duration_frames - actual_out_frames)}</keyframe>
                        <value>100</value>
                      </value>
                      <value>
                        <keyframe>{duration_frames}</keyframe>
                        <value>0</value>
                      </value>
                    </valuelist>
                  </parameter>
                </effect>
              </filter>"""

            # -------------------------------------------------------------
            # Track V2: Konuşan Şampiyonun Kostüm Splash Art Görseli (Toplama)
            # -------------------------------------------------------------
            if include_splash:
                if not splash_path:
                    skin_data = cls.resolve_speaker_and_skin(abs_path, target_champion=target_champion)
                    splash_path = cls.get_or_download_splash_art(skin_data, force_4k=True) if skin_data else None

                if splash_path and os.path.exists(splash_path):
                    splash_raw_entries.append({
                        "splash_path": splash_path,
                        "speaker": spk_upper,
                        "start_frame": start_frame,
                        "end_frame": end_frame,
                        "clip_id": clip_id,
                        "filter_xml": filter_xml
                    })

            # -------------------------------------------------------------
            # Track V3: Altyazı / Metin (DaVinci Yerel "Title - Text" Şablonu, PNG Değil!)
            # -------------------------------------------------------------
            if include_text:
                if not clean_quote or not clean_quote.strip() or not spk_upper:
                    raw_ev = file_item.get('event', '') if isinstance(file_item, dict) else file_name
                    wem_id_val = file_item.get('wem_id') if isinstance(file_item, dict) else None
                    spk_name = file_item.get('speaker', '') if isinstance(file_item, dict) else file_name.split('_')[0]

                    spoken_text = cls.lookup_or_transcribe(abs_path, speaker=spk_name, raw_event=raw_ev, wem_id=wem_id_val)
                    action_type = "Replik"
                    if 'karsilasma' in file_name:
                        action_type = "Karşılaşma"
                    elif 'katletme' in file_name:
                        action_type = "Katletme"

                    spk_upper, clean_quote = cls.clean_dialogue_and_speaker(file_name, spoken_text, action_type)
                    if not spk_upper and spk_name:
                        spk_upper = cls.turkish_upper(spk_name)

                wrapped_quote = cls.balance_wrap(clean_quote, max_chars=38)
                clean_title_label = f"{spk_upper}: {wrapped_quote.replace(chr(10), ' ')}"
                formatted_quote = escape(wrapped_quote).replace('\n', '&#13;')
                display_text = f"{escape(spk_upper)}&#13;{formatted_quote}"

                title_clip_xml = f"""
            <generatoritem id="generatoritem-title-{clip_id}">
              <name>{escape(clean_title_label)}</name>
              <duration>{duration_frames}</duration>
              <rate>
                <timebase>{fps}</timebase>
                <ntsc>FALSE</ntsc>
              </rate>
              <in>0</in>
              <out>{duration_frames}</out>
              <start>{start_frame}</start>
              <end>{end_frame}</end>
              <effect>
                <name>Text</name>
                <effectid>Text</effectid>
                <effecttype>generator</effecttype>
                <mediatype>video</mediatype>
                <parameter>
                  <parameterid>str</parameterid>
                  <name>Text</name>
                  <value>{display_text}</value>
                </parameter>
                <parameter>
                  <parameterid>font</parameterid>
                  <name>Font</name>
                  <value>Poppins</value>
                </parameter>
                <parameter>
                  <parameterid>style</parameterid>
                  <name>Style</name>
                  <value>Bold</value>
                </parameter>
                <parameter>
                  <parameterid>size</parameterid>
                  <name>Size</name>
                  <value>56</value>
                </parameter>
                <parameter>
                  <parameterid>align</parameterid>
                  <name>Alignment</name>
                  <value>Center</value>
                </parameter>
                <parameter>
                  <parameterid>center</parameterid>
                  <name>Center</name>
                  <value>
                    <horiz>{text_horiz}</horiz>
                    <vert>{text_vert}</vert>
                  </value>
                </parameter>
                <parameter>
                  <parameterid>textcolor</parameterid>
                  <name>Font Color</name>
                  <value>
                    <alpha>255</alpha>
                    <red>255</red>
                    <green>225</green>
                    <blue>70</blue>
                  </value>
                </parameter>
              </effect>
              <filter>
                <effect>
                  <name>Basic Motion</name>
                  <effectid>basic</effectid>
                  <effecttype>motion</effecttype>
                  <mediatype>video</mediatype>
                  <parameter>
                    <parameterid>scale</parameterid>
                    <name>Scale</name>
                    <valuemin>0</valuemin>
                    <valuemax>1000</valuemax>
                    <value>{text_scale}</value>
                  </parameter>
                  <parameter>
                    <parameterid>center</parameterid>
                    <name>Center</name>
                    <value>
                      <horiz>{text_horiz}</horiz>
                      <vert>{text_vert}</vert>
                    </value>
                  </parameter>
                </effect>
              </filter>{filter_xml}
            </generatoritem>"""
                video_title_items.append(title_clip_xml)

            # Olay / Eylem Şablonu (Kışkırtınca, Karşılaşınca vb.) Generator Item
            if include_text and include_action_label:
                raw_ev = file_item.get('event', '') if isinstance(file_item, dict) else file_name
                act_type = file_item.get('action_type', '') if isinstance(file_item, dict) else ''
                action_label = cls.format_event_action_template(raw_ev, act_type)

                action_clip_xml = f"""
            <generatoritem id="generatoritem-action-{clip_id}">
              <name>{escape(action_label)}</name>
              <duration>{duration_frames}</duration>
              <rate>
                <timebase>{fps}</timebase>
                <ntsc>FALSE</ntsc>
              </rate>
              <in>0</in>
              <out>{duration_frames}</out>
              <start>{start_frame}</start>
              <end>{end_frame}</end>
              <effect>
                <name>Text</name>
                <effectid>Text</effectid>
                <effecttype>generator</effecttype>
                <mediatype>video</mediatype>
                <parameter>
                  <parameterid>str</parameterid>
                  <name>Text</name>
                  <value>{escape(action_label)}</value>
                </parameter>
                <parameter>
                  <parameterid>font</parameterid>
                  <name>Font</name>
                  <value>Poppins</value>
                </parameter>
                <parameter>
                  <parameterid>style</parameterid>
                  <name>Style</name>
                  <value>Bold Italic</value>
                </parameter>
                <parameter>
                  <parameterid>size</parameterid>
                  <name>Size</name>
                  <value>56</value>
                </parameter>
                <parameter>
                  <parameterid>align</parameterid>
                  <name>Alignment</name>
                  <value>Center</value>
                </parameter>
                <parameter>
                  <parameterid>outline</parameterid>
                  <name>Outline</name>
                  <value>1</value>
                </parameter>
                <parameter>
                  <parameterid>outsideonly</parameterid>
                  <name>Outside Only</name>
                  <value>1</value>
                </parameter>
                <parameter>
                  <parameterid>center</parameterid>
                  <name>Center</name>
                  <value>
                    <horiz>{action_horiz}</horiz>
                    <vert>{action_vert}</vert>
                  </value>
                </parameter>
                <parameter>
                  <parameterid>textcolor</parameterid>
                  <name>Font Color</name>
                  <value>
                    <alpha>255</alpha>
                    <red>255</red>
                    <green>225</green>
                    <blue>70</blue>
                  </value>
                </parameter>
                <parameter>
                  <parameterid>outlinecolor</parameterid>
                  <name>Outline Color</name>
                  <value>
                    <alpha>255</alpha>
                    <red>0</red>
                    <green>0</green>
                    <blue>0</blue>
                  </value>
                </parameter>
              </effect>
              <filter>
                <effect>
                  <name>Basic Motion</name>
                  <effectid>basic</effectid>
                  <effecttype>motion</effecttype>
                  <mediatype>video</mediatype>
                  <parameter>
                    <parameterid>scale</parameterid>
                    <name>Scale</name>
                    <valuemin>0</valuemin>
                    <valuemax>1000</valuemax>
                    <value>{action_scale}</value>
                  </parameter>
                  <parameter>
                    <parameterid>center</parameterid>
                    <name>Center</name>
                    <value>
                      <horiz>{action_horiz}</horiz>
                      <vert>{action_vert}</vert>
                    </value>
                  </parameter>
                </effect>
              </filter>{filter_xml}
            </generatoritem>"""
                video_action_items.append(action_clip_xml)

            clip_id += 1

        # Splash Art Kliplerini Grupla (Aynı karakterin ardışık repliklerinde tek görsel)
        if splash_raw_entries:
            splash_groups = []
            curr_sg = []
            for s_entry in splash_raw_entries:
                if not curr_sg:
                    curr_sg.append(s_entry)
                else:
                    prev_sg = curr_sg[-1]
                    if prev_sg['splash_path'] == s_entry['splash_path'] and prev_sg['speaker'] == s_entry['speaker']:
                        curr_sg.append(s_entry)
                    else:
                        splash_groups.append(curr_sg)
                        curr_sg = [s_entry]
            if curr_sg:
                splash_groups.append(curr_sg)

            for sg_idx, s_grp in enumerate(splash_groups, 1):
                first_s = s_grp[0]
                last_s = s_grp[-1]
                s_path = first_s['splash_path']
                sg_start = first_s['start_frame']
                sg_end = last_s['end_frame']
                sg_duration = max(1, sg_end - sg_start)

                splash_file_name = os.path.basename(s_path)
                splash_w, splash_h = cls.get_image_dimensions_fast(s_path)
                s_url_path = s_path.replace(os.sep, '/')
                if not s_url_path.startswith('/'):
                    s_url_path = '/' + s_url_path
                splash_path_url = 'file://localhost' + urllib.parse.quote(s_url_path)

                splash_clip_xml = f"""
            <clipitem id="clipitem-splash-{sg_idx}">
              <name>{escape(splash_file_name)}</name>
              <duration>{sg_duration}</duration>
              <rate>
                <timebase>{fps}</timebase>
                <ntsc>FALSE</ntsc>
              </rate>
              <start>{sg_start}</start>
              <end>{sg_end}</end>
              <in>0</in>
              <out>{sg_duration}</out>
              <file id="file-splash-{sg_idx}">
                <name>{escape(splash_file_name)}</name>
                <pathurl>{splash_path_url}</pathurl>
                <rate>
                  <timebase>{fps}</timebase>
                  <ntsc>FALSE</ntsc>
                </rate>
                <duration>{sg_duration}</duration>
                <media>
                  <video>
                    <samplecharacteristics>
                      <rate>
                        <timebase>{fps}</timebase>
                        <ntsc>FALSE</ntsc>
                      </rate>
                      <width>{splash_w}</width>
                      <height>{splash_h}</height>
                      <anamorphic>FALSE</anamorphic>
                      <pixelaspectratio>square</pixelaspectratio>
                      <fielddominance>none</fielddominance>
                    </samplecharacteristics>
                  </video>
                </media>
              </file>
              <sourcetrack>
                <mediatype>video</mediatype>
                <trackindex>1</trackindex>
              </sourcetrack>
              <filter>
                <effect>
                  <name>Basic Motion</name>
                  <effectid>basic</effectid>
                  <effecttype>motion</effecttype>
                  <mediatype>video</mediatype>
                  <parameter>
                    <parameterid>scale</parameterid>
                    <name>Scale</name>
                    <valuemin>0</valuemin>
                    <valuemax>1000</valuemax>
                    <value>{splash_scale}</value>
                  </parameter>
                  <parameter>
                    <parameterid>center</parameterid>
                    <name>Center</name>
                    <value>
                      <horiz>{splash_horiz}</horiz>
                      <vert>{splash_vert}</vert>
                    </value>
                  </parameter>
                </effect>
              </filter>
            </clipitem>"""
                video_splash_items.append(splash_clip_xml)

        total_duration = max(60, current_frame)

        # -------------------------------------------------------------
        # Track V1: Arka Plan Medyası (Background Video veya Görsel)
        # -------------------------------------------------------------
        background_track_items = ""
        if background_media and os.path.exists(background_media):
            bg_abs = os.path.abspath(background_media)
            bg_name = os.path.basename(bg_abs)
            bg_w, bg_h = cls.get_image_dimensions_fast(bg_abs)
            bg_url = bg_abs.replace(os.sep, '/')
            if not bg_url.startswith('/'):
                bg_url = '/' + bg_url
            bg_path_url = 'file://localhost' + urllib.parse.quote(bg_url)

            background_track_items = f"""
            <clipitem id="clipitem-bg-1">
              <name>{escape(bg_name)}</name>
              <duration>{total_duration}</duration>
              <rate>
                <timebase>{fps}</timebase>
                <ntsc>FALSE</ntsc>
              </rate>
              <start>0</start>
              <end>{total_duration}</end>
              <in>0</in>
              <out>{total_duration}</out>
              <file id="file-bg-1">
                <name>{escape(bg_name)}</name>
                <pathurl>{bg_path_url}</pathurl>
                <rate>
                  <timebase>{fps}</timebase>
                  <ntsc>FALSE</ntsc>
                </rate>
                <duration>{total_duration}</duration>
                <media>
                  <video>
                    <samplecharacteristics>
                      <rate>
                        <timebase>{fps}</timebase>
                        <ntsc>FALSE</ntsc>
                      </rate>
                      <width>{bg_w}</width>
                      <height>{bg_h}</height>
                      <anamorphic>FALSE</anamorphic>
                      <pixelaspectratio>square</pixelaspectratio>
                      <fielddominance>none</fielddominance>
                    </samplecharacteristics>
                  </video>
                </media>
              </file>
              <sourcetrack>
                <mediatype>video</mediatype>
                <trackindex>1</trackindex>
              </sourcetrack>
            </clipitem>"""

        # Video Track Katmanları (V1: Arka Plan, V2: Sol Splash, V3: Replik Altyazısı, V4: Eylem Başlığı)
        action_track_xml = f"""
        <!-- Track V4: Olay / Eylem Şablonu (Kışkırtınca, Karşılaşınca vb. - X={action_pos_x}, Y={action_pos_y}, Zoom={action_zoom}) -->
        <track>
          {''.join(video_action_items)}
        </track>""" if include_text and include_action_label and video_action_items else ""

        title_track_xml = f"""
        <!-- Track V3: Replik Altyazısı / Metin (X={text_pos_x}, Y={text_pos_y}, Zoom={text_zoom}) -->
        <track>
          {''.join(video_title_items)}
        </track>""" if include_text and video_title_items else ""

        if include_splash:
            video_tracks_xml = f"""
        <!-- Track V1: Arka Plan (Atmosfer Videosu veya Ortam Görseli) -->
        <track>
          {background_track_items}
        </track>
        <!-- Track V2: Konuşan Şampiyon Splash Art (X={splash_pos_x}, Y={splash_pos_y}, Zoom={splash_zoom}) -->
        <track>
          {''.join(video_splash_items)}
        </track>{title_track_xml}{action_track_xml}"""
        else:
            if include_text and video_title_items:
                video_tracks_xml = f"""
        <track>
          <!-- Track V1: Replik Altyazıları / Başlıklar -->
          {''.join(video_title_items)}
        </track>{action_track_xml}"""
            else:
                video_tracks_xml = """
        <track>
        </track>"""

        # 1920x1080 Full HD 60 FPS Standardı (Piksel Birebir Eşleşme)
        full_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE xmeml>
<xmeml version="5">
  <sequence id="sequence-1">
    <name>{escape(timeline_name)}</name>
    <duration>{total_duration}</duration>
    <rate>
      <timebase>{fps}</timebase>
      <ntsc>FALSE</ntsc>
    </rate>
    <timecode>
      <rate>
        <timebase>{fps}</timebase>
        <ntsc>FALSE</ntsc>
      </rate>
      <string>01:00:00:00</string>
      <frame>0</frame>
      <displayformat>NDF</displayformat>
    </timecode>
    <media>
      <video>
        <format>
          <samplecharacteristics>
            <rate>
              <timebase>{fps}</timebase>
              <ntsc>FALSE</ntsc>
            </rate>
            <width>{timeline_w}</width>
            <height>{timeline_h}</height>
            <anamorphic>FALSE</anamorphic>
            <pixelaspectratio>square</pixelaspectratio>
            <fielddominance>none</fielddominance>
          </samplecharacteristics>
        </format>
        {video_tracks_xml}
      </video>
      <audio>
        <numOutputChannels>2</numOutputChannels>
        <format>
          <samplecharacteristics>
            <depth>16</depth>
            <samplerate>48000</samplerate>
          </samplecharacteristics>
        </format>
        <track>
          <!-- Track A1: Single Unified Audio Stream (Sequentially aligned with gaps) -->
          {''.join(audio_clip_items)}
        </track>
      </audio>
    </media>
  </sequence>
</xmeml>"""

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(full_xml)

        # File naming logic for companions:
        out_dir = os.path.dirname(os.path.abspath(output_path))
        base_name = os.path.basename(output_path)
        base_no_ext = os.path.splitext(base_name)[0]

        if base_name.startswith("02_"):
            fcpxml_name = base_no_ext.replace("02_", "01_") + ".fcpxml"
            srt_name = base_no_ext.replace("02_", "03_") + ".srt"
            titles_fcpxml_name = base_no_ext.replace("02_", "04_") + "_Sadece_Metinler.fcpxml"
            setting_name = base_no_ext.replace("02_", "05_") + "_Daktilo_TextPlus.setting"
        else:
            fcpxml_name = base_no_ext + ".fcpxml"
            srt_name = base_no_ext + ".srt"
            titles_fcpxml_name = base_no_ext + "_Sadece_Metinler.fcpxml"
            setting_name = base_no_ext + "_Daktilo_TextPlus.setting"

        fcpxml_path = os.path.join(out_dir, fcpxml_name)
        titles_fcpxml_path = os.path.join(out_dir, titles_fcpxml_name)
        srt_path = os.path.join(out_dir, srt_name)
        setting_path = os.path.join(out_dir, setting_name)

        # Companion FCPXML export (2560x1440 60FPS) with Native Text Titles & Audio & Splash
        if generate_companion_fcpxml:
            cls.generate_fcpxml_from_sorted(
                sorted_files,
                fcpxml_path,
                gap_seconds=gap_seconds,
                timeline_name=timeline_name,
                fps=fps,
                target_champion=target_champion,
                fade_in_seconds=fade_in_seconds,
                fade_out_seconds=fade_out_seconds,
                include_splash=include_splash,
                splash_pos_x=splash_pos_x,
                splash_pos_y=splash_pos_y,
                splash_zoom=splash_zoom,
                text_pos_x=text_pos_x,
                text_pos_y=text_pos_y,
                text_zoom=text_zoom
            )

        # Companion Dedicated Titles FCPXML (Pure SRT-style Text Title timeline)
        if include_text:
            cls.generate_titles_only_fcpxml(sorted_files, titles_fcpxml_path, gap_seconds, timeline_name, fps, fade_in_seconds=fade_in_seconds, fade_out_seconds=fade_out_seconds)

        # Companion SRT subtitle export (Synced with Timeline)
        if generate_srt and include_text:
            try:
                cls.generate_srt_subtitles(sorted_files, srt_path, gap_seconds, target_champion=target_champion)
            except Exception as e:
                print(f"  ⚠️ SRT Altyazı üretilirken hata: {e}")

        # Companion Native Fusion Typewriter Text+ Comp (.setting & Windows Clipboard)
        if include_text:
            try:
                cls.generate_fusion_typewriter_comp(
                    sorted_files,
                    setting_path,
                    gap_seconds=gap_seconds,
                    fps=fps,
                    copy_to_clipboard=True,
                    target_champion=target_champion
                )
            except Exception as e:
                print(f"  ⚠️ Fusion Daktilo Text+ üretilirken hata: {e}")

        return output_path, len(audio_clip_items), total_duration / float(fps)

    @classmethod
    def generate_titles_only_fcpxml(cls, sorted_files, output_path, gap_seconds=0.8, timeline_name="LoL Metinler", fps=60, fade_in_seconds=0.1, fade_out_seconds=0.1):
        """
        Generates pure Text/Title FCPXML (like online SRT to FCPXML converters).
        When dragged into DaVinci Resolve, every subtitle becomes a standalone editable Text Title clip on Video Track 1 with Text+ & Transitions.
        """
        try:
            from ai_voice_detector import AIVoiceDetector
        except ImportError:
            try:
                import sys
                sys.path.append(os.path.dirname(os.path.abspath(__file__)))
                from ai_voice_detector import AIVoiceDetector
            except Exception:
                AIVoiceDetector = None

        resources = [
            f'<format id="r1" name="FFVideoFormat2160p{fps}" frameDuration="1/{fps}s" width="2560" height="1440"/>',
            f'<effect id="r_title" name="Text+" uid=".../Titles.localized/Fusion Titles.localized/Text+.localized/Text+.moti"/>',
            f'<effect id="r_dissolve" name="Cross Dissolve" uid=".../Transitions.localized/Dissolves.localized/Cross Dissolve.localized/Cross Dissolve.motr"/>'
        ]
        spine_items = []
        current_frame = 0

        for idx, file_item in enumerate(sorted_files):
            abs_path = os.path.abspath(file_item['audio_path'] if isinstance(file_item, dict) else file_item)
            file_name = os.path.basename(abs_path)
            duration_sec, _, _, _ = cls.get_audio_info_fast(abs_path)
            dur_frames = max(1, int(round(duration_sec * fps)))

            # If gap between clips
            if idx > 0 and gap_seconds > 0:
                gap_frames = int(round(gap_seconds * fps))
                gap_offset_str = f"{current_frame}/{fps}s"
                gap_dur_str = f"{gap_frames}/{fps}s"
                spine_items.append(f'<gap name="Gap" offset="{gap_offset_str}" duration="{gap_dur_str}" start="0s"/>')
                current_frame += gap_frames

            action_type = "Replik"
            if 'karsilasma' in file_name:
                action_type = "Karşılaşma"
            elif 'katletme' in file_name:
                action_type = "Katletme"

            if isinstance(file_item, dict) and file_item.get('transcript'):
                spk_upper = file_item.get('speaker', '').upper()
                clean_quote = file_item.get('transcript', '')
            else:
                spoken_text = ""
                if AIVoiceDetector:
                    try:
                        _, spoken_text = AIVoiceDetector.is_spoken_dialogue(abs_path)
                    except Exception:
                        spoken_text = ""
                spk_upper, clean_quote = cls.clean_dialogue_and_speaker(file_name, spoken_text, action_type)
            formatted_quote = escape(clean_quote).replace('\n', '&#13;&#10;')

            title_offset_str = f"{current_frame}/{fps}s"
            title_dur_str = f"{dur_frames}/{fps}s"

            fade_in_frames = max(1, int(round(float(fade_in_seconds) * fps)))
            fade_out_frames = max(1, int(round(float(fade_out_seconds) * fps)))
            actual_in_frames = min(fade_in_frames, max(1, dur_frames // 2))
            actual_out_frames = min(fade_out_frames, max(1, dur_frames // 2))

            in_trans_str = f"""<transition name="Cross Dissolve" offset="{current_frame}/{fps}s" duration="{actual_in_frames}/{fps}s">
              <filter-video ref="r_dissolve" name="Cross Dissolve"/>
            </transition>""" if fade_in_seconds > 0 else ""

            out_trans_offset = current_frame + dur_frames - actual_out_frames
            out_trans_str = f"""<transition name="Cross Dissolve" offset="{out_trans_offset}/{fps}s" duration="{actual_out_frames}/{fps}s">
              <filter-video ref="r_dissolve" name="Cross Dissolve"/>
            </transition>""" if fade_out_seconds > 0 else ""

            title_item = f"""{in_trans_str}
            <title ref="r_title" name="{escape(spk_upper)}" offset="{title_offset_str}" duration="{title_dur_str}" start="0s">
              <text>
                <text-style ref="ts_spk_{idx+1}">{escape(spk_upper)}</text-style>
                <text-style ref="ts_quote_{idx+1}">&#13;&#10;{formatted_quote}</text-style>
              </text>
              <text-style-def id="ts_spk_{idx+1}">
                <text-style font="Poppins" fontSize="56" fontColor="0.30 0.85 0.95 1" bold="1" alignment="center" shadowColor="0 0 0 0.9" shadowOffset="3 -3"/>
              </text-style-def>
              <text-style-def id="ts_quote_{idx+1}">
                <text-style font="Poppins" fontSize="48" fontColor="0.95 0.82 0.25 1" bold="1" alignment="center" shadowColor="0 0 0 0.9" shadowOffset="3 -3"/>
              </text-style-def>
            </title>
            {out_trans_str}"""
            spine_items.append(title_item)
            current_frame += dur_frames

        total_dur_str = f"{max(1, current_frame)}/{fps}s"

        fcpxml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE fcpxml>
<fcpxml version="1.8">
  <resources>
    {''.join(resources)}
  </resources>
  <library>
    <event name="LoL Metinler">
      <project name="{escape(timeline_name)} (Metinler)">
        <sequence format="r1" duration="{total_dur_str}">
          <spine>
            {''.join(spine_items)}
          </spine>
        </sequence>
      </project>
    </event>
  </library>
</fcpxml>"""

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(fcpxml_content)

        return output_path

    @classmethod
    def generate_fcpxml_from_sorted(cls, sorted_files, output_path, gap_seconds=0.2, timeline_name="LoL Sesler Timeline", fps=60, target_champion=None, fade_in_seconds=0.1, fade_out_seconds=0.1, include_splash=True, splash_pos_x=-430, splash_pos_y=160, splash_zoom=0.6, text_pos_x=-430, text_pos_y=-480, text_zoom=1.0, include_action_label=True, action_pos_x=2090, action_pos_y=890, action_zoom=0.64, font_family="Poppins", font_size_spk=56, font_size_quote=48, stroke_width=1, include_text=True):
        """
        Generates DaVinci Resolve 21 native FCPXML (v1.8) containing:
        - Track V1/Spine: Splash Art (<video>) with exact Transform (position="-430 160" scale="0.6 0.6")
        - Track V2 (lane="1"): Native Text Title (<title>) exactly below the image at Safe Point (position="-430 -480")
        - Track V3 (lane="2"): Olay / Eylem Şablonu (<title> - Kışkırtınca, Karşılaşınca, Saldırınca... - X=2090 Y=890 Zoom=0.64)
        - Track A1 (lane="-1"): Synchronized voice audio clip (<asset-clip>)
        - Clean rational timecode math and timeline gaps
        """
        from pathlib import Path

        try:
            from ai_voice_detector import AIVoiceDetector
        except ImportError:
            try:
                import sys
                sys.path.append(os.path.dirname(os.path.abspath(__file__)))
                from ai_voice_detector import AIVoiceDetector
            except Exception:
                AIVoiceDetector = None

        resources = [
            f'<format id="r1" name="FFVideoFormat2160p{fps}" frameDuration="1/{fps}s" width="2560" height="1440" colorSpace="1-1-1 (Rec. 709)"/>',
            '<effect id="r_title" name="Basic Title" uid=".../Titles.localized/Bumper:Opener.localized/Basic Title.localized/Basic Title.moti"/>',
            '<effect id="r_dissolve" name="Cross Dissolve" uid=".../Transitions.localized/Dissolves.localized/Cross Dissolve.localized/Cross Dissolve.motr"/>'
        ]
        spine_items = []
        current_frame = 0

        # Action Label Koordinat ve Zoom Normalizasyonu (2560x1440 standardı)
        timeline_w = 2560
        timeline_h = 1440
        fcpxml_scale_factor = timeline_h / 100.0  # 14.4

        raw_ax = float(action_pos_x)
        raw_ay = float(action_pos_y)
        raw_azoom = float(action_zoom)
        if raw_azoom > 10.0:
            raw_azoom = raw_azoom / 1000.0  # örn. 640 -> 0.64

        act_rel_x = raw_ax - (timeline_w / 2.0) if raw_ax > (timeline_w / 2.0) else raw_ax
        act_rel_y = raw_ay - (timeline_h / 2.0) if raw_ay > (timeline_h / 2.0) else raw_ay

        fcpxml_action_x = round(act_rel_x / fcpxml_scale_factor, 6)
        fcpxml_action_y = round(act_rel_y / fcpxml_scale_factor, 6)
        fcpxml_action_zoom = round(raw_azoom, 4)

        gap_frames = int(round(gap_seconds * fps)) if gap_seconds > 0 else 0
        parsed_items = []
        registered_images = {}  # splash_path -> img_id

        for idx, file_item in enumerate(sorted_files, start=1):
            if isinstance(file_item, dict):
                abs_path = os.path.abspath(file_item['audio_path'])
                splash_path = file_item.get('splash_path')
                spk_upper = cls.turkish_upper(file_item.get('speaker', ''))
                clean_quote = file_item.get('transcript', '') or file_item.get('quote', '') or file_item.get('text', '')
            else:
                abs_path = os.path.abspath(file_item)
                splash_path = None
                spk_upper = None
                clean_quote = None

            file_name = os.path.basename(abs_path)
            duration_sec, samplerate, channels, bitdepth = cls.get_audio_info_fast(abs_path)

            aud_id = f"aud_{idx}"
            aud_uri = Path(abs_path).resolve().as_uri()
            dur_frames = max(1, int(round(duration_sec * fps)))
            dur_str = f"{dur_frames}/{fps}s"

            resources.append(
                f'<asset id="{aud_id}" name="{escape(Path(abs_path).stem)}" src="{aud_uri}" start="0s" duration="{dur_str}" hasAudio="1" audioSources="1" audioChannels="{channels}" audioRate="{samplerate}"/>'
            )

            # Splash Art Görseli İndir / Çözümle
            img_id = None
            img_stem = ""
            if include_splash:
                if not splash_path:
                    skin_data = cls.resolve_speaker_and_skin(abs_path, target_champion=target_champion)
                    splash_path = cls.get_or_download_splash_art(skin_data, force_4k=True) if skin_data else None
                if splash_path and os.path.exists(splash_path):
                    if splash_path not in registered_images:
                        img_id = f"img_{len(registered_images) + 1}"
                        registered_images[splash_path] = img_id
                        img_stem = Path(splash_path).stem
                        img_uri = Path(splash_path).resolve().as_uri()
                        resources.append(
                            f'<asset id="{img_id}" name="{escape(img_stem)}" src="{img_uri}" start="0s" duration="0s" hasVideo="1" format="r1"/>'
                        )
                    else:
                        img_id = registered_images[splash_path]
                        img_stem = Path(splash_path).stem

            # Türkçe replik metnini çözümle (Önbellekten veya Whisper ile)
            if include_text:
                if not clean_quote or not clean_quote.strip() or not spk_upper:
                    raw_ev = file_item.get('event', '') if isinstance(file_item, dict) else file_name
                    target_cand = file_item.get('target', '') if isinstance(file_item, dict) else (target_champion or '')
                    wem_id_val = file_item.get('wem_id') if isinstance(file_item, dict) else None
                    spk_name = file_item.get('speaker', '') if isinstance(file_item, dict) else file_name.split('_')[0]

                    spoken_text = cls.lookup_or_transcribe(abs_path, speaker=spk_name, raw_event=raw_ev, wem_id=wem_id_val)
                    action_type = "Replik"
                    if 'karsilasma' in file_name:
                        action_type = "Karşılaşma"
                    elif 'katletme' in file_name:
                        action_type = "Katletme"
                    elif 'yetenek' in file_name:
                        action_type = "Yetenek"

                    parsed_spk, parsed_quote = cls.clean_dialogue_and_speaker(file_name, spoken_text, action_type)
                    if not spk_upper:
                        spk_upper = cls.turkish_upper(spk_name) if spk_name else parsed_spk
                    if not clean_quote:
                        clean_quote = parsed_quote
            else:
                clean_quote = ""
                if not spk_upper:
                    spk_name = file_item.get('speaker', '') if isinstance(file_item, dict) else file_name.split('_')[0]
                    spk_upper = cls.turkish_upper(spk_name) if spk_name else ""

            wrapped_quote = cls.balance_wrap(clean_quote, max_chars=38)
            formatted_quote = escape(wrapped_quote).replace('\n', '&#13;&#10;')

            # Olay / Eylem Şablon Etiketi (Kışkırtınca, Karşılaşınca, Saldırınca vb.)
            action_label = ""
            if include_action_label:
                raw_ev = file_item.get('event', '') if isinstance(file_item, dict) else file_name
                act_type = file_item.get('action_type', '') if isinstance(file_item, dict) else ''
                action_label = cls.format_event_action_template(raw_ev, act_type)

            parsed_items.append({
                "idx": idx,
                "abs_path": abs_path,
                "file_name": file_name,
                "dur_frames": dur_frames,
                "aud_id": aud_id,
                "splash_path": splash_path,
                "img_id": img_id,
                "img_stem": img_stem,
                "spk_upper": spk_upper,
                "clean_quote": clean_quote,
                "formatted_quote": formatted_quote,
                "action_label": action_label
            })

        # DaVinci Resolve FCPXML Position Matematiği:
        fcpxml_splash_x = round(float(splash_pos_x) / fcpxml_scale_factor, 6)
        fcpxml_splash_y = round(float(splash_pos_y) / fcpxml_scale_factor, 6)
        fcpxml_text_x = round(float(text_pos_x) / fcpxml_scale_factor, 6)
        fcpxml_text_y = round(float(text_pos_y) / fcpxml_scale_factor, 6)

        # -------------------------------------------------------------
        # Ardışık Aynı Konuşmacı / Splash Görseli Gruplaması
        # Aynı karakterin ardışık repliklerinde tek kesintisiz görsel uzanır!
        # -------------------------------------------------------------
        groups = []
        curr_g = []
        for p_item in parsed_items:
            if not curr_g:
                curr_g.append(p_item)
            else:
                prev_p = curr_g[-1]
                # Aynı konuşmacı ve aynı splash art ise aynı gruba dahil et
                if prev_p['spk_upper'] == p_item['spk_upper'] and prev_p.get('splash_path') == p_item.get('splash_path'):
                    curr_g.append(p_item)
                else:
                    groups.append(curr_g)
                    curr_g = [p_item]
        if curr_g:
            groups.append(curr_g)

        for g_idx, grp in enumerate(groups):
            g_start_frame = current_frame
            rel_frame = 0

            for c_idx, c in enumerate(grp):
                c['rel_start_frame'] = rel_frame
                rel_frame += c['dur_frames']
                if c_idx < len(grp) - 1:
                    rel_frame += gap_frames

            g_total_frames = rel_frame
            g_dur_str = f"{g_total_frames}/{fps}s"
            g_offset_str = f"{g_start_frame}/{fps}s"

            # Gruptaki ilk öğenin görsel bilgileri
            first_item = grp[0]
            g_splash_path = first_item['splash_path']
            g_img_id = first_item['img_id']
            g_img_stem = first_item['img_stem']

            titles_xml = []
            actions_xml = []
            audios_xml = []

            for c in grp:
                c_idx_val = c['idx']
                c_dur_str = f"{c['dur_frames']}/{fps}s"
                c_rel_offset_str = f"{c['rel_start_frame']}/{fps}s" if c['rel_start_frame'] > 0 else "0s"

                style_spk_id = f"ts_spk_{c_idx_val}"
                style_quote_id = f"ts_quote_{c_idx_val}"
                style_action_id = f"ts_action_{c_idx_val}"

                # 1. Altyazı Başlığı (Track V2 / lane 1): 1. Satır Turkuaz Kalın Konuşmacı, 2. Satır Sıcak Sarı Replik Metni
                if include_text:
                    t_xml = f"""
                  <title name="{escape(c['spk_upper'])}" lane="1" ref="r_title" offset="{c_rel_offset_str}" duration="{c_dur_str}" start="0s">
                    <adjust-transform position="{fcpxml_text_x} {fcpxml_text_y}"/>
                    <text>
                      <text-style ref="{style_spk_id}">{escape(c['spk_upper'])}</text-style>
                      <text-style ref="{style_quote_id}">&#13;&#10;{c['formatted_quote']}</text-style>
                    </text>
                    <text-style-def id="{style_spk_id}">
                      <text-style font="{escape(font_family)}" fontSize="{font_size_spk}" fontFace="Bold" fontColor="0.25 0.88 0.95 1" strokeColor="0 0 0 1" strokeWidth="{stroke_width}" alignment="center" shadowColor="0 0 0 0.95" shadowOffset="3 -3"/>
                    </text-style-def>
                    <text-style-def id="{style_quote_id}">
                      <text-style font="{escape(font_family)}" fontSize="{font_size_quote}" fontFace="Bold" fontColor="1 0.88 0.28 1" strokeColor="0 0 0 1" strokeWidth="{stroke_width}" alignment="center" shadowColor="0 0 0 0.95" shadowOffset="3 -3"/>
                    </text-style-def>
                    <param name="Stroke" key="stroke" value="1"/>
                    <param name="Stroke Size" key="stroke_size" value="{stroke_width}"/>
                    <param name="Stroke Color" key="stroke_color" value="0 0 0 1"/>
                  </title>"""
                    titles_xml.append(t_xml)

                # 2. Olay / Eylem Şablonu (Track V3 / lane 2): Sarı İtalik, Stroke Size 1 (Yazı Kaybolmaz)
                if include_text and include_action_label and c['action_label']:
                    act_label = c['action_label']
                    a_xml = f"""
                  <title name="{escape(act_label)}" lane="2" ref="r_title" offset="{c_rel_offset_str}" duration="{c_dur_str}" start="0s">
                    <adjust-transform position="{fcpxml_action_x} {fcpxml_action_y}" scale="{fcpxml_action_zoom} {fcpxml_action_zoom}"/>
                    <text>
                      <text-style ref="{style_action_id}">{escape(act_label)}</text-style>
                    </text>
                    <text-style-def id="{style_action_id}">
                      <text-style font="{escape(font_family)}" fontSize="{font_size_spk}" fontFace="Bold Italic" italic="1" fontColor="1 0.88 0.28 1" strokeColor="0 0 0 1" strokeWidth="{stroke_width}" alignment="center" shadowColor="0 0 0 0.95" shadowOffset="2 -2"/>
                    </text-style-def>
                    <param name="Stroke" key="stroke" value="1"/>
                    <param name="Stroke Size" key="stroke_size" value="{stroke_width}"/>
                    <param name="Stroke Color" key="stroke_color" value="0 0 0 1"/>
                  </title>"""
                    actions_xml.append(a_xml)

                # 3. Ses Klibi (Track A1 / lane -1)
                aud_xml = f"""
                  <asset-clip name="{escape(Path(c['abs_path']).stem)}" lane="-1" ref="{c['aud_id']}" offset="{c_rel_offset_str}" duration="{c_dur_str}" start="0s" role="dialogue"/>"""
                audios_xml.append(aud_xml)

            # V1 Kanalı (Spine Video): Görsel grubun başından sonuna kadar tek parça uzanır!
            if g_splash_path and os.path.exists(g_splash_path):
                spine_item = f"""
                <video name="{escape(g_img_stem)}" ref="{g_img_id}" offset="{g_offset_str}" duration="{g_dur_str}" start="0s">
                  <adjust-transform position="{fcpxml_splash_x} {fcpxml_splash_y}" scale="{splash_zoom} {splash_zoom}"/>
                  {''.join(titles_xml)}
                  {''.join(actions_xml)}
                  {''.join(audios_xml)}
                </video>"""
            else:
                # Görsel yoksa ilk klibin altyazısı spine olur
                first_t = titles_xml[0] if titles_xml else ""
                other_t = titles_xml[1:]
                spine_item = f"""
                <title name="{escape(first_item['spk_upper'])}" ref="r_title" offset="{g_offset_str}" duration="{g_dur_str}" start="0s">
                  <adjust-transform position="{fcpxml_text_x} {fcpxml_text_y}"/>
                  <text>
                    <text-style ref="ts_spk_{first_item['idx']}">{escape(first_item['spk_upper'])}</text-style>
                    <text-style ref="ts_quote_{first_item['idx']}">&#13;&#10;{first_item['formatted_quote']}</text-style>
                  </text>
                  <text-style-def id="ts_spk_{first_item['idx']}">
                    <text-style font="Poppins" fontSize="56" fontFace="Bold" fontColor="0.25 0.88 0.95 1" alignment="center"/>
                  </text-style-def>
                  <text-style-def id="ts_quote_{first_item['idx']}">
                    <text-style font="Poppins" fontSize="48" fontFace="Bold" fontColor="1 0.88 0.28 1" alignment="center"/>
                  </text-style-def>
                  {''.join(other_t)}
                  {''.join(actions_xml)}
                  {''.join(audios_xml)}
                </title>"""

            spine_items.append(spine_item)
            current_frame += g_total_frames

            # Gruplar arasına gap ekleme (son gruptan sonra eklenmez)
            if g_idx < len(groups) - 1 and gap_frames > 0:
                gap_offset_str = f"{current_frame}/{fps}s"
                gap_dur_str = f"{gap_frames}/{fps}s"
                spine_items.append(f'<gap name="Gap" offset="{gap_offset_str}" duration="{gap_dur_str}" start="0s"/>')
                current_frame += gap_frames

        total_dur_str = f"{max(1, current_frame)}/{fps}s"

        fcpxml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE fcpxml>
<fcpxml version="1.8">
  <resources>
    {''.join(resources)}
  </resources>
  <library>
    <event name="LoL Sesler">
      <project name="{escape(timeline_name)}">
        <sequence format="r1" duration="{total_dur_str}">
          <spine>
            {''.join(spine_items)}
          </spine>
        </sequence>
      </project>
    </event>
  </library>
</fcpxml>"""

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(fcpxml_content)

        return output_path

    @staticmethod
    def copy_to_windows_clipboard(text: str) -> bool:
        """
        Windows Panosuna (Clipboard) UTF-16 Unicode metin kopyalar.
        64-bit güvenli ctypes Win32 API, Tkinter ve PowerShell fallback mekanizmaları içerir.
        """
        if not text:
            return False

        # 1. 64-bit Güvenli Win32 API (ctypes)
        try:
            import ctypes

            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32

            kernel32.GlobalAlloc.restype = ctypes.c_void_p
            kernel32.GlobalAlloc.argtypes = [ctypes.c_uint, ctypes.c_size_t]
            kernel32.GlobalLock.restype = ctypes.c_void_p
            kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
            kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
            user32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]
            user32.OpenClipboard.argtypes = [ctypes.c_void_p]

            CF_UNICODETEXT = 13
            GMEM_MOVEABLE = 0x0002

            if user32.OpenClipboard(None):
                try:
                    user32.EmptyClipboard()
                    data = text.encode('utf-16le') + b'\x00\x00'
                    h_mem = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
                    if h_mem:
                        p_mem = kernel32.GlobalLock(h_mem)
                        if p_mem:
                            ctypes.memmove(p_mem, data, len(data))
                            kernel32.GlobalUnlock(h_mem)
                            user32.SetClipboardData(CF_UNICODETEXT, h_mem)
                            return True
                finally:
                    user32.CloseClipboard()
        except Exception:
            pass

        # 2. Tkinter Fallback
        try:
            import tkinter as tk
            root = tk.Tk()
            root.withdraw()
            root.clipboard_clear()
            root.clipboard_append(text)
            root.update()
            root.destroy()
            return True
        except Exception:
            pass

        # 3. PowerShell Fallback
        try:
            import subprocess
            cmd = ["powershell", "-NoProfile", "-Command", "$input | Set-Clipboard"]
            p = subprocess.Popen(cmd, stdin=subprocess.PIPE, creationflags=0x08000000)
            p.communicate(input=text.encode('utf-8'))
            return p.returncode == 0
        except Exception:
            pass

        return False

    @classmethod
    def generate_fusion_typewriter_comp(
        cls,
        sorted_files,
        output_setting_path=None,
        gap_seconds=0.8,
        fps=60,
        copy_to_clipboard=True,
        target_champion=None,
        width=2560,
        height=1440,
        font="Poppins",
        style="SemiBold",
        size=0.046
    ):
        """
        DaVinci Resolve Free ve Studio için %100 Yerel Text+ (Fusion TextPlus) Daktilo Şablonu.
        
        Özellikler:
        - Standart ilkel 'Text' yerine gerçek vektörel 'TextPlus' düğümleri üretir.
        - Harf harf akıcı Daktilo (Write-On) animasyonu: Cümle uzunluğuna göre ~0.5s - 1.1s arasında
          tamamlanır, replik bitene kadar ekranda tam okunur kalır, son 10-12 karede fade out olur.
        - DaVinci'nin düğüm editöründe üst üste binmez; düzenli bir şerit (grid) halinde dizilir.
        - Üretilen düğüm ağacını hem .setting dosyasına kaydeder hem de Windows Panosuna kopyalar.
        - Kullanıcı DaVinci'de boş bir Fusion Composition açıp Ctrl + V yaptığında anında yapışır.
        """
        try:
            from ai_voice_detector import AIVoiceDetector
        except ImportError:
            try:
                import sys
                sys.path.append(os.path.dirname(os.path.abspath(__file__)))
                from ai_voice_detector import AIVoiceDetector
            except Exception:
                AIVoiceDetector = None

        def escape_lua(s: str) -> str:
            return s.replace('\\', '\\\\').replace('"', '\\"').replace('\r', '').replace('\n', '\\n')

        def balance_wrap(text: str, max_chars: int = 40) -> str:
            """
            Maksimum 2 satır kuralı: 40 karakterden uzun replikleri tam ortasından 
            iki dengeli satıra katlar. Asla 3 satıra bölmez.
            """
            if len(text) <= max_chars:
                return text
            mid = len(text) // 2
            best_split = -1
            min_dist = 99999
            for i, ch in enumerate(text):
                if ch == ' ':
                    dist = abs(i - mid)
                    if dist < min_dist:
                        min_dist = dist
                        best_split = i
            if best_split != -1:
                line1 = text[:best_split].strip()
                line2 = text[best_split+1:].strip()
                return f"{line1}\n{line2}"
            return text

        # Hedef Şampiyonu ve Özel Sıralamayı (Lore / Anlatı Hiyerarşisi) Otomatik Algıla
        if not (sorted_files and isinstance(sorted_files[0], dict)):
            if not target_champion and sorted_files:
                norm_parts = os.path.abspath(sorted_files[0]).replace('/', os.sep).split(os.sep)
                if 'Champions' in norm_parts:
                    c_idx = norm_parts.index('Champions')
                    if c_idx + 1 < len(norm_parts):
                        target_champion = norm_parts[c_idx + 1]

            # XML ile %100 birebir aynı akıllı sırayı (Yone, Taliyah, Ahri vb.) garanti et
            sorted_files = cls.filter_and_sort_files(sorted_files, exclude_sfx=True, smart_sort=True, target_champion=target_champion)

        # 1. Aşama: Timeline yerleşimini ve toplam kare sayısını önceden hesapla
        clips_info = []
        calc_frame = 0
        for idx, file_item in enumerate(sorted_files):
            abs_path = os.path.abspath(file_item['audio_path'] if isinstance(file_item, dict) else file_item)
            duration_sec, _, _, _ = cls.get_audio_info_fast(abs_path)
            dur_frames = max(1, int(round(duration_sec * fps)))
            if idx > 0 and gap_seconds > 0:
                calc_frame += int(round(gap_seconds * fps))
            s_frame = calc_frame
            e_frame = s_frame + dur_frames
            calc_frame = e_frame
            clips_info.append({
                "path": abs_path,
                "file_name": os.path.basename(abs_path),
                "dur_sec": duration_sec,
                "dur_frames": dur_frames,
                "start_frame": s_frame,
                "end_frame": e_frame,
                "item_dict": file_item if isinstance(file_item, dict) else None
            })

        total_timeline_frames = max(1, calc_frame + 60)
        total_clips = len(clips_info)
        tools_entries = []

        # 2. Aşama: Düğümleri ve zaman kilitli (time-bounded) keyframe'leri üret
        for idx, c_info in enumerate(clips_info):
            abs_path = c_info["path"]
            file_name = c_info["file_name"]
            dur_frames = c_info["dur_frames"]
            start_frame = c_info["start_frame"]
            end_frame = c_info["end_frame"]

            # Konuşmacı ve Eylem Tespiti
            spk_raw = file_name.split('_')[0].capitalize()
            action_type = "Replik"
            if 'karsilasma' in file_name:
                action_type = "Karşılaşma"
            elif 'katletme' in file_name:
                action_type = "Katletme"
            elif 'yetenek' in file_name:
                action_type = "Yetenek"

            spoken_text = ""
            if c_info.get("item_dict") and c_info["item_dict"].get("transcript"):
                spoken_text = c_info["item_dict"]["transcript"]
                spk_raw = c_info["item_dict"].get("speaker", spk_raw).capitalize()
            elif AIVoiceDetector:
                try:
                    _, spoken_text = AIVoiceDetector.is_spoken_dialogue(abs_path)
                except Exception:
                    spoken_text = ""

            if spoken_text:
                raw_display_text = f'{spk_raw}: "{spoken_text}"'
            else:
                raw_display_text = f'{spk_raw} ({action_type})'

            display_text = balance_wrap(raw_display_text, max_chars=40)
            lua_text = escape_lua(display_text)

            # Sese %100 Senkron Daktilo (Write-On):
            # Karakter konuştukça harfler ekrana dökülür; konuşma bittiği an daktilo tamamlanır!
            char_len = len(display_text)
            fade_out_dur = min(14, max(4, dur_frames // 6))
            fade_start_frame = max(start_frame + 1, end_frame - fade_out_dur)

            # Daktilo konuşmanın sonuna kadar yayılır (ses biterken son harf yazılır):
            type_dur = max(16, dur_frames - fade_out_dur - 6)
            type_end_frame = start_frame + type_dur

            # Koordinat Grid'i (Yatay şerit: X artar, Merge y=0, TextPlus y=66)
            pos_x = 160 * (idx + 1)
            prev_bg = "Background_Base" if idx == 0 else f"Merge_{idx}"

            # Daktilo Write-On Keyframes (Önce 0, sonra yazar, sonra 1 kalır)
            if start_frame > 0:
                writeon_kf = f"""\t\t\t\t[0] = {{ 0, Flags = {{ Linear = true }} }},
\t\t\t\t[{start_frame}] = {{ 0, Flags = {{ Linear = true }} }},
\t\t\t\t[{type_end_frame}] = {{ 1, Flags = {{ Linear = true }} }},
\t\t\t\t[{total_timeline_frames}] = {{ 1, Flags = {{ Linear = true }} }},"""
            else:
                writeon_kf = f"""\t\t\t\t[0] = {{ 0, Flags = {{ Linear = true }} }},
\t\t\t\t[{type_end_frame}] = {{ 1, Flags = {{ Linear = true }} }},
\t\t\t\t[{total_timeline_frames}] = {{ 1, Flags = {{ Linear = true }} }},"""

            # Opacity Keyframes (Metin kendi aralığı dışında KESİNLİKLE 0 opaklıktadır)
            if start_frame > 0:
                opacity_kf = f"""\t\t\t\t[0] = {{ 0, Flags = {{ Linear = true }} }},
\t\t\t\t[{start_frame - 1}] = {{ 0, Flags = {{ Linear = true }} }},
\t\t\t\t[{start_frame}] = {{ 1, Flags = {{ Linear = true }} }},
\t\t\t\t[{fade_start_frame}] = {{ 1, Flags = {{ Linear = true }} }},
\t\t\t\t[{end_frame}] = {{ 0, Flags = {{ Linear = true }} }},
\t\t\t\t[{total_timeline_frames}] = {{ 0, Flags = {{ Linear = true }} }},"""
            else:
                opacity_kf = f"""\t\t\t\t[0] = {{ 1, Flags = {{ Linear = true }} }},
\t\t\t\t[{fade_start_frame}] = {{ 1, Flags = {{ Linear = true }} }},
\t\t\t\t[{end_frame}] = {{ 0, Flags = {{ Linear = true }} }},
\t\t\t\t[{total_timeline_frames}] = {{ 0, Flags = {{ Linear = true }} }},"""

            # Merge Blend Keyframes (Merge katmanı kendi aralığı dışında KESİNLİKLE 0 blend'dir, asla görünmez)
            if start_frame > 0:
                blend_kf = f"""\t\t\t\t[0] = {{ 0, Flags = {{ Linear = true }} }},
\t\t\t\t[{start_frame - 1}] = {{ 0, Flags = {{ Linear = true }} }},
\t\t\t\t[{start_frame}] = {{ 1, Flags = {{ Linear = true }} }},
\t\t\t\t[{fade_start_frame}] = {{ 1, Flags = {{ Linear = true }} }},
\t\t\t\t[{end_frame}] = {{ 0, Flags = {{ Linear = true }} }},
\t\t\t\t[{total_timeline_frames}] = {{ 0, Flags = {{ Linear = true }} }},"""
            else:
                blend_kf = f"""\t\t\t\t[0] = {{ 1, Flags = {{ Linear = true }} }},
\t\t\t\t[{fade_start_frame}] = {{ 1, Flags = {{ Linear = true }} }},
\t\t\t\t[{end_frame}] = {{ 0, Flags = {{ Linear = true }} }},
\t\t\t\t[{total_timeline_frames}] = {{ 0, Flags = {{ Linear = true }} }},"""

            node_lua = f"""\t\tTextPlus_{idx+1} = TextPlus {{
\t\t\tCtrlWZoom = false,
\t\t\tInputs = {{
\t\t\t\tGlobalIn = Input {{ Value = {start_frame}, }},
\t\t\t\tGlobalOut = Input {{ Value = {end_frame}, }},
\t\t\t\tWidth = Input {{ Value = {width}, }},
\t\t\t\tHeight = Input {{ Value = {height}, }},
\t\t\t\tUseFrameFormatSettings = Input {{ Value = 1, }},
\t\t\t\t["Gamut.SLogVersion"] = Input {{ Value = FuID {{ "SLog2" }}, }},
\t\t\t\tFont = Input {{ Value = "{font}", }},
\t\t\t\tStyle = Input {{ Value = "{style}", }},
\t\t\t\tSize = Input {{ Value = 0.040, }},
\t\t\t\tVerticalJustificationNew = Input {{ Value = 3, }},
\t\t\t\tHorizontalJustificationNew = Input {{ Value = 3, }},
\t\t\t\tCenter = Input {{ Value = {{ 0.5, 0.10 }}, }},
\t\t\t\t-- Hextech Champagne Gold Karakter Rengi
\t\t\t\tRed1 = Input {{ Value = 0.96, }},
\t\t\t\tGreen1 = Input {{ Value = 0.86, }},
\t\t\t\tBlue1 = Input {{ Value = 0.38, }},
\t\t\t\tAlpha1 = Input {{ Value = 1, }},
\t\t\t\t-- Shading Element 2: Kontrast Arka Plan Gölgesi / Outline
\t\t\t\tEnabled2 = Input {{ Value = 1, }},
\t\t\t\tElement2 = Input {{ Value = 2, }},
\t\t\t\tRed2 = Input {{ Value = 0, }},
\t\t\t\tGreen2 = Input {{ Value = 0, }},
\t\t\t\tBlue2 = Input {{ Value = 0, }},
\t\t\t\tAlpha2 = Input {{ Value = 0.85, }},
\t\t\t\tSoftness2 = Input {{ Value = 1.8, }},
\t\t\t\tOffset2 = Input {{ Value = {{ 0.002, -0.002 }}, }},
\t\t\t\tStyledText = Input {{ Value = "{lua_text}", }},
\t\t\t\tStart = Input {{ Value = 0, }},
\t\t\t\tEnd = Input {{
\t\t\t\t\tSourceOp = "TextPlus_{idx+1}_WriteOn",
\t\t\t\t\tSource = "Value",
\t\t\t\t}},
\t\t\t\tWriteOnEnd = Input {{
\t\t\t\t\tSourceOp = "TextPlus_{idx+1}_WriteOn",
\t\t\t\t\tSource = "Value",
\t\t\t\t}},
\t\t\t\tWriteOn = Input {{
\t\t\t\t\tSourceOp = "TextPlus_{idx+1}_WriteOn",
\t\t\t\t\tSource = "Value",
\t\t\t\t}},
\t\t\t\tOpacity1 = Input {{
\t\t\t\t\tSourceOp = "TextPlus_{idx+1}_Opacity",
\t\t\t\t\tSource = "Value",
\t\t\t\t}},
\t\t\t}},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ {pos_x}, 66 }} }},
\t\t}},
\t\tTextPlus_{idx+1}_WriteOn = BezierSpline {{
\t\t\tSplineColor = {{ Red = 250, Green = 210, Blue = 70 }},
\t\t\tKeyFrames = {{
{writeon_kf}
\t\t\t}}
\t\t}},
\t\tTextPlus_{idx+1}_Opacity = BezierSpline {{
\t\t\tSplineColor = {{ Red = 255, Green = 255, Blue = 255 }},
\t\t\tKeyFrames = {{
{opacity_kf}
\t\t\t}}
\t\t}},
\t\tMerge_{idx+1} = Merge {{
\t\t\tInputs = {{
\t\t\t\tBackground = Input {{
\t\t\t\t\tSourceOp = "{prev_bg}",
\t\t\t\t\tSource = "Output",
\t\t\t\t}},
\t\t\t\tForeground = Input {{
\t\t\t\t\tSourceOp = "TextPlus_{idx+1}",
\t\t\t\t\tSource = "Output",
\t\t\t\t}},
\t\t\t\tPerformDepthMerge = Input {{ Value = 0, }},
\t\t\t\tBlend = Input {{
\t\t\t\t\tSourceOp = "Merge_{idx+1}_Blend",
\t\t\t\t\tSource = "Value",
\t\t\t\t}},
\t\t\t}},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ {pos_x}, 0 }} }},
\t\t}},
\t\tMerge_{idx+1}_Blend = BezierSpline {{
\t\t\tSplineColor = {{ Red = 255, Green = 255, Blue = 255 }},
\t\t\tKeyFrames = {{
{blend_kf}
\t\t\t}}
\t\t}},"""
            tools_entries.append(node_lua)

        # Global Subtitle Transform Control (Tek bir düğümden tüm altyazıları büyütme/küçültme/kaydırma)
        control_pos_x = 160 * (total_clips + 1)
        last_merge = f"Merge_{total_clips}" if total_clips > 0 else "Background_Base"
        global_control_node = f"""\t\tSubtitle_Global_Control = Transform {{
\t\t\tInputs = {{
\t\t\t\tInput = Input {{
\t\t\t\t\tSourceOp = "{last_merge}",
\t\t\t\t\tSource = "Output",
\t\t\t\t}},
\t\t\t\tCenter = Input {{ Value = {{ 0.5, 0.5 }}, }},
\t\t\t\tSize = Input {{ Value = 1.0, }},
\t\t\t}},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ {control_pos_x}, 0 }} }},
\t\t}},"""
        tools_entries.append(global_control_node)

        active_tool = "Subtitle_Global_Control"

        base_bg = f"""\t\tBackground_Base = Background {{
\t\t\tInputs = {{
\t\t\t\tGlobalIn = Input {{ Value = 0, }},
\t\t\t\tGlobalOut = Input {{ Value = {total_timeline_frames}, }},
\t\t\t\tWidth = Input {{ Value = {width}, }},
\t\t\t\tHeight = Input {{ Value = {height}, }},
\t\t\t\tUseFrameFormatSettings = Input {{ Value = 1, }},
\t\t\t\t["TopLeftAlpha"] = Input {{ Value = 0, }},
\t\t\t}},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ 0, 0 }} }},
\t\t}},"""

        all_tools = [base_bg] + tools_entries
        full_tools_str = "\n".join(all_tools)

        setting_content = f"""{{\n\tTools = ordered() {{\n{full_tools_str}\n\t}},\n\tActiveTool = "{active_tool}"\n}}"""

        # Save to .setting file if path provided
        if output_setting_path:
            os.makedirs(os.path.dirname(os.path.abspath(output_setting_path)), exist_ok=True)
            with open(output_setting_path, 'w', encoding='utf-8') as f:
                f.write(setting_content)

        # Copy to Windows Clipboard
        clipboard_ok = False
        if copy_to_clipboard:
            try:
                clipboard_ok = cls.copy_to_windows_clipboard(setting_content)
            except Exception:
                clipboard_ok = False

        return output_setting_path, total_clips, clipboard_ok

    @classmethod
    def convert_srt_to_fcpxml(cls, srt_path, output_fcpxml_path=None, fps=60, timeline_name="Subtitle Titles", fade_in_seconds=1.5, fade_out_seconds=0.5):
        """
        Dahili SRT -> DaVinci Resolve FCPXML Text+ Title Converter.
        İnternetteki harici sitelere ihtiyaç duymadan herhangi bir .srt dosyasını 
        DaVinci Resolve'da anında düzenlenebilir Text+ (Fusion Title) kliplerine dönüştürür.
        """
        if not os.path.isfile(srt_path):
            raise FileNotFoundError(f"SRT dosyası bulunamadı: {srt_path}")

        if not output_fcpxml_path:
            output_fcpxml_path = os.path.splitext(srt_path)[0] + ".fcpxml"

        with open(srt_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        import re
        srt_pattern = re.compile(
            r'(\d+)\s*\n'
            r'(\d{2}):(\d{2}):(\d{2})[,\.](\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})[,\.](\d{3})\s*\n'
            r'([\s\S]*?)(?=\n\s*\d+\s*\n|\Z)',
            re.MULTILINE
        )

        matches = list(srt_pattern.finditer(content))
        if not matches:
            raise ValueError("SRT dosyası içinde geçerli altyazı bloğu bulunamadı.")

        resources = [
            f'<format id="r1" name="FFVideoFormat2160p{fps}" frameDuration="1/{fps}s" width="2560" height="1440"/>',
            f'<effect id="r_title" name="Text+" uid=".../Titles.localized/Fusion Titles.localized/Text+.localized/Text+.moti"/>',
            f'<effect id="r_dissolve" name="Cross Dissolve" uid=".../Transitions.localized/Dissolves.localized/Cross Dissolve.localized/Cross Dissolve.motr"/>'
        ]

        spine_items = []
        last_end_frame = 0

        for idx, match in enumerate(matches):
            sh, sm, ss, sms = int(match.group(2)), int(match.group(3)), int(match.group(4)), int(match.group(5))
            eh, em, es, ems = int(match.group(6)), int(match.group(7)), int(match.group(8)), int(match.group(9))

            start_sec = sh * 3600 + sm * 60 + ss + sms / 1000.0
            end_sec = eh * 3600 + em * 60 + es + ems / 1000.0
            dur_sec = max(0.1, end_sec - start_sec)

            start_frame = int(round(start_sec * fps))
            dur_frames = max(1, int(round(dur_sec * fps)))

            # HTML/Font tag temizliği ve Karakter Adı / Replik Ayrıştırma
            raw_text = match.group(10).strip()
            lines = [l.strip() for l in raw_text.split('\n') if l.strip()]
            spk_part = ""
            quote_part = ""
            if len(lines) >= 2:
                spk_part = re.sub(r'<[^>]+>', '', lines[0]).strip(' :"\'-')
                quote_part = ' '.join([re.sub(r'<[^>]+>', '', l).strip(' "\'') for l in lines[1:]])
            elif ':' in raw_text:
                parts = raw_text.split(':', 1)
                spk_part = re.sub(r'<[^>]+>', '', parts[0]).strip(' :"\'-')
                quote_part = re.sub(r'<[^>]+>', '', parts[1]).strip(' "\'')
            else:
                quote_part = re.sub(r'<[^>]+>', '', raw_text).strip(' "\'')

            # Önceki altyazı ile bu altyazı arasında boşluk varsa gap ekle
            gap_frames = start_frame - last_end_frame
            if gap_frames > 0:
                gap_offset_str = f"{last_end_frame}/{fps}s"
                gap_dur_str = f"{gap_frames}/{fps}s"
                spine_items.append(f'<gap name="Gap" offset="{gap_offset_str}" duration="{gap_dur_str}" start="0s"/>')

            title_offset_str = f"{start_frame}/{fps}s"
            title_dur_str = f"{dur_frames}/{fps}s"

            # Title Clip (1. Satır Cyan Karakter Adı, 2. Satır Altın Sarısı Tırnaksız Replik)
            if spk_part and len(spk_part.split()) <= 2:
                spk_upper = cls.turkish_upper(spk_part)
                clean_quote = cls.balance_wrap(quote_part, max_chars=42)
                formatted_quote = escape(clean_quote).replace('\n', '&#10;')
                title_item = f"""<title ref="r_title" name="{escape(spk_upper)}" offset="{title_offset_str}" duration="{title_dur_str}" start="0s">
              <text>
                <text-style ref="ts_spk_{idx+1}">{escape(spk_upper)}&#10;</text-style>
                <text-style ref="ts_quote_{idx+1}">{formatted_quote}</text-style>
              </text>
              <text-style-def id="ts_spk_{idx+1}">
                <text-style font="Poppins" fontSize="56" fontColor="0.30 0.85 0.95 1" bold="1" alignment="center" shadowColor="0 0 0 0.9" shadowOffset="3 -3"/>
              </text-style-def>
              <text-style-def id="ts_quote_{idx+1}">
                <text-style font="Poppins" fontSize="48" fontColor="0.95 0.82 0.25 1" bold="1" alignment="center" shadowColor="0 0 0 0.9" shadowOffset="3 -3"/>
              </text-style-def>
            </title>"""
            else:
                clean_quote = cls.balance_wrap(quote_part, max_chars=42)
                formatted_quote = escape(clean_quote).replace('\n', '&#10;')
                title_item = f"""<title ref="r_title" name="Subtitle_{idx+1}" offset="{title_offset_str}" duration="{title_dur_str}" start="0s">
              <text>
                <text-style ref="ts{idx+1}">{formatted_quote}</text-style>
              </text>
              <text-style-def id="ts{idx+1}">
                <text-style font="Poppins" fontSize="52" fontColor="0.95 0.82 0.25 1" bold="1" alignment="center" shadowColor="0 0 0 0.85" shadowOffset="3 -3"/>
              </text-style-def>
            </title>"""
            spine_items.append(title_item)

            last_end_frame = start_frame + dur_frames

        total_dur_str = f"{max(1, last_end_frame)}/{fps}s"

        fcpxml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE fcpxml>
<fcpxml version="1.8">
  <resources>
    {''.join(resources)}
  </resources>
  <library>
    <event name="LoL Altyazılar">
      <project name="{escape(timeline_name)}">
        <sequence format="r1" duration="{total_dur_str}">
          <spine>
            {''.join(spine_items)}
          </spine>
        </sequence>
      </project>
    </event>
  </library>
</fcpxml>"""

        os.makedirs(os.path.dirname(os.path.abspath(output_fcpxml_path)), exist_ok=True)
        with open(output_fcpxml_path, 'w', encoding='utf-8') as f:
            f.write(fcpxml_content)

        return output_fcpxml_path

    @classmethod
    def _resolve_and_bundle_splash(cls, skins_db, champ_name, skin_num=0, skin_name="", wav_fallback=None, target_fallback="", splash_dir=None, bundle_folder=True, is_lor=False):
        """Şampiyon ve kostüm bilgisine göre 4K Splash Art'ı (veya LoR runeterra.ar kart görselini) indirir ve proje klasörüne kopyalar."""
        if not champ_name:
            return None
        skin_num = int(skin_num or 0)
        skin_data = None

        def _norm_k(s):
            if not s:
                return ""
            s = s.replace('İ', 'i').replace('I', 'i').replace('ı', 'i')
            s = s.replace('Ş', 's').replace('ş', 's')
            s = s.replace('Ğ', 'g').replace('ğ', 'g')
            s = s.replace('Ü', 'u').replace('ü', 'u')
            s = s.replace('Ö', 'o').replace('ö', 'o')
            s = s.replace('Ç', 'c').replace('ç', 'c')
            return re.sub(r'[^a-zA-Z0-9]', '', str(s).lower())

        target_norm = _norm_k(champ_name)

        # Eğer LoR modundaysak önce lor_full_database içinden kart kodunu ve runeterra.ar / DataDragon URL'lerini kontrol et
        if is_lor:
            try:
                import jit_audio_streamer
                lor_db = jit_audio_streamer.get_lor_full_db()
                char_meta = lor_db.get('char_meta', {})
                cmeta = char_meta.get(champ_name)
                if not cmeta:
                    # Normalizasyon ile tam eşleşme ara
                    for k, v in char_meta.items():
                        if _norm_k(k) == target_norm:
                            cmeta = v
                            break
                if not cmeta and target_norm:
                    # Kısmi içerik eşleşmesi ara
                    for k, v in char_meta.items():
                        nk = _norm_k(k)
                        if nk and (target_norm == nk or target_norm in nk or nk in target_norm):
                            cmeta = v
                            break

                if cmeta:
                    code = cmeta.get('base_code', '')
                    c_set = cmeta.get('set', 'Set1')
                    skins_dict = cmeta.get('skins', {})
                    chosen_sk = skins_dict.get(str(skin_num)) or skins_dict.get(skin_num)
                    if not chosen_sk and skin_name:
                        sn_norm = _norm_k(skin_name)
                        for s_k, s_v in skins_dict.items():
                            if sn_norm in _norm_k(s_v.get('name', '')):
                                chosen_sk = s_v
                                break
                    if chosen_sk and chosen_sk.get('card_code'):
                        code = chosen_sk['card_code']
                    elif skin_num > 0 and len(cmeta.get('codes', [])) > skin_num:
                        code = cmeta['codes'][skin_num]

                    if target_norm == 'jax':
                        code = '06RU008'
                        c_set = 'set6'
                    elif target_norm in ('lillia', 'lilia'):
                        code = '09IO052'
                        c_set = 'set9'
                    elif target_norm == 'neeko':
                        code = '07RU012'
                        c_set = 'set7'

                    # Birincil: Riot DataDragon 2048x1024 kristal netliğinde PNG kart çizimi!
                    # İkincil: runeterra.ar WebP kart çizimi!
                    dd_url = f"https://dd.b.pvp.net/latest/{c_set.lower()}/en_us/img/cards/{code}-full.png"
                    ar_url = f"https://cdn.runeterra.ar/assets/img/card/en_us/{code}-full.webp"
                    skin_data = {
                        "skin_id": f"LOR_{code}_{skin_num}",
                        "champion_name": cmeta.get('name') or champ_name,
                        "skin_num": skin_num,
                        "name_tr": (chosen_sk.get('name') if chosen_sk else None) or skin_name or f"LoR_{champ_name}",
                        "splash_url": dd_url if code else cmeta.get('splash_url', ''),
                        "extra_urls": [dd_url, ar_url] if code else []
                    }
            except Exception as e:
                print(f"⚠️ LoR meta cozumleme hatasi ({champ_name}): {e}")

        # Eğer LoR ise ve hala skin_data bulunamadıysa ASLA LoL kostümlerine düşme!
        if is_lor and not skin_data:
            # Genel bir LoR kartı formatı oluştur
            safe_c = re.sub(r'[^a-zA-Z0-9]', '', champ_name)
            skin_data = {
                "skin_id": f"LOR_{safe_c}_{skin_num}",
                "champion_name": champ_name,
                "skin_num": skin_num,
                "name_tr": skin_name or f"LoR_{champ_name}",
                "splash_url": "",
                "extra_urls": []
            }

        if not skin_data and not is_lor:
            for s in skins_db:
                c_cand = s.get('champion_name') or s.get('champion_alias') or ''
                if c_cand.lower() == champ_name.lower() and int(s.get('skin_num', 0)) == skin_num:
                    skin_data = s
                    break
        if not skin_data and skin_name and not is_lor:
            for s in skins_db:
                c_cand = s.get('champion_name') or s.get('champion_alias') or ''
                if c_cand.lower() == champ_name.lower() and (skin_name in s.get('name_tr', '') or s.get('name_tr', '') in skin_name):
                    skin_data = s
                    break
        if not skin_data and wav_fallback and not is_lor:
            skin_data = cls.resolve_speaker_and_skin(wav_fallback, target_champion=target_fallback)

        if not skin_data:
            skin_data = {
                "champion_name": champ_name,
                "skin_num": skin_num,
                "name_tr": skin_name or f"Varsayılan {champ_name}",
                "splash_url": f"https://ddragon.leagueoflegends.com/cdn/img/champion/splash/{champ_name}_{skin_num}.jpg"
            }

        raw_splash = cls.get_or_download_splash_art(skin_data, force_4k=True)
        if raw_splash and os.path.exists(raw_splash):
            if bundle_folder and splash_dir:
                safe_skin = re.sub(r'[^a-zA-Z0-9_]', '', skin_name or f"Skin_{skin_num}")
                dest_splash_name = f"{champ_name}_{safe_skin}_4K.jpg"
                dest_splash_path = os.path.join(splash_dir, dest_splash_name)
                try:
                    import shutil
                    if os.path.abspath(raw_splash) != os.path.abspath(dest_splash_path):
                        shutil.copy2(raw_splash, dest_splash_path)
                    return dest_splash_path
                except Exception:
                    return raw_splash
            return raw_splash
        return None

    # 4K LoL Splash Art & LoR Kartlarında Karakter Yüz/Kafa Merkez Koordinatları (fx, fy)
    # Riot Resmi Centered Splash + Square Portrait NCC Eşleştirmesi + UltraFace ONNX ile doğrulanmış gerçek koordinatlar.
    CHAMPION_SPLASH_FACE_COORDS = {
        "04sh003": (0.50, 0.24), "aatrox": (0.662, 0.285), "ahri": (0.592, 0.224), "akali": (0.499, 0.156),
        "akshan": (0.400, 0.145), "alistar": (0.598, 0.340), "ambessa": (0.420, 0.155), "amumu": (0.683, 0.311),
        "anivia": (0.507, 0.340), "annie": (0.788, 0.320), "aphelios": (0.549, 0.195), "ashe": (0.657, 0.201),
        "aurelionsol": (0.540, 0.141), "aurora": (0.560, 0.158), "azir": (0.747, 0.186), "bard": (0.607, 0.220),
        "belveth": (0.397, 0.280), "blitzcrank": (0.699, 0.308), "brand": (0.767, 0.220), "braum": (0.767, 0.186),
        "briar": (0.519, 0.279), "caitlyn": (0.730, 0.192), "camille": (0.837, 0.153), "cassiopeia": (0.607, 0.269),
        "chogath": (0.573, 0.340), "corki": (0.670, 0.288), "darius": (0.530, 0.158), "diana": (0.679, 0.337),
        "draven": (0.717, 0.271), "drmundo": (0.526, 0.196), "ekko": (0.722, 0.222), "elise": (0.707, 0.136),
        "evelynn": (0.512, 0.178), "ezreal": (0.620, 0.277), "fiddlesticks": (0.520, 0.240), "fiora": (0.637, 0.151),
        "fizz": (0.812, 0.229), "galio": (0.497, 0.140), "gangplank": (0.719, 0.251), "garen": (0.792, 0.318),
        "gnar": (0.727, 0.420), "gragas": (0.570, 0.226), "graves": (0.737, 0.140), "gwen": (0.499, 0.179),
        "hecarim": (0.677, 0.153), "heimerdinger": (0.722, 0.368), "hwei": (0.593, 0.192), "illaoi": (0.589, 0.150),
        "irelia": (0.517, 0.135), "ivern": (0.527, 0.235), "janna": (0.829, 0.291), "jarvaniv": (0.717, 0.186),
        "jax": (0.666, 0.303), "jayce": (0.767, 0.271), "jhin": (0.582, 0.228), "jinx": (0.649, 0.218),
        "kaisa": (0.497, 0.153), "kalista": (0.577, 0.220), "karma": (0.737, 0.186), "karthus": (0.690, 0.140),
        "kassadin": (0.657, 0.150), "katarina": (0.609, 0.360), "kayle": (0.700, 0.226), "kayn": (0.500, 0.360),
        "kennen": (0.727, 0.252), "khazix": (0.650, 0.280), "kindred": (0.570, 0.260), "kled": (0.780, 0.214),
        "kogmaw": (0.693, 0.360), "ksante": (0.346, 0.190), "leblanc": (0.509, 0.173), "leesin": (0.640, 0.226),
        "leona": (0.667, 0.136), "lillia": (0.439, 0.212), "lissandra": (0.667, 0.153), "locke": (0.622, 0.150),
        "lucian": (0.700, 0.360), "lulu": (0.686, 0.367), "lux": (0.605, 0.268), "malphite": (0.653, 0.264),
        "malzahar": (0.639, 0.193), "maokai": (0.618, 0.360), "masteryi": (0.786, 0.318), "mel": (0.429, 0.150),
        "milio": (0.492, 0.262), "missfortune": (0.739, 0.325), "monkeyking": (0.620, 0.277), "wukong": (0.620, 0.277),
        "mordekaiser": (0.450, 0.135), "morgana": (0.820, 0.294), "naafiri": (0.310, 0.380), "nami": (0.770, 0.277),
        "nasus": (0.677, 0.235), "nautilus": (0.738, 0.219), "neeko": (0.482, 0.262), "nidalee": (0.757, 0.186),
        "nilah": (0.622, 0.303), "nocturne": (0.616, 0.360), "nunu": (0.580, 0.226), "olaf": (0.619, 0.296),
        "orianna": (0.787, 0.151), "ornn": (0.500, 0.340), "pantheon": (0.522, 0.218), "poppy": (0.662, 0.238),
        "pyke": (0.500, 0.316), "qiyana": (0.520, 0.225), "quinn": (0.637, 0.271), "rakan": (0.612, 0.167),
        "rammus": (0.587, 0.360), "reksai": (0.534, 0.360), "rell": (0.477, 0.136), "renata": (0.527, 0.140),
        "renekton": (0.587, 0.196), "rengar": (0.676, 0.340), "riven": (0.737, 0.203), "rumble": (0.680, 0.254),
        "ryze": (0.780, 0.380), "samira": (0.572, 0.190), "sejuani": (0.557, 0.136), "senna": (0.520, 0.243),
        "seraphine": (0.520, 0.240), "sett": (0.487, 0.140), "shaco": (0.687, 0.169), "shen": (0.747, 0.140),
        "shyvana": (0.520, 0.203), "singed": (0.710, 0.231), "sion": (0.673, 0.181), "sivir": (0.537, 0.140),
        "skarner": (0.500, 0.340), "smolder": (0.497, 0.286), "sona": (0.677, 0.186), "soraka": (0.529, 0.150),
        "swain": (0.680, 0.141), "sylas": (0.525, 0.252), "syndra": (0.487, 0.203), "tahmkench": (0.683, 0.295),
        "taliyah": (0.766, 0.233), "talon": (0.650, 0.277), "taric": (0.717, 0.140), "teemo": (0.540, 0.286),
        "thresh": (0.614, 0.242), "tristana": (0.649, 0.249), "trundle": (0.547, 0.310), "tryndamere": (0.687, 0.203),
        "twistedfate": (0.720, 0.220), "twitch": (0.590, 0.360), "udyr": (0.540, 0.140), "urgot": (0.569, 0.150),
        "varus": (0.542, 0.161), "vayne": (0.817, 0.203), "veigar": (0.628, 0.277), "velkoz": (0.583, 0.350),
        "vex": (0.657, 0.298), "vi": (0.687, 0.237), "viego": (0.500, 0.200), "viktor": (0.477, 0.220),
        "vladimir": (0.750, 0.220), "volibear": (0.556, 0.144), "warwick": (0.650, 0.380), "xayah": (0.310, 0.271),
        "xerath": (0.570, 0.158), "xinzhao": (0.502, 0.190), "yasuo": (0.777, 0.339), "yone": (0.554, 0.259),
        "yorick": (0.639, 0.140), "yunara": (0.499, 0.296), "yuumi": (0.457, 0.214), "zaahen": (0.565, 0.150),
        "zac": (0.683, 0.380), "zed": (0.612, 0.167), "zeri": (0.560, 0.265), "ziggs": (0.702, 0.380),
        "zilean": (0.577, 0.203), "zoe": (0.539, 0.246), "zyra": (0.737, 0.203)
    }
    _DYNAMIC_FOCUS_CACHE = None

    @classmethod
    def _load_focus_cache(cls) -> dict:
        if cls._DYNAMIC_FOCUS_CACHE is not None:
            return cls._DYNAMIC_FOCUS_CACHE
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cache_file = os.path.join(root_dir, "data", "champion_splash_focus_coords.json")
        data = {}
        if os.path.exists(cache_file):
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                    if isinstance(raw, dict):
                        data = raw
            except Exception:
                pass
        for k, v in cls.CHAMPION_SPLASH_FACE_COORDS.items():
            data[k] = [float(v[0]), float(v[1])]
        cls._DYNAMIC_FOCUS_CACHE = data
        return data

    @classmethod
    def _save_focus_cache_entry(cls, key: str, fx: float, fy: float):
        cache = cls._load_focus_cache()
        cache[key] = [round(float(fx), 3), round(float(fy), 3)]
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cache_file = os.path.join(root_dir, "data", "champion_splash_focus_coords.json")
        try:
            os.makedirs(os.path.dirname(cache_file), exist_ok=True)
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(cache, f, indent=2, sort_keys=True)
        except Exception:
            pass

    @classmethod
    def detect_image_subject_focus_2d(cls, img_path: str) -> tuple:
        """
        Hafif Yerel AI / 2D Portre Yüz & Baş Odaklayıcı:
        1. Doğrulanmış Şampiyon & Kostüm Odak Önbelleği (CHAMPION_SPLASH_FACE_COORDS + JSON Cache)
        2. Özel kostümlerde Riot Resmi Centered Splash (1280x720) Çapraz Korelasyon (NCC) Hizalaması
        3. Yerel ONNX Yüz Dedektörü (data/models/ultraface_320.onnx - ONNX Runtime)
        4. 2D Gövde-Çapalı Baş/Yüz Saliency Dedektörü (NumPy + PIL)
        """
        if not img_path or not os.path.exists(img_path):
            return (0.62, 0.22)

        focus_cache = cls._load_focus_cache()
        fname = os.path.splitext(os.path.basename(img_path))[0].lower()
        clean_fname = re.sub(r'[^a-z0-9]', '', fname)

        # 0. Tam dosya adı önbellekte varsa doğrudan dön
        if clean_fname in focus_cache:
            c = focus_cache[clean_fname]
            return (float(c[0]), float(c[1]))

        # 1. Dosya adından bilinen LoL/LoR şampiyon yüz koordinatını kontrol et
        matched_champ_key = None
        for champ_key in sorted(cls.CHAMPION_SPLASH_FACE_COORDS.keys(), key=len, reverse=True):
            if champ_key in clean_fname:
                matched_champ_key = champ_key
                # Eğer temel kostüm (_0 veya varsayılan / varsaylan) ise doğrudan doğrulanmış kafa koordinatını kullan
                if any(k in clean_fname for k in ('varsayilan', 'varsaylan', 'default')) or '_0' in fname or not re.search(r'_[1-9]\d*', fname):
                    return cls.CHAMPION_SPLASH_FACE_COORDS[champ_key]
                break

        # 2. Yerel ONNX yüz/baş dedektörü varsa çalıştır (data/models/ultraface_320.onnx)
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        onnx_model_path = os.path.join(root_dir, "data", "models", "ultraface_320.onnx")
        if os.path.exists(onnx_model_path):
            try:
                import onnxruntime as ort
                import numpy as np
                from PIL import Image
                sess = getattr(cls, "_onnx_face_sess", None)
                if sess is None:
                    so = ort.SessionOptions()
                    so.log_severity_level = 3
                    sess = ort.InferenceSession(onnx_model_path, sess_options=so, providers=["CPUExecutionProvider"])
                    cls._onnx_face_sess = sess
                with Image.open(img_path) as im:
                    im_rgb = im.convert("RGB").resize((320, 240))
                    arr = (np.asarray(im_rgb, dtype=np.float32) - 127.0) / 128.0
                    arr = np.transpose(arr, (2, 0, 1))[np.newaxis, ...]
                    conf, boxes = sess.run(None, {sess.get_inputs()[0].name: arr})
                    scores = conf[0, :, 1]
                    best_idx = int(np.argmax(scores))
                    if scores[best_idx] > 0.58:
                        bx = boxes[0, best_idx]
                        fx = max(0.18, min(0.86, float((bx[0] + bx[2]) * 0.5)))
                        fy = max(0.12, min(0.42, float((bx[1] + bx[3]) * 0.5)))
                        cls._save_focus_cache_entry(clean_fname, fx, fy)
                        return (fx, fy)
            except Exception:
                pass

        # 3. 2D Gövde-Çapalı Baş/Yüz Saliency Dedektörü (NumPy + PIL)
        # LoL Splash Art'larda karakterlerin %80'i sağ yarıda (0.58..0.78) yer aldığı için sağ-merkez önceliğiyle tarar
        try:
            import numpy as np
            from PIL import Image, ImageFilter
            with Image.open(img_path) as img:
                rgb = img.convert("RGB").resize((240, 135), Image.Resampling.BILINEAR)
                gray = rgb.convert("L")
                edges = np.asarray(gray.filter(ImageFilter.FIND_EDGES), dtype=np.float32)
                arr_rgb = np.asarray(rgb, dtype=np.float32)
                sh, sw = edges.shape

                r, g, b = arr_rgb[:, :, 0], arr_rgb[:, :, 1], arr_rgb[:, :, 2]
                lum = 0.299 * r + 0.587 * g + 0.114 * b
                warm_face = np.clip((r - b) * 0.35 + (lum > 70) * 18.0, 0.0, 60.0)
                head_map = (edges * 1.35) + warm_face

                y_start, y_end = int(sh * 0.10), int(sh * 0.44)
                x_start, x_end = int(sw * 0.18), int(sw * 0.86)
                win_w, win_h = int(sw * 0.14), int(sh * 0.16)

                best_score = -1.0
                best_cx, best_cy = 0.64, 0.22
                for y0 in range(y_start, max(y_start + 1, y_end - win_h), 3):
                    for x0 in range(x_start, max(x_start + 1, x_end - win_w), 4):
                        head_patch = head_map[y0:y0 + win_h, x0:x0 + win_w]
                        ty0 = min(sh - 4, y0 + win_h)
                        ty1 = min(sh, ty0 + int(sh * 0.22))
                        tx0 = max(0, x0 - win_w // 3)
                        tx1 = min(sw, x0 + win_w + win_w // 3)
                        torso_patch = edges[ty0:ty1, tx0:tx1]
                        torso_support = float(np.mean(torso_patch)) if torso_patch.size > 0 else 1.0

                        cx_norm = (x0 + win_w * 0.5) / float(sw)
                        cy_norm = (y0 + win_h * 0.5) / float(sh)
                        horiz_prior = 1.0 - 0.18 * (abs(cx_norm - 0.64) ** 2)
                        vert_prior = 1.0 - 0.30 * (abs(cy_norm - 0.22) / 0.25) ** 2
                        score = float(np.mean(head_patch)) * (0.65 + 0.35 * (torso_support / (torso_support + 25.0))) * horiz_prior * vert_prior
                        if score > best_score:
                            best_score = score
                            best_cx, best_cy = cx_norm, cy_norm

                fx = max(0.18, min(0.85, best_cx))
                fy = max(0.12, min(0.42, best_cy))
                cls._save_focus_cache_entry(clean_fname, fx, fy)
                return (fx, fy)
        except Exception:
            pass
        if matched_champ_key:
            return cls.CHAMPION_SPLASH_FACE_COORDS[matched_champ_key]
        return (0.62, 0.22)

    @classmethod
    def detect_image_subject_focus(cls, img_path: str) -> float:
        """
        Görselin yatay karakter yüz odak noktasını döner (detect_image_subject_focus_2d ile senkron).
        """
        fx, _ = cls.detect_image_subject_focus_2d(img_path)
        return fx

    @classmethod
    def _prepare_split_scene_2560x1440(cls, left_img_path: str, right_img_path: str = None, out_dir: str = None, compact_bar: bool = False) -> str:
        """
        DaVinci Resolve'da 1 piksel bile siyah bar veya en-boy eşleme (transform) hatası oluşmasını engellemek için:
        Sol Konuşmacı ve Sağ Hedef karakteri doğrudan 2560x1440 yekpare tuvalde birleştirir.
        - Sol %50 (X: 0..1280): Sol görsel karakterin YÜZÜNE (fx, fy) odaklanarak yerleştirilir.
        - Sağ %50 (X: 1280..2560): Sağ görsel karakterin YÜZÜNE (fx, fy) odaklanarak yerleştirilir.
          (Eğer sağ görsel yoksa sol görsel tam 2560x1440 ekranı kaplar)
        - Ortada (X: 1279..1281): 2px şık ayırıcı çizgi.
        - Alt kısımda daha kibar ve kompakt Frosted Glass (GaussianBlur) yarı saydam koyu cam şeridi.
        """
        if not left_img_path or not os.path.exists(left_img_path):
            return left_img_path
        try:
            from PIL import Image, ImageFilter, ImageEnhance, ImageDraw
            target_dir = out_dir or os.path.dirname(os.path.abspath(left_img_path))
            stem_l = os.path.splitext(os.path.basename(left_img_path))[0]
            stem_r = os.path.splitext(os.path.basename(right_img_path))[0] if right_img_path else "SOLO"
            bar_tag = "c2" if compact_bar else "f2"
            out_name = f"{stem_l}_VS_{stem_r}_SPLIT_v5_{bar_tag}_2560x1440.jpg"
            out_path = os.path.join(target_dir, out_name)
            if os.path.exists(out_path) and os.path.getsize(out_path) > 15000:
                return out_path

            full_w, full_h = 2560, 1440
            half_w = 1280

            def _crop_cover(im_path, w, h):
                with Image.open(im_path) as im:
                    im = im.convert("RGB")
                    orig_w, orig_h = im.size
                    fx, fy = cls.detect_image_subject_focus_2d(im_path)
                    base_scale = max(w / float(orig_w), h / float(orig_h))
                    if w == half_w:
                        # Eğer karakter görselin sağ/sol kenarına çok yakınsa (örn: Garen fx=0.792, Shen fx=0.747, Camille fx=0.837),
                        # yüzün sağ kenara yapışmaması ve tam yarı-ekranın ortasına (w*0.50) gelmesi için dinamik ölçek uygula!
                        edge_dist_x = max(0.16, min(fx, 1.0 - fx))
                        req_w_for_center = (w * 0.50) / edge_dist_x
                        scale_for_x = min(base_scale * 1.32, req_w_for_center / float(orig_w))
                        scale = max(base_scale * 1.12, scale_for_x)
                    else:
                        scale = base_scale
                    sw = max(w, int(round(orig_w * scale)))
                    sh = max(h, int(round(orig_h * scale)))
                    resized = im.resize((sw, sh), Image.Resampling.LANCZOS)
                    center_px = int(round(fx * sw))
                    center_py = int(round(fy * sh))
                    # Karakterin yüzünü yatayda tam ortaya (w*0.50), dikeyde üst-orta altın noktaya (h*0.26) oturt
                    crop_x0 = max(0, min(sw - w, center_px - (w // 2)))
                    crop_y0 = max(0, min(sh - h, center_py - int(h * 0.26)))
                    return resized.crop((crop_x0, crop_y0, crop_x0 + w, crop_y0 + h))

            if right_img_path and os.path.exists(right_img_path):
                left_half = _crop_cover(left_img_path, half_w, full_h)
                right_half = _crop_cover(right_img_path, half_w, full_h)
                canvas = Image.new("RGB", (full_w, full_h))
                canvas.paste(left_half, (0, 0))
                canvas.paste(right_half, (half_w, 0))
                draw = ImageDraw.Draw(canvas)
                # Orta keskin sınır çizgisi (X=1279..1281)
                draw.line([(half_w - 1, 0), (half_w - 1, full_h)], fill=(15, 23, 42), width=3)
            else:
                canvas = _crop_cover(left_img_path, full_w, full_h)
                draw = ImageDraw.Draw(canvas)

            # Alt replik bölgesi için zarif ve taşmayan Frosted Glass / Gaussian Blur şeridi
            if compact_bar:
                # Sadece tek satır eylem/olay yazısı varken (uzun atıf başlıklarının bile sağdan/soldan taşmaması için 1960x116px)
                bx0, by0 = 300, 1222
                bx1, by1 = 2260, 1338
            else:
                # Eylem + Replik metni varken önceki 2440x340px dev kutu yerine yüksekliği zarif ama yanlardan taşmayan 2040x200px kutu
                bx0, by0 = 260, 1160
                bx1, by1 = 2300, 1360

            blur_patch = canvas.crop((bx0, by0, bx1, by1)).filter(ImageFilter.GaussianBlur(radius=22))
            blur_patch = ImageEnhance.Brightness(blur_patch).enhance(0.32)
            canvas.paste(blur_patch, (bx0, by0))

            # Blur kutusunun üst ve alt ince parlak çerçevesi
            draw = ImageDraw.Draw(canvas)
            draw.line([(bx0, by0), (bx1, by0)], fill=(255, 255, 255, 45), width=2)
            draw.line([(bx0, by1), (bx1, by1)], fill=(255, 255, 255, 35), width=2)
            draw.line([(bx0, by0), (bx0, by1)], fill=(255, 255, 255, 40), width=2)
            draw.line([(bx1, by0), (bx1, by1)], fill=(255, 255, 255, 40), width=2)

            canvas.save(out_path, "JPEG", quality=95)
            return out_path
        except Exception as e:
            print(f"⚠️ Split scene hazirlanamadi ({left_img_path}): {e}")
            return left_img_path

    @classmethod
    def _resolve_item_partner(cls, item: dict, primary_champ: str = "Azir") -> str:
        """
        Replikten deterministik ve hatasız partner şampiyon çıkarımı (Jarvan/Irelia, Jax/Nasus vb. karışıklıklarını önler):
        1. raw_event içindeki 'interaction_{type}_{c1}_{c2}' şablonundan çıkarım (örn: JarvanIV_Azir -> Jarvan IV)
        2. partner_champ alanı
        3. target_champ / target alanı (primary_champ haricindekiler)
        """
        raw = str(item.get("raw_event") or item.get("event") or item.get("wem_id") or "")
        m = re.search(r'interaction_(?:enemy|ally)_([a-zA-Z0-9]+)_([a-zA-Z0-9]+)', raw, re.IGNORECASE)
        if m:
            c1, c2 = m.group(1), m.group(2)
            tgt = c2 if c1.lower() == primary_champ.lower() else c1
            if tgt.lower() in ("jarvaniv", "jarvan_iv"):
                return "Jarvan IV"
            return tgt

        p = item.get("partner_champ")
        if p and p.lower() != primary_champ.lower() and p not in ("Diğer", "Hedef", ""):
            if p.lower() in ("jarvaniv", "jarvan_iv"):
                return "Jarvan IV"
            return p

        t = item.get("target_champ") or item.get("target") or item.get("right_champ")
        if t and t.lower() != primary_champ.lower() and t not in ("Diğer", "Hedef", ""):
            if t.lower() in ("jarvaniv", "jarvan_iv"):
                return "Jarvan IV"
            return t

        return None

    @classmethod
    def _clean_action_label(cls, action_raw: str) -> str:
        """
        Kullanıcı İsteği - Üstteki karmaşık eylem metnini sade ve anlaşılır Türkçe başlığa dönüştürür:
        'Varsayılan Azir ⇄ Varsayılan Jax • Azir ➔ Jax (Düşman Karşılaşması #1)' -> 'Düşman Karşılaşması'
        """
        if not action_raw:
            return "Karşılaşma"
        raw = str(action_raw).lower()
        if 'dost' in raw or 'ally' in raw:
            return "Dost Karşılaşması"
        if 'düşman' in raw or 'dusman' in raw or 'enemy' in raw:
            return "Düşman Karşılaşması"
        if any(k in raw for k in ['katlet', 'ölüm', 'olum', 'kill', 'death']):
            return "Katletme"
        if any(k in raw for k in ['kışkırt', 'kiskirt', 'taunt']):
            return "Kışkırtma"
        if any(k in raw for k in ['şaka', 'saka', 'joke']):
            return "Şaka"
        if any(k in raw for k in ['blok', 'savunma', 'guard', 'block']):
            return "Savunma & Blok"
        if any(k in raw for k in ['büyü', 'buyu', 'spell', 'saldırı', 'saldiri', 'attack']):
            return "Büyü & Saldırı"
        m = re.search(r'\(([^#\)]+)(?:#\d+)?\)', str(action_raw))
        if m:
            clean = m.group(1).strip()
            if clean:
                return f"{clean}"
        return "Karşılaşma"

    @classmethod
    def _prepare_versus_scene_2560x1440(cls, left_img_path: str, right_img_path: str, speaking_side: str = "left", left_name: str = "Şampiyon", right_name: str = "Hedef", is_ally: bool = False, out_dir: str = None) -> str:
        """
        Kullanıcı İsteği - Preview ile Birebir Aynı Versus Sahnesi (2560x1440):
        - Sol ve Sağda iki karakter kartı (1080x608).
        - Yuvarlak / Kare Kart Desteği (Madde 7): 16:9'a zorlanmadan 608x608 dairesel formatta, dairesel border ve glow ile hizalı gösterilir.
        - Dost Karşılaşması Rengi (Madde 4): Dost ise zümrüt yeşili (16, 185, 129), düşman ise gül kırmızısı (244, 63, 94).
        - Yükseklik farkı: Konuşan kart Y=270 (hafif yukarıda), Dinleyen kart Y=340 (hafif aşağıda, 70px fark).
        - Dinleyen kart: Sönük koyu border, %65 parlaklık.
        """
        if not left_img_path or not os.path.exists(left_img_path):
            return left_img_path
        try:
            from PIL import Image, ImageFilter, ImageEnhance, ImageDraw
            target_dir = out_dir or os.path.dirname(os.path.abspath(left_img_path))
            stem_l = os.path.splitext(os.path.basename(left_img_path))[0]
            stem_r = os.path.splitext(os.path.basename(right_img_path))[0] if (right_img_path and os.path.exists(right_img_path)) else "SOLO"
            safe_l = re.sub(r'[^a-zA-Z0-9_]', '_', cls.turkish_to_ascii(stem_l)).strip('_')
            safe_r = re.sub(r'[^a-zA-Z0-9_]', '_', cls.turkish_to_ascii(stem_r)).strip('_')
            safe_rel = "ALLY" if is_ally else "ENEMY"
            out_name = f"{safe_l}_VS_{safe_r}_{safe_rel}_TURN_{speaking_side}_2560x1440.jpg"
            out_path = os.path.join(target_dir, out_name)
            if os.path.exists(out_path) and os.path.getsize(out_path) > 20000:
                return out_path

            full_w, full_h = 2560, 1440
            canvas = Image.new("RGBA", (full_w, full_h), (8, 12, 20, 255))

            card_w, card_h = 1080, 608
            corner_radius = 24

            left_box_x = 140
            right_box_x = 1340
            left_y = 270 if speaking_side == "left" else 340
            right_y = 270 if speaking_side == "right" else 340

            # Madde 4: Dost karşılaşmalarında yeşil, düşmanda kırmızı border
            ally_rgb = (16, 185, 129)   # Canlı Zümrüt Yeşili
            enemy_rgb = (244, 63, 94)   # Canlı Gül Kırmızısı
            border_color_rgb = ally_rgb if is_ally else enemy_rgb

            def _inspect_is_round(im_path):
                if not im_path or not os.path.exists(im_path):
                    return False
                try:
                    with Image.open(im_path) as im:
                        ow, oh = im.size
                        ratio = float(ow) / float(oh)
                        return (0.75 <= ratio <= 1.25)
                except Exception:
                    return False

            left_is_round = _inspect_is_round(left_img_path)
            right_is_round = _inspect_is_round(right_img_path)

            def _render_card_image(im_path, is_speaker, is_round):
                with Image.open(im_path) as im:
                    im = im.convert("RGBA")
                    orig_w, orig_h = im.size

                    if is_round:
                        # Dairesel kart: Çap = card_h (608px) böylece 16:9 kartla aynı dikey boyutta ve hizada olur
                        d = card_h
                        scale = max(d / float(orig_w), d / float(orig_h))
                        sw = max(d, int(round(orig_w * scale)))
                        sh = max(d, int(round(orig_h * scale)))
                        im_resized = im.resize((sw, sh), Image.Resampling.LANCZOS)
                        cw, ch = im_resized.size
                        cx = max(0, (cw - d) // 2)
                        cy = max(0, (ch - d) // 2)
                        cropped = im_resized.crop((cx, cy, cx + d, cy + d))

                        if not is_speaker:
                            cropped = ImageEnhance.Brightness(cropped).enhance(0.65)

                        mask = Image.new("L", (d, d), 0)
                        draw_m = ImageDraw.Draw(mask)
                        draw_m.ellipse([(0, 0), (d, d)], fill=255)

                        out_im = Image.new("RGBA", (d, d), (0, 0, 0, 0))
                        out_im.paste(cropped, (0, 0), mask=mask)
                        return out_im, d, d
                    else:
                        # 16:9 dikdörtgen kart (Karakterin yüzüne/kafasına akıllı odaklanma)
                        w, h = card_w, card_h
                        fx, fy = cls.detect_image_subject_focus_2d(im_path)
                        base_scale = max(w / float(orig_w), h / float(orig_h))
                        scale = base_scale * 1.08
                        sw = max(w, int(round(orig_w * scale)))
                        sh = max(h, int(round(orig_h * scale)))
                        im_resized = im.resize((sw, sh), Image.Resampling.LANCZOS)
                        cw, ch = im_resized.size
                        center_px = int(round(fx * cw))
                        center_py = int(round(fy * ch))
                        cx = max(0, min(cw - w, center_px - (w // 2)))
                        cy = max(0, min(ch - h, center_py - int(h * 0.32)))
                        cropped = im_resized.crop((cx, cy, cx + w, cy + h))

                        if not is_speaker:
                            cropped = ImageEnhance.Brightness(cropped).enhance(0.65)

                        mask = Image.new("L", (w, h), 0)
                        draw_m = ImageDraw.Draw(mask)
                        draw_m.rounded_rectangle([(0, 0), (w, h)], radius=corner_radius, fill=255)

                        out_im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
                        out_im.paste(cropped, (0, 0), mask=mask)
                        return out_im, w, h

            card_l, cw_l, ch_l = _render_card_image(left_img_path, is_speaker=(speaking_side == "left"), is_round=left_is_round)
            cur_left_x = left_box_x if not left_is_round else (left_box_x + (card_w - cw_l) // 2)

            right_valid = bool(right_img_path and os.path.exists(right_img_path))
            card_r, cw_r, ch_r = (None, 0, 0)
            cur_right_x = right_box_x
            if right_valid:
                card_r, cw_r, ch_r = _render_card_image(right_img_path, is_speaker=(speaking_side == "right"), is_round=right_is_round)
                cur_right_x = right_box_x if not right_is_round else (right_box_x + (card_w - cw_r) // 2)

            def _draw_card_glow(cvs, x, y, w, h, is_speaker, is_round, color_rgb):
                if is_speaker:
                    glow_pad = 40
                    g_cvs = Image.new("RGBA", (w + glow_pad * 2, h + glow_pad * 2), (0, 0, 0, 0))
                    d_g = ImageDraw.Draw(g_cvs)
                    for i in range(16, 0, -2):
                        alpha = int(35 * (1.0 - i / 18.0))
                        bbox = [(glow_pad - i, glow_pad - i), (glow_pad + w + i, glow_pad + h + i)]
                        if is_round:
                            d_g.ellipse(bbox, outline=(*color_rgb, alpha), width=4)
                        else:
                            d_g.rounded_rectangle(bbox, radius=corner_radius + i, outline=(*color_rgb, alpha), width=4)
                    g_blur = g_cvs.filter(ImageFilter.GaussianBlur(radius=8))
                    cvs.paste(g_blur, (x - glow_pad, y - glow_pad), mask=g_blur)

            def _draw_card_border(cvs, x, y, w, h, is_speaker, is_round, color_rgb):
                d = ImageDraw.Draw(cvs)
                bbox = [(x, y), (x + w, y + h)]
                if is_speaker:
                    # Konuşan kart: Kalın 8px parlak neon çerçeve (Yeşil veya Kırmızı)
                    if is_round:
                        d.ellipse(bbox, outline=(*color_rgb, 255), width=8)
                    else:
                        d.rounded_rectangle(bbox, radius=corner_radius, outline=(*color_rgb, 255), width=8)
                else:
                    # Dinleyen kart: Koyu zarif çerçeve
                    if is_round:
                        d.ellipse(bbox, outline=(71, 85, 105, 230), width=3)
                    else:
                        d.rounded_rectangle(bbox, radius=corner_radius, outline=(71, 85, 105, 230), width=3)

            # 1. Glow Parlaması (Konuşan kart arkasında neon hale)
            _draw_card_glow(canvas, cur_left_x, left_y, cw_l, ch_l, is_speaker=(speaking_side == "left"), is_round=left_is_round, color_rgb=border_color_rgb)
            if card_r:
                _draw_card_glow(canvas, cur_right_x, right_y, cw_r, ch_r, is_speaker=(speaking_side == "right"), is_round=right_is_round, color_rgb=border_color_rgb)

            # 2. Kart Görsellerini Yapıştır
            canvas.paste(card_l, (cur_left_x, left_y), mask=card_l)
            if card_r:
                canvas.paste(card_r, (cur_right_x, right_y), mask=card_r)

            # 3. Neon Çerçeve (Kartın tam üzerine çizilir)
            _draw_card_border(canvas, cur_left_x, left_y, cw_l, ch_l, is_speaker=(speaking_side == "left"), is_round=left_is_round, color_rgb=border_color_rgb)
            if card_r:
                _draw_card_border(canvas, cur_right_x, right_y, cw_r, ch_r, is_speaker=(speaking_side == "right"), is_round=right_is_round, color_rgb=border_color_rgb)

            final_rgb = canvas.convert("RGB")
            os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
            final_rgb.save(out_path, "JPEG", quality=95)
            return out_path
        except Exception as e:
            print(f"⚠️ Versus scene hazirlanamadi ({left_img_path}): {e}")
            return left_img_path

    @classmethod
    def _prepare_half_screen_splash(cls, img_path: str, side: str = "left", out_dir: str = None) -> str:
        """Eski çağrılar için geriye dönük uyumluluk sarmalayıcısı."""
        return cls._prepare_split_scene_2560x1440(img_path, None, out_dir)

    @classmethod
    def _prepare_full_screen_splash(cls, img_path: str, out_dir: str = None) -> str:
        """Genel replikler için 2560x1440 tam ekran + alt blur şeritli görsel üretir."""
        return cls._prepare_split_scene_2560x1440(img_path, None, out_dir)

    @staticmethod
    def _hex_to_fcpxml_rgba(hex_str: str, default_rgba: str = "1 0.88 0.28 1") -> str:
        if not hex_str or not isinstance(hex_str, str):
            return default_rgba
        h = hex_str.lstrip('#')
        if len(h) == 6:
            try:
                r = round(int(h[0:2], 16) / 255.0, 4)
                g = round(int(h[2:4], 16) / 255.0, 4)
                b = round(int(h[4:6], 16) / 255.0, 4)
                return f"{r} {g} {b} 1"
            except Exception:
                pass
        return default_rgba

    @classmethod
    def generate_champion_voices_fcpxml(cls, rich_entries, output_path, gap_seconds=0.2, timeline_name="LoL_Karakter_Replikleri", fps=60, include_splash=True, include_action_label=True, font_family="Montserrat", font_face="Bold", font_size_spk=34, font_size_quote=40, stroke_width=1, spk_color_hex="#40e0f2", quote_color_hex="#ffe047", include_text=True):
        """
        KULLANICI İSTEĞİ - Kusursuz %50/%50 Bölünmüş Sahne, Kesintisiz Görsel Gruplama ve Gerçek Blur Şeridi:
        1. Sadece SESLER arasında Gap (boşluk) bulunur; soldaki Azir ve sağdaki hedef karakter görselleri
           Gap sırasında KESİLMEZ (ekran kararmaz).
        2. Arka arkaya aynı hedef karaktere/karta söylenen repliklerde sağdaki hedef görseli ve üst başlığı
           bölük pörçük olmaz; tüm ardışık replikler + aralarındaki ses boşlukları boyunca TEK PARÇA uzanır.
        3. Sol karakter (Azir) ardışık tüm replikler boyunca kesintisiz tek blok olarak kalır.
        4. Görseller tam 1280x1440 yarı-ekran olarak karakterin YÜZÜNE göre kırpılıp ölçeklendiği için
           2:1 (LoR), 1:1 (Büyü) veya 16:9 (LoL 4K) fark etmeksizin ekranı tam ortadan jilet gibi ikiye böler.
        5. Alt kısımda zarif küçültülmüş Gaussian Blur arka plan şeridi ve kompakt Font boyutları yer alır.
        """
        from pathlib import Path

        timeline_w = 2560
        timeline_h = 1440
        scale_factor = timeline_h / 100.0  # 14.4

        # %50 Sol merkez X = -640px (-44.444444), %50 Sağ merkez X = +640px (+44.444444)
        left_half_x = round(-640.0 / scale_factor, 6)
        right_half_x = round(640.0 / scale_factor, 6)
        bottom_text_x = 0.0
        # Küçültülmüş zarif blur cam kutusunun tam dikey merkezi:
        # include_text açıkken Y: 1160..1360 (merkez 1260px -> -540px -> -37.5)
        # include_text kapalıyken Y: 1220..1340 (merkez 1280px -> -560px -> -38.888889)
        bottom_center_px = -540.0 if include_text else -560.0
        bottom_text_y = round(bottom_center_px / scale_factor, 6)
        top_names_y = round(580.0 / scale_factor, 6)

        # Kullanıcı İsteği: Alt kısımdaki eylem ve replik yazısını küçültüp zarif hale getir ve atıflarda taşmayı önle
        raw_spk_sz = int(font_size_spk or 32)
        raw_quo_sz = int(font_size_quote or 38)
        eff_spk_size = min(31, max(22, int(round(raw_spk_sz * 0.70)))) if raw_spk_sz > 32 else max(22, raw_spk_sz)
        eff_quo_size = min(37, max(26, int(round(raw_quo_sz * 0.74)))) if raw_quo_sz > 38 else max(26, raw_quo_sz)
        eff_act_only_size = min(31, max(24, eff_spk_size))

        spk_rgba = cls._hex_to_fcpxml_rgba(spk_color_hex, "0.25 0.88 0.95 1")
        quo_rgba = cls._hex_to_fcpxml_rgba(quote_color_hex, "1 0.88 0.28 1")
        clean_face = font_face or "Bold"
        bold_attr = '1' if ('bold' in clean_face.lower() or 'black' in clean_face.lower()) else '0'
        spk_face = f"{clean_face} Italic" if "italic" not in clean_face.lower() else clean_face

        resources = [
            f'<format id="r1" name="FFVideoFormat2160p{fps}" frameDuration="1/{fps}s" width="{timeline_w}" height="{timeline_h}" colorSpace="1-1-1 (Rec. 709)"/>',
            '<effect id="r_title" name="Basic Title" uid=".../Titles.localized/Bumper:Opener.localized/Basic Title.localized/Basic Title.moti"/>'
        ]

        registered_images = {}
        parsed_clips = []
        gap_frames = int(round(gap_seconds * fps)) if gap_seconds > 0 else 0

        def _reg_img(img_path):
            if not img_path or not os.path.exists(img_path):
                return None, ""
            if img_path not in registered_images:
                iid = f"img_{len(registered_images) + 1}"
                registered_images[img_path] = iid
                stem = Path(img_path).stem
                uri = Path(img_path).resolve().as_uri()
                resources.append(
                    f'<asset id="{iid}" name="{escape(stem)}" src="{uri}" start="0s" duration="0s" hasVideo="1" format="r1"/>'
                )
                return iid, stem
            return registered_images[img_path], Path(img_path).stem

        for idx, item in enumerate(rich_entries, start=1):
            abs_path = os.path.abspath(item['audio_path'])
            duration_sec, samplerate, channels, _ = cls.get_audio_info_fast(abs_path)
            dur_frames = max(1, int(round(duration_sec * fps)))
            dur_str = f"{dur_frames}/{fps}s"

            aud_id = f"aud_{idx}"
            aud_uri = Path(abs_path).resolve().as_uri()
            resources.append(
                f'<asset id="{aud_id}" name="{escape(Path(abs_path).stem)}" src="{aud_uri}" start="0s" duration="{dur_str}" hasAudio="1" audioSources="1" audioChannels="{channels}" audioRate="{samplerate}"/>'
            )

            raw_main_splash = item.get('splash_path') if include_splash else None
            target_champ = item.get('target', '') or ''
            raw_target_splash = item.get('target_splash_path') if (include_splash and target_champ) else None
            has_target = bool(target_champ and raw_target_splash and os.path.exists(raw_target_splash))

            compact_flag = not bool(include_text)
            if has_target:
                scene_splash = cls._prepare_split_scene_2560x1440(raw_main_splash, raw_target_splash, compact_bar=compact_flag)
            else:
                scene_splash = cls._prepare_split_scene_2560x1440(raw_main_splash, None, compact_bar=compact_flag) if raw_main_splash else None

            scene_img_id, scene_img_stem = _reg_img(scene_splash) if scene_splash else (None, "")

            raw_ev_str = str(item.get('event') or item.get('raw_event') or '')
            action_tr = item.get('action_name') or item.get('action_type') or ''
            if not action_tr or 'Item 1' in action_tr or 'Item 2' in action_tr or 'Item ' in action_tr or action_tr == 'Eşya Alınca':
                try:
                    import event_categorizer
                    item_tr = event_categorizer.resolve_item_event_turkish(raw_ev_str)
                    if item_tr:
                        action_tr = item_tr
                except Exception:
                    pass
            if not action_tr:
                action_tr = cls.format_event_action_template(raw_ev_str, '')

            quote_raw = (item.get('transcript') or '').strip().strip(' "\'“”«»')
            wrapped_quote = cls.balance_wrap(quote_raw, max_chars=46) if quote_raw else ""

            parsed_clips.append({
                "idx": idx,
                "abs_path": abs_path,
                "dur_frames": dur_frames,
                "aud_id": aud_id,
                "scene_img_id": scene_img_id,
                "scene_img_stem": scene_img_stem,
                "has_target": has_target,
                "target_champ": target_champ,
                "target_skin_name": item.get('target_skin_name', ''),
                "action_tr": action_tr,
                "wrapped_quote": wrapped_quote,
                "speaker": item.get('speaker', '')
            })

        # Her klibin timeline üzerindeki kesin başlangıç karesini (start_frame) ve ses süresini belirle.
        # Gap (boşluk) SADECE sesler arasına girer; görseller gap süresini de kapsayarak kesintisiz uzanır!
        current_frame = 0
        for i, c in enumerate(parsed_clips):
            c['start_frame'] = current_frame
            c['audio_dur_frames'] = c['dur_frames']
            # Son klip hariç her klibin görsel süresi ses + gap kadardır (böylece hiç siyah ekran / gap kesintisi olmaz)
            extra_gap = gap_frames if i < len(parsed_clips) - 1 else 0
            c['visual_dur_frames'] = c['dur_frames'] + extra_gap
            current_frame += c['visual_dur_frames']

        total_timeline_frames = max(1, current_frame)

        # Ardışık aynı sahne görseline (scene_img_id) sahip klipleri TEK BİR ANA SPINE VİDEOSUNDA birleştir!
        # Böylece aynı konuşmacı ve aynı hedefe söylenen tüm replikler boyunca görsel asla kesilmez/bölünmez.
        spine_blocks = []
        for c in parsed_clips:
            if not spine_blocks:
                spine_blocks.append([c])
            else:
                prev = spine_blocks[-1][-1]
                if prev['scene_img_id'] == c['scene_img_id'] and prev['has_target'] == c['has_target'] and prev['target_champ'] == c['target_champ']:
                    spine_blocks[-1].append(c)
                else:
                    spine_blocks.append([c])

        spine_items = []
        block_counter = 0

        for block in spine_blocks:
            block_counter += 1
            b_start_frame = block[0]['start_frame']
            b_dur_frames = sum(x['visual_dur_frames'] for x in block)
            b_offset_str = f"{b_start_frame}/{fps}s"
            b_dur_str = f"{b_dur_frames}/{fps}s"

            first_c = block[0]
            spk_up = cls.turkish_upper(first_c['speaker'] or 'ŞAMPİYON')
            tgt_up = cls.turkish_upper(first_c['target_champ'] or '')

            inner_elements_xml = []

            # 1) Karakter Başlıkları:
            #    - Üst Sol Konuşan Başlığı (AZİR) tüm blok boyunca kesintisiz tek parça durur (lane="3")
            #    - Üst Sağ Hedef Başlığı (İRELİA / LİLLİA) tüm blok boyunca kesintisiz tek parça durur (lane="4")
            #    Kullanıcı İsteği: Replik metinleri kapalı olsa dahi karakter isim başlıkları daima korunur!
            if first_c['has_target']:
                style_hdr_spk_block = f"ts_hdr_spk_b{block_counter}"
                inner_elements_xml.append(f"""
                  <title name="{escape(spk_up)}" lane="3" ref="r_title" offset="0s" duration="{b_dur_str}" start="0s">
                    <adjust-transform position="{left_half_x} {top_names_y}" scale="0.82 0.82"/>
                    <text>
                      <text-style ref="{style_hdr_spk_block}">{escape(spk_up)}</text-style>
                    </text>
                    <text-style-def id="{style_hdr_spk_block}">
                      <text-style font="{escape(font_family)}" fontSize="42" fontFace="{escape(clean_face)}" bold="{bold_attr}" fontColor="{spk_rgba}" strokeColor="0 0 0 1" strokeWidth="{stroke_width}" alignment="center" shadowColor="0 0 0 0.95" shadowOffset="2 -2"/>
                    </text-style-def>
                  </title>""")

                if tgt_up:
                    style_hdr_tgt_id = f"ts_hdr_tgt_b{block_counter}"
                    inner_elements_xml.append(f"""
                  <title name="{escape(tgt_up)}" lane="4" ref="r_title" offset="0s" duration="{b_dur_str}" start="0s">
                    <adjust-transform position="{right_half_x} {top_names_y}" scale="0.82 0.82"/>
                    <text>
                      <text-style ref="{style_hdr_tgt_id}">{escape(tgt_up)}</text-style>
                    </text>
                    <text-style-def id="{style_hdr_tgt_id}">
                      <text-style font="{escape(font_family)}" fontSize="42" fontFace="{escape(clean_face)}" bold="{bold_attr}" fontColor="1 0.65 0.25 1" strokeColor="0 0 0 1" strokeWidth="{stroke_width}" alignment="center" shadowColor="0 0 0 0.95" shadowOffset="2 -2"/>
                    </text-style-def>
                  </title>""")

            # 2) Her bir replik klibinin kendi Sesi (lane="-1") ve kendi Alt Replik Metni (lane="2"):
            #    Sadece ses süresi (audio_dur_frames) kadar sürer, böylece iki replik arasında tam istenen gap boşluğu oluşur!
            for c in block:
                c_idx = c['idx']
                c_rel_start = c['start_frame'] - b_start_frame
                c_rel_offset = f"{c_rel_start}/{fps}s"
                c_aud_dur_str = f"{c['audio_dur_frames']}/{fps}s"

                # Kullanıcı İsteği: include_text kapalı olsa bile replik metni yerine sadece karakter başlığı / eylem etiketi eklenir veya replik gizlenir
                if include_text:
                    style_act_id = f"ts_act_{c_idx}"
                    style_quo_id = f"ts_quo_{c_idx}"
                    c_tgt_up = cls.turkish_upper(c['target_champ'] or '')
                    act_escaped = escape(c['action_tr'])
                    header_prefix = f"{escape(spk_up)} ➔ {escape(c_tgt_up)} • " if c_tgt_up else f"{escape(spk_up)} • "

                    if c['wrapped_quote']:
                        quo_escaped = escape(c['wrapped_quote']).replace('\n', '&#13;&#10;')
                        text_inner_xml = f"""<text>
                          <text-style ref="{style_act_id}">[ {header_prefix}{act_escaped} ]</text-style>
                          <text-style ref="{style_quo_id}">&#13;&#10;“{quo_escaped}”</text-style>
                        </text>
                        <text-style-def id="{style_act_id}">
                          <text-style font="{escape(font_family)}" fontSize="{eff_spk_size}" fontFace="{escape(spk_face)}" bold="{bold_attr}" italic="1" fontColor="{spk_rgba}" strokeColor="0 0 0 1" strokeWidth="{stroke_width}" alignment="center" shadowColor="0 0 0 0.95" shadowOffset="2 -2"/>
                        </text-style-def>
                        <text-style-def id="{style_quo_id}">
                          <text-style font="{escape(font_family)}" fontSize="{eff_quo_size}" fontFace="{escape(clean_face)}" bold="{bold_attr}" fontColor="{quo_rgba}" strokeColor="0 0 0 1" strokeWidth="{stroke_width}" alignment="center" shadowColor="0 0 0 0.95" shadowOffset="3 -3"/>
                        </text-style-def>"""
                    else:
                        text_inner_xml = f"""<text>
                          <text-style ref="{style_act_id}">[ {header_prefix}{act_escaped} ]</text-style>
                        </text>
                        <text-style-def id="{style_act_id}">
                          <text-style font="{escape(font_family)}" fontSize="{eff_act_only_size}" fontFace="{escape(spk_face)}" bold="{bold_attr}" italic="1" fontColor="{quo_rgba}" strokeColor="0 0 0 1" strokeWidth="{stroke_width}" alignment="center" shadowColor="0 0 0 0.95" shadowOffset="2 -2"/>
                        </text-style-def>"""

                    inner_elements_xml.append(f"""
                  <title name="{act_escaped}" lane="2" ref="r_title" offset="{c_rel_offset}" duration="{c_aud_dur_str}" start="0s">
                    <adjust-transform position="{bottom_text_x} {bottom_text_y}" scale="1 1"/>
                    {text_inner_xml}
                  </title>""")
                elif include_action_label and c['action_tr']:
                    # Replik kapalı ama eylem başlığı veya karakter bilgisi aktif (Uzun atıflarda bile kutudan taşmayan dinamik boyut)
                    style_act_id = f"ts_act_{c_idx}"
                    c_tgt_up = cls.turkish_upper(c['target_champ'] or '')
                    act_escaped = escape(c['action_tr'])
                    header_prefix = f"{escape(spk_up)} ➔ {escape(c_tgt_up)} • " if c_tgt_up else f"{escape(spk_up)} • "
                    full_lbl_len = len(f"[ {spk_up} ➔ {c_tgt_up} • {c['action_tr']} ]") if c_tgt_up else len(f"[ {spk_up} • {c['action_tr']} ]")
                    dyn_act_sz = max(23, min(eff_act_only_size, int(1520 / max(1, full_lbl_len)))) if full_lbl_len > 48 else eff_act_only_size
                    text_inner_xml = f"""<text>
                      <text-style ref="{style_act_id}">[ {header_prefix}{act_escaped} ]</text-style>
                    </text>
                    <text-style-def id="{style_act_id}">
                      <text-style font="{escape(font_family)}" fontSize="{dyn_act_sz}" fontFace="{escape(spk_face)}" bold="{bold_attr}" italic="1" fontColor="{quo_rgba}" strokeColor="0 0 0 1" strokeWidth="{stroke_width}" alignment="center" shadowColor="0 0 0 0.95" shadowOffset="2 -2"/>
                    </text-style-def>"""
                    inner_elements_xml.append(f"""
                  <title name="{act_escaped}" lane="2" ref="r_title" offset="{c_rel_offset}" duration="{c_aud_dur_str}" start="0s">
                    <adjust-transform position="{bottom_text_x} {bottom_text_y}" scale="1 1"/>
                    {text_inner_xml}
                  </title>""")

                inner_elements_xml.append(f"""
                  <asset-clip name="{escape(Path(c['abs_path']).stem)}" lane="-1" ref="{c['aud_id']}" offset="{c_rel_offset}" duration="{c_aud_dur_str}" start="0s" role="dialogue"/>""")

            # Ana Spine Video (Yekpare 2560x1440 Split Sahne veya Tam Ekran Sahne)
            if first_c['scene_img_id']:
                spine_item = f"""
                <video name="{escape(first_c['scene_img_stem'])}" ref="{first_c['scene_img_id']}" offset="{b_offset_str}" duration="{b_dur_str}" start="0s">
                  <adjust-transform position="0 0" scale="1 1"/>
                  {''.join(inner_elements_xml)}
                </video>"""
            else:
                spine_item = f"""
                <gap name="VisualBlock" offset="{b_offset_str}" duration="{b_dur_str}" start="0s">
                  {''.join(inner_elements_xml)}
                </gap>"""

            spine_items.append(spine_item)

        total_dur_str = f"{total_timeline_frames}/{fps}s"
        fcpxml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE fcpxml>
<fcpxml version="1.8">
  <resources>
    {''.join(resources)}
  </resources>
  <library>
    <event name="LoL Karakter Replikleri">
      <project name="{escape(timeline_name)}">
        <sequence format="r1" duration="{total_dur_str}">
          <spine>
            {''.join(spine_items)}
          </spine>
        </sequence>
      </project>
    </event>
  </library>
</fcpxml>"""

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(fcpxml_content)
        return output_path

    @classmethod
    def generate_versus_dialogue_fcpxml(cls, rich_entries, output_path, gap_seconds=0.2, timeline_name="LoL_Birebir_Diyaloglar", fps=60, include_splash=True, include_action_label=True, font_family="Montserrat", font_face="Bold", font_size_spk=48, font_size_quote=42, stroke_width=1, spk_color_hex="#40e0f2", quote_color_hex="#ffe047", include_text=True):
        """
        KULLANICI İSTEĞİ - Birebir Diyaloglar Özel DaVinci FCPXML v1.8 Layout'u:
        - 2560x1440 çözünürlükte yekpare sinematik sahne (_prepare_versus_scene_2560x1440):
          * Konuşan kart etrafında parlak neon border (6px + soft glow) ve hafif yüksekte (Yükseklik farkı: 70px)
          * Dinleyen kart sönük border, %65 parlaklık ve altında soluk "(X sırasını bekliyor...)" metni
          * Konuşan değiştikçe border parlaması ve yükseklik anında diğerine geçer!
        - DaVinci Resolve CRASH-FREE & Kararlı Timeline Mimarisi:
          * Still image asset duration="0s" (asla 86400s veya video stream atanmaz, anında Resim tanınır).
          * Integer rational timecode (fps tam sayı normalize edilir: paydada asla ondalıklı .0 yer alamaz).
          * Kesintisiz video akışı: Her sahne klibi ses + gap kadar uzanır, siyah boşluk (gap) ekran kararması olmaz.
          * Altyazı ve Eylem başlıkları ses süresi boyunca ekranda kalır, konuşma bittiğinde kaybolur.
        """
        from pathlib import Path

        # 1. FPS ve Gap Güvenli Tam Sayı Normalizasyonu
        fps = int(round(float(fps))) if fps else 60
        gap_sec = float(gap_seconds) if gap_seconds is not None else 0.2
        gap_frames = int(round(gap_sec * fps)) if gap_sec > 0 else 0

        timeline_w = 2560
        timeline_h = 1440
        scale_factor = timeline_h / 100.0  # 14.4

        left_sub_x = round(-600.0 / scale_factor, 6)   # -41.666667
        right_sub_x = round(600.0 / scale_factor, 6)   # +41.666667
        sub_y = round(-350.0 / scale_factor, 6)         # -24.305556
        top_banner_y = round(560.0 / scale_factor, 6)   # +38.888889

        clean_face = font_face or "Bold"
        bold_attr = '1' if ('bold' in clean_face.lower() or 'black' in clean_face.lower() or 'heavy' in clean_face.lower()) else '0'
        spk_rgba = cls._hex_to_fcpxml_rgba(spk_color_hex, "0.25 0.88 0.95 1")
        quo_rgba = cls._hex_to_fcpxml_rgba(quote_color_hex, "1 0.88 0.28 1")

        resources = [
            f'<format id="r1" name="FFVideoFormat2160p{fps}" frameDuration="1/{fps}s" width="{timeline_w}" height="{timeline_h}" colorSpace="1-1-1 (Rec. 709)"/>',
            '<effect id="r_title" name="Basic Title" uid=".../Titles.localized/Bumper:Opener.localized/Basic Title.localized/Basic Title.moti"/>'
        ]

        registered_scenes = {}
        skins_db = cls.get_skins_database()

        # Sol şampiyonu sabitle (Projenin ana sol şampiyonu - örn: Azir)
        primary_left_champ = "Azir"
        if rich_entries:
            cand = rich_entries[0].get('left_champ') or ""
            if not cand:
                from collections import Counter
                all_c = [e.get('speaker') for e in rich_entries if e.get('speaker')]
                if all_c:
                    cand = Counter(all_c).most_common(1)[0][0]
            if cand:
                primary_left_champ = cand

        export_dir = os.path.dirname(os.path.abspath(output_path))
        scenes_dir = os.path.join(export_dir, "Gorseller")
        os.makedirs(scenes_dir, exist_ok=True)

        parsed_turns = []

        for idx, item in enumerate(rich_entries, start=1):
            abs_path = os.path.abspath(item['audio_path'])
            duration_sec, samplerate, channels, _ = cls.get_audio_info_fast(abs_path)
            aud_dur_frames = max(1, int(round(duration_sec * fps)))
            aud_dur_str = f"{aud_dur_frames}/{fps}s"

            aud_id = f"aud_{idx}"
            aud_uri = Path(abs_path).resolve().as_uri()
            resources.append(
                f'<asset id="{aud_id}" name="{escape(Path(abs_path).stem)}" src="{aud_uri}" start="0s" duration="{aud_dur_str}" hasAudio="1" audioSources="1" audioChannels="{channels}" audioRate="{samplerate}"/>'
            )

            spk_name = item.get('speaker', '')
            spk_upper = cls.turkish_upper(spk_name)
            side = item.get('dialogue_side', '')
            if side not in ('left', 'right'):
                side = 'left' if spk_name.lower() == primary_left_champ.lower() else 'right'

            # Madde 1: Deterministik ve Hatasız Partner Tespiti (Jarvan/Irelia, Jax/Nasus onarımı)
            resolved_p = cls._resolve_item_partner(item, primary_champ=primary_left_champ)
            if not resolved_p:
                if idx < len(rich_entries):
                    nxt_p = cls._resolve_item_partner(rich_entries[idx], primary_champ=primary_left_champ)
                    if nxt_p and nxt_p.lower() != primary_left_champ.lower():
                        resolved_p = nxt_p
                    elif (rich_entries[idx].get('speaker') or '').lower() != primary_left_champ.lower():
                        resolved_p = rich_entries[idx].get('speaker')
                if not resolved_p and idx > 1:
                    prv_p = cls._resolve_item_partner(rich_entries[idx - 2], primary_champ=primary_left_champ)
                    if prv_p and prv_p.lower() != primary_left_champ.lower():
                        resolved_p = prv_p
                    elif (rich_entries[idx - 2].get('speaker') or '').lower() != primary_left_champ.lower():
                        resolved_p = rich_entries[idx - 2].get('speaker')

            right_label = resolved_p or item.get('right_champ') or item.get('target') or 'Hedef'
            if right_label.lower() in ("jarvaniv", "jarvan_iv"):
                right_label = "Jarvan IV"

            spk_splash = item.get('splash_path')
            prt_splash = item.get('target_splash_path')

            # Sol ve Sağ Kart Sabitliği Kuralı:
            # - Sol kart HER ZAMAN ana şampiyon (primary_left_champ / Azir)
            # - Sağ kart HER ZAMAN karşı/hedef şampiyon (Jarvan IV, Jax, Lillia, Pyke vb.)
            # - side değişkeni: Konuşan taraf (soldaki Azir konuşuyorsa 'left', sağdaki konuşuyorsa 'right')
            left_label = primary_left_champ
            if side == 'left':
                left_splash_path = spk_splash
                right_splash_path = prt_splash
                if right_label and right_label != 'Hedef':
                    safe_r_norm = re.sub(r'[^a-zA-Z0-9]', '', right_label).lower()
                    cur_base = re.sub(r'[^a-zA-Z0-9]', '', os.path.basename(right_splash_path or '')).lower()
                    if not right_splash_path or (safe_r_norm not in cur_base and cur_base not in safe_r_norm):
                        right_splash_path = cls._resolve_and_bundle_splash(
                            skins_db, right_label,
                            splash_dir=scenes_dir, bundle_folder=True,
                            is_lor=True
                        ) or right_splash_path
            else:
                side = 'right'
                left_splash_path = prt_splash
                right_splash_path = spk_splash
                safe_l_norm = re.sub(r'[^a-zA-Z0-9]', '', primary_left_champ).lower()
                cur_l_base = re.sub(r'[^a-zA-Z0-9]', '', os.path.basename(left_splash_path or '')).lower()
                if not left_splash_path or (safe_l_norm not in cur_l_base and cur_l_base not in safe_l_norm):
                    left_splash_path = cls._resolve_and_bundle_splash(
                        skins_db, primary_left_champ,
                        splash_dir=scenes_dir, bundle_folder=True,
                        is_lor=True
                    ) or left_splash_path

            # Madde 2: Sade ve Anlaşılır Türkçe Başlık
            action_tr = cls._clean_action_label(item.get('action_name') or item.get('action_type') or item.get('event', ''))
            raw_act_info = f"{action_tr} {item.get('event', '')} {item.get('action_name', '')} {item.get('action_type', '')}".lower()
            is_ally = any(k in raw_act_info for k in ['dost', 'ally', 'arkadas', 'yardim', 'savunma'])

            # 2560x1440 versus sahne görseli (Madde 4: Yeşil/Kırmızı Border + Madde 7: Yuvarlak Kart Desteği)
            scene_path = None
            if include_splash and left_splash_path:
                scene_path = cls._prepare_versus_scene_2560x1440(
                    left_img_path=left_splash_path,
                    right_img_path=right_splash_path,
                    speaking_side=side,
                    left_name=cls.turkish_upper(left_label),
                    right_name=cls.turkish_upper(right_label),
                    is_ally=is_ally,
                    out_dir=scenes_dir
                )

            scene_img_id = None
            scene_img_stem = ""
            if scene_path and os.path.exists(scene_path):
                if scene_path not in registered_scenes:
                    sid = f"scn_{len(registered_scenes) + 1}"
                    registered_scenes[scene_path] = sid
                    stem = Path(scene_path).stem
                    s_uri = Path(scene_path).resolve().as_uri()
                    # CRASH FIX: duration="0s" DaVinci still image standardı! Asla çökmez!
                    resources.append(
                        f'<asset id="{sid}" name="{escape(stem)}" src="{s_uri}" start="0s" duration="0s" hasVideo="1" format="r1"/>'
                    )
                scene_img_id = registered_scenes[scene_path]
                scene_img_stem = Path(scene_path).stem

            quote_raw = (item.get('transcript') or '').strip().strip(' "\'“”«»')
            if not quote_raw:
                quote_raw = f"({item.get('action_name') or item.get('action_type') or 'Replik'})"
            wrapped_quote = cls.balance_wrap(quote_raw, max_chars=34)

            parsed_turns.append({
                "idx": idx,
                "abs_path": abs_path,
                "aud_id": aud_id,
                "aud_dur_frames": aud_dur_frames,
                "spk_name": spk_name,
                "spk_upper": spk_upper,
                "side": side,
                "left_label": left_label,
                "right_label": right_label,
                "target_name": right_label,
                "scene_img_id": scene_img_id,
                "scene_img_stem": scene_img_stem,
                "wrapped_quote": wrapped_quote,
                "action_tr": action_tr,
                "is_ally": is_ally
            })

        # Timeline kare yerleşimi:
        # Her turn görseli ses süresi + gap kadar sürer (ekran kararmaz, akıcı sinematik geçiş)
        # Ses ve Altyazı turn başında başlar ve kendi ses süresi kadar kalır.
        current_frame = 0
        spine_items = []

        for i, turn in enumerate(parsed_turns):
            idx = turn['idx']
            turn_start_frame = current_frame
            extra_gap = gap_frames if i < len(parsed_turns) - 1 else 0
            turn_total_frames = turn['aud_dur_frames'] + extra_gap

            turn_offset_str = f"{turn_start_frame}/{fps}s"
            turn_dur_str = f"{turn_total_frames}/{fps}s"
            aud_dur_str = f"{turn['aud_dur_frames']}/{fps}s"

            sub_x = left_sub_x if turn['side'] == 'left' else right_sub_x

            # Madde 2: Dost karşılaşmasında YEŞİL (#10b981), Düşmanda KIRMIZI (#f43f5e)
            ally_green_rgba = "0.06 0.73 0.50 1"   # Canlı Neon Yeşil #10b981
            enemy_red_rgba  = "0.96 0.25 0.37 1"   # Canlı Gül Kırmızısı #f43f5e
            partner_color_rgba = ally_green_rgba if turn.get('is_ally') else enemy_red_rgba

            if turn['side'] == 'left':
                cur_spk_color = spk_rgba
                cur_oth_color = partner_color_rgba
            else:
                cur_spk_color = partner_color_rgba
                cur_oth_color = spk_rgba

            # Madde 6: Karşıda Dinleyen / Yanıt Vermeyen Tarafın Adı (Karşı Kartın Altında Şampiyon/Kart Adı)
            other_side = 'right' if turn['side'] == 'left' else 'left'
            other_sub_x = right_sub_x if turn['side'] == 'left' else left_sub_x
            other_name = turn['right_label'] if turn['side'] == 'left' else turn['left_label']
            if not other_name or other_name.lower() in ('diğer', 'diger', 'solo', 'none', 'hedef'):
                other_name = turn.get('target_name', '')
            other_upper = cls.turkish_upper(other_name) if other_name else ""

            style_spk_id = f"ts_vspk_{idx}"
            style_quo_id = f"ts_vquo_{idx}"
            style_act_id = f"ts_vact_{idx}"
            style_oth_id = f"ts_voth_{idx}"

            sub_xml = ""
            other_xml = ""
            banner_xml = ""

            # 1. Madde Çözümü: Altyazı ve Karakter Başlığı
            # Kullanıcı İsteği: include_text kapalı olsa dahi konuşan karakterin ismi daima gelir!
            if include_text:
                formatted_quote = escape(turn['wrapped_quote']).replace('\n', '&#13;&#10;')
                sub_xml = f"""
                  <title name="{escape(turn['spk_upper'])}" lane="1" ref="r_title" offset="0s" duration="{aud_dur_str}" start="0s">
                    <adjust-transform position="{sub_x} {sub_y}" scale="1 1"/>
                    <text>
                      <text-style ref="{style_spk_id}">{escape(turn['spk_upper'])}</text-style>
                      <text-style ref="{style_quo_id}">&#13;&#10;{formatted_quote}</text-style>
                    </text>
                    <text-style-def id="{style_spk_id}">
                      <text-style font="{escape(font_family)}" fontSize="{font_size_spk}" fontFace="{escape(clean_face)}" bold="{bold_attr}" fontColor="{cur_spk_color}" strokeColor="0 0 0 1" strokeWidth="{stroke_width}" alignment="center" shadowColor="0 0 0 0.95" shadowOffset="3 -3"/>
                    </text-style-def>
                    <text-style-def id="{style_quo_id}">
                      <text-style font="{escape(font_family)}" fontSize="{font_size_quote}" fontFace="{escape(clean_face)}" bold="{bold_attr}" fontColor="{quo_rgba}" strokeColor="0 0 0 1" strokeWidth="{stroke_width}" alignment="center" shadowColor="0 0 0 0.95" shadowOffset="3 -3"/>
                    </text-style-def>
                    <param name="Stroke" key="stroke" value="1"/>
                    <param name="Stroke Size" key="stroke_size" value="{stroke_width}"/>
                    <param name="Stroke Color" key="stroke_color" value="0 0 0 1"/>
                  </title>"""
            else:
                # Sadece Karakter Adı
                sub_xml = f"""
                  <title name="{escape(turn['spk_upper'])}" lane="1" ref="r_title" offset="0s" duration="{aud_dur_str}" start="0s">
                    <adjust-transform position="{sub_x} {sub_y}" scale="1 1"/>
                    <text>
                      <text-style ref="{style_spk_id}">{escape(turn['spk_upper'])}</text-style>
                    </text>
                    <text-style-def id="{style_spk_id}">
                      <text-style font="{escape(font_family)}" fontSize="{font_size_spk}" fontFace="{escape(clean_face)}" bold="{bold_attr}" fontColor="{cur_spk_color}" strokeColor="0 0 0 1" strokeWidth="{stroke_width}" alignment="center" shadowColor="0 0 0 0.95" shadowOffset="3 -3"/>
                    </text-style-def>
                    <param name="Stroke" key="stroke" value="1"/>
                    <param name="Stroke Size" key="stroke_size" value="{stroke_width}"/>
                    <param name="Stroke Color" key="stroke_color" value="0 0 0 1"/>
                  </title>"""

            # Madde 6 & Madde 2: Karşı tarafta dinleyen / tek taraflı diyalogda yanıt vermeyen kartın veya şampiyonun adı
            # Renk: Dost ise YEŞİL, Düşman ise KIRMIZI!
            if other_upper and other_upper != turn['spk_upper']:
                other_xml = f"""
                  <title name="{escape(other_upper)}" lane="3" ref="r_title" offset="0s" duration="{aud_dur_str}" start="0s">
                    <adjust-transform position="{other_sub_x} {sub_y}" scale="1 1"/>
                    <text>
                      <text-style ref="{style_oth_id}">{escape(other_upper)}</text-style>
                    </text>
                    <text-style-def id="{style_oth_id}">
                      <text-style font="{escape(font_family)}" fontSize="{font_size_spk}" fontFace="{escape(clean_face)}" bold="{bold_attr}" fontColor="{cur_oth_color}" strokeColor="0 0 0 1" strokeWidth="{stroke_width}" alignment="center" shadowColor="0 0 0 0.95" shadowOffset="3 -3"/>
                    </text-style-def>
                    <param name="Stroke" key="stroke" value="1"/>
                    <param name="Stroke Size" key="stroke_size" value="{stroke_width}"/>
                    <param name="Stroke Color" key="stroke_color" value="0 0 0 1"/>
                  </title>"""

            # Üst Ortada Sadeleştirilmiş Etkileşim Başlık Banner'ı (Madde 2)
            if include_action_label and turn['action_tr']:
                act_esc = escape(turn['action_tr'])
                banner_color = "0.20 0.88 0.55 1" if turn.get('is_ally') else "1 0.88 0.28 1"
                banner_xml = f"""
                  <title name="{act_esc}" lane="2" ref="r_title" offset="0s" duration="{aud_dur_str}" start="0s">
                    <adjust-transform position="0 {top_banner_y}" scale="0.75 0.75"/>
                    <text>
                      <text-style ref="{style_act_id}">{act_esc}</text-style>
                    </text>
                    <text-style-def id="{style_act_id}">
                      <text-style font="{escape(font_family)}" fontSize="44" fontFace="{escape(clean_face)}" bold="{bold_attr}" italic="0" fontColor="{banner_color}" strokeColor="0 0 0 1" strokeWidth="{stroke_width}" alignment="center" shadowColor="0 0 0 0.95" shadowOffset="2 -2"/>
                    </text-style-def>
                    <param name="Stroke" key="stroke" value="1"/>
                    <param name="Stroke Size" key="stroke_size" value="{stroke_width}"/>
                    <param name="Stroke Color" key="stroke_color" value="0 0 0 1"/>
                  </title>"""

            # Senkron Ses (lane="-1", offset="0s", duration="{aud_dur_str}")
            aud_xml = f"""
                  <asset-clip name="{escape(Path(turn['abs_path']).stem)}" lane="-1" ref="{turn['aud_id']}" offset="0s" duration="{aud_dur_str}" start="0s" role="dialogue"/>"""

            if turn['scene_img_id']:
                spine_item = f"""
                <video name="{escape(turn['scene_img_stem'])}" ref="{turn['scene_img_id']}" offset="{turn_offset_str}" duration="{turn_dur_str}" start="0s">
                  <adjust-transform position="0 0" scale="1 1"/>
                  {sub_xml}
                  {other_xml}
                  {banner_xml}
                  {aud_xml}
                </video>"""
            else:
                spine_item = f"""
                <gap name="Turn_{idx}_{escape(turn['spk_upper'])}" offset="{turn_offset_str}" duration="{turn_dur_str}" start="0s">
                  {sub_xml}
                  {other_xml}
                  {banner_xml}
                  {aud_xml}
                </gap>"""

            spine_items.append(spine_item)
            current_frame += turn_total_frames

        total_dur_str = f"{max(1, current_frame)}/{fps}s"
        fcpxml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE fcpxml>
<fcpxml version="1.8">
  <resources>
    {''.join(resources)}
  </resources>
  <library>
    <event name="LoL Birebir Diyaloglar">
      <project name="{escape(timeline_name)}">
        <sequence format="r1" duration="{total_dur_str}">
          <spine>
            {''.join(spine_items)}
          </spine>
        </sequence>
      </project>
    </event>
  </library>
</fcpxml>"""

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(fcpxml_content)
        return output_path

    @classmethod
    def export_matrix_items(cls, items, output_dir=None, timeline_name="LoL_Secilen_Atiflar", gap_seconds=0.2, fps=60, include_splash=True, include_action_label=True, action_pos_x=2090, action_pos_y=890, action_zoom=0.64, bundle_folder=True, layout_mode="matrix_default", font_family="Montserrat", font_face="Bold", font_size_spk=46, font_size_quote=50, stroke_width=1, spk_color_hex="#40e0f2", quote_color_hex="#ffe047", include_subtitles=True, progress_callback=None):
        """
        Exports selected matrix / champion voice / versus dialogue items directly into:
        - Cleanly organized project folder (DaVinci_Exports/<ProjectName>/Sesler & Gorseller)
        - 4K Splash Art (or LoR runeterra.ar Full Art) downloaded / cached for both speaker and target champion skins
        - High-resolution WAV extracted just-in-time
        - Supports 3 distinct DaVinci Resolve FCPXML v1.8 layouts:
          1. 'matrix_default'  : Atıf Matrisi standart sol-üst görsel + alt altyazı + sağ eylem şablonu
          2. 'champion_voices' : Karakter Replikleri / Söyledikleri (%100 Tam Ekran / Hedef Varsa %50-%50 Bölünmüş Sol Konuşan + Sağ Hedef + Alt Senkron Türkçe Eylem & Replik)
          3. 'versus_dialogue' : Birebir Diyaloglar (Sol ve Sağda kendi kapladıkları boyutta aralıklı kartlar + sırayla konuşanın altında çıkan replik)
        """
        import jit_audio_streamer
        import shutil

        total_items = len(items)
        if progress_callback:
            try:
                progress_callback({
                    "type": "init",
                    "message": f"Dışa aktarım başlatıldı. Toplam {total_items} adet replik işlenecek.",
                    "current": 0,
                    "total": total_items
                })
            except Exception:
                pass

        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if not output_dir:
            output_dir = os.path.join(root_dir, "DaVinci_Exports")
        os.makedirs(output_dir, exist_ok=True)

        clean_name = re.sub(r'[\\/*?:"<>|]', '_', timeline_name).strip('_') or "LoL_Secilen_Atiflar"

        # Klasörleme (Organize Project Folder)
        if bundle_folder:
            project_dir = os.path.join(output_dir, clean_name)
            audio_dir = os.path.join(project_dir, "Sesler")
            splash_dir = os.path.join(project_dir, "Gorseller")
            os.makedirs(audio_dir, exist_ok=True)
            os.makedirs(splash_dir, exist_ok=True)
            export_target_dir = project_dir
        else:
            project_dir = output_dir
            audio_dir = None
            splash_dir = None
            export_target_dir = output_dir

        skins_db = cls.get_skins_database()
        rich_entries = []

        # Madde 3: Hayatsöndüren (Spirit Blossom Kindred) kopyasını Kindred lehine filtrele
        filtered_items = []
        for it in items:
            spk = str(it.get('speaker_champ') or it.get('speaker') or '')
            tgt = str(it.get('target_champ') or it.get('target') or '')
            wid = str(it.get('wem_id') or it.get('raw_event') or '')
            if 'hayats' in spk.lower() or 'hayats' in tgt.lower() or '98sb044' in wid.lower():
                continue
            filtered_items.append(it)
        items = filtered_items

        # Projenin ana sol şampiyonunu belirle (örn: Azir)
        primary_champ = "Azir"
        if items:
            p_cand = items[0].get('left_champ') or ""
            if not p_cand:
                from collections import Counter
                all_c = [it.get('speaker_champ') or it.get('speaker') for it in items if it.get('speaker_champ') or it.get('speaker')]
                if all_c:
                    p_cand = Counter(all_c).most_common(1)[0][0]
            if p_cand:
                primary_champ = p_cand

        # Madde 1 & 5: Deterministik hedef şampiyon senkronizasyonu ve YouTube izlenme odaklı akıllı sıralama
        for i in range(len(items)):
            it = items[i]
            cur_spk = it.get('speaker_champ') or it.get('speaker') or ''
            raw_ev = str(it.get('raw_event') or it.get('event') or '')
            if raw_ev:
                try:
                    import importlib
                    import event_categorizer
                    importlib.reload(event_categorizer)
                    item_tr = event_categorizer.resolve_item_event_turkish(raw_ev)
                    if item_tr:
                        it['action_name'] = item_tr
                        it['action_type'] = item_tr
                    elif not it.get('action_name') or 'Item ' in str(it.get('action_name', '')):
                        _, fresh_act = event_categorizer.parse_event_info(raw_ev, cur_spk or primary_champ)
                        if fresh_act:
                            it['action_name'] = fresh_act
                            it['action_type'] = fresh_act
                except Exception:
                    pass

            if cur_spk.lower() == primary_champ.lower():
                resolved_p = cls._resolve_item_partner(it, primary_champ=primary_champ)
                if not resolved_p and layout_mode in ("versus_dialogue", "versus"):
                    if i + 1 < len(items):
                        nxt_spk = items[i + 1].get('speaker_champ') or items[i + 1].get('speaker') or ''
                        if nxt_spk.lower() != primary_champ.lower():
                            resolved_p = nxt_spk
                    if not resolved_p and i > 0:
                        prv_spk = items[i - 1].get('speaker_champ') or items[i - 1].get('speaker') or ''
                        if prv_spk.lower() != primary_champ.lower():
                            resolved_p = prv_spk
                if resolved_p:
                    it['target_champ'] = resolved_p
                    it['target'] = resolved_p
                    it['right_champ'] = resolved_p
                    if not it.get('target_skin_name'):
                        it['target_skin_name'] = f"Varsayılan {resolved_p}"
            elif layout_mode in ("versus_dialogue", "versus"):
                it['target_champ'] = primary_champ
                it['target'] = primary_champ
                it['left_champ'] = primary_champ
                it['right_champ'] = cur_spk
                if not it.get('target_skin_name'):
                    it['target_skin_name'] = f"Varsayılan {primary_champ}"

        # Karakterin Söyledikleri (champion_voices) modunda izleyiciyi videoda tutan optimum YouTube sıralaması:
        # 1) Özel Karakter Atıfları (Hedef şampiyona göre gruplu, kesintisiz %50/%50 görsel blok)
        # 2) Destansı Katletmeler (İlk Kan, Pentakill, Baron, Ejderha)
        # 3) Seçim, Yasaklama & Oyun Başlangıcı
        # 4) Genel Hikâye Replikleri, Seviye Atlama & Şaka/Kışkırtma/Kahkaha
        # 5) Eşya Satın Alma & Mağaza Replikleri
        # 6) Yetenekler (Q -> W -> E -> R Ulti) & Saldırı
        # 7) Hareket (Yürüme) & Recall / Yeniden Doğuş
        # 8) Ölüm / Can Verirken & Tüm Ses Efektleri / Homurtular (SFX) KESİNLİKLE EN SONDA!
        if layout_mode == "champion_voices" and len(items) > 1:
            try:
                import importlib
                import event_categorizer
                importlib.reload(event_categorizer)
                def _youtube_engagement_sort_key(item_With_idx):
                    orig_idx, x = item_With_idx
                    spk_c = x.get('speaker_champ') or x.get('speaker') or primary_champ
                    r_ev = str(x.get('raw_event') or x.get('event') or '')
                    act_n = str(x.get('action_name') or x.get('action_type') or '')
                    tgt_c = str(x.get('target_champ') or x.get('target') or '').strip()
                    cat_id, parsed_act = event_categorizer.parse_event_info(r_ev, spk_c) if r_ev else ("10_Genel_Replikler", act_n)
                    eff_act = parsed_act or act_n
                    w = event_categorizer.get_event_sort_weight(cat_id, eff_act, r_ev, spk_c)
                    ev_low = (r_ev + " " + eff_act).lower()
                    is_death_or_sfx = bool(
                        x.get('is_sfx') or
                        cat_id == "11_Efektler_ve_Homurtular" or
                        any(k in ev_low for k in ['death', 'die', 'ölürken', 'ölüm', 'can verirken', 'sfx', 'efor', 'homurtu', 'inilti', 'effort', 'grunt'])
                    )
                    if is_death_or_sfx:
                        return (2, "", max(880, w), eff_act, orig_idx)
                    # Hedef şampiyon varsa önce tüm hedef şampiyon etkileşimlerini (10..95) kendi içinde hedef ismine göre grupla
                    if tgt_c and w < 200:
                        return (0, tgt_c.lower(), w, eff_act, orig_idx)
                    return (1, "", w, eff_act, orig_idx)

                items = [x for _, x in sorted(enumerate(items), key=_youtube_engagement_sort_key)]
            except Exception as e:
                print(f"⚠️ YouTube siralama hatasi: {e}")

        for idx, it in enumerate(items):
            speaker = it.get('speaker_champ') or it.get('speaker')
            if not speaker:
                continue
            raw_event = it.get('raw_event') or it.get('event') or ''
            target = it.get('target_champ') or it.get('target') or ''
            wem_id = it.get('wem_id')
            transcript = it.get('transcript', '')
            action_type = it.get('action_type') or it.get('action_name') or ''
            action_name = it.get('action_name') or action_type
            is_lor_item = bool(
                str(raw_event).upper().startswith('VO_') or
                str(wem_id or '').upper().startswith('VO_') or
                str(it.get('ref_id', '')).startswith('LOR-') or
                str(it.get('speaker_skin_name', '')).startswith('LoR') or
                str(it.get('target_skin_name', '')).startswith('LoR') or
                it.get('is_lor', False) or
                it.get('game_type') == 'lor'
            )

            if progress_callback:
                try:
                    progress_callback({
                        "type": "processing",
                        "message": f"[{idx+1}/{total_items}] {speaker} repliği hazırlanıyor...",
                        "current": idx + 1,
                        "total": total_items,
                        "speaker": speaker
                    })
                except Exception:
                    pass

            # 1. JIT Audio Extraction
            wav_path = jit_audio_streamer.get_or_extract_audio(speaker, raw_event, target, wem_id=wem_id if wem_id else None)
            if not wav_path or not os.path.exists(wav_path):
                continue

            # Klasöre kopyalama (Audio bundling)
            final_audio_path = wav_path
            if bundle_folder and audio_dir:
                safe_spk = re.sub(r'[^a-zA-Z0-9_]', '', speaker)
                safe_wid = re.sub(r'[^a-zA-Z0-9_]', '_', str(wem_id or idx+1))
                dest_wav_name = f"{idx+1:02d}_{safe_spk}_{safe_wid}.wav"
                dest_wav_path = os.path.join(audio_dir, dest_wav_name)
                try:
                    shutil.copy2(wav_path, dest_wav_path)
                    final_audio_path = dest_wav_path
                except Exception:
                    final_audio_path = wav_path

            # 2. Transcript Çözümleme (Önbellekten veya Whisper ile)
            if not include_subtitles:
                transcript = ""
                if progress_callback:
                    try:
                        progress_callback({
                            "type": "processing",
                            "message": f"[{idx+1}/{total_items}] {speaker} ses ve görsel hazırlandı (Replik metinleri ve Whisper atlandı)",
                            "current": idx + 1,
                            "total": total_items,
                            "speaker": speaker
                        })
                    except Exception:
                        pass
            else:
                is_english_or_empty = (
                    not transcript or not transcript.strip() or
                    any(w in transcript.lower() for w in ['you should', 'watch me', 'glad you', 'gonna witness', 'hail to thee', 'an alliance', 'it is an honour', 'perish', 'join the', 'emperor of shurima'])
                )
                master_verified = cls.lookup_or_transcribe(wav_path, speaker=speaker, raw_event=raw_event, wem_id=wem_id)
                if master_verified and (is_english_or_empty or not it.get('user_edited', False)):
                    transcript = master_verified
                elif not transcript or not transcript.strip():
                    if progress_callback:
                        try:
                            progress_callback({
                                "type": "whisper_start",
                                "message": f"[{idx+1}/{total_items}] {speaker} için Whisper GPU (CUDA) transkript çözülüyor...",
                                "current": idx + 1,
                                "total": total_items,
                                "speaker": speaker
                            })
                        except Exception:
                            pass
                    transcript = master_verified or cls.lookup_or_transcribe(wav_path, speaker=speaker, raw_event=raw_event, wem_id=wem_id)

                if progress_callback:
                    try:
                        progress_callback({
                            "type": "whisper_done",
                            "message": f"[{idx+1}/{total_items}] {speaker}: \"{transcript or '(Replik metni yok)'}\"",
                            "current": idx + 1,
                            "total": total_items,
                            "speaker": speaker,
                            "transcript": transcript
                        })
                    except Exception:
                        pass

            # 3. Konuşmacı ve Hedef 4K Splash Art (veya LoR runeterra.ar / DataDragon Full Art) Çözümleme & İndirme
            splash_path = None
            target_splash_path = None
            if include_splash:
                spk_skin_num = it.get('speaker_skin_num', 0)
                spk_skin_name = it.get('speaker_skin_name', '')
                splash_path = cls._resolve_and_bundle_splash(
                    skins_db, speaker, spk_skin_num, spk_skin_name,
                    wav_fallback=wav_path, target_fallback=target,
                    splash_dir=splash_dir, bundle_folder=bundle_folder,
                    is_lor=is_lor_item
                )

                if target:
                    tgt_skin_num = it.get('target_skin_num', 0)
                    tgt_skin_name = it.get('target_skin_name', '')
                    # Eğer konuşmacı LoR ise veya hedef LoR şampiyonları arasındaysa daima LoR kart görseli çöz
                    target_splash_path = cls._resolve_and_bundle_splash(
                        skins_db, target, tgt_skin_num, tgt_skin_name,
                        wav_fallback=None, target_fallback="",
                        splash_dir=splash_dir, bundle_folder=bundle_folder,
                        is_lor=is_lor_item
                    )

            rich_entries.append({
                'audio_path': final_audio_path,
                'splash_path': splash_path,
                'target_splash_path': target_splash_path,
                'speaker': speaker,
                'skin_name': it.get('speaker_skin_name', ''),
                'target': target,
                'target_skin_num': it.get('target_skin_num', 0),
                'target_skin_name': it.get('target_skin_name', ''),
                'transcript': transcript,
                'event': raw_event,
                'action_type': action_type,
                'action_name': action_name,
                'dialogue_side': it.get('dialogue_side', ''),
                'left_champ': it.get('left_champ', ''),
                'wem_id': wem_id
            })

        if not rich_entries:
            if progress_callback:
                try:
                    progress_callback({
                        "type": "error",
                        "message": "Hiçbir ses veya replik işlenemedi.",
                        "current": 0,
                        "total": total_items
                    })
                except Exception:
                    pass
            return None

        fcpxml_path = os.path.join(export_target_dir, f"{clean_name}.fcpxml")
        xml_path = os.path.join(export_target_dir, f"{clean_name}.xml")

        if progress_callback:
            try:
                progress_callback({
                    "type": "xml",
                    "message": f"FCPXML v1.8 ({layout_mode} • Font: {font_family} {font_face}) ve FCP7 XML timeline dosyaları derleniyor...",
                    "current": total_items,
                    "total": total_items
                })
            except Exception:
                pass

        safe_fps = int(round(float(fps))) if fps else 60

        # Generate DaVinci FCPXML v1.8 according to layout_mode
        if layout_mode == "champion_voices":
            cls.generate_champion_voices_fcpxml(
                rich_entries,
                fcpxml_path,
                gap_seconds=gap_seconds,
                timeline_name=clean_name,
                fps=safe_fps,
                include_splash=include_splash,
                include_action_label=include_action_label,
                font_family=font_family,
                font_face=font_face,
                font_size_spk=font_size_spk,
                font_size_quote=font_size_quote,
                stroke_width=stroke_width,
                spk_color_hex=spk_color_hex,
                quote_color_hex=quote_color_hex,
                include_text=include_subtitles
            )
        elif layout_mode in ("versus_dialogue", "versus"):
            cls.generate_versus_dialogue_fcpxml(
                rich_entries,
                fcpxml_path,
                gap_seconds=gap_seconds,
                timeline_name=clean_name,
                fps=safe_fps,
                include_splash=include_splash,
                include_action_label=include_action_label,
                font_family=font_family,
                font_face=font_face,
                font_size_spk=font_size_spk,
                font_size_quote=font_size_quote,
                stroke_width=stroke_width,
                spk_color_hex=spk_color_hex,
                quote_color_hex=quote_color_hex,
                include_text=include_subtitles
            )
        else:
            cls.generate_fcpxml_from_sorted(
                rich_entries,
                fcpxml_path,
                gap_seconds=gap_seconds,
                timeline_name=clean_name,
                fps=safe_fps,
                include_splash=include_splash,
                text_pos_y=-480,
                include_action_label=include_action_label,
                action_pos_x=action_pos_x,
                action_pos_y=action_pos_y,
                action_zoom=action_zoom,
                font_family=font_family,
                include_text=include_subtitles
            )

        # Generate FCP 7 XML v5
        cls.generate_fcp7_xml(
            rich_entries,
            xml_path,
            gap_seconds=gap_seconds,
            timeline_name=clean_name,
            fps=safe_fps,
            include_splash=include_splash,
            text_pos_y=-480,
            include_action_label=include_action_label,
            action_pos_x=action_pos_x,
            action_pos_y=action_pos_y,
            action_zoom=action_zoom,
            generate_companion_fcpxml=False,
            include_text=include_subtitles,
            generate_srt=include_subtitles
        )

        # Optional ZIP archive generation
        zip_path = None
        if bundle_folder and project_dir and os.path.exists(project_dir):
            if progress_callback:
                try:
                    progress_callback({
                        "type": "zip",
                        "message": "Sesler, görseller ve timeline tek bir .ZIP paketinde toplanıyor...",
                        "current": total_items,
                        "total": total_items
                    })
                except Exception:
                    pass
            try:
                zip_base = os.path.join(output_dir, f"{clean_name}_Paket")
                zip_result = shutil.make_archive(zip_base, 'zip', project_dir)
                zip_path = zip_result
            except Exception as e:
                print(f"⚠️ ZIP olusturulamadi: {e}")

        result_payload = {
            "status": "success",
            "layout_mode": layout_mode,
            "fcpxml_path": fcpxml_path,
            "xml_path": xml_path,
            "project_dir": project_dir,
            "audio_dir": audio_dir,
            "splash_dir": splash_dir,
            "zip_path": zip_path,
            "clips_count": len(rich_entries),
            "gap_seconds": gap_seconds,
            "timeline_name": clean_name,
            "output_dir": output_dir,
            "items": rich_entries
        }

        if progress_callback:
            try:
                progress_callback({
                    "type": "done",
                    "message": f"Dışa aktarım başarıyla tamamlandı! Toplam {len(rich_entries)} replik hazır.",
                    "current": total_items,
                    "total": total_items,
                    "result": result_payload
                })
            except Exception:
                pass

        return result_payload

