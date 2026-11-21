# -*- coding: utf-8 -*-
import os
import json
import re
import difflib

# Sistemdeki mevcut DaVinci Resolve NVIDIA CUDA 12 ve cuBLAS DLL'lerini otomatik bağla
davinci_dir = r"C:\Program Files\Blackmagic Design\DaVinci Resolve"
if os.path.exists(davinci_dir):
    try:
        os.add_dll_directory(davinci_dir)
    except Exception:
        pass
    os.environ['PATH'] = davinci_dir + ';' + os.environ.get('PATH', '')

class AIVoiceDetector:
    """
    Yüksek Başarımlı, Optimize Edilmiş Çoklu Yapay Zeka & Fonetik Güven Skorlu
    Faster-Whisper (Large-v3-Turbo) Seslendirme ve Replik Çözümleme Motoru.
    """
    _model_instance = None
    _memory_cache = {}

    CHAMPION_KEYWORDS = {
        'azir': "Azir, Shurima'nın İmparatoru, kum askerleri, güneş kursu, yükselmiş, imparatorluğum.",
        'yasuo': "Yasuo, Günahkâr Kılıç, hasagi, rüzgar tekniği, Yone, Ionia, kılıç.",
        'pyke': "Pyke, Kanlırıhtım'ın Öcü, zıpkın, boğulanlar, ölüm listesi, Bilgewater.",
        'jax': "Jax, Silah Ustası, lamba, Icathia, ayaklanma, sürpriz.",
        'jarvan iv': "Jarvan IV, Demacia Prensi, Demacia'nın Simgesi, çelik, kumun ittifakı.",
        'jarvan': "Jarvan IV, Demacia Prensi, Demacia'nın Simgesi, çelik, kumun ittifakı.",
        'irelia': "Irelia, Bıçakların Dansı, Ionia, direniş, dans, ata mirası.",
        'renekton': "Renekton, Kumların Kasabı, Shurima, intikam, kardeş, Nasus.",
        'nasus': "Nasus, Kumların Efendisi, kütüphane, akıl, Shurima, Renekton.",
        'xerath': "Xerath, Yüksek Büyücü, Shurima, büyü, taht, serbest.",
        'sivir': "Sivir, Savaş Hanımı, Shurima mirası, kiralık savaşçı, altın.",
        'taliyah': "Taliyah, Taş Örücü, Shurima çölü, taşlar, Ionia, çırak.",
        'ekko': "Ekko, Zamanı Kıran Çocuk, Zaun, Z-Sürücüsü, Piltover, zaman sıçraması.",
        'kindred': "Kindred, Kuzubaşı ve Kurt, av, ölüm, ecel, son nefes.",
        'lillia': "Lillia, Narin Çiçek, düşler, Ionia ormanı, rüya, ağaç.",
        'neeko': "Neeko, Meraklı Bukalemun, Oovi-kat, vastaya, taklit, şekil değiştirici.",
        'garen': "Garen, Demacia'nın Kudreti, adalet, dönen kılıç, koruyucu.",
        'darius': "Darius, Noxus'un Eli, güç, tereddüt, balta, zafer.",
        'aatrox': "Aatrox, Darkin Kılıcı, sonun başlangıcı, gazap, kılıç, karanlık.",
        'jhin': "Jhin, Kusursuz Katil, dört, sanat, sahne, Ionia.",
        'riven': "Riven, Sürgün, kırık kılıç, kefaret, rüzgar darbesi.",
        'viego': "Viego, Mahvolmuş Kral, Isolde, kara sis, kılıç, taç.",
        'swain': "Swain, Noxus'un Büyük Generali, kuzgun, iblis, sır, Karagül, imparatorluk, püskürtün, Leviathan, Darkwill, vastaya."
    }

    _quote_pool_cache = {}

    @classmethod
    def get_champion_quote_pool(cls, speaker: str) -> list:
        """
        Şampiyonun bilinen tüm resmi Türkçe repliklerini master veritabanından
        ve veri dosyalarından toplar. Fonetik doğrulama için aday havuzu oluşturur.
        """
        if not speaker:
            return []
        spk_clean = speaker.strip().lower()
        if spk_clean in cls._quote_pool_cache:
            return cls._quote_pool_cache[spk_clean]

        pool = set()
        # 1. master_transcripts.json
        master_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cache", "master_transcripts.json")
        if os.path.exists(master_path):
            try:
                with open(master_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for k, v in data.items():
                    if isinstance(v, str) and v.strip() and spk_clean in k.lower():
                        pool.add(v.strip())
            except Exception:
                pass

        # 2. lor_matrix_data.json
        lor_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lol-matrix-web", "public", "data", "lor_matrix_data.json")
        if os.path.exists(lor_path):
            try:
                with open(lor_path, 'r', encoding='utf-8') as f:
                    lmd = json.load(f)
                for c in lmd.get('champions', []):
                    c_name = (c.get('name') or c.get('champion') or '').lower()
                    if c_name == spk_clean:
                        for it in c.get('outgoing_items', []) + c.get('incoming_items', []):
                            txt = (it.get('transcript') or it.get('text') or '').strip()
                            if txt:
                                pool.add(txt)
            except Exception:
                pass

        # 3. data/wiki_quotes/{speaker}.json (Wiki resmi replik veri seti)
        wiki_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "wiki_quotes", f"{speaker.capitalize()}.json")
        if os.path.exists(wiki_file):
            try:
                with open(wiki_file, 'r', encoding='utf-8') as f:
                    wiki_data = json.load(f)
                for entry in wiki_data:
                    # Varsa Türkçe çeviri/karşılık veya event kalıbı
                    tr_text = entry.get('turkish_quote') or entry.get('transcript') or ''
                    if tr_text:
                        pool.add(tr_text.strip())
            except Exception:
                pass

        res = list(pool)
        cls._quote_pool_cache[spk_clean] = res
        return res

    @classmethod
    def get_model(cls):
        if cls._model_instance is None:
            from faster_whisper import WhisperModel
            import ctranslate2

            has_cuda = False
            try:
                has_cuda = ctranslate2.get_cuda_device_count() > 0
            except Exception:
                has_cuda = False

            if has_cuda:
                for model_name in ("large-v3-turbo", "turbo"):
                    try:
                        cls._model_instance = WhisperModel(model_name, device="cuda", compute_type="float16")
                        print(f"[Whisper AI] CUDA GPU (float16) aktif: {model_name}")
                        break
                    except Exception as e:
                        print(f"[Whisper AI] CUDA başlatılamadı ({model_name}): {e}")
                        has_cuda = False

            if not has_cuda or cls._model_instance is None:
                cpu_count = os.cpu_count() or 4
                optimal_threads = max(4, min(8, cpu_count - 2 if cpu_count > 4 else cpu_count))
                for model_name in ("large-v3-turbo", "turbo"):
                    try:
                        cls._model_instance = WhisperModel(model_name, device="cpu", compute_type="int8", cpu_threads=optimal_threads)
                        print(f"[Whisper AI] CPU (int8) aktif: {model_name}")
                        break
                    except Exception:
                        continue
        return cls._model_instance

    @classmethod
    def build_initial_prompt(cls, speaker: str = "", target: str = "") -> str:
        """
        Whisper Large-v3-Turbo için oyun terimlerini, bölgelerini ve şampiyon kilit kelimelerini
        aşılama amacıyla 224 token sınırını aşmayacak zengin bir sözlük ve stil ipucu üretir.
        """
        prompts = []
        spk_clean = str(speaker or "").lower().strip()
        tgt_clean = str(target or "").lower().strip()

        # 1. Konuşan şampiyona özel ön ek
        if spk_clean in cls.CHAMPION_KEYWORDS:
            prompts.append(cls.CHAMPION_KEYWORDS[spk_clean])
        elif speaker:
            prompts.append(f"{speaker} repliği ve seslendirmesi.")

        # 2. Hedef şampiyon karşılaşma ipucu
        if tgt_clean and tgt_clean != spk_clean:
            if tgt_clean in cls.CHAMPION_KEYWORDS:
                prompts.append(f"{target} ile karşılaşma.")
            else:
                prompts.append(f"{target} karşı karşıya.")

        # 3. Genel LoL / LoR Evren Sözlüğü (Bölgeler ve Fonetik Kilit Kelimeler)
        prompts.append(
            "League of Legends ve Legends of Runeterra şampiyon replikleri ve seslendirmeleri. "
            "Demacia, Noxus, Shurima, Ionia, Zaun, Piltover, Targon, Freljord, Gölge Adalar, Bilgewater. "
            "Darkin, Sihirdar Vadisi, Runeterra."
        )

        return " ".join(prompts)

    @classmethod
    def load_cache(cls, champion_dir):
        if not champion_dir or not os.path.isdir(champion_dir):
            return {}
        cache_path = os.path.join(champion_dir, ".ai_voice_cache.json")
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    @classmethod
    def save_cache(cls, champion_dir, cache_data):
        if not champion_dir or not os.path.isdir(champion_dir):
            return
        cache_path = os.path.join(champion_dir, ".ai_voice_cache.json")
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    @classmethod
    def transcribe_with_confidence(cls, file_path: str, speaker: str = "", target: str = "", reference_text: str = "") -> dict:
        """
        Çoklu Yapay Zeka & Fonetik Güven Skoru Motoru:
        - Whisper Large-v3-Turbo ile optimize edilmiş decoding parametreleri (beam_size=5, Silero VAD, initial_prompt).
        - Fonetik sözlük düzeltmeleri (fix_champion_names_in_text).
        - Akustik log-olasılık + difflib fonetik benzerlik skoru hesaplama (0 - 100 arası).
        """
        if not os.path.isfile(file_path):
            return {
                "text": "",
                "confidence_score": 0,
                "has_speech": False,
                "status": "file_not_found"
            }

        # 1. Stil ve Sözlük İpucu Oluştur
        initial_prompt = cls.build_initial_prompt(speaker, target)

        model = cls.get_model()
        segs = []
        dur = 0.0

        # Decode Parametreleri: Sıkılaştırılmış, halüsinasyonu kesen tam konfigürasyon
        transcribe_kwargs = dict(
            language="tr",
            initial_prompt=initial_prompt,
            beam_size=5,
            temperature=0.0,
            condition_on_previous_text=False,
            compression_ratio_threshold=2.2,
            no_speech_threshold=0.6,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=250, speech_pad_ms=150)
        )

        try:
            segments, info = model.transcribe(file_path, **transcribe_kwargs)
            segs = list(segments)
            dur = getattr(info, 'duration', 0.0)
        except Exception as e_gpu:
            # GPU başarısız olursa CPU fallback
            try:
                from faster_whisper import WhisperModel
                cpu_count = os.cpu_count() or 4
                optimal_threads = max(4, min(8, cpu_count - 2 if cpu_count > 4 else cpu_count))
                cpu_model = WhisperModel("turbo", device="cpu", compute_type="int8", cpu_threads=optimal_threads)
                segments, info = cpu_model.transcribe(file_path, **transcribe_kwargs)
                segs = list(segments)
                dur = getattr(info, 'duration', 0.0)
            except Exception:
                segs = []

        if not segs:
            # VAD konuşma bulamadıysa (sadece combat kükremesi/efekt)
            return {
                "text": "",
                "confidence_score": 0,
                "has_speech": False,
                "status": "no_speech_detected",
                "duration": dur
            }

        full_text = " ".join([s.text.strip() for s in segs]).strip()

        # YouTube / Whisper standart halüsinasyon kalıplarını temizle
        hallucinations = ['altyazı', 'abone', 'beğen', 'teşekkür', 'izlediğiniz', 'çeviri', 'subtitle', 'transcript']
        if any(h in full_text.lower() for h in hallucinations):
            full_text = ""

        # 1. Metin Normalizasyonu ve Fonotaktik N/M Düzeltmesi
        try:
            from text_normalizer import normalize_turkish_vo, phonetic_similarity
            corrected_text = normalize_turkish_vo(full_text)
        except Exception:
            corrected_text = full_text

        # 2. Akustik Güven Skoru Hesabı (avg_logprob bazlı)
        avg_logprob = sum(getattr(s, 'avg_logprob', -0.5) for s in segs) / max(1, len(segs))
        no_speech_prob = max(getattr(s, 'no_speech_prob', 0.0) for s in segs)

        acoustic_score = max(30, min(98, int(round((1.0 + avg_logprob) * 95))))
        if no_speech_prob > 0.4:
            acoustic_score = max(20, acoustic_score - int(no_speech_prob * 40))

        # 3. Çoklu Yapay Zeka & Fonetik Güven Skoru ile Wiki / Replik Havuzu Eşleştirmesi
        # Körü körüne çeviri yapmak yerine akustik fonetik benzerliğe göre doğrular
        quote_pool = cls.get_champion_quote_pool(speaker)
        candidates = []
        if reference_text and reference_text.strip():
            candidates.append(reference_text.strip())
        candidates.extend(quote_pool)

        best_cand = None
        best_ratio = 0.0

        if candidates and corrected_text:
            try:
                from text_normalizer import phonetic_similarity
                for cand in candidates:
                    ratio = phonetic_similarity(corrected_text, cand)
                    if ratio > best_ratio:
                        best_ratio = ratio
                        best_cand = cand
            except Exception:
                pass

        final_score = acoustic_score
        chosen_text = corrected_text
        needs_review = False

        if best_ratio >= 0.72 and best_cand:
            # Fonetik olarak aynı cümle (n/m kaymaları, harf düşmesi, takı farkı resmi dublaja kilitlenir)
            chosen_text = best_cand
            final_score = max(acoustic_score, int(round(90 + best_ratio * 10)))
            needs_review = False
        elif 0.55 <= best_ratio < 0.72 and best_cand:
            # Şüpheli kısmi benzerlik: Körü körüne atlama, Whisper'ın duyduğu temiz Türkçe metni koru
            chosen_text = corrected_text
            final_score = max(acoustic_score, int(round(72 + best_ratio * 10)))
            needs_review = True
        else:
            # Havuzda bulunmayan özgün replik: Fonotaktik temizlenmiş hali kullanılır
            chosen_text = corrected_text
            final_score = acoustic_score
            needs_review = bool(acoustic_score < 80)

        has_speech = bool(chosen_text and len(chosen_text.split()) >= 1)

        return {
            "text": chosen_text,
            "raw_text": full_text,
            "confidence_score": final_score if has_speech else 0,
            "phonetic_match_ratio": round(best_ratio, 2),
            "needs_review": needs_review,
            "matched_candidate": best_cand if best_ratio >= 0.72 else "",
            "avg_logprob": round(avg_logprob, 3),
            "no_speech_prob": round(no_speech_prob, 3),
            "has_speech": has_speech,
            "duration": dur,
            "status": "success" if has_speech else "non_verbal"
        }

    @classmethod
    def is_spoken_dialogue(cls, file_path, champion_dir=None, speaker="", target="", reference_text=""):
        """
        Dosyayı optimize edilmiş Whisper Large-v3-Turbo ve Fonetik Skoru ile dinler.
        (True, text): Anlamlı konuşma varsa.
        (False, ""): Sadece vokal olmayan combat çığlığı / efekt ise.
        """
        if not os.path.isfile(file_path):
            return False, ""

        abs_path = os.path.abspath(file_path)
        if abs_path in cls._memory_cache:
            return cls._memory_cache[abs_path]

        file_name = os.path.basename(file_path)
        cache = cls.load_cache(champion_dir) if champion_dir else {}

        if file_name in cache:
            entry = cache[file_name]
            res = (entry.get("has_speech", False), entry.get("text", ""))
            cls._memory_cache[abs_path] = res
            return res

        # Çoklu yapay zeka & fonetik güven skoru ile transkripsiyon yap
        res_dict = cls.transcribe_with_confidence(
            file_path,
            speaker=speaker,
            target=target,
            reference_text=reference_text
        )

        has_speech = res_dict.get("has_speech", False)
        text = res_dict.get("text", "")

        result_entry = {
            "has_speech": has_speech,
            "text": text,
            "confidence_score": res_dict.get("confidence_score", 0),
            "duration": res_dict.get("duration", 0.0)
        }

        if champion_dir:
            cache[file_name] = result_entry
            cls.save_cache(champion_dir, cache)

        res_tuple = (has_speech, text)
        cls._memory_cache[abs_path] = res_tuple
        return res_tuple
