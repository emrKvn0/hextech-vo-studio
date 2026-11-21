# -*- coding: utf-8 -*-
"""
LoL Türkçe Ses & Replik İmla ve Metin Normalizasyon Motoru
Kullanıcı veya AI tarafından girilen replikleri Türkçe dilbilgisi kurallarına,
büyük/küçük harf düzenine, soru eklerine ve LoL evren terminolojisine göre otomatik formatlar.
"""

import re

# LoL Evreni Özel İsimler ve Terimler Sözlüğü
LOL_PROPER_NOUNS = {
    "rakan": "Rakan",
    "xayah": "Xayah",
    "vastaya": "Vastaya",
    "vastayalar": "Vastayalar",
    "vastayalı": "Vastayalı",
    "ionia": "Ionia",
    "ionialı": "Ionialı",
    "noxus": "Noxus",
    "noxuslu": "Noxuslu",
    "demacia": "Demacia",
    "demacialı": "Demacialı",
    "demacialısın": "Demacialısın",
    "piltover": "Piltover",
    "zaun": "Zaun",
    "zaunlu": "Zaunlu",
    "shurima": "Shurima",
    "targon": "Targon",
    "freljord": "Freljord",
    "bilgewater": "Bilgewater",
    "runeterra": "Runeterra",
    "bandle": "Bandle",
    "yordle": "Yordle",
    "aatrox": "Aatrox",
    "ahri": "Ahri",
    "akali": "Akali",
    "yasuo": "Yasuo",
    "yone": "Yone",
    "zed": "Zed",
    "shen": "Shen",
    "jhin": "Jhin",
    "darkin": "Darkin",
    "darkwill": "Darkwill",
    "karagül": "Karagül",
    "leviathan": "Leviathan"
}

# Dudaksılaşma (N-B / N-P) ve Türkçe Fonotaktik N/M Düzeltmeleri
PHONETIC_NM_RULES = [
    (r"\bcanbaz\b", "cambaz"),
    (r"\bçenber\b", "çember"),
    (r"\btenbel\b", "tembel"),
    (r"\btenbih\b", "tembih"),
    (r"\bsaklanbaç\b", "saklambaç"),
    (r"\bsünbül\b", "sümbül"),
    (r"\banbar\b", "ambar"),
    (r"\bmenbaa\b", "menba"),
    (r"\bçarşanba\b", "çarşamba"),
    (r"\bperşenbe\b", "perşembe"),
    (r"\btünbul\b", "tombul"),
]

# LoL Repliklerinde Whisper'ın Sık Yaptığı Akustik & Fonetik Kaymalar
LOL_ACOUSTIC_PHONETIC_FIXES = [
    (r"\bvasıtaya\b", "vastaya"),
    (r"\bvasıta\b", "vastaya"),
    (r"\bvasıtalar\b", "vastayalar"),
    (r"\bteşkürtün\b", "püskürtün"),
    (r"\bteşkürt\b", "püskürt"),
    (r"\bşurima\b", "Shurima"),
    (r"\bşurima'nın\b", "Shurima'nın"),
    (r"\bdemasya\b", "Demacia"),
    (r"\bdemacia'sın\b", "Demacialısın"),
    (r"\bdarkvil\b", "Darkwill"),
    (r"\bdarkwill'in\b", "Darkwill'in"),
    (r"\bümün eli\b", "Ölümün eli"),
    (r"\bümün\b", "Ölümün"),
    (r"\bfethi\b", "fetih için"),
    (r"\beğlerim\b", "yeğlerim"),
    (r"\bkaranlıkta sana bakar\b", "karanlık da sana bakar"),
    (r"\bkaranlıkta sana\b", "karanlık da sana"),
    (r"\bhükmetmek marifet\b", "tahta oturmak marifet"),
]

# Yaygın de/da ve ki bağlaç düzeltmeleri
CONJUNCTION_FIXES = [
    (r"\bbanada\b", "bana da"),
    (r"\bbende\b", "ben de"),
    (r"\bsende\b", "sen de"),
    (r"\bondada\b", "onda da"),
    (r"\bbizdede\b", "bizde de"),
    (r"\bsizdede\b", "sizde de"),
    (r"\böylede\b", "öyle de"),
    (r"\bböylede\b", "böyle de"),
    (r"\bdiyorki\b", "diyor ki"),
    (r"\bbilmembile\b", "bilmem bile"),
]

# Soru eki istisnaları (bu kelimelerin sonundaki mi/mu/mü soru eki değildir)
QUESTION_SUFFIX_EXCEPTIONS = {
    "gemi", "acemi", "sami", "hami", "semi", "azami", "hükmi", "resmi", "ilmi", "cismi",
    "kamu", "kumru", "ebru", "doğru", "kumlu", "türlü", "özlü", "sözlü"
}

QUESTION_WORDS = [
    "mı", "mi", "mu", "mü", "mısın", "misin", "musun", "müsün", "mıyız", "miyiz",
    "nasıl", "ne", "neden", "niye", "niçin", "kim", "nerede", "nereye", "nereden",
    "hangisi", "kaç", "ne zaman", "kimin", "kaçta"
]

EXCLAMATION_WORDS = [
    "aman", "hey", "dur", "kaç", "dikkat", "yaaa", "yaa", "ah", "tata", "hah",
    "hoppala", "vur", "bekle", "koş", "yeter", "hayır", "harika", "muhteşem",
    "aferin", "eyvah", "sakın", "defol"
]


def capitalize_turkish(s: str) -> str:
    """Türkçe karakter duyarlı ilk harf büyütme."""
    if not s:
        return s
    first = s[0]
    rest = s[1:]
    if first == 'i':
        first = 'İ'
    elif first == 'ı':
        first = 'I'
    else:
        first = first.upper()
    return first + rest


def normalize_turkish_vo(text: str) -> str:
    """
    Ham kullanıcı veya Whisper replik metnini temizler, düzeltir ve formatlar.
    """
    if not text:
        return ""

    t = text.strip()

    # Efekt veya sahne yönergeleri tek başına ise dokunma: [Kahkaha], [Sinyal...]
    if (t.startswith("[") and t.endswith("]")) or (t.startswith("(") and t.endswith(")")):
        return t

    # 1. Fazla boşlukları temizle
    t = re.sub(r"\s+", " ", t)

    # 2. Dudaksılaşma N/M kurallarını uygula (örn. canbaz -> cambaz)
    for pattern, repl in PHONETIC_NM_RULES:
        t = re.sub(pattern, repl, t, flags=re.IGNORECASE)

    # 3. LoL Akustik ve Fonetik Kaymaları Düzelt (örn. vasıtaya -> vastaya, teşkürtün -> püskürtün)
    for pattern, repl in LOL_ACOUSTIC_PHONETIC_FIXES:
        t = re.sub(pattern, repl, t, flags=re.IGNORECASE)

    # 4. Yaygın bağlaç düzeltmeleri
    for pattern, repl in CONJUNCTION_FIXES:
        t = re.sub(pattern, repl, t, flags=re.IGNORECASE)

    # 5. Ayrılmamış soru şahıs eklerini ayır (SADECE açık fiil/şahıs ekleri: mısınız, misiniz vb. Tek heceli mı/mi/mu/mü isim belirtme ekiyle karıştığı için ayrılmaz)
    words = t.split(" ")
    fixed_words = []
    for w in words:
        clean_w = re.sub(r"[^\wçğıöşüÇĞİÖŞÜ]", "", w.lower())
        matched = False
        if clean_w not in QUESTION_SUFFIX_EXCEPTIONS and len(clean_w) > 4:
            for suffix in ["mısınız", "misiniz", "musunuz", "müsünüz", "mısın", "misin", "musun", "müsün", "mıyız", "miyiz", "muyuz", "müyüz"]:
                if clean_w.endswith(suffix) and len(clean_w) > len(suffix) + 2:
                    base = w[:-len(suffix)]
                    fixed_words.append(base)
                    fixed_words.append(suffix)
                    matched = True
                    break
        if not matched:
            fixed_words.append(w)

    t = " ".join(fixed_words)

    # 5.b Yanlışlıkla ayrılmış Türkçe iyelik ve belirtme eklerini geri birleştir
    ACCUSATIVE_RESTORE_RULES = [
        (r"\bsaygıları mı\b", "saygılarımı"),
        (r"\bkalbi mi\b", "kalbimi"),
        (r"\bgünbatı mı\b", "günbatımı"),
        (r"\btorunu mu\b", "torunumu"),
        (r"\bkendi mi\b", "kendimi"),
        (r"\bgörke mi\b", "görkemi"),
        (r"\byaşa mı\b", "yaşamı"),
        (r"\bgördükleri mi\b", "gördüklerimi"),
        (r"\byolu mu\b", "yolumu"),
        (r"\badı mı\b", "adımı"),
        (r"\bboyu mu\b", "boyumu"),
        (r"\bcanı mı\b", "canımı"),
        (r"\baklı mı\b", "aklımı"),
        (r"\bgözü mü\b", "gözümü"),
        (r"\bhakkı mı\b", "hakkımı"),
        (r"\bsözü mü\b", "sözümü"),
    ]
    for pattern, repl in ACCUSATIVE_RESTORE_RULES:
        t = re.sub(pattern, repl, t, flags=re.IGNORECASE)

    # 6. LoL Özel İsimlerini Düzelt
    tokens = t.split(" ")
    normalized_tokens = []
    for tok in tokens:
        match = re.match(r"^([^\wçğıöşüÇĞİÖŞÜ]*)([\wçğıöşüÇĞİÖŞÜ]+)([^\wçğıöşüÇĞİÖŞÜ]*)$", tok)
        if match:
            prefix, core, suffix = match.groups()
            core_lower = core.lower()
            if core_lower in LOL_PROPER_NOUNS:
                core = LOL_PROPER_NOUNS[core_lower]
            normalized_tokens.append(f"{prefix}{core}{suffix}")
        else:
            normalized_tokens.append(tok)

    t = " ".join(normalized_tokens)

    # 7. Yanlış Title Case Düzeltmesi (örn. "Leviathan Bana Ait" -> "Leviathan bana ait")
    # Eğer ilk kelime hariç diğer kelimeler de büyükse ve özel isim değilse küçült
    words = t.split(" ")
    if len(words) > 1 and all(w and w[0].isupper() for w in words if len(w) > 1):
        clean_first = words[0]
        rest = []
        for w in words[1:]:
            w_clean = re.sub(r"[^\wçğıöşüÇĞİÖŞÜ]", "", w.lower())
            if w_clean in LOL_PROPER_NOUNS:
                rest.append(LOL_PROPER_NOUNS[w_clean] + w[len(w_clean):])
            else:
                rest.append(w.lower())
        t = clean_first + " " + " ".join(rest)

    # 8. İlk harfi büyük yap
    t = capitalize_turkish(t)

    # 6. Noktalama işaretleri ve cümle bitişi
    last_char = t[-1] if len(t) > 0 else ""
    valid_endings = {'.', '!', '?', '"', "'", ']', ')', '🎶', '🔔', '…'}

    if last_char not in valid_endings:
        t_lower = t.lower()
        has_question_word = any(re.search(rf"\b{re.escape(qw)}\b", t_lower) for qw in QUESTION_WORDS)
        has_exclamation_word = any(re.search(rf"\b{re.escape(ew)}\b", t_lower) for ew in EXCLAMATION_WORDS)

        if has_question_word:
            t += "?"
        elif has_exclamation_word:
            t += "!"
        else:
            t += "."

    return t


def phonetic_similarity(text1: str, text2: str) -> float:
    """
    İki Türkçe replik metninin fonetik akustik benzerliğini hesaplar (0.0 - 1.0).
    Türkçe ses denklikleri (n/m, c/ç, s/ş, g/ğ, o/ö, u/ü, ı/i) tolere edilir.
    """
    if not text1 or not text2:
        return 0.0

    import difflib

    def _phonetic_fold(s: str) -> str:
        s = s.lower().strip()
        s = re.sub(r"[^\wçğıöşüÇĞİÖŞÜ]", "", s)
        folds = {
            'ç': 'c', 'ş': 's', 'ğ': 'g', 'ö': 'o', 'ü': 'u', 'ı': 'i',
            'm': 'n'  # n/m akustik yakınsaması
        }
        for k, v in folds.items():
            s = s.replace(k, v)
        return s

    f1 = _phonetic_fold(text1)
    f2 = _phonetic_fold(text2)

    raw_ratio = difflib.SequenceMatcher(None, text1.lower().strip(), text2.lower().strip()).ratio()
    folded_ratio = difflib.SequenceMatcher(None, f1, f2).ratio()
    return max(raw_ratio, folded_ratio)
