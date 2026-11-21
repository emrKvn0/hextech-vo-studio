import React, { useState, useRef, useEffect } from 'react';
import { 
  Film, X, Download, Copy, Check, Sparkles, Loader2, 
  FolderOpen, Sliders, CheckSquare, Clock, AlertCircle,
  Package, Music, Terminal, Cpu, Zap, RotateCcw, Type,
  MessageSquare, Volume2
} from 'lucide-react';
import { RECOMMENDED_VIDEO_FONTS } from './FcpxmlFontSimulatorView';

export default function DaVinciExportModal({ 
  isOpen, 
  onClose, 
  selectedItems = [], 
  defaultTimelineName = 'LoL_Secilen_Atiflar',
  layoutMode = 'matrix_default',
  onClearSelection 
}) {
  const [timelineName, setTimelineName] = useState(defaultTimelineName);
  const [activeLayoutMode, setActiveLayoutMode] = useState(layoutMode);
  const [gapSeconds, setGapSeconds] = useState(0.2);
  const [includeSplash, setIncludeSplash] = useState(true);
  const [includeActionLabel, setIncludeActionLabel] = useState(true);
  const [includeSubtitles, setIncludeSubtitles] = useState(() => {
    try {
      const saved = localStorage.getItem('lol_fcpxml_include_subtitles');
      return saved !== 'false';
    } catch (e) {
      return true;
    }
  });
  const [bundleFolder, setBundleFolder] = useState(true);
  const [fontFamily, setFontFamily] = useState('Montserrat');
  const [fontFace, setFontFace] = useState('Bold');
  const [fontSizeSpk, setFontSizeSpk] = useState(34);
  const [fontSizeQuote, setFontSizeQuote] = useState(40);
  const [strokeWidth, setStrokeWidth] = useState(1);
  const [isItalicSpk, setIsItalicSpk] = useState(true);
  const [isItalicQuote, setIsItalicQuote] = useState(false);
  const [spkColorHex, setSpkColorHex] = useState('#40e0f2');
  const [quoteColorHex, setQuoteColorHex] = useState('#ffe047');
  const [shadowOffset, setShadowOffset] = useState(3);
  const [shadowOpacity, setShadowOpacity] = useState(95);
  const [alignment, setAlignment] = useState('center');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [copiedPath, setCopiedPath] = useState(false);

  // Canlı Terminal & Progress State
  const [logs, setLogs] = useState([]);
  const [progress, setProgress] = useState({ current: 0, total: 0, percent: 0, text: '', speaker: '' });
  const [autoScroll, setAutoScroll] = useState(true);
  const [showConfig, setShowConfig] = useState(true);
  const terminalEndRef = useRef(null);

  useEffect(() => {
    setTimelineName(defaultTimelineName);
  }, [defaultTimelineName]);

  useEffect(() => {
    setActiveLayoutMode(layoutMode);
  }, [layoutMode]);

  useEffect(() => {
    if (isOpen) {
      try {
        const raw = localStorage.getItem('lol_fcpxml_style_config');
        if (raw) {
          const cfg = JSON.parse(raw);
          if (cfg.fontFamily) setFontFamily(cfg.fontFamily);
          if (cfg.fontFace) setFontFace(cfg.fontFace);
          if (cfg.fontSizeSpk) setFontSizeSpk(Number(cfg.fontSizeSpk));
          if (cfg.fontSizeQuote) setFontSizeQuote(Number(cfg.fontSizeQuote));
          if (cfg.strokeWidth !== undefined) setStrokeWidth(Number(cfg.strokeWidth));
          if (cfg.isItalicSpk !== undefined) setIsItalicSpk(Boolean(cfg.isItalicSpk));
          if (cfg.isItalicQuote !== undefined) setIsItalicQuote(Boolean(cfg.isItalicQuote));
          if (cfg.spkColorHex) setSpkColorHex(cfg.spkColorHex);
          if (cfg.quoteColorHex) setQuoteColorHex(cfg.quoteColorHex);
          if (cfg.shadowOffset !== undefined) setShadowOffset(Number(cfg.shadowOffset));
          if (cfg.shadowOpacity !== undefined) setShadowOpacity(Number(cfg.shadowOpacity));
          if (cfg.alignment) setAlignment(cfg.alignment);
        }
      } catch (e) {}
    }
  }, [isOpen]);

  useEffect(() => {
    if (autoScroll && terminalEndRef.current) {
      terminalEndRef.current.scrollTop = terminalEndRef.current.scrollHeight;
    }
  }, [logs, autoScroll]);

  if (!isOpen) return null;

  const handleExport = async () => {
    if (selectedItems.length === 0) return;
    setLoading(true);
    setError(null);
    setResult(null);
    setShowConfig(false); // Dışa aktarım başlayınca terminal ekranına odaklan
    const modeDesc = includeSubtitles
      ? `Font: ${fontFamily} ${fontFace} • Replik Metinleri Aktif`
      : 'Yalnızca Ses & 4K Görseller (Replik metinleri ve Whisper kapalı)';
    setLogs([{
      time: new Date().toLocaleTimeString(),
      type: 'init',
      text: `Dışa aktarım oturumu başlatıldı (${selectedItems.length} replik işlenecek • ${modeDesc})...`
    }]);
    setProgress({ current: 0, total: selectedItems.length, percent: 0, text: '', speaker: '' });

    try {
      const response = await fetch('http://127.0.0.1:8080/api/davinci-export-stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          timeline_name: timelineName || 'LoL_Secilen_Atiflar',
          gap_seconds: !isNaN(parseFloat(gapSeconds)) && parseFloat(gapSeconds) >= 0 ? parseFloat(gapSeconds) : 0.2,
          fps: 60,
          include_splash: includeSplash,
          include_action_label: includeActionLabel,
          include_subtitles: includeSubtitles,
          bundle_folder: bundleFolder,
          layout_mode: activeLayoutMode,
          font_family: fontFamily,
          font_face: fontFace,
          font_size_spk: Number(fontSizeSpk) || 34,
          font_size_quote: Number(fontSizeQuote) || 40,
          stroke_width: Number(strokeWidth) !== undefined ? Number(strokeWidth) : 1,
          is_italic_spk: isItalicSpk,
          is_italic_quote: isItalicQuote,
          spk_color_hex: spkColorHex,
          quote_color_hex: quoteColorHex,
          shadow_offset: Number(shadowOffset) || 3,
          shadow_opacity: Number(shadowOpacity) || 95,
          alignment: alignment || 'center',
          action_pos_x: 2090,
          action_pos_y: 890,
          action_zoom: 0.64,
          items: selectedItems
        })
      });

      if (!response.ok) {
        throw new Error(`Sunucu hatası: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const blocks = buffer.split('\n\n');
        buffer = blocks.pop() || '';

        for (const block of blocks) {
          const trimmed = block.trim();
          if (!trimmed.startsWith('data:')) continue;
          const jsonStr = trimmed.replace(/^data:\s*/, '');
          try {
            const data = JSON.parse(jsonStr);
            const timeStr = new Date().toLocaleTimeString();

            setLogs(prev => [...prev, {
              time: timeStr,
              type: data.type || 'info',
              text: data.message || '',
              speaker: data.speaker,
              transcript: data.transcript
            }]);

            if (data.total > 0 && typeof data.current === 'number') {
              const pct = Math.round((data.current / data.total) * 100);
              setProgress({
                current: data.current,
                total: data.total,
                percent: pct,
                text: data.transcript || (data.message || ''),
                speaker: data.speaker || ''
              });
            }

            if (data.type === 'done' && data.result) {
              setResult(data.result);
            } else if (data.type === 'error') {
              setError(data.message || 'Dışa aktarım sırasında bir hata oluştu');
            }
          } catch (e) {
            console.error("SSE parse hatası:", e);
          }
        }
      }
    } catch (err) {
      console.error("DaVinci Export Hatası:", err);
      setError(err.message || 'Timeline oluşturulurken bir hata meydana geldi.');
    } finally {
      setLoading(false);
    }
  };

  const copyPathToClipboard = (path) => {
    if (!path) return;
    navigator.clipboard.writeText(path);
    setCopiedPath(true);
    setTimeout(() => setCopiedPath(false), 2000);
  };

  const handleDownload = (filePath) => {
    if (!filePath) return;
    const downloadUrl = `http://127.0.0.1:8080/api/davinci-download?file=${encodeURIComponent(filePath)}`;
    const a = document.createElement('a');
    a.href = downloadUrl;
    a.download = filePath.split(/[\\/]/).pop();
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-5 md:p-6 bg-black/85 backdrop-blur-md animate-in fade-in duration-200">
      <div className="relative w-full max-w-2xl lg:max-w-3xl h-[82vh] max-h-[720px] bg-[#050D1E] border border-amber-500/40 rounded-2xl shadow-2xl flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        
        {/* Modal Header */}
        <div className="shrink-0 flex items-center justify-between px-5 sm:px-6 py-3.5 border-b border-slate-800 bg-gradient-to-r from-amber-500/10 via-[#061022] to-cyan-500/10">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-xl bg-amber-500/20 border border-amber-400/50 flex items-center justify-center text-amber-300 shadow">
              <Film className="w-4.5 h-4.5" />
            </div>
            <div>
              <h3 className="text-base sm:text-lg font-black text-amber-300 font-['Cinzel'] tracking-wide">
                DaVinci Resolve Timeline İhracatı
              </h3>
              <p className="text-[11px] sm:text-xs text-slate-300 font-medium">
                4K Splash Art Duvar Kağıtları • Doğrudan WAV Sesleri • Güvenli Bölge Altyazılar
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-400 hover:text-white flex items-center justify-center transition cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Modal Scrollable Body (Görünmez akıcı scroll bar) */}
        <div className="flex-1 overflow-y-auto min-h-0 p-4 sm:p-5 md:p-6 space-y-4 no-scrollbar">
          
          {error && (
            <div className="p-3.5 rounded-xl bg-rose-950/40 border border-rose-500/60 text-rose-300 text-xs flex items-center space-x-2.5">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Canlı Terminal & Progress Ekranı (Dışa aktarım çalışırken veya tamamlandığında) */}
          {(!showConfig && (loading || logs.length > 0)) ? (
            <div className="space-y-4">
              
              {/* Donanım & İlerleme Kartı */}
              <div className="p-4 rounded-xl bg-gradient-to-r from-[#071329] via-[#091833] to-[#040e1f] border border-amber-500/40 shadow-lg space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded-full bg-emerald-500/15 border border-emerald-500/40 text-[11px] font-bold text-emerald-300">
                      <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                      <Cpu className="w-3.5 h-3.5 text-emerald-400" />
                      <span>CUDA GPU Hızlandırma Aktif (RTX 5060 Ti • float16)</span>
                    </div>
                  </div>
                  <div className="text-right font-mono text-xs font-black text-amber-300">
                    {progress.current} / {progress.total || selectedItems.length} ({progress.percent}%)
                  </div>
                </div>

                {/* Progress Bar */}
                <div className="w-full h-2.5 bg-slate-900 rounded-full overflow-hidden border border-slate-700/80 p-0.5">
                  <div 
                    className="h-full bg-gradient-to-r from-amber-500 via-yellow-400 to-cyan-400 rounded-full transition-all duration-300 ease-out shadow-sm"
                    style={{ width: `${Math.min(100, Math.max(0, progress.percent))}%` }}
                  />
                </div>

                {/* Güncel Replik / Whisper Önizleme Kartı */}
                {progress.text && (
                  <div className="p-2.5 rounded-lg bg-black/50 border border-amber-500/20 text-xs space-y-1">
                    <div className="flex items-center space-x-1.5 text-[10px] font-bold text-amber-400/90 uppercase tracking-wider">
                      <Zap className="w-3 h-3 text-amber-400" />
                      <span>{progress.speaker ? `${progress.speaker} Replik Metni` : 'Çözülen Replik'}:</span>
                    </div>
                    <div className="text-slate-100 font-medium italic line-clamp-2 pl-2 border-l-2 border-amber-400">
                      "{progress.text}"
                    </div>
                  </div>
                )}
              </div>

              {/* Terminal Penceresi */}
              <div className="rounded-xl border border-slate-700/80 bg-[#070b14] shadow-2xl overflow-hidden flex flex-col">
                {/* Terminal Header */}
                <div className="flex items-center justify-between px-3.5 py-2 bg-[#0d1322] border-b border-slate-800 text-[11px] font-mono">
                  <div className="flex items-center space-x-2">
                    <div className="flex space-x-1.5">
                      <span className="w-2.5 h-2.5 rounded-full bg-rose-500/80"></span>
                      <span className="w-2.5 h-2.5 rounded-full bg-amber-500/80"></span>
                      <span className="w-2.5 h-2.5 rounded-full bg-emerald-500/80"></span>
                    </div>
                    <span className="text-slate-400 pl-1 font-bold flex items-center space-x-1">
                      <Terminal className="w-3.5 h-3.5 text-cyan-400" />
                      <span className="text-slate-300">Canlı Dışa Aktarım Terminali</span>
                    </span>
                  </div>

                  <div className="flex items-center space-x-2 text-[10px]">
                    <button
                      type="button"
                      onClick={() => setAutoScroll(!autoScroll)}
                      className={`px-2 py-0.5 rounded cursor-pointer border transition ${
                        autoScroll 
                          ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40' 
                          : 'bg-slate-800 text-slate-400 border-slate-700'
                      }`}
                    >
                      {autoScroll ? 'Oto-Kaydır: Açık' : 'Oto-Kaydır: Kapalı'}
                    </button>
                    <button
                      type="button"
                      onClick={() => setLogs([])}
                      className="px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-slate-200 border border-slate-700 cursor-pointer transition"
                    >
                      Temizle
                    </button>
                  </div>
                </div>

                {/* Terminal Body */}
                <div 
                  ref={terminalEndRef}
                  className="p-3.5 font-mono text-[11px] leading-relaxed max-h-56 overflow-y-auto space-y-1 select-text scrollbar-thin scrollbar-thumb-slate-700"
                >
                  {logs.length === 0 ? (
                    <div className="text-slate-500 italic">Terminal logları bekleniyor...</div>
                  ) : (
                    logs.map((lg, i) => {
                      let badge = null;
                      if (lg.type === 'whisper_done' || lg.type === 'whisper') {
                        badge = <span className="text-emerald-400 font-bold bg-emerald-950/60 px-1.5 py-0.2 rounded border border-emerald-500/30">[WHISPER CUDA]</span>;
                      } else if (lg.type === 'whisper_start') {
                        badge = <span className="text-yellow-400 font-bold bg-yellow-950/60 px-1.5 py-0.2 rounded border border-yellow-500/30">[WHISPER AI]</span>;
                      } else if (lg.type === 'processing' || lg.type === 'audio') {
                        badge = <span className="text-cyan-400 font-bold bg-cyan-950/60 px-1.5 py-0.2 rounded border border-cyan-500/30">[JIT AUDIO]</span>;
                      } else if (lg.type === 'xml') {
                        badge = <span className="text-indigo-400 font-bold bg-indigo-950/60 px-1.5 py-0.2 rounded border border-indigo-500/30">[FCPXML v1.8]</span>;
                      } else if (lg.type === 'zip') {
                        badge = <span className="text-amber-400 font-bold bg-amber-950/60 px-1.5 py-0.2 rounded border border-amber-500/30">[ZIP ARŞİV]</span>;
                      } else if (lg.type === 'done') {
                        badge = <span className="text-emerald-300 font-black bg-emerald-900/80 px-1.5 py-0.2 rounded border border-emerald-400">[TAMAMLANDI]</span>;
                      } else if (lg.type === 'error') {
                        badge = <span className="text-rose-400 font-bold bg-rose-950/80 px-1.5 py-0.2 rounded border border-rose-500">[HATA]</span>;
                      } else {
                        badge = <span className="text-slate-400 font-bold">[SİSTEM]</span>;
                      }

                      return (
                        <div key={i} className="flex items-start space-x-2">
                          <span className="text-slate-500 shrink-0">{lg.time}</span>
                          <span className="shrink-0">{badge}</span>
                          <span className={`${
                            lg.type === 'whisper_done' ? 'text-amber-200 font-semibold' :
                            lg.type === 'done' ? 'text-emerald-300 font-bold' :
                            lg.type === 'error' ? 'text-rose-300' :
                            'text-slate-300'
                          }`}>
                            {lg.text}
                          </span>
                        </div>
                      );
                    })
                  )}
                  {loading && (
                    <div className="flex items-center space-x-2 text-cyan-400 text-xs pt-1">
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      <span>İşlem yürütülüyor, replikler derleniyor...</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Sonuç Kartı ve İndirme Butonları (Tamamlandığında) */}
              {result && (
                <div className="space-y-4 pt-2 animate-in fade-in duration-300">
                  <div className="p-4 rounded-xl bg-emerald-950/30 border border-emerald-500/50 flex items-start space-x-3.5">
                    <div className="w-8 h-8 rounded-lg bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 flex items-center justify-center shrink-0">
                      <Check className="w-4 h-4 stroke-[3]" />
                    </div>
                    <div>
                      <h4 className="text-sm font-bold text-emerald-300">
                        Timeline Dosyaları Başarıyla Hazırlandı!
                      </h4>
                      <p className="text-xs text-slate-300 mt-1">
                        Toplam <span className="font-bold text-amber-300">{result.clips_count}</span> adet replik ve 4K görsel, <span className="font-bold text-cyan-300">{result.gap_seconds}s</span> aralıkla hizalandı.
                      </p>
                    </div>
                  </div>

                  {/* Download Buttons */}
                  <div className="space-y-2.5">
                    {result.zip_path && (
                      <button
                        onClick={() => handleDownload(result.zip_path)}
                        className="w-full p-3.5 rounded-xl bg-gradient-to-r from-amber-500/25 via-amber-500/35 to-cyan-500/25 hover:from-amber-500/35 hover:to-cyan-500/35 border-2 border-amber-400 text-amber-200 font-bold flex items-center justify-between transition cursor-pointer shadow-lg group"
                      >
                        <div className="flex items-center space-x-3 text-left">
                          <div className="w-9 h-9 rounded-lg bg-amber-500/30 border border-amber-400 flex items-center justify-center text-amber-300 group-hover:scale-105 transition">
                            <Package className="w-5 h-5" />
                          </div>
                          <div>
                            <div className="text-sm font-extrabold text-amber-300 flex items-center space-x-2">
                              <span>Tüm Proje Paketini İndir (.ZIP)</span>
                              <span className="px-2 py-0.5 rounded text-[10px] bg-emerald-500/20 text-emerald-300 font-mono border border-emerald-400/40">
                                Sesler + Görseller + XML
                              </span>
                            </div>
                            <p className="text-[11px] text-slate-300 font-normal">
                              Tüm replik WAV seslerini ve 4K splash görsellerini derli toplu klasörlenmiş tek bir zip dosyası olarak indir.
                            </p>
                          </div>
                        </div>
                        <div className="w-8 h-8 rounded-lg bg-amber-400 text-slate-950 flex items-center justify-center shrink-0 group-hover:translate-y-0.5 transition">
                          <Download className="w-4 h-4 stroke-[3]" />
                        </div>
                      </button>
                    )}

                    <div className="grid grid-cols-2 gap-3">
                      <button
                        onClick={() => handleDownload(result.fcpxml_path)}
                        className="p-3 rounded-xl bg-slate-900/80 hover:bg-slate-800 border border-amber-500/40 text-amber-200 font-bold text-xs flex flex-col items-center justify-center space-y-1 transition cursor-pointer group shadow"
                      >
                        <Download className="w-4 h-4 text-amber-300 group-hover:scale-110 transition" />
                        <span className="text-xs font-extrabold text-amber-300">Yalnızca .fcpxml İndir</span>
                        <span className="text-[10px] text-slate-400 font-mono">DaVinci Resolve 18/19</span>
                      </button>

                      <button
                        onClick={() => handleDownload(result.xml_path)}
                        className="p-3 rounded-xl bg-slate-900/80 hover:bg-slate-800 border border-cyan-500/40 text-cyan-200 font-bold text-xs flex flex-col items-center justify-center space-y-1 transition cursor-pointer group shadow"
                      >
                        <Download className="w-4 h-4 text-cyan-300 group-hover:scale-110 transition" />
                        <span className="text-xs font-extrabold text-cyan-300">Yalnızca .xml İndir (FCP7)</span>
                        <span className="text-[10px] text-slate-400 font-mono">Premiere / FCP7</span>
                      </button>
                    </div>
                  </div>

                  {/* Direct Path Box */}
                  <div className="p-3.5 rounded-xl bg-[#040A18] border border-slate-700 space-y-2">
                    <div className="flex items-center justify-between text-xs text-slate-300 font-medium">
                      <span className="flex items-center space-x-1.5">
                        <FolderOpen className="w-3.5 h-3.5 text-amber-400" />
                        <span className="font-bold text-amber-300">Proje Klasörü (Sesler &amp; Görseller):</span>
                      </span>
                      <button
                        onClick={() => copyPathToClipboard(result.project_dir || result.fcpxml_path)}
                        className="flex items-center space-x-1 text-xs font-bold text-cyan-400 hover:text-cyan-300 cursor-pointer"
                      >
                        {copiedPath ? (
                          <>
                            <Check className="w-3.5 h-3.5 text-emerald-400" />
                            <span className="text-emerald-400">Kopyalandı!</span>
                          </>
                        ) : (
                          <>
                            <Copy className="w-3.5 h-3.5" />
                            <span>Klasör Yolunu Kopyala</span>
                          </>
                        )}
                      </button>
                    </div>
                    <div className="p-2.5 rounded-lg bg-black/60 font-mono text-[11px] text-slate-300 break-all select-all border border-slate-800">
                      {result.project_dir || result.fcpxml_path}
                    </div>
                  </div>
                </div>
              )}

              {/* Alt Butonlar */}
              <div className="flex items-center justify-between pt-2">
                <button
                  type="button"
                  onClick={() => setShowConfig(true)}
                  disabled={loading}
                  className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-xs font-bold text-slate-200 cursor-pointer transition flex items-center space-x-1.5"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  <span>Ayarlara Dön</span>
                </button>

                {result && (
                  <button
                    onClick={onClose}
                    className="px-5 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-black text-xs cursor-pointer transition shadow"
                  >
                    Kapat
                  </button>
                )}
              </div>

            </div>
          ) : (
            /* Configuration Form */
            <div className="space-y-4.5">
              
              {/* Selected Count & Info */}
              <div className="p-3.5 rounded-xl bg-[#061022] border border-amber-500/30 flex items-center justify-between">
                <div className="flex items-center space-x-2.5">
                  <CheckSquare className="w-5 h-5 text-amber-400" />
                  <div>
                    <span className="text-sm font-extrabold text-slate-100 font-mono">
                      {selectedItems.length} Replik Seçildi
                    </span>
                    <p className="text-[11px] text-slate-400">
                      Tüm replikler belirlenen boşluklarla sıralı bir video projesine dönüştürülecek.
                    </p>
                  </div>
                </div>
                {logs.length > 0 && (
                  <button
                    type="button"
                    onClick={() => setShowConfig(false)}
                    className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-bold text-amber-300 border border-amber-500/40 cursor-pointer transition flex items-center space-x-1.5"
                  >
                    <Terminal className="w-3.5 h-3.5 text-cyan-400" />
                    <span>Terminali Gör</span>
                  </button>
                )}
                {onClearSelection && (
                  <button
                    onClick={onClearSelection}
                    className="text-xs text-rose-400 hover:text-rose-300 font-bold cursor-pointer ml-auto"
                  >
                    Seçimi Temizle
                  </button>
                )}
              </div>

              {/* Timeline Name Input */}
              <div className="space-y-1.5">
                <label className="text-xs font-extrabold text-slate-300 uppercase tracking-wider">
                  Timeline / Proje Adı
                </label>
                <input
                  type="text"
                  value={timelineName}
                  onChange={e => setTimelineName(e.target.value)}
                  placeholder="LoL_Secilen_Atiflar"
                  className="w-full bg-[#030914] border border-slate-700 focus:border-amber-400 rounded-xl px-3.5 py-2 text-sm text-slate-100 font-medium outline-none transition"
                />
              </div>

              {/* Replik Metinleri Dahil Et / Etme Seçici */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-extrabold text-amber-300 uppercase tracking-wider flex items-center space-x-1.5">
                    <MessageSquare className="w-3.5 h-3.5 text-amber-400" />
                    <span>Replik Metinleri &amp; Altyazı Şablonu</span>
                  </label>
                  <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full font-bold ${
                    includeSubtitles 
                      ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30' 
                      : 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
                  }`}>
                    {includeSubtitles ? 'Metinler + Whisper Açık' : 'Yalnızca Ses & Görsel'}
                  </span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => {
                      setIncludeSubtitles(true);
                      try { localStorage.setItem('lol_fcpxml_include_subtitles', 'true'); } catch (e) {}
                    }}
                    className={`p-3 rounded-xl text-left transition cursor-pointer border flex flex-col justify-between ${
                      includeSubtitles
                        ? 'bg-gradient-to-r from-amber-500/20 via-amber-500/10 to-amber-500/5 border-amber-400 ring-1 ring-amber-400/50'
                        : 'bg-[#030914] border-slate-800 hover:border-slate-700'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className={`text-xs font-black ${includeSubtitles ? 'text-amber-300' : 'text-slate-300'}`}>
                        Replik Metinlerini Dahil Et
                      </span>
                      {includeSubtitles && <Check className="w-3.5 h-3.5 text-amber-400" />}
                    </div>
                    <p className="text-[11px] text-slate-400 mt-1 leading-relaxed">
                      Seslerle senkron replik metinleri, karakter başlıkları ve eksik metinler için Whisper GPU transkripsiyonu dahil edilir.
                    </p>
                  </button>

                  <button
                    type="button"
                    onClick={() => {
                      setIncludeSubtitles(false);
                      try { localStorage.setItem('lol_fcpxml_include_subtitles', 'false'); } catch (e) {}
                    }}
                    className={`p-3 rounded-xl text-left transition cursor-pointer border flex flex-col justify-between ${
                      !includeSubtitles
                        ? 'bg-gradient-to-r from-cyan-500/20 via-cyan-500/10 to-cyan-500/5 border-cyan-400 ring-1 ring-cyan-400/50'
                        : 'bg-[#030914] border-slate-800 hover:border-slate-700'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className={`text-xs font-black ${!includeSubtitles ? 'text-cyan-300' : 'text-slate-300'}`}>
                        Metinleri Dahil Etme
                      </span>
                      {!includeSubtitles && <Check className="w-3.5 h-3.5 text-cyan-400" />}
                    </div>
                    <p className="text-[11px] text-slate-400 mt-1 leading-relaxed">
                      Sadece ses ve 4K Splash Art kullanılır. Text/altyazı şablonu ve replik metinleri gelmez, Whisper çalıştırılmaz.
                    </p>
                  </button>
                </div>
              </div>

              {/* DaVinci Resolve FCPXML Layout Mode Selector */}
              <div className="space-y-2">
                <label className="text-xs font-extrabold text-amber-300 uppercase tracking-wider flex items-center space-x-1.5">
                  <Sliders className="w-3.5 h-3.5 text-amber-400" />
                  <span>DaVinci FCPXML Sahne &amp; Görsel Düzeni (Layout)</span>
                </label>
                <div className="grid grid-cols-1 gap-2">
                  {[
                    {
                      id: 'champion_voices',
                      title: '1. Karakterin Söyledikleri & Replikleri Düzeni (Atıfta %50 Konuşan / %50 Hedef Fotosu)',
                      desc: 'Örn: Azir konuşurken Sol %50 Azir, Sağ %50 atıfta bulunduğu karakterin (Aurelion Sol, Xerath vb.) fotosu yer alır; üstte isimleri, altta ise sesle senkron Türkçe eylem ve replik yazar. Genel repliklerde ise %100 tam ekran olur.'
                    },
                    {
                      id: 'versus_dialogue',
                      title: '2. Birebir Diyalog Düzeni (Sol & Sağ Aralıklı Kartlar • Sıralı Konuşma)',
                      desc: 'İki karakter sol ve sağda kendi kapladıkları boyutta, aralarında boşlukla birbirini bekler. Sırayla biri konuşur altında repliği çıkar, sonra diğeri konuşur onun altında repliği çıkar.'
                    },
                    {
                      id: 'matrix_default',
                      title: '3. Atıf Matrisi Standart Düzeni (Sol Kadraj + Sağ Eylem Başlığı)',
                      desc: 'Konuşan şampiyon sol üstte (X=-430, Y=160, Zoom=0.60), altyazı altta ve olay/eylem etiketi sağda yer alır.'
                    }
                  ].map(lOpt => {
                    const isSelectedLayout = activeLayoutMode === lOpt.id;
                    return (
                      <button
                        key={lOpt.id}
                        type="button"
                        onClick={() => setActiveLayoutMode(lOpt.id)}
                        className={`p-3 rounded-xl text-left transition cursor-pointer border ${
                          isSelectedLayout
                            ? 'bg-gradient-to-r from-amber-500/20 via-amber-500/10 to-cyan-500/15 border-amber-400 ring-1 ring-amber-400/50'
                            : 'bg-[#030914] border-slate-800 hover:border-slate-600'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <span className={`text-xs font-black ${isSelectedLayout ? 'text-amber-300' : 'text-slate-200'}`}>
                            {lOpt.title}
                          </span>
                          {isSelectedLayout && (
                            <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-amber-500 text-slate-950">
                              Aktif Layout
                            </span>
                          )}
                        </div>
                        <p className="text-[11px] text-slate-400 mt-1 leading-relaxed">
                          {lOpt.desc}
                        </p>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Font Family & Boyut Seçici */}
              {includeSubtitles ? (
                <div className="p-3.5 rounded-xl bg-[#061022] border border-slate-700/80 space-y-2.5">
                  <div className="flex items-center justify-between">
                    <label className="text-xs font-extrabold text-amber-300 uppercase tracking-wider flex items-center space-x-1.5">
                      <Type className="w-3.5 h-3.5 text-amber-400" />
                      <span>FCPXML Altyazı Font Ailesi &amp; Boyutu</span>
                    </label>
                    <span className="text-[11px] text-slate-400">
                      Canlı önizleme için üst menüdeki <strong className="text-rose-300">FCPXML Font &amp; Sahne</strong> sekmesini kullanabilirsin
                    </span>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-4 gap-2.5">
                    <div className="sm:col-span-2">
                      <select
                        value={fontFamily}
                        onChange={e => setFontFamily(e.target.value)}
                        className="w-full bg-[#030914] border border-slate-700 focus:border-amber-400 rounded-xl px-3 py-2 text-xs text-slate-100 font-bold outline-none"
                        style={{ fontFamily: `'${fontFamily}', sans-serif` }}
                      >
                        {(RECOMMENDED_VIDEO_FONTS || []).map(f => (
                          <option key={f.family} value={f.family}>
                            {f.family} — {f.badge}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <select
                        value={fontFace}
                        onChange={e => setFontFace(e.target.value)}
                        className="w-full bg-[#030914] border border-slate-700 focus:border-amber-400 rounded-xl px-3 py-2 text-xs text-amber-300 font-bold outline-none"
                        title="Font Kalınlığı (Font Face)"
                      >
                        {['Regular', 'Medium', 'SemiBold', 'Bold', 'ExtraBold', 'Black', 'Bold Italic'].map(face => (
                          <option key={face} value={face}>{face}</option>
                        ))}
                      </select>
                    </div>
                    <div className="flex items-center space-x-2 bg-[#030914] border border-slate-700 rounded-xl px-3 py-1.5">
                      <span className="text-[11px] text-slate-400">Boyut:</span>
                      <input
                        type="number"
                        min="28"
                        max="76"
                        value={fontSizeQuote}
                        onChange={e => setFontSizeQuote(Number(e.target.value))}
                        className="w-full bg-transparent text-right font-mono text-xs font-black text-amber-300 outline-none"
                      />
                      <span className="text-[10px] font-mono text-slate-400">pt</span>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="p-3.5 rounded-xl bg-cyan-950/25 border border-cyan-500/30 flex items-start space-x-3">
                  <Volume2 className="w-4 h-4 text-cyan-400 shrink-0 mt-0.5" />
                  <div>
                    <div className="text-xs font-black text-cyan-300">
                      Replik Metinleri Devre Dışı (Saf Ses &amp; Görsel Modu)
                    </div>
                    <div className="text-[11px] text-slate-300 mt-0.5 leading-relaxed">
                      Replik metinleri dahil edilmeyecek, altyazı ve başlık şablonları oluşturulmayacak ve Whisper GPU transkripsiyonu çalıştırılmayacaktır.
                    </div>
                  </div>
                </div>
              )}

              {/* Gap Selector */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-extrabold text-slate-300 uppercase tracking-wider flex items-center space-x-1.5">
                    <Clock className="w-3.5 h-3.5 text-cyan-400" />
                    <span>Replikler Arası Boşluk (Gap Süresi)</span>
                  </label>
                  <div className="flex items-center space-x-1.5 bg-[#030914] border border-amber-500/50 focus-within:border-amber-400 focus-within:ring-1 focus-within:ring-amber-400 rounded-lg px-2.5 py-1">
                    <input
                      type="number"
                      step="0.05"
                      min="0"
                      max="10"
                      value={gapSeconds}
                      onChange={e => {
                        const v = e.target.value;
                        setGapSeconds(v === '' ? '' : Number(v));
                      }}
                      className="w-16 bg-transparent text-right font-mono text-xs font-black text-amber-300 outline-none"
                    />
                    <span className="text-[11px] font-mono font-bold text-amber-400">sn</span>
                  </div>
                </div>

                <div className="grid grid-cols-5 gap-2">
                  {[0.0, 0.1, 0.2, 0.3, 0.5].map(val => (
                    <button
                      key={val}
                      type="button"
                      onClick={() => setGapSeconds(val)}
                      className={`py-2 rounded-xl text-xs font-bold font-mono transition cursor-pointer border ${
                        Number(gapSeconds) === val
                          ? 'bg-amber-500/30 text-amber-300 border-amber-400 ring-1 ring-amber-400'
                          : 'bg-[#030914] text-slate-300 border-slate-700 hover:border-slate-500'
                      }`}
                    >
                      {val}s {val === 0.2 ? '★' : ''}
                    </button>
                  ))}
                </div>
              </div>

              {/* 4K Splash Toggle */}
              <div className="p-3.5 rounded-xl bg-[#061022] border border-slate-700/80 flex items-center justify-between">
                <div>
                  <div className="text-xs font-extrabold text-slate-200">
                    4K Duvar Kağıtlarını (Splash Art) Dahil Et
                  </div>
                  <div className="text-[11px] text-slate-400 mt-0.5">
                    Ana karakterin ve varsa atıf yapılan hedef karakter kostümünün 4K görsellerini indirir.
                  </div>
                </div>
                <input
                  type="checkbox"
                  checked={includeSplash}
                  onChange={e => setIncludeSplash(e.target.checked)}
                  className="w-4 h-4 accent-amber-400 rounded cursor-pointer"
                />
              </div>

              {/* Event Action Template Toggle (Hem metinler aktifken hem de metinler kapalıyken gösterilebilir) */}
              <div className="p-3.5 rounded-xl bg-[#061022] border border-slate-700/80 flex items-center justify-between">
                <div>
                  <div className="flex items-center space-x-2">
                    <span className="text-xs font-extrabold text-amber-300">
                      Türkçeleştirilmiş Olay / Eylem Yazısını Göster
                    </span>
                    <span className="px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 text-[10px] font-mono border border-amber-400/30">
                      Senkron
                    </span>
                  </div>
                  <div className="text-[11px] text-slate-300 mt-0.5">
                    Olayın ve satın alınan eşyanın tam Türkçe adı (Örn: <span className="text-amber-200 italic font-semibold">"Ebedi Kılıç Satın Alınca", "Mahvolmuş Kralın Kılıcı Satın Alınca", "Düşman Graves ile İlk Karşılaşınca"</span>) alt kompakt şeritte sesle senkron görünür.
                  </div>
                </div>
                <input
                  type="checkbox"
                  checked={includeActionLabel}
                  onChange={e => setIncludeActionLabel(e.target.checked)}
                  className="w-4 h-4 accent-amber-400 rounded cursor-pointer"
                />
              </div>

              {/* Bundle Folder Toggle */}
              <div className="p-3.5 rounded-xl bg-[#061022] border border-amber-500/40 bg-gradient-to-r from-amber-500/5 to-cyan-500/5 flex items-center justify-between">
                <div className="space-y-0.5 pr-3">
                  <div className="flex items-center space-x-2">
                    <Package className="w-4 h-4 text-amber-400" />
                    <span className="text-xs font-extrabold text-amber-300">
                      Ses ve Görselleri Proje Klasöründe Paketle (.ZIP Hazırla)
                    </span>
                    <span className="px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 text-[10px] font-mono border border-emerald-400/30">
                      Önerilen
                    </span>
                  </div>
                  <div className="text-[11px] text-slate-300">
                    Tüm replik seslerini (<span className="text-amber-200 font-mono">DaVinci_Exports/{timelineName || 'Proje'}/Sesler/</span>) ve 4K görselleri ayrı bir klasörde toplar.
                  </div>
                  <div className="text-[10px] text-slate-400">
                    DaVinci'de "Media Offline" hatası almazsınız ve projeyi tek tıkla ZIP olarak indirebilirsiniz.
                  </div>
                </div>
                <input
                  type="checkbox"
                  checked={bundleFolder}
                  onChange={e => setBundleFolder(e.target.checked)}
                  className="w-4 h-4 accent-amber-400 rounded cursor-pointer shrink-0"
                />
              </div>

            </div>
          )}

        </div>

        {/* Modal Footer (Sabit alt bar - asla kaybolmaz ve taşmaz) */}
        {showConfig && (
          <div className="shrink-0 px-5 py-3.5 sm:px-6 sm:py-4 bg-[#030914] border-t border-amber-500/30 shadow-[0_-8px_25px_rgba(0,0,0,0.6)] z-20">
            <button
              type="button"
              onClick={handleExport}
              disabled={loading || selectedItems.length === 0}
              className="w-full py-3 sm:py-3.5 rounded-xl bg-gradient-to-r from-amber-500 via-amber-400 to-amber-600 hover:from-amber-400 hover:to-amber-500 disabled:opacity-50 text-slate-950 font-black text-xs sm:text-sm tracking-wide transition flex items-center justify-center space-x-2 cursor-pointer shadow-xl active:scale-[0.99]"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin text-slate-950" />
                  <span>{includeSubtitles ? '4K Görseller & Timeline Hazırlanıyor...' : 'Sesler & Görseller Hazırlanıyor...'}</span>
                </>
              ) : (
                <>
                  <Film className="w-4 h-4 text-slate-950" />
                  <span>
                    DaVinci Resolve Timeline Oluştur ({selectedItems.length} Replik {!includeSubtitles ? '• Saf Ses & Görsel' : ''})
                  </span>
                </>
              )}
            </button>
          </div>
        )}

      </div>
    </div>
  );
}
