# -*- coding: utf-8 -*-
"""
🎮 LoL Wwise Event Categorizer & Semantic Action Explainer
Riot Wwise Event isimlerini %100 deterministik olarak analiz eder.
Eylemleri kullanıcı dostu, açıklayıcı Türkçe ("yapınca", "edince", "kesince")
formatına dönüştürür ve mantıksal sıralama ağırlığı (sort weight) atar.
"""

import os
import re

# Bilinen LoL Şampiyonları
CHAMPIONS = [
    "Aatrox", "Ahri", "Akali", "Akshan", "Alistar", "Ambessa", "Amumu", "Anivia", "Annie", "Aphelios", "Ashe", "AurelionSol", "Azir",
    "Bard", "Belveth", "Blitzcrank", "Brand", "Braum", "Briar", "Caitlyn", "Camille", "Cassiopeia", "Chogath", "Corki", "Darius",
    "Diana", "Draven", "DrMundo", "Ekko", "Elise", "Evelynn", "Ezreal", "Fiddlesticks", "Fiora", "Fizz", "Galio", "Gangplank",
    "Garen", "Gnar", "Gragas", "Graves", "Gwen", "Hecarim", "Heimerdinger", "Hwei", "Illaoi", "Irelia", "Ivern", "Janna", "JarvanIV",
    "Jax", "Jayce", "Jhin", "Jinx", "KSante", "Kaisa", "Kalista", "Karma", "Karthus", "Kassadin", "Katarina", "Kayle", "Kayn",
    "Kennen", "KhaZix", "Kindred", "Kled", "KogMaw", "Leblanc", "LeeSin", "Leona", "Lillia", "Lissandra", "Lucian", "Lulu", "Lux",
    "Malphite", "Malzahar", "Maokai", "Melo", "MasterYi", "Milio", "MissFortune", "Mordekaiser", "Morgana", "Naafiri", "Nami",
    "Nasus", "Nautilus", "Neeko", "Nidalee", "Nilah", "Nocturne", "Nunu", "Olaf", "Orianna", "Ornn", "Pantheon", "Poppy", "Pyke",
    "Qiyana", "Quinn", "Rakan", "Rammus", "RekSai", "Rell", "Renata", "Renekton", "Rengar", "Riven", "Rumble", "Ryze", "Samira",
    "Sejuani", "Senna", "Seraphine", "Sett", "Shaco", "Shen", "Shyvana", "Singed", "Sion", "Sivir", "Skarner", "Smolder", "Sona",
    "Soraka", "Swain", "Sylas", "Syndra", "TahmKench", "Taliyah", "Talon", "Taric", "Teemo", "Thresh", "Tristana", "Trundle",
    "Tryndamere", "TwistedFate", "Twitch", "Udyr", "Urgot", "Varus", "Vayne", "Veigar", "Velkoz", "Vex", "Vi", "Viego", "Viktor",
    "Vladimir", "Volibear", "Warwick", "Wukong", "Xayah", "Xerath", "XinZhao", "Yasuo", "Yone", "Yorick", "Yuumi", "Zac", "Zed",
    "Zeri", "Ziggs", "Zilean", "Zoe", "Zyra"
]

CHAMP_REGEX = re.compile(r'(' + '|'.join(CHAMPIONS) + r')', re.IGNORECASE)

# Resmi League of Legends Türkçe Eşya (Item) ve Mağaza Sözlüğü
# Riot Wwise Event sonekleri ve sayısal Item ID'leri -> Resmi TR Eşya Adı
LOL_ITEMS_TR_MAP = {

    # Sayısal Riot Item ID'leri
    "1054": "Doran'ın Kalkanı",
    "1055": "Doran'ın Kılıcı",
    "1056": "Doran'ın Yüzüğü",
    "3001": "Cehennem Maskesi",
    "3006": "Savaşçı Çizmeleri",
    "3025": "Buzdoğan Eldiveni",
    "3026": "Koruyucu Melek",
    "3035": "Son Fısıltı",
    "3046": "Hayalet Dansçı",
    "3068": "Günateşi Pelerini",
    "3072": "Kanasusamış",
    "3083": "Warmog'un Zırhı",
    "3085": "Runaan'ın Kasırgası",
    "3087": "Statikk Hançer",
    "3094": "Bombardıman Topu",
    "3102": "Banshee'nin Duvağı",
    "3123": "Celladın Çağrısı",
    "3136": "Liandry'nin Eziyeti",
    "3139": "Cıva Yatağan",
    "3151": "Liandry'nin Eziyeti",
    "3153": "Mahvolmuş Kralın Kılıcı",
    "3157": "Zhonya'nın Kumsaati",
    "3158": "Ionia Çizmeleri",
    "3508": "Canbiçen",

    # İngilizce Wwise Eşya Anahtarları (Küçük harf normalize edilmiş)
    "abyssalmask": "Cehennem Maskesi",
    "aegisofthelegion": "Ordu Kalkanı",
    "aegisofthelegions": "Ordu Kalkanı",
    "amplifyingtome": "Kuvvet Kitabı",
    "archangelsstaff": "Başmelek Asası",
    "bfs": "A.M.K. Kılıcı",
    "bfsword": "A.M.K. Kılıcı",
    "badsheesveil": "Banshee'nin Duvağı",
    "bandleglassmirror": "Bandle Camı Ayna",
    "bansheesveil": "Banshee'nin Duvağı",
    "berserkersgreaves": "Savaşçı Çizmeleri",
    "beserkergreaves": "Savaşçı Çizmeleri",
    "beserkersgreaves": "Savaşçı Çizmeleri",
    "blackcleaver": "Kara Balta",
    "bladeoftheruinedking": "Mahvolmuş Kralın Kılıcı",
    "bloodthirster": "Kanasusamış",
    "boots": "Çizme",
    "bootsofswiftness": "Atiklik Çizmeleri",
    "bootstiertwo": "Gelişmiş Çizme",
    "caulfieldswarhammer": "Caulfield'ın Savaş Çekici",
    "celestialopposition": "Göksel Muhalefet",
    "clotharmor": "Dokuma Zırh",
    "deadmansplate": "Ölü Adamın Zırhı",
    "demonicembrace": "Uğursuz Koruma",
    "doransshield": "Doran'ın Kalkanı",
    "doransblade": "Doran'ın Kılıcı",
    "doransring": "Doran'ın Yüzüğü",
    "duskbladeofdraktharr": "Draktharr'ın Gece Kılıcı",
    "edgeofnight": "Gecenin Kıyısı",
    "elixerofsorcery": "Büyücülük İksiri",
    "elixirofsorcery": "Büyücülük İksiri",
    "elixirofiron": "Demir İksiri",
    "elixirofwrath": "Gazap İksiri",
    "elixir": "İksir",
    "essencereaver": "Canbiçen",
    "evenshroud": "Akşam Kefeni",
    "everfrost": "Hepbuz",
    "executionerscalling": "Celladın Çağrısı",
    "faeriecharm": "Peri Tılsımı",
    "fiendhunterbolts": "İblisavcısı Okları",
    "frostfiregauntlet": "Buzateşi Eldiveni",
    "frozenheart": "Donmuş Yürek",
    "giantslayer": "Dev Katili",
    "giantsbelt": "Dev Kemeri",
    "glacialbuckler": "Buzul Kalkan",
    "guardianangel": "Koruyucu Melek",
    "guardianangelr": "Koruyucu Melek",
    "guardiansorb": "Muhafız Küresi",
    "guinsoosrageblade": "Guinsoo'nun Hiddeti",
    "healthpotion": "Can İksiri",
    "hextechrocketbelt": "Hextech Roketkemer",
    "infinityedge": "Ebedi Kılıç",
    "ionianboots": "Ionia Çizmeleri",
    "ionianbootsoflucidity": "Ionia Çizmeleri",
    "kindlegem": "Alazcevher",
    "lastwhisper": "Son Fısıltı",
    "liandrysanguish": "Liandry'nin Istırabı",
    "liandrystorment": "Liandry'nin Eziyeti",
    "lichbane": "Lich Boğan",
    "locketoftheironsolari": "Demir Solari'nin Broşu",
    "lorddominiksregards": "Dominik Efendi'nin Hürmetleri",
    "ludenstempest": "Luden'in Çığlığı",
    "mawofmalmortius": "Malmortius'un Ağzı",
    "mejaissoulstealer": "Mejai'nin Ruhyiyeni",
    "mercurialscimitar": "Cıva Yatağan",
    "mercurystreads": "Merkür'ün Adımları",
    "mikaelsblessing": "Mikael'in Lütfu",
    "morellonomicon": "Morellonomikon",
    "nashorstooth": "Nashor'un Dişi",
    "navoriquickblades": "Navori Seribıçakları",
    "needlesslylargerod": "Aşırı Büyük Sopa",
    "oraclelens": "Kâhin Merceği",
    "phantomdancer": "Hayalet Dansçı",
    "porosnax": "Poro Çerezi",
    "potion": "Can İksiri",
    "quicksilversash": "Cıva Kuşağı",
    "rabadonsdeathcap": "Rabadon'un Şapkası",
    "randuinsomen": "Randuin'in Alameti",
    "rapidfirecannon": "Bombardıman Topu",
    "ravenoushydra": "Vahşi Hydra",
    "redemption": "Kefaret",
    "relicshield": "Yadigâr Kalkan",
    "rubycrystal": "Yakut Kristal",
    "runaanshurricane": "Runaan'ın Kasırgası",
    "rylaiscrystalscepter": "Rylai'nin Kristal Asası",
    "sapphirecrystal": "Safir Kristal",
    "serpentsfang": "Yılan Dişi",
    "sorcerersshoes": "Sihirbaz Pabuçları",
    "spectrescowl": "Hayalet Pelerini",
    "spiritvisage": "Ruh Gömleği",
    "statikkshiv": "Statikk Hançer",
    "steraksgage": "Sterak'ın Güvencesi",
    "stormrazor": "Fırtınabiçen",
    "stridebreaker": "Hızkesen",
    "sunfireaegis": "Günateşi Kalkanı",
    "tearofthegoddess": "Tanrıça'nın Gözyaşı",
    "thornmail": "Çivili Zırh",
    "titanichydra": "Haşmetli Hydra",
    "trinityforce": "Üçlü Kuvvet",
    "turbochemtank": "Turbo Kimya Tankı",
    "voidstaff": "Hiçlik Değneği",
    "ward": "Totem (Ward)",
    "warmogsarmor": "Warmog'un Zırhı",
    "youmuusghostblade": "Youmuu'nun Hayaletkılıcı",
    "zhonyashourglass": "Zhonya'nın Kumsaati",
}


def resolve_item_event_turkish(event_name: str) -> str:
    """
    Riot Wwise eşya / mağaza / totem / iksir event adını resmi Türkçe eşya adıyla açıklar.
    Örn:
      Play_vo_Kalista_BuyItem2DInfinityEdge -> 'Ebedi Kılıç Satın Alınca'
      Play_vo_Azir_BuyItem2DZhonyasHourglass -> 'Zhonya'nın Kumsaati Satın Alınca'
      Play_vo_Kalista_UseItem2DWard -> 'Totem (Ward) Yerleştirince'
      Play_vo_Kalista_BuyItem2D3157 -> 'Zhonya'nın Kumsaati Satın Alınca'
    Eğer eşya/mağaza eventi değilse '' (boş string) döner.
    """
    if not event_name:
        return ""
    ev = str(event_name)
    ev_lower = ev.lower()

    # Özel Ornn demirhane ve takım eşya replikleri
    if 'forgeitem' in ev_lower:
        return "Demirhanede Eşya Döverken"
    if 'finishforging' in ev_lower:
        return "Eşya Dövmeyi Tamamlayınca"
    if 'allypurchasesitem' in ev_lower:
        return "Takım Arkadaşı Eşya Satın Alınca"
    if 'kill3dward' in ev_lower or 'kill2dward' in ev_lower or ('kill' in ev_lower and 'ward' in ev_lower):
        return "Rakip Totemi (Ward) Kırınca"
    if 'nearby3duseitemhealthpotenemy' in ev_lower:
        return "Rakip Yakında Can İksiri İçince"
    if 'shop2dopen' in ev_lower or 'shop3dopen' in ev_lower or ('shop' in ev_lower and 'open' in ev_lower):
        return "Mağazayı Açınca"
    if 'shop2dclose' in ev_lower or 'shop3dclose' in ev_lower or ('shop' in ev_lower and 'close' in ev_lower):
        return "Mağazayı Kapatınca"
    if 'itemhurricanejinxattack' in ev_lower:
        return "Runaan'ın Kasırgası ile Saldırırken"

    # BuyItem / GiftedItem / Purchase kalıbı: BuyItem2D<Key>, BuyItem3D<Key>, BuyItem<Key>
    m_buy = re.search(r'(?:BuyItem|GiftedItem|Purchase)(?:Group)?(?:2D|3D)?_?([A-Za-z0-9]+)', ev, re.IGNORECASE)
    if m_buy:
        raw_key = m_buy.group(1)
        # Sondaki varyasyon/OnBuffCast eklerini temizle
        raw_key = re.sub(r'(?:_OnBuffCast|_cast3D|_cast2D)$', '', raw_key, flags=re.IGNORECASE)
        key_low = raw_key.lower()
        if key_low in ('general', 'default', ''):
            return "Mağazadan Eşya Satın Alınca"
        item_tr = LOL_ITEMS_TR_MAP.get(key_low)
        if not item_tr:
            # CamelCase'i okunaklı hale getir
            pretty = re.sub(r'([a-z])([A-Z])', r'\1 \2', raw_key).strip()
            item_tr = pretty
        if 'gifteditem' in ev_lower:
            return f"{item_tr} Eşyası Alınca"
        return f"{item_tr} Satın Alınca"

    # UseItem kalıbı: UseItem2D<Key>, UseItem3D<Key>, UseItemGroup2D<Key>
    m_use = re.search(r'UseItem(?:Group)?(?:2D|3D)?_?([A-Za-z0-9]+)', ev, re.IGNORECASE)
    if m_use:
        raw_key = m_use.group(1)
        key_low = raw_key.lower()
        if 'ward' in key_low:
            return "Totem (Ward) Yerleştirince"
        if 'guardianangel' in key_low:
            return "Koruyucu Melek ile Yeniden Dirilince"
        if 'porosnax' in key_low:
            return "Poro Çerezi Verince"
        if 'oraclelens' in key_low:
            return "Kâhin Merceği Kullanınca"
        if 'healthpotion' in key_low or key_low == 'potion':
            return "Can İksiri İçince"
        if 'elixirofiron' in key_low:
            return "Demir İksiri İçince"
        if 'elixir' in key_low:
            return "İksir İçince"
        item_tr = LOL_ITEMS_TR_MAP.get(key_low)
        if not item_tr:
            item_tr = re.sub(r'([a-z])([A-Z])', r'\1 \2', raw_key).strip()
        return f"{item_tr} Kullanınca"

    return ""


def is_item_or_shop_event(event_name: str, action_name: str = "") -> bool:
    """
    Bir eventin veya Türkçe eylem adının Eşya / Mağaza / İksir / Totem ile ilgili olup olmadığını
    %100 deterministik olarak döner. Eşya isimlerinin ('GuardianAngel' -> 'Diana',
    'DemonicEmbrace' -> 'Ace', 'Navori Seribıçakları' -> 'Seri', 'PhantomDancer' -> 'Dance')
    diğer kategorilere sızmasını kesin olarak engeller.
    """
    ev = str(event_name or "")
    ev_low = ev.lower()
    act_low = str(action_name or "").lower()
    if resolve_item_event_turkish(ev):
        return True
    if any(k in ev_low for k in [
        'buyitem', 'useitem', 'gifteditem', 'forgeitem', 'finishforging',
        'allypurchasesitem', 'shop2d', 'shop3d', 'purchase', 'porosnax',
        'itemhurricane', 'kill3dward', 'kill2dward'
    ]):
        return True
    if any(k in act_low for k in [
        'satın alınca', 'eşya alınca', 'eşya döv', 'mağazayı', 'mağazadan',
        'iksir içince', 'iksiri içince', 'totem (ward) yerleştirince',
        'totemi (ward) kırınca', 'poro çerezi', 'kâhin merceği kullanınca',
        'koruyucu melek ile yeniden dirilince'
    ]):
        return True
    return False



# League of Legends Resmi Bölgeleri, Fraksiyonları ve Irksal Karşılaşmalar
FACTIONS_TR_MAP = {
    "ionia": "Ionia",
    "noxus": "Noxus",
    "demacia": "Demacia",
    "freljord": "Freljord",
    "piltover": "Piltover",
    "zaun": "Zaun",
    "shurima": "Shurima",
    "bilgewater": "Bilgewater",
    "targon": "Targon",
    "mounttargon": "Targon",
    "shadowisles": "Gölge Adalar",
    "shadowisle": "Gölge Adalar",
    "bandlecity": "Bandle Şehri",
    "bandle": "Bandle Şehri",
    "yordle": "Yordle",
    "void": "Hiçlik",
    "darkin": "Darkin",
    "vastaya": "Vastaya",
    "ascended": "Yükselmiş"
}


def parse_event_faction(event_name, champ_name=""):
    """
    Event adından bölgesel/fraksiyonel karşılaşma varsa (Ionia, Noxus, Demacia vb.) Türkçe bölge adını döner.
    Bölgeler şampiyon DEĞİLDİR; bu yüzden parse_event_target içinde döndürülmez!
    """
    if not event_name or is_item_or_shop_event(event_name):
        return None
    if not champ_name:
        m_self = re.match(r'^(?:Play_)?vo_([A-Za-z]+?)(?:Skin\d+)?_', event_name, re.IGNORECASE)
        if m_self:
            champ_name = m_self.group(1)
    cleaned_for_target = re.sub(re.escape(champ_name) + r'(skin\d+)?', '', event_name, flags=re.IGNORECASE) if champ_name else event_name
    for fac_key, fac_label in FACTIONS_TR_MAP.items():
        if re.search(r'(?:firstencounter|encounter|enemy|ally|kill|taunt|joke)(?:3d|2d)?_?' + re.escape(fac_key), cleaned_for_target, re.IGNORECASE) or re.search(r'(?:^|[_0-9])' + re.escape(fac_key) + r'(?=$|[_0-9]|[A-Z])', cleaned_for_target, re.IGNORECASE):
            return fac_label
    return None


def parse_event_target(event_name, champ_name=""):
    """
    Event adından YALNIZCA gerçek hedef şampiyonu ve hedef kostüm numarasını çıkarır.
    Bölgeler (Ionia, Noxus vb.) şampiyon olmadığı için burada döndürülmez; böylece
    spesifik şampiyon atıflarının (Bard..Zed) arasına sızmaz ve sahte şampiyon fotosu açmaz!
    Dönüş: (target_champ, target_skin_num) veya (None, 0)
    """
    if not event_name:
        return None, 0
    # Eşya/Mağaza eventleri ASLA hedef şampiyon olamaz!
    if is_item_or_shop_event(event_name):
        return None, 0

    if not champ_name:
        m_self = re.match(r'^(?:Play_)?vo_([A-Za-z]+?)(?:Skin\d+)?_', event_name, re.IGNORECASE)
        if m_self:
            champ_name = m_self.group(1)
    champ_lower = champ_name.lower() if champ_name else ""
    cleaned_for_target = re.sub(re.escape(champ_name) + r'(skin\d+)?', '', event_name, flags=re.IGNORECASE) if champ_name else event_name

    # Standart LoL Şampiyonları
    for ch in sorted(CHAMPIONS, key=len, reverse=True):
        if ch.lower() == champ_lower:
            continue
        m = re.search(r'(' + re.escape(ch) + r')(?:Skin0*([0-9]{1,2}))?', cleaned_for_target, re.IGNORECASE)
        if m:
            matched_str = m.group(1)
            start_idx = m.start(1)
            end_idx = m.end(0)
            prev_char = cleaned_for_target[start_idx - 1] if start_idx > 0 else '_'
            next_char = cleaned_for_target[end_idx] if end_idx < len(cleaned_for_target) else '_'
            if prev_char.isalpha() and prev_char.islower() and matched_str[0].islower():
                continue
            if next_char.isalpha() and next_char.islower():
                continue
            t_skin = int(m.group(2)) if m.group(2) else 0
            return ch, t_skin

    return None, 0


def parse_event_info(event_name, champ_name=""):
    """
    Riot Wwise Event ismini analiz eder ve hangi oyun içi olayda çaldığını
    kristal netliğinde açıklayıcı Türkçe eylem adına dönüştürür.
    Dönüş: (kategori_id, aciklayici_turkce_ad)
    """
    ev = event_name
    ev_lower = event_name.lower()
    champ_lower = champ_name.lower() if champ_name else "sampiyon"

    # -------------------------------------------------------------
    # 0. EŞYA / MARKET ALIMLARI VE KULLANIMLARI (EN YÜKSEK ÖNCELİK!)
    # -------------------------------------------------------------
    item_action_tr = resolve_item_event_turkish(ev)
    if item_action_tr:
        return "6_Esya_Alimi_ve_Magaza", item_action_tr
    if 'buyitem' in ev_lower or 'useitem' in ev_lower or 'gifteditem' in ev_lower or 'shop' in ev_lower or 'purchase' in ev_lower:
        return "6_Esya_Alimi_ve_Magaza", "Mağazadan Eşya Satın Alınca"

    matched_target, target_skin_num = parse_event_target(ev, champ_name)
    target_label = f"{matched_target} (Kostüm {target_skin_num})" if (matched_target and target_skin_num > 0) else matched_target

    # -------------------------------------------------------------
    # 1-A. HEDEF ŞAMPİYONA ÖZEL ATIFLAR VE ETKİLEŞİMLER
    # -------------------------------------------------------------
    if matched_target and matched_target.lower() != champ_lower:
        if 'kill' in ev_lower or 'firstblood' in ev_lower:
            return "5_Ozel_Karsilasmalar_ve_Atiflar", f"{target_label} Katledilince"
        elif 'tauntresponse' in ev_lower:
            return "5_Ozel_Karsilasmalar_ve_Atiflar", f"{target_label} Kışkırtmasına Yanıt Verirken"
        elif 'jokeresponse' in ev_lower:
            return "5_Ozel_Karsilasmalar_ve_Atiflar", f"{target_label} Şakasına Yanıt Verirken"
        elif 'taunt' in ev_lower:
            return "5_Ozel_Karsilasmalar_ve_Atiflar", f"{target_label} Kışkırtılınca (CTRL+2)"
        elif 'joke' in ev_lower:
            return "5_Ozel_Karsilasmalar_ve_Atiflar", f"{target_label} Şaka Yapılınca (CTRL+1)"
        elif 'ally' in ev_lower:
            return "5_Ozel_Karsilasmalar_ve_Atiflar", f"Dost {target_label} ile Karşılaşınca"
        elif 'enemy' in ev_lower or 'firstencounter' in ev_lower:
            return "5_Ozel_Karsilasmalar_ve_Atiflar", f"Düşman {target_label} ile İlk Karşılaşınca"
        elif 'move' in ev_lower and ('near' in ev_lower or 'with' in ev_lower):
            return "5_Ozel_Karsilasmalar_ve_Atiflar", f"{target_label} ile Yan Yana Yürürken"
        elif 'recall' in ev_lower:
            return "5_Ozel_Karsilasmalar_ve_Atiflar", f"{target_label} ile Birlikte Üsse Dönerken (Recall)"
        elif 'spell' in ev_lower or 'cast' in ev_lower or 'hit' in ev_lower:
            return "5_Ozel_Karsilasmalar_ve_Atiflar", f"{target_label} Üzerinde Yetenek Kullanınca"
        elif 'assist' in ev_lower:
            return "5_Ozel_Karsilasmalar_ve_Atiflar", f"{target_label} Katledilirken Asist Yapınca"
        else:
            return "5_Ozel_Karsilasmalar_ve_Atiflar", f"{target_label} ile Özel Etkileşime Girince"

    # -------------------------------------------------------------
    # 1-B. BÖLGESEL / FRAKSİYONEL KARŞILAŞMALAR (Ionia, Noxus, Demacia vb.)
    # Şampiyon atıflarının arasına sızmaz ve sahte şampiyon fotoğrafı açmaz!
    # -------------------------------------------------------------
    matched_faction = parse_event_faction(ev, champ_name)
    if matched_faction:
        fac_label = f"{matched_faction} Şampiyonu"
        if 'kill' in ev_lower:
            return "5_Ozel_Karsilasmalar_ve_Atiflar", f"{fac_label} Katledilince"
        elif 'taunt' in ev_lower:
            return "5_Ozel_Karsilasmalar_ve_Atiflar", f"{fac_label} Kışkırtılınca (CTRL+2)"
        elif 'joke' in ev_lower:
            return "5_Ozel_Karsilasmalar_ve_Atiflar", f"{fac_label} Şaka Yapılınca (CTRL+1)"
        elif 'ally' in ev_lower:
            return "5_Ozel_Karsilasmalar_ve_Atiflar", f"Dost {fac_label} ile Karşılaşınca"
        elif 'enemy' in ev_lower or 'firstencounter' in ev_lower or 'encounter' in ev_lower:
            return "5_Ozel_Karsilasmalar_ve_Atiflar", f"Düşman {fac_label} ile İlk Karşılaşınca"
        else:
            return "5_Ozel_Karsilasmalar_ve_Atiflar", f"{fac_label} ile Karşılaşınca"

    # -------------------------------------------------------------
    # 2. KATLETME VE ZAFER ZİNCİRİ (First Blood, Double, Triple, Quadra, Penta, Ace)
    # -------------------------------------------------------------
    if 'first' in ev_lower and 'blood' in ev_lower:
        return "5_Ozel_Karsilasmalar_ve_Atiflar", "İlk Kanı Akıtınca (First Blood)"

    if 'penta' in ev_lower:
        return "5_Ozel_Karsilasmalar_ve_Atiflar", "Beşte Beş (Penta) Atınca"

    if 'quadra' in ev_lower:
        return "5_Ozel_Karsilasmalar_ve_Atiflar", "Dörtte Dört Atınca (Quadra Kill)"

    if 'triple' in ev_lower:
        return "5_Ozel_Karsilasmalar_ve_Atiflar", "Üçte Üç Alınca (Triple Kill)"

    if 'double' in ev_lower:
        return "5_Ozel_Karsilasmalar_ve_Atiflar", "İkide İki Yapınca (Double Kill)"

    if re.search(r'(?:^|[_0-9]|kill)ace(?:$|[_0-9]|3d|2d)', ev_lower):
        return "5_Ozel_Karsilasmalar_ve_Atiflar", "Katliam Yapınca (Ace)"

    if 'spree' in ev_lower or 'streak' in ev_lower:
        return "5_Ozel_Karsilasmalar_ve_Atiflar", "Katletme Serisi Yakalayınca (Killing Spree)"

    if 'shutdown' in ev_lower:
        return "5_Ozel_Karsilasmalar_ve_Atiflar", "Rakibin Serisini Durdurunca (Shutdown)"

    # -------------------------------------------------------------
    # 3. DESTANSI CANAVARLAR VE HARİTA HEDEFLERİ (Baron, Vadi, Ejder, Kule)
    # -------------------------------------------------------------
    if 'baron' in ev_lower or 'nashor' in ev_lower:
        return "5_Ozel_Karsilasmalar_ve_Atiflar", "Baron Nashor'u Katledince"

    if 'herald' in ev_lower or 'rift' in ev_lower or 'vadi' in ev_lower:
        return "5_Ozel_Karsilasmalar_ve_Atiflar", "Vadi'nin Alameti'ni Alınca"

    if 'dragon' in ev_lower or 'drake' in ev_lower or 'elder' in ev_lower:
        if 'elder' in ev_lower:
            return "5_Ozel_Karsilasmalar_ve_Atiflar", "Kadim Ejderha'yı Katledince"
        return "5_Ozel_Karsilasmalar_ve_Atiflar", "Ejderha Katledince"

    if 'grub' in ev_lower or 'voidgrub' in ev_lower or 'kurtcuk' in ev_lower:
        return "5_Ozel_Karsilasmalar_ve_Atiflar", "Hiçlik Kurtçuklarını Kesince"

    if 'turret' in ev_lower or 'tower' in ev_lower or 'structure' in ev_lower:
        return "5_Ozel_Karsilasmalar_ve_Atiflar", "Kule veya Yapı Yıkınca"

    if 'inhib' in ev_lower:
        return "5_Ozel_Karsilasmalar_ve_Atiflar", "İnhibitör Yıkınca"

    # Genel Karşılaşmalar (Hedefsiz - Genel Rakiple İlk Karşılaşma)
    if 'firstencounter' in ev_lower or 'encounter' in ev_lower:
        if 'ally' in ev_lower:
            return "5_Ozel_Karsilasmalar_ve_Atiflar", "Dost Şampiyonla İlk Karşılaşınca"
        return "5_Ozel_Karsilasmalar_ve_Atiflar", "Düşman Şampiyonla İlk Karşılaşınca"

    if 'kill' in ev_lower:
        return "5_Ozel_Karsilasmalar_ve_Atiflar", "Düşman Katledince (Kill)"

    if 'kill' in ev_lower:
        return "5_Ozel_Karsilasmalar_ve_Atiflar", "Düşman Katledince (Kill)"

    # -------------------------------------------------------------
    # 4. YETENEKLER (Q, W, E, R / Ulti)
    # -------------------------------------------------------------
    # Q Yeteneği (Örn: KalistaMysticShot_cast3D, SpellQ, Q_cast)
    if re.search(r'q_cast|spell_?q|spell3dq|mysticshot|' + re.escape(champ_lower) + r'q', ev_lower):
        if 'hit' in ev_lower:
            return "1_Q_Yetenegi", "Q Yeteneğini İsabet Ettirince"
        if 'kill' in ev_lower:
            return "1_Q_Yetenegi", "Q Yeteneğiyle Düşman Katledince"
        return "1_Q_Yetenegi", "Q Yeteneğini Kullanınca"

    # W Yeteneği
    if re.search(r'w_cast|w2_cast|spell_?w|spell3dw|' + re.escape(champ_lower) + r'w(?:_|$)', ev_lower):
        if 'hit' in ev_lower:
            return "2_W_Yetenegi", "W Yeteneğini İsabet Ettirince"
        return "2_W_Yetenegi", "W Yeteneğini Kullanınca"

    # E Yeteneği (Örn: KalistaExpunge_cast3D, KalistaVOEHighStack, SpellE, E_cast)
    if re.search(r'e_cast|spell_?e|spell3de|expunge|voehighstack|' + re.escape(champ_lower) + r'e(?:_|$)', ev_lower):
        if 'hit' in ev_lower:
            return "3_E_Yetenegi", "E Yeteneğini İsabet Ettirince"
        return "3_E_Yetenegi", "E Yeteneğiyle Hamle Yapınca / Atılınca"

    # R Yeteneği (Ulti) (Örn: KalistaRMis_cast3D, KalistaVORNormal, KalistaVORAllyLowHealth, SpellR)
    if re.search(r'r_cast|rmis_cast|vornormal|vorally|spell_?r|spell3dr|' + re.escape(champ_lower) + r'r(?:_|$)|ult', ev_lower):
        if 'hit' in ev_lower:
            return "4_R_Ulti", "R Ulti Yeteneğini İsabet Ettirince"
        if 'kill' in ev_lower:
            return "4_R_Ulti", "R Ulti Yeteneğiyle Düşman Katledince"
        return "4_R_Ulti", "R Ulti Yeteneğini Kullanınca"

    # -------------------------------------------------------------
    # 5. AĞIZ SES EFEKTLERİ, HOMURTULAR VE EFORLAR (SFX)
    # -------------------------------------------------------------
    is_effort = any(k in ev_lower for k in ['effort', 'grunt', 'exertion', 'breathe', 'breath', 'pant', 'groan', 'gasp', 'pain', 'hit_vo', 'cast_effort', 'attack_effort', 'spell_effort', 'vo_effort'])
    if is_effort:
        if 'spell' in ev_lower or any(s in ev_lower for s in ['q_', 'w_', 'e_', 'r_']):
            return "11_Efektler_ve_Homurtular", "Yetenek Kullanırken Bağırma / Efor (SFX)"
        elif 'attack' in ev_lower:
            return "11_Efektler_ve_Homurtular", "Normal Saldırırken Efor / Hıkırtı (SFX)"
        elif 'death' in ev_lower or 'pain' in ev_lower:
            return "11_Efektler_ve_Homurtular", "Hasar Alınca Acı İniltisi (SFX)"
        else:
            return "11_Efektler_ve_Homurtular", "Genel Karakter Eforu / Homurtu (SFX)"

    # -------------------------------------------------------------
    # 6. EŞYA / MARKET ALIMLARI VE KULLANIMLARI (Türkçe Eşya Sözlüğü)
    # -------------------------------------------------------------
    item_action_tr = resolve_item_event_turkish(ev)
    if item_action_tr:
        return "6_Esya_Alimi_ve_Magaza", item_action_tr
    if 'item' in ev_lower or 'buy' in ev_lower or 'shop' in ev_lower or 'purchase' in ev_lower:
        return "6_Esya_Alimi_ve_Magaza", "Mağazadan Eşya Satın Alınca"

    # -------------------------------------------------------------
    # 7. DUYGULAR / EMOTES (Şaka, Kışkırtma, Kahkaha, Dans)
    # -------------------------------------------------------------
    if 'joke' in ev_lower:
        return "7_Saka_Kiskirtma_Kahkaha", "Şaka Yapınca (CTRL+1 Joke)"

    if 'taunt' in ev_lower:
        return "7_Saka_Kiskirtma_Kahkaha", "Kışkırtınca (CTRL+2 Taunt)"

    if 'laugh' in ev_lower or 'gule' in ev_lower:
        return "7_Saka_Kiskirtma_Kahkaha", "Kahkaha Atarken (CTRL+4 Laugh)"

    if 'dance' in ev_lower:
        return "7_Saka_Kiskirtma_Kahkaha", "Dans Ederken (CTRL+3 Dance)"

    # -------------------------------------------------------------
    # 8. DOĞUŞ, DÖNÜŞ VE ÖLÜM
    # -------------------------------------------------------------
    if 'intro' in ev_lower or 'matchstart' in ev_lower or 'gamestart' in ev_lower:
        return "8_Donus_ve_Olum", "Vadide İlk Doğuşta / Oyun Başlayınca"
    if 'respawn' in ev_lower or 'revive' in ev_lower:
        return "8_Donus_ve_Olum", "Yeniden Canlanınca (Respawn)"
    if 'recall' in ev_lower:
        return "8_Donus_ve_Olum", "Üsse Dönüş Yaparken (Recall B)"
    if 'death' in ev_lower or 'die' in ev_lower:
        return "8_Donus_ve_Olum", "Can Verirken / Ölürken (Ölüm)"

    # -------------------------------------------------------------
    # 9. HAREKET VE SALDIRI
    # -------------------------------------------------------------
    if 'move' in ev_lower:
        if 'long' in ev_lower:
            return "9_Hareket_ve_Saldiri", "Uzun Mesafeli Yürüyüş Yaparken"
        return "9_Hareket_ve_Saldiri", "Haritada Yürürken / Hareket Ederken"
    if 'attack' in ev_lower or 'crit' in ev_lower or 'basicattack' in ev_lower:
        if 'crit' in ev_lower:
            return "9_Hareket_ve_Saldiri", "Kritik Vuruş Yapınca"
        return "9_Hareket_ve_Saldiri", "Normal Saldırı Yaparken / Dövüşürken"
    if 'level' in ev_lower or 'lvl' in ev_lower:
        return "10_Genel_Replikler", "Seviye Atlayınca (Level Up)"

    # Varsayılan Genel Replik
    return "10_Genel_Replikler", "Genel Karakter Repliği"


def get_event_sort_weight(cat_id, action_name, raw_event, champ_name=""):
    """
    Eylemlerin YouTube izleyici tutma (retention) ve hikaye akışına göre
    mükemmel sırayla dizilmesi için sıralama ağırlığı döner.
    Öncelik Sırası:
      1. Karakter Atıfları (İlk Karşılaşma -> Dost -> Kışkırtma/Şaka -> Katletme) [5..95]
      2. Destansı Katletmeler & Zafer Zinciri (İlk Kan -> Penta -> Baron -> Ejderha -> Kule) [110..195]
      3. Seçim, Yasaklama & Vadide İlk Doğuş (Intro / GameStart) [210..250]
      4. Genel Replikler, Seviye Atlama & Duygular (Şaka, Kışkırtma, Dans, Kahkaha) [310..440]
      5. Eşya & Mağaza Alımları (Özel eşya replikleri önce, genel mağaza sonra) [450..490]
      6. Dövüş & Yetenek Replikleri (Q -> W -> E -> R Ulti -> Normal Saldırı) [510..580]
      7. Haritada Gezerken / Hareket & Üsse Dönüş (Recall) / Yeniden Canlanma [610..680]
      8. Ölüm & Ses Efektleri / Homurtular / Saldırı Eforları (SFX) [880..950]
    """
    ev_lower = (str(raw_event or '') + " " + str(action_name or '')).lower()
    is_item_event = bool(
        cat_id == "6_Esya_Alimi_ve_Magaza" or
        is_item_or_shop_event(str(raw_event or ''), str(action_name or ''))
    )

    # 0-A. EŞYA & MAĞAZA ALIMLARI (En başta yakalanır ki Navori Seribıçakları 'seri',
    # Uğursuz Koruma 'ace', Koruyucu Melek 'diana', Hayalet Dansçı 'dance',
    # Ölümün Dansı 'death' yüzünden başka ağırlıklara ASLA sızmasın!)
    if is_item_event:
        if 'mağazadan eşya satın alınca' in ev_lower or 'mağazayı' in ev_lower or 'general' in ev_lower:
            return 485
        return 460

    tgt_champ, _ = parse_event_target(str(raw_event or ''), champ_name)

    # 0-B. ÖLÜM / CAN VERİRKEN VE TÜM SES EFEKTLERİ / HOMURTULAR (SFX) DAİMA EN SONDA!
    if cat_id == "11_Efektler_ve_Homurtular" or any(k in ev_lower for k in ['sfx', 'bağırma', 'efor', 'homurtu', 'hıkırtı', 'effort', 'grunt', 'exertion', 'pain', 'inilti']):
        return 920
    if any(k in ev_lower for k in ['ölürken', 'ölüm', 'can verirken', 'death3d', 'death2d', '_death', 'allydeath']):
        return 880

    # 1. KARAKTER ATIFLARI (Target Champion dolu olanlar EN BAŞTA!)
    if tgt_champ:
        if 'düşman' in ev_lower and 'karşılaş' in ev_lower:
            return 10
        if 'dost' in ev_lower and 'karşılaş' in ev_lower:
            return 20
        if 'karşılaş' in ev_lower or 'firstencounter' in ev_lower or 'encounter' in ev_lower:
            return 25
        if 'kışkırt' in ev_lower or 'taunt' in ev_lower:
            return 35
        if 'şaka' in ev_lower or 'joke' in ev_lower:
            return 45
        if 'yan yana' in ev_lower or 'birlikte' in ev_lower:
            return 55
        if 'yetenek' in ev_lower or 'spell' in ev_lower or 'hit' in ev_lower:
            return 65
        if 'katledince' in ev_lower or 'kill' in ev_lower:
            return 75
        if 'asist' in ev_lower or 'assist' in ev_lower:
            return 85
        return 90

    # 1-B. BÖLGESEL / FRAKSİYONEL KARŞILAŞMALAR (Tüm spesifik şampiyon atıflarından SONRA gelir: W:100..108)
    matched_faction = parse_event_faction(str(raw_event or ''), champ_name)
    if matched_faction:
        if 'düşman' in ev_lower and 'karşılaş' in ev_lower:
            return 100
        if 'dost' in ev_lower and 'karşılaş' in ev_lower:
            return 102
        if 'kışkırt' in ev_lower or 'taunt' in ev_lower:
            return 104
        if 'şaka' in ev_lower or 'joke' in ev_lower:
            return 106
        if 'katledilince' in ev_lower or 'kill' in ev_lower:
            return 108
        return 105

    # 2. KATLETME ZİNCİRİ & DESTANSI CANAVARLAR
    if 'ilk kan' in ev_lower or 'firstblood' in ev_lower or 'first_blood' in ev_lower:
        return 110
    if 'beşte beş' in ev_lower or 'penta' in ev_lower:
        return 115
    if 'dörtte dört' in ev_lower or 'quadra' in ev_lower:
        return 120
    if 'üçte üç' in ev_lower or 'triple' in ev_lower:
        return 125
    if 'ikide iki' in ev_lower or 'double' in ev_lower:
        return 130
    if 'katliam yap' in ev_lower or re.search(r'(?:^|[_0-9\s]|kill)ace(?:$|[_0-9\s]|3d|2d)', ev_lower):
        return 135
    if 'katletme serisi' in ev_lower or 'killing spree' in ev_lower or 'spree' in ev_lower or 'streak' in ev_lower:
        return 140
    if 'serisini durdur' in ev_lower or 'shutdown' in ev_lower:
        return 145
    if 'baron' in ev_lower or 'nashor' in ev_lower:
        return 155
    if 'kadim ejder' in ev_lower:
        return 160
    if 'ejder' in ev_lower or 'dragon' in ev_lower:
        return 165
    if 'vadi' in ev_lower or 'herald' in ev_lower or 'alamet' in ev_lower:
        return 170
    if 'kurtcuk' in ev_lower or 'kurtçuk' in ev_lower or 'grub' in ev_lower or 'voidgrub' in ev_lower:
        return 175
    if 'kule' in ev_lower or 'turret' in ev_lower:
        return 180
    if 'inhib' in ev_lower:
        return 185
    if 'düşman katledince' in ev_lower or 'kill' in ev_lower:
        return 190
    if 'karşılaş' in ev_lower:
        return 195

    # 3. SEÇİM, YASAKLAMA & OYUN BAŞLANGICI
    if 'seçilince' in ev_lower or 'select' in ev_lower or 'pick' in ev_lower:
        return 210
    if ('yasaklan' in ev_lower or '_ban' in ev_lower or 'ban_' in ev_lower) and 'banshee' not in ev_lower:
        return 220
    if 'vadide ilk doğuş' in ev_lower or 'gamestart' in ev_lower or 'matchstart' in ev_lower or 'intro' in ev_lower:
        return 230

    # 4. GENEL REPLİKLER & SEVİYE ATLAMA
    if 'genel karakter repliği' in ev_lower:
        return 310
    if 'seviye' in ev_lower or 'level' in ev_lower:
        return 320

    # 5. DUYGULAR / EMOTES (CTRL 1..4 Kesintisiz Blok: Şaka -> Kışkırtma -> Dans -> Kahkaha)
    if 'joke' in ev_lower or 'şaka' in ev_lower:
        return 410  # CTRL+1 (Şaka)
    if 'taunt' in ev_lower or 'kışkırt' in ev_lower:
        return 420  # CTRL+2 (Kışkırtma)
    if ('dance' in ev_lower or 'dans' in ev_lower) and not any(k in ev_lower for k in ['dansçı', 'dancer', 'phantom']):
        return 430  # CTRL+3 (Dans)
    if 'laugh' in ev_lower or 'kahkaha' in ev_lower:
        return 440  # CTRL+4 (Kahkaha)

    # 6. DÖVÜŞ & YETENEK REPLİKLERİ (Q -> W -> E -> R Ulti -> Saldırı)
    if cat_id == "1_Q_Yetenegi" or 'q yetene' in ev_lower or 'q_' in ev_lower:
        return 510
    if cat_id == "2_W_Yetenegi" or 'w yetene' in ev_lower or 'w_' in ev_lower:
        return 520
    if cat_id == "3_E_Yetenegi" or 'e yetene' in ev_lower or 'e_' in ev_lower:
        return 530
    if cat_id == "4_R_Ulti" or 'r ulti' in ev_lower or 'ulti' in ev_lower or 'r_' in ev_lower:
        return 540
    if ('saldırı' in ev_lower or 'attack' in ev_lower or 'kritik' in ev_lower) and 'sfx' not in ev_lower and 'efor' not in ev_lower:
        return 560

    # 7. HARİTADA GEZERKEN (HAREKET), ÜSSE DÖNÜŞ & YENİDEN CANLANMA
    if 'uzun mesafeli yürüyüş' in ev_lower:
        return 610
    if 'yürürken' in ev_lower or 'hareket' in ev_lower or 'move' in ev_lower:
        return 620
    if 'üsse dönüş' in ev_lower or 'recall' in ev_lower:
        return 650
    if 'yeniden canlan' in ev_lower or 'respawn' in ev_lower:
        return 660

    # 8. ÖLÜM & SES EFEKTLERİ / HOMURTULAR (SFX) - EN SONDA!
    if 'ölürken' in ev_lower or 'ölüm' in ev_lower or 'can verirken' in ev_lower or 'death' in ev_lower or 'die' in ev_lower:
        return 880
    if 'sfx' in ev_lower or 'bağırma' in ev_lower or 'efor' in ev_lower or 'homurtu' in ev_lower or 'hıkırtı' in ev_lower:
        return 910
    if 'acı' in ev_lower or 'inilti' in ev_lower:
        return 930

    return 750
