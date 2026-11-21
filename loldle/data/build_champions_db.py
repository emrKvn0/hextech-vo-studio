# -*- coding: utf-8 -*-
"""
League of Legends LoLdle Turkish Database Builder
Fetches DDragon & Community Dragon data and creates loldle/data/champions.json
"""

import os
import sys
import json
import urllib.request
import concurrent.futures
import time

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

CHAMPION_METADATA_MAP = {
    "Aatrox": {
        "gender": "Erkek",
        "positions": ["Üst Koridor"],
        "species": ["Darkin"],
        "resource": "Manasız",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Shurima", "Runeterra"],
        "release_year": 2013,
        "emojis": ["🗡️", "🩸", "🪽", "💀"],
        "quote_tr": "Ben bir kral değilim, ben bir tanrı değilim... Ben daha kötüsüyüm!",
        "ban_quote_tr": "Korkak! Kaçışın sadece sonunu geciktirir.",
        "quote_hint": "Büyük kılıçlı karanlık bir savaşçı"
    },
    "Ahri": {
        "gender": "Kadın",
        "positions": ["Orta Koridor"],
        "species": ["Vastaya"],
        "resource": "Mana",
        "range_type": ["Menzilli"],
        "regions": ["Ionia"],
        "release_year": 2011,
        "emojis": ["🦊", "🔮", "💖", "🌸"],
        "quote_tr": "Bana güvenmiyor musun?",
        "ban_quote_tr": "Yazık, tam da eğlenmeye başlamıştık.",
        "quote_hint": "Ruh küresi ve dokuz kuyruk"
    },
    "Akali": {
        "gender": "Kadın",
        "positions": ["Orta Koridor", "Üst Koridor"],
        "species": ["İnsan"],
        "resource": "Enerji",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Ionia"],
        "release_year": 2010,
        "emojis": ["🥷", "💨", "🗡️", "🍜"],
        "quote_tr": "Korkarsan vururlar, ölürsen unutulursun. Yaşa ve iz bırak!",
        "ban_quote_tr": "Dengenizi bozmaktan korkuyorsunuz.",
        "quote_hint": "Sis perdesi arkasında gizlenen suikastçı"
    },
    "Akshan": {
        "gender": "Erkek",
        "positions": ["Orta Koridor", "Alt Koridor"],
        "species": ["İnsan"],
        "resource": "Mana",
        "range_type": ["Menzilli"],
        "regions": ["Shurima"],
        "release_year": 2021,
        "emojis": ["🪝", "🔫", "🕶️", "✨"],
        "quote_tr": "İntikam soğuk yenen bir yemektir ama ben ısıtıp da yerim!",
        "ban_quote_tr": "Hey, intikam sıramı çaldın!",
        "quote_hint": "Kancasıyla binalarda sallanan fedai"
    },
    "Alistar": {
        "gender": "Erkek",
        "positions": ["Destek"],
        "species": ["Minotaur"],
        "resource": "Mana",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Runeterra"],
        "release_year": 2009,
        "emojis": ["🐂", "🔔", "🛡️", "💥"],
        "quote_tr": "Beni kimse durduramaz!",
        "ban_quote_tr": "Öküzün boynuzlarını göremeyeceksin.",
        "quote_hint": "Çan çalan devasa boğa"
    },
    "Ambessa": {
        "gender": "Kadın",
        "positions": ["Üst Koridor", "Orman"],
        "species": ["İnsan"],
        "resource": "Enerji",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Noxus"],
        "release_year": 2024,
        "emojis": ["⚔️", "👑", "🩸", "🐺"],
        "quote_tr": "Noxus'un gücü kandan gelir, benim kanımdan!",
        "ban_quote_tr": "Korkaklık en büyük zayıflıktır.",
        "quote_hint": "Medarda hanedanının acımasız matriarkı"
    },
    "Amumu": {
        "gender": "Erkek",
        "positions": ["Orman", "Destek"],
        "species": ["Yordle", "Ölümsüz"],
        "resource": "Mana",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Shurima"],
        "release_year": 2009,
        "emojis": ["🤕", "😭", "🩹", "💔"],
        "quote_tr": "Benimle arkadaş olur musun?",
        "ban_quote_tr": "Zaten kimse beni sevmiyor...",
        "quote_hint": "Sonsuza dek ağlayan sargılı mumya"
    },
    "Anivia": {
        "gender": "Kadın",
        "positions": ["Orta Koridor"],
        "species": ["Tanrı", "Ruh"],
        "resource": "Mana",
        "range_type": ["Menzilli"],
        "regions": ["Freljord"],
        "release_year": 2009,
        "emojis": ["🦅", "❄️", "🥚", "🧊"],
        "quote_tr": "Kanatlarımın rüzgârında donacaksınız.",
        "ban_quote_tr": "Kış er ya da geç gelecek.",
        "quote_hint": "Freljord'un buz anka kuşu"
    },
    "Annie": {
        "gender": "Kadın",
        "positions": ["Orta Koridor", "Destek"],
        "species": ["İnsan", "Büyüyle Değişmiş"],
        "resource": "Mana",
        "range_type": ["Menzilli"],
        "regions": ["Noxus", "Runeterra"],
        "release_year": 2009,
        "emojis": ["👧", "🔥", "🧸", "👗"],
        "quote_tr": "Ayıcığım Tibbers'ı gördün mü?",
        "ban_quote_tr": "Sıkıcısın! Tibbers da öyle düşünüyor.",
        "quote_hint": "Alevler saçan küçük kız ve ayısı"
    },
    "Aphelios": {
        "gender": "Erkek",
        "positions": ["Alt Koridor"],
        "species": ["İnsan"],
        "resource": "Mana",
        "range_type": ["Menzilli"],
        "regions": ["Targon"],
        "release_year": 2019,
        "emojis": ["🌙", "🔫", "🗡️", "🤫"],
        "quote_tr": "Ayın fısıltısı bize rehberlik ediyor...",
        "ban_quote_tr": "Gölge seni terk etmeyecek.",
        "quote_hint": "5 farklı silah kullanan suskun Lunari suikastçısı"
    },
    "Ashe": {
        "gender": "Kadın",
        "positions": ["Alt Koridor", "Destek"],
        "species": ["İnsan", "Buzdoğumlu"],
        "resource": "Mana",
        "range_type": ["Menzilli"],
        "regions": ["Freljord"],
        "release_year": 2009,
        "emojis": ["🏹", "❄️", "👑", "🦅"],
        "quote_tr": "Tek bir okla!",
        "ban_quote_tr": "Birleşmiş bir Freljord'u durduramazsın.",
        "quote_hint": "Avarosan kabilesinin Buz Okçusu ve Savaş Anası"
    },
    "AurelionSol": {
        "gender": "Erkek",
        "positions": ["Orta Koridor"],
        "species": ["Ejderha", "Tanrı"],
        "resource": "Mana",
        "range_type": ["Menzilli"],
        "regions": ["Targon", "Runeterra"],
        "release_year": 2016,
        "emojis": ["🌌", "🐉", "⭐", "🪐"],
        "quote_tr": "Yıldızları ben dövdüm, sizi de ben yok edeceğim.",
        "ban_quote_tr": "Kozmik ihtişamımı anlayamazsınız.",
        "quote_hint": "Evreni ve yıldızları yaratan uzay ejderhası"
    },
    "Aurora": {
        "gender": "Kadın",
        "positions": ["Orta Koridor", "Üst Koridor"],
        "species": ["Vastaya"],
        "resource": "Mana",
        "range_type": ["Menzilli"],
        "regions": ["Freljord"],
        "release_year": 2024,
        "emojis": ["🐰", "🔮", "✨", "❄️"],
        "quote_tr": "Ruhlar dünyası düşündüğünden çok daha yakın.",
        "ban_quote_tr": "Tavşanlar her zaman bir yolunu bulur.",
        "quote_hint": "Ruhlar alemine adım atan Vastaya tavşanı"
    },
    "Azir": {
        "gender": "Erkek",
        "positions": ["Orta Koridor"],
        "species": ["Tanrı", "Büyüyle Değişmiş"],
        "resource": "Mana",
        "range_type": ["Menzilli"],
        "regions": ["Shurima"],
        "release_year": 2014,
        "emojis": ["🏜️", "🦅", "👑", "💂"],
        "quote_tr": "Shurima! İmparatorun geri döndü!",
        "ban_quote_tr": "Kuma gömüleceksiniz.",
        "quote_hint": "Kumdan askerler yaratan Shurima İmparatoru"
    },
    "Bard": {
        "gender": "Diğer",
        "positions": ["Destek"],
        "species": ["Ruh", "Tanrı"],
        "resource": "Mana",
        "range_type": ["Menzilli"],
        "regions": ["Runeterra", "Targon"],
        "release_year": 2015,
        "emojis": ["🎺", "✨", "🔔", "🌀"],
        "quote_tr": "*Kozmik çan sesleri ve flüt melodisi*",
        "ban_quote_tr": "*Derin kozmik uğultu*",
        "quote_hint": "Geçitler açıp tını toplayan kozmik gezgin"
    },
    "Belveth": {
        "gender": "Kadın",
        "positions": ["Orman"],
        "species": ["Hiçlik"],
        "resource": "Manasız",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Hiçlik"],
        "release_year": 2022,
        "emojis": ["🪸", "👑", "🟣", "🐟"],
        "quote_tr": "Bu dünya yok olacak ve yerini benim lavanta denizim alacak.",
        "ban_quote_tr": "Hiçlik her şeyi yutacak.",
        "quote_hint": "Hiçliğin imparatoriçesi ve vatoz formundaki yaratık"
    },
    "Blitzcrank": {
        "gender": "Diğer",
        "positions": ["Destek"],
        "species": ["Golem", "Sayborg"],
        "resource": "Mana",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Zaun"],
        "release_year": 2009,
        "emojis": ["🤖", "🪝", "⚡", "💛"],
        "quote_tr": "Harekete geçmeye hazırım.",
        "ban_quote_tr": "Buhar motorlarım soğuyor.",
        "quote_hint": "Zaun'un roket elli buhar devi"
    },
    "Brand": {
        "gender": "Erkek",
        "positions": ["Destek", "Orta Koridor", "Orman"],
        "species": ["İnsan", "Büyüyle Değişmiş"],
        "resource": "Mana",
        "range_type": ["Menzilli"],
        "regions": ["Freljord", "Runeterra"],
        "release_year": 2011,
        "emojis": ["🔥", "🌋", "💀", "☄️"],
        "quote_tr": "Dünyayı ateşe vermeye hazırım!",
        "ban_quote_tr": "Alevler asla sönmez!",
        "quote_hint": "Dünya Rünü ateşiyle yanan intikam ateşi"
    },
    "Braum": {
        "gender": "Erkek",
        "positions": ["Destek"],
        "species": ["İnsan", "Buzdoğumlu"],
        "resource": "Mana",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Freljord"],
        "release_year": 2014,
        "emojis": ["🛡️", "🧔", "❄️", "🥛"],
        "quote_tr": "Braum arkanda! Kapı gibi korurum!",
        "ban_quote_tr": "Poro gibi kaçmak yakışmadı.",
        "quote_hint": "Dev kapı kalkanı ve bıyıklarıyla Freljord'un yüreği"
    },
    "Briar": {
        "gender": "Kadın",
        "positions": ["Orman", "Üst Koridor"],
        "species": ["Büyüyle Değişmiş", "Ölümsüz"],
        "resource": "Can",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Noxus"],
        "release_year": 2023,
        "emojis": ["🧛‍♀️", "🩸", "⛓️", "🍖"],
        "quote_tr": "Açım! Bana kan verin, kan!",
        "ban_quote_tr": "Ama ben sadece arkadaş olmak ve biraz ısırmak istemiştim!",
        "quote_hint": "Boyunduruğunu kırınca çılgına dönen vampir kız"
    },
    "Caitlyn": {
        "gender": "Kadın",
        "positions": ["Alt Koridor"],
        "species": ["İnsan"],
        "resource": "Mana",
        "range_type": ["Menzilli"],
        "regions": ["Piltover"],
        "release_year": 2011,
        "emojis": ["🎩", "🎯", "🧁", "🔫"],
        "quote_tr": "Gözüm üzerinde!",
        "ban_quote_tr": "Davanın peşini bırakmayacağım.",
        "quote_hint": "Piltover'ın şapkalı keskin nişancı şerifi"
    },
    "Camille": {
        "gender": "Kadın",
        "positions": ["Üst Koridor"],
        "species": ["Sayborg", "İnsan"],
        "resource": "Mana",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Piltover"],
        "release_year": 2016,
        "emojis": ["✂️", "🦵", "💎", "👵"],
        "quote_tr": "Hassasiyet, kaba kuvvetten her zaman üstündür.",
        "ban_quote_tr": "Zarafetten nasibinizi almamışsınız.",
        "quote_hint": "Bıçak bacaklı Piltover istihbarat şefi"
    },
    "Cassiopeia": {
        "gender": "Kadın",
        "positions": ["Orta Koridor"],
        "species": ["Büyüyle Değişmiş", "İnsan"],
        "resource": "Mana",
        "range_type": ["Menzilli"],
        "regions": ["Noxus", "Shurima"],
        "release_year": 2010,
        "emojis": ["🐍", "🧪", "🗿", "👁️"],
        "quote_tr": "Gözlerime bak... Taş kesileceksin!",
        "ban_quote_tr": "Zehirden kaçamazsın.",
        "quote_hint": "Noxus'lu yılan gövdeli zehirli büyücü"
    },
    "Chogath": {
        "gender": "Diğer",
        "positions": ["Üst Koridor", "Orta Koridor"],
        "species": ["Hiçlik"],
        "resource": "Mana",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Hiçlik"],
        "release_year": 2009,
        "emojis": ["🦖", "🍽️", "🟣", "🌋"],
        "quote_tr": "Ruhunu bir lokmada yutacağım!",
        "ban_quote_tr": "Açlığım asla dinmeyecek.",
        "quote_hint": "Yedikçe devasa büyüyen Hiçliğin Dehşeti"
    },
    "Corki": {
        "gender": "Erkek",
        "positions": ["Orta Koridor", "Alt Koridor"],
        "species": ["Yordle"],
        "resource": "Mana",
        "range_type": ["Menzilli"],
        "regions": ["Bandle Şehri", "Piltover"],
        "release_year": 2009,
        "emojis": ["✈️", "💣", "🚁", "👴"],
        "quote_tr": "Havalanmaya hazırım!",
        "ban_quote_tr": "Kuyruğumu kıstırıp kaçacak değilim.",
        "quote_hint": "Helikopteriyle bomba yağdıran bıyıklı Yordle pilot"
    },
    "Darius": {
        "gender": "Erkek",
        "positions": ["Üst Koridor"],
        "species": ["İnsan"],
        "resource": "Mana",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Noxus"],
        "release_year": 2012,
        "emojis": ["🪓", "🩸", "🌪️", "🐺"],
        "quote_tr": "Noxus yükselecek!",
        "ban_quote_tr": "Korkaklar cellattan kaçamaz.",
        "quote_hint": "Noxus'un baltalı eli ve kanama ustası"
    },
    "Diana": {
        "gender": "Kadın",
        "positions": ["Orman", "Orta Koridor"],
        "species": ["İnsan", "Tanrı"],
        "resource": "Mana",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Targon"],
        "release_year": 2012,
        "emojis": ["🌙", "🗡️", "🌕", "✨"],
        "quote_tr": "Ayın ışığı gerçeği ortaya çıkaracak.",
        "ban_quote_tr": "Güneşin yalanlarına kanmaya devam edin.",
        "quote_hint": "Hilal kılıçlı Targon Lunari savaşçısı"
    },
    "DrMundo": {
        "gender": "Erkek",
        "positions": ["Üst Koridor", "Orman"],
        "species": ["Büyüyle Değişmiş", "İnsan"],
        "resource": "Can",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Zaun"],
        "release_year": 2009,
        "emojis": ["💉", "🪓", "🟣", "👅"],
        "quote_tr": "Mundo istediği yere gider!",
        "ban_quote_tr": "Mundo çok üzgün...",
        "quote_hint": "Zaun'un kemik kıran deli doktoru"
    },
    "Draven": {
        "gender": "Erkek",
        "positions": ["Alt Koridor"],
        "species": ["İnsan"],
        "resource": "Mana",
        "range_type": ["Menzilli"],
        "regions": ["Noxus"],
        "release_year": 2012,
        "emojis": ["🪓", "🎪", "🧔", "💰"],
        "quote_tr": "Draven Ligi'ne hoş geldiniz!",
        "ban_quote_tr": "Bu kadar gösteriş fazla geldi değil mi?",
        "quote_hint": "Dönen baltalarıyla şov yapan kibirli gladyatör"
    },
    "Ekko": {
        "gender": "Erkek",
        "positions": ["Orman", "Orta Koridor"],
        "species": ["İnsan"],
        "resource": "Mana",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Zaun"],
        "release_year": 2015,
        "emojis": ["⏳", "🏏", "⚡", "🛹"],
        "quote_tr": "Zamanı bükmek çocuk oyuncağı.",
        "ban_quote_tr": "İkinci bir şansın olmayacak.",
        "quote_hint": "Zamanı geri alan Zaun'lu dahi çocuk"
    },
    "Elise": {
        "gender": "Kadın",
        "positions": ["Orman"],
        "species": ["Büyüyle Değişmiş", "İnsan"],
        "resource": "Mana",
        "range_type": ["Yakın Dövüş", "Menzilli"],
        "regions": ["Noxus", "Gölge Adalar"],
        "release_year": 2012,
        "emojis": ["🕷️", "🕸️", "👠", "🥚"],
        "quote_tr": "Ağıma düşen asla kurtulamaz.",
        "ban_quote_tr": "Örümcek tanrı kurbanını bekleyecek.",
        "quote_hint": "Örümcek kadına dönüşen Gölge Adalar kraliçesi"
    },
    "Evelynn": {
        "gender": "Kadın",
        "positions": ["Orman"],
        "species": ["Demon", "Ruh"],
        "resource": "Mana",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Runeterra"],
        "release_year": 2009,
        "emojis": ["😈", "👠", "💋", "🗡️"],
        "quote_tr": "Karanlıkta fısıldayan ses benim.",
        "ban_quote_tr": "Acı çekmeyi kaçırdın tatlım.",
        "quote_hint": "Kurbanlarını zevk ve acıyla avlayan görünmez iblis"
    },
    "Ezreal": {
        "gender": "Erkek",
        "positions": ["Alt Koridor", "Orta Koridor"],
        "species": ["İnsan"],
        "resource": "Mana",
        "range_type": ["Menzilli"],
        "regions": ["Piltover"],
        "release_year": 2010,
        "emojis": ["🧤", "✨", "🏹", "🗺️"],
        "quote_tr": "Müzede olması gereken sensin!",
        "ban_quote_tr": "Zaten ben de harita aramaya gidiyordum.",
        "quote_hint": "Sihirli Shurima eldiveniyle parlayan kâşif"
    },
    "Fiddlesticks": {
        "gender": "Diğer",
        "positions": ["Orman", "Destek"],
        "species": ["Demon", "Ruh"],
        "resource": "Mana",
        "range_type": ["Menzilli"],
        "regions": ["Runeterra"],
        "release_year": 2009,
        "emojis": ["🌾", "🐦‍⬛", "🪓", "😱"],
        "quote_tr": "KORKU... İLK KORKU...",
        "ban_quote_tr": "Fiddleee... stiiicks...",
        "quote_hint": "Kargalarıyla ansızın beliren ilkel korku iblisi korkuluk"
    },
    "Fiora": {
        "gender": "Kadın",
        "positions": ["Üst Koridor"],
        "species": ["İnsan"],
        "resource": "Mana",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Demacia"],
        "release_year": 2012,
        "emojis": ["🤺", "⚔️", "🎯", "🌹"],
        "quote_tr": "Benimle düelloya var mısın?",
        "ban_quote_tr": "Korkaklara kılıç çekmem.",
        "quote_hint": "Zayıf noktaları vuran asil Demacia düellocusu"
    },
    "Fizz": {
        "gender": "Erkek",
        "positions": ["Orta Koridor"],
        "species": ["Yordle"],
        "resource": "Mana",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Bilgewater", "Bandle Şehri"],
        "release_year": 2011,
        "emojis": ["🐟", "🔱", "🦈", "🌊"],
        "quote_tr": "Hadi yüzmeye gidelim!",
        "ban_quote_tr": "Köpekbalığım seni arayacak!",
        "quote_hint": "Zıpkınıyla sıçrayıp dev köpekbalığı çağıran su Yordle'ı"
    },
    "Galio": {
        "gender": "Diğer",
        "positions": ["Orta Koridor", "Destek"],
        "species": ["Golem"],
        "resource": "Mana",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Demacia"],
        "release_year": 2010,
        "emojis": ["🗿", "🪽", "👑", "🛡️"],
        "quote_tr": "Ezme zamanı geldi!",
        "ban_quote_tr": "Heykele dönsem iyi olacak.",
        "quote_hint": "Büyüyle canlanan devasa Demacia petrisit heykeli"
    },
    "Gangplank": {
        "gender": "Erkek",
        "positions": ["Üst Koridor", "Orta Koridor"],
        "species": ["İnsan"],
        "resource": "Mana",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Bilgewater"],
        "release_year": 2009,
        "emojis": ["🏴‍☠️", "🍊", "💣", "🔫"],
        "quote_tr": "Ne ölüm ne de donanma beni durdurabilir!",
        "ban_quote_tr": "Portakalım bittiğinde dönerim.",
        "quote_hint": "Barut fıçısı patlatan ve portakal yiyen korsan kral"
    },
    "Garen": {
        "gender": "Erkek",
        "positions": ["Üst Koridor"],
        "species": ["İnsan"],
        "resource": "Manasız",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Demacia"],
        "release_year": 2010,
        "emojis": ["⚔️", "🛡️", "🌪️", "👑"],
        "quote_tr": "Demacia'nın gücü adına!",
        "ban_quote_tr": "Adaletten kaçamazsınız!",
        "quote_hint": "Çalıda bekleyen ve kılıcıyla dönen Demacia savaşçısı"
    },
    "Gnar": {
        "gender": "Erkek",
        "positions": ["Üst Koridor"],
        "species": ["Yordle"],
        "resource": "Öfke",
        "range_type": ["Menzilli", "Yakın Dövüş"],
        "regions": ["Freljord"],
        "release_year": 2014,
        "emojis": ["🪃", "🦴", "🦖", "❄️"],
        "quote_tr": "Gnar gada! Shugi shugi shugi!",
        "ban_quote_tr": "Vanna gnar!",
        "quote_hint": "Öfkelenince devasa canavara dönüşen tarih öncesi Yordle"
    },
    "Gragas": {
        "gender": "Erkek",
        "positions": ["Orman", "Üst Koridor", "Orta Koridor"],
        "species": ["İnsan"],
        "resource": "Mana",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Freljord"],
        "release_year": 2010,
        "emojis": ["🍺", "🛢️", "🧔", "💥"],
        "quote_tr": "Şerefe!",
        "ban_quote_tr": "Fıçımı alır başka bara giderim.",
        "quote_hint": "Fıçı fırlatan göbekli bira ustası"
    },
    "Graves": {
        "gender": "Erkek",
        "positions": ["Orman"],
        "species": ["İnsan"],
        "resource": "Mana",
        "range_type": ["Menzilli"],
        "regions": ["Bilgewater"],
        "release_year": 2011,
        "emojis": ["🤠", "🚬", "💥", "🔫"],
        "quote_tr": "Ölü adamlar konuşamaz.",
        "ban_quote_tr": "Puromu bile bitiremedim.",
        "quote_hint": "Çifte kırma tüfeği ve purosuy la ünlü Bilgewater kanun kaçağı"
    },
    "Gwen": {
        "gender": "Kadın",
        "positions": ["Üst Koridor", "Orman"],
        "species": ["Ruh", "Büyüyle Değişmiş"],
        "resource": "Mana",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Gölge Adalar", "Camavor"],
        "release_year": 2021,
        "emojis": ["✂️", "🧵", "🪡", "👗"],
        "quote_tr": "Kutsanmış Sis beni koruyor!",
        "ban_quote_tr": "Dikiş tutturamadın canım.",
        "quote_hint": "Dev makası ve iğneleriyle canlanan oyuncak bebek"
    },
    "Hecarim": {
        "gender": "Erkek",
        "positions": ["Orman"],
        "species": ["Ölümsüz"],
        "resource": "Mana",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Gölge Adalar"],
        "release_year": 2012,
        "emojis": ["🐎", "👻", "🪓", "💨"],
        "quote_tr": "Gölge Süvarileri asla durmaz!",
        "ban_quote_tr": "Ezilmekten korktunuz.",
        "quote_hint": "Gölge Adalar'ın hayalet atlı savaşçısı"
    },
    "Heimerdinger": {
        "gender": "Erkek",
        "positions": ["Orta Koridor", "Üst Koridor", "Destek"],
        "species": ["Yordle"],
        "resource": "Mana",
        "range_type": ["Menzilli"],
        "regions": ["Piltover", "Bandle Şehri"],
        "release_year": 2009,
        "emojis": ["🧠", "🔧", "🔬", "🚀"],
        "quote_tr": "Bunu kesinlikle ben icat ettim!",
        "ban_quote_tr": "Teorim henüz çürütülmedi.",
        "quote_hint": "Taretler kuran dev beyinli Yordle mucit"
    },
    "Hwei": {
        "gender": "Erkek",
        "positions": ["Orta Koridor", "Destek"],
        "species": ["İnsan"],
        "resource": "Mana",
        "range_type": ["Menzilli"],
        "regions": ["Ionia"],
        "release_year": 2023,
        "emojis": ["🎨", "🖌️", "🎭", "🌈"],
        "quote_tr": "Her fırça darbesi bir duygunun çığlığıdır.",
        "ban_quote_tr": "Tuvalim yarım kaldı...",
        "quote_hint": "Büyülü fırçasıyla 10 farklı büyü çizen melankolik ressam"
    },
    "Illaoi": {
        "gender": "Kadın",
        "positions": ["Üst Koridor"],
        "species": ["İnsan"],
        "resource": "Mana",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Bilgewater"],
        "release_year": 2015,
        "emojis": ["🐙", "🗿", "🌊", "💪"],
        "quote_tr": "Hareket etmeyen ölür!",
        "ban_quote_tr": "Nagakabouros seni sınayacak.",
        "quote_hint": "Devasa dokunaçlar çıkaran Nagakabouros rahibesi"
    },
    "Irelia": {
        "gender": "Kadın",
        "positions": ["Üst Koridor", "Orta Koridor"],
        "species": ["İnsan"],
        "resource": "Mana",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Ionia"],
        "release_year": 2010,
        "emojis": ["🗡️", "💃", "🌸", "🛡️"],
        "quote_tr": "Placidium'u asla unutmayacağız!",
        "ban_quote_tr": "Ionia direnişi bitmeyecek.",
        "quote_hint": "Uçan kılıçlarıyla dans eden Ionia direniş lideri"
    },
    "Ivern": {
        "gender": "Erkek",
        "positions": ["Orman"],
        "species": ["Ruh", "Büyüyle Değişmiş"],
        "resource": "Mana",
        "range_type": ["Menzilli"],
        "regions": ["Ionia", "Freljord"],
        "release_year": 2016,
        "emojis": ["🌳", "🌿", "🌻", "🪨"],
        "quote_tr": "Ormandaki tüm dostlarıma selam olsun!",
        "ban_quote_tr": "Ağaçlar senin için yas tutacak.",
        "quote_hint": "Orman yaratıklarını öldürmeden serbest bırakan ağaç adam"
    },
    "Janna": {
        "gender": "Kadın",
        "positions": ["Destek"],
        "species": ["Tanrı", "Ruh"],
        "resource": "Mana",
        "range_type": ["Menzilli"],
        "regions": ["Zaun"],
        "release_year": 2009,
        "emojis": ["🌪️", "🕊️", "💨", "🛡️"],
        "quote_tr": "Rüzgârın kanatlarında!",
        "ban_quote_tr": "Fırtına dindiğinde tekrar görüşürüz.",
        "quote_hint": "Zaun'un koruyucu rüzgâr tanrıçası"
    },
    "JarvanIV": {
        "gender": "Erkek",
        "positions": ["Orman", "Üst Koridor"],
        "species": ["İnsan"],
        "resource": "Mana",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Demacia"],
        "release_year": 2011,
        "emojis": ["👑", "🚩", "🛡️", "🪨"],
        "quote_tr": "Demacia için!",
        "ban_quote_tr": "Tahtım sarsılmaz.",
        "quote_hint": "Mızrağını atıp arena kuran Demacia veliaht prensi"
    },
    "Jax": {
        "gender": "Erkek",
        "positions": ["Üst Koridor", "Orman"],
        "species": ["Bilinmeyen", "İnsan"],
        "resource": "Mana",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Icathia", "Runeterra"],
        "release_year": 2009,
        "emojis": ["🏮", "🥚", "🥋", "💥"],
        "quote_tr": "Bir de gerçek silahım olsaydı görün siz!",
        "ban_quote_tr": "Sokak lambamı özleyeceksin.",
        "quote_hint": "Sokak lambasıyla dövüşen Icathia'lı silah ustası"
    },
    "Jayce": {
        "gender": "Erkek",
        "positions": ["Üst Koridor", "Orta Koridor"],
        "species": ["İnsan"],
        "resource": "Mana",
        "range_type": ["Yakın Dövüş", "Menzilli"],
        "regions": ["Piltover"],
        "release_year": 2012,
        "emojis": ["🔨", "⚡", "🕶️", "🚀"],
        "quote_tr": "Daha parlak bir gelecek için savaşacağım!",
        "ban_quote_tr": "İlerlemeyi durduramazsın.",
        "quote_hint": "Çekiç ve topa dönüşen Hextech cıvalı çekiciyle Piltover koruyucusu"
    },
    "Jhin": {
        "gender": "Erkek",
        "positions": ["Alt Koridor"],
        "species": ["İnsan"],
        "resource": "Mana",
        "range_type": ["Menzilli"],
        "regions": ["Ionia"],
        "release_year": 2016,
        "emojis": ["🎭", "🔫", "🌹", "4️⃣"],
        "quote_tr": "Sanat ancak ölümle kusursuzlaşır!",
        "ban_quote_tr": "Perde kapandı... Ama 4. perde henüz bitmedi.",
        "quote_hint": "4 sayısına takıntılı maskeli Ionia'lı sanatçı suikastçı"
    },
    "Jinx": {
        "gender": "Kadın",
        "positions": ["Alt Koridor"],
        "species": ["İnsan", "Büyüyle Değişmiş"],
        "resource": "Mana",
        "range_type": ["Menzilli"],
        "regions": ["Zaun"],
        "release_year": 2013,
        "emojis": ["💣", "🎀", "💥", "🦈"],
        "quote_tr": "Kuralları kim takar? Patlat gitsin!",
        "ban_quote_tr": "Pofuduk roketim seni asla affetmeyecek!",
        "quote_hint": "Makineli tüfeği ve roketatarıyla ortalığı patlatan çılgın mavi saçlı kız"
    },
    "KSante": {
        "gender": "Erkek",
        "positions": ["Üst Koridor"],
        "species": ["İnsan"],
        "resource": "Mana",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Shurima"],
        "release_year": 2022,
        "emojis": ["🛡️", "🦁", "🥋", "💪"],
        "quote_tr": "Nazumah halkı asla boyun eğmez!",
        "ban_quote_tr": "Av devam edecek.",
        "quote_hint": "Ntofolarıyla duvarlardan fırlatan Nazumah'ın gururu"
    },
    "Kaisa": {
        "gender": "Kadın",
        "positions": ["Alt Koridor"],
        "species": ["İnsan", "Hiçlik"],
        "resource": "Mana",
        "range_type": ["Menzilli"],
        "regions": ["Hiçlik", "Shurima"],
        "release_year": 2018,
        "emojis": ["🟣", "🪽", "🍑", "🚀"],
        "quote_tr": "Ben Hiçlik'te hayatta kaldım, sen burada kalamayacaksın.",
        "ban_quote_tr": "İkinci derim beni korur.",
        "quote_hint": "Hiçlik zırhıyla yaşayan Kassadin'in kızı"
    },
    "Kalista": {
        "gender": "Kadın",
        "positions": ["Alt Koridor"],
        "species": ["Ölümsüz"],
        "resource": "Mana",
        "range_type": ["Menzilli"],
        "regions": ["Gölge Adalar", "Camavor"],
        "release_year": 2014,
        "emojis": ["👻", "🗡️", "🎯", "💚"],
        "quote_tr": "İhanete uğrayanların intikamı olacağız!",
        "ban_quote_tr": "Yeminin bozuldu.",
        "quote_hint": "Ruh bağı kurup mızrak saplayan intikam mızrağı"
    },
    "Karma": {
        "gender": "Kadın",
        "positions": ["Destek", "Orta Koridor"],
        "species": ["İnsan", "Ruh"],
        "resource": "Mana",
        "range_type": ["Menzilli"],
        "regions": ["Ionia"],
        "release_year": 2011,
        "emojis": ["🧘‍♀️", "🛡️", "🌸", "🐉"],
        "quote_tr": "İçindeki uyumu bul.",
        "ban_quote_tr": "Ruhun huzur bulsun.",
        "quote_hint": "Mantra ile yeteneklerini güçlendiren Ionia'nın bilgesi"
    },
    "Karthus": {
        "gender": "Erkek",
        "positions": ["Orman", "Alt Koridor", "Orta Koridor"],
        "species": ["Ölümsüz"],
        "resource": "Mana",
        "range_type": ["Menzilli"],
        "regions": ["Gölge Adalar"],
        "release_year": 2009,
        "emojis": ["💀", "📖", "⚡", "👻"],
        "quote_tr": "Ölümün şarkısını dinleyin!",
        "ban_quote_tr": "Ağıtım tüm haritayı saracak.",
        "quote_hint": "Tüm haritaya ulti atan ölüm şarkıcısı"
    },
    "Kassadin": {
        "gender": "Erkek",
        "positions": ["Orta Koridor"],
        "species": ["İnsan", "Hiçlik"],
        "resource": "Mana",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Hiçlik", "Shurima"],
        "release_year": 2009,
        "emojis": ["🟣", "🗡️", "🥷", "⚡"],
        "quote_tr": "Hiçlik'in güçleri bana boyun eğecek!",
        "ban_quote_tr": "Kızımı kurtarana kadar durmayacağım.",
        "quote_hint": "Sürekli ışınlanarak tek atan Hiçlik Gezgini"
    },
    "Katarina": {
        "gender": "Kadın",
        "positions": ["Orta Koridor"],
        "species": ["İnsan"],
        "resource": "Manasız",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Noxus"],
        "release_year": 2009,
        "emojis": ["🗡️", "🩸", "💃", "🌪️"],
        "quote_tr": "Noxus adına kan dökeceğim!",
        "ban_quote_tr": "Hançerlerimden kaçamazsın.",
        "quote_hint": "Hançerleri üstüne sıçrayıp dönen kızıl saçlı Noxus suikastçısı"
    },
    "Kayle": {
        "gender": "Kadın",
        "positions": ["Üst Koridor", "Orta Koridor"],
        "species": ["Tanrı", "İnsan"],
        "resource": "Mana",
        "range_type": ["Yakın Dövüş", "Menzilli"],
        "regions": ["Targon", "Demacia"],
        "release_year": 2009,
        "emojis": ["🪽", "⚔️", "🔥", "👑"],
        "quote_tr": "Adalet alevlerle arınacak!",
        "ban_quote_tr": "Karanlıkta kalacaksınız.",
        "quote_hint": "Seviye atladıkça kanatlanan ve menzile kavuşan adalet meleği"
    },
    "Kayn": {
        "gender": "Erkek",
        "positions": ["Orman"],
        "species": ["İnsan", "Darkin"],
        "resource": "Mana",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Ionia", "Noxus", "Runeterra"],
        "release_year": 2017,
        "emojis": ["🪓", "🌑", "🩸", "🥷"],
        "quote_tr": "Karanlık beni seçecek, Rhaast değil!",
        "ban_quote_tr": "Tırpandan kaçış yok.",
        "quote_hint": "Duvarların içinden geçen ve Gölge Suikastçı ya da Rhaast'a dönüşen savaşçı"
    },
    "Kennen": {
        "gender": "Erkek",
        "positions": ["Üst Koridor"],
        "species": ["Yordle"],
        "resource": "Enerji",
        "range_type": ["Menzilli"],
        "regions": ["Ionia", "Bandle Şehri"],
        "release_year": 2010,
        "emojis": ["⚡", "🥷", "🦔", "🌪️"],
        "quote_tr": "Fırtınanın kalbi atıyor!",
        "ban_quote_tr": "Yıldırımdan kaçamazsın.",
        "quote_hint": "Yıldırımlarla fırtına koparan Yordle ninja"
    },
    "Khazix": {
        "gender": "Diğer",
        "positions": ["Orman"],
        "species": ["Hiçlik"],
        "resource": "Mana",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Hiçlik"],
        "release_year": 2012,
        "emojis": ["🦗", "🟣", "🪽", "🩸"],
        "quote_tr": "Değiş ve geliş!",
        "ban_quote_tr": "Avım olmaktan kurtuldun.",
        "quote_hint": "Yeteneklerini evrimleştiren Hiçlik peygamberdevesi"
    },
    "Kindred": {
        "gender": "Diğer",
        "positions": ["Orman"],
        "species": ["Tanrı", "Ruh"],
        "resource": "Mana",
        "range_type": ["Menzilli"],
        "regions": ["Runeterra"],
        "release_year": 2015,
        "emojis": ["🐑", "🐺", "🏹", "💀"],
        "quote_tr": "Kuzu'nun okuyla mı, Kurt'un dişiyle mi ölmek istersin?",
        "ban_quote_tr": "Ölümden asla kaçamazsın.",
        "quote_hint": "Kuzu ve Kurt ikilisinden oluşan ölümün sureti"
    },
    "Kled": {
        "gender": "Erkek",
        "positions": ["Üst Koridor"],
        "species": ["Yordle"],
        "resource": "Cesaret",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Noxus", "Bandle Şehri"],
        "release_year": 2016,
        "emojis": ["🦎", "🪓", "🤠", "😡"],
        "quote_tr": "Burası benim arazim! Buradan defolun!",
        "ban_quote_tr": "Skaarl! Bunlar korktu kaçtı!",
        "quote_hint": "Kertenkelesi Skaarl'ın sırtında naralar atan huysuz süvari"
    },
    "KogMaw": {
        "gender": "Diğer",
        "positions": ["Alt Koridor"],
        "species": ["Hiçlik"],
        "resource": "Mana",
        "range_type": ["Menzilli"],
        "regions": ["Hiçlik"],
        "release_year": 2010,
        "emojis": ["🐛", "🧪", "🍽️", "🟣"],
        "quote_tr": "Yemek zamanı!",
        "ban_quote_tr": "Aç kaldım...",
        "quote_hint": "Asit püskürten sevimli ama ölümcül Hiçlik larvası"
    },
    "Leblanc": {
        "gender": "Kadın",
        "positions": ["Orta Koridor"],
        "species": ["İnsan", "Büyüyle Değişmiş"],
        "resource": "Mana",
        "range_type": ["Menzilli"],
        "regions": ["Noxus"],
        "release_year": 2010,
        "emojis": ["🎭", "🪄", "🪞", "🌹"],
        "quote_tr": "Gördüğün her şey bir yanılsamadan ibaret.",
        "ban_quote_tr": "Güllerin ardından fısıldamaya devam edeceğim.",
        "quote_hint": "Kara Gül'ün aynadaki sureti ve aldatıcı büyücüsü"
    },
    "LeeSin": {
        "gender": "Erkek",
        "positions": ["Orman"],
        "species": ["İnsan"],
        "resource": "Enerji",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Ionia"],
        "release_year": 2011,
        "emojis": ["🥋", "👁️", "🐉", "💥"],
        "quote_tr": "Gözlerin kapalı olsa bile ruhun görmeli.",
        "ban_quote_tr": "İçindeki ejderha susturuldu.",
        "quote_hint": "Gözleri bağlı Ionia'lı kör keşiş"
    },
    "Leona": {
        "gender": "Kadın",
        "positions": ["Destek"],
        "species": ["İnsan", "Tanrı"],
        "resource": "Mana",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Targon"],
        "release_year": 2011,
        "emojis": ["☀️", "🛡️", "⚔️", "👑"],
        "quote_tr": "Güneşin ışığı seni aydınlatsın!",
        "ban_quote_tr": "Karanlık sana fayda sağlamaz.",
        "quote_hint": "Güneş kalkanı ve kılıcıyla Targon Solari savaşçısı"
    },
    "Lillia": {
        "gender": "Kadın",
        "positions": ["Orman", "Üst Koridor"],
        "species": ["Ruh", "Büyüyle Değişmiş"],
        "resource": "Mana",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Ionia"],
        "release_year": 2020,
        "emojis": ["🦌", "🌸", "💤", "🌳"],
        "quote_tr": "Eep! Düşler ağacı solmamalı!",
        "ban_quote_tr": "Umarım güzel rüyalar görürsün...",
        "quote_hint": "Rakipleri uyutan narin geyik kızı"
    },
    "Lissandra": {
        "gender": "Kadın",
        "positions": ["Orta Koridor"],
        "species": ["İnsan", "Buzdoğumlu"],
        "resource": "Mana",
        "range_type": ["Menzilli"],
        "regions": ["Freljord"],
        "release_year": 2013,
        "emojis": ["🧊", "👑", "❄️", "👁️"],
        "quote_tr": "Buzdan bir tabuta hapsolacaksınız!",
        "ban_quote_tr": "Gözcülerin gelişi engellenemez.",
        "quote_hint": "Kara Buz'un efendisi ve Freljord'un kör cadısı"
    },
    "Lucian": {
        "gender": "Erkek",
        "positions": ["Alt Koridor", "Orta Koridor"],
        "species": ["İnsan"],
        "resource": "Mana",
        "range_type": ["Menzilli"],
        "regions": ["Demacia", "Gölge Adalar"],
        "release_year": 2013,
        "emojis": ["🔫", "✨", "🧥", "💖"],
        "quote_tr": "Karanlığa karşı ışığın koruyucusu.",
        "ban_quote_tr": "Senna'yla intikamımız sürecek.",
        "quote_hint": "Çift ışık tabancası kullanan ışık muhafızı"
    },
    "Lulu": {
        "gender": "Kadın",
        "positions": ["Destek"],
        "species": ["Yordle"],
        "resource": "Mana",
        "range_type": ["Menzilli"],
        "regions": ["Bandle Şehri"],
        "release_year": 2012,
        "emojis": ["🧙‍♀️", "🧚", "🍄", "🧁"],
        "quote_tr": "Morun tadı harika!",
        "ban_quote_tr": "Pix ve ben başka çiçekler buluruz.",
        "quote_hint": "Pix adlı perisiyle dostlarını devleştiren Yordle cadısı"
    },
    "Lux": {
        "gender": "Kadın",
        "positions": ["Destek", "Orta Koridor"],
        "species": ["İnsan"],
        "resource": "Mana",
        "range_type": ["Menzilli"],
        "regions": ["Demacia"],
        "release_year": 2010,
        "emojis": ["✨", "🌈", "🪄", "💡"],
        "quote_tr": "Karanlığı aydınlatmaya geldim!",
        "ban_quote_tr": "Işığım asla sönmez!",
        "quote_hint": "Devasa ışık lazeri ateşleyen Demacia'lı ışık büyücüsü"
    },
    "Malphite": {
        "gender": "Diğer",
        "positions": ["Üst Koridor", "Destek", "Orta Koridor"],
        "species": ["Golem"],
        "resource": "Mana",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Ixtal", "Shurima"],
        "release_year": 2009,
        "emojis": ["🪨", "⛰️", "🛡️", "💥"],
        "quote_tr": "Kaya gibi sağlam!",
        "ban_quote_tr": "Dağlar yerinden oynamaz.",
        "quote_hint": "Dağ gibi çarparak havaya savuran dev kaya parçası"
    },
    "Malzahar": {
        "gender": "Erkek",
        "positions": ["Orta Koridor"],
        "species": ["İnsan", "Hiçlik"],
        "resource": "Mana",
        "range_type": ["Menzilli"],
        "regions": ["Hiçlik", "Shurima"],
        "release_year": 2010,
        "emojis": ["🟣", "👁️", "🦗", "🪄"],
        "quote_tr": "Hiçlik kaçınılmazdır!",
        "ban_quote_tr": "Gördüğüm kehanet gerçekleşecek.",
        "quote_hint": "Hiçlik haşereleri çıkarıp ultisiyle kilitleyen peygamber"
    },
    "Maokai": {
        "gender": "Erkek",
        "positions": ["Destek", "Orman", "Üst Koridor"],
        "species": ["Ruh", "Büyüyle Değişmiş"],
        "resource": "Mana",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Gölge Adalar"],
        "release_year": 2011,
        "emojis": ["🌲", "🌱", "🪵", "🌊"],
        "quote_tr": "Topraklarımı geri alacağım!",
        "ban_quote_tr": "Köklerim asla kurumayacak.",
        "quote_hint": "Fidan fırlatan ve doğayı savunan çınar devi"
    },
    "MasterYi": {
        "gender": "Erkek",
        "positions": ["Orman"],
        "species": ["İnsan"],
        "resource": "Mana",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Ionia"],
        "release_year": 2009,
        "emojis": ["🗡️", "👓", "⚡", "🥋"],
        "quote_tr": "Kılıcım senin emrinde!",
        "ban_quote_tr": "Wuju sanatı asla ölmez.",
        "quote_hint": "Alfa vuruşuyla görünmez olup biçen Wuju ustası"
    },
    "Mel": {
        "gender": "Kadın",
        "positions": ["Destek", "Orta Koridor"],
        "species": ["İnsan"],
        "resource": "Mana",
        "range_type": ["Menzilli"],
        "regions": ["Piltover", "Noxus"],
        "release_year": 2025,
        "emojis": ["👑", "✨", "🏛️", "🎨"],
        "quote_tr": "Gelecek, onu şekillendirenlerin ellerindedir.",
        "ban_quote_tr": "Diplomasi her zaman bir yolunu bulur.",
        "quote_hint": "Piltover konsey üyesi ve Medarda aristokratı"
    },
    "Milio": {
        "gender": "Erkek",
        "positions": ["Destek"],
        "species": ["İnsan"],
        "resource": "Mana",
        "range_type": ["Menzilli"],
        "regions": ["Ixtal"],
        "release_year": 2023,
        "emojis": ["🔥", "🎒", "⚽", "🪵"],
        "quote_tr": "Alevciklerim hazır, haydi eğlenelim!",
        "ban_quote_tr": "Alevciklerim sana kırıldı.",
        "quote_hint": "Sırt çantasında iyileştirici ateş böcekleri taşıyan Ixtal'lı çocuk"
    },
    "MissFortune": {
        "gender": "Kadın",
        "positions": ["Alt Koridor"],
        "species": ["İnsan"],
        "resource": "Mana",
        "range_type": ["Menzilli"],
        "regions": ["Bilgewater"],
        "release_year": 2010,
        "emojis": ["👒", "🔫", "💋", "🏴‍☠️"],
        "quote_tr": "Şans bana hep güler!",
        "ban_quote_tr": "Korkak korsanlar denize atılır.",
        "quote_hint": "Çift tabancasıyla mermi fırtınası estiren Bilgewater kaptanı"
    },
    "MonkeyKing": {
        "gender": "Erkek",
        "positions": ["Üst Koridor", "Orman"],
        "species": ["Vastaya"],
        "resource": "Mana",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Ionia"],
        "release_year": 2011,
        "emojis": ["🐒", "🥢", "☁️", "🥋"],
        "quote_tr": "En iyisi olmak için savaşacağım!",
        "ban_quote_tr": "Sopamın tadına bakmaktan kaçtın.",
        "quote_hint": "Uzatılabilen asasıyla fırıl fırıl dönen Maymun Kral Wukong"
    },
    "Mordekaiser": {
        "gender": "Erkek",
        "positions": ["Üst Koridor"],
        "species": ["Ölümsüz"],
        "resource": "Kalkan",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Noxus", "Gölge Adalar"],
        "release_year": 2010,
        "emojis": ["💀", "🔨", "👑", "🟢"],
        "quote_tr": "Kader... Hüküm... Ölüm!",
        "ban_quote_tr": "Ölüm alemine er ya da geç geleceksin.",
        "quote_hint": "Rakipleri ölüm alemine hapseden demir zırhlı tiran"
    },
    "Morgana": {
        "gender": "Kadın",
        "positions": ["Destek", "Orta Koridor", "Orman"],
        "species": ["Tanrı", "İnsan"],
        "resource": "Mana",
        "range_type": ["Menzilli"],
        "regions": ["Demacia", "Targon"],
        "release_year": 2009,
        "emojis": ["🪽", "⛓️", "🖤", "🟣"],
        "quote_tr": "Acı çekmeden gerçeği göremezsin.",
        "ban_quote_tr": "Karanlık kanatlarım seni izleyecek.",
        "quote_hint": "Işık kementiyle yere mıhlayan düşmüş melek"
    },
    "Naafiri": {
        "gender": "Diğer",
        "positions": ["Orta Koridor"],
        "species": ["Darkin"],
        "resource": "Mana",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Shurima"],
        "release_year": 2023,
        "emojis": ["🐺", "🗡️", "🩸", "🏜️"],
        "quote_tr": "Biz tek bir Darkin değiliz, biz bir sürüyüz!",
        "ban_quote_tr": "Sürü avını asla unutmaz.",
        "quote_hint": "Tazı sürüsüyle avlanan hançerli Darkin"
    },
    "Nami": {
        "gender": "Kadın",
        "positions": ["Destek"],
        "species": ["Vastaya"],
        "resource": "Mana",
        "range_type": ["Menzilli"],
        "regions": ["Bilgewater", "Targon"],
        "release_year": 2012,
        "emojis": ["🧜‍♀️", "🌊", "🫧", "🔱"],
        "quote_tr": "Dalgaların sesini duyuyor musun?",
        "ban_quote_tr": "Okyanus her şeyi temizler.",
        "quote_hint": "Devasa dalga çağıran denizkızı Vastaya"
    },
    "Nasus": {
        "gender": "Erkek",
        "positions": ["Üst Koridor"],
        "species": ["Tanrı", "Büyüyle Değişmiş"],
        "resource": "Mana",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Shurima"],
        "release_year": 2009,
        "emojis": ["🐕", "⏳", "🪓", "🏜️"],
        "quote_tr": "Zamanın akışı hiçbir şeyi durduramaz.",
        "ban_quote_tr": "Kumlar seni unutacak.",
        "quote_hint": "Yük biriktirdikçe tek atan Shurima'lı çakal başlı ilah"
    },
    "Nautilus": {
        "gender": "Erkek",
        "positions": ["Destek"],
        "species": ["Ölümsüz", "Büyüyle Değişmiş"],
        "resource": "Mana",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Bilgewater"],
        "release_year": 2012,
        "emojis": ["⚓", "🤿", "🌊", "🛡️"],
        "quote_tr": "Karanlık sularda kaybolacaksın.",
        "ban_quote_tr": "Denizin haracı ödenmeliydi.",
        "quote_hint": "Devasa çapasını savuran derinlikler devi dalgıç"
    },
    "Neeko": {
        "gender": "Kadın",
        "positions": ["Orta Koridor", "Destek"],
        "species": ["Vastaya"],
        "resource": "Mana",
        "range_type": ["Menzilli"],
        "regions": ["Ixtal"],
        "release_year": 2018,
        "emojis": ["🦎", "🌸", "🪞", "🌈"],
        "quote_tr": "Neeko güçlü bir domates!",
        "ban_quote_tr": "Neeko seninle oynamak istemişti...",
        "quote_hint": "Minyonlara ve canavarlara dönüşen bukalemun Vastaya"
    },
    "Nidalee": {
        "gender": "Kadın",
        "positions": ["Orman"],
        "species": ["İnsan", "Büyüyle Değişmiş"],
        "resource": "Mana",
        "range_type": ["Menzilli", "Yakın Dövüş"],
        "regions": ["Ixtal", "Shurima"],
        "release_year": 2009,
        "emojis": ["🐆", "🏹", "🐾", "🌿"],
        "quote_tr": "Pençelerimden kaçamazsın!",
        "ban_quote_tr": "Orman yabancıları sevmez.",
        "quote_hint": "Mızrak atıp pumaya dönüşen vahşi avcı"
    },
    "Nilah": {
        "gender": "Kadın",
        "positions": ["Alt Koridor"],
        "species": ["İnsan", "Büyüyle Değişmiş"],
        "resource": "Mana",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Bilgewater", "Kathkan"],
        "release_year": 2022,
        "emojis": ["🌊", "🗡️", "😄", "✨"],
        "quote_tr": "Neşe iblisinin gücüyle dövüşüyorum!",
        "ban_quote_tr": "Neşemizi kaçıramazsın.",
        "quote_hint": "Su kamçısıyla rakiplerini kendine çeken yedinci iblis savaşçısı"
    },
    "Nocturne": {
        "gender": "Diğer",
        "positions": ["Orman"],
        "species": ["Demon", "Ruh"],
        "resource": "Mana",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Runeterra"],
        "release_year": 2011,
        "emojis": ["🌑", "🗡️", "😱", "👻"],
        "quote_tr": "KARANLIK...",
        "ban_quote_tr": "Kabusların peşini bırakmayacak.",
        "quote_hint": "Bütün haritanın ışığını kapatıp ultiyle atlayan kabus iblisi"
    },
    "Nunu": {
        "gender": "Erkek",
        "positions": ["Orman"],
        "species": ["İnsan", "Yeti"],
        "resource": "Mana",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Freljord"],
        "release_year": 2009,
        "emojis": ["👦", "❄️", "⛄", "🦧"],
        "quote_tr": "Willump ile dünyayı kurtaracağız!",
        "ban_quote_tr": "Kartopumuz erimedi!",
        "quote_hint": "Devasa kartopu yuvarlayan çocuk ve Yeti dostu"
    },
    "Olaf": {
        "gender": "Erkek",
        "positions": ["Üst Koridor", "Orman"],
        "species": ["İnsan", "Buzdoğumlu"],
        "resource": "Mana",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Freljord"],
        "release_year": 2010,
        "emojis": ["🪓", "🧔", "⚡", "🍺"],
        "quote_tr": "Şerefli bir ölüm arıyorum!",
        "ban_quote_tr": "Korkakça kaçtın.",
        "quote_hint": "Baltalarıyla kitle kontrol tanımaz şekilde koşan vahşi Viking"
    },
    "Orianna": {
        "gender": "Kadın",
        "positions": ["Orta Koridor"],
        "species": ["Golem", "Sayborg"],
        "resource": "Mana",
        "range_type": ["Menzilli"],
        "regions": ["Piltover"],
        "release_year": 2011,
        "emojis": ["🤖", "🩰", "🔮", "⚙️"],
        "quote_tr": "Tık tık... Zaman akıyor.",
        "ban_quote_tr": "Kukum durdu.",
        "quote_hint": "Mekanik topuyla dans eden kurmalı robot kız"
    },
    "Ornn": {
        "gender": "Erkek",
        "positions": ["Üst Koridor"],
        "species": ["Tanrı", "Ruh"],
        "resource": "Mana",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Freljord"],
        "release_year": 2017,
        "emojis": ["🔨", "🐏", "🌋", "🛡️"],
        "quote_tr": "Konuşmayı sevmem. Çekiç sesini severim.",
        "ban_quote_tr": "İyi, zaten ocağımda işim vardı.",
        "quote_hint": "Ateş koçu çağıran ve eşya döven Freljord demirci ilahı"
    },
    "Pantheon": {
        "gender": "Erkek",
        "positions": ["Destek", "Orta Koridor", "Üst Koridor"],
        "species": ["İnsan", "Tanrı"],
        "resource": "Mana",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Targon"],
        "release_year": 2010,
        "emojis": ["🛡️", "🗡️", "🥖", "⭐"],
        "quote_tr": "Tanrılar düştü, geriye sadece adam kaldı!",
        "ban_quote_tr": "Mızrağım göklerden inecektir.",
        "quote_hint": "Gökten mızrağıyla yıldız gibi inen Targon savaşçısı Atreus"
    },
    "Poppy": {
        "gender": "Kadın",
        "positions": ["Üst Koridor", "Orman", "Destek"],
        "species": ["Yordle"],
        "resource": "Mana",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Demacia", "Bandle Şehri"],
        "release_year": 2010,
        "emojis": ["🔨", "👧", "🛡️", "💥"],
        "quote_tr": "Ben kahraman değilim, sadece çekici taşıyorum.",
        "ban_quote_tr": "Kahraman bir gün dönecek.",
        "quote_hint": "Devasa çekiciyle rakipleri üslerine fırlatan sarışın Yordle"
    },
    "Pyke": {
        "gender": "Erkek",
        "positions": ["Destek"],
        "species": ["Ölümsüz"],
        "resource": "Mana",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Bilgewater"],
        "release_year": 2018,
        "emojis": ["🦈", "🗡️", "📜", "🪙"],
        "quote_tr": "Listenin sonuna kadar herkes boğulacak!",
        "ban_quote_tr": "Adın listemde kaldı.",
        "quote_hint": "Görünmez olup kancayla çeken ve X işaretiyle biçen zıpkıncı"
    },
    "Qiyana": {
        "gender": "Kadın",
        "positions": ["Orta Koridor", "Orman"],
        "species": ["İnsan"],
        "resource": "Mana",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Ixtal"],
        "release_year": 2019,
        "emojis": ["👑", "⭕", "🌿", "💧"],
        "quote_tr": "Ixaocan'ın gerçek imparatoriçesi benim!",
        "ban_quote_tr": "Mükemmelliğime dayanamadınız.",
        "quote_hint": "Element çemberiyle duvarları patlatan kibirli Ixtal prensesi"
    },
    "Quinn": {
        "gender": "Kadın",
        "positions": ["Üst Koridor"],
        "species": ["İnsan"],
        "resource": "Mana",
        "range_type": ["Menzilli"],
        "regions": ["Demacia"],
        "release_year": 2013,
        "emojis": ["🦅", "🏹", "🎯", "💨"],
        "quote_tr": "Valor, havadan gözle!",
        "ban_quote_tr": "Gökyüzü hâlâ bizim.",
        "quote_hint": "Kuşu Valor ile haritada uçan Demacia sınır korucusu"
    },
    "Rakan": {
        "gender": "Erkek",
        "positions": ["Destek"],
        "species": ["Vastaya"],
        "resource": "Mana",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Ionia"],
        "release_year": 2017,
        "emojis": ["🦚", "🕺", "🪽", "💖"],
        "quote_tr": "Bana bakın, dansıma odaklanın!",
        "ban_quote_tr": "Xayah beni bekler!",
        "quote_hint": "Büyüleyici tüyleriyle rakipleri kendine çeken dansçı Vastaya"
    },
    "Rammus": {
        "gender": "Diğer",
        "positions": ["Orman"],
        "species": ["Tanrı", "Büyüyle Değişmiş"],
        "resource": "Mana",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Shurima"],
        "release_year": 2009,
        "emojis": ["🦔", "💨", "🛡️", "👍"],
        "quote_tr": "Tamam.",
        "ban_quote_tr": "Peki.",
        "quote_hint": "Top gibi dönüp 'Tamam' diyen zırhlı kirpi"
    },
    "RekSai": {
        "gender": "Kadın",
        "positions": ["Orman"],
        "species": ["Hiçlik"],
        "resource": "Öfke",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Hiçlik", "Shurima"],
        "release_year": 2014,
        "emojis": ["🦈", "🟣", "🏜️", "🔊"],
        "quote_tr": "*Hiçlik kükremesi ve yer altı titreşimi*",
        "ban_quote_tr": "*Boğuk tıslama sesi*",
        "quote_hint": "Toprağın altından tüneller açıp avlanan Hiçlik kraliçesi"
    },
    "Rell": {
        "gender": "Kadın",
        "positions": ["Destek", "Orman"],
        "species": ["İnsan", "Büyüyle Değişmiş"],
        "resource": "Mana",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Noxus"],
        "release_year": 2020,
        "emojis": ["🐎", "🛡️", "🧲", "⚡"],
        "quote_tr": "Demir bana itaat eder, ben kimseye!",
        "ban_quote_tr": "Kara Gül bunun bedelini ödeyecek.",
        "quote_hint": "Demir atını zırha dönüştüren manyetizma ustası"
    },
    "Renata": {
        "gender": "Kadın",
        "positions": ["Destek"],
        "species": ["İnsan", "Sayborg"],
        "resource": "Mana",
        "range_type": ["Menzilli"],
        "regions": ["Zaun"],
        "release_year": 2022,
        "emojis": ["🧪", "💼", "💵", "👠"],
        "quote_tr": "Herkesin bir fiyatı vardır.",
        "ban_quote_tr": "Yatırımımı geri çektim.",
        "quote_hint": "Rakipleri birbirine kırdıran Zaun'lu kimya baronu"
    },
    "Renekton": {
        "gender": "Erkek",
        "positions": ["Üst Koridor", "Orta Koridor"],
        "species": ["Tanrı", "Büyüyle Değişmiş"],
        "resource": "Öfke",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Shurima"],
        "release_year": 2011,
        "emojis": ["🐊", "🪓", "😡", "🏜️"],
        "quote_tr": "Nasus... Kanınla yıkanacağım!",
        "ban_quote_tr": "Öfkem asla dinmeyecek.",
        "quote_hint": "Hilal bıçağıyla dönen Shurima'lı timsah başlı ilah"
    },
    "Rengar": {
        "gender": "Erkek",
        "positions": ["Orman", "Üst Koridor"],
        "species": ["Vastaya"],
        "resource": "Manasız",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Ixtal", "Shurima"],
        "release_year": 2012,
        "emojis": ["🦁", "🗡️", "👁️", "🥩"],
        "quote_tr": "Bugün güzel bir av olacak!",
        "ban_quote_tr": "Kha'Zix'i bulana kadar avım sensin.",
        "quote_hint": "Çalılardan tek gözü kör aslan gibi atlayan kupa avcısı"
    },
    "Riven": {
        "gender": "Kadın",
        "positions": ["Üst Koridor"],
        "species": ["İnsan"],
        "resource": "Manasız",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Noxus", "Ionia"],
        "release_year": 2011,
        "emojis": ["🗡️", "🥋", "💨", "🛡️"],
        "quote_tr": "Kırık bir kılıç bile bir amaca hizmet eder.",
        "ban_quote_tr": "Sürgünüm devam ediyor.",
        "quote_hint": "Kırık rün kılıcıyla taklalar atan sürgün Noxus askeri"
    },
    "Rumble": {
        "gender": "Erkek",
        "positions": ["Üst Koridor", "Orta Koridor"],
        "species": ["Yordle"],
        "resource": "Isı",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Bandle Şehri", "Shurima"],
        "release_year": 2011,
        "emojis": ["🤖", "🔥", "🚀", "⚡"],
        "quote_tr": "Hurdamın gazabına uğrayacaksınız!",
        "ban_quote_tr": "Tristana beni izliyordu...",
        "quote_hint": "Alev püskürten hurda robotuyla savaşan Yordle"
    },
    "Ryze": {
        "gender": "Erkek",
        "positions": ["Orta Koridor", "Üst Koridor"],
        "species": ["İnsan", "Büyüyle Değişmiş"],
        "resource": "Mana",
        "range_type": ["Menzilli"],
        "regions": ["Runeterra"],
        "release_year": 2009,
        "emojis": ["📜", "🧙‍♂️", "🟣", "⚡"],
        "quote_tr": "Dünya Rünleri güvende olmalı.",
        "ban_quote_tr": "Parşömenimdeki yazgıyı değiştiremezsin.",
        "quote_hint": "Sırtında devasa parşömen taşıyan mavi rün büyücüsü"
    },
    "Samira": {
        "gender": "Kadın",
        "positions": ["Alt Koridor"],
        "species": ["İnsan"],
        "resource": "Mana",
        "range_type": ["Menzilli", "Yakın Dövüş"],
        "regions": ["Noxus", "Shurima"],
        "release_year": 2020,
        "emojis": ["🗡️", "🔫", "🌹", "💃"],
        "quote_tr": "S-Derecesi şov başlıyor!",
        "ban_quote_tr": "Tarzımı kaldıramadın.",
        "quote_hint": "Tabanca ve kılıçla stil puanı toplayıp dönen Noxus'lu fedai"
    },
    "Sejuani": {
        "gender": "Kadın",
        "positions": ["Orman", "Üst Koridor"],
        "species": ["İnsan", "Buzdoğumlu"],
        "resource": "Mana",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Freljord"],
        "release_year": 2012,
        "emojis": ["🐗", "❄️", "⛓️", "🛡️"],
        "quote_tr": "Kışın Pençesi sizi ezecek!",
        "ban_quote_tr": "Domuzum Bristle aç kaldı.",
        "quote_hint": "Yaban domuzu Bristle'ın sırtında gürz savuran Freljord savaş anası"
    },
    "Senna": {
        "gender": "Kadın",
        "positions": ["Destek", "Alt Koridor"],
        "species": ["İnsan", "Ölümsüz"],
        "resource": "Mana",
        "range_type": ["Menzilli"],
        "regions": ["Demacia", "Gölge Adalar"],
        "release_year": 2019,
        "emojis": ["🔫", "👻", "✨", "🖤"],
        "quote_tr": "Fenerden kurtuldum, artık ışığın kendisiyim.",
        "ban_quote_tr": "Lucian'la yolumuza devam edeceğiz.",
        "quote_hint": "Thresh'in fenerinden kurtulan devasa ışık topu taşıyıcısı"
    },
    "Seraphine": {
        "gender": "Kadın",
        "positions": ["Destek", "Alt Koridor", "Orta Koridor"],
        "species": ["İnsan"],
        "resource": "Mana",
        "range_type": ["Menzilli"],
        "regions": ["Piltover", "Zaun"],
        "release_year": 2020,
        "emojis": ["🎤", "💖", "🎶", "✨"],
        "quote_tr": "Şarkımız tüm şehri birleştirecek!",
        "ban_quote_tr": "Konserim iptal edildi mi yani?",
        "quote_hint": "Uçan sahnesinde mikrofonla şarkı söyleyen pembe saçlı pop yıldızı"
    },
    "Sett": {
        "gender": "Erkek",
        "positions": ["Üst Koridor", "Destek", "Orta Koridor"],
        "species": ["Vastaya", "İnsan"],
        "resource": "Metanet",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Ionia"],
        "release_year": 2020,
        "emojis": ["🥊", "🐺", "👑", "💪"],
        "quote_tr": "Patron geri döndü!",
        "ban_quote_tr": "Anneme dövüşmediğimi söylemeyin yeter.",
        "quote_hint": "Yeraltı dövüş çetesinin Vastaya yumrukçu patronu"
    },
    "Shaco": {
        "gender": "Diğer",
        "positions": ["Orman", "Destek"],
        "species": ["Ruh", "Büyüyle Değişmiş"],
        "resource": "Mana",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Runeterra"],
        "release_year": 2009,
        "emojis": ["🤡", "🗡️", "🎁", "💨"],
        "quote_tr": "Neden bu kadar ciddisin?",
        "ban_quote_tr": "Klonum arkanda bekliyor...",
        "quote_hint": "Görünmez olup arkadan bıçaklayan ve kutu koyan sinsi soytarı"
    },
    "Shen": {
        "gender": "Erkek",
        "positions": ["Üst Koridor", "Destek"],
        "species": ["İnsan"],
        "resource": "Enerji",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Ionia"],
        "release_year": 2010,
        "emojis": ["🥷", "🗡️", "🛡️", "👁️"],
        "quote_tr": "Ruhlar dünyası ile aramızdaki denge bozulamaz.",
        "ban_quote_tr": "Gözüm üzerinizde.",
        "quote_hint": "Haritadaki dostuna kalkanla ışınlanan Alacakaranlığın Gözü ninja"
    },
    "Shyvana": {
        "gender": "Kadın",
        "positions": ["Orman", "Üst Koridor"],
        "species": ["Ejderha", "İnsan"],
        "resource": "Öfke",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Demacia"],
        "release_year": 2011,
        "emojis": ["🐉", "🔥", "👧", "🛡️"],
        "quote_tr": "Ejderhanın öfkesiyle yüzleşin!",
        "ban_quote_tr": "Alevler sönmez.",
        "quote_hint": "Ateş püskürten ejderhaya dönüşen melez Demacia savaşçısı"
    },
    "Singed": {
        "gender": "Erkek",
        "positions": ["Üst Koridor"],
        "species": ["İnsan", "Büyüyle Değişmiş"],
        "resource": "Mana",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Zaun"],
        "release_year": 2009,
        "emojis": ["🧪", "💨", "🛡️", "🏃"],
        "quote_tr": "Arkamdan gelmeye cesaretin var mı?",
        "ban_quote_tr": "Zehirli izim Zaun'da kalacak.",
        "quote_hint": "Arkasında zehirli gaz bırakıp koşan Zaun kimyageri"
    },
    "Sion": {
        "gender": "Erkek",
        "positions": ["Üst Koridor"],
        "species": ["Ölümsüz"],
        "resource": "Mana",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Noxus"],
        "release_year": 2009,
        "emojis": ["🧟", "🪓", "🚆", "👑"],
        "quote_tr": "NOXUS DİYE BAĞIRIN!",
        "ban_quote_tr": "Ölüm bile beni durduramayacak.",
        "quote_hint": "Tren gibi kükreyerek kulelere toslayan hortlak Noxus devi"
    },
    "Sivir": {
        "gender": "Kadın",
        "positions": ["Alt Koridor"],
        "species": ["İnsan"],
        "resource": "Mana",
        "range_type": ["Menzilli"],
        "regions": ["Shurima"],
        "release_year": 2009,
        "emojis": ["🪃", "💰", "🗡️", "🏜️"],
        "quote_tr": "Kılıcım parayı verene aittir.",
        "ban_quote_tr": "Daha iyi bir teklif bekleyeceğim.",
        "quote_hint": "Dönen haç bıçağıyla dalga temizleyen paralı Shurima askeri"
    },
    "Skarner": {
        "gender": "Erkek",
        "positions": ["Orman", "Üst Koridor"],
        "species": ["Brakern"],
        "resource": "Mana",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Ixtal"],
        "release_year": 2011,
        "emojis": ["🦂", "🪨", "🌐", "💎"],
        "quote_tr": "Ixtal'ın kadim koruyucusunu uyandırdınız!",
        "ban_quote_tr": "Toprağın derinliklerine dönüyorum.",
        "quote_hint": "Devasa taşları fırlatıp kuyruğuyla sürükleyen kadim akrep"
    },
    "Smolder": {
        "gender": "Erkek",
        "positions": ["Alt Koridor", "Orta Koridor"],
        "species": ["Ejderha"],
        "resource": "Mana",
        "range_type": ["Menzilli"],
        "regions": ["Camavor", "Runeterra"],
        "release_year": 2024,
        "emojis": ["🐲", "🔥", "👶", "👑"],
        "quote_tr": "Anneme söyleyeceğim, hepinizi yakacak!",
        "ban_quote_tr": "Anneeee! Beni banladılar!",
        "quote_hint": "Ateş hapşırıp annesini yardıma çağıran yavru imparatorluk ejderhası"
    },
    "Sona": {
        "gender": "Kadın",
        "positions": ["Destek"],
        "species": ["İnsan"],
        "resource": "Mana",
        "range_type": ["Menzilli"],
        "regions": ["Demacia", "Ionia"],
        "release_year": 2010,
        "emojis": ["🎹", "🎶", "🤫", "✨"],
        "quote_tr": "*Etwahl enstrümanının büyüleyici tınısı*",
        "ban_quote_tr": "*Hüzünlü akor melodisi*",
        "quote_hint": "Etwahl adlı çalgısıyla melodiler çalan sessiz müzisyen"
    },
    "Soraka": {
        "gender": "Kadın",
        "positions": ["Destek"],
        "species": ["Tanrı"],
        "resource": "Mana",
        "range_type": ["Menzilli"],
        "regions": ["Targon", "Ionia"],
        "release_year": 2009,
        "emojis": ["🦄", "🍌", "✨", "⭐"],
        "quote_tr": "Yıldızlar yaralarınızı saracak.",
        "ban_quote_tr": "Şifamı hak etmiyorsunuz.",
        "quote_hint": "Kendi canını verip tüm takımı iyileştiren yıldız çocuğu"
    },
    "Swain": {
        "gender": "Erkek",
        "positions": ["Destek", "Orta Koridor", "Alt Koridor"],
        "species": ["İnsan", "Demon"],
        "resource": "Mana",
        "range_type": ["Menzilli"],
        "regions": ["Noxus"],
        "release_year": 2010,
        "emojis": ["🐦‍⬛", "👁️", "👑", "🩸"],
        "quote_tr": "Noxus için bir adım geri atmak, iki adım ileri gitmektir.",
        "ban_quote_tr": "Kuzgunlar sırlarını bana fısıldadı bile.",
        "quote_hint": "Kuzgun iblisiyle ruh toplayan Noxus Büyük Generali"
    },
    "Sylas": {
        "gender": "Erkek",
        "positions": ["Orta Koridor", "Üst Koridor"],
        "species": ["İnsan", "Büyüyle Değişmiş"],
        "resource": "Mana",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Demacia", "Freljord"],
        "release_year": 2019,
        "emojis": ["⛓️", "🪄", "👑", "💥"],
        "quote_tr": "Kırın zincirlerinizi! Büyü hepimizin!",
        "ban_quote_tr": "Demacia yine de yıkılacak.",
        "quote_hint": "Petrisit zincirleriyle başkalarının ultisini çalan Demacia isyancısı"
    },
    "Syndra": {
        "gender": "Kadın",
        "positions": ["Orta Koridor"],
        "species": ["İnsan", "Büyüyle Değişmiş"],
        "resource": "Mana",
        "range_type": ["Menzilli"],
        "regions": ["Ionia"],
        "release_year": 2012,
        "emojis": ["🔮", "👑", "🟣", "⚡"],
        "quote_tr": "Sınırsız bir güç benim elimde!",
        "ban_quote_tr": "Karanlık kürelerimi durduramazsın.",
        "quote_hint": "Karanlık küreleri fırlatıp havada süzülen güç delisi büyücü"
    },
    "TahmKench": {
        "gender": "Erkek",
        "positions": ["Destek", "Üst Koridor"],
        "species": ["Demon", "Ruh"],
        "resource": "Mana",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Bilgewater", "Runeterra"],
        "release_year": 2015,
        "emojis": ["🐸", "🎩", "👅", "🍽️"],
        "quote_tr": "Bana nehirlerin kralı derler evlat!",
        "ban_quote_tr": "Doyumsuzluğum seni bulacak.",
        "quote_hint": "Uzun diliyle yalayarak midesine indiren nehir iblisi yayınbalığı"
    },
    "Taliyah": {
        "gender": "Kadın",
        "positions": ["Orta Koridor", "Orman"],
        "species": ["İnsan"],
        "resource": "Mana",
        "range_type": ["Menzilli"],
        "regions": ["Shurima"],
        "release_year": 2016,
        "emojis": ["🪨", "🏄‍♀️", "🧱", "🏜️"],
        "quote_tr": "Taş taş üstünde bırakmayacağım!",
        "ban_quote_tr": "Taş örgüsü asla bozulmaz.",
        "quote_hint": "Taşların üstünde kayarak devasa duvar ören Shurima'lı taş büyücüsü"
    },
    "Talon": {
        "gender": "Erkek",
        "positions": ["Orta Koridor", "Orman"],
        "species": ["İnsan"],
        "resource": "Mana",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Noxus"],
        "release_year": 2011,
        "emojis": ["🗡️", "🧗", "🩸", "🥷"],
        "quote_tr": "Bıçakların gölgesinde yaşa.",
        "ban_quote_tr": "Duvarlardan atlayıp kaçmadım.",
        "quote_hint": "Bıçak peleriniyle duvarların üstünden sıçrayan Noxus suikastçısı"
    },
    "Taric": {
        "gender": "Erkek",
        "positions": ["Destek"],
        "species": ["İnsan", "Tanrı"],
        "resource": "Mana",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Targon", "Demacia"],
        "release_year": 2009,
        "emojis": ["💎", "✨", "🛡️", "🔨"],
        "quote_tr": "Göz kamaştırıcı bir zarafet!",
        "ban_quote_tr": "Mücevherlerim seni bağışlamaz.",
        "quote_hint": "Targon'un parlak kristalleriyle tüm takımı ölümsüz yapan muhafız"
    },
    "Teemo": {
        "gender": "Erkek",
        "positions": ["Üst Koridor"],
        "species": ["Yordle"],
        "resource": "Mana",
        "range_type": ["Menzilli"],
        "regions": ["Bandle Şehri"],
        "release_year": 2009,
        "emojis": ["🍄", "💨", "🎯", "😈"],
        "quote_tr": "Emir ve görüşlerinize hazırım komutanım!",
        "ban_quote_tr": "Mantarlarım haritada seni bekliyor...",
        "quote_hint": "Haritanın her yerine zehirli mantar döşeyen izci Yordle"
    },
    "Thresh": {
        "gender": "Erkek",
        "positions": ["Destek"],
        "species": ["Ölümsüz"],
        "resource": "Mana",
        "range_type": ["Menzilli"],
        "regions": ["Gölge Adalar"],
        "release_year": 2013,
        "emojis": ["🏮", "🪝", "💀", "⛓️"],
        "quote_tr": "Ruhunu fenerime hapsedeceğim!",
        "ban_quote_tr": "Fenerime er ya da geç gireceksin.",
        "quote_hint": "Kancası ve feneriyle ruh toplayan Gölge Adalar gardiyanı"
    },
    "Tristana": {
        "gender": "Kadın",
        "positions": ["Alt Koridor", "Orta Koridor"],
        "species": ["Yordle"],
        "resource": "Mana",
        "range_type": ["Menzilli"],
        "regions": ["Bandle Şehri"],
        "release_year": 2009,
        "emojis": ["💣", "🚀", "👧", "💥"],
        "quote_tr": "Ateş etmeye doyamıyorum!",
        "ban_quote_tr": "Bozookam soğumaya bırakıldı.",
        "quote_hint": "Devasa topu Boomer ile roket atlayışı yapan topçu Yordle"
    },
    "Trundle": {
        "gender": "Erkek",
        "positions": ["Üst Koridor", "Orman"],
        "species": ["Troll", "Buzdoğumlu"],
        "resource": "Mana",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Freljord"],
        "release_year": 2010,
        "emojis": ["🧌", "🧊", "🦴", "👑"],
        "quote_tr": "Troll Krallığı'na hoş geldiniz!",
        "ban_quote_tr": "Buz sütunumu kafana yiyeceksin.",
        "quote_hint": "Buzdan sopa ve sütunla kule kemiren Troll Kralı"
    },
    "Tryndamere": {
        "gender": "Erkek",
        "positions": ["Üst Koridor"],
        "species": ["İnsan", "Buzdoğumlu"],
        "resource": "Öfke",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Freljord"],
        "release_year": 2009,
        "emojis": ["🗡️", "😡", "👑", "🍗"],
        "quote_tr": "Sol kolum sağ kolumdan çok daha güçlüdür!",
        "ban_quote_tr": "Öfkem asla bitmez!",
        "quote_hint": "5 saniye boyunca ölmeyen Freljord'lu barbar kral"
    },
    "TwistedFate": {
        "gender": "Erkek",
        "positions": ["Orta Koridor", "Alt Koridor"],
        "species": ["İnsan", "Büyüyle Değişmiş"],
        "resource": "Mana",
        "range_type": ["Menzilli"],
        "regions": ["Bilgewater"],
        "release_year": 2009,
        "emojis": ["🃏", "🎩", "💰", "👁️"],
        "quote_tr": "Kaderin kartları benim elimde.",
        "ban_quote_tr": "Şansını başka masada dene.",
        "quote_hint": "Sarı kartla sersemletip ışınlanan kumarbaz kâğıt ustası"
    },
    "Twitch": {
        "gender": "Erkek",
        "positions": ["Alt Koridor", "Orman"],
        "species": ["Büyüyle Değişmiş"],
        "resource": "Mana",
        "range_type": ["Menzilli"],
        "regions": ["Zaun"],
        "release_year": 2009,
        "emojis": ["🐀", "🧀", "🧪", "🏹"],
        "quote_tr": "Ben oradaydım, tam arkandaydım!",
        "ban_quote_tr": "Peynirimi çaldın!",
        "quote_hint": "Görünmez olup arbaletle zehirli oklar yağdıran Zaun lağım faresi"
    },
    "Udyr": {
        "gender": "Erkek",
        "positions": ["Orman", "Üst Koridor"],
        "species": ["İnsan", "Ruh"],
        "resource": "Mana",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Freljord", "Ionia"],
        "release_year": 2009,
        "emojis": ["🐻", "🐅", "🦧", "🦅"],
        "quote_tr": "Kadim ruhlar bedenimde yaşıyor!",
        "ban_quote_tr": "Ayı duruşundan kaçamazsın.",
        "quote_hint": "Ayı, Kaplan, Kaplumbağa ve Anka duruşlarına geçen şaman"
    },
    "Urgot": {
        "gender": "Erkek",
        "positions": ["Üst Koridor"],
        "species": ["Sayborg", "İnsan"],
        "resource": "Mana",
        "range_type": ["Menzilli"],
        "regions": ["Zaun", "Noxus"],
        "release_year": 2010,
        "emojis": ["🦀", "⚙️", "🪚", "🔫"],
        "quote_tr": "Acı seni arındıracak!",
        "ban_quote_tr": "Öğütücümden kaçamazsın.",
        "quote_hint": "Dizlerindeki pompalılarla dönen ve zincirle öğütücüsüne çeken sayborg"
    },
    "Varus": {
        "gender": "Erkek",
        "positions": ["Alt Koridor", "Orta Koridor"],
        "species": ["Darkin", "İnsan"],
        "resource": "Mana",
        "range_type": ["Menzilli"],
        "regions": ["Ionia", "Shurima"],
        "release_year": 2012,
        "emojis": ["🏹", "🟣", "🩸", "🎯"],
        "quote_tr": "İntikam okum kalbini delecek.",
        "ban_quote_tr": "Karanlık yayım gerildi.",
        "quote_hint": "Delici okuyla uzaktan vuran Darkin yay kullanıcısı"
    },
    "Vayne": {
        "gender": "Kadın",
        "positions": ["Alt Koridor", "Üst Koridor"],
        "species": ["İnsan"],
        "resource": "Mana",
        "range_type": ["Menzilli"],
        "regions": ["Demacia"],
        "release_year": 2011,
        "emojis": ["🕶️", "🏹", "🦇", "💨"],
        "quote_tr": "Karanlıkta gizlenen kötülükleri temizleyeceğim.",
        "ban_quote_tr": "Gümüş oklarımdan kaçamazsın.",
        "quote_hint": "Gözlükleriyle takla atıp 3. vuruşta gerçek hasar vuran gece avcısı"
    },
    "Veigar": {
        "gender": "Erkek",
        "positions": ["Orta Koridor", "Alt Koridor"],
        "species": ["Yordle"],
        "resource": "Mana",
        "range_type": ["Menzilli"],
        "regions": ["Bandle Şehri", "Noxus"],
        "release_year": 2009,
        "emojis": ["🧙‍♂️", "⚡", "😈", "🪐"],
        "quote_tr": "Bana küçük deme! Ben kötülüğün ta kendisiyim!",
        "ban_quote_tr": "Karanlık maddem seni yok edecek!",
        "quote_hint": "Yetenek gücü sonsuza kadar biriken minik karanlık büyücü"
    },
    "Velkoz": {
        "gender": "Diğer",
        "positions": ["Destek", "Orta Koridor"],
        "species": ["Hiçlik"],
        "resource": "Mana",
        "range_type": ["Menzilli"],
        "regions": ["Hiçlik"],
        "release_year": 2014,
        "emojis": ["👁️", "🐙", "📐", "⚡"],
        "quote_tr": "Bilgi için parçalayacağım!",
        "ban_quote_tr": "Analiz tamamlanamadı.",
        "quote_hint": "Geometri lazerleri ve 3 dokunacı olan tek gözlü Hiçlik varlığı"
    },
    "Vex": {
        "gender": "Kadın",
        "positions": ["Orta Koridor"],
        "species": ["Yordle"],
        "resource": "Mana",
        "range_type": ["Menzilli"],
        "regions": ["Bandle Şehri", "Gölge Adalar"],
        "release_year": 2021,
        "emojis": ["😒", "👻", "🖤", "🌧️"],
        "quote_tr": "Of ya... Her şey o kadar sıkıcı ki.",
        "ban_quote_tr": "Mükemmel, zaten kimseyle uğraşmak istemiyordum.",
        "quote_hint": "Gölgesiyle atlayıp atılmaları cezalandıran depresif Yordle"
    },
    "Vi": {
        "gender": "Kadın",
        "positions": ["Orman"],
        "species": ["İnsan"],
        "resource": "Mana",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Piltover", "Zaun"],
        "release_year": 2012,
        "emojis": ["🥊", "⚙️", "💥", "🚓"],
        "quote_tr": "Önce yumruklarım konuşur, sonra soruları sorarım!",
        "ban_quote_tr": "Piltover asayişi için iyi bir gün.",
        "quote_hint": "Devasa Hextech eldivenleriyle duvarları delen pembe saçlı fedai"
    },
    "Viego": {
        "gender": "Erkek",
        "positions": ["Orman", "Orta Koridor"],
        "species": ["Ölümsüz"],
        "resource": "Manasız",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Gölge Adalar", "Camavor"],
        "release_year": 2021,
        "emojis": ["👑", "🗡️", "💚", "💔"],
        "quote_tr": "İsolde nerede? Aşkım için tüm dünyayı mahvedeceğim!",
        "ban_quote_tr": "Kara Sis asla durdurulamaz.",
        "quote_hint": "Öldürdüğü şampiyonların bedenine bürünen Mahvolmuş Kral"
    },
    "Viktor": {
        "gender": "Erkek",
        "positions": ["Orta Koridor"],
        "species": ["Sayborg", "İnsan"],
        "resource": "Mana",
        "range_type": ["Menzilli"],
        "regions": ["Zaun", "Piltover"],
        "release_year": 2011,
        "emojis": ["🤖", "⚡", "🦾", "📐"],
        "quote_tr": "Şanlı Evrim'e katılın!",
        "ban_quote_tr": "Gelişime engel olamazsınız.",
        "quote_hint": "Omuzundaki lazer koluyla Şanlı Evrimi savunan dahi mucit"
    },
    "Vladimir": {
        "gender": "Erkek",
        "positions": ["Orta Koridor", "Üst Koridor"],
        "species": ["İnsan", "Büyüyle Değişmiş"],
        "resource": "Can",
        "range_type": ["Menzilli"],
        "regions": ["Noxus", "Camavor"],
        "release_year": 2010,
        "emojis": ["🩸", "🍷", "🦇", "🧛‍♂️"],
        "quote_tr": "Kan nehir gibi akacak!",
        "ban_quote_tr": "Bir kadeh kanla teselli bulurum.",
        "quote_hint": "Kan havuzuna dönüşüp can çalan Noxus'lu hemomanser"
    },
    "Volibear": {
        "gender": "Erkek",
        "positions": ["Üst Koridor", "Orman"],
        "species": ["Tanrı", "Ruh"],
        "resource": "Mana",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Freljord"],
        "release_year": 2011,
        "emojis": ["🐻", "⚡", "❄️", "👑"],
        "quote_tr": "Fırtınanın kükreyişi susmayacak!",
        "ban_quote_tr": "Kuleleriniz bile sizi kurtaramaz.",
        "quote_hint": "Kuleleri devre dışı bırakan devasa yıldırımlı Freljord ayı ilahı"
    },
    "Warwick": {
        "gender": "Erkek",
        "positions": ["Orman", "Üst Koridor"],
        "species": ["Sayborg", "Büyüyle Değişmiş"],
        "resource": "Mana",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Zaun"],
        "release_year": 2009,
        "emojis": ["🐺", "🩸", "⚙️", "🍖"],
        "quote_tr": "Kan kokusu alıyorum!",
        "ban_quote_tr": "Zaun sokakları benden kaçamaz.",
        "quote_hint": "Canı azalan düşmanların kokusunu alıp hızlanan mekanik kurt adam"
    },
    "Xayah": {
        "gender": "Kadın",
        "positions": ["Alt Koridor"],
        "species": ["Vastaya"],
        "resource": "Mana",
        "range_type": ["Menzilli"],
        "regions": ["Ionia"],
        "release_year": 2017,
        "emojis": ["🪶", "🗡️", "💜", "🪽"],
        "quote_tr": "Tüylerim asla hedefini şaşmaz.",
        "ban_quote_tr": "Rakan'la dansımız sürecek.",
        "quote_hint": "Yere bıraktığı keskin tüyleri geri çekerek biçen Vastaya isyancısı"
    },
    "Xerath": {
        "gender": "Erkek",
        "positions": ["Destek", "Orta Koridor"],
        "species": ["Tanrı", "Büyüyle Değişmiş"],
        "resource": "Mana",
        "range_type": ["Menzilli"],
        "regions": ["Shurima"],
        "release_year": 2011,
        "emojis": ["⚡", " sarcophagus", "💎", "☄️"],
        "quote_tr": "Ben saf enerjiyim!",
        "ban_quote_tr": "Lahit prangalarım kırıldı.",
        "quote_hint": "Çok uzaklardan keskin nişancı gibi büyü atan saf enerji büyücüsü"
    },
    "XinZhao": {
        "gender": "Erkek",
        "positions": ["Orman"],
        "species": ["İnsan"],
        "resource": "Mana",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Demacia", "Ionia"],
        "release_year": 2010,
        "emojis": ["🗡️", "🥋", "🛡️", "👑"],
        "quote_tr": "Mızrağım Demacia kralını korur!",
        "ban_quote_tr": "Meydan okumanız yetersiz kaldı.",
        "quote_hint": "Mızrağını çevirip 3 vuruşta havaya kaldıran Demacia baş muhafızı"
    },
    "Yasuo": {
        "gender": "Erkek",
        "positions": ["Orta Koridor", "Üst Koridor", "Alt Koridor"],
        "species": ["İnsan"],
        "resource": "Akış",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Ionia"],
        "release_year": 2013,
        "emojis": ["🌪️", "🗡️", "🍶", "💨"],
        "quote_tr": "Ölüm bir rüzgâr gibidir, hep yanımda...",
        "ban_quote_tr": "Hasagi diye bağıramayacaksın.",
        "quote_hint": "Rüzgar duvarı açıp 'Hasaki' diye bağıran kılıç ustası"
    },
    "Yone": {
        "gender": "Erkek",
        "positions": ["Orta Koridor", "Üst Koridor"],
        "species": ["İnsan", "Ruh"],
        "resource": "Manasız",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Ionia"],
        "release_year": 2020,
        "emojis": ["🗡️", "🎭", "💨", "👻"],
        "quote_tr": "Bir kılıç gerçeği arar, diğeri ise azakana avlar.",
        "ban_quote_tr": "Maskem asla düşmeyecek.",
        "quote_hint": "Ruh formuna geçip çift kılıcıyla fırtına gibi biçen Yasuo'nun abisi"
    },
    "Yorick": {
        "gender": "Erkek",
        "positions": ["Üst Koridor"],
        "species": ["İnsan", "Ölümsüz"],
        "resource": "Mana",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Gölge Adalar"],
        "release_year": 2011,
        "emojis": ["🪦", "🧟", "👻", "⚰️"],
        "quote_tr": "Ölülerin mezarcısı asla yalnız değildir.",
        "ban_quote_tr": "Küreğim seni bekleyecek.",
        "quote_hint": "Küreğiyle mezar kazıp Sis Bakiresi ile kule yıkan mezarcı"
    },
    "Yuumi": {
        "gender": "Kadın",
        "positions": ["Destek"],
        "species": ["Yordle", "Ruh"],
        "resource": "Mana",
        "range_type": ["Menzilli"],
        "regions": ["Bandle Şehri"],
        "release_year": 2019,
        "emojis": ["🐱", "📖", "🐟", "✨"],
        "quote_tr": "Bizi takip et Kitap! Yeni dostlar bulduk!",
        "ban_quote_tr": "Ben de gidip kestiririm o zaman!",
        "quote_hint": "Uçan büyü kitabının üstünde dostlarına yapışan kedi"
    },
    "Zac": {
        "gender": "Diğer",
        "positions": ["Orman", "Üst Koridor", "Destek"],
        "species": ["Golem", "Büyüyle Değişmiş"],
        "resource": "Can",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Zaun"],
        "release_year": 2013,
        "emojis": ["🟢", "🧪", "🦹", "💥"],
        "quote_tr": "Takım elbise giymeliydim...",
        "ban_quote_tr": "Balçıklarım geri toplanacak.",
        "quote_hint": "Sapan gibi fırlayıp peltelere bölünen yeşil Zaun jel devi"
    },
    "Zed": {
        "gender": "Erkek",
        "positions": ["Orta Koridor", "Orman"],
        "species": ["İnsan"],
        "resource": "Enerji",
        "range_type": ["Yakın Dövüş"],
        "regions": ["Ionia"],
        "release_year": 2012,
        "emojis": ["🥷", "🌑", "🗡️", "❌"],
        "quote_tr": "Gölgelerden kaçış yoktur!",
        "ban_quote_tr": "Gölgen bile senden korktu.",
        "quote_hint": "Gölgeleriyle yer değiştirip Ölüm İşareti bırakan ninja suikastçı"
    },
    "Zeri": {
        "gender": "Kadın",
        "positions": ["Alt Koridor"],
        "species": ["İnsan", "Büyüyle Değişmiş"],
        "resource": "Mana",
        "range_type": ["Menzilli"],
        "regions": ["Zaun"],
        "release_year": 2022,
        "emojis": ["⚡", "🛹", "感受", "💚"],
        "quote_tr": "Kıvılcımı çaktım, Zaun arkamda!",
        "ban_quote_tr": "Elektriğim kesilmez!",
        "quote_hint": "Elektrik bataryası ve kıvılcımlarıyla kaykay gibi koşan Zaun kızı"
    },
    "Ziggs": {
        "gender": "Erkek",
        "positions": ["Alt Koridor", "Orta Koridor"],
        "species": ["Yordle"],
        "resource": "Mana",
        "range_type": ["Menzilli"],
        "regions": ["Zaun", "Bandle Şehri", "Piltover"],
        "release_year": 2012,
        "emojis": ["💣", "💥", "🧨", "🤪"],
        "quote_tr": "Patlatalım mı? Hadi her şeyi havaya uçuralım!",
        "ban_quote_tr": "Fitil söndü...",
        "quote_hint": "Kuleleri uzaktan patlatan çılgın bombacı Yordle"
    },
    "Zilean": {
        "gender": "Erkek",
        "positions": ["Destek", "Orta Koridor"],
        "species": ["İnsan", "Büyüyle Değişmiş"],
        "resource": "Mana",
        "range_type": ["Menzilli"],
        "regions": ["Icathia", "Shurima", "Runeterra"],
        "release_year": 2009,
        "emojis": ["⏰", "👴", "💣", "⏳"],
        "quote_tr": "Zamanı geri alabilseydim keşke...",
        "ban_quote_tr": "Geleceğinde beni göreceksin.",
        "quote_hint": "Sırtındaki dev saatle dostlarını ölümden dirilten zaman büyücüsü"
    },
    "Zoe": {
        "gender": "Kadın",
        "positions": ["Orta Koridor", "Destek"],
        "species": ["Tanrı", "İnsan"],
        "resource": "Mana",
        "range_type": ["Menzilli"],
        "regions": ["Targon"],
        "release_year": 2017,
        "emojis": ["✨", "🦋", "🍭", "🕳️"],
        "quote_tr": "Kelebekler, portallar ve devasa yıldızlar!",
        "ban_quote_tr": "Hiç eğlenceli değilsin!",
        "quote_hint": "Portallardan atlayıp uyku balonu fırlatan Targon alacalık sureti"
    },
    "Zyra": {
        "gender": "Kadın",
        "positions": ["Destek", "Orta Koridor", "Orman"],
        "species": ["Büyüyle Değişmiş", "Ruh"],
        "resource": "Mana",
        "range_type": ["Menzilli"],
        "regions": ["Ixtal", "Shurima"],
        "release_year": 2012,
        "emojis": ["🥀", "🌿", "🌱", "👠"],
        "quote_tr": "Dikenlerin arasında can vereceksiniz.",
        "ban_quote_tr": "Tohumlarım filizlenmeye devam edecek.",
        "quote_hint": "Yere tohumlar saçıp tüküren bitkiler yetiştiren sarmaşık kadını"
    }
}

def generate_fallback_meta(champ_id, ddragon_data):
    tags = ddragon_data.get("tags", ["Fighter"])
    partype = ddragon_data.get("partype", "Mana")
    
    pos = ["Orta Koridor"]
    if "Fighter" in tags or "Tank" in tags:
        pos = ["Üst Koridor", "Orman"]
    elif "Marksman" in tags:
        pos = ["Alt Koridor"]
    elif "Support" in tags:
        pos = ["Destek"]
    elif "Assassin" in tags:
        pos = ["Orta Koridor", "Orman"]
    elif "Mage" in tags:
        pos = ["Orta Koridor", "Destek"]
        
    res = "Mana"
    if "Energy" in partype or "Enerji" in partype:
        res = "Enerji"
    elif "None" in partype or "Manasız" in partype or "Öfke" in partype:
        res = "Manasız" if "None" in partype else "Öfke"
        
    range_type = ["Yakın Dövüş"] if ddragon_data.get("stats", {}).get("attackrange", 175) < 300 else ["Menzilli"]
    
    return {
        "gender": "Erkek",
        "positions": pos,
        "species": ["İnsan"],
        "resource": res,
        "range_type": range_type,
        "regions": ["Runeterra"],
        "release_year": 2024,
        "emojis": ["⚔️", "✨", "🛡️", "🔥"],
        "quote_tr": f"{ddragon_data.get('name', champ_id)} savaşa hazır!",
        "ban_quote_tr": "Korkaklar savaştan kaçar.",
        "quote_hint": ddragon_data.get("title", "Runeterra Şampiyonu")
    }

def build_database():
    print("🚀 DDragon Türkiye API'sinden en güncel LoL şampiyon verileri indiriliyor...")
    
    # 1. Get latest version
    ver_url = "https://ddragon.leagueoflegends.com/api/versions.json"
    with urllib.request.urlopen(ver_url, timeout=10) as res:
        versions = json.loads(res.read().decode())
        latest_version = versions[0]
        print(f"📦 En güncel Data Dragon versiyonu: {latest_version}")
        
    # 2. Get champion list in tr_TR
    champs_url = f"https://ddragon.leagueoflegends.com/cdn/{latest_version}/data/tr_TR/champion.json"
    with urllib.request.urlopen(champs_url, timeout=10) as res:
        raw_champs = json.loads(res.read().decode())["data"]
        
    print(f"🎮 Toplam {len(raw_champs)} şampiyon listesi alındı. Detaylar paralel çekiliyor...")
    
    def fetch_details(champ_id):
        u = f"https://ddragon.leagueoflegends.com/cdn/{latest_version}/data/tr_TR/champion/{champ_id}.json"
        try:
            with urllib.request.urlopen(u, timeout=10) as r:
                d = json.loads(r.read().decode())
                return champ_id, d["data"][champ_id]
        except Exception as e:
            print(f"⚠️ {champ_id} detay indirilemedi: {e}")
            return champ_id, None
            
    with concurrent.futures.ThreadPoolExecutor(max_workers=25) as executor:
        details_map = dict(executor.map(fetch_details, raw_champs.keys()))
        
    compiled_db = []
    
    for champ_id, raw in raw_champs.items():
        details = details_map.get(champ_id) or raw
        key_num = raw.get("key", "0")
        
        meta = CHAMPION_METADATA_MAP.get(champ_id)
        if not meta:
            meta = generate_fallback_meta(champ_id, raw)
            
        spells = []
        # Passive
        passive_raw = details.get("passive", {})
        passive_img = passive_raw.get("image", {}).get("full", "")
        spells.append({
            "key": "P",
            "name": passive_raw.get("name", "Pasif"),
            "description": passive_raw.get("description", ""),
            "icon_url": f"https://ddragon.leagueoflegends.com/cdn/{latest_version}/img/passive/{passive_img}" if passive_img else ""
        })
        
        # Q, W, E, R
        keys = ["Q", "W", "E", "R"]
        for idx, sp in enumerate(details.get("spells", [])):
            if idx < 4:
                k_name = keys[idx]
                sp_img = sp.get("image", {}).get("full", "")
                spells.append({
                    "key": k_name,
                    "name": sp.get("name", f"Yetenek {k_name}"),
                    "description": sp.get("description", ""),
                    "icon_url": f"https://ddragon.leagueoflegends.com/cdn/{latest_version}/img/spell/{sp_img}" if sp_img else ""
                })
                
        # Image URLs
        square_img = f"https://ddragon.leagueoflegends.com/cdn/{latest_version}/img/champion/{champ_id}.png"
        splash_img = f"https://ddragon.leagueoflegends.com/cdn/img/champion/splash/{champ_id}_0.jpg"
        loading_img = f"https://ddragon.leagueoflegends.com/cdn/img/champion/loading/{champ_id}_0.jpg"
        
        # Audio URLs (proxyable or direct CDragon)
        choose_vo_url = f"/api/audio/{champ_id}?type=choose"
        ban_vo_url = f"/api/audio/{champ_id}?type=ban"
        remote_choose_vo = f"https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/tr_tr/v1/champion-choose-vo/{key_num}.ogg"
        remote_ban_vo = f"https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/tr_tr/v1/champion-ban-vo/{key_num}.ogg"
        
        champ_entry = {
            "id": champ_id,
            "key": key_num,
            "name": raw.get("name", champ_id),
            "title": raw.get("title", ""),
            "blurb": raw.get("blurb", ""),
            "gender": meta["gender"],
            "positions": meta["positions"],
            "species": meta["species"],
            "resource": meta["resource"],
            "range_type": meta["range_type"],
            "regions": meta["regions"],
            "release_year": meta["release_year"],
            "emojis": meta["emojis"],
            "quotes": {
                "choose_quote_tr": meta["quote_tr"],
                "ban_quote_tr": meta.get("ban_quote_tr", ""),
                "hint": meta.get("quote_hint", ""),
                "choose_audio_url": choose_vo_url,
                "ban_audio_url": ban_vo_url,
                "remote_choose_audio": remote_choose_vo,
                "remote_ban_audio": remote_ban_vo
            },
            "spells": spells,
            "images": {
                "square": square_img,
                "splash": splash_img,
                "loading": loading_img
            },
            "stats": raw.get("stats", {})
        }
        compiled_db.append(champ_entry)
        
    # Sort alphabetically by Turkish name
    compiled_db.sort(key=lambda x: x["name"].lower())
    
    out_path = os.path.join(os.path.dirname(__file__), "champions.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(compiled_db, f, ensure_ascii=False, indent=2)
        
    print(f"✅ {len(compiled_db)} şampiyon içeren veri tabanı başarıyla oluşturuldu:")
    print(f"📁 Dosya: {out_path}")
    return compiled_db

if __name__ == "__main__":
    build_database()
