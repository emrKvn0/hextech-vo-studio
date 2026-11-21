import React, { useState, useEffect, useMemo } from 'react';
import {
  Type, Film, Sparkles, Sliders, Check, Copy, Download, RotateCcw,
  Eye, Layers, Palette, AlignLeft, AlignCenter, AlignRight, Award, Zap, Info
} from 'lucide-react';

export const RECOMMENDED_VIDEO_FONTS = [
  {
    family: 'Cinzel',
    category: 'Sinematik & Lore (Riot / Runeterra Ruhu)',
    badge: '👑 Lore Favorisi',
    desc: 'Riot Games\'in kendi Hextech başlık fontu (Beaufort for LoL) ile neredeyse aynı keskin serif karakterine sahiptir. Azir, Aurelion Sol, Mordekaiser, Pantheon gibi destansı replik videolarında muazzam ağırlık verir.',
    bestFor: 'Şampiyon İsimleri, Destansı Lore Videoları, Shurima / Targon / Noxus Temaları',
    recommendedSpkSize: 46,
    recommendedQuoteSize: 44
  },
  {
    family: 'Montserrat',
    category: 'Modern YouTube & Shorts (Yüksek Okunabilirlik)',
    badge: '🔥 En Dengeli',
    desc: 'Geometrik ve geniş harf aralıklı modern sans-serif. Hem 16:9 masaüstü videolarda hem de telefon ekranında (Shorts/Reels) Türkçe karakterleri (Ğ, Ş, İ, Ö, Ç) kusursuz ve tok gösterir.',
    bestFor: 'Atıf Matrisi, Karşılaşma Replikleri, Hızlı Okunan Altyazılar',
    recommendedSpkSize: 44,
    recommendedQuoteSize: 46
  },
  {
    family: 'Poppins',
    category: 'Modern YouTube & Shorts (Yüksek Okunabilirlik)',
    badge: '⭐ Stüdyo Varsayılanı',
    desc: 'Yuvarlak hatlı, sıcak ve modern. Siyah kontur (Stroke) ve gölge (Drop Shadow) eklendiğinde parlak 4K splash artların üzerinde asla kaybolmaz.',
    bestFor: 'Tüm LoL & LoR Etkileşim Videoları, Genel Amaçlı Altyazı',
    recommendedSpkSize: 44,
    recommendedQuoteSize: 48
  },
  {
    family: 'Marcellus',
    category: 'Sinematik & Lore (Riot / Runeterra Ruhu)',
    badge: '🏛️ Antik & Zarif',
    desc: 'Cinzel\'in küçük harfleri de destekleyen, hafif oyma taş hissi veren sinematik versiyonu. Uzun replik cümlelerinde gözü yormadan epik bir hikaye anlatımı sunar.',
    bestFor: 'Legends of Runeterra Kart Hikayeleri, Karanlık & Epik Diyaloglar',
    recommendedSpkSize: 46,
    recommendedQuoteSize: 48
  },
  {
    family: 'Oswald',
    category: 'Keskin Gaming & E-Spor',
    badge: '⚡ Sıkı & Vurucu',
    desc: 'Dikey olarak daraltılmış (Condensed) güçlü yapı. Uzun cümlelerin tek veya iki satıra taşmadan sığmasını sağlar; Birebir Diyalog (%50-%50 veya Sol/Sağ Kart) düzeninde harika durur.',
    bestFor: 'Birebir Diyaloglar (Sol/Sağ Kart Altı), Uzun Cümleli Şampiyonlar',
    recommendedSpkSize: 48,
    recommendedQuoteSize: 50
  },
  {
    family: 'Rajdhani',
    category: 'Keskin Gaming & E-Spor',
    badge: '🤖 Hextech / Bilimkurgu',
    desc: 'Köşeli ve teknolojik çizgiler. KOD Adı (PROJECT), K/DA, Piltover & Zaun veya fütüristik kostüm etkileşimlerinde modern oyun HUD hissi yaratır.',
    bestFor: 'Kostüm Özel Etkileşimleri, Piltover/Zaun, Hextech Arayüz Videoları',
    recommendedSpkSize: 48,
    recommendedQuoteSize: 50
  },
  {
    family: 'Rubik',
    category: 'Modern YouTube & Shorts (Yüksek Okunabilirlik)',
    badge: '🎯 Tok & Net',
    desc: 'Hafif yuvarlatılmış köşeleriyle hem samimi hem de kalın (Bold/ExtraBold) ağırlıklarda çok yüksek kontrastlı bir görünüm verir.',
    bestFor: 'Şaka / Kışkırtma Replikleri, Dinamik YouTube Derlemeleri',
    recommendedSpkSize: 44,
    recommendedQuoteSize: 46
  },
  {
    family: 'Outfit',
    category: 'Modern YouTube & Shorts (Yüksek Okunabilirlik)',
    badge: '✨ Temiz & Minimal',
    desc: 'Son dönem sinematik oyun kanallarının sıkça tercih ettiği modern ligatürsüz geometrik font. Çok temiz bir ekran görüntüsü bırakır.',
    bestFor: 'Minimalist 4K Splash Art Videoları, Birebir Karşılaşmalar',
    recommendedSpkSize: 44,
    recommendedQuoteSize: 48
  },
  {
    family: 'Exo 2',
    category: 'Keskin Gaming & E-Spor',
    badge: '⚔️ Aksiyon & İtalik',
    desc: 'Özellikle Bold Italic (Kalın İtalik) modunda olay/eylem başlıklarına ("Düşman Azir ile İlk Karşılaşınca") müthiş bir hız ve aksiyon katar.',
    bestFor: 'Olay / Eylem Etiketleri, Savaş & Saldırı Replikleri',
    recommendedSpkSize: 44,
    recommendedQuoteSize: 46
  },
  {
    family: 'Bebas Neue',
    category: 'Keskin Gaming & E-Spor',
    badge: '🎬 Devasa Başlık',
    desc: 'Tamamı büyük harf, sinema afişi ve YouTube thumbnail kalitesinde dikey vurgu. Kısa ve sert repliklerde izleyiciyi ekrana kilitler.',
    bestFor: 'Kısa Vurucu Replikler, Şampiyon İsim Başlıkları',
    recommendedSpkSize: 52,
    recommendedQuoteSize: 54
  },
  {
    family: 'Lora',
    category: 'Sinematik & Lore (Riot / Runeterra Ruhu)',
    badge: '📜 Kitap & Hikaye',
    desc: 'Edebi ve kaligrafik fırça darbelerine sahip serif font. Özellikle İtalik modda "tırnak içi" replikleri bir roman veya parşömen sayfası gibi gösterir.',
    bestFor: 'Duygusal / Felsefi Replikler (Kindred, Jhin, Nasus, Morgana)',
    recommendedSpkSize: 44,
    recommendedQuoteSize: 46
  },
  {
    family: 'Cormorant Garamond',
    category: 'Sinematik & Lore (Riot / Runeterra Ruhu)',
    badge: '🎭 Asil & Dramatik',
    desc: 'Klasik fantezi RPG oyunlarının (Witcher / Dark Souls / Elden Ring tarzı) altyazı estetiğini LoL ve Runeterra videolarına taşır.',
    bestFor: 'Karanlık Lore, Viego / Mahvolmuş Kral, Gölge Adalar Replikleri',
    recommendedSpkSize: 48,
    recommendedQuoteSize: 52
  }
];

const SAMPLE_PRESETS = [
  {
    id: 'azir_asol',
    label: '🃏 LoR: Azir ➔ Aurelion Sol (Giden Atıf)',
    speaker: 'Azir',
    target: 'Aurelion Sol',
    action: 'Düşman Aurelion Sol Kartı Görüldüğünde',
    quote: 'İmparatorluğumun göklerinde yalnızca Shurima\'nın güneşi parlar, ejderha!',
    speakerImg: 'https://cdn.runeterra.ar/assets/img/card/en_us/04SH003-full.webp',
    targetImg: 'https://cdn.runeterra.ar/assets/img/card/en_us/03MT087-full.webp'
  },
  {
    id: 'azir_ascended',
    label: '☀️ LoR: Yükselmiş Azir (04SH003T2) ➔ Xerath',
    speaker: 'Azir (Yükselmiş)',
    target: 'Xerath',
    action: 'İmparatorların Destesi • Seviye Atlayınca',
    quote: 'İhanetin kumlara gömüldü Xerath! Shurima küllerinden yeniden doğdu!',
    speakerImg: 'https://cdn.runeterra.ar/assets/img/card/en_us/04SH003T2-full.webp',
    targetImg: 'https://cdn.runeterra.ar/assets/img/card/en_us/05SH014-full.webp'
  },
  {
    id: 'yasuo_yone',
    label: '⚔️ LoL: Yasuo ➔ Yone (Kanon Karşılaşma)',
    speaker: 'Yasuo',
    target: 'Yone',
    action: 'Düşman Yone ile İlk Karşılaşınca',
    quote: 'Onur rüzgârda savrulup gitse bile, kılıcım hâlâ gerçeği arıyor kardeşim.',
    speakerImg: 'https://ddragon.leagueoflegends.com/cdn/img/champion/splash/Yasuo_0.jpg',
    targetImg: 'https://ddragon.leagueoflegends.com/cdn/img/champion/splash/Yone_0.jpg'
  }
];

function hexToFcpxmlRgba(hex, alpha = 1) {
  const clean = (hex || '#ffffff').replace('#', '');
  const num = parseInt(clean, 16);
  const r = ((num >> 16) & 255) / 255;
  const g = ((num >> 8) & 255) / 255;
  const b = (num & 255) / 255;
  return `${r.toFixed(2)} ${g.toFixed(2)} ${b.toFixed(2)} ${alpha}`;
}

export default function FcpxmlFontSimulatorView() {
  // Kayıtlı FCPXML font ayarlarını yükle
  const savedConfig = useMemo(() => {
    try {
      const raw = localStorage.getItem('lol_fcpxml_style_config');
      return raw ? JSON.parse(raw) : {};
    } catch (e) {
      return {};
    }
  }, []);

  const [selectedPreset, setSelectedPreset] = useState(SAMPLE_PRESETS[0]);
  const [simLayout, setSimLayout] = useState('champion_voices'); // 'champion_voices' | 'versus_dialogue' | 'matrix_default'
  const [simSpeakingSide, setSimSpeakingSide] = useState('left'); // 'left' | 'right'
  const [fontFamily, setFontFamily] = useState(savedConfig.fontFamily || 'Cinzel');
  const [fontFace, setFontFace] = useState(savedConfig.fontFace || 'Bold');
  const [fontSizeSpk, setFontSizeSpk] = useState(savedConfig.fontSizeSpk || 34);
  const [fontSizeQuote, setFontSizeQuote] = useState(savedConfig.fontSizeQuote || 40);
  const [spkColorHex, setSpkColorHex] = useState(savedConfig.spkColorHex || '#40e0f2');
  const [quoteColorHex, setQuoteColorHex] = useState(savedConfig.quoteColorHex || '#ffe047');
  const [strokeColorHex, setStrokeColorHex] = useState(savedConfig.strokeColorHex || '#000000');
  const [strokeWidth, setStrokeWidth] = useState(savedConfig.strokeWidth !== undefined ? savedConfig.strokeWidth : 1.5);
  const [shadowOffset, setShadowOffset] = useState(savedConfig.shadowOffset !== undefined ? savedConfig.shadowOffset : 3);
  const [shadowOpacity, setShadowOpacity] = useState(savedConfig.shadowOpacity !== undefined ? savedConfig.shadowOpacity : 0.95);
  const [alignment, setAlignment] = useState(savedConfig.alignment || 'center');

  // Özel örnek metin alanları
  const [speakerText, setSpeakerText] = useState(SAMPLE_PRESETS[0].speaker);
  const [targetText, setTargetText] = useState(SAMPLE_PRESETS[0].target);
  const [actionText, setActionText] = useState(SAMPLE_PRESETS[0].action);
  const [quoteText, setQuoteText] = useState(SAMPLE_PRESETS[0].quote);

  const [savedToast, setSavedToast] = useState(false);
  const [copiedXml, setCopiedXml] = useState(false);
  const [categoryFilter, setCategoryFilter] = useState('all');

  const handleSelectPreset = (preset) => {
    setSelectedPreset(preset);
    setSpeakerText(preset.speaker);
    setTargetText(preset.target);
    setActionText(preset.action);
    setQuoteText(preset.quote);
  };

  // Her değişiklikte otomatik olarak localStorage'a kaydet (kullanıcı butona basmayı unutsa bile aktarılsın)
  useEffect(() => {
    const cfg = {
      fontFamily,
      fontFace,
      fontSizeSpk: Number(fontSizeSpk),
      fontSizeQuote: Number(fontSizeQuote),
      spkColorHex,
      quoteColorHex,
      strokeColorHex,
      strokeWidth: Number(strokeWidth),
      shadowOffset: Number(shadowOffset),
      shadowOpacity: Number(shadowOpacity),
      alignment
    };
    try {
      localStorage.setItem('lol_fcpxml_style_config', JSON.stringify(cfg));
    } catch (e) {}
  }, [fontFamily, fontFace, fontSizeSpk, fontSizeQuote, spkColorHex, quoteColorHex, strokeColorHex, strokeWidth, shadowOffset, shadowOpacity, alignment]);

  const handleApplyToStudio = () => {
    const cfg = {
      fontFamily,
      fontFace,
      fontSizeSpk: Number(fontSizeSpk),
      fontSizeQuote: Number(fontSizeQuote),
      spkColorHex,
      quoteColorHex,
      strokeColorHex,
      strokeWidth: Number(strokeWidth),
      shadowOffset: Number(shadowOffset),
      shadowOpacity: Number(shadowOpacity),
      alignment
    };
    try {
      localStorage.setItem('lol_fcpxml_style_config', JSON.stringify(cfg));
      setSavedToast(true);
      setTimeout(() => setSavedToast(false), 3000);
    } catch (e) {}
  };

  const handleResetDefaults = () => {
    setFontFamily('Poppins');
    setFontFace('Bold');
    setFontSizeSpk(44);
    setFontSizeQuote(48);
    setSpkColorHex('#40e0f2');
    setQuoteColorHex('#ffe047');
    setStrokeColorHex('#000000');
    setStrokeWidth(1);
    setShadowOffset(3);
    setShadowOpacity(0.95);
    setAlignment('center');
  };

  // Canlı üretilen DaVinci Resolve FCPXML v1.8 örnek kodu
  const generatedFcpxmlSnippet = useMemo(() => {
    const spkRgba = hexToFcpxmlRgba(spkColorHex, 1);
    const quoteRgba = hexToFcpxmlRgba(quoteColorHex, 1);
    const strokeRgba = hexToFcpxmlRgba(strokeColorHex, 1);
    const shadowRgba = `0 0 0 ${shadowOpacity}`;
    const isItalicAttr = fontFace.includes('Italic') ? ' italic="1"' : '';
    const isBoldAttr = fontFace.includes('Bold') || fontFace === 'Black' ? ' bold="1"' : '';

    return `<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE fcpxml>
<fcpxml version="1.8">
  <resources>
    <format id="r1" name="FFVideoFormat2160p60" frameDuration="1/60s" width="2560" height="1440" colorSpace="1-1-1 (Rec. 709)"/>
    <effect id="r_title" name="Basic Title" uid=".../Titles.localized/Bumper:Opener.localized/Basic Title.localized/Basic Title.moti"/>
  </resources>
  <library>
    <event name="FCPXML_Font_Test_Studyo">
      <project name="Font_Test_${fontFamily.replace(/\s+/g, '_')}">
        <sequence format="r1" duration="300/60s">
          <spine>
            <title name="${speakerText.toUpperCase()} -> ${targetText.toUpperCase()}" ref="r_title" offset="0s" duration="300/60s" start="0s">
              <adjust-transform position="0 -34.027778" scale="1 1"/>
              <text>
                <text-style ref="ts_spk">[ ${speakerText.toUpperCase()} ➔ ${targetText.toUpperCase()} • ${actionText} ]</text-style>
                <text-style ref="ts_quote">&#13;&#10;${quoteText}</text-style>
              </text>
              <text-style-def id="ts_spk">
                <text-style font="${fontFamily}" fontSize="${fontSizeSpk}" fontFace="${fontFace}"${isBoldAttr}${isItalicAttr} fontColor="${spkRgba}" strokeColor="${strokeRgba}" strokeWidth="${strokeWidth}" alignment="${alignment}" shadowColor="${shadowRgba}" shadowOffset="${shadowOffset} -${shadowOffset}"/>
              </text-style-def>
              <text-style-def id="ts_quote">
                <text-style font="${fontFamily}" fontSize="${fontSizeQuote}" fontFace="${fontFace}"${isBoldAttr}${isItalicAttr} fontColor="${quoteRgba}" strokeColor="${strokeRgba}" strokeWidth="${strokeWidth}" alignment="${alignment}" shadowColor="${shadowRgba}" shadowOffset="${shadowOffset} -${shadowOffset}"/>
              </text-style-def>
              <param name="Stroke" key="stroke" value="1"/>
              <param name="Stroke Size" key="stroke_size" value="${strokeWidth}"/>
              <param name="Stroke Color" key="stroke_color" value="${strokeRgba}"/>
            </title>
          </spine>
        </sequence>
      </project>
    </event>
  </library>
</fcpxml>`;
  }, [fontFamily, fontFace, fontSizeSpk, fontSizeQuote, spkColorHex, quoteColorHex, strokeColorHex, strokeWidth, shadowOffset, shadowOpacity, alignment, speakerText, targetText, actionText, quoteText]);

  const handleDownloadSampleFcpxml = () => {
    const blob = new Blob([generatedFcpxmlSnippet], { type: 'application/xml;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `DaVinci_Font_Test_${fontFamily.replace(/\s+/g, '_')}.fcpxml`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleCopyFeedback = () => {
    const summary = `Font: ${fontFamily} (${fontFace}) | Eylem Boyutu: ${fontSizeSpk}px | Replik Boyutu: ${fontSizeQuote}px | Stroke: ${strokeWidth}px | Layout: ${simLayout}`;
    navigator.clipboard.writeText(summary);
    setCopiedXml(true);
    setTimeout(() => setCopiedXml(false), 2000);
  };

  // 2560x1440 tuvalindeki font boyutunu önizleme kutusuna (yaklaşık %42 ölçek) oranla
  const previewSpkPx = Math.max(14, Math.round(fontSizeSpk * 0.44));
  const previewQuotePx = Math.max(15, Math.round(fontSizeQuote * 0.46));

  const commonTextStyle = (colorHex, sizePx, forceItalic = false) => {
    const effectiveStrokePx = strokeWidth > 0 ? (strokeWidth * 0.55).toFixed(2) : 0;
    const shadowDist = Math.max(2, shadowOffset * 0.7);
    const shadowColor = `rgba(0, 0, 0, ${shadowOpacity})`;

    // Güçlü 3 katmanlı düşme gölgesi ve ortam karartması (kontur 0 olsa bile asla kaybolmaz)
    const shadows = [
      `${shadowDist}px ${shadowDist}px 3px ${shadowColor}`,
      `-${shadowDist * 0.6}px ${shadowDist * 0.6}px 4px ${shadowColor}`,
      `0px 0px 8px rgba(0, 0, 0, ${Math.min(1, shadowOpacity + 0.1)})`
    ];

    return {
      fontFamily: `'${fontFamily}', sans-serif`,
      fontSize: `${sizePx}px`,
      fontWeight: fontFace.includes('Bold') || fontFace === 'Black' ? 800 : 600,
      fontStyle: forceItalic || fontFace.includes('Italic') ? 'italic' : 'normal',
      color: colorHex,
      textAlign: alignment,
      // paint-order: stroke fill sayesinde kontur harfin içini YEMEZ, harfin dışına çizilir!
      paintOrder: 'stroke fill',
      WebkitTextStroke: effectiveStrokePx > 0 ? `${effectiveStrokePx}px ${strokeColorHex}` : 'none',
      textShadow: shadowOpacity > 0 ? shadows.join(', ') : 'none',
      lineHeight: 1.35,
      letterSpacing: '0.02em'
    };
  };

  const filteredFonts = useMemo(() => {
    if (categoryFilter === 'all') return RECOMMENDED_VIDEO_FONTS;
    return RECOMMENDED_VIDEO_FONTS.filter(f => f.category.includes(categoryFilter));
  }, [categoryFilter]);

  const activeFontMeta = RECOMMENDED_VIDEO_FONTS.find(f => f.family === fontFamily) || RECOMMENDED_VIDEO_FONTS[0];

  return (
    <div className="flex-1 w-full h-full overflow-y-auto pr-1 space-y-6 pb-24 scrollbar-thin">
      {/* Üst Bilgi & Hızlı Kaydetme Barı */}
      <div className="p-5 rounded-2xl bg-gradient-to-r from-[#1d2333] via-[#23293a] to-[#1d2333] border border-amber-500/40 shadow-xl flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4 shrink-0">
        <div className="flex items-start space-x-3.5">
          <div className="w-12 h-12 rounded-2xl bg-amber-500/20 border border-amber-400/50 flex items-center justify-center text-amber-300 shrink-0 shadow-md">
            <Type className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center flex-wrap gap-2">
              <h2 className="text-lg font-black text-amber-300 font-['Cinzel'] tracking-wide">
                DaVinci Resolve FCPXML v1.8 Font &amp; Sahne Simülatörü
              </h2>
              <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-400/40">
                2560×1440 (2K/4K) Gerçek Ölçekli Önizleme
              </span>
            </div>
            <p className="text-xs text-slate-300 mt-1">
              DaVinci Resolve <code className="text-amber-200 font-mono">&lt;text-style&gt;</code> motorunun desteklediği tüm biçimlendirme özelliklerini (Font Family, Bold/Italic, Font Size, RGB Renk, Stroke Kontur, Drop Shadow) ve <strong>Azir ➔ Hedef Karakter</strong> sahne düzenini burada canlı test edip doğrudan FCPXML ihracatına uygulayabilirsin.
            </p>
          </div>
        </div>

        <div className="flex items-center flex-wrap gap-2.5 shrink-0">
          <button
            type="button"
            onClick={handleApplyToStudio}
            className="px-4 py-2.5 rounded-xl bg-gradient-to-r from-amber-400 via-amber-500 to-orange-500 hover:from-amber-300 hover:to-orange-400 text-slate-950 font-black text-xs tracking-wide shadow-lg transition flex items-center space-x-2 cursor-pointer"
          >
            {savedToast ? <Check className="w-4 h-4 stroke-[3]" /> : <Sparkles className="w-4 h-4" />}
            <span>{savedToast ? 'Tüm FCPXML İhracatlarına Uygulandı!' : 'Bu Fontu FCPXML İhracatı İçin Varsayılan Yap'}</span>
          </button>

          <button
            type="button"
            onClick={handleDownloadSampleFcpxml}
            className="px-3.5 py-2.5 rounded-xl bg-[#2b3246] hover:bg-[#353d54] text-amber-200 border border-amber-400/40 font-bold text-xs transition flex items-center space-x-1.5 cursor-pointer"
            title="Bu font ve ayarlarla örnek bir .fcpxml dosyası indirip DaVinci'de hemen test et"
          >
            <Download className="w-4 h-4 text-amber-300" />
            <span>Test .FCPXML İndir</span>
          </button>

          <button
            type="button"
            onClick={handleCopyFeedback}
            className="px-3.5 py-2.5 rounded-xl bg-[#2b3246] hover:bg-[#353d54] text-sky-200 border border-sky-400/40 font-bold text-xs transition flex items-center space-x-1.5 cursor-pointer"
            title="Beğendiğin font ayarını sohbete yapıştırmak için kopyala"
          >
            {copiedXml ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4 text-sky-300" />}
            <span>{copiedXml ? 'Ayar Kopyalandı!' : 'Beğendiğim Ayarı Kopyala'}</span>
          </button>
        </div>
      </div>

      {/* Ana 12 Sütunlu Grid: Sol 7 Sütun Canlı 16:9 DaVinci Monitörü + Font Kartları | Sağ 5 Sütun FCPXML Inspector */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
        
        {/* SOL BÖLÜM (7 Sütun): 16:9 Canlı DaVinci Tuvali & Örnek Sahne Seçici */}
        <div className="xl:col-span-7 space-y-4">
          
          {/* Sahne Layout ve Örnek Kart Seçici */}
          <div className="p-4 rounded-2xl bg-[#232836] border border-slate-700/70 space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="text-xs font-extrabold text-amber-300 uppercase tracking-wider flex items-center gap-1.5">
                <Film className="w-4 h-4 text-amber-400" />
                <span>1. DaVinci FCPXML Sahne Düzeni (Layout) Seçimi:</span>
              </span>
              <div className="flex flex-wrap items-center gap-1.5">
                {[
                  { id: 'champion_voices', label: '🔥 %50 Konuşan (Azir) + %50 Hedef Fotosu (Önerilen)' },
                  { id: 'versus_dialogue', label: '⚔️ Birebir Diyalog (Sol & Sağ Kartlar)' },
                  { id: 'matrix_default', label: '📐 Matris Standart (Sol Kadraj)' }
                ].map(l => (
                  <button
                    key={l.id}
                    type="button"
                    onClick={() => setSimLayout(l.id)}
                    className={`px-3 py-1.5 rounded-xl text-xs font-bold transition cursor-pointer border ${
                      simLayout === l.id
                        ? 'bg-amber-500/25 text-amber-200 border-amber-400 shadow-sm'
                        : 'bg-[#1a1f2c] text-slate-300 border-slate-700 hover:border-slate-500'
                    }`}
                  >
                    {l.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-slate-700/50">
              <span className="text-xs font-bold text-slate-300">Örnek Kart &amp; Splash Art Sahnesi:</span>
              <div className="flex flex-wrap items-center gap-1.5">
                {SAMPLE_PRESETS.map(pr => (
                  <button
                    key={pr.id}
                    type="button"
                    onClick={() => handleSelectPreset(pr)}
                    className={`px-2.5 py-1 rounded-lg text-[11px] font-bold transition cursor-pointer border ${
                      selectedPreset.id === pr.id
                        ? 'bg-indigo-500/30 text-indigo-200 border-indigo-400'
                        : 'bg-[#1a1f2c] text-slate-400 border-slate-700 hover:text-slate-200'
                    }`}
                  >
                    {pr.label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* 16:9 CANLI DAVINCI RESOLVE VIEWER CANVAS */}
          <div className="relative w-full aspect-video rounded-2xl overflow-hidden bg-[#050811] border-2 border-amber-500/50 shadow-[0_20px_60px_rgba(0,0,0,0.85)] select-none">
            
            {/* DaVinci Üst Timecode & Güvenli Bölge (Safe Area) Rehberi */}
            <div className="absolute top-2.5 left-3 right-3 z-30 flex items-center justify-between pointer-events-none text-[10px] font-mono">
              <div className="px-2 py-0.5 rounded bg-black/70 border border-slate-700/80 text-slate-300 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
                <span>REC 01:00:04:12 • 2560×1440 60fps</span>
              </div>
              <div className="px-2.5 py-0.5 rounded bg-amber-500/20 backdrop-blur-md border border-amber-400/50 text-amber-200 font-bold">
                Aktif Font: {fontFamily} ({fontFace})
              </div>
            </div>

            {/* LAYOUT 1: ŞAMPİYONUN SÖYLEDİKLERİ (%50 SOL KONUŞAN AZİR + %50 SAĞ HEDEF FOTOSU) */}
            {simLayout === 'champion_voices' && (
              <div className="relative w-full h-full flex">
                {/* Sol %50: Konuşan Şampiyon - Karakter objesini merkeze hizala (Sol kenar yerine ana karakteri odaklar) */}
                <div className="relative w-1/2 h-full overflow-hidden border-r border-black/40">
                  <img
                    src={selectedPreset.speakerImg}
                    alt={speakerText}
                    className="w-full h-full object-cover object-[25%_center]"
                  />
                  {/* Üst Sol Konuşan Başlığı (lane="3" - DaVinci position="-44.444444 40.277778") */}
                  <div className="absolute top-4 left-1/2 -translate-x-1/2 z-20 whitespace-nowrap">
                    <div className="px-3 py-1 rounded-xl bg-black/60 backdrop-blur-sm border border-cyan-400/40" style={commonTextStyle(spkColorHex, Math.max(13, Math.round(previewSpkPx * 0.9)), false)}>
                      {speakerText.toLocaleUpperCase('tr-TR')}
                    </div>
                  </div>
                </div>

                {/* Sağ %50: Atıfta Bulunulan Hedef Karakter - Karakter objesini merkeze hizala */}
                <div className="relative w-1/2 h-full overflow-hidden">
                  <img
                    src={selectedPreset.targetImg}
                    alt={targetText}
                    className="w-full h-full object-cover object-[75%_center]"
                  />
                  {/* Üst Sağ Hedef Başlığı (lane="4" - DaVinci position="44.444444 40.277778") */}
                  <div className="absolute top-4 left-1/2 -translate-x-1/2 z-20 whitespace-nowrap">
                    <div className="px-3 py-1 rounded-xl bg-black/60 backdrop-blur-sm border border-amber-400/40" style={commonTextStyle('#ffa640', Math.max(13, Math.round(previewSpkPx * 0.9)), false)}>
                      {targetText.toLocaleUpperCase('tr-TR')}
                    </div>
                  </div>
                </div>

                {/* Alt Orta Güvenli Bölge (Y = -540px / lane="2"): DaVinci'deki Küçültülmüş Zarif Buzlu Cam Replik Şeridi */}
                <div className="absolute bottom-4 left-[16%] right-[16%] z-20 flex flex-col items-center justify-center px-5 py-2 rounded-xl bg-black/75 backdrop-blur-md border border-white/15 shadow-2xl">
                  <div style={commonTextStyle(spkColorHex, Math.max(11, Math.round(previewSpkPx * 0.82)), true)}>
                    [ {speakerText.toLocaleUpperCase('tr-TR')} ➔ {targetText.toLocaleUpperCase('tr-TR')} • {actionText} ]
                  </div>
                  <div className="mt-0.5 text-center" style={commonTextStyle(quoteColorHex, Math.max(12, Math.round(previewQuotePx * 0.85)), false)}>
                    “{quoteText}”
                  </div>
                </div>
              </div>
            )}

            {/* LAYOUT 2: BİREBİR DİYALOG (SOL & SAĞ ARALIKLI KARTLAR) */}
            {simLayout === 'versus_dialogue' && (
              <div className="relative w-full h-full bg-[radial-gradient(ellipse_at_center,_#162238_0%,_#050811_100%)] flex flex-col justify-between p-6">
                {/* Üst Orta Etkileşim Başlığı (lane="3") */}
                <div className="mt-4 z-20 flex flex-col items-center gap-1.5">
                  <span style={commonTextStyle(quoteColorHex, Math.max(13, Math.round(previewSpkPx * 0.9)), true)}>
                    {actionText}
                  </span>
                  {/* Sıra Değiştirme Butonu (Sol / Sağ test simülasyonu) */}
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => setSimSpeakingSide('left')}
                      className={`px-2.5 py-0.5 rounded text-[10px] font-mono font-bold transition cursor-pointer border ${
                        simSpeakingSide === 'left'
                          ? 'bg-rose-500 text-white border-rose-400 shadow'
                          : 'bg-slate-900/80 text-slate-400 border-slate-700'
                      }`}
                    >
                      Konuşan: Sol ({speakerText})
                    </button>
                    <button
                      type="button"
                      onClick={() => setSimSpeakingSide('right')}
                      className={`px-2.5 py-0.5 rounded text-[10px] font-mono font-bold transition cursor-pointer border ${
                        simSpeakingSide === 'right'
                          ? 'bg-rose-500 text-white border-rose-400 shadow'
                          : 'bg-slate-900/80 text-slate-400 border-slate-700'
                      }`}
                    >
                      Konuşan: Sağ ({targetText})
                    </button>
                  </div>
                </div>

                {/* Sol ve Sağ Aralıklı Karakter Kartları (scale="0.44 0.44") */}
                <div className="grid grid-cols-2 gap-8 px-4 my-auto items-center z-10">
                  {/* Sol Kart (Soldaki Şampiyon) */}
                  <div className={`flex flex-col items-center transition-all duration-300 ${simSpeakingSide === 'left' ? '-translate-y-3' : 'opacity-70 translate-y-3'}`}>
                    <div className={`w-full aspect-video rounded-xl overflow-hidden transition-all duration-300 ${
                      simSpeakingSide === 'left'
                        ? 'border-4 border-rose-500 shadow-[0_0_30px_rgba(244,63,94,0.5)] scale-[1.02]'
                        : 'border border-slate-700 shadow-md brightness-75'
                    }`}>
                      <img src={selectedPreset.speakerImg} alt={speakerText} className="w-full h-full object-cover" />
                    </div>
                    {simSpeakingSide === 'left' ? (
                      <>
                        <div className="mt-3 px-2" style={commonTextStyle(spkColorHex, previewSpkPx, false)}>
                          {speakerText.toLocaleUpperCase('tr-TR')}
                        </div>
                        <div className="mt-0.5 px-2" style={commonTextStyle(quoteColorHex, Math.max(12, previewQuotePx - 2), false)}>
                          “{quoteText}”
                        </div>
                      </>
                    ) : (
                      <div className="mt-3 px-2 text-xs font-mono text-slate-400">
                        ({speakerText} sırasını bekliyor...)
                      </div>
                    )}
                  </div>

                  {/* Sağ Kart (Sağdaki Şampiyon) */}
                  <div className={`flex flex-col items-center transition-all duration-300 ${simSpeakingSide === 'right' ? '-translate-y-3' : 'opacity-70 translate-y-3'}`}>
                    <div className={`w-full aspect-video rounded-xl overflow-hidden transition-all duration-300 ${
                      simSpeakingSide === 'right'
                        ? 'border-4 border-rose-500 shadow-[0_0_30px_rgba(244,63,94,0.5)] scale-[1.02]'
                        : 'border border-slate-700 shadow-md brightness-75'
                    }`}>
                      <img src={selectedPreset.targetImg} alt={targetText} className="w-full h-full object-cover" />
                    </div>
                    {simSpeakingSide === 'right' ? (
                      <>
                        <div className="mt-3 px-2" style={commonTextStyle(spkColorHex, previewSpkPx, false)}>
                          {targetText.toLocaleUpperCase('tr-TR')}
                        </div>
                        <div className="mt-0.5 px-2" style={commonTextStyle(quoteColorHex, Math.max(12, previewQuotePx - 2), false)}>
                          “{quoteText}”
                        </div>
                      </>
                    ) : (
                      <div className="mt-3 px-2 text-xs font-mono text-slate-400">
                        ({targetText} sırasını bekliyor...)
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* LAYOUT 3: ATIF MATRİSİ STANDART (SOL KADRAJ + SAĞ EYLEM) */}
            {simLayout === 'matrix_default' && (
              <div className="relative w-full h-full bg-[#060a14] p-6 flex items-center">
                {/* Sol Üst Görsel (position="-430 160" scale="0.6") */}
                <div className="w-[58%] flex flex-col items-center">
                  <div className="w-full aspect-video rounded-xl overflow-hidden border border-amber-400/50 shadow-2xl">
                    <img src={selectedPreset.speakerImg} alt={speakerText} className="w-full h-full object-cover" />
                  </div>
                  {/* Görsel Altı Altyazı (position="-430 -480") */}
                  <div className="mt-3 w-full">
                    <div style={commonTextStyle(spkColorHex, previewSpkPx, false)}>
                      {speakerText.toLocaleUpperCase('tr-TR')}
                    </div>
                    <div className="mt-0.5" style={commonTextStyle(quoteColorHex, previewQuotePx, false)}>
                      {quoteText}
                    </div>
                  </div>
                </div>

                {/* Sağ Üst Olay / Eylem Etiketi (X=2090 Y=890) */}
                <div className="w-[42%] pl-6 flex flex-col items-center justify-center">
                  <div className="p-3 rounded-xl bg-black/40 border border-amber-500/30">
                    <div style={commonTextStyle(quoteColorHex, previewSpkPx, true)}>
                      {actionText}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/*Aktif Font Hakkında İpucu Kartı */}
          <div className="p-4 rounded-2xl bg-gradient-to-r from-indigo-950/60 via-[#1e2436] to-amber-950/40 border border-indigo-400/40 flex items-start space-x-3">
            <Award className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
            <div className="text-xs space-y-1">
              <div className="flex items-center gap-2">
                <span className="font-black text-amber-300 text-sm">{activeFontMeta.family}</span>
                <span className="px-2 py-0.5 rounded-md bg-amber-500/20 text-amber-200 font-bold text-[10px] border border-amber-400/30">
                  {activeFontMeta.badge}
                </span>
                <span className="text-slate-400 font-medium">• {activeFontMeta.category}</span>
              </div>
              <p className="text-slate-200 leading-relaxed">{activeFontMeta.desc}</p>
              <p className="text-indigo-300 font-semibold">
                💡 En İyi Kullanım: <span className="text-slate-200 font-normal">{activeFontMeta.bestFor}</span>
              </p>
            </div>
          </div>

          {/* 12 ÖNERİLEN VİDEO FONTU HIZLI SEÇİM GALERİSİ */}
          <div className="p-4 rounded-2xl bg-[#232836] border border-slate-700/70 space-y-3.5">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <h3 className="text-xs font-extrabold text-amber-300 uppercase tracking-wider flex items-center gap-1.5">
                <Sparkles className="w-4 h-4 text-amber-400" />
                <span>2. LoL &amp; Runeterra Videoları İçin Önerilen Font Aileleri (Tıkla &amp; Dene)</span>
              </h3>
              <div className="flex items-center gap-1 text-[11px]">
                {[
                  { id: 'all', label: 'Tümü (12)' },
                  { id: 'Sinematik', label: '👑 Sinematik & Lore' },
                  { id: 'Modern', label: '🔥 Modern YouTube' },
                  { id: 'Keskin', label: '⚡ Keskin Gaming' }
                ].map(cat => (
                  <button
                    key={cat.id}
                    type="button"
                    onClick={() => setCategoryFilter(cat.id)}
                    className={`px-2.5 py-1 rounded-lg font-bold transition cursor-pointer ${
                      categoryFilter === cat.id
                        ? 'bg-amber-500 text-slate-950'
                        : 'bg-[#181c26] text-slate-300 hover:text-white'
                    }`}
                  >
                    {cat.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5 max-h-[480px] overflow-y-auto pr-1.5 scrollbar-thin">
              {filteredFonts.map(f => {
                const isSelected = fontFamily === f.family;
                return (
                  <button
                    key={f.family}
                    type="button"
                    onClick={() => {
                      setFontFamily(f.family);
                      setFontSizeSpk(f.recommendedSpkSize);
                      setFontSizeQuote(f.recommendedQuoteSize);
                    }}
                    className={`p-3 rounded-xl text-left transition cursor-pointer border flex flex-col justify-between ${
                      isSelected
                        ? 'bg-gradient-to-r from-amber-500/25 via-amber-500/15 to-indigo-500/20 border-amber-400 ring-1 ring-amber-400/50 shadow-md'
                        : 'bg-[#191d28] border-slate-700/70 hover:border-slate-500'
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span
                        className="text-base font-bold text-slate-100 truncate"
                        style={{ fontFamily: `'${f.family}', sans-serif` }}
                      >
                        {f.family}
                      </span>
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold shrink-0 ${
                        isSelected ? 'bg-amber-400 text-slate-950' : 'bg-slate-800 text-amber-300 border border-amber-500/30'
                      }`}>
                        {f.badge}
                      </span>
                    </div>

                    <div
                      className="mt-2 text-xs text-amber-200/95 truncate"
                      style={{ fontFamily: `'${f.family}', sans-serif` }}
                    >
                      “İmparatorluğumun göklerinde yalnızca Shurima parlar!”
                    </div>

                    <div className="mt-1.5 text-[10px] text-slate-400 line-clamp-1">
                      {f.bestFor}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

        </div>

        {/* SAĞ BÖLÜM (5 Sütun): FCPXML v1.8 Biçimlendirme Denetleyicisi (Inspector) */}
        <div className="xl:col-span-5 space-y-4">
          <div className="p-5 rounded-2xl bg-[#232836] border border-slate-700/80 shadow-xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-700/70 pb-3">
              <div className="flex items-center space-x-2">
                <Sliders className="w-4 h-4 text-amber-400" />
                <h3 className="text-sm font-black text-slate-100 uppercase tracking-wider">
                  FCPXML &lt;text-style&gt; Denetleyicisi
                </h3>
              </div>
              <button
                type="button"
                onClick={handleResetDefaults}
                className="text-xs text-slate-400 hover:text-amber-300 flex items-center gap-1 cursor-pointer font-semibold"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Sıfırla</span>
              </button>
            </div>

            {/* 1. Özel Font Family & Font Face */}
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="text-[11px] font-bold text-slate-300">
                  Font Ailesi (<code className="text-amber-300">font</code>)
                </label>
                <select
                  value={fontFamily}
                  onChange={e => setFontFamily(e.target.value)}
                  className="w-full bg-[#161a24] border border-slate-600 focus:border-amber-400 rounded-xl px-3 py-2 text-xs text-slate-100 font-bold outline-none"
                >
                  {RECOMMENDED_VIDEO_FONTS.map(f => (
                    <option key={f.family} value={f.family}>
                      {f.family} ({f.badge})
                    </option>
                  ))}
                </select>
              </div>

              <div className="space-y-1">
                <label className="text-[11px] font-bold text-slate-300">
                  Yazı Tipi Yüzü (<code className="text-amber-300">fontFace</code>)
                </label>
                <select
                  value={fontFace}
                  onChange={e => setFontFace(e.target.value)}
                  className="w-full bg-[#161a24] border border-slate-600 focus:border-amber-400 rounded-xl px-3 py-2 text-xs text-slate-100 font-bold outline-none"
                >
                  <option value="Bold">Bold (Kalın - Önerilen)</option>
                  <option value="Bold Italic">Bold Italic (Kalın İtalik)</option>
                  <option value="Regular">Regular (Normal)</option>
                  <option value="Italic">Italic (İtalik)</option>
                  <option value="Black">Black (Ekstra Kalın)</option>
                </select>
              </div>
            </div>

            {/* 2. Font Boyutları (2560x1440 Timeline Ölçeğinde) */}
            <div className="grid grid-cols-2 gap-3 pt-1">
              <div className="p-3 rounded-xl bg-[#181c26] border border-slate-700/70 space-y-1.5">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-bold text-cyan-300">Konuşmacı / Eylem Boyutu</span>
                  <span className="font-mono font-black text-amber-300">{fontSizeSpk} pt</span>
                </div>
                <input
                  type="range"
                  min="28"
                  max="72"
                  value={fontSizeSpk}
                  onChange={e => setFontSizeSpk(Number(e.target.value))}
                  className="w-full accent-cyan-400 cursor-pointer"
                />
              </div>

              <div className="p-3 rounded-xl bg-[#181c26] border border-slate-700/70 space-y-1.5">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-bold text-amber-300">Replik Altyazı Boyutu</span>
                  <span className="font-mono font-black text-amber-300">{fontSizeQuote} pt</span>
                </div>
                <input
                  type="range"
                  min="28"
                  max="76"
                  value={fontSizeQuote}
                  onChange={e => setFontSizeQuote(Number(e.target.value))}
                  className="w-full accent-amber-400 cursor-pointer"
                />
              </div>
            </div>

            {/* 3. Renk Seçiciler (fontColor & strokeColor) */}
            <div className="grid grid-cols-3 gap-2.5 pt-1">
              <div className="p-2.5 rounded-xl bg-[#181c26] border border-slate-700/70 flex items-center justify-between">
                <div>
                  <div className="text-[10px] font-bold text-slate-300">Konuşmacı Rengi</div>
                  <div className="text-[10px] font-mono text-cyan-300">{spkColorHex}</div>
                </div>
                <input
                  type="color"
                  value={spkColorHex}
                  onChange={e => setSpkColorHex(e.target.value)}
                  className="w-7 h-7 rounded cursor-pointer bg-transparent border-0"
                />
              </div>

              <div className="p-2.5 rounded-xl bg-[#181c26] border border-slate-700/70 flex items-center justify-between">
                <div>
                  <div className="text-[10px] font-bold text-slate-300">Replik Rengi</div>
                  <div className="text-[10px] font-mono text-amber-300">{quoteColorHex}</div>
                </div>
                <input
                  type="color"
                  value={quoteColorHex}
                  onChange={e => setQuoteColorHex(e.target.value)}
                  className="w-7 h-7 rounded cursor-pointer bg-transparent border-0"
                />
              </div>

              <div className="p-2.5 rounded-xl bg-[#181c26] border border-slate-700/70 flex items-center justify-between">
                <div>
                  <div className="text-[10px] font-bold text-slate-300">Kontur (Stroke)</div>
                  <div className="text-[10px] font-mono text-slate-400">{strokeColorHex}</div>
                </div>
                <input
                  type="color"
                  value={strokeColorHex}
                  onChange={e => setStrokeColorHex(e.target.value)}
                  className="w-7 h-7 rounded cursor-pointer bg-transparent border-0"
                />
              </div>
            </div>

            {/* 4. Kontur Kalınlığı (strokeWidth) & Gölge (shadowOffset) */}
            <div className="grid grid-cols-2 gap-3 pt-1">
              <div className="p-3 rounded-xl bg-[#181c26] border border-slate-700/70 space-y-1.5">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-bold text-slate-200">Kontur (<code className="text-amber-300">strokeWidth</code>)</span>
                  <span className="font-mono font-black text-emerald-300">{strokeWidth} px</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="4"
                  step="0.5"
                  value={strokeWidth}
                  onChange={e => setStrokeWidth(Number(e.target.value))}
                  className="w-full accent-emerald-400 cursor-pointer"
                />
                <div className="text-[10px] text-slate-400">
                  DaVinci'de yazının kaybolmaması için 1.0 - 2.0 arası önerilir.
                </div>
              </div>

              <div className="p-3 rounded-xl bg-[#181c26] border border-slate-700/70 space-y-1.5">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-bold text-slate-200">Gölge (<code className="text-amber-300">shadowOffset</code>)</span>
                  <span className="font-mono font-black text-sky-300">{shadowOffset} px</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="8"
                  step="1"
                  value={shadowOffset}
                  onChange={e => setShadowOffset(Number(e.target.value))}
                  className="w-full accent-sky-400 cursor-pointer"
                />
                <div className="text-[10px] text-slate-400">
                  Parlak kart görsellerinde okunabilirliği artırır.
                </div>
              </div>
            </div>

            {/* 5. Örnek Metin Düzenleyici */}
            <div className="space-y-2.5 pt-2 border-t border-slate-700/70">
              <div className="text-xs font-extrabold text-amber-300 uppercase tracking-wider">
                Canlı Örnek Metinleri Değiştir
              </div>
              <div className="grid grid-cols-2 gap-2.5">
                <div>
                  <label className="text-[10px] font-bold text-slate-400">Konuşan Şampiyon (Sol %50)</label>
                  <input
                    type="text"
                    value={speakerText}
                    onChange={e => setSpeakerText(e.target.value)}
                    className="w-full mt-0.5 bg-[#161a24] border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-100"
                  />
                </div>
                <div>
                  <label className="text-[10px] font-bold text-slate-400">Hedef Karakter (Sağ %50)</label>
                  <input
                    type="text"
                    value={targetText}
                    onChange={e => setTargetText(e.target.value)}
                    className="w-full mt-0.5 bg-[#161a24] border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-100"
                  />
                </div>
              </div>
              <div>
                <label className="text-[10px] font-bold text-slate-400">Olay / Eylem Açıklaması</label>
                <input
                  type="text"
                  value={actionText}
                  onChange={e => setActionText(e.target.value)}
                  className="w-full mt-0.5 bg-[#161a24] border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-100"
                />
              </div>
              <div>
                <label className="text-[10px] font-bold text-slate-400">Replik Sözü (Türkçe Karakter Testi: ĞÜŞİÖÇ)</label>
                <textarea
                  rows={2}
                  value={quoteText}
                  onChange={e => setQuoteText(e.target.value)}
                  className="w-full mt-0.5 bg-[#161a24] border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-100 resize-none"
                />
              </div>
            </div>

            {/* 6. Canlı FCPXML v1.8 Kodu Önizlemesi */}
            <div className="space-y-1.5 pt-2 border-t border-slate-700/70">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-extrabold text-indigo-300 font-mono">
                  Üretilen DaVinci FCPXML v1.8 &lt;text-style-def&gt; Kodu
                </span>
                <span className="text-[10px] text-slate-400">UTF-8 • Rec.709</span>
              </div>
              <pre className="p-3 rounded-xl bg-[#0b0e17] border border-slate-800 text-[10px] font-mono text-emerald-300 overflow-x-auto max-h-40 leading-relaxed select-all">
                {generatedFcpxmlSnippet}
              </pre>
            </div>

          </div>
        </div>

      </div>
    </div>
  );
}
