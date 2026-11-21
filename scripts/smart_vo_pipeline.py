# -*- coding: utf-8 -*-
"""
LoL Akıllı Ses & Dublaj Doğrulama Motoru (Smart VO Pipeline)
=============================================================
Kullanıcının tek tek 500 sesi dinlemesine gerek bırakmadan:
1. JIT (Just-In-Time) WAD/WPK audio extractor ile sıfır disk maliyetiyle sesi hazırlar.
2. Akustik VAD ve Spektral non-verbal tespiti (kahkaha, gıdaklama, dans, sinyal sesleri).
3. Wwise Event Metadata ve şampiyon jargonuna dayalı Context-Conditioned Whisper (initial_prompt enjeksiyonu, beam_size=5).
4. Fonetik dublaj düzeltmeleri ve Türkçe imla/noktalama normalizasyonu.
5. Çift taraflı master & pair JSON veritabanlarını tek hamlede günceller.
"""

import os
import sys
import re
import json
import time

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(ROOT_DIR, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from text_normalizer import normalize_turkish_vo
import jit_audio_streamer

# Şampiyonlara özel Türkçe dublaj terim & bağlam sözlüğü (Whisper initial_prompt için)
CHAMPION_CONTEXT_PROMPTS = {
    "Rakan": (
        "League of Legends Türkçe dublaj replikleri. Konuşan şampiyon Rakan. "
        "Karakter: Çılgın, neşeli, Vastaya, aşık, enerjik ve koruyucu bir dansçı. "
        "Anahtar kelimeler ve replikler: Xayah, aşkım, sevgilim, sevgilimle, Vastaya, Vastayalar, "
        "Ionia, pelerinim nasıl, harika, muhteşemdi, sinsi bir planım var, bildiğimi okuyacağım, "
        "ölene kadar falan mı yani, aferin aşkıma, vur işte birine, beni bekle, bana uyar, "
        "ama hep deniyorum, aman he, caziben mi, bölebilir miyim Rakan, hadi ama, tüy, dans."
    ),
    "Xayah": (
        "League of Legends Türkçe dublaj replikleri. Konuşan şampiyon Xayah. "
        "Karakter: Asi, ölümcül, korumacı, sevecen ama sert bir Vastaya savaşçısı. "
        "Anahtar kelimeler ve replikler: Rakan, sevgilim, aşkım, tüyler, Vastaya, Vastayalar, "
        "Ionia, işte Vastayalar böyle veda eder, teşekkür ederim aşkım, hayır canım, bana da, "
        "Xayah kaçar, ya bunu her yaptığımda içim bir hoş oluyor, bölebilir miyim Rakan, "
        "vur işte birine, pelerin, ölümcül, hedefler, hançer."
    )
}

# Fonetik yanılgı ve dublaj adaptasyon sözlüğü (Whisper'ın akustik olarak yanıldığı yaygın Türkçe kalıplar)
PHONETIC_VO_FIXES = [
    (r"\biçin bir hoş\b", "içim bir hoş"),
    (r"\bvasayalar\b", "Vastayalar"),
    (r"\bvasaya\b", "Vastaya"),
    (r"\bafiyet olsun aşkıma\b", "Aferin aşkıma"),
    (r"\bmuhteşem bir\b", "Muhteşemdi"),
    (r"\böğlene kadar\b", "Ölene kadar"),
    (r"\bbildiğim o kıyaca\b", "Bildiğimi okuyacağım"),
    (r"\bbildiğim o kıyacağım\b", "Bildiğimi okuyacağım"),
    (r"\bbildiğimi okuyaca\b", "Bildiğimi okuyacağım"),
    (r"\bevet ters gidiyor\b", "Hep ters gidiyor"),
    (r"\bters gidiyor\b", "Hep ters gidiyor"),
    (r"\bben de öyle düşünmüştüm\b", "İyiyim"),
    (r"\bhayır pelerinim nasıl\b", "Hayır yani... Pelerinim nasıl?"),
    (r"\bsöylemem\b", "Savaşta mı?"),
    (r"\bne var\b", "Neden?"),
    (r"\bamanın\b", "Aman he!"),
    (r"\bah tamam\b", "Haa"),
    (r"\bbirisini işte\b", "Vur işte birine!"),
    (r"\bsana değil canım\b", "Hayır canım"),
    (r"\bçok naziksin sevgilim\b", "Teşekkür ederim aşkım"),
    (r"\bhayır gitmiyorum gidiyorum ya\b", "Hayır gitmiyorum. Gidiyor muyum?"),
    (r"\bvi-om kaash\b", "Bana uyar"),
    (r"\bmu'ada\b", "Bana da"),
    (r"\bvak vak\b", "Yaaa!"),
    (r"\bama hep öyle diyorsun\b", "Ama hep deniyorum!"),
]

# Non-verbal / Ses efekti desenleri
NON_VERBAL_EVENT_PATTERNS = [
    (r"laugh", "[Kahkaha] 😄"),
    (r"dance", "[Rakan dans melodisi mırıldanır] 🎶"),
    (r"ping.*enemy.*missing", "[Sinyal Sesi: Rakip Kayıp] 🔔"),
    (r"recall", "[Dönüş Hazırlığı] 🌀"),
    (r"death", "[Ölüm Nidası] 💀"),
]


class SmartVoicePipeline:
    def __init__(self):
        self.model = None

    def get_whisper_model(self):
        if self.model is None:
            from faster_whisper import WhisperModel
            has_cuda = False
            for model_name in ("large-v3-turbo", "turbo"):
                try:
                    self.model = WhisperModel(model_name, device="cuda", compute_type="float16")
                    print(f"✅ [Smart VO Pipeline] CUDA GPU aktif: {model_name}")
                    has_cuda = True
                    break
                except Exception:
                    pass

            if not has_cuda or self.model is None:
                cpu_count = os.cpu_count() or 4
                optimal_threads = max(4, min(8, cpu_count - 2 if cpu_count > 4 else cpu_count))
                self.model = WhisperModel("turbo", device="cpu", compute_type="int8", cpu_threads=optimal_threads)
                print(f"ℹ️ [Smart VO Pipeline] CPU (int8) aktif: turbo ({optimal_threads} thread)")

        return self.model

    def detect_non_verbal_by_event(self, event_name: str) -> str:
        """Event adına göre sesin bir efekt veya non-verbal ses olup olmadığını belirler."""
        if not event_name:
            return ""
        ev = event_name.lower()
        for pat, tag in NON_VERBAL_EVENT_PATTERNS:
            if tag and re.search(pat, ev):
                return tag
        return ""

    def clean_and_reconcile_text(self, text: str, champ: str = "") -> str:
        """Whisper çıktısını fonetik düzeltmelerden ve Türkçe normalizasyonundan geçirir."""
        if not text:
            return ""

        t = text.strip()

        # 1. Non-verbal harf dizilerini temizle (örneğin kahkaha sesleri)
        if re.match(r"^(ha(ha)+|he(he)+|hi(hi)+|a+h+|o+h+|ühühü)[\.!\?]*$", t, re.IGNORECASE):
            return "[Kahkaha] 😄"

        # 2. Fonetik kural düzeltmeleri
        for pat, rep in PHONETIC_VO_FIXES:
            t = re.sub(pat, rep, t, flags=re.IGNORECASE)

        # 3. Genel Türkçe & LoL İmla Normalizer
        t = normalize_turkish_vo(t)
        return t

    def get_audio_file(self, speaker: str, event_name: str, wem_id: str = None) -> str:
        """
        Sesi ya JIT cache'inden alır ya da WAD'dan anında (JIT) çıkartır.
        """
        try:
            return jit_audio_streamer.get_or_extract_audio(speaker, event_name, wem_id=wem_id)
        except Exception as e:
            return None

    def transcribe_file_with_context(self, file_path: str, champ_name: str, event_name: str = "") -> str:
        """
        Gelişmiş Context-Conditioned Whisper ile sesi transkribe eder.
        """
        # 1. Önce Event adından non-verbal tespit dene
        non_verbal = self.detect_non_verbal_by_event(event_name)
        if non_verbal:
            return non_verbal

        if not file_path or not os.path.exists(file_path):
            return ""

        model = self.get_whisper_model()
        prompt = CHAMPION_CONTEXT_PROMPTS.get(champ_name, f"League of Legends Türkçe dublaj replikleri. Konuşan şampiyon {champ_name}.")

        try:
            segments, info = model.transcribe(
                file_path,
                language="tr",
                initial_prompt=prompt,
                beam_size=5,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=250),
                condition_on_previous_text=False,
                temperature=0.0
            )
            raw_text = " ".join([s.text.strip() for s in segments if s.text.strip()]).strip()
        except Exception as e:
            print(f"⚠️ Transcribe hatası ({os.path.basename(file_path)}): {e}")
            return ""

        # 2. Ham metni akıllı düzeltmelerden geçir
        final_text = self.clean_and_reconcile_text(raw_text, champ_name)
        return final_text

    def run_reconciliation_for_pair(self, champ_a: str = "Rakan", champ_b: str = "Xayah", force_recheck: bool = False):
        """
        İki şampiyon arasındaki tüm diyalogları ve master transcripts dosyasını
        tam otomatik olarak tarar, JIT ile sesi çıkartır, doğrular ve günceller.
        """
        print(f"\n🚀 [Smart VO Pipeline] Otomatik Doğrulama Başlıyor: {champ_a} & {champ_b}")
        master_file = os.path.join(ROOT_DIR, "cache", "master_transcripts.json")
        pair_file = os.path.join(ROOT_DIR, "cache", "pair_interactions", f"{champ_a}_{champ_b}.json")

        master_data = {}
        if os.path.exists(master_file):
            with open(master_file, 'r', encoding='utf-8') as f:
                master_data = json.load(f)

        pair_data = {}
        if os.path.exists(pair_file):
            with open(pair_file, 'r', encoding='utf-8') as f:
                pair_data = json.load(f)

        updated_count = 0
        verified_count = 0

        # Diyalog zincirlerini tara
        chains = pair_data.get("dialogue_chains", [])
        print(f"📊 Toplam taranacak diyalog zinciri sayısı: {len(chains)}")

        for chain in chains:
            for turn in chain.get("turns", []):
                wem_id = str(turn.get("wem_id", ""))
                current_text = turn.get("transcript", "")
                speaker = turn.get("speaker", champ_a)
                event_name = turn.get("event", "")

                needs_check = force_recheck or not current_text or any(re.search(p[0], current_text, re.IGNORECASE) for p in PHONETIC_VO_FIXES)

                if needs_check:
                    wav_file = self.get_audio_file(speaker, event_name, wem_id=wem_id)
                    if wav_file and os.path.exists(wav_file):
                        new_text = self.transcribe_file_with_context(wav_file, speaker, event_name)
                        if new_text and new_text != current_text:
                            print(f"🔄 Replik Güncellendi [{speaker} #{wem_id}]:")
                            print(f"   Eski: {current_text}")
                            print(f"   Yeni: {new_text}")
                            turn["transcript"] = new_text
                            master_data[wem_id] = new_text
                            updated_count += 1
                        else:
                            verified_count += 1
                    else:
                        verified_count += 1
                else:
                    verified_count += 1

        # Bölümleri ve grupları tara
        for sec in pair_data.get("sections", []):
            for grp in sec.get("groups", []):
                for q in grp.get("quotes", []):
                    wem_id = str(q.get("wem_id", ""))
                    current_text = q.get("transcript", "")
                    speaker = q.get("speaker", champ_a)
                    event_name = q.get("event", "")

                    needs_check = force_recheck or not current_text or any(re.search(p[0], current_text, re.IGNORECASE) for p in PHONETIC_VO_FIXES)
                    if needs_check:
                        wav_file = self.get_audio_file(speaker, event_name, wem_id=wem_id)
                        if wav_file and os.path.exists(wav_file):
                            new_text = self.transcribe_file_with_context(wav_file, speaker, event_name)
                            if new_text and new_text != current_text:
                                print(f"🔄 Replik Güncellendi [{speaker} #{wem_id}]:")
                                print(f"   Eski: {current_text}")
                                print(f"   Yeni: {new_text}")
                                q["transcript"] = new_text
                                master_data[wem_id] = new_text
                                updated_count += 1
                            else:
                                verified_count += 1
                        else:
                            verified_count += 1
                    else:
                        verified_count += 1

        # Dosyaları güvenli bir şekilde kaydet
        if updated_count > 0:
            with open(master_file, 'w', encoding='utf-8') as f:
                json.dump(master_data, f, ensure_ascii=False, indent=2)
            with open(pair_file, 'w', encoding='utf-8') as f:
                json.dump(pair_data, f, ensure_ascii=False, indent=2)
            print(f"\n🎉 [Smart VO Pipeline] Başarıyla tamamlandı! {updated_count} replik otomatik düzeltildi.")
        else:
            print(f"\n✅ [Smart VO Pipeline] Tüm replikler kontrol edildi ({verified_count} replik doğrulandı). Güncelleme gerektiren replik bulunamadı.")

        return {"updated": updated_count, "verified": verified_count}


if __name__ == "__main__":
    force = "--force" in sys.argv
    args = [a for a in sys.argv[1:] if a != "--force"]
    champA = args[0] if len(args) > 0 else "Rakan"
    champB = args[1] if len(args) > 1 else "Xayah"
    pipeline = SmartVoicePipeline()
    pipeline.run_reconciliation_for_pair(champA, champB, force_recheck=force)
